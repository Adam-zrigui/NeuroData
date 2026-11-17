import json, time
import os
import traceback
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from google.genai import types
load_dotenv()
from google.genai import types
client = genai.Client(http_options=types.HttpOptions(timeout=120 * 1000))
out = json.load(open("extractions.json", encoding="utf-8")) if os.path.exists("extractions.json") else {}

PROMPT = """You extract parameters from the methods section of a rodent fear conditioning paper.
Rules:
- Report only what the text states. If a parameter is not stated, set value and source to null.
- "source" must be one sentence copied exactly from the text.
- Never infer or guess.
- Report a number only if the text states it directly. Do not count or calculate it.

METHODS TEXT:
"""


class Field(BaseModel):
    value: str | None
    source: str | None
class Extraction(BaseModel):
    species: Field
    strain: Field
    shock_intensity_ma: Field
    n_pairings: Field
    tone_duration_s: Field
    apparatus: Field
def extract_parameters(methods_text: str) -> dict:
    print("sending", len(methods_text), "chars...")
    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=PROMPT + methods_text,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": Extraction.model_json_schema(),
        },
    )
    print("got response")
    return Extraction.model_validate_json(interaction.output_text).model_dump()
records = json.load(open("papers.json"))
            
out = json.load(open("extractions.json", encoding="utf-8")) if os.path.exists("extractions.json") else {}


for rec in records:
    if rec["pmcid"] in out:
        continue                      # already done: skip
    try:
        out[rec["pmcid"]] = extract_parameters(rec["methods_text"])
    except Exception as e:
        print("failed", rec["pmcid"], e)
        continue
    json.dump(out, open("extractions.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    time.sleep(5)