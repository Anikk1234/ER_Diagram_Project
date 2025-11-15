import argparse
import os
import pandas as pd
import json
from itertools import combinations, chain
from collections import defaultdict


def is_fd(df, lhs, rhs):
    """Check if lhs -> rhs holds in the DataFrame (no data loss)."""
    # For each group of LHS values, check if RHS is always the same
    grouped = df.groupby(list(lhs))[rhs].nunique(dropna=False)
    return (grouped <= 1).all()


def powerset(iterable, max_size=None):
    """powerset([A,B,C], max_size=2) --> (A,) (B,) (C,) (A,B) (A,C) (B,C)"""
    s = list(iterable)
    for r in range(1, (max_size or len(s))+1):
        for combo in combinations(s, r):
            yield combo


def find_minimal_fds(df, max_lhs_size=2, sample_size=None, verbose=False, log_callback=None):
    """
    Find minimal (non-redundant, nontrivial) FDs up to max_lhs_size.
    Returns a list of (lhs_tuple, rhs_col).
    """
    if sample_size is not None and sample_size < len(df):
        if log_callback: log_callback(f"Sampling {sample_size} rows for FD discovery.")
        df = df.sample(sample_size, random_state=42)
    
    columns = list(df.columns)
    all_fds = []
    already_found = defaultdict(set)  # rhs -> set of minimal LHSs
    num_cols = len(columns)

    for i, rhs in enumerate(columns):
        if log_callback: 
            log_callback(f"[{i+1}/{num_cols}] Checking FDs for RHS: {rhs}")
        
        candidates = [c for c in columns if c != rhs]
        for sz in range(1, (max_lhs_size or len(candidates)) + 1):
            if log_callback: log_callback(f"  - Checking LHS of size {sz}...")
            for lhs in combinations(candidates, sz):
                # Pruning Step: Skip if a subset of this LHS already determines the RHS
                is_minimal = True
                for k in range(1, len(lhs)):
                    for sub in combinations(lhs, k):
                        if sub in already_found[rhs]:
                            is_minimal = False
                            break
                    if not is_minimal:
                        break
                if not is_minimal:
                    continue

                if is_fd(df, lhs, rhs):
                    all_fds.append((lhs, rhs))
                    already_found[rhs].add(lhs)
                    if log_callback: log_callback(f"    -> Found FD: {lhs} -> {rhs}")
    
    # Final cleanup for trivial FDs
    all_fds = [fd for fd in all_fds if fd[1] not in fd[0]]
    return all_fds


def group_fds(fds):
    groups = defaultdict(list)
    for lhs, rhs in fds:
        groups[lhs].append(rhs)
    return groups


def run_fd_discovery(input_file, output_file, max_lhs_size=None, sample_size=None, verbose=False):
    """Callable function for the GUI and for main()."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df = pd.read_csv(input_file, dtype=str, keep_default_na=False)
    
    if max_lhs_size is None:
        max_lhs_size = len(df.columns)

    messages = []
    def log_to_list(message):
        messages.append(message)

    log_to_list(f"Loaded: {input_file} ({df.shape[0]} rows, {df.shape[1]} columns)")
    log_to_list(f"Discovering minimal FDs (max LHS size={max_lhs_size})...")
    
    fds = find_minimal_fds(df, max_lhs_size=max_lhs_size, sample_size=sample_size, verbose=verbose, log_callback=log_to_list)
    
    log_to_list(f"Found {len(fds)} minimal, nontrivial FDs in total.")

    grouped = group_fds(fds)
    serializable = {','.join(lhs): rhs_list for lhs, rhs_list in grouped.items()}
    with open(output_file, 'w') as f:
        json.dump(serializable, f, indent=2)
    log_to_list(f"FDs (canonical cover) saved to {output_file}.")

    messages.append("\nFD Group Summary:")
    for lhs, rhs_list in serializable.items():
        messages.append(f"  {{{lhs}}} -> {{{ ', '.join(rhs_list) }}}")
        
    return messages


def main():
    parser = argparse.ArgumentParser(
        description=" FD discovery  (canonical cover, minimal and nontrivial).")
    parser.add_argument('--input_file', required=True,
                        help='Path to cleaned 1NF CSV')
    parser.add_argument('--output_file', required=True,
                        help='Path to output JSON of discovered FDs')
    parser.add_argument('--max_lhs_size', type=int, default=None,
                        help='Maximum size of LHS to search for FDs (None for all columns)')
    parser.add_argument('--sample_size', type=int, default=None,
                        help='Rows to sample for FD discovery (None=all)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print each FD as found')
    args = parser.parse_args()

    messages = run_fd_discovery(args.input_file, args.output_file, args.max_lhs_size, args.sample_size, args.verbose)
    for message in messages:
        print(message)


if __name__ == "__main__":
    main()
