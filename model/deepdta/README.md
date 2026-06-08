# DeepDTA Predict Package

This folder contains the minimum files needed to run DeepDTA binary classification inference.

## Files

- `inference.py`: prediction entry point
- `utils.py`: model definition and sequence/SMILES encoding
- `requirements.txt`: minimal Python dependencies
- `checkpoints/`: bundled `.h5` model weights copied from this project
- `examples/`: example input and output location

## Input format

`input_csv` must contain:

- `Protein`
- `Ligand`

Optional columns such as `classification_label` are kept in the output.

## Run

```bash
python inference.py --input_csv examples/sample_input.csv --checkpoint human_1_best_model.h5 --output_csv examples/pred.csv
```

## Output

The output CSV keeps the original columns and adds:

- `sample_index`
- `pred_prob`

## Bundled checkpoints

- `human_1_best_model.h5`
- `human_2_best_model.h5`
- `gpcr_1_best_finetuned.h5`
- `gpcr_2_best_model.h5`
- `biosnap_1_best_finetuned.h5`
- `biosnap_2_best_finetuned.h5`
