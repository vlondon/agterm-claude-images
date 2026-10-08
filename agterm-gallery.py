#!/usr/bin/env python3
"""agterm-gallery: show every image in a Claude Code conversation in agterm's split pane.

Claude Code's terminal UI prints images as "[Image #1]". This hook copies each image in the
conversation (pasted screenshots, images Claude reads, MCP screenshots) into a static HTML
gallery and shows it as an HTML overlay on the split pane beside Claude (agterm >= 0.33).

Hook usage (PostToolUse, UserPromptSubmit, Stop), from ~/.claude/settings.json (install.sh
writes these):
    {"type": "command", "command": "~/.claude/hooks/agterm-gallery.py"}
The hook forks and returns at once, so Claude never waits on it.

Manual usage from a shell in the same agterm pane as Claude:
    agterm-gallery.py open     show the gallery (creates the split if needed)
    agterm-gallery.py close    close the gallery overlay
    agterm-gallery.py toggle   open or close it (what the hotkey runs)
    agterm-gallery.py clear    forget this conversation's images

Environment:
    AGTERM_GALLERY=0            disable entirely
    AGTERM_GALLERY_AUTO_OPEN=0  never create the split; only refresh a gallery already shown
    AGTERM_GALLERY_ROOT         where galleries live (default ~/.cache/agterm-gallery)
    AGTERMCTL                   agtermctl to use (default: PATH, then /Applications/agterm.app)

Hotkey, in ~/.config/agterm/keymap.conf (a custom command gets AGT_* vars, mapped below):
    command "Image gallery" cmd+shift+i "$HOME/.claude/hooks/agterm-gallery.py" toggle

The split pane is only taken over when the gallery created it. A split the user opened for
something else is never covered automatically; `open` does that on request.
"""

import base64
import fcntl
import hashlib
import html
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.environ.get("AGTERM_GALLERY_ROOT") or os.path.join(
    os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "agterm-gallery")
MIN_VERSION = (0, 33)
KEEP_DAYS = 14
EXT = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp"}


# --- images ------------------------------------------------------------------------------------

def find_images(node, label, out):
    """find_images collects (mime, base64, label) from the three shapes images take in Claude Code
    JSON: API blocks ({type: image, source: {type: base64}}), Read results ({file: {base64, type}})
    and MCP content ({type: image, data, mimeType})."""
    if isinstance(node, list):
        for item in node:
            find_images(item, label, out)
        return
    if not isinstance(node, dict):
        return
    src = node.get("source")
    if node.get("type") == "image" and isinstance(src, dict) and src.get("type") == "base64":
        out.append((src.get("media_type", ""), src.get("data", ""), label))
    elif isinstance(node.get("base64"), str) and str(node.get("type", "")).startswith("image/"):
        out.append((node["type"], node["base64"], label))
    elif node.get("type") == "image" and isinstance(node.get("data"), str) and node.get("mimeType"):
        out.append((node["mimeType"], node["data"], label))
    else:
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                find_images(value, "tool result" if node.get("type") == "tool_result" else label, out)


def transcript_images(state, path):
    """transcript_images reads the transcript from the saved offset to its last complete line."""
    out = []
    try:
        size = os.path.getsize(path)
    except OSError:
        return out
    offset = state.get("offset", 0)
    if size < offset:  # rewritten transcript: start over, the seen set still dedupes
        offset = 0
    with open(path, "rb") as f:
        f.seek(offset)
        chunk = f.read(size - offset)
    end = chunk.rfind(b"\n") + 1
    for line in chunk[:end].splitlines():
        if b'"image' not in line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") == "user":
            find_images(entry.get("message", {}).get("content"), "pasted", out)
        elif entry.get("type") == "attachment":  # a prompt sent mid-turn arrives as a queued_command
            find_images(entry.get("attachment"), "pasted", out)
    state["offset"] = offset + end
    return out


def add_images(state, gdir, found):
    seen = set(state.setdefault("seen", []))
    items = state.setdefault("items", [])
    added = 0
    for mime, data, label in found:
        digest = hashlib.sha1(data.encode()).hexdigest()
        if not data or digest in seen or mime not in EXT:
            continue
        try:
            raw = base64.b64decode(data)
        except ValueError:
            continue
        seen.add(digest)
        state["seen"].append(digest)
        n = len(items) + 1
        name = f"{n:04d}.{EXT[mime]}"
        with open(os.path.join(gdir, "img", name), "wb") as f:
            f.write(raw)
        items.append({"n": n, "file": name, "label": label, "time": time.strftime("%H:%M")})
        added += 1
    return added


def write_index(gdir, items):
    figures = "\n".join(
        f'<figure><img src="img/{html.escape(i["file"])}" alt="image {i["n"]}">'
        f'<figcaption>#{i["n"]} · {html.escape(i["label"])} · {i["time"]}</figcaption></figure>'
        for i in reversed(items))
    empty = '<p class="empty">No images in this conversation yet.</p>'
    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Images · {len(items)}</title>
<style>
body {{ margin: 0; padding: 12px; font: 12px -apple-system, sans-serif;
  background: var(--agterm-background, #1e1e1e); color: var(--agterm-foreground, #ddd); }}
figure {{ margin: 0 0 18px; }}
img {{ display: block; max-width: 100%; height: auto; border-radius: 4px;
  outline: 1px solid color-mix(in srgb, var(--agterm-foreground, #ddd) 15%, transparent); }}
figcaption {{ margin-top: 4px; opacity: .6; }}
.empty {{ opacity: .6; }}
</style></head><body>
{figures or empty}
</body></html>
"""
    tmp = os.path.join(gdir, ".index.html.tmp")
    with open(tmp, "w") as f:
        f.write(page)
    os.replace(tmp, os.path.join(gdir, "index.html"))


# --- state -------------------------------------------------------------------------------------

def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(path, value):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(value, f)
    os.replace(tmp, path)


def pane_state_path():
    return os.path.join(ROOT, "panes", os.environ["AGTERM_SESSION_ID"] + ".json")


def prune():
    cutoff = time.time() - KEEP_DAYS * 86400
    for name in os.listdir(ROOT):
        path = os.path.join(ROOT, name)
        if name != "panes" and os.path.isdir(path) and os.path.getmtime(path) < cutoff:
            shutil.rmtree(path, ignore_errors=True)


# --- agterm ------------------------------------------------------------------------------------

def ctl(*args):
    exe = os.environ.get("AGTERMCTL") or shutil.which("agtermctl") or \
        "/Applications/agterm.app/Contents/MacOS/agtermctl"
    cmd = [exe, *args]
    if os.environ.get("AGTERM_SOCKET"):
        cmd += ["--socket", os.environ["AGTERM_SOCKET"]]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout if p.returncode == 0 else None


def find_session():
    """find_session returns (tree, session) for this pane's agterm session, or (None, None)."""
    sid = os.environ["AGTERM_SESSION_ID"]
    window = os.environ.get("AGTERM_WINDOW_ID")
    for extra in ((["--window", window] if window else []), []):
        out = ctl("tree", "--json", *extra)
        if not out:
            continue
        tree = json.loads(out).get("result", {}).get("tree", {})
        for ws in tree.get("workspaces", []):
            for s in ws.get("sessions", []):
                if s.get("id", "").upper() == sid.upper():
                    return tree, s
    return None, None


def version_ok(tree):
    try:
        parts = tuple(int(x) for x in tree["app"]["version"].split(".")[:2])
    except (KeyError, ValueError, AttributeError):
        return False
    return parts >= MIN_VERSION


def show(gdir, force=False):
    """show reloads the gallery overlay if it is up, or opens it on the pane beside Claude."""
    tree, s = find_session()
    if not s or not version_ok(tree):
        return
    sid = s["id"]
    index = os.path.join(gdir, "index.html")
    mine = os.environ.get("AGTERM_PANE_ID", "")
    surfaces = {x.get("kind"): x for x in s.get("surfaces", [])}
    role = next((k for k, x in surfaces.items() if x.get("paneID") == mine and k in ("left", "right")), "left")
    other = "right" if role == "left" else "left"

    page = next((h for h in s.get("htmlOverlays", []) if h.get("pane") == other), None)
    if page:
        if page.get("file") == index:
            ctl("session", "overlay", "reload", "--pane", other, "--target", sid)
            return
        if not (page.get("file") or "").startswith(ROOT + os.sep):
            return  # someone else's page
        ctl("session", "overlay", "close", "--pane", other, "--target", sid)
    elif other in s.get("paneOverlays", []):
        return  # a program overlay holds the pane

    pstate = load(pane_state_path(), {})
    if not s.get("hasSplit"):
        if not force and os.environ.get("AGTERM_GALLERY_AUTO_OPEN", "1") == "0":
            return
        if ctl("session", "split", "on", "--target", sid) is None:
            return
        _, s = find_session()
        created = next((x.get("paneID") for x in (s or {}).get("surfaces", []) if x.get("kind") == other), None)
        pstate["splitPaneID"] = created
        save(pane_state_path(), pstate)
    elif not force and surfaces.get(other, {}).get("paneID") != pstate.get("splitPaneID"):
        return  # the user's own split: leave it alone

    ctl("session", "overlay", "open", "--html", index, "--cwd", gdir, "--pane", other, "--target", sid)
    ctl("session", "focus", role, "--target", sid)


# --- entry points ------------------------------------------------------------------------------

def hook(event):
    session_id = event.get("session_id")
    if not session_id:
        return
    gdir = os.path.join(ROOT, session_id)
    os.makedirs(os.path.join(gdir, "img"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "panes"), exist_ok=True)
    with open(os.path.join(gdir, ".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load(os.path.join(gdir, "state.json"), {})
        found = []
        if event.get("hook_event_name") == "PostToolUse":
            name = event.get("tool_name", "tool").removeprefix("mcp__")
            path = (event.get("tool_input") or {}).get("file_path")
            find_images(event.get("tool_response"), f"{name} {os.path.basename(path)}" if path else name, found)
        if event.get("transcript_path"):
            found += transcript_images(state, event["transcript_path"])
        added = add_images(state, gdir, found)
        save(os.path.join(gdir, "state.json"), state)
        pstate = load(pane_state_path(), {})
        pstate["gallery"] = gdir
        save(pane_state_path(), pstate)
        if added:
            write_index(gdir, state["items"])
            show(gdir)
    if event.get("hook_event_name") == "Stop":
        prune()


def manual(cmd):
    gdir = load(pane_state_path(), {}).get("gallery")
    if not gdir or not os.path.isdir(gdir):
        sys.exit("no gallery for this agterm session yet: the hook has not run here")
    if cmd == "open":
        state = load(os.path.join(gdir, "state.json"), {})
        write_index(gdir, state.get("items", []))
        show(gdir, force=True)
    elif cmd in ("close", "toggle"):
        _, s = find_session()
        shown = [h for h in (s or {}).get("htmlOverlays", []) if (h.get("file") or "").startswith(ROOT + os.sep)]
        for h in shown:
            ctl("session", "overlay", "close", "--pane", h.get("pane", "right"), "--target", s["id"])
        if cmd == "toggle" and not shown:
            return manual("open")
    elif cmd == "clear":
        state = load(os.path.join(gdir, "state.json"), {})
        state["items"] = []  # keep offset and seen so old images do not come back
        save(os.path.join(gdir, "state.json"), state)
        shutil.rmtree(os.path.join(gdir, "img"), ignore_errors=True)
        os.makedirs(os.path.join(gdir, "img"))
        write_index(gdir, [])
        show(gdir)
    else:
        sys.exit(f"usage: {os.path.basename(sys.argv[0])} open|close|toggle|clear")


def main():
    if os.environ.get("AGT_SESSION_ID"):  # fired from a keymap custom command, which passes AGT_* instead
        for name in ("SESSION_ID", "PANE_ID", "SOCKET", "WINDOW_ID"):
            if os.environ.get("AGT_" + name):
                os.environ["AGTERM_" + name] = os.environ["AGT_" + name]
        os.environ["AGTERM_ENABLED"] = "1"
    if os.environ.get("AGTERM_ENABLED") != "1" or not os.environ.get("AGTERM_SESSION_ID"):
        return
    if os.environ.get("AGTERM_GALLERY", "1") == "0":
        return
    if len(sys.argv) > 1:
        return manual(sys.argv[1])
    raw = sys.stdin.buffer.read()
    if os.environ.get("AGTERM_GALLERY_FOREGROUND") != "1":
        if os.fork():
            return  # Claude only waits for this parent
        os.setsid()
        devnull = os.open(os.devnull, os.O_RDWR)
        for fd in (0, 1, 2):
            os.dup2(devnull, fd)
    try:
        hook(json.loads(raw))
    except Exception:  # a broken gallery must never disturb the conversation
        if os.environ.get("AGTERM_GALLERY_FOREGROUND") == "1":
            raise


if __name__ == "__main__":
    main()
