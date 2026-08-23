# -*- coding: utf-8 -*-
"""Read recent JetBrains projects.

Each IDE maintains its own `recentProjects.xml` for every major version
(`PyCharm2026.1`, `PyCharm2026.2`, ...), and the lists differ, so they must be
merged by product while keeping the most recent timestamp.
"""

import glob
import os
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass

_CONFIG_GLOB = os.path.join(os.environ.get("APPDATA", ""), "JetBrains", "*", "options", "recentProjects.xml")

_MAP_PATH = 'component[@name="RecentProjectsManager"]/option[@name="additionalInfo"]/map'


@dataclass
class Project:
    name: str
    path: str
    code: str
    timestamp: int


def discover_projects():
    """Return recent projects from all IDEs, from newest to oldest."""
    merged: dict[tuple[str, str], Project] = {}
    for xml_path in glob.iglob(_CONFIG_GLOB):
        for project in _parse(xml_path):
            key = (project.code, os.path.normcase(project.path))
            current = merged.get(key)
            if current is None or project.timestamp > current.timestamp:
                merged[key] = project

    projects = [p for p in merged.values() if os.path.isdir(p.path)]
    projects.sort(key=lambda p: p.timestamp, reverse=True)
    return projects


def _parse(xml_path):
    try:
        root = ElementTree.parse(xml_path).getroot()
    except (OSError, ElementTree.ParseError):
        return  # An unreadable file should not cause the query to fail.

    entries = root.find(_MAP_PATH)
    if entries is None:
        return

    for entry in entries.findall("entry"):
        raw_path = entry.get("key")
        meta = entry.find("value/RecentProjectMetaInfo")
        if not raw_path or meta is None:
            continue

        code = _product_code(meta)
        if not code:
            continue

        path = _expand(raw_path)
        name = os.path.basename(path)
        if not name:
            continue

        timestamp = max(
            _option_int(meta, "activationTimestamp"),
            _option_int(meta, "projectOpenTimestamp"),
        )
        yield Project(name=name, path=path, code=code, timestamp=timestamp)


def _product_code(meta) -> str | None:
    code = _option(meta, "productionCode")
    if code:
        return code
    # Older entries lack productionCode, but the build contains it ("PY-261.26222.68").
    build = _option(meta, "build") or ""
    return build.split("-", 1)[0] if "-" in build else None


def _option(meta, name) -> str | None:
    element = meta.find('option[@name="%s"]' % name)
    return element.get("value") if element is not None else None


def _option_int(meta, name):
    try:
        return int(_option(meta, name) or 0)
    except ValueError:
        return 0


def _expand(raw_path: str) -> str:
    """Resolve the $USER_HOME$ macro and normalize separators for Windows."""
    return os.path.normpath(raw_path.replace("$USER_HOME$", os.path.expanduser("~")))
