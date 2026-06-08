import os

import numpy as np
import pandas as pd
from keras.layers import Conv1D, Dense, Dropout, Embedding, GlobalMaxPooling1D, Input
from keras.layers import concatenate
from keras.models import Model


CHARPROTSET = {
    "A": 1, "C": 2, "B": 3, "E": 4, "D": 5, "G": 6, "F": 7, "I": 8, "H": 9,
    "K": 10, "M": 11, "L": 12, "O": 13, "N": 14, "Q": 15, "P": 16, "S": 17,
    "R": 18, "U": 19, "T": 20, "W": 21, "V": 22, "Y": 23, "X": 24, "Z": 25,
}
CHARPROTLEN = 25

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
CHARISOSMILEN = 64


def label_smiles(smiles, max_len):
    encoded = np.zeros(max_len, dtype=np.int32)
    for idx, char in enumerate(str(smiles)[:max_len]):
        encoded[idx] = CHARISOSMISET.get(char, 0)
    return encoded


def label_sequence(sequence, max_len):
    encoded = np.zeros(max_len, dtype=np.int32)
    for idx, char in enumerate(str(sequence)[:max_len]):
        encoded[idx] = CHARPROTSET.get(char, 0)
    return encoded


def build_deepdta_model(max_smi_len=100, max_seq_len=1000, num_filters=32, filter_len_smi=4, filter_len_seq=8):
    drug_input = Input(shape=(max_smi_len,), dtype='int32', name='drug_input')
    protein_input = Input(shape=(max_seq_len,), dtype='int32', name='protein_input')

    drug = Embedding(CHARISOSMILEN + 1, 128, input_length=max_smi_len, name='drug_embedding')(drug_input)
    drug = Conv1D(num_filters, filter_len_smi, activation='relu', padding='valid', name='drug_conv1')(drug)
    drug = Conv1D(num_filters * 2, filter_len_smi, activation='relu', padding='valid', name='drug_conv2')(drug)
    drug = Conv1D(num_filters * 3, filter_len_smi, activation='relu', padding='valid', name='drug_conv3')(drug)
    drug = GlobalMaxPooling1D(name='drug_pooling')(drug)

    protein = Embedding(CHARPROTLEN + 1, 128, input_length=max_seq_len, name='protein_embedding')(protein_input)
    protein = Conv1D(num_filters, filter_len_seq, activation='relu', padding='valid', name='protein_conv1')(protein)
    protein = Conv1D(num_filters * 2, filter_len_seq, activation='relu', padding='valid', name='protein_conv2')(protein)
    protein = Conv1D(num_filters * 3, filter_len_seq, activation='relu', padding='valid', name='protein_conv3')(protein)
    protein = GlobalMaxPooling1D(name='protein_pooling')(protein)

    merged = concatenate([drug, protein], name='concat')
    fc1 = Dense(1024, activation='relu', name='fc1')(merged)
    drop1 = Dropout(0.1, name='dropout1')(fc1)
    fc2 = Dense(1024, activation='relu', name='fc2')(drop1)
    drop2 = Dropout(0.1, name='dropout2')(fc2)
    fc3 = Dense(512, activation='relu', name='fc3')(drop2)
    output = Dense(1, activation='sigmoid', name='output')(fc3)

    return Model(inputs=[drug_input, protein_input], outputs=[output])


def load_input_csv(input_csv):
    df = pd.read_csv(input_csv)
    required = {'Protein', 'Ligand'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError('Missing required columns: {}'.format(', '.join(sorted(missing))))

    output_df = df.copy().reset_index().rename(columns={'index': 'sample_index'})
    drugs = np.array([label_smiles(value, 100) for value in output_df['Ligand']])
    proteins = np.array([label_sequence(value, 1000) for value in output_df['Protein']])
    return output_df, drugs, proteins


def resolve_checkpoint_path(package_dir, checkpoint_name):
    if os.path.isabs(checkpoint_name) and os.path.exists(checkpoint_name):
        return checkpoint_name

    direct_path = os.path.join(package_dir, checkpoint_name)
    if os.path.exists(direct_path):
        return direct_path

    checkpoint_path = os.path.join(package_dir, 'checkpoints', checkpoint_name)
    if os.path.exists(checkpoint_path):
        return checkpoint_path

    raise FileNotFoundError('Checkpoint not found: {}'.format(checkpoint_name))
