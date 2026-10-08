# agterm-image-gallery

See the images in your Claude Code conversations right inside [agterm](https://github.com/umputun/agterm).

Claude Code's terminal UI shows an image as `[Image #1]` and nothing more, in any terminal.
The Claude mobile and desktop apps draw them because they are graphical clients, not terminals.
This adds the missing piece for agterm: a gallery in the split pane beside Claude that fills in as images show up in the conversation.

It picks up:

- screenshots you paste, including ones pasted while Claude is still working
- images Claude reads with its `Read` tool
- screenshots returned by MCP tools (browser automation, simulators and so on)

Newest image first, in the terminal's theme colours.

## Requirements

- macOS with **agterm 0.33 or later** (HTML overlays arrived in 0.33). Check with `agtermctl version`.
- **Claude Code**, running inside agterm.
- **python3** (ships with the Xcode command line tools: `xcode-select --install`).

## Install

```sh
git clone <this repo> agterm-image-gallery
cd agterm-image-gallery
./install.sh
```

The installer:

1. copies `agterm-gallery.py` to `~/.claude/hooks/`,
2. adds it to the `PostToolUse`, `UserPromptSubmit` and `Stop` hooks in `~/.claude/settings.json`, leaving your other hooks alone (a backup goes to `settings.json.bak-agterm-gallery`),
3. binds **⌘⇧I** in `~/.config/agterm/keymap.conf` to show or hide the gallery, and reloads the keymap if agterm is running.

Then restart any Claude Code sessions that are already running, so they load the hooks.

Options: `--hotkey cmd+opt+i` for another chord, `--no-hotkey` to skip the hotkey.
The installer can be re-run safely; it replaces its own entries.
It respects `CLAUDE_CONFIG_DIR` and `AGTERM_CONFIG_DIR` if you've moved either directory.

## Use

Paste a screenshot into Claude, or ask Claude to look at an image file.
A split opens on the right with the gallery, and keyboard focus stays with Claude.

- **⌘⇧I** shows or hides the gallery. Press it from Claude's pane: it opens in the *other* pane.
- **⌘W** in the gallery closes it; the next image brings it back.
- From a shell in Claude's pane: `~/.claude/hooks/agterm-gallery.py open | close | toggle | clear`.

When an image appears:

- an image Claude reads shows up straight away,
- an image pasted at the start of a turn shows up at Claude's first tool call or the end of the turn,
- an image pasted while Claude is working shows up at the tool call after it's delivered.

The gallery never covers a split you opened yourself (say, a second agent).
In that case nothing opens on its own; press ⌘⇧I when you want the gallery over that pane.

## Settings

Environment variables, set where Claude Code starts:

| Variable | Effect |
|---|---|
| `AGTERM_GALLERY=0` | turn it off |
| `AGTERM_GALLERY_AUTO_OPEN=0` | never open a split by itself; only refresh a gallery that is already shown |
| `AGTERM_GALLERY_ROOT` | where images are saved (default `~/.cache/agterm-gallery`) |
| `AGTERMCTL` | the `agtermctl` to use (default: `PATH`, then `/Applications/agterm.app`) |

## How it works

Claude Code passes each hook the conversation's transcript path.
The hook reads the transcript from where it last stopped, decodes every image in it, and saves them as files under `~/.cache/agterm-gallery/<conversation id>/`.
Images are matched by content, so an image seen twice is saved once.
It then writes a static `index.html` and shows it with `agtermctl session overlay open --html … --pane right`, or reloads it with `session overlay reload` if it is already up.
The page has no JavaScript and only reads files inside that folder.

The hook forks and returns at once, so Claude never waits for it (about 50 ms per call).
Outside agterm, or on an agterm older than 0.33, it does nothing.
Galleries older than 14 days are deleted.

## Limitations

- Images Claude reads appear at the size Claude was sent (at most 2000 px on the long side), not the original file.
- Images from subagents aren't included; those live in separate transcripts.
- The gallery follows one Claude conversation. After `/clear` or a new session, the next image starts a fresh gallery.

## Uninstall

```sh
./install.sh --uninstall
```

This removes the hooks, the hotkey and the script.
Saved images stay in `~/.cache/agterm-gallery` until you delete that folder.

## License

MIT
