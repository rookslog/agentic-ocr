"""String normalization and n-gram helpers, local to the checker suite.

``eval/lib/normalize`` is *element*-oriented (it turns YAML ground truth into
:class:`~eval.lib.normalize.NormalizedElement` records); it has no string-level
normalizer. Text-fidelity n-gram containment (PLAN §5 anti-hallucination tripwire:
"n-gram containment of output against GT/source") needs string-level normalization,
so it lives here rather than as a behavioural change to the ported ``eval/lib``
(which the goal packet forbids editing).

The normalizer is intentionally aggressive about *markup* and gentle about
*content*: it casefolds, NFC-normalizes, and strips everything that is not a
Unicode letter or *decimal* digit to whitespace — so footnote markers (``¹``,
``*``, ``†``), punctuation, and superscripts vanish, while Greek/German/French
letters and ordinary numerals (``1922``) survive. Superscript digits like ``¹`` are
``isnumeric`` but not ``isdecimal``, so they are correctly treated as markup, not
content. That choice is what isolates the negative controls: dropping a footnote
*marker* leaves the normalized token stream unchanged (so text-fidelity ignores
it), while corrupting *letters* changes tokens (so text-fidelity catches it).
"""

from __future__ import annotations

import unicodedata
from collections import Counter


def normalize_text(text: str) -> str:
    """Casefold + NFC + reduce non-content runs to single spaces.

    Unicode letters (any script) and *decimal* digits are preserved; everything
    else (punctuation, footnote markers, superscripts, symbols) becomes a space.
    Returns a single space-separated string with no leading/trailing space.
    """
    nfc = unicodedata.normalize("NFC", text)
    folded = nfc.casefold()
    out: list[str] = []
    prev_space = True  # collapse leading space
    for ch in folded:
        if ch.isalpha() or ch.isdecimal():
            out.append(ch)
            prev_space = False
        elif not prev_space:
            out.append(" ")
            prev_space = True
    result = "".join(out)
    return result.rstrip()


def tokens(text: str) -> list[str]:
    """Normalized whitespace-delimited tokens of ``text``."""
    norm = normalize_text(text)
    return norm.split() if norm else []


def ngrams(items: list[str], n: int) -> list[tuple[str, ...]]:
    """Contiguous n-grams of ``items``; empty when ``len(items) < n``."""
    if n <= 0 or len(items) < n:
        return []
    return [tuple(items[i : i + n]) for i in range(len(items) - n + 1)]


def ngram_multiset(text: str, n: int) -> Counter[tuple[str, ...]]:
    """Multiset of word n-grams of ``text`` after normalization."""
    return Counter(ngrams(tokens(text), n))


def containment(reference: Counter, candidate: Counter) -> float:
    """Fraction of the reference multiset contained in the candidate multiset.

    ``sum_g min(ref[g], cand[g]) / sum_g ref[g]`` — multiset containment of
    ``reference`` within ``candidate``. Returns 1.0 when ``reference`` is empty
    (nothing to contain is vacuously contained).
    """
    total = sum(reference.values())
    if total == 0:
        return 1.0
    covered = sum(min(count, candidate.get(gram, 0)) for gram, count in reference.items())
    return covered / total
