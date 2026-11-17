import re

WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
         "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

def numbers(s):
    if s is None:
        return None
    return [float(x) for x in re.findall(r"\d+\.?\d*", s)]

def to_int(s):
    if s is None:
        return None
    s = s.strip().lower()
    if s in WORDS:
        return WORDS[s]
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None