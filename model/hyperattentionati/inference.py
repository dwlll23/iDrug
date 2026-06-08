import argparse
import os

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from utils import InferenceDataset, collate_batch, default_output_name, load_model


def main():
    parser = argparse.ArgumentParser(description="Run DTI inference from a CSV file.")
    parser.add_argument("--model_path", required=True, help="Path to a .pt checkpoint.")
    parser.add_argument("--input_csv", required=True, help="CSV with columns Protein and Ligand.")
    parser.add_argument("--pred_csv", default="", help="Output CSV path. Default: <input>_pred.csv")
    parser.add_argument("--emb_npy", default="", help="Output embedding path. Default: <input>_emb.npy")
    parser.add_argument("--batch_size", type=int, default=2, help="Inference batch size. CPU mode usually needs a small value.")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"], help="Inference device.")
    args = parser.parse_args()

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    pred_csv = args.pred_csv or default_output_name(args.input_csv, "pred.csv")
    emb_npy = args.emb_npy or default_output_name(args.input_csv, "emb.npy")

    dataset = InferenceDataset(args.input_csv)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False, num_workers=0, collate_fn=collate_batch)
    model = load_model(args.model_path, device)

    all_probs = []
    all_preds = []
    all_embs = []

    with torch.no_grad():
        for compounds, proteins in dataloader:
            compounds = compounds.to(device)
            proteins = proteins.to(device)
            logits, embeddings = model.forward_with_embedding(compounds, proteins)
            probs = F.softmax(logits, dim=1)
            all_probs.append(probs[:, 1].cpu().numpy())
            all_preds.append(torch.argmax(probs, dim=1).cpu().numpy())
            all_embs.append(embeddings.cpu().numpy())

    pred_df = dataset.df.copy()
    pred_df.insert(0, "sample_idx", np.arange(len(pred_df)))
    pred_df["pred_label"] = np.concatenate(all_preds)
    pred_df["pred_prob"] = np.concatenate(all_probs)
    pred_df.to_csv(pred_csv, index=False)

    emb_array = np.concatenate(all_embs, axis=0)
    np.save(emb_npy, emb_array)

    print(f"Model: {os.path.abspath(args.model_path)}")
    print(f"Input: {os.path.abspath(args.input_csv)}")
    print(f"Saved predictions to: {os.path.abspath(pred_csv)}")
    print(f"Saved embeddings to: {os.path.abspath(emb_npy)}")
    print(f"Embedding shape: {emb_array.shape}")


if __name__ == "__main__":
    main()
