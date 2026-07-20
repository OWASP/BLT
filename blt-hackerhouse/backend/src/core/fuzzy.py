"""Pure Python fuzzy matching — replaces rapidfuzz for Cloudflare Workers.

Implements Levenshtein distance and token-set Jaccard ratio using
only the standard library (no C extensions required).
"""

from __future__ import annotations


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein (edit) distance between *s1* and *s2*.

    Returns the minimum number of single-character edits (insertions,
    deletions, substitutions) required to change *s1* into *s2*.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if not s2:
        return len(s1)

    prev_row: list[int] = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1, start=1):
        curr_row = [i]
        for j, c2 in enumerate(s2, start=1):
            insertions = prev_row[j] + 1
            deletions = curr_row[j - 1] + 1
            substitutions = prev_row[j - 1] + (0 if c1 == c2 else 1)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


def _char_trigrams(s: str) -> set[str]:
    """Return the set of 3-character substrings of *s*."""
    if len(s) < 3:
        return {s}
    return {s[i:i + 3] for i in range(len(s) - 2)}


def token_set_jaccard(s1: str, s2: str) -> float:
    """Compute Jaccard similarity based on character trigrams.

    Returns a float in [0.0, 1.0] where higher values indicate
    greater similarity. Roughly approximates rapidfuzz's
    ``token_set_ratio / 100`` for identity-resolution purposes.
    """
    t1 = _char_trigrams(s1.lower())
    t2 = _char_trigrams(s2.lower())

    if not t1 and not t2:
        return 1.0
    if not t1 or not t2:
        return 0.0

    intersection = len(t1 & t2)
    union = len(t1 | t2)
    return intersection / union
