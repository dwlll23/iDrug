# Portable Predictor

This folder is a minimal standalone inference package for the HyperAttentionDTI model.

## Files
- `inference.py`: command line entry for prediction
- `utils.py`: tokenizer, dataset loader, model definition, checkpoint loader
- `requirements.txt`: minimal dependencies
- `checkpoints/`: packaged model weights
- `examples/`: sample CSV for quick testing

## Input format
Input CSV must contain these columns:
- `Protein`
- `Ligand`

`classification_label` is optional for inference and will be preserved if present.

## Quick start
Install dependencies:

```bash
pip install -r requirements.txt
```

Run inference:

```bash
python inference.py \
  --model_path checkpoints/human_random.pt \
  --input_csv examples/sample_input.csv \
  --pred_csv examples/sample_pred.csv \
  --emb_npy examples/sample_emb.npy \
  --batch_size 2
```

## Outputs
- `pred_csv`: original input plus `sample_idx`, `pred_label`, `pred_prob`
- `emb_npy`: embedding array with shape `(N, 512)`

## Notes
- CPU inference should usually use a small `--batch_size`, such as `1` or `2`
- `--device auto` uses CUDA when available, otherwise CPU
- Available packaged checkpoints are under `checkpoints/`
