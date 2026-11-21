import json, os, time
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()
client = OpenAI(base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                timeout=90, max_retries=1)
MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
LIMIT = 100          # stop after this many papers, to test first

PROMPT = """You extract parameters from the methods section of a rodent fear conditioning paper.
Rules:
- Report only what the text states. If a parameter is not stated, set value and source to null.
- "source" must be one sentence copied exactly from the text.
- Never infer or guess.
- Copy values exactly as written, including units (for example "0.8 mA").
- Report a number only if the text states it directly. Do not count or calculate it.
- Copy exactly one sentence. Never join sentences.
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


def extract_parameters(methods_text):
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT + methods_text}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": "extraction",
                                         "schema": Extraction.model_json_schema()}},
    )
    content = r.choices[0].message.content
    if not content:
        raise RuntimeError("empty response")
    return Extraction.model_validate_json(content).model_dump()


def extract_patiently(text, tries=5):
    for i in range(tries):
        try:
            return extract_parameters(text)
        except Exception as e:
            if "429" not in str(e) and "503" not in str(e):
                raise
            wait = 60 * (i + 1)
            print(f"busy, waiting {wait}s")
            time.sleep(wait)
    raise RuntimeError("gave up")


def load(path):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


records = json.load(open("papers.json", encoding="utf-8"))
out = load("extractions_qwen.json")
done = set(load("extractions.json")) | set(out)

processed = 0
failures = 0
for rec in records:
    if rec["pmcid"] in done:
        continue
    if processed >= LIMIT:
        break
    t0 = time.time()
    try:
        out[rec["pmcid"]] = extract_patiently(rec["methods_text"])
        failures = 0
    except Exception as e:
        print("failed", rec["pmcid"], e)
        failures += 1
        if failures >= 3:
            print("3 failures in a row, stopping")
            break
        continue
    processed += 1
    json.dump(out, open("extractions_qwen.json", "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)
    print(f"{rec['pmcid']} done in {time.time() - t0:.0f}s")
    time.sleep(5)
    