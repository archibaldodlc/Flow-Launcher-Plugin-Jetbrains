### I'm a developer but this plugin was made using AI in some cases.

# Flow Launcher — JetBrains

Open recent projects and JetBrains IDEs from Flow Launcher. **No configuration required**:
installed IDEs and their recent projects are detected automatically.

## Usage

| Query | Action |
|---|---|
| `jb` | Lists all recent projects, from most recently used to oldest |
| `jb flow` | Searches for "flow" in the project name, then in the path if it does not match |
| `jb py` | Opens PyCharm in a new window and lists its recent projects below |
| `jb py flow` | Works like `jb flow`, but only searches PyCharm projects |

The first token is interpreted as an IDE only when it exactly matches an alias, so `jb pyth`
remains a regular text search.

Alias: `py`/`pycharm`, `ij`/`idea`/`intellij`, `go`/`goland`, `ws`/`webstorm`, `db`/`datagrip`,
`cl`/`clion`, `rd`/`rider`, `ps`/`phpstorm`, `rm`/`rubymine`, `rr`/`rustrover`, `as`/`studio`.
The full lowercase IDE name and its product code (`py`, `iu`, `ws`...) also work.

**Context menu** (`Shift+Enter` on a project): open its folder in File Explorer, copy its path,
or open the same project in any other installed IDE.

## How detection works

- **IDEs**: `product-info.json` in the installation directory provides the product code, version,
  executable, and icon. Candidate directories come from JetBrains Toolbox's `state.json`,
  `%LOCALAPPDATA%\Programs\*`, and `C:\Program Files\JetBrains\*`. The Windows registry is checked
  only when an IDE associated with recent projects cannot be found through those locations.
- **Projects**: `%APPDATA%\JetBrains\<Product><Version>\options\recentProjects.xml`. Lists from each
  major version are merged (2026.1 and 2026.2 do not contain the same entries), and projects whose
  folders no longer exist are discarded.

Only the standard library is used; the sole dependency is `flowlauncher`.

## Development

```powershell
# dependencies bundled with the plugin
python -m pip install -r requirements.txt -t ./lib

# run it as Flow does, using its own Python interpreter
& "$env:APPDATA\FlowLauncher\Environments\Python\PythonEmbeddable-v3.11.4\python.exe" main.py --% {"method":"query","parameters":["py flow"]}
```

To test it in Flow without copying it after every change, create a directory junction:

```powershell
cmd /c mklink /J "$env:APPDATA\FlowLauncher\Plugins\Flow.Launcher.Plugin.Jetbrains" "[<repository path>](D:\git\10-OtrasCosas\Flow.Launcher.Plugin.Jetbrains)"
```

Then restart Flow Launcher.
