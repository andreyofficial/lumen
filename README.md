# Lumen

A fast, focused, professionally-styled code editor for Linux, built with PyQt6.

> Strict monochrome chrome (pure black / white surfaces, brushed-graphite
> hero buttons with a soft glow halo) paired with **vibrant, fully-coloured
> syntax highlighting**. Every code token gets its own hue so the editor
> reads at a glance.

## Highlights

- **Two themes** — a *Dark* theme (true black backgrounds, white text) and
  a *Light* sister theme (pure white, black text). Toggle anywhere with
  `Ctrl+K Ctrl+T`, the activity-bar moon/sun button, or the status-bar
  indicator.
- **Coloured syntax** — pink keywords, mint strings, amber numbers, cyan
  functions, gold class names, lavender constants, rose decorators,
  aqua types, slate-italic comments. Saturated against the black bg so
  tokens read like they're glowing.
- **TODO / FIXME / NOTE highlighting** — markers in any language's
  comments are picked out in warning amber / red / cyan respectively.
- **Glossy hero buttons with shine glow** — multi-stop chrome gradient
  plus a soft outer halo (`QGraphicsDropShadowEffect`) that intensifies
  on hover and tightens on press, FileHub-style.
- **PyCharm-style productivity**:
  - File-structure outline panel (`Ctrl+F12`) — classes, methods, top-level
    functions for Python / JS / TS / Rust / Go / Java / C / C++.
  - Recent files switcher (`Ctrl+E`) with type-to-filter.
  - Go-to-line:column dialog (`Ctrl+G`).
  - Run current file (`Shift+F10`) — output streamed into a docked
    Run console next to the integrated terminal. Stop with `Ctrl+F2`.
  - Code-completion popup (`Ctrl+Space`, also auto-triggers after typing
    two letters). Suggests language keywords + words already in the file.
  - Move line up / down with `Alt+Shift+↑` / `Alt+Shift+↓`.
  - Duplicate line / selection with `Ctrl+D`, toggle line comment with
    `Ctrl+/`, smart bracket / quote auto-pairing.
- **Multi-language syntax highlighting** — Python, JavaScript, TypeScript,
  JSON, HTML, CSS, Markdown, C, C++, Go, Rust, Shell, YAML, TOML, INI.
- **Built-in AI assistant** — open with `Ctrl+Shift+A`. Speaks the OpenAI
  chat-completions protocol so it works with **local Ollama by default**
  (no API key, no setup, no payment), or any compatible provider
  (OpenAI, Groq, OpenRouter, your own server). Streaming replies, code
  context attach, "Ask AI about selection" (`Ctrl+L`). Toggle the entire
  feature off in *AI → Enable AI Assistant*; the toggle persists across
  restarts.
- **Chat autosave + history** — every AI conversation is debounced-saved
  to `~/.config/Lumen/Lumen/ai-chats.json` as you type and stream. Click
  the clock icon in the AI toolbar to switch between past chats, rename
  them, or delete them. The most recent conversation is restored when
  the editor reopens.
- **Taskbar / system-tray icon** — Lumen registers a tray icon while
  running. Right-click for quick actions (Show Lumen, New File, Open,
  Ask Lumen AI, Quit); single-click to toggle the window.
- **Tabs** with close buttons, modified-marker (•), drag-to-reorder, and
  tooltips.
- **Activity bar + multi-view sidebar** — Explorer, Search, Structure, AI.
- **Project-wide search (`Ctrl+Shift+F`)** — incremental, async search
  across the active folder.
- **Integrated terminal (`` Ctrl+` ``)** — runs in the project root,
  built-in `cd`/`clear`, history with ↑/↓.
- **Bottom dock** — tabbed Terminal + Run views share the same horizontal
  band so the editor doesn't lose extra vertical real estate.
- **Minimap** on the right of every editor; click anywhere to scroll.
- **Find & Replace** with case / whole-word / regex toggles and live
  match counts.
- **Command palette** (`Ctrl+Shift+P`) for fuzzy-searchable actions.
- **Welcome screen** with three glowing hero buttons and a shortcut
  cheatsheet.
- **Status bar** showing path, line/column, indent style, encoding,
  theme, and language (clickable to switch).
- **Persistent state** — geometry, sidebar/terminal visibility, theme,
  font size, recent files, last folder, AI enable/disable.
- **Self-contained** — SVG icons rendered inline, no external icon themes.

## Run from source

```bash
cd lumen
./run.sh
```

The launcher creates a virtualenv in `.venv/`, installs `PyQt6`, and starts
the app. Pass files or a folder as arguments:

```bash
./run.sh path/to/file.py path/to/folder
```

## Build a standalone executable

```bash
cd lumen
./build.sh                # one-folder build at  dist/lumen/   (fast startup)
./build.sh --onefile      # single binary at      dist/lumen    (slower startup)
./build.sh --clean        # remove previous build/ + dist/
```

PyInstaller produces a fully self-contained bundle — users do **not** need
Python or PyQt6 installed to run it. Distribute it however you like:

```bash
tar czf lumen-linux-x86_64.tar.gz -C dist lumen   # one-folder bundle
cp dist/lumen ~/bin/lumen                         # single binary
```

Run it directly:

```bash
./dist/lumen/lumen          # one-folder build
./dist/lumen                # one-file build
```

## Requirements

- Python 3.10+ (only to build / run from source — not to use the binary)
- `PyQt6` (installed automatically by `run.sh` and `build.sh`)
- A working X11 / Wayland session
- *Optional, for the AI assistant*: a running `ollama serve` plus a model
  pulled with `ollama pull llama3.2`. The editor itself ships with no AI
  baked in; it just speaks the OpenAI HTTP protocol to whatever endpoint
  you configure.

## Install (system menu)

```bash
./install.sh
```

This creates `~/.local/bin/lumen`, copies the SVG icon to
`~/.local/share/icons/hicolor/scalable/apps/`, and writes a
`~/.local/share/applications/lumen.desktop` entry so Lumen appears in
your application launcher with a hammer icon. Uninstall with
`./uninstall.sh`.

## Keyboard Shortcuts

| Action | Shortcut |
| --- | --- |
| Command Palette | `Ctrl+Shift+P` |
| Recent Files | `Ctrl+E` |
| Go to Line | `Ctrl+G` |
| File Structure | `Ctrl+F12` |
| New File | `Ctrl+N` |
| Open File / Folder | `Ctrl+O` / `Ctrl+K Ctrl+O` |
| Save / Save As | `Ctrl+S` / `Ctrl+Shift+S` |
| Close Tab | `Ctrl+W` |
| Find / Replace | `Ctrl+F` / `Ctrl+H` |
| Find Next / Previous | `F3` / `Shift+F3` |
| Search in Folder | `Ctrl+Shift+F` |
| AI Assistant | `Ctrl+Shift+A` |
| Ask AI About Selection | `Ctrl+L` |
| Toggle Sidebar | `Ctrl+B` |
| Show Explorer | `Ctrl+Shift+E` |
| Toggle Terminal | `` Ctrl+` `` |
| Toggle Theme | `Ctrl+K Ctrl+T` |
| Toggle Comment | `Ctrl+/` |
| Duplicate Line / Selection | `Ctrl+D` |
| Move Line Up / Down | `Alt+Shift+↑` / `Alt+Shift+↓` |
| Run Current File | `Shift+F10` |
| Stop Running Process | `Ctrl+F2` |
| Trigger Completion | `Ctrl+Space` |
| Zoom In / Out / Reset | `Ctrl+=` / `Ctrl+-` / `Ctrl+0` |
| Quit | `Ctrl+Q` |

## Project Layout

```
lumen/
├── lumen/
│   ├── app.py           # main window, menus, toolbar, tab/state plumbing
│   ├── editor.py        # CodeEditor (gutter, indent, completion popup)
│   ├── highlighter.py   # multi-language syntax highlighter + TODO badges
│   ├── findbar.py       # find/replace bar
│   ├── palette.py       # command palette overlay
│   ├── sidebar.py       # file tree
│   ├── search.py        # project-wide search panel (async)
│   ├── activitybar.py   # left rail with view-switch icons
│   ├── terminal.py      # integrated terminal (QProcess)
│   ├── minimap.py       # editor minimap
│   ├── welcome.py       # welcome screen with shine buttons
│   ├── ai.py            # AI assistant panel (OpenAI / Ollama)
│   ├── chats.py         # JSON-backed chat history (autosave + restore)
│   ├── preferences.py   # tabbed preferences dialog
│   ├── pycharm.py       # GotoLine, RecentFiles, Outline, Run dialogs
│   ├── shine.py         # ShineButton (animated soft-glow halo)
│   ├── icons.py         # inline SVG icon registry
│   └── theme.py         # Dark + Light palettes and Qt Style Sheet
├── assets/              # app icons (lumen.svg + lumen-hammer.svg)
├── lumen.desktop        # desktop entry template
├── install.sh / uninstall.sh
├── run.sh               # source launcher
├── build.sh             # builds a standalone executable via PyInstaller
├── lumen.spec           # PyInstaller spec
├── main.py              # PyInstaller entry point
├── requirements.txt
├── LICENSE
└── README.md
```

## License

[MIT](LICENSE) — feel free to adapt.
