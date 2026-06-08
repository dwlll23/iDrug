import csv
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_DIR.parent
MODELS_DIR = REPO_ROOT / "model"
RUNTIME_TMP_DIR = APP_DIR / "runtime_tmp_ascii"

TASK_CONFIG = {
    "drug_repositioning": {"label": "Drug Repositioning"},
    "novel_target_screening": {"label": "Novel Target Screening"},
    "new_drug_evaluation": {"label": "New Drug Evaluation"},
    "affinity_prediction": {"label": "Affinity Prediction"},
}

HYPERATTENTION_HUMAN_CHECKPOINT = "human_random.pt"
HYPERATTENTION_GPCR_CHECKPOINT = "gpcr_unseen_protein.pt"


def _build_result(task_type, status, message, result_items=None):
    return {
        "task_type": task_type,
        "task_label": TASK_CONFIG[task_type]["label"],
        "status": status,
        "message": message,
        "result_items": result_items or [],
    }


def _normalize_multiline_input(raw_text):
    text = str(raw_text or "").replace("\r", "\n").strip()
    if not text:
        return []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return lines or [text]


def _resolve_python(model_key):
    env_mapping = {
        "hyperattentionati": "HYPERATTENTIONDTI_PYTHON",
        "psichic": "PSICHIC_PYTHON",
        "deepdta": "DEEPDTA_PYTHON",
        "transformercpi": "TRANSFORMERCPI_PYTHON",
        "graphdta": "GRAPHDTA_PYTHON",
    }
    return os.environ.get(env_mapping.get(model_key, ""), sys.executable)


def _write_pair_csv(csv_path, protein_values, ligand_values, include_sample_id=False):
    rows = []
    pair_index = 0
    for protein in protein_values:
        for ligand in ligand_values:
            row = {
                "Protein": protein,
                "Ligand": ligand,
                "classification_label": 0,
            }
            if include_sample_id:
                row["sample_id"] = pair_index
            rows.append(row)
            pair_index += 1

    fieldnames = ["Protein", "Ligand", "classification_label"]
    if include_sample_id:
        fieldnames = ["sample_id"] + fieldnames

    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows


def _read_csv_rows(csv_path):
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _make_runtime_temp_dir(prefix):
    RUNTIME_TMP_DIR.mkdir(parents=True, exist_ok=True)
    target = RUNTIME_TMP_DIR / f"{prefix}{uuid.uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _run_subprocess(command, cwd, env=None):
    process = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if process.returncode != 0:
        stderr = (process.stderr or "").strip()
        stdout = (process.stdout or "").strip()
        details = stderr or stdout or f"Exit code {process.returncode}"
        raise RuntimeError(details)
    return process


def _run_hyperattention_batch(drug_input, protein_input, checkpoint_name):
    model_dir = MODELS_DIR / "hyperattentionati"
    temp_dir = _make_runtime_temp_dir("hyperattention_")
    try:
        input_csv = temp_dir / "input.csv"
        pred_csv = temp_dir / "pred.csv"
        emb_npy = temp_dir / "emb.npy"
        input_rows = _write_pair_csv(
            input_csv,
            _normalize_multiline_input(protein_input),
            _normalize_multiline_input(drug_input),
            include_sample_id=False,
        )
        command = [
            _resolve_python("hyperattentionati"),
            str((model_dir / "inference.py").resolve()),
            "--model_path",
            str((model_dir / "checkpoints" / checkpoint_name).resolve()),
            "--input_csv",
            str(input_csv.resolve()),
            "--pred_csv",
            str(pred_csv.resolve()),
            "--emb_npy",
            str(emb_npy.resolve()),
            "--batch_size",
            "2",
            "--device",
            "auto",
        ]
        _run_subprocess(command, model_dir)
        output_rows = _read_csv_rows(pred_csv)
        return input_rows, output_rows
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def predict_hyperattention_scores(drug_input, protein_input, checkpoint_name=HYPERATTENTION_HUMAN_CHECKPOINT):
    _, output_rows = _run_hyperattention_batch(drug_input, protein_input, checkpoint_name)
    return [round(float(row.get("pred_prob", 0) or 0), 3) for row in output_rows]


def run_hyperattention_task(task_type, drug_input, protein_input, checkpoint_name, success_message):
    input_rows, output_rows = _run_hyperattention_batch(drug_input, protein_input, checkpoint_name)
    result_items = []
    for index, row in enumerate(output_rows, start=1):
        source_row = input_rows[index - 1]
        result_items.append({
            "rank": index,
            "drug_input": source_row["Ligand"],
            "protein_input": source_row["Protein"],
            "raw_score": float(row.get("pred_prob", 0) or 0),
            "pred_label": row.get("pred_label", ""),
        })
    return _build_result(task_type, "ok", success_message, result_items=result_items)


def _extract_psichic_score(row):
    for key in ["predicted_binary_interaction", "predicted_binding_affinity", "predicted_class_1", "predicted_class_0"]:
        value = row.get(key, "")
        if value not in (None, ""):
            return float(value)
    return 0.0


def run_psichic(drug_input, protein_input):
    model_dir = MODELS_DIR / "psichic"
    temp_dir = _make_runtime_temp_dir("psichic_")
    try:
        input_csv = temp_dir / "input.csv"
        result_dir = temp_dir / "outputs"
        result_dir.mkdir(parents=True, exist_ok=True)
        input_rows = _write_pair_csv(
            input_csv,
            _normalize_multiline_input(protein_input),
            _normalize_multiline_input(drug_input),
            include_sample_id=False,
        )
        command = [
            _resolve_python("psichic"),
            str((model_dir / "inference.py").resolve()),
            "--device",
            "cpu",
            "--classification_task",
            "True",
            "--trained_model_path",
            str((model_dir / "checkpoints").resolve()),
            "--screenfile",
            str(input_csv.resolve()),
            "--result_path",
            str(result_dir.resolve()),
        ]
        torch_home = (APP_DIR / "runtime_cache" / "torch_home").resolve()
        torch_home.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["TORCH_HOME"] = str(torch_home)
        _run_subprocess(command, model_dir, env=env)
        output_rows = _read_csv_rows(result_dir / "pred.csv")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    result_items = []
    for index, row in enumerate(output_rows, start=1):
        source_row = input_rows[index - 1]
        result_items.append({
            "rank": index,
            "drug_input": source_row["Ligand"],
            "protein_input": source_row["Protein"],
            "raw_score": _extract_psichic_score(row),
        })

    return _build_result(
        "new_drug_evaluation",
        "ok",
        "PSICHIC prediction completed successfully.",
        result_items=result_items,
    )


def run_deepdta(drug_input, protein_input):
    model_dir = MODELS_DIR / "deepdta"
    temp_dir = _make_runtime_temp_dir("deepdta_")
    try:
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "pred.csv"
        input_rows = _write_pair_csv(
            input_csv,
            _normalize_multiline_input(protein_input),
            _normalize_multiline_input(drug_input),
            include_sample_id=False,
        )
        command = [
            _resolve_python("deepdta"),
            str((model_dir / "inference.py").resolve()),
            "--input_csv",
            str(input_csv.resolve()),
            "--checkpoint",
            "gpcr_1_best_finetuned.h5",
            "--output_csv",
            str(output_csv.resolve()),
        ]
        _run_subprocess(command, model_dir)
        output_rows = _read_csv_rows(output_csv)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    result_items = []
    for index, row in enumerate(output_rows, start=1):
        source_row = input_rows[index - 1]
        result_items.append({
            "rank": index,
            "drug_input": source_row["Ligand"],
            "protein_input": source_row["Protein"],
            "raw_score": float(row.get("pred_prob", 0) or 0),
        })

    return _build_result(
        "affinity_prediction",
        "ok",
        "DeepDTA prediction completed successfully.",
        result_items=result_items,
    )


def run_prediction_task(task_type, drug_input, protein_input):
    if task_type == "drug_repositioning":
        return run_hyperattention_task(
            "drug_repositioning",
            drug_input,
            protein_input,
            HYPERATTENTION_HUMAN_CHECKPOINT,
            "HyperAttentionDTI prediction completed successfully.",
        )
    if task_type == "novel_target_screening":
        return run_hyperattention_task(
            "novel_target_screening",
            drug_input,
            protein_input,
            HYPERATTENTION_GPCR_CHECKPOINT,
            "HyperAttentionDTI prediction completed successfully.",
        )
    if task_type == "new_drug_evaluation":
        return run_psichic(drug_input, protein_input)
    if task_type == "affinity_prediction":
        return run_deepdta(drug_input, protein_input)
    raise ValueError("Unsupported task type")



