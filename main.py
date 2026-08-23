# -*- coding: utf-8 -*-

import os
import subprocess
import sys
from json import dumps

parent_folder_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(parent_folder_path)
sys.path.append(os.path.join(parent_folder_path, 'lib'))
sys.path.append(os.path.join(parent_folder_path, 'plugin'))

from flowlauncher import FlowLauncher

from plugin.ides import discover_ides
from plugin.matching import score_ide, score_project
from plugin.projects import discover_projects
from plugin.query import parse

PLUGIN_ICON = os.path.join(parent_folder_path, "Images", "app.png")

# Flow sorts by descending Score, so the order calculated here is translated
# into explicitly decreasing scores.
TOP_SCORE = 10000


class Jetbrains(FlowLauncher):
    """Opens recent projects and automatically detected JetBrains IDEs."""

    def query(self, param=''):
        projects = discover_projects()
        ides = discover_ides({project.code for project in projects})
        if not ides:
            return [_notice(
                "No JetBrains IDE was found",
                "Searched in Toolbox, Program Files, and %LOCALAPPDATA%\\Programs",
            )]

        ide_filter, terms = parse(param, ides)
        matched = _project_results(projects, ides, ide_filter, terms)
        launchers = _ide_results(ides, ide_filter, terms)

        # With a selected IDE and no search text, the IDE itself is requested.
        if ide_filter and not terms:
            ordered = launchers + matched
        else:
            ordered = matched + launchers

        if not ordered:
            return [_notice(
                "No results",
                "No project or IDE matches \"%s\"" % (param or "").strip(),
            )]

        for index, result in enumerate(ordered):
            result["Score"] = TOP_SCORE - index
        return ordered

    def context_menu(self, data):
        if not data:
            return []

        path = data[0]
        code = data[1] if len(data) > 1 else None
        results = [
            {
                "Title": "Open folder",
                "SubTitle": path,
                "IcoPath": PLUGIN_ICON,
                "JsonRPCAction": {"method": "open_folder", "parameters": [path]},
            },
            {
                "Title": "Copy path",
                "SubTitle": path,
                "IcoPath": PLUGIN_ICON,
                "JsonRPCAction": {"method": "copy_path", "parameters": [path]},
            },
        ]
        for ide in sorted(discover_ides().values(), key=lambda item: item.name):
            if ide.code == code:
                continue
            results.append({
                "Title": "Open in %s" % ide.name,
                "SubTitle": "%s  ·  %s" % (ide.label, path),
                "IcoPath": ide.icon,
                "JsonRPCAction": {"method": "open_project", "parameters": [ide.exe, path]},
            })
        return results

    # --- actions --------------------------------------------------------
    # Note: these must be instance methods. FlowLauncher.__init__ resolves the
    # JSON-RPC method with inspect.getmembers(..., inspect.ismethod), and a
    # staticmethod does not pass that filter, so making them static breaks them.

    def open_project(self, exe, path):
        _spawn([exe, path])

    def open_ide(self, exe):
        _spawn([exe])

    def open_folder(self, path):
        os.startfile(path)

    def copy_path(self, path):
        # flowlauncher 0.2.0 does not expose this API, so emit the JSON-RPC.
        print(dumps({"method": "Flow.Launcher.CopyToClipboard", "parameters": [path]}))


def _project_results(projects, ides, ide_filter, terms):
    scored = []
    for project in projects:
        ide = ides.get(project.code)
        if ide is None:
            continue  # The IDE is no longer installed, so it cannot be opened.
        if ide_filter is not None and ide.code != ide_filter.code:
            continue
        points = score_project(terms, project)
        if points is None:
            continue
        scored.append((points, project.timestamp, project, ide))

    scored.sort(key=lambda item: (-item[0], -item[1]))
    return [
        {
            "Title": project.name,
            "SubTitle": "%s  ·  %s" % (ide.label, project.path),
            "IcoPath": ide.icon,
            "ContextData": [project.path, ide.code],
            "JsonRPCAction": {"method": "open_project", "parameters": [ide.exe, project.path]},
        }
        for _, _, project, ide in scored
    ]


def _ide_results(ides, ide_filter, terms):
    candidates = [ide_filter] if ide_filter is not None else list(ides.values())

    scored = []
    for ide in candidates:
        points = score_ide(terms, ide)
        if points is None:
            continue
        scored.append((points, ide))

    scored.sort(key=lambda item: (-item[0], item[1].name))
    return [
        {
            "Title": "Open %s" % ide.name,
            "SubTitle": "%s  ·  new window, no project" % ide.label,
            "IcoPath": ide.icon,
            "JsonRPCAction": {"method": "open_ide", "parameters": [ide.exe]},
        }
        for _, ide in scored
    ]


def _notice(title, subtitle):
    return {"Title": title, "SubTitle": subtitle, "IcoPath": PLUGIN_ICON, "Score": TOP_SCORE}


def _spawn(args):
    # DETACHED_PROCESS detaches the IDE from the console Flow gives Python. It
    # is not combined with CREATE_NO_WINDOW because Windows ignores the latter.
    subprocess.Popen(args, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0), close_fds=True)


if __name__ == "__main__":
    Jetbrains()
