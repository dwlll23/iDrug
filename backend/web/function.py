from pathlib import Path

from web.drug_services import get_drug_info
from web.protein_services import get_online_pdb_info, get_online_protein_info, get_pdb_seq


def get_pdb_info(pdb_id, seq=None, base_dir=None):
    resolved_base_dir = base_dir or str(Path(__file__).resolve().parent.parent)
    pdb_info = get_online_pdb_info(pdb_id, resolved_base_dir)
    if seq and not pdb_info.get("seq"):
        pdb_info["seq"] = seq
    return pdb_info


__all__ = [
    "get_drug_info",
    "get_pdb_info",
    "get_online_protein_info",
    "get_pdb_seq",
]
