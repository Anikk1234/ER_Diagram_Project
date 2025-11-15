import argparse
import os
import json
import pandas as pd
from collections import defaultdict

def load_json(path):
    """Loads a JSON file with basic error handling."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at '{path}'.")
        raise
    except json.JSONDecodeError:
        print(f"Error: Malformed JSON in file '{path}'.")
        raise

def make_3nf_relations(fds):
    """For each FD, create a relation with attributes and the LHS as the key."""
    relations = []
    for lhs_str, rhses in fds.items():
        lhs = set(lhs_str.split(','))
        attrs = lhs.union(rhses)
        relations.append({'attributes': attrs, 'primary_key': lhs})
    return relations

def ensure_key_in_relations(relations, candidate_keys):
    """Add a relation for the first candidate key if no relation contains a key."""
    key_covered = False
    for key in candidate_keys:
        key_set = set(key)
        if any(key_set.issubset(rel['attributes']) for rel in relations):
            key_covered = True
            break
    if not key_covered and candidate_keys:
        first_key = set(candidate_keys[0])
        relations.append({'attributes': first_key, 'primary_key': first_key})
    return relations

def synthesis_relations(relations, log_callback=None):
    """Synthesizes a minimal set of 3NF relations by merging and removing redundancy."""
    def log(msg):
        if log_callback:
            log_callback(msg)

    log("  -> Starting synthesis...")
    log(f"  -> Initial relations count: {len(relations)}")

    # 1. Merge relations with the same primary key
    merged_by_key = defaultdict(set)
    for rel in relations:
        pk = frozenset(rel['primary_key'])
        merged_by_key[pk].update(rel['attributes'])
    
    log(f"  -> Merged into {len(merged_by_key)} groups by primary key.")

    merged_relations = []
    for pk, attrs in merged_by_key.items():
        merged_relations.append({'primary_key': set(pk), 'attributes': attrs})

    # 2. Aggressively merge relations
    final_relations = []
    for rel1 in merged_relations:
        merged = False
        for i, rel2 in enumerate(final_relations):
            # if rel1's pk is a subset of rel2's pk, merge into rel2
            if rel1['primary_key'].issubset(rel2['primary_key']):
                final_relations[i]['attributes'].update(rel1['attributes'])
                merged = True
                break
            # if rel2's pk is a subset of rel1's pk, merge into rel1 and replace rel2
            elif rel2['primary_key'].issubset(rel1['primary_key']):
                rel1['attributes'].update(rel2['attributes'])
                final_relations[i] = rel1
                merged = True
                break
        if not merged:
            final_relations.append(rel1)

    log(f"  -> Final relations count: {len(final_relations)} (after aggressive merging)")

    # 3. Ensure all original attributes are covered
    all_attributes_in_final_relations = set()
    for rel in final_relations:
        all_attributes_in_final_relations.update(rel['attributes'])

    all_attributes_in_initial_relations = set()
    for rel in relations:
        all_attributes_in_initial_relations.update(rel['attributes'])

    missing_attributes = all_attributes_in_initial_relations - all_attributes_in_final_relations
    if missing_attributes:
        log(f"  -> Found {len(missing_attributes)} missing attributes. Creating a new relation for them.")
        # Find a candidate key to be the primary key of the new relation
        candidate_keys = [rel['primary_key'] for rel in relations]
        new_pk = set()
        for key in sorted(list(candidate_keys), key=len):
            if set(key).issubset(missing_attributes):
                new_pk = set(key)
                break
        if not new_pk:
            new_pk = set(sorted(list(missing_attributes))[0])

        final_relations.append({'primary_key': new_pk, 'attributes': missing_attributes})
        log(f"  -> Added new relation with PK {new_pk} for missing attributes.")

    for rel in final_relations:
        log(f"    - Created final relation with PK {sorted(list(rel['primary_key']))}: {len(rel['attributes'])} attributes")

    return final_relations

def project_to_relation(df, attrs):
    """Project dataframe to given attributes, dropping duplicate rows."""
    cols = [col for col in df.columns if col in attrs]
    missing_cols = set(attrs) - set(cols)
    if missing_cols:
        print(f"Warning: Some attributes in relations were not found in the CSV: {sorted(list(missing_cols))}")
    return df[cols].drop_duplicates()

def run_3nf_decomposition(input_file, fd_file, keys_file, out_dir):
    """Callable function for the GUI and for main()."""
    messages = []
    def log(msg):
        messages.append(msg)
        print(msg)

    log("Starting 3NF decomposition.")
    os.makedirs(out_dir, exist_ok=True)

    try:
        log("Loading required files...")
        df = pd.read_csv(input_file, dtype=str, keep_default_na=False)
        fds = load_json(fd_file)
        keys_nf = load_json(keys_file)
        candidate_keys = keys_nf["candidate_keys"]

        log(f"  - Loaded {len(fds)} FD groups and {len(candidate_keys)} candidate keys.")

        log("\nStep 1: Creating initial relations from FDs.")
        relations = make_3nf_relations(fds)

        log("\nStep 2: Ensuring a candidate key is preserved.")
        relations = ensure_key_in_relations(relations, candidate_keys)

        log("\nStep 3: Synthesizing final relations by merging.")
        final_relations = synthesis_relations(relations, log_callback=log)
        log(f"  - Created {len(final_relations)} final relations.")

        log("\nStep 4: Projecting data and saving decomposed tables.")
        rel_list = []
        for i, rel_data in enumerate(final_relations):
            attrs = rel_data['attributes']
            pk = rel_data['primary_key']
            rel_name = f"table_{i + 1}"
            rel_path = os.path.join(out_dir, f"{rel_name}.csv")
            tdf = project_to_relation(df, attrs)
            tdf.to_csv(rel_path, index=False)
            rel_info = {
                "table": rel_name,
                "attributes": sorted(list(attrs)),
                "primary_key": sorted(list(pk)),
                "num_rows": len(tdf),
                "csv": rel_path
            }
            rel_list.append(rel_info)
            log(f"  - Saved {rel_name}: {len(tdf)} rows, {len(attrs)} cols, PK: {sorted(list(pk))}")

        log("\nStep 5: Saving decomposition summary.")
        summary = {
            "relations": rel_list,
            "candidate_keys": candidate_keys
        }
        summary_path = os.path.join(out_dir, "3nf_decomposition_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        log(f"  - Summary saved to {summary_path}")

        log("\n3NF decomposition process completed.")

    except Exception as e:
        log(f"ERROR: Process failed. {str(e)}")

    return messages

def main():
    parser = argparse.ArgumentParser(
        description="3NF decomposition with Bernstein's synthesis algorithm.")
    parser.add_argument('--input_file', required=True)
    parser.add_argument('--fd_file', required=True)
    parser.add_argument('--keys_file', required=True)
    parser.add_argument('--out_dir', required=True)
    args = parser.parse_args()
    run_3nf_decomposition(args.input_file, args.fd_file, args.keys_file, args.out_dir)

if __name__ == "__main__":
    main()