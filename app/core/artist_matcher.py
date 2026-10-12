"""Shared artist-name normalization and credit-splitting, used by cluster
cleanup and the Christian artists module so there's exactly one
implementation of "does this artist credit match that list entry" in the
app. Ported from christian_tag.py's norm()/CREDIT_SPLIT (the version the
Christian artists spec's matching rules describe: NFKC, casefold, leading
"The ", "&" vs "and", and punctuation all ignored) - a strict superset of
cluster cleanup's previous, simpler normalization (lowercase + "&"/"+" ->
"and" + strip punctuation, no NFKC/casefold/"The"-stripping), so switching
cluster cleanup onto this can only gain matches, never lose one it had.
"""
import re
import unicodedata

CREDIT_SPLIT = re.compile(
    r"\s*(?:,|;|/|&|\+| x | and | feat\.? | ft\.? | featuring | with )\s*", re.I)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").casefold().strip().replace("&", "and")
    if s.startswith("the "):
        s = s[4:]
    s = re.sub(r"[^\w\s]", "", s)
    return " ".join(s.split())


def credit_keys(name: str) -> set[str]:
    """The full credit string, plus each individual name split out of it
    ("Elevation Worship & Maverick City Music" -> both the whole string and
    each half), all normalized. A credit matches a list entry if any key in
    this set is in the list."""
    keys = {norm(name)}
    keys.update(norm(p) for p in CREDIT_SPLIT.split(name or "") if p and p.strip())
    keys.discard("")
    return keys
