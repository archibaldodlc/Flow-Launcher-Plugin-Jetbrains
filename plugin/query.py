# -*- coding: utf-8 -*-
"""Query grammar: `jb [ide-alias] text`."""


def parse(text, ides):
    """Return (IDE or None, [terms]).

    The first token is consumed as an IDE filter only if it exactly matches an
    alias or the IDE name. Requiring an exact match (rather than a prefix) lets
    `jb pyth` remain a text search instead of a partially typed filter.
    """
    terms = (text or "").split()
    if not terms:
        return None, []

    head = terms[0].lower()
    for ide in sorted(ides.values(), key=lambda item: item.code):
        if head in ide.aliases:
            return ide, terms[1:]

    return None, terms
