import argparse
import json
import os

import numpy as np
import pandas as pd
import torch

from models.net import net
from utils import DataLoader, ProteinMoleculeDataset, ligand_init, protein_init


def str2bool(value):
    if isinstance(value, bool):
        return value
    value = str(value).strip().lower()
    if value in {'true', '1', 'yes', 'y'}:
        return True
    if value in {'false', '0', 'no', 'n'}:
        return False
    raise argparse.ArgumentTypeError(f'Invalid boolean value: {value}')


def sanitize_screen_df(df):
    df = df.copy()
    required_cols = ['Protein', 'Ligand']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f'Missing required columns: {missing_cols}')

    df = df.dropna(subset=required_cols)
    for col in required_cols:
        df[col] = df[col].astype(str).str.strip()
        df = df[df[col] != '']
        df = df[df[col].str.lower() != 'nan']
    return df.reset_index(drop=True)


def build_model(config, degree_dict, device):
    model = net(
        degree_dict['ligand_deg'],
        degree_dict['protein_deg'],
        mol_in_channels=config['params']['mol_in_channels'],
        prot_in_channels=config['params']['prot_in_channels'],
        prot_evo_channels=config['params']['prot_evo_channels'],
        hidden_channels=config['params']['hidden_channels'],
        pre_layers=config['params']['pre_layers'],
        post_layers=config['params']['post_layers'],
        aggregators=config['params']['aggregators'],
        scalers=config['params']['scalers'],
        total_layer=config['params']['total_layer'],
        K=config['params']['K'],
        heads=config['params']['heads'],
        dropout=config['params']['dropout'],
        dropout_attn_score=config['params']['dropout_attn_score'],
        regression_head=config['tasks']['regression_task'],
        classification_head=config['tasks']['classification_task'],
        multiclassification_head=config['tasks']['mclassification_task'],
        device=device,
    ).to(device)
    model.reset_parameters()
    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screenfile', type=str, required=True, help='CSV with Protein and Ligand columns')
    parser.add_argument('--result_path', type=str, required=True, help='Output folder for pred.csv and emb.npy')
    parser.add_argument('--trained_model_path', type=str, default='checkpoints', help='Folder with model.pt/degree.pt/config.json')
    parser.add_argument('--degree_path', type=str, default='', help='Optional explicit degree.pt path')
    parser.add_argument('--device', type=str, default='cpu')
    parser.add_argument('--batch_size', type=int, default=16)
    parser.add_argument('--classification_task', type=str2bool, default=None)
    parser.add_argument('--regression_task', type=str2bool, default=None)
    parser.add_argument('--mclassification_task', type=int, default=None)
    args = parser.parse_args()

    os.makedirs(args.result_path, exist_ok=True)
    device = torch.device(args.device)

    config_path = os.path.join(args.trained_model_path, 'config.json')
    degree_path = args.degree_path if args.degree_path else os.path.join(args.trained_model_path, 'degree.pt')
    model_path = os.path.join(args.trained_model_path, 'model.pt')

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    if args.classification_task is not None:
        config['tasks']['classification_task'] = args.classification_task
    if args.regression_task is not None:
        config['tasks']['regression_task'] = args.regression_task
    if args.mclassification_task is not None:
        config['tasks']['mclassification_task'] = args.mclassification_task

    degree_dict = torch.load(degree_path, map_location='cpu')
    model = build_model(config, degree_dict, device)
    model.load_state_dict(torch.load(model_path, map_location=device), strict=False)
    model.eval()

    screen_df = sanitize_screen_df(pd.read_csv(args.screenfile))
    screen_df['sample_id'] = np.arange(len(screen_df))
    protein_seqs = screen_df['Protein'].unique().tolist()
    ligand_smiles = screen_df['Ligand'].unique().tolist()

    protein_dict = protein_init(protein_seqs)
    ligand_dict = ligand_init(ligand_smiles)

    screen_df = screen_df[screen_df['Ligand'].isin(ligand_dict.keys())].reset_index(drop=True)
    screen_dataset = ProteinMoleculeDataset(screen_df, ligand_dict, protein_dict, device=args.device)
    screen_loader = DataLoader(
        screen_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        follow_batch=['mol_x', 'clique_x', 'prot_node_aa'],
    )

    pred_rows = []
    embeddings = []
    row_start = 0

    with torch.no_grad():
        for data in screen_loader:
            data = data.to(device)
            reg_pred, cls_pred, mcls_pred, _, _, _, attention_dict = model(
                mol_x=data.mol_x,
                mol_x_feat=data.mol_x_feat,
                bond_x=data.mol_edge_attr,
                atom_edge_index=data.mol_edge_index,
                clique_x=data.clique_x,
                clique_edge_index=data.clique_edge_index,
                atom2clique_index=data.atom2clique_index,
                residue_x=data.prot_node_aa,
                residue_evo_x=data.prot_node_evo,
                residue_edge_index=data.prot_edge_index,
                residue_edge_weight=data.prot_edge_weight,
                mol_batch=data.mol_x_batch,
                prot_batch=data.prot_node_aa_batch,
                clique_batch=data.clique_x_batch,
            )

            current_batch_size = len(data.mol_key)
            batch_rows = screen_df.iloc[row_start: row_start + current_batch_size].copy()
            row_start += current_batch_size

            if reg_pred is not None:
                batch_rows['predicted_binding_affinity'] = reg_pred.reshape(-1).detach().cpu().numpy()
            if cls_pred is not None:
                batch_rows['predicted_binary_interaction'] = torch.sigmoid(cls_pred).reshape(-1).detach().cpu().numpy()
            if mcls_pred is not None:
                mcls_prob = torch.softmax(mcls_pred, dim=-1).detach().cpu().numpy()
                for idx in range(mcls_prob.shape[1]):
                    batch_rows[f'predicted_class_{idx}'] = mcls_prob[:, idx]

            pred_rows.append(batch_rows)
            embeddings.append(attention_dict['interaction_fingerprint'].detach().cpu().numpy())

    pred_df = pd.concat(pred_rows, axis=0).reset_index(drop=True) if pred_rows else screen_df.iloc[0:0].copy()
    emb_array = np.concatenate(embeddings, axis=0) if embeddings else np.empty((0,))

    pred_df.to_csv(os.path.join(args.result_path, 'pred.csv'), index=False)
    np.save(os.path.join(args.result_path, 'emb.npy'), emb_array)


if __name__ == '__main__':
    main()
