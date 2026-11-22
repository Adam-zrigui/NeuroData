import re

WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
         "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def numbers(s):
    """All numbers in a string: '0.4 or 0.9' -> [0.4, 0.9]."""
    if s is None:
        return None
    return [float(x) for x in re.findall(r"\d*\.?\d+", s)]


def to_int(s):
    """'five' -> 5, '10' -> 10, anything else -> None (unknown)."""
    if s is None:
        return None
    s = s.strip().lower()
    if s in WORDS:
        return WORDS[s]
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None

MOUSE = r"\b(mouse|mice)\b|mus musculus|c57bl|balb|\bcd-?1\b|\bdba\b|\b129s?\d*"
RAT = r"\b(rat|rats)\b|rattus|wistar|sprague|long[- ]?evans|fischer|\bf344\b|lister"


def species_norm(species, strain=None):
    """mouse / rat / both / other, using species and strain text. None if both empty."""
    s = " ".join(x for x in (species, strain) if x).lower()
    if not s:
        return None
    mouse = re.search(MOUSE, s)
    rat = re.search(RAT, s)
    if mouse and rat:
        return "both"
    if mouse:
        return "mouse"
    if rat:
        return "rat"
    return "other"


if __name__ == "__main__":
    assert species_norm("Human") == "other"
    assert species_norm("C57BL/6N", "C57BL/6N") == "mouse"
    assert species_norm("Mus musculus", "B6.129(Cg)-Cntnap2tm1Pele/J") == "mouse"
    assert species_norm("Male Fischer F344/NSlc rats") == "rat"
    assert species_norm("mice and rats") == "both"
    assert species_norm(None, None) is None