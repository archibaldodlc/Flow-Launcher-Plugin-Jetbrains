# -*- coding: utf-8 -*-
"""Detection of installed JetBrains IDEs.

All information comes from `product-info.json`, which each IDE includes in its
installation directory. It works for both Toolbox and standalone installations,
so no name tables or hardcoded paths are needed.
"""

import glob
import json
import os
from dataclasses import dataclass, field

_LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")

_TOOLBOX_STATE = os.path.join(_LOCALAPPDATA, "JetBrains", "Toolbox", "state.json")

# Directories where installations not managed by Toolbox usually appear.
_INSTALL_GLOBS = (
    os.path.join(_LOCALAPPDATA, "Programs", "*"),
    r"C:\Program Files\JetBrains\*",
    r"C:\Program Files (x86)\JetBrains\*",
)

# Fallback icon when the IDE does not include an .ico file.
_PLUGIN_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FALLBACK_ICON: str = os.path.join(_PLUGIN_DIR, "Images", "app.png")

# Aliases by product code. The lowercase IDE name is added automatically, so
# only abbreviations belong here.
_ALIASES = {
    "PY": ("py", "pycharm"),
    "PC": ("py", "pycharm"),
    "IU": ("ij", "idea", "intellij"),
    "IC": ("ij", "idea", "intellij"),
    "GO": ("go", "goland"),
    "WS": ("ws", "webstorm"),
    "DB": ("db", "datagrip"),
    "CL": ("cl", "clion"),
    "RD": ("rd", "rider"),
    "PS": ("ps", "phpstorm"),
    "RM": ("rm", "rubymine"),
    "RR": ("rr", "rustrover"),
    "AI": ("as", "studio", "androidstudio"),
}


@dataclass
class IDE:
    code: str
    name: str
    version: str
    exe: str
    icon: str
    aliases: frozenset = field(default_factory=frozenset)

    @property
    def label(self):
        return "%s %s" % (self.name, self.version) if self.version else self.name


def discover_ides(required_codes=None):
    """Return {product code: IDE} for installed IDEs.

    `required_codes` contains the relevant codes (those found in recent
    projects). If any cannot be found through inexpensive methods, scan the
    registry as a last resort; normally, the registry is not accessed.
    """
    found = {}
    for install_dir in _cheap_candidates():
        _register(found, install_dir)

    missing = set(required_codes or ()) - set(found)
    if missing:
        for install_dir in _registry_candidates():
            _register(found, install_dir)

    return found


def _register(found, install_dir):
    ide = _read_product_info(install_dir)
    if ide is None:
        return
    current = found.get(ide.code)
    if current is None or _version_key(ide.version) > _version_key(current.version):
        found[ide.code] = ide


def _cheap_candidates():
    seen = set()
    for install_dir in _toolbox_locations():
        if _mark(seen, install_dir):
            yield install_dir
    for pattern in _INSTALL_GLOBS:
        for install_dir in glob.iglob(pattern):
            if os.path.isdir(install_dir) and _mark(seen, install_dir):
                yield install_dir


def _mark(seen, path):
    key = os.path.normcase(os.path.normpath(path))
    if key in seen:
        return False
    seen.add(key)
    return True


def _toolbox_locations():
    try:
        with open(_TOOLBOX_STATE, encoding="utf-8") as handle:
            state = json.load(handle)
    except (OSError, ValueError):
        return
    for tool in state.get("tools") or ():
        location = tool.get("installLocation")
        if location:
            yield location


def _registry_candidates():
    try:
        import winreg
    except ImportError:  # Another operating system.
        return

    roots = (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    )
    for hive, subkey in roots:
        try:
            parent = winreg.OpenKey(hive, subkey)
        except OSError:
            continue
        with parent:
            count = winreg.QueryInfoKey(parent)[0]
            for index in range(count):
                try:
                    name = winreg.EnumKey(parent, index)
                    with winreg.OpenKey(parent, name) as key:
                        publisher = _reg_value(key, "Publisher")
                        if not publisher or "jetbrains" not in publisher.lower():
                            continue
                        location = _reg_value(key, "InstallLocation")
                except OSError:
                    continue
                if location:
                    yield location


def _reg_value(key, name):
    import winreg

    try:
        value = winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None
    return value if isinstance(value, str) else None


def _read_product_info(install_dir):
    try:
        with open(os.path.join(install_dir, "product-info.json"), encoding="utf-8") as handle:
            info = json.load(handle)
    except (OSError, ValueError):
        return None

    code = info.get("productCode")
    launches = info.get("launch") or []
    launcher = launches[0].get("launcherPath") if launches else ""
    if not code or not launcher:
        return None

    exe = os.path.join(install_dir, launcher.replace("/", os.sep))
    if not os.path.isfile(exe):
        return None

    name = info.get("name") or code
    aliases = set(_ALIASES.get(code, ()))
    aliases.add(name.lower().replace(" ", ""))
    aliases.add(code.lower())

    return IDE(
        code=code,
        name=name,
        version=info.get("version") or "",
        exe=exe,
        icon=_icon_for(install_dir, info.get("svgIconPath")),
        aliases=frozenset(aliases),
    )


def _icon_for(install_dir: str, svg_icon_path) -> str:
    """Flow does not rasterize SVG, but IDEs include the same icon as .ico."""
    if svg_icon_path:
        ico = os.path.join(install_dir, svg_icon_path.replace("/", os.sep))
        ico = os.path.splitext(ico)[0] + ".ico"
        if os.path.isfile(ico):
            return ico
    return _FALLBACK_ICON


def _version_key(version):
    parts = []
    for chunk in (version or "").split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    return tuple(parts)
