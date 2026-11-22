import json, os, time
from typing import Literal
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from textutil import squash

load_dotenv()
client = OpenAI(base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                timeout=120, max_retries=1)
MODEL = os.getenv("QUERY_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")


class Cue(BaseModel):
    cue_type: Literal["tone", "light", "white_noise", "odour", "other_cue", "none", "unclear"]
    source: str | None


PROMPT = """Read the methods of a rodent fear conditioning paper.
Question: which cue is paired with the foot shock during conditioning?
- "tone", "light", "white_noise", "odour" or "other_cue" if a cue is paired with shocks.
- "none" if foot shocks are given with no cue (shock only, or context only).
- "unclear" if the text does not say.
Copy one sentence from the text as "source". Never guess.

METHODS TEXT:
"""


def ask(text):
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT + text}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": "cue", "schema": Cue.model_json_schema()}},
    )
    return Cue.model_validate_json(r.choices[0].message.content)


def load(path):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


papers = {p["pmcid"]: p for p in json.load(open("papers.json", encoding="utf-8"))}
clean = load("clean_extractions.json")
out = load("cue_types.json")

for pmcid, f in clean.items():
    if pmcid in out:
        continue
    if f["n_pairings"]["value"] is None and f["tone_duration_s"]["value"] is None:
        continue                       # nothing to check for this paper
    text = papers[pmcid]["methods_text"]
    try:
        cue = ask(text).model_dump()
    except Exception as e:
        print("failed", pmcid, str(e)[:100])
        continue
    if cue["source"] and squash(cue["source"]) not in squash(text):
        cue = {"cue_type": "unclear", "source": None}     # same rule: no real quote, no value
    out[pmcid] = cue
    json.dump(out, open("cue_types.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(pmcid, cue["cue_type"])
    time.sleep(5)