#!/bin/bash
# install.sh: install agterm-image-gallery for Claude Code, or remove it with --uninstall.
#
#   ./install.sh                      install the hook, plus the cmd+shift+i hotkey
#   ./install.sh --hotkey cmd+opt+i   install with another hotkey
#   ./install.sh --no-hotkey          install the hook only
#   ./install.sh --uninstall          remove the hook, the hotkey and the script
#
# Safe to re-run: it replaces its own entries and never touches anything else.
# Respects CLAUDE_CONFIG_DIR (default ~/.claude) and AGTERM_CONFIG_DIR (default ~/.config/agterm).
set -euo pipefail

HOTKEY="cmd+shift+i"
MODE=install
while [ $# -gt 0 ]; do
    case "$1" in
        --hotkey) HOTKEY="${2:?--hotkey needs a chord, e.g. cmd+shift+i}"; shift ;;
        --no-hotkey) HOTKEY="" ;;
        --uninstall) MODE=uninstall ;;
        -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $1 (see --help)" >&2; exit 1 ;;
    esac
    shift
done

command -v python3 >/dev/null || { echo "python3 is required (xcode-select --install)" >&2; exit 1; }

CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SETTINGS="$CLAUDE_DIR/settings.json"
TARGET="$CLAUDE_DIR/hooks/agterm-gallery.py"
KEYMAP="${AGTERM_CONFIG_DIR:-$HOME/.config/agterm}/keymap.conf"
MARK="# agterm-image-gallery"
SRC="$(cd "$(dirname "$0")" && pwd)/agterm-gallery.py"

# settings.json: drop every hook that runs agterm-gallery.py, then add ours back on install
update_settings() {
    [ "$MODE" = uninstall ] && [ ! -f "$SETTINGS" ] && return
    mkdir -p "$CLAUDE_DIR"
    [ -f "$SETTINGS" ] && cp "$SETTINGS" "$SETTINGS.bak-agterm-gallery"
    python3 - "$SETTINGS" "\"$TARGET\"" "$MODE" <<'EOF'
import json, os, sys
path, command, mode = sys.argv[1:4]
try:
    with open(path) as f:
        data = json.load(f)
except FileNotFoundError:
    data = {}
except ValueError as e:
    sys.exit(f"{path} is not valid JSON ({e}); fix it and re-run")
hooks = data.setdefault("hooks", {})
for event in ("PostToolUse", "UserPromptSubmit", "Stop"):
    kept = []
    for group in hooks.get(event, []):
        rest = [h for h in group.get("hooks", []) if "agterm-gallery.py" not in h.get("command", "")]
        if rest:
            kept.append({**group, "hooks": rest})
    if mode == "install":
        entry = {"hooks": [{"type": "command", "command": command}]}
        kept.append({"matcher": "", **entry} if event == "PostToolUse" else entry)
    if kept:
        hooks[event] = kept
    else:
        hooks.pop(event, None)
if not hooks:
    data.pop("hooks")
tmp = path + ".tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.replace(tmp, path)
EOF
}

# keymap.conf: drop our lines, then append the hotkey on install
CTL="${AGTERMCTL:-$(command -v agtermctl || echo /Applications/agterm.app/Contents/MacOS/agtermctl)}"
ctl() { [ -x "$CTL" ] && "$CTL" "$@" ${AGTERM_SOCKET:+--socket "$AGTERM_SOCKET"} 2>/dev/null; }

# keymap.conf: drop our lines, then append the hotkey on install
update_keymap() {
    if [ -f "$KEYMAP" ]; then
        grep -v -e "agterm-gallery.py" -e "^$MARK" "$KEYMAP" > "$KEYMAP.tmp" || true
        mv "$KEYMAP.tmp" "$KEYMAP"
        ctl keymap reload >/dev/null || true
    fi
    if [ "$MODE" = install ] && [ -n "$HOTKEY" ]; then
        # a running agterm also knows the built-in defaults, which keymap.conf does not list
        local chord="(^|[[:space:]|])${HOTKEY//+/\\+}([[:space:]|]|$)"
        if { [ -f "$KEYMAP" ] && grep -qiE "$chord" "$KEYMAP"; } || ctl keymap list | grep -qiE "$chord"; then
            echo "warning: $HOTKEY is already bound in agterm; skipped the hotkey (pick another with --hotkey)" >&2
            HOTKEY=""
            return
        fi
        mkdir -p "$(dirname "$KEYMAP")"
        printf '%s: show or hide the Claude image gallery\ncommand "Image gallery" %s "%s" toggle\n' \
            "$MARK" "$HOTKEY" "$TARGET" >> "$KEYMAP"
        ctl keymap reload >/dev/null || true  # otherwise it loads at the next launch
    fi
}

if [ "$MODE" = install ]; then
    mkdir -p "$(dirname "$TARGET")"
    cp "$SRC" "$TARGET"
    chmod +x "$TARGET"
    update_settings
    update_keymap
    echo "installed $TARGET"
    echo "hooks added to $SETTINGS (backup: $SETTINGS.bak-agterm-gallery)"
    [ -n "$HOTKEY" ] && echo "hotkey: $HOTKEY (custom command \"Image gallery\" in $KEYMAP)"
    echo "restart running Claude Code sessions to pick up the hooks"
else
    update_settings
    update_keymap
    rm -f "$TARGET"
    echo "removed the hook, the hotkey and $TARGET"
    echo "saved images stay in ~/.cache/agterm-gallery until you delete them"
fi
