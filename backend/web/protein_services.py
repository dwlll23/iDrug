import json
import os
import re
import csv
from io import StringIO
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

import pypdb
from Bio import PDB
from Bio.PDB import PDBParser
from pypdb.clients.pdb.pdb_client import get_pdb_file


MOCK_SEQUENCE = "MOCK_SEQUENCE"


MOCK_PROTEIN_DATA = {
    "5IMT": {
        "seq": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN",
        "deposit_date": "2015-06-25",
        "release_date": "2015-09-23",
        "molecular_weight": "5808.0",
        "nonpolymer_bound_components": "ZINC ION, WATER",
        "pdbx_keywords": "INSULIN, HORMONE, STRUCTURE",
    }
}


class ProteinNotFoundError(ValueError):
    pass


def _mock_protein_info(pdb_id, base_dir, seq=""):
    pdb_id = str(pdb_id).strip().upper() or "UNKNOWN"
    mock = MOCK_PROTEIN_DATA.get(pdb_id, {})
    return {
        "pdb_id": pdb_id,
        "uniprot_id": "",
        "source": "mock",
        "seq": seq or mock.get("seq") or "模拟序列",
        "deposit_date": mock.get("deposit_date", "NOT FOUND"),
        "release_date": mock.get("release_date", "NOT FOUND"),
        "molecular_weight": str(mock.get("molecular_weight", "NOT FOUND")),
        "nonpolymer_bound_components": mock.get("nonpolymer_bound_components", "NOT FOUND"),
        "pdbx_keywords": mock.get("pdbx_keywords", "MOCK PROTEIN"),
        "image_url": _find_local_pdb_image(pdb_id, base_dir) or "/pic/5IMT.png",
    }


def _is_mock_like(info):
    return isinstance(info, dict) and str(info.get("source", "")).strip().lower() == "mock"


def get_pdb_seq(pdb_id):
    try:
        pdb_file = get_pdb_file(pdb_id)
        parser = PDBParser()
        structure = parser.get_structure(pdb_id, StringIO(pdb_file))
        ppb = PDB.PPBuilder()
        peptides = ppb.build_peptides(structure)
        if not peptides:
            return ""
        return str(peptides[0].get_sequence())
    except Exception:
        return MOCK_PROTEIN_DATA.get(str(pdb_id).strip().upper(), {}).get("seq", "模拟序列")


def _load_json_url(url, timeout=10):
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _safe_get(data, *keys, default=""):
    current = data
    for key in keys:
        if isinstance(current, list):
            if not current:
                return default
            current = current[key]
        elif isinstance(current, dict):
            if key not in current:
                return default
            current = current[key]
        else:
            return default
    return current if current not in (None, "") else default


def _find_local_pdb_image(pdb_id, base_dir):
    pic_dir = os.path.join(base_dir, "pic")
    target = f"{pdb_id}.png".lower()
    if not os.path.isdir(pic_dir):
        return ""

    for filename in os.listdir(pic_dir):
        if filename.lower() == target:
            return f"/pic/{filename}"
    return ""


def _remote_pdb_image(pdb_id):
    return f"https://cdn.rcsb.org/images/structures/{pdb_id.lower()}_assembly-1.jpeg"


def _normalize_bound_components(value):
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "NOT FOUND"
    if value in (None, ""):
        return "NOT FOUND"
    return str(value)


def _protein_map_path(base_dir):
    return os.path.join(base_dir, "pdb_protein_map.csv")


def _complex_map_path(base_dir):
    return os.path.join(base_dir, "pdb_complex_map.csv")


def _load_local_protein_map(base_dir):
    path = _protein_map_path(base_dir)
    if not os.path.isfile(path):
        return []

    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            normalized = {str(k).strip(): str(v).strip() for k, v in row.items() if k}
            pdb_id = normalized.get("pdb_id", "").upper()
            if not pdb_id:
                continue
            normalized["pdb_id"] = pdb_id
            rows.append(normalized)
    return rows


def _load_local_complex_map(base_dir):
    path = _complex_map_path(base_dir)
    if not os.path.isfile(path):
        return []

    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            normalized = {str(k).strip(): str(v).strip() for k, v in row.items() if k}
            pdb_id = normalized.get("pdb_id", "").upper()
            if not pdb_id:
                continue
            normalized["pdb_id"] = pdb_id
            rows.append(normalized)
    return rows


def _build_local_protein_info(row, base_dir):
    pdb_id = row.get("pdb_id", "").upper()
    local_image = _find_local_pdb_image(pdb_id, base_dir)
    image_url = local_image or row.get("image_url") or _remote_pdb_image(pdb_id)
    image_source = "local" if local_image else (row.get("image_source") or "rcsb")
    data_source = row.get("data_source") or "local_manual"
    data_status = row.get("data_status") or "full"

    return {
        "pdb_id": pdb_id,
        "uniprot_id": row.get("uniprot_id", ""),
        "protein_name": row.get("protein_name", ""),
        "source": data_source,
        "query_status": "ok",
        "data_status": data_status,
        "seq": row.get("seq", "") or MOCK_SEQUENCE,
        "deposit_date": row.get("deposit_date", "NOT FOUND") or "NOT FOUND",
        "release_date": row.get("release_date", "NOT FOUND") or "NOT FOUND",
        "molecular_weight": row.get("molecular_weight", "NOT FOUND") or "NOT FOUND",
        "nonpolymer_bound_components": row.get("bound_components", "NOT FOUND") or "NOT FOUND",
        "pdbx_keywords": row.get("keywords", "NOT FOUND") or "NOT FOUND",
        "image_url": image_url,
        "image_source": image_source,
    }


def get_local_pdb_info(pdb_id, base_dir):
    target = str(pdb_id).strip().upper()
    if not target:
        return None

    for row in _load_local_protein_map(base_dir):
        if row.get("pdb_id") == target:
            return _build_local_protein_info(row, base_dir)
    return None


def get_local_uniprot_info(uniprot_id, base_dir):
    target = str(uniprot_id).strip().upper()
    if not target:
        return None

    for row in _load_local_protein_map(base_dir):
        aliases = [item.strip().upper() for item in row.get("uniprot_id", "").split(";") if item.strip()]
        if target in aliases:
            info = _build_local_protein_info(row, base_dir)
            info["uniprot_id"] = target
            info["source"] = "local_uniprot"
            return info
    return None


def get_local_sequence_info(sequence, base_dir):
    target = re.sub(r"\s+", "", str(sequence).strip()).upper()
    if not target:
        return None

    for row in _load_local_protein_map(base_dir):
        if re.sub(r"\s+", "", row.get("seq", "").strip()).upper() == target:
            info = _build_local_protein_info(row, base_dir)
            info["source"] = "local_sequence"
            return info
    return None


def _build_local_complex_info(row, base_dir):
    pdb_id = row.get("pdb_id", "").upper()
    local_image = _find_local_pdb_image(pdb_id, base_dir)
    image_url = local_image or row.get("image_url") or _remote_pdb_image(pdb_id)
    structure_file_url = row.get("structure_file_url") or f"https://files.rcsb.org/download/{pdb_id}.cif"
    return {
        "pdb_id": pdb_id,
        "title": row.get("title", "") or f"{pdb_id} Complex",
        "protein_name": row.get("protein_name", "") or "NOT FOUND",
        "uniprot_id": row.get("uniprot_id", ""),
        "ligand_ids": row.get("ligand_ids", "") or "NOT FOUND",
        "ligand_names": row.get("ligand_names", "") or "NOT FOUND",
        "bound_components": row.get("bound_components", "") or "NOT FOUND",
        "experimental_method": row.get("experimental_method", "") or "NOT FOUND",
        "resolution": row.get("resolution", "") or "NOT FOUND",
        "keywords": row.get("keywords", "") or "NOT FOUND",
        "image_url": image_url,
        "structure_file_url": structure_file_url,
        "source": row.get("data_source", "") or "local_complex",
        "query_status": "ok",
        "data_status": row.get("data_status", "") or "full",
    }


def get_local_complex_info(pdb_id, base_dir):
    target = str(pdb_id).strip().upper()
    if not target:
        return None

    for row in _load_local_complex_map(base_dir):
        if row.get("pdb_id") == target:
            return _build_local_complex_info(row, base_dir)
    return None


def get_online_complex_info(pdb_id, base_dir):
    pdb_id = str(pdb_id).strip().upper()
    local_info = get_local_complex_info(pdb_id, base_dir)
    if local_info:
        return local_info

    try:
        description = pypdb.describe_pdb(pdb_id)
    except Exception as exc:
        raise RuntimeError(f"Failed to access online PDB source: {exc}") from exc

    if not description:
        raise ProteinNotFoundError(f"Complex entry not found: {pdb_id}")

    local_protein = get_local_pdb_info(pdb_id, base_dir) or {}
    struct_info = description.get("struct", {})
    entry_info = description.get("rcsb_entry_info", {})
    keywords_info = description.get("struct_keywords", {})
    exptl = description.get("exptl", [])
    accession_info = description.get("rcsb_accession_info", {})
    resolution = entry_info.get("resolution_combined", [])
    if isinstance(resolution, list):
        resolution_text = ", ".join(str(item) for item in resolution) if resolution else "NOT FOUND"
    else:
        resolution_text = str(resolution or "NOT FOUND")

    bound_components = _normalize_bound_components(entry_info.get("nonpolymer_bound_components", "NOT FOUND"))
    ligand_ids = bound_components if bound_components != "NOT FOUND" else ""
    ligand_names = bound_components if bound_components != "NOT FOUND" else "NOT FOUND"

    return {
        "pdb_id": pdb_id,
        "title": struct_info.get("title", "") or f"{pdb_id} Complex",
        "protein_name": local_protein.get("protein_name", "") or keywords_info.get("pdbx_keywords", "NOT FOUND"),
        "uniprot_id": local_protein.get("uniprot_id", ""),
        "ligand_ids": ligand_ids or "NOT FOUND",
        "ligand_names": ligand_names,
        "bound_components": bound_components,
        "experimental_method": exptl[0].get("method", "NOT FOUND") if exptl else "NOT FOUND",
        "resolution": resolution_text,
        "keywords": keywords_info.get("pdbx_keywords", "NOT FOUND"),
        "image_url": _find_local_pdb_image(pdb_id, base_dir) or _remote_pdb_image(pdb_id),
        "structure_file_url": f"https://files.rcsb.org/download/{pdb_id}.cif",
        "source": "pdb_online",
        "query_status": "ok",
        "data_status": "partial" if not local_protein else "full",
        "release_date": accession_info.get("initial_release_date", "NOT FOUND"),
    }


def query_complex_info(pdb_id, base_dir):
    value = str(pdb_id).strip().upper()
    if not value:
        raise ValueError("PDB ID is required")
    local_info = get_local_complex_info(value, base_dir)
    if local_info:
        return local_info
    return get_online_complex_info(value, base_dir)


def get_online_pdb_info(pdb_id, base_dir):
    pdb_id = str(pdb_id).strip().upper()
    local_info = get_local_pdb_info(pdb_id, base_dir)
    if local_info:
        return local_info

    try:
        description = pypdb.describe_pdb(pdb_id)
    except Exception as exc:
        fallback = _mock_protein_info(pdb_id, base_dir)
        fallback["query_status"] = "degraded"
        fallback["source_message"] = "Online PDB source is temporarily unavailable; using fallback data."
        fallback["error_type"] = "online_unavailable"
        fallback["error_detail"] = str(exc)
        return fallback
    if not description:
        raise ProteinNotFoundError(f"PDB entry not found: {pdb_id}")

    accession_info = description.get("rcsb_accession_info", {})
    entry_info = description.get("rcsb_entry_info", {})
    struct_keywords = description.get("struct_keywords", {})

    return {
        "pdb_id": pdb_id,
        "uniprot_id": "",
        "source": "pdb",
        "query_status": "ok",
        "seq": get_pdb_seq(pdb_id),
        "deposit_date": accession_info.get("deposit_date", "NOT FOUND"),
        "release_date": accession_info.get("initial_release_date", "NOT FOUND"),
        "molecular_weight": str(entry_info.get("molecular_weight", "NOT FOUND")),
        "nonpolymer_bound_components": _normalize_bound_components(
            entry_info.get("nonpolymer_bound_components", "NOT FOUND")
        ),
        "pdbx_keywords": struct_keywords.get("pdbx_keywords", "NOT FOUND"),
        "image_url": _find_local_pdb_image(pdb_id, base_dir) or _remote_pdb_image(pdb_id),
    }


def get_uniprot_info(uniprot_id, base_dir):
    accession = str(uniprot_id).strip().upper()
    local_info = get_local_uniprot_info(accession, base_dir)
    if local_info:
        return local_info

    url = f"https://rest.uniprot.org/uniprotkb/{quote(accession)}.json"
    try:
        data = _load_json_url(url)
    except HTTPError as exc:
        if exc.code == 404:
            raise ProteinNotFoundError(f"UniProt entry not found: {accession}") from exc
        raise

    sequence = _safe_get(data, "sequence", "value", default="")
    mol_weight = _safe_get(data, "sequence", "molWeight", default="NOT FOUND")
    protein_name = _safe_get(
        data,
        "proteinDescription",
        "recommendedName",
        "fullName",
        "value",
        default="UNIPROT PROTEIN",
    )

    pdb_refs = []
    for item in data.get("uniProtKBCrossReferences", []):
        if item.get("database") == "PDB" and item.get("id"):
            pdb_refs.append(item["id"].upper())

    base_info = {
        "pdb_id": pdb_refs[0] if pdb_refs else "",
        "uniprot_id": accession,
        "source": "uniprot",
        "query_status": "ok",
        "seq": sequence,
        "deposit_date": "NOT FOUND",
        "release_date": "NOT FOUND",
        "molecular_weight": str(mol_weight),
        "nonpolymer_bound_components": "NOT FOUND",
        "pdbx_keywords": protein_name,
        "image_url": "",
    }

    if not pdb_refs:
        return base_info

    try:
        pdb_info = get_online_pdb_info(pdb_refs[0], base_dir)
        pdb_info["uniprot_id"] = accession
        pdb_info["source"] = "uniprot+pdb"
        if not pdb_info.get("seq"):
            pdb_info["seq"] = sequence
        if pdb_info.get("pdbx_keywords") in ("", "NOT FOUND"):
            pdb_info["pdbx_keywords"] = protein_name
        return pdb_info
    except Exception:
        return base_info


def search_pdb_by_sequence(sequence):
    cleaned_sequence = re.sub(r"\s+", "", str(sequence).strip()).upper()
    if not cleaned_sequence:
        raise ValueError("Protein sequence is empty")

    query = pypdb.Query(cleaned_sequence, query_type="sequence")
    result = query.search()

    if isinstance(result, dict):
        result_set = result.get("result_set", [])
        if result_set:
            identifier = result_set[0].get("identifier", "")
            if identifier:
                return identifier.split("_")[0].upper()
    elif isinstance(result, list) and result:
        return str(result[0]).split("_")[0].upper()
    elif isinstance(result, str) and result:
        return result.split("_")[0].upper()

    raise ValueError("No matching PDB entry found for the protein sequence")


def resolve_protein_info(select_op, input_text, base_dir):
    value = str(input_text).strip()
    if not value:
        raise ValueError("Protein query is empty")

    option = str(select_op)

    if option == "1":
        return get_online_pdb_info(value, base_dir)

    if option == "2":
        try:
            return get_uniprot_info(value, base_dir)
        except ProteinNotFoundError:
            raise
        except (HTTPError, URLError, ValueError):
            raise
        except Exception:
            fallback = _mock_protein_info("5IMT", base_dir)
            fallback["query_status"] = "degraded"
            fallback["source_message"] = "Online UniProt source is temporarily unavailable; using fallback data."
            fallback["error_type"] = "online_unavailable"
            return fallback

    local_sequence_info = get_local_sequence_info(value, base_dir)
    if local_sequence_info:
        return local_sequence_info

    try:
        pdb_id = search_pdb_by_sequence(value)
        pdb_info = get_online_pdb_info(pdb_id, base_dir)
        if not pdb_info.get("seq"):
            pdb_info["seq"] = value
        pdb_info["source"] = "sequence+pdb"
        return pdb_info
    except Exception:
        return _mock_protein_info("5IMT", base_dir, seq=value)


def resolve_pdb_protein_info(pdb_id, base_dir):
    return resolve_protein_info("1", pdb_id, base_dir)


def get_online_protein_info(select_op, input_text, base_dir):
    return resolve_protein_info(select_op, input_text, base_dir)


def query_protein_info(select_op, input_text, base_dir):
    """Query-oriented resolver that distinguishes not found from degraded fallback."""
    value = str(input_text).strip()
    if str(select_op) == "1":
        return get_online_pdb_info(value, base_dir)
    if str(select_op) == "2":
        return get_uniprot_info(value, base_dir)
    return resolve_protein_info(select_op, value, base_dir)
