import copy
import json
import re
from functools import lru_cache

from django.conf import settings


DEMO_CACHE_PATH = settings.BASE_DIR / "demo_cache" / "demo_results.json"


def _clean_scalar(value, lowercase=False):
    text = str(value or "").replace("\r", "\n").strip()
    text = re.sub(r"\s+", " ", text)
    return text.lower() if lowercase else text


def _clean_lines(value, split_semicolon=False, uppercase=False):
    text = str(value or "").replace("\r", "\n").replace("；", ";").strip()
    if split_semicolon:
        text = text.replace(";", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    normalized = "\n".join(lines)
    return normalized.upper() if uppercase else normalized


def _clean_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = re.split(r"[,;\n]+", str(value))
    items = [str(item).strip().lower() for item in raw_items if str(item).strip()]
    return sorted(items)


@lru_cache(maxsize=1)
def _load_entries():
    if not DEMO_CACHE_PATH.exists():
        return []
    with DEMO_CACHE_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload.get("entries", [])


def _cached_response(entry):
    response = copy.deepcopy(entry.get("response", {}))
    response["demo_cache_hit"] = True
    response["demo_cache_id"] = entry.get("id", "")
    response["demo_cache_title"] = entry.get("title", "")
    return response


def _find_entry(section, request_match, normalizer):
    for entry in _load_entries():
        if entry.get("section") != section:
            continue
        if normalizer(entry.get("match", {})) == request_match:
            return _cached_response(entry)
    return None


def _normalize_prediction_match(raw):
    return {
        "task_type": _clean_scalar(raw.get("task_type"), lowercase=True),
        "drug_input": _clean_lines(raw.get("drug_input")),
        "protein_input": _clean_lines(raw.get("protein_input"), uppercase=True),
    }


def _normalize_dti_match(raw):
    return {
        "input1": _clean_lines(raw.get("input1"), split_semicolon=True, uppercase=True),
        "input2": _clean_lines(raw.get("input2"), split_semicolon=True),
        "age": _clean_int(raw.get("age")),
        "sex": _clean_scalar(raw.get("sex"), lowercase=True),
        "disease_history": _clean_list(raw.get("disease_history")),
        "allergy_history": _clean_list(raw.get("allergy_history")),
        "insurance_preference": _clean_scalar(raw.get("insurance_preference"), lowercase=True),
    }


def _normalize_personalized_match(raw):
    disease = raw.get("disease") or raw.get("disease_type") or raw.get("illness")
    return {
        "disease": _clean_scalar(disease, lowercase=True),
        "age": _clean_int(raw.get("age")),
        "gender": _clean_scalar(raw.get("gender", "Any"), lowercase=True),
    }


def _normalize_structure_match(raw):
    return {
        "kind": _clean_scalar(raw.get("kind"), lowercase=True),
        "selectOp": _clean_scalar(raw.get("selectOp")),
        "inputText": _clean_scalar(raw.get("inputText"), lowercase=True),
    }


def get_prediction_model_demo_result(task_type, drug_input, protein_input):
    request_match = _normalize_prediction_match(
        {
            "task_type": task_type,
            "drug_input": drug_input,
            "protein_input": protein_input,
        }
    )
    return _find_entry("prediction_models", request_match, _normalize_prediction_match)


def get_dti_recommendation_demo_result(payload):
    request_match = _normalize_dti_match(payload or {})
    return _find_entry("dti_recommendation", request_match, _normalize_dti_match)


def get_personalized_recommend_demo_result(disease, age, gender):
    request_match = _normalize_personalized_match(
        {
            "disease": disease,
            "age": age,
            "gender": gender,
        }
    )
    return _find_entry("personalized_recommend", request_match, _normalize_personalized_match)


def get_structure_query_demo_result(kind, select_op, input_text):
    request_match = _normalize_structure_match(
        {
            "kind": kind,
            "selectOp": select_op,
            "inputText": input_text,
        }
    )
    return _find_entry("structure_query", request_match, _normalize_structure_match)
