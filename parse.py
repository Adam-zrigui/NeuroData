import json, pathlib, re, statistics
from lxml import etree
import traceback
XLINK_NS = "{http://www.w3.org/1999/xlink}href"
ALI = {"ali": "http://www.niso.org/schemas/ali/1.0/"}
def text_of(el):
    return " ".join("".join(el.itertext()).split())
def sec_title(sec):
    t = sec.find("title")
    return norm(text_of(t)) if t is not None else ""
def norm(title):
    # lowercase, strip leading numbers/dots/spaces
    return re.sub(r"^[\d\.\s]+", "", title.lower())
    ...

def is_methods(sec):
    ...   # use sec-type OR norm(title) containing "method"
    return "method" in (sec.get("sec-type") or "") or "method" in sec_title(sec)

def is_results(sec):
    return "results" in (sec.get("sec-type") or "") or "result" in sec_title(sec)
    ...
def get_license(tree):
    licenses = tree.xpath("//front//permissions//license")
    for lic in licenses:
        url = lic.get(XLINK_NS)
        if url:
            return url
        link = lic.find(".//ext-link")
        if link is not None and link.get(XLINK_NS):
            return link.get(XLINK_NS)
        ref = lic.xpath(".//ali:license_ref", namespaces=ALI)
        if ref and ref[0].text and ref[0].text.strip():
            return ref[0].text.strip()
        match = re.search(
            r"https?://creativecommons\.org/licenses/[^\s<>\"']+",
            text_of(lic),
            re.IGNORECASE,
        )
        if match:
            return match.group(0).rstrip(".,;:)]}")
    return None
def parse(path):
    tree = etree.parse(str(path))
    t = tree.xpath("//front//article-title")
    title = text_of(t[0]) if t else None
    secs = tree.xpath("//body//sec")
    matched = [s for s in secs if is_methods(s)]
    methods = [s for s in matched if not any(a in matched for a in s.iterancestors())]  # only top-level methods
    has_results = any(is_results(s) for s in secs)
    license = get_license(tree)
    return {
        "pmcid": path.stem,
        "title": title,        # //front//article-title via text_of
        "licence": license or None,      # or None
        "has_results": has_results,
        "methods_text": " ".join(text_of(s) for s in methods) or None,
    }
records = []
for f in pathlib.Path("papers").glob("*.xml"):
    try :
        records.append(parse(f))
    except Exception as e:
        print(f"Error parsing {f.name}: {e}")    
        traceback.print_exc()
        break
eligible = [r for r in records if r["methods_text"] and r["has_results"]]
missing = [r for r in eligible if r["licence"] is None]
kept = [r for r in eligible if r["licence"] is not None]
dropped = [r for r in records if r not in kept]
json.dump(kept, open("papers.json", "w"), indent=1)
print(f"Kept {len(kept)} records, dropped {len(dropped)} records")
if kept:
    print(f"Median methods_text length: {statistics.median(len(r['methods_text']) for r in kept):.0f} characters")
else:
    print("Median methods_text length: N/A (no records kept)")
print(f"Missing license: {len(missing)} records of {len(eligible)} eligible records have no license")
if missing:
    print("Missing license PMCIDs: " + ", ".join(r["pmcid"] for r in missing))
for r in dropped[:5]:
    print(f"Dropped {r['pmcid']}: {r['title']}")