from functools import lru_cache
from pathlib import Path
import csv

import pubchempy as pcp


BASE_DIR = Path(__file__).resolve().parent.parent
FDA_CSV_PATH = BASE_DIR / "FDA_PubChem_matched_database.csv"
CID_SMILES_CSV_PATH = BASE_DIR / "cid_smiles_map.csv"


def _build_pubchem_image_url(cid):
    cid_text = str(cid).strip()
    return (
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/CID/"
        f"{cid_text}/PNG/?record_type=2d&size=500x500&bgcolor=white"
    )


def _safe_text(value, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.upper() == "N/A":
        return default
    return text


def _normalize_smiles(value):
    return _safe_text(value)


def _compatible_smiles_fields(smiles):
    normalized = _normalize_smiles(smiles)
    return {
        "canonical_smiles": normalized,
        "isomeric_smiles": normalized,
        "smiles": normalized,
    }


def _extract_compound_smiles(compound):
    for attr in ("isomeric_smiles", "canonical_smiles"):
        value = _normalize_smiles(getattr(compound, attr, ""))
        if value:
            return value
    return ""


def _extract_compound_name(compound):
    iupac_name = _safe_text(getattr(compound, "iupac_name", ""))
    if iupac_name:
        return iupac_name

    synonyms = getattr(compound, "synonyms", None)
    if isinstance(synonyms, (list, tuple)) and synonyms:
        return _safe_text(synonyms[0])

    return ""


def _build_payload(
    cid,
    drug_name="",
    smiles="",
    molecular_formula="",
    molecular_weight="",
    iupac_name="",
    xlogp="",
    rotatable_bond_count="",
):
    cid_text = str(cid).strip()
    payload = {
        "drugx_id": cid_text,
        "drug_name": _safe_text(drug_name),
        "molecular_formula": _safe_text(molecular_formula),
        "molecular_weight": _safe_text(molecular_weight),
        "iupac_name": _safe_text(iupac_name),
        "xlogp": _safe_text(xlogp),
        "rotatable_bond_count": _safe_text(rotatable_bond_count),
        "url_": _build_pubchem_image_url(cid_text),
    }
    payload.update(_compatible_smiles_fields(smiles))
    return payload


@lru_cache(maxsize=1)
def _load_fda_cid_map():
    cid_map = {}
    if not FDA_CSV_PATH.exists():
        return cid_map

    with FDA_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            cid = _safe_text(row.get("CID"))
            if cid:
                cid_map[cid] = row
    return cid_map


@lru_cache(maxsize=1)
def _load_cid_smiles_map():
    cid_map = {}
    if not CID_SMILES_CSV_PATH.exists():
        return cid_map

    with CID_SMILES_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            cid = _safe_text(row.get("cid"))
            if cid:
                cid_map[cid] = row
    return cid_map


def _build_payload_from_local_row(cid, row):
    drug_name = row.get("drug_name", "")
    smiles = row.get("smiles", "")
    molecular_formula = row.get("molecular_formula", "")
    molecular_weight = row.get("molecular_weight", "")
    return _build_payload(
        cid=cid,
        drug_name=drug_name,
        smiles=smiles,
        molecular_formula=molecular_formula,
        molecular_weight=molecular_weight,
        iupac_name=drug_name,
    )


def _build_payload_from_fda_row(cid, row):
    drug_name = row.get("Proprietary_Name") or row.get("Active_Ingredient") or ""
    return _build_payload(
        cid=cid,
        drug_name=drug_name,
        smiles=row.get("SMILES", ""),
        molecular_formula=row.get("Molecular_Formula", ""),
        molecular_weight=row.get("Molecular_Weight", ""),
        iupac_name=row.get("IUPAC_Name", "") or drug_name,
        xlogp=row.get("XLogP", ""),
    )


def _build_payload_from_properties(cid, properties):
    drug_name = properties.get("Title", "")
    smiles = properties.get("IsomericSMILES") or properties.get("CanonicalSMILES") or ""
    return _build_payload(
        cid=cid,
        drug_name=drug_name,
        smiles=smiles,
        molecular_formula=properties.get("MolecularFormula", ""),
        molecular_weight=properties.get("MolecularWeight", ""),
        iupac_name=drug_name,
        xlogp=properties.get("XLogP", ""),
        rotatable_bond_count=properties.get("RotatableBondCount", ""),
    )


def _build_payload_from_compound(compound, cid=None):
    resolved_cid = cid if cid is not None else getattr(compound, "cid", "")
    drug_name = _extract_compound_name(compound)
    return _build_payload(
        cid=resolved_cid,
        drug_name=drug_name,
        smiles=_extract_compound_smiles(compound),
        molecular_formula=getattr(compound, "molecular_formula", ""),
        molecular_weight=getattr(compound, "molecular_weight", ""),
        iupac_name=getattr(compound, "iupac_name", ""),
        xlogp=getattr(compound, "xlogp", ""),
        rotatable_bond_count=getattr(compound, "rotatable_bond_count", ""),
    )


def _resolve_drug_payload_by_cid(cid):
    cid_text = str(cid).strip()

    local_row = _load_cid_smiles_map().get(cid_text)
    if local_row:
        payload = _build_payload_from_local_row(cid_text, local_row)
        if payload["smiles"]:
            return payload

    cid_int = int(cid_text)

    try:
        compound = pcp.Compound.from_cid(cid_int)
        payload = _build_payload_from_compound(compound, cid_text)
        if payload["smiles"]:
            return payload
    except Exception:
        pass

    try:
        compounds = pcp.get_compounds(cid_int, "cid")
        if compounds:
            payload = _build_payload_from_compound(compounds[0], cid_text)
            if payload["smiles"]:
                return payload
    except Exception:
        pass

    try:
        properties_list = pcp.get_properties(
            [
                "Title",
                "CanonicalSMILES",
                "IsomericSMILES",
                "MolecularFormula",
                "MolecularWeight",
                "XLogP",
                "RotatableBondCount",
            ],
            cid_int,
            "cid",
        )
        if properties_list:
            payload = _build_payload_from_properties(cid_text, properties_list[0])
            if payload["smiles"]:
                return payload
    except Exception:
        pass

    fda_row = _load_fda_cid_map().get(cid_text)
    if fda_row:
        payload = _build_payload_from_fda_row(cid_text, fda_row)
        if payload["smiles"]:
            return payload

    raise ValueError(f"Unable to resolve drug payload for CID {cid_text}")


def get_drug_info(compound, c):
    if c is None:
        raise ValueError("Compound is required")
    return _build_payload_from_compound(c)


def get_drug_info_by_cid(cid, compound=None):
    return _resolve_drug_payload_by_cid(cid)


def build_drug_entry_from_cid(cid):
    payload = get_drug_info_by_cid(cid)
    return payload, payload.get("smiles", "")


def build_fallback_drug_entry(cid):
    cid_text = str(cid).strip()
    payload = _build_payload(
        cid=cid_text,
        drug_name=f"未知药物_{cid_text}",
        smiles="",
        molecular_formula="",
        molecular_weight="",
        iupac_name=f"未知药物_{cid_text}",
    )
    return payload, ""
