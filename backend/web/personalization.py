import csv
import json
import re
from functools import lru_cache
from pathlib import Path


NEUTRAL_SCORE = 0.5
DEFAULT_REASON = (
    "The recommendation is primarily driven by the base DTI prediction because "
    "personalization metadata is limited for this drug."
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_TEMPLATE_DIR = BASE_DIR / "data_templates"

DISEASE_TAG_DICT_PATH = BASE_DIR / "disease_tag_dict.csv"
ALLERGY_TAG_DICT_PATH = BASE_DIR / "allergy_tag_dict.csv"
DRUG_METADATA_CSV_PATH = BASE_DIR / "drug_personalization_metadata.csv"
DRUG_METADATA_JSON_PATH = Path(__file__).resolve().parent / "drug_metadata.json"

DISEASE_TAG_TEMPLATE_PATH = DATA_TEMPLATE_DIR / "disease_tag_dict_template.csv"
ALLERGY_TAG_TEMPLATE_PATH = DATA_TEMPLATE_DIR / "allergy_tag_dict_template.csv"
DRUG_METADATA_TEMPLATE_PATH = DATA_TEMPLATE_DIR / "drug_personalization_metadata_template.csv"

_SEX_MAP = {
    "male": "male",
    "m": "male",
    "man": "male",
    "boy": "male",
    "男": "male",
    "女性": "female",
    "female": "female",
    "f": "female",
    "woman": "female",
    "girl": "female",
    "女": "female",
    "unknown": "unknown",
    "未知": "unknown",
    "all": "all",
    "any": "all",
    "不限": "all",
    "通用": "all",
}

_INSURANCE_PREFERENCE_MAP = {
    "yes": "yes",
    "true": "yes",
    "1": "yes",
    "care": "yes",
    "insured": "yes",
    "prefer insured drugs": "yes",
    "insurance focused": "yes",
    "yes_insurance": "yes",
    "采纳医保": "yes",
    "医保优先": "yes",
    "考虑医保": "yes",
    "是": "yes",
    "no": "no",
    "false": "no",
    "0": "no",
    "neutral": "no",
    "none": "no",
    "no insurance preference": "no",
    "不采纳医保": "no",
    "不考虑医保": "no",
    "否": "no",
}

_INSURANCE_STATUS_MAP = {
    "covered": "covered",
    "insured": "covered",
    "医保": "covered",
    "已医保": "covered",
    "partially_covered": "partially_covered",
    "partial": "partially_covered",
    "部分医保": "partially_covered",
    "not_covered": "not_covered",
    "not covered": "not_covered",
    "uninsured": "not_covered",
    "未医保": "not_covered",
    "自费": "not_covered",
    "unknown": "unknown",
    "": "unknown",
}

_SEX_CONSTRAINT_MAP = {
    "male": "male",
    "female": "female",
    "all": "all",
    "any": "all",
    "unknown": "unknown",
    "avoid_female": "avoid_female",
    "avoid_male": "avoid_male",
    "男": "male",
    "女": "female",
    "不限": "all",
    "未知": "unknown",
    "女性慎用": "avoid_female",
    "男性慎用": "avoid_male",
}

_DISEASE_LABELS = {
    "hypertension": "Hypertension",
    "diabetes": "Diabetes",
    "asthma": "Asthma",
    "arthritis": "Arthritis",
    "ulcer": "Ulcer",
    "renal_impairment": "Renal Impairment",
    "liver_impairment": "Liver Impairment",
    "bleeding": "Bleeding",
    "pregnancy": "Pregnancy",
    "heart_failure": "Heart Failure",
    "coronary_artery_disease": "Coronary Artery Disease",
    "copd": "COPD",
    "hyperkalemia": "Hyperkalemia",
    "angioedema": "Angioedema",
    "gastrointestinal_bleeding": "Gastrointestinal Bleeding",
    "anxiety": "Anxiety",
    "depression": "Depression",
    "hypothyroidism": "Hypothyroidism",
    "obesity": "Obesity",
}

_ALLERGY_LABELS = {
    "penicillin": "Penicillin",
    "nsaid": "NSAIDs",
    "sulfonamide": "Sulfonamides",
    "aspirin": "Aspirin",
    "cephalosporin": "Cephalosporins",
    "beta_lactam": "Beta-lactams",
    "ibuprofen": "Ibuprofen",
    "amoxicillin": "Amoxicillin",
    "macrolide": "Macrolides",
    "fluoroquinolone": "Fluoroquinolones",
    "tetracycline": "Tetracyclines",
    "clindamycin": "Clindamycin",
    "vancomycin": "Vancomycin",
    "carbapenem": "Carbapenems",
    "contrast_media": "Contrast Media",
    "aminoglycoside": "Aminoglycosides",
    "opioid": "Opioids",
    "local_anesthetic": "Local Anesthetics",
    "insulin": "Insulin",
}


def clamp_score(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return NEUTRAL_SCORE


def _split_items(value):
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[,;\n]+", str(value))
    return [str(item).strip() for item in raw_items if str(item).strip()]


def parse_tag_list(value):
    return [item.lower() for item in _split_items(value)]


def normalize_sex(value):
    if value is None:
        return None
    sex = str(value).strip().lower()
    if not sex:
        return None
    return _SEX_MAP.get(sex, sex)


def parse_age(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_insurance_preference(value):
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized:
        return None
    return _INSURANCE_PREFERENCE_MAP.get(normalized, normalized)


def _normalize_insurance_status(value):
    if value is None:
        return "unknown"
    normalized = str(value).strip().lower()
    return _INSURANCE_STATUS_MAP.get(normalized, normalized or "unknown")


def _normalize_sex_constraint(value):
    if value is None:
        return "unknown"
    normalized = str(value).strip().lower()
    return _SEX_CONSTRAINT_MAP.get(normalized, normalized or "unknown")


def _display_label(code, lookup):
    if code in lookup:
        return lookup[code]
    return str(code).replace("_", " ").title()


def _load_csv_rows(primary_path, fallback_path=None):
    for path in [primary_path, fallback_path]:
        if not path or not Path(path).exists():
            continue
        try:
            with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
                return list(csv.DictReader(file))
        except OSError:
            continue
    return []


def load_disease_tag_dict():
    options = []
    for row in _load_csv_rows(DISEASE_TAG_DICT_PATH, DISEASE_TAG_TEMPLATE_PATH):
        code = str(row.get("code", "")).strip().lower()
        if not code:
            continue
        options.append(
            {
                "code": code,
                "label": _display_label(code, _DISEASE_LABELS),
                "aliases": parse_tag_list(row.get("aliases")),
                "is_active": str(row.get("is_active", "true")).strip().lower() != "false",
                "sort_order": int(row.get("sort_order") or 9999),
            }
        )
    return sorted(options, key=lambda item: (item["sort_order"], item["label"]))


def load_allergy_tag_dict():
    options = []
    for row in _load_csv_rows(ALLERGY_TAG_DICT_PATH, ALLERGY_TAG_TEMPLATE_PATH):
        code = str(row.get("code", "")).strip().lower()
        if not code:
            continue
        options.append(
            {
                "code": code,
                "label": _display_label(code, _ALLERGY_LABELS),
                "aliases": parse_tag_list(row.get("aliases")),
                "is_active": str(row.get("is_active", "true")).strip().lower() != "false",
                "sort_order": int(row.get("sort_order") or 9999),
            }
        )
    return sorted(options, key=lambda item: (item["sort_order"], item["label"]))


@lru_cache(maxsize=1)
def _build_tag_lookup_maps():
    disease_lookup = {}
    for item in load_disease_tag_dict():
        disease_lookup[item["code"]] = item["code"]
        disease_lookup[item["label"].strip().lower()] = item["code"]
        for alias in item.get("aliases", []):
            disease_lookup[alias] = item["code"]

    allergy_lookup = {}
    for item in load_allergy_tag_dict():
        allergy_lookup[item["code"]] = item["code"]
        allergy_lookup[item["label"].strip().lower()] = item["code"]
        for alias in item.get("aliases", []):
            allergy_lookup[alias] = item["code"]

    for none_token in ("none", "无", "없음", "n/a", "na", "null"):
        disease_lookup[none_token] = "none"
        allergy_lookup[none_token] = "none"

    return disease_lookup, allergy_lookup


def _normalize_tag_codes(values, lookup):
    normalized = []
    for value in parse_tag_list(values):
        mapped = lookup.get(value, value)
        if mapped and mapped not in normalized:
            normalized.append(mapped)
    return normalized


def build_patient_profile(age=None, sex=None, disease_history=None, allergy_history=None, insurance_preference=None):
    disease_lookup, allergy_lookup = _build_tag_lookup_maps()
    disease_tags = [tag for tag in _normalize_tag_codes(disease_history, disease_lookup) if tag != "none"]
    allergy_tags = [tag for tag in _normalize_tag_codes(allergy_history, allergy_lookup) if tag != "none"]
    return {
        "age": parse_age(age),
        "sex": normalize_sex(sex),
        "disease_history": disease_tags,
        "allergy_history": allergy_tags,
        "insurance_preference": normalize_insurance_preference(insurance_preference),
    }


def has_personalization_input(patient_profile):
    return any(
        [
            patient_profile.get("age") is not None,
            patient_profile.get("sex") not in (None, "", "unknown"),
            bool(patient_profile.get("disease_history")),
            bool(patient_profile.get("allergy_history")),
            patient_profile.get("insurance_preference") == "yes",
        ]
    )


def get_personalization_options():
    return {
        "disease_tags": [item for item in load_disease_tag_dict() if item["is_active"]],
        "allergy_tags": [item for item in load_allergy_tag_dict() if item["is_active"]],
        "sex_options": [
            {"code": "male", "label": "Male"},
            {"code": "female", "label": "Female"},
            {"code": "unknown", "label": "Unknown"},
        ],
        "insurance_preference_options": [
            {"code": "yes", "label": "Insurance Focused"},
            {"code": "no", "label": "No Insurance Preference"},
        ],
    }


def _normalize_metadata_entry(entry):
    normalized = dict(entry)
    cid = entry.get("pubchem_cid")
    normalized["pubchem_cid"] = str(cid).strip() if cid not in (None, "") else ""
    normalized["drug_name"] = str(entry.get("drug_name", "")).strip()
    normalized["smiles"] = str(entry.get("smiles", "")).strip()
    normalized["disease_tags"] = parse_tag_list(entry.get("disease_tags"))
    normalized["allergen_tags"] = parse_tag_list(entry.get("allergen_tags"))
    normalized["contraindication_tags"] = parse_tag_list(entry.get("contraindication_tags"))
    normalized["caution_tags"] = parse_tag_list(entry.get("caution_tags"))
    normalized["age_group"] = str(entry.get("age_group", "unknown")).strip().lower() or "unknown"
    normalized["sex_constraint"] = _normalize_sex_constraint(entry.get("sex_constraint", "unknown"))
    normalized["insurance_status"] = _normalize_insurance_status(entry.get("insurance_status", "unknown"))
    return normalized


@lru_cache(maxsize=1)
def load_drug_metadata():
    metadata_by_cid = {}
    metadata_by_smiles = {}

    csv_entries = _load_csv_rows(DRUG_METADATA_CSV_PATH, DRUG_METADATA_TEMPLATE_PATH)
    if csv_entries:
        for row in csv_entries:
            normalized = _normalize_metadata_entry(row)
            if normalized["pubchem_cid"]:
                metadata_by_cid[normalized["pubchem_cid"]] = normalized
            smiles = normalized.get("smiles")
            if smiles:
                metadata_by_smiles[smiles] = normalized
        return {"by_cid": metadata_by_cid, "by_smiles": metadata_by_smiles}

    if DRUG_METADATA_JSON_PATH.exists():
        try:
            with DRUG_METADATA_JSON_PATH.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError):
            payload = []
        entries = payload.values() if isinstance(payload, dict) else payload
        for entry in entries:
            normalized = _normalize_metadata_entry(entry)
            if normalized["pubchem_cid"]:
                metadata_by_cid[normalized["pubchem_cid"]] = normalized
            smiles = normalized.get("smiles")
            if smiles:
                metadata_by_smiles[smiles] = normalized
    return {"by_cid": metadata_by_cid, "by_smiles": metadata_by_smiles}


def find_metadata_for_drug(drug):
    metadata_map = load_drug_metadata()
    cid = str(drug.get("drugx_id", "")).strip()
    if cid and cid in metadata_map["by_cid"]:
        return metadata_map["by_cid"][cid], "pubchem_cid"

    smiles = str(drug.get("smiles", "")).strip()
    if smiles and smiles in metadata_map["by_smiles"]:
        return metadata_map["by_smiles"][smiles], "smiles"
    return None, "unmatched"


def has_clinical_personalization_metadata(metadata):
    if not metadata:
        return False

    for field in ("disease_tags", "allergen_tags", "contraindication_tags", "caution_tags"):
        if metadata.get(field):
            return True

    age_group = str(metadata.get("age_group", "unknown")).strip().lower()
    if age_group not in ("", "unknown", "all"):
        return True

    sex_constraint = str(metadata.get("sex_constraint", "unknown")).strip().lower()
    if sex_constraint not in ("", "unknown", "all"):
        return True

    insurance_status = str(metadata.get("insurance_status", "unknown")).strip().lower()
    if insurance_status not in ("", "unknown"):
        return True

    return False


def build_metadata_status(drug, metadata=None):
    smiles = str(drug.get("smiles", "")).strip()
    if metadata and has_clinical_personalization_metadata(metadata):
        return {
            "level": "full",
            "label": "Complete metadata",
            "message": "Clinical metadata is available and can be used for personalized reranking.",
        }
    if smiles:
        return {
            "level": "compound_only",
            "label": "Structure only",
            "message": "Only compound structure information is available, so recommendation relies mostly on DTI prediction.",
        }
    return {
        "level": "unknown",
        "label": "Information incomplete",
        "message": "The drug is missing both mapped metadata and reliable structure information.",
    }


def enrich_drug_with_metadata_status(drug):
    enriched = dict(drug)
    metadata, matched_by = find_metadata_for_drug(drug)
    metadata_status = build_metadata_status(drug, metadata)
    enriched["personalization_available"] = metadata_status["level"] == "full"
    enriched["metadata_status"] = metadata_status
    enriched["metadata_match_by"] = matched_by
    return enriched


def normalize_dti_scores(raw_scores):
    if not raw_scores:
        return []
    if len(raw_scores) == 1:
        return [clamp_score(raw_scores[0])]
    min_score = min(raw_scores)
    max_score = max(raw_scores)
    if max_score == min_score:
        return [clamp_score(score) for score in raw_scores]
    return [clamp_score((score - min_score) / (max_score - min_score)) for score in raw_scores]


def score_disease(disease_history, metadata):
    if not disease_history or not metadata:
        return NEUTRAL_SCORE, []
    disease_tags = metadata.get("disease_tags", [])
    matched = sorted(set(disease_history) & set(disease_tags))
    if not matched:
        return 0.0, []
    return clamp_score(len(matched) / max(1, len(disease_history))), matched


def _patient_age_group(age):
    if age is None:
        return None
    if age < 18:
        return "child"
    if age < 65:
        return "adult"
    return "elderly"


def penalty_age(age, metadata):
    if age is None or not metadata:
        return 0.0, "unknown"
    age_group = metadata.get("age_group", "unknown")
    patient_group = _patient_age_group(age)
    if age_group in ("unknown", "", "all") or patient_group is None:
        return 0.0, "matched"
    if age_group == patient_group:
        return 0.0, "matched"
    if age_group == "adult" and patient_group == "child":
        return 0.15, "major"
    if age_group == "elderly" and patient_group == "adult":
        return 0.10, "moderate"
    return 0.05, "minor"


def penalty_sex(sex, metadata):
    if sex in (None, "", "unknown") or not metadata:
        return 0.0, "unknown"
    sex_constraint = metadata.get("sex_constraint", "unknown")
    if sex_constraint in ("unknown", "", "all"):
        return 0.0, "matched"
    if sex_constraint == sex:
        return 0.0, "matched"
    if sex_constraint == "avoid_female" and sex == "female":
        return 0.10, "moderate"
    if sex_constraint == "avoid_male" and sex == "male":
        return 0.10, "moderate"
    return 0.15, "major"


def score_insurance(metadata, insurance_preference):
    if insurance_preference != "yes":
        return 0.0, 0.0
    if not metadata:
        return NEUTRAL_SCORE, 0.15
    mapping = {
        "covered": 1.0,
        "partially_covered": 0.5,
        "not_covered": 0.0,
        "unknown": NEUTRAL_SCORE,
    }
    return mapping.get(metadata.get("insurance_status", "unknown"), NEUTRAL_SCORE), 0.15


def penalty_allergy(allergy_history, metadata):
    if not allergy_history or not metadata:
        return 0.0, []
    matched = sorted(set(allergy_history) & set(metadata.get("allergen_tags", [])))
    if not matched:
        return 0.0, []
    return (0.60, matched) if len(matched) >= 2 else (0.30, matched)


def penalty_contraindication(patient_history, metadata):
    if not patient_history or not metadata:
        return 0.0, []
    matched = sorted(set(patient_history) & set(metadata.get("contraindication_tags", [])))
    if not matched:
        return 0.0, []
    return (0.30, matched) if len(matched) >= 2 else (0.20, matched)


def penalty_caution(patient_history, metadata):
    if not patient_history or not metadata:
        return 0.0, []
    matched = sorted(set(patient_history) & set(metadata.get("caution_tags", [])))
    if not matched:
        return 0.0, []
    return (0.10, matched) if len(matched) >= 2 else (0.05, matched)


def build_recommendation_reason(
    dti_score_norm,
    matched_disease_tags,
    insurance_preference,
    metadata,
    metadata_status_level,
    age_penalty_level,
    sex_penalty_level,
    allergy_hits,
    contraindication_hits,
    caution_hits,
):
    if metadata_status_level == "compound_only":
        return (
            "The recommendation is mainly driven by DTI prediction because only "
            "compound structure information is available for this candidate."
        )
    if metadata_status_level == "unknown":
        return (
            "The recommendation is based on DTI prediction, but the candidate has "
            "limited supporting metadata."
        )

    parts = []

    if dti_score_norm >= 0.75:
        parts.append("Strong DTI support")
    elif dti_score_norm >= 0.4:
        parts.append("Moderate DTI support")
    else:
        parts.append("Basic DTI support")

    if matched_disease_tags:
        parts.append(f"Matched disease history: {', '.join(matched_disease_tags)}")

    if insurance_preference == "yes":
        insurance_status = metadata.get("insurance_status", "unknown") if metadata else "unknown"
        parts.append(f"Insurance status: {insurance_status}")

    if age_penalty_level == "minor":
        parts.append("Minor age-related caution")
    elif age_penalty_level == "moderate":
        parts.append("Moderate age-related caution")
    elif age_penalty_level == "major":
        parts.append("Major age-related caution")

    if sex_penalty_level == "moderate":
        parts.append("Moderate sex-specific caution")
    elif sex_penalty_level == "major":
        parts.append("Major sex-specific caution")

    if allergy_hits:
        parts.append(f"Allergy-related risk: {', '.join(allergy_hits)}")
    if contraindication_hits:
        parts.append(f"Contraindication tags matched: {', '.join(contraindication_hits)}")
    if caution_hits:
        parts.append(f"Caution tags matched: {', '.join(caution_hits)}")

    if not parts:
        return DEFAULT_REASON
    return "; ".join(parts) + "."


def rerank_drugs(drug_info_list, prob_list, patient_profile):
    protein_count = max(1, len(prob_list) // max(1, len(drug_info_list)))
    raw_scores = []
    for index, _drug in enumerate(drug_info_list):
        start = index * protein_count
        end = start + protein_count
        score_slice = prob_list[start:end] or [NEUTRAL_SCORE]
        raw_scores.append(max(clamp_score(score) for score in score_slice))

    normalized_scores = normalize_dti_scores(raw_scores)
    candidates = []

    for source_index, drug in enumerate(drug_info_list):
        cid_value = drug.get("drugx_id")
        metadata, matched_by = find_metadata_for_drug(drug)
        metadata_status = build_metadata_status(drug, metadata)
        personalization_available = metadata_status["level"] == "full"

        disease_score, matched_disease_tags = score_disease(patient_profile["disease_history"], metadata)
        age_penalty, age_penalty_level = penalty_age(patient_profile["age"], metadata)
        sex_penalty, sex_penalty_level = penalty_sex(patient_profile["sex"], metadata)
        insurance_score, insurance_weight = score_insurance(metadata, patient_profile["insurance_preference"])
        allergy_penalty, matched_allergy_tags = penalty_allergy(patient_profile["allergy_history"], metadata)
        contraindication_penalty, matched_contraindication_tags = penalty_contraindication(
            patient_profile["disease_history"], metadata
        )
        caution_penalty, matched_caution_tags = penalty_caution(patient_profile["disease_history"], metadata)

        dti_score_raw = raw_scores[source_index]
        dti_score_norm = normalized_scores[source_index] if source_index < len(normalized_scores) else NEUTRAL_SCORE

        final_score = (
            0.65 * dti_score_norm
            + 0.20 * disease_score
            + insurance_weight * insurance_score
            - age_penalty
            - sex_penalty
            - allergy_penalty
            - contraindication_penalty
            - caution_penalty
        )
        final_score = round(clamp_score(final_score), 6)

        default_name = drug.get("iupac_name") or f"Drug_{cid_value or source_index + 1}"
        recommendation_reason = build_recommendation_reason(
            dti_score_norm=dti_score_norm,
            matched_disease_tags=matched_disease_tags,
            insurance_preference=patient_profile["insurance_preference"],
            metadata=metadata,
            metadata_status_level=metadata_status["level"],
            age_penalty_level=age_penalty_level,
            sex_penalty_level=sex_penalty_level,
            allergy_hits=matched_allergy_tags,
            contraindication_hits=matched_contraindication_tags,
            caution_hits=matched_caution_tags,
        )

        candidates.append(
            {
                "source_index": source_index,
                "pubchem_cid": cid_value,
                "drug_name": metadata.get("drug_name", default_name) if metadata else default_name,
                "dti_score_raw": round(dti_score_raw, 6),
                "dti_score_norm": round(clamp_score(dti_score_norm), 6),
                "final_score": final_score,
                "personalization_available": personalization_available,
                "metadata_status": metadata_status,
                "score_breakdown": {
                    "s_dti": round(clamp_score(dti_score_norm), 6),
                    "s_disease": round(clamp_score(disease_score), 6),
                    "s_insurance": round(clamp_score(insurance_score), 6),
                    "p_age": round(clamp_score(age_penalty), 6),
                    "p_sex": round(clamp_score(sex_penalty), 6),
                    "p_allergy": round(clamp_score(allergy_penalty), 6),
                    "p_contraindication": round(clamp_score(contraindication_penalty), 6),
                    "p_caution": round(clamp_score(caution_penalty), 6),
                },
                "match_info": {
                    "matched_by": matched_by,
                    "matched_disease_tags": matched_disease_tags,
                    "matched_allergy_tags": matched_allergy_tags,
                    "matched_contraindication_tags": matched_contraindication_tags,
                    "matched_caution_tags": matched_caution_tags,
                },
                "insurance_status": metadata.get("insurance_status", "unknown") if metadata else "unknown",
                "age_group": metadata.get("age_group", "unknown") if metadata else "unknown",
                "sex_constraint": metadata.get("sex_constraint", "unknown") if metadata else "unknown",
                "allergen_tags": metadata.get("allergen_tags", []) if metadata else [],
                "contraindication_tags": metadata.get("contraindication_tags", []) if metadata else [],
                "caution_tags": metadata.get("caution_tags", []) if metadata else [],
                "disease_tags": metadata.get("disease_tags", []) if metadata else [],
                "recommendation_reason": recommendation_reason,
            }
        )

    original_sorted = sorted(candidates, key=lambda item: (-item["dti_score_raw"], item["source_index"]))
    for rank, item in enumerate(original_sorted, start=1):
        item["original_rank"] = rank

    personalized_sorted = sorted(
        candidates,
        key=lambda item: (-item["final_score"], item["original_rank"], item["source_index"]),
    )
    for rank, item in enumerate(personalized_sorted, start=1):
        item["personalized_rank"] = rank

    for item in personalized_sorted:
        item.pop("source_index", None)

    return personalized_sorted
