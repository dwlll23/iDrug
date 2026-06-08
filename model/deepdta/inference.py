import argparse
import os

from utils import build_deepdta_model, load_input_csv, resolve_checkpoint_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_csv', required=True, help='CSV with Protein and Ligand columns.')
    parser.add_argument('--checkpoint', required=True, help='Checkpoint filename in checkpoints/ or a full path.')
    parser.add_argument('--output_csv', default='pred.csv', help='Prediction output CSV path.')
    parser.add_argument('--batch_size', type=int, default=256)
    args = parser.parse_args()

    package_dir = os.path.dirname(os.path.abspath(__file__))
    checkpoint_path = resolve_checkpoint_path(package_dir, args.checkpoint)

    model = build_deepdta_model()
    model.load_weights(checkpoint_path, by_name=True, skip_mismatch=True)

    output_df, drugs, proteins = load_input_csv(args.input_csv)
    predictions = model.predict([drugs, proteins], batch_size=args.batch_size).flatten()

    output_df['pred_prob'] = predictions
    output_df.to_csv(args.output_csv, index=False)
    print(args.output_csv)


if __name__ == '__main__':
    main()
