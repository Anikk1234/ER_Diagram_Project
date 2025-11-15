import argparse
import os
import json
import pandas as pd
from itertools import combinations


def load_known_keys(path):
    """Optional: Load known/likely keys (one per line, comma-separated attributes)."""
    if not path or not os.path.exists(path):
        return []
    with open(path) as f:
        return [tuple(line.strip().split(',')) for line in f if line.strip()]


def attribute_closure(attrs, fds, memo=None):
    """Compute closure of a set of attributes under given FDs (with memoization)."""
    attrs = frozenset(attrs)
    if memo is not None and attrs in memo:
        return memo[attrs]
    closure = set(attrs)
    changed = True
    while changed:
        changed = False
        for lhs, rhses in fds.items():
            lhs_set = set(lhs.split(','))
            if lhs_set.issubset(closure):
                for rhs in rhses:
                    if rhs not in closure:
                        closure.add(rhs)
                        changed = True
    if memo is not None:
        memo[attrs] = closure
    return closure


def find_candidate_keys(attributes, fds, max_key_size=3, known_keys=None, log_callback=None):
    """Find minimal candidate keys up to max_key_size, using closure and early pruning."""
    all_attrs = set(attributes)
    keys = []
    memo = {}

    if log_callback: log_callback(f"Searching for candidate keys (max size {max_key_size})...")

    # Step 1: Check known keys first
    if known_keys:
        if log_callback: log_callback(f"Checking {len(known_keys)} provided known keys first.")
        for key in known_keys:
            closure = attribute_closure(key, fds, memo)
            if closure == all_attrs:
                is_minimal = not any(set(k).issubset(key) for k in keys)
                if is_minimal:
                    keys.append(tuple(key))
                    if log_callback: log_callback(f"  - Confirmed known key: {key}")
    
    # Step 2: Brute force small subsets
    if log_callback: log_callback("Brute-forcing attribute combinations.")
    for r in range(1, min(max_key_size, len(attributes)) + 1):
        if log_callback: log_callback(f"  - Checking keys of size {r}...")
        for subset in combinations(attributes, r):
            subset_set = set(subset)
            # Minimality check: skip if it's a superset of a key we already found
            if any(set(k).issubset(subset_set) for k in keys):
                continue
            
            closure = attribute_closure(subset_set, fds, memo)
            if closure == all_attrs:
                keys.append(subset)
                if log_callback: log_callback(f"    -> Found candidate key: {subset}")
    
    if log_callback: log_callback(f"Found {len(keys)} candidate keys in total.")
    return keys

def nf_analysis(attributes, candidate_keys, fds, log_callback=None):
    """Strict 2NF and 3NF violation analysis using all candidate keys."""
    if log_callback: log_callback("Analyzing for 2NF and 3NF violations...")
    prime_attributes = set()
    for key in candidate_keys:
        prime_attributes.update(key)
    if log_callback: log_callback(f"  - Prime attributes: {prime_attributes}")

    violations_2nf = []
    violations_3nf = []
    all_keys_set = [set(k) for k in candidate_keys]

    for lhs_str, rhses in fds.items():
        lhs = set(lhs_str.split(','))
        for rhs in rhses:
            if rhs in lhs: continue # Skip trivial dependencies

            # 2NF Check: A proper subset of a candidate key determines a non-prime attribute.
            is_2nf_violation = False
            for ck_set in all_keys_set:
                if lhs < ck_set and rhs not in prime_attributes:
                    violations_2nf.append((lhs_str, rhs))
                    if log_callback: log_callback(f"  - 2NF VIOLATION: {lhs_str} -> {rhs} (partial dependency on key {ck_set})")
                    is_2nf_violation = True
                    break # Found one violation for this FD, no need to check other keys
            if is_2nf_violation: continue

            # 3NF Check: A non-key attribute determines another non-key attribute.
            # (LHS is not a superkey) AND (RHS is not a prime attribute)
            is_superkey = any(ck_set.issubset(lhs) for ck_set in all_keys_set)
            if not is_superkey and rhs not in prime_attributes:
                violations_3nf.append((lhs_str, rhs))
                if log_callback: log_callback(f"  - 3NF VIOLATION: {lhs_str} -> {rhs} (transitive dependency)")

    if log_callback: log_callback(f"Found {len(violations_2nf)} 2NF violations and {len(violations_3nf)} 3NF violations.")
    return violations_2nf, violations_3nf

def run_key_analysis(input_file, fd_file, output_file, max_key_size=3, known_keys_path=None):
    """Callable function for the GUI and for main()."""
    messages = []
    def log_to_list(message):
        messages.append(message)

    log_to_list(f"Loading data from {input_file} and FDs from {fd_file}")
    df = pd.read_csv(input_file, dtype=str, keep_default_na=False)
    with open(fd_file) as f:
        fds = json.load(f)

    attributes = list(df.columns)
    log_to_list(f"Attributes for analysis: {attributes}")
    known_keys = load_known_keys(known_keys_path)
    
    keys = find_candidate_keys(
        attributes, fds, max_key_size=max_key_size, known_keys=known_keys, log_callback=log_to_list)
    
    violations_2nf, violations_3nf = nf_analysis(attributes, keys, fds, log_callback=log_to_list)

    result = {
        "attributes": attributes,
        "candidate_keys": [list(k) for k in keys],
        "violations_2nf": violations_2nf,
        "violations_3nf": violations_3nf,
    }
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    log_to_list(f"Saved analysis results to {output_file}")

    # Final summary message
    summary_message = f"\nAnalysis Complete: Found {len(keys)} Candidate Keys, {len(violations_2nf)} 2NF violations, and {len(violations_3nf)} 3NF violations."
    messages.append(summary_message)
    return messages


def main():
    parser = argparse.ArgumentParser(
        description="Efficient real-world key discovery and 2NF/3NF analysis.")
    parser.add_argument('--input_file', required=True)
    parser.add_argument('--fd_file', required=True)
    parser.add_argument('--output_file', required=True)
    parser.add_argument('--max_key_size', type=int, default=3,
                        help='Max candidate key size to check (default=3)')
    parser.add_argument('--known_keys', type=str, default=None,
                        help='Optional: path to file with known keys, one per line')
    args = parser.parse_args()

    messages = run_key_analysis(args.input_file, args.fd_file, args.output_file, args.max_key_size, args.known_keys)
    for message in messages:
        print(message)


if __name__ == "__main__":
    main()
