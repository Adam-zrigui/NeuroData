def squash(s):
    return " ".join(s.split())


def verify(extraction, text):
    t = squash(text)
    for name, f in extraction.items():
        if f["source"] and squash(f["source"]) not in t:
            print("unverified, dropped:", name)
            extraction[name] = {"value": None, "source": None}
    return extraction