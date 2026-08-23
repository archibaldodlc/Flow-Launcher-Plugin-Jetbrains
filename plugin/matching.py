# -*- coding: utf-8 -*-
"""Minimal fuzzy scoring using only the standard library.

As with any launcher, the query must appear as a subsequence of the text, with
bonuses for contiguous runs and word boundaries. rapidfuzz/fuzzywuzzy is not
used to avoid adding binary dependencies to the plugin's `lib/` directory.
"""

_BOUNDARY = frozenset(" -_.\\/()[]{}@#")

# Weights: the project name takes precedence over its path.
NAME_WEIGHT = 3
PATH_WEIGHT = 1


def score(query, text):
    """Return a score (higher is better), or None if `query` does not match `text`."""
    if not query:
        return 0
    if not text:
        return None

    lowered = text.lower()
    total = 0
    position = 0
    previous = -2

    for char in query.lower():
        index = lowered.find(char, position)
        if index < 0:
            return None
        points = 4
        if index == 0:
            points += 12
        elif lowered[index - 1] in _BOUNDARY:
            points += 8
        if index == previous + 1:
            points += 8
        total += points
        previous = index
        position = index + 1

    if lowered.startswith(query.lower()):
        total += 20
    elif query.lower() in lowered:
        total += 12

    # A much longer text with the same match is a worse candidate.
    return total - min(len(lowered) // 8, 10)


def score_terms(terms, text):
    """Require all terms to match (AND) and return their sum, or None."""
    if not terms:
        return 0
    total = 0
    for term in terms:
        points = score(term, text)
        if points is None:
            return None
        total += points
    return total


def score_project(terms, project):
    """Match against the name, falling back to the full path."""
    if not terms:
        return 0
    by_name = score_terms(terms, project.name)
    if by_name is not None:
        return by_name * NAME_WEIGHT
    by_path = score_terms(terms, project.path)
    if by_path is not None:
        return by_path * PATH_WEIGHT
    return None


def score_ide(terms, ide):
    """Return the best score among the IDE name and its aliases."""
    if not terms:
        return 0
    candidates = [ide.name] + sorted(ide.aliases)
    best = None
    for candidate in candidates:
        points = score_terms(terms, candidate)
        if points is not None and (best is None or points > best):
            best = points
    return best
