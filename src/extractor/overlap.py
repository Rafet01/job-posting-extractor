"""Shared word sequences between texts, used to keep test postings out of prompts and dev data."""

import re

# Two different ads from the same employer share at most 27% of their five-word sequences
# in the test set (Apple 007/010, Assura 018/019). The same ad copied twice shares nearly all.
DUPLICATE_SHARE = 0.5


def word_ngrams(text: str, n: int = 5) -> set[tuple[str, ...]]:
    """All sequences of n consecutive lowercase words."""
    words = re.findall(r"\w+", text.lower())
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def shared_share(text: str, other: str, n: int = 5) -> float:
    """The share of the n-word sequences of text that also occur in other (0 to 1)."""
    grams = word_ngrams(text, n)
    if not grams:
        return 0.0
    return len(grams & word_ngrams(other, n)) / len(grams)
