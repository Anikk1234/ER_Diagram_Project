import argparse
import os
import re
import pandas as pd
from collections import defaultdict


def snake_case(s):
    # Lowercase, replace spaces and special chars with underscores, remove double underscores
    s = s.strip().lower()
    s = re.sub(r'[\s\-\/\.]+', '_', s)
    s = re.sub(r'[^a-z0-9_]', '', s)
    return re.sub(r'_+', '_', s).strip('_')


def deduplicate_columns(columns):
    """Ensures unique column names by appending .1, .2, etc where needed (like pandas does)"""
    seen = defaultdict(int)
    new_cols = []
    for col in columns:
        base = col
        while col in new_cols:
            seen[base] += 1
            col = f"{base}.{seen[base]}"
        new_cols.append(col)
    return new_cols


def load_and_clean(input_file):
    messages = []
    df = pd.read_csv(input_file, dtype=str, keep_default_na=False)
    messages.append(f"Initial shape: {df.shape}")
    
    original_cols = df.columns.tolist()
    cleaned_cols = [snake_case(col) for col in original_cols]
    final_cols = deduplicate_columns(cleaned_cols)
    df.columns = final_cols
    
    renamed_cols = [(orig, new) for orig, new in zip(original_cols, final_cols) if orig != new]
    if renamed_cols:
        messages.append(f"Renamed {len(renamed_cols)} columns to snake_case.")

    initial_rows = len(df)
    df.dropna(how='all', inplace=True)
    dropped_rows = initial_rows - len(df)
    if dropped_rows > 0:
        messages.append(f"Dropped {dropped_rows} fully empty rows.")

    context_cols = []
    col_counts = defaultdict(int)
    for c in final_cols:
        base = c.split('.')[0]
        col_counts[base] += 1
    for c in final_cols:
        base = c.split('.')[0]
        if col_counts[base] == 1:
            context_cols.append(c)
    
    if context_cols:
        messages.append(f"Identified {len(context_cols)} context columns for forward-filling.")
        df[context_cols] = df[context_cols].replace('', pd.NA).ffill()
    
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    messages.append("Stripped whitespace from all cells.")
    
    return df, messages

def run_cleaning(input_file, output_file):
    """Callable function for the GUI and for main()."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    run_messages = []
    run_messages.append(f"Loading and cleaning: {input_file}")
    
    df, clean_messages = load_and_clean(input_file)
    run_messages.extend(clean_messages)
    
    run_messages.append(f"Final cleaned shape: {df.shape}")
    df.to_csv(output_file, index=False)
    run_messages.append(f"Saved cleaned file to: {output_file}")
    return run_messages

def main():
    parser = argparse.ArgumentParser(
        description="Domain-agnostic data cleaning and 1NF transformer.")
    parser.add_argument('--input_file', required=True,
                        help='Path to raw noisy CSV input file')
    parser.add_argument('--output_file', required=True,
                        help='Path to write cleaned 1NF CSV')
    args = parser.parse_args()

    try:
        messages = run_cleaning(args.input_file, args.output_file)
        for message in messages:
            print(message)
    except FileNotFoundError:
        print(f"Error: The input file could not be found at {args.input_file}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
