import os

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset


CHARISOSMISET = {
    "#": 29, "%": 30, ")": 31, "(": 1, "+": 32, "-": 33, "/": 34, ".": 2,
    "1": 35, "0": 3, "3": 36, "2": 4, "5": 37, "4": 5, "7": 38, "6": 6,
    "9": 39, "8": 7, "=": 40, "A": 41, "@": 8, "C": 42, "B": 9, "E": 43,
    "D": 10, "G": 44, "F": 11, "I": 45, "H": 12, "K": 46, "M": 47, "L": 13,
    "O": 48, "N": 14, "P": 15, "S": 49, "R": 16, "U": 50, "T": 17, "W": 51,
    "V": 18, "Y": 52, "[": 53, "Z": 19, "]": 54, "\\": 20, "a": 55, "c": 56,
    "b": 21, "e": 57, "d": 22, "g": 58, "f": 23, "i": 59, "h": 24, "m": 60,
    "l": 25, "o": 61, "n": 26, "s": 62, "r": 27, "u": 63, "t": 28, "y": 64,
}

CHARPROTSET = {
    "A": 1, "C": 2, "B": 3, "E": 4, "D": 5, "G": 6, "F": 7, "I": 8, "H": 9,
    "K": 10, "M": 11, "L": 12, "O": 13, "N": 14, "Q": 15, "P": 16, "S": 17,
    "R": 18, "U": 19, "T": 20, "W": 21, "V": 22, "Y": 23, "X": 24, "Z": 25,
}


class HyperParameters:
    def __init__(self):
        self.protein_kernel = [4, 8, 12]
        self.drug_kernel = [4, 6, 8]
        self.conv = 40
        self.char_dim = 64


def label_smiles(line, smi_ch_ind, max_smi_len=100):
    encoded = np.zeros(max_smi_len, dtype=np.int64)
    for i, ch in enumerate(line[:max_smi_len]):
        encoded[i] = smi_ch_ind.get(ch, 0)
    return encoded


def label_sequence(line, prot_ch_ind, max_seq_len=1000):
    encoded = np.zeros(max_seq_len, dtype=np.int64)
    for i, ch in enumerate(line[:max_seq_len]):
        encoded[i] = prot_ch_ind.get(ch, 0)
    return encoded


class InferenceDataset(Dataset):
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        required_columns = {"Protein", "Ligand"}
        missing = required_columns - set(self.df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        compound = torch.from_numpy(label_smiles(str(row["Ligand"]), CHARISOSMISET, 100))
        protein = torch.from_numpy(label_sequence(str(row["Protein"]), CHARPROTSET, 1000))
        return compound, protein


def collate_batch(batch):
    compounds, proteins = zip(*batch)
    return torch.stack(compounds), torch.stack(proteins)


class AttentionDTI(nn.Module):
    def __init__(self, hp, protein_max_length=1000, drug_max_length=100):
        super().__init__()
        self.dim = hp.char_dim
        self.conv = hp.conv
        self.drug_max_length = drug_max_length
        self.drug_kernel = hp.drug_kernel
        self.protein_max_length = protein_max_length
        self.protein_kernel = hp.protein_kernel

        self.protein_embed = nn.Embedding(26, self.dim, padding_idx=0)
        self.drug_embed = nn.Embedding(65, self.dim, padding_idx=0)
        self.Drug_CNNs = nn.Sequential(
            nn.Conv1d(in_channels=self.dim, out_channels=self.conv, kernel_size=self.drug_kernel[0]),
            nn.ReLU(),
            nn.Conv1d(in_channels=self.conv, out_channels=self.conv * 2, kernel_size=self.drug_kernel[1]),
            nn.ReLU(),
            nn.Conv1d(in_channels=self.conv * 2, out_channels=self.conv * 4, kernel_size=self.drug_kernel[2]),
            nn.ReLU(),
        )
        self.Drug_max_pool = nn.MaxPool1d(
            self.drug_max_length - self.drug_kernel[0] - self.drug_kernel[1] - self.drug_kernel[2] + 3
        )
        self.Protein_CNNs = nn.Sequential(
            nn.Conv1d(in_channels=self.dim, out_channels=self.conv, kernel_size=self.protein_kernel[0]),
            nn.ReLU(),
            nn.Conv1d(in_channels=self.conv, out_channels=self.conv * 2, kernel_size=self.protein_kernel[1]),
            nn.ReLU(),
            nn.Conv1d(in_channels=self.conv * 2, out_channels=self.conv * 4, kernel_size=self.protein_kernel[2]),
            nn.ReLU(),
        )
        self.Protein_max_pool = nn.MaxPool1d(
            self.protein_max_length - self.protein_kernel[0] - self.protein_kernel[1] - self.protein_kernel[2] + 3
        )
        self.attention_layer = nn.Linear(self.conv * 4, self.conv * 4)
        self.protein_attention_layer = nn.Linear(self.conv * 4, self.conv * 4)
        self.drug_attention_layer = nn.Linear(self.conv * 4, self.conv * 4)
        self.dropout1 = nn.Dropout(0.1)
        self.dropout2 = nn.Dropout(0.1)
        self.dropout3 = nn.Dropout(0.1)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()
        self.leaky_relu = nn.LeakyReLU()
        self.fc1 = nn.Linear(self.conv * 8, 1024)
        self.fc2 = nn.Linear(1024, 1024)
        self.fc3 = nn.Linear(1024, 512)
        self.out = nn.Linear(512, 2)

    def forward_with_embedding(self, drug, protein):
        drug_embed = self.drug_embed(drug).permute(0, 2, 1)
        protein_embed = self.protein_embed(protein).permute(0, 2, 1)

        drug_conv = self.Drug_CNNs(drug_embed)
        protein_conv = self.Protein_CNNs(protein_embed)

        drug_att = self.drug_attention_layer(drug_conv.permute(0, 2, 1))
        protein_att = self.protein_attention_layer(protein_conv.permute(0, 2, 1))

        d_att_layers = torch.unsqueeze(drug_att, 2).repeat(1, 1, protein_conv.shape[-1], 1)
        p_att_layers = torch.unsqueeze(protein_att, 1).repeat(1, drug_conv.shape[-1], 1, 1)
        atten_matrix = self.attention_layer(self.relu(d_att_layers + p_att_layers))
        compound_atte = torch.mean(atten_matrix, 2)
        protein_atte = torch.mean(atten_matrix, 1)
        compound_atte = self.sigmoid(compound_atte.permute(0, 2, 1))
        protein_atte = self.sigmoid(protein_atte.permute(0, 2, 1))

        drug_conv = drug_conv * 0.5 + drug_conv * compound_atte
        protein_conv = protein_conv * 0.5 + protein_conv * protein_atte

        drug_conv = self.Drug_max_pool(drug_conv).squeeze(2)
        protein_conv = self.Protein_max_pool(protein_conv).squeeze(2)

        pair = torch.cat([drug_conv, protein_conv], dim=1)
        pair = self.dropout1(pair)
        fully1 = self.leaky_relu(self.fc1(pair))
        fully1 = self.dropout2(fully1)
        fully2 = self.leaky_relu(self.fc2(fully1))
        fully2 = self.dropout3(fully2)
        embedding = self.leaky_relu(self.fc3(fully2))
        logits = self.out(embedding)
        return logits, embedding


def load_model(model_path, device):
    hp = HyperParameters()
    model = AttentionDTI(hp).to(device)
    checkpoint = torch.load(model_path, map_location=device)
    state_dict = checkpoint["state_dict"] if isinstance(checkpoint, dict) and "state_dict" in checkpoint else checkpoint
    model.load_state_dict(state_dict)
    model.eval()
    return model


def default_output_name(input_csv, suffix):
    stem = os.path.splitext(os.path.basename(input_csv))[0]
    return f"{stem}_{suffix}"
