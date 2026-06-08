# PSICHIC Predict Package

This folder is a minimal inference bundle extracted from the current PSICHIC project.

## Folder layout

- `inference.py`: prediction entry script
- `requirements.txt`: minimal dependency list
- `checkpoints/`: packaged checkpoint files
- `models/`: model code required by inference
- `utils/`: preprocessing and graph construction code required by inference
- `examples/`: sample input files

## Required input CSV

Your input CSV must contain at least these columns:

- `Protein`
- `Ligand`

`Protein` should be the amino-acid sequence string.
`Ligand` should be the SMILES string.

## Packaged checkpoints

The bundled checkpoint directory contains:

- `checkpoints/model.pt`
- `checkpoints/degree.pt`
- `checkpoints/config.json`

## Quick start

### CPU

```bash
python inference.py --device cpu --classification_task True --screenfile examples/sample_input.csv --result_path outputs
```

### GPU

```bash
python inference.py --device cuda:0 --classification_task True --screenfile examples/sample_input.csv --result_path outputs
```

## Custom checkpoint path

```bash
python inference.py --device cpu --classification_task True --trained_model_path checkpoints --screenfile your_input.csv --result_path outputs
```

## Outputs

After prediction, the output folder will contain:

- `pred.csv`
- `emb.npy`

## Notes

- If your checkpoint is a binary classification model, pass `--classification_task True`.
- If your checkpoint is a regression model, pass `--regression_task True`.
- If your checkpoint is a multiclass model, pass `--mclassification_task <num_classes>`.
- ESM weights may be downloaded automatically on first run unless already cached in `TORCH_HOME`.
