"""Turn a dataset request into visible, editable search filters."""

from __future__ import annotations

import json
import os
import re
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()


class Filters(BaseModel):
    modalities: list[str] = Field(default_factory=list)
    species: str | None = None
    population: str | None = None
    min_participants: int | None = None
    min_age: float | None = None
    max_age: float | None = None
    tasks: list[str] = Field(default_factory=list)
    longitudinal: bool | None = None
    resting_state: bool | None = None
    processed_data_available: bool | None = None
    field_strength: str | None = None


class ParsedQuery(BaseModel):
    semantic_query: str
    filters: Filters


def parse_rules(text: str) -> ParsedQuery:
    lower = text.lower()
    modalities = []
    for name, pattern in (
        ("fmri", r"\bf\s?-?mri\b|functional mri|\bbold\b"),
        ("mri", r"\bmri\b|structural mri|diffusion mri"),
    ):
        if re.search(pattern, lower) and name not in modalities:
            modalities.append(name)
    species = next((name for name in ("human", "mouse", "rat", "macaque")
                    if re.search(rf"\b{name}s?\b", lower)), None)
    min_age = None
    match = re.search(r"(?:over|older than|at least|age\s*>=?)\s*(\d+(?:\.\d+)?)", lower)
    if match:
        min_age = float(match.group(1))
    max_age = None
    match = re.search(r"(?:under|younger than|up to|age\s*<=?)\s*(\d+(?:\.\d+)?)", lower)
    if match:
        max_age = float(match.group(1))
    min_participants = None
    match = re.search(r"(?:at least|more than|over|>=?)\s*(\d+)\s*(?:participants|subjects|people)", lower)
    if match:
        min_participants = int(match.group(1))
    longitudinal = True if "longitudinal" in lower else None
    resting_state = True if "resting state" in lower or "resting-state" in lower else None
    processed = True if any(term in lower for term in ("preprocessed", "pre-processed", "derivatives")) else None
    population = None
    if re.search(r"\b(healthy|control)s?\b", lower):
        population = "healthy"
    elif re.search(r"\b(patient|clinical|diagnos(?:is|ed))\b", lower):
        population = "clinical"
    elif "mixed population" in lower:
        population = "mixed"
    field_strength = None
    if match := re.search(r"\b(\d+(?:\.\d+)?\s*t)\b", lower):
        field_strength = match.group(1).replace(" ", "").upper()
    tasks = []
    if re.search(r"\bmotor task\b", lower):
        tasks.append("motor")
    if re.search(r"\bvisual (?:task|stimuli|stimulation)\b", lower):
        tasks.append("visual")
    if re.search(r"\bworking memory\b", lower):
        tasks.append("working memory")
    return ParsedQuery(
        semantic_query=text,
        filters=Filters(
            modalities=modalities, species=species, min_age=min_age, max_age=max_age,
            population=population, min_participants=min_participants, tasks=tasks, longitudinal=longitudinal,
            resting_state=resting_state, processed_data_available=processed,
            field_strength=field_strength,
        ),
    )


def parse_query(text: str) -> ParsedQuery:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return parse_rules(text)
    try:
        client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=api_key, timeout=45, max_retries=1,
        )
        response = client.chat.completions.create(
            model=os.getenv("QUERY_MODEL", os.getenv("LLM_MODEL", "google/gemma-4-26b-a4b-it:free")),
            messages=[
                {"role": "system", "content": (
                    "Convert a researcher's public neuroscience dataset request into search filters. "
                    "Only fill requirements stated in the request; otherwise use null or an empty list. "
                    "Keep the full original meaning in semantic_query. Modalities use names such as mri/fmri."
                )},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_schema", "json_schema": {
                "name": "parsed_dataset_query", "schema": ParsedQuery.model_json_schema()
            }},
        )
        content = response.choices[0].message.content
        if not content:
            return parse_rules(text)
        return ParsedQuery.model_validate(json.loads(content))
    except Exception:
        return parse_rules(text)


if __name__ == "__main__":
    import sys

    print(parse_query(" ".join(sys.argv[1:])).model_dump_json(indent=2))
