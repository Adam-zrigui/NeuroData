import os, sys
from typing import Literal
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
import re
from normalise import to_int
load_dotenv()
client = OpenAI(base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                timeout=60, max_retries=0)
MODEL = os.getenv("QUERY_MODEL", "google/gemma-4-26b-a4b-it:free")


class Query(BaseModel):
    species: Literal["mouse", "rat"] | None = Field(
        description="mouse or rat. Map 'mice' to mouse and 'rats' to rat. null if not mentioned.")
    shock_ma: float | None = Field(
        description="Shock intensity in milliamps. Convert microamps to mA. null if not mentioned.")
    n_pairings: int | None = Field(
        description="Number of tone-shock pairings as an integer ('five' -> 5). null if not mentioned.")
    tone_duration_s: float | None = Field(
        description="Tone duration in seconds. null if not mentioned.")


PROMPT = """You turn a researcher's request about rodent fear conditioning experiments into search filters.
Rules:
- Fill a field only if the request states it. Otherwise use null.
- Never guess and never fill in typical values.
- Convert units: shock in milliamps (500 microamps = 0.5), tone in seconds.
- Number words become integers.

REQUEST:
"""
def parse_rules(text: str) -> Query:
    t = text.lower()

    species = None
    if re.search(r"\b(mouse|mice)\b", t):
        species = "mouse"
    elif re.search(r"\b(rat|rats)\b", t):
        species = "rat"

    shock = None
    m = re.search(r"(\d*\.?\d+)\s*(?:ma|milliamps?)\b", t)
    if m:
        shock = float(m.group(1))
    else:
        m = re.search(r"(\d*\.?\d+)\s*(?:µa|μa|ua|microamps?)\b", t)
        if m:
            shock = float(m.group(1)) / 1000

    pairings = None
    m = re.search(r"\b(\w+)\s+(?:tone[- ]shock\s+)?pairings?\b", t)
    if m:
        pairings = to_int(m.group(1))

    tone = None
    m = re.search(r"(\d*\.?\d+)[- ]?(?:s|sec|secs|seconds?)\b[- ]*tones?\b", t)
    if m:
        tone = float(m.group(1))

    return Query(species=species, shock_ma=shock,
                 n_pairings=pairings, tone_duration_s=tone)

def parse(text: str) -> Query:
    """LLM first, rules as the fallback."""
    try:
        return parse_query(text)
    except Exception:
        print("(LLM unavailable, using rule-based parser)")
        return parse_rules(text)

def parse_query(text: str) -> Query:
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT + text}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": "query",
                                         "schema": Query.model_json_schema()}},
    )
    content = r.choices[0].message.content
    if not content:
        raise RuntimeError("empty response")
    return Query.model_validate_json(content)


if __name__ == "__main__":
    text = " ".join(sys.argv[1:])
    print("rules:", parse_rules(text).model_dump())
    try:
        print("llm:  ", parse_query(text).model_dump())
    except Exception as e:
        print("llm failed:", getattr(e, "body", None) or str(e)[:200])