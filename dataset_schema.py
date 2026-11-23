"""Shared dataset record and evidence helpers used by the existing root scripts."""

from __future__ import annotations

import re

FIELDS = (
    "dataset_id", "repository", "title", "url", "description", "licence", "doi",
    "modalities", "species", "population", "n_participants", "age_min", "age_max",
    "longitudinal", "tasks", "resting_state", "processed_data_available",
    "field_strength", "paper_doi",
)


def stated(value, source):
    if value is None or value == "" or value == []:
        return {"value": None, "status": "not_stated", "source": None}
    return {"value": value, "status": "stated", "source": source}


def blank_fields():
    return {key: stated(None, None) for key in FIELDS}


def _source(label, value):
    if isinstance(value, (list, tuple)):
        rendered = ", ".join(str(item) for item in value)
    else:
        rendered = str(value)
    return f"OpenNeuro {label}: {rendered}"


def normalize(raw):
    snapshot = raw.get("latestSnapshot") or {}
    desc = snapshot.get("description") or {}
    summary = snapshot.get("summary") or {}
    dataset = snapshot.get("dataset") or {}
    dataset_metadata = dataset.get("metadata") or {}
    dataset_id = raw.get("id", "")
    title = desc.get("Name") or dataset.get("name") or raw.get("name") or dataset_id

    raw_modalities = list(summary.get("modalities") or [])
    raw_modalities.extend(summary.get("secondaryModalities") or [])
    def normalized_modality(value):
        value = str(value).lower()
        if value in {"mri_bold", "mri_func"} or value.startswith("mri_bold_"):
            return "fmri"
        if value.startswith("mri_"):
            return "mri"
        return value

    modalities = list(dict.fromkeys(normalized_modality(value) for value in raw_modalities if value))
    tasks = [str(value) for value in (summary.get("tasks") or []) if value]
    subjects = summary.get("subjectCount", summary.get("subjects"))
    n_participants = len(subjects) if isinstance(subjects, list) else subjects
    age_range = summary.get("ageRange") or {}
    ages = []
    for value in (age_range.get("min"), age_range.get("max")):
        try:
            if value is not None:
                ages.append(float(value))
        except (TypeError, ValueError):
            pass

    longitudinal_raw = dataset_metadata.get("studyLongitudinal")
    longitudinal = None
    if isinstance(longitudinal_raw, str):
        if longitudinal_raw.lower() == "longitudinal":
            longitudinal = True
        elif longitudinal_raw.lower() in {"cross-sectional", "cross sectional", "not longitudinal"}:
            longitudinal = False
    elif isinstance(longitudinal_raw, bool):
        longitudinal = longitudinal_raw

    processed = summary.get("dataProcessed")
    if processed is None:
        processed = dataset_metadata.get("dataProcessed")
    population_raw = dataset_metadata.get("dxStatus")
    population = None
    if population_raw:
        lower_population = str(population_raw).lower()
        if "healthy" in lower_population or "control" in lower_population:
            population = "healthy"
        elif "patient" in lower_population or "clinical" in lower_population or "diagnos" in lower_population:
            population = "clinical"
        else:
            population = str(population_raw)

    paper_doi = dataset_metadata.get("openneuroPaperDOI") or dataset_metadata.get("associatedPaperDOI")
    resting_source = next((task for task in tasks if re.search(r"\b(rest|resting)\b", task, re.I)), None)
    description_values = []
    metadata_pairs = [
        ("Study design", dataset_metadata.get("studyDesign")),
        ("Study domain", dataset_metadata.get("studyDomain")),
        ("Dataset type", desc.get("DatasetType")),
        ("Diagnosis status", population_raw),
        ("Species", dataset_metadata.get("species")),
        ("Tasks", tasks),
        ("Modalities", modalities),
        ("Participant count", n_participants),
        ("Participant age range", f"{min(ages):g}-{max(ages):g} years" if ages else None),
        ("Processed data", processed),
        ("Longitudinal status", longitudinal_raw),
        ("Trial count", dataset_metadata.get("trialCount")),
    ]
    for label, value in metadata_pairs:
        if value is not None and value != []:
            description_values.append(f"{label}: {value if isinstance(value, str) else ', '.join(map(str, value)) if isinstance(value, list) else value}")
    for key in ("BIDSVersion", "Authors", "Acknowledgements", "HowToAcknowledge", "Funding", "ReferencesAndLinks"):
        value = desc.get(key)
        if value:
            rendered = "; ".join(map(str, value)) if isinstance(value, (list, tuple)) else str(value)
            description_values.append(f"{key}: {rendered}")
    description = "\n".join(description_values)

    fields = blank_fields()
    dataset_url = f"https://openneuro.org/datasets/{dataset_id}"
    for key, value in (
        ("dataset_id", dataset_id), ("repository", "OpenNeuro"), ("title", title),
        ("url", dataset_url), ("description", description),
        ("licence", desc.get("License")), ("doi", desc.get("DatasetDOI")),
        ("modalities", modalities or None),
        ("species", dataset_metadata.get("species")),
        ("population", population), ("n_participants", n_participants),
        ("age_min", min(ages) if ages else None), ("age_max", max(ages) if ages else None),
        ("longitudinal", longitudinal), ("tasks", tasks or None),
        ("resting_state", True if resting_source else None),
        ("processed_data_available", processed),
        ("paper_doi", paper_doi),
    ):
        label = f"snapshot.{key}"
        value_source = _source(label, value) if value is not None and value != [] else None
        if key == "modalities" and raw_modalities:
            value_source = _source("summary modalities", raw_modalities)
        fields[key] = stated(value, value_source)
    if ages:
        age_source = _source("summary subject age range", f"{min(ages):g}-{max(ages):g} years")
        fields["age_min"]["source"] = age_source
        fields["age_max"]["source"] = age_source
    if raw_modalities:
        fields["modalities"]["source"] = _source("summary modalities", raw_modalities)
    if population_raw:
        fields["population"]["source"] = _source("dataset.metadata.dxStatus", population_raw)
    if longitudinal_raw is not None:
        fields["longitudinal"]["source"] = _source("dataset.metadata.studyLongitudinal", longitudinal_raw)
    if processed is not None:
        processed_label = "summary.dataProcessed" if summary.get("dataProcessed") is not None else "dataset.metadata.dataProcessed"
        fields["processed_data_available"]["source"] = _source(processed_label, processed)
    if resting_source:
        fields["resting_state"]["source"] = _source("summary.tasks", resting_source)

    return {
        "dataset_id": dataset_id,
        "repository": "OpenNeuro",
        "title": title,
        "url": dataset_url,
        "description": description,
        "metadata_text": description,
        "licence": desc.get("License"),
        "doi": desc.get("DatasetDOI"),
        "fields": fields,
        "metadata": {
            "snapshot_tag": snapshot.get("tag"),
            "snapshot_created": snapshot.get("created"),
            "publish_date": raw.get("publishDate"),
            "dataset_metadata": dataset_metadata,
            "summary": summary,
            "dataset_type": desc.get("DatasetType"),
            "senior_author": desc.get("SeniorAuthor"),
            "size_bytes": snapshot.get("size"),
        },
    }


def is_mri_dataset(dataset):
    values = [str(value).lower() for value in dataset["fields"]["modalities"]["value"] or []]
    return any(value in {"mri", "fmri", "bold", "anat", "dwi", "dti"} for value in values)
