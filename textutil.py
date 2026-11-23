import re
from normalise import WORDS, numbers, to_int

COUNT_WORDS = {**WORDS, "once": 1, "twice": 2}

PAIR_CUE = re.compile(r"pair|tone|noise|cue|\bcs\b|conditioned stimul|light", re.I)


def supported(name, value, quote):
    """Is the number in the value written in the quote, and does it describe a cue pairing?"""
    if name == "n_pairings":
        n = to_int(value)
        if n is None:
            return True
        return float(n) in quote_numbers(quote) and bool(PAIR_CUE.search(quote))
    if name in ("shock_intensity_ma", "tone_duration_s"):
        return all(v in quote_numbers(quote) for v in (numbers(value) or []))
    return True
def quote_numbers(quote):
    found = {float(x) for x in re.findall(r"\d*\.?\d+", quote)}
    found |= {float(COUNT_WORDS[w]) for w in re.findall(r"[a-z]+", quote.lower())
              if w in COUNT_WORDS}
    return found

def verify(extraction, text, label=""):
    t = squash(text)
    for name, f in extraction.items():
        if f["value"] is None:
            continue
        reason = None
        if not f["source"] or squash(f["source"]) not in t:
            reason = "no valid quote"
        elif not supported(name, f["value"], f["source"]):
            reason = "value not supported by quote"
        if reason:
            print(f"dropped {label} {name} = {f['value']!r} ({reason}): {(f['source'] or '')[:160]}")
            extraction[name] = {"value": None, "source": None}
    return extraction



def squash(s):
    return " ".join(s.split())


