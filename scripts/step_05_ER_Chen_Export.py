import json
import argparse
import subprocess

def load_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_dot(dot_str, filename):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(dot_str)

def make_entity(entity_name, attributes, pk_attributes):
    """Creates a styled HTML-like label for an entity."""
    pk_icon = '&#128273;'  # Unicode key icon
    
    header_bg_color = "#4CAF50"  # Green
    entity_bg_color = "#FFFFFF"  # White
    font_color = "#333333"
    pk_font_color = "#D32F2F" # Red

    label = f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" BGCOLOR="{entity_bg_color}" STYLE="ROUNDED">'
    label += f'<TR><TD COLSPAN="2" BGCOLOR="{header_bg_color}" ALIGN="CENTER"><FONT COLOR="white"><B>{entity_name.upper()}</B></FONT></TD></TR>'
    
    for attr in attributes:
        align = 'LEFT'
        attr_val = attr
        # Bold and color primary keys
        if attr in pk_attributes:
            attr_val = f'<FONT COLOR="{pk_font_color}"><B>{attr}</B></FONT> {pk_icon}'
        
        label += f'<TR><TD ALIGN="{align}" PORT="{attr}" CELLPADDING="5">{attr_val}</TD></TR>'
    
    label += '</TABLE>>'
    return f'"{entity_name}" [label={label}];'

def infer_relationships(relations):
    """Infers relationships based on shared primary keys."""
    relationships = []
    for i, tbl1 in enumerate(relations):
        for j, tbl2 in enumerate(relations):
            if i >= j:
                continue

            pk1 = set(tbl1.get("primary_key", []))
            pk2 = set(tbl2.get("primary_key", []))
            attrs1 = set(tbl1["attributes"])
            attrs2 = set(tbl2["attributes"])

            # Relationship exists if one table's PK is a subset of another table's attributes (FK)
            # and the PKs are not identical (not the same table)
            fk_1_in_2 = pk1 and pk1.issubset(attrs2) and pk1 != attrs2
            fk_2_in_1 = pk2 and pk2.issubset(attrs1) and pk2 != attrs1

            if fk_1_in_2 and fk_2_in_1:
                if pk1 == pk2:
                    continue
                else:
                    rel_name = f"{tbl1['table']}_to_{tbl2['table']}"
                    relationships.append({
                        "name": rel_name, # <--- ERROR HERE
                        "from": tbl1["table"],
                        "to": tbl2["table"],
                        "relationship_type": "many-to-many"
                    })
            elif fk_1_in_2:
                rel_name = f"{tbl1['table']}_to_{tbl2['table']}"
                relationships.append({
                    "name": rel_name,
                    "from": tbl1["table"],
                    "to": tbl2["table"],
                    "relationship_type": "one-to-many"
                })
            elif fk_2_in_1:
                rel_name = f"{tbl2['table']}_to_{tbl1['table']}"
                relationships.append({
                    "name": rel_name,
                    "from": tbl2["table"],
                    "to": tbl1["table"],
                    "relationship_type": "one-to-many"
                })
    return relationships



def run_er_export(summary_file, output_dot):
    """Callable function for the GUI and for main()."""
    messages = []
    def log(msg): messages.append(msg)

    log(f"Generating ER Diagram DOT file from {summary_file}")
    summary = load_json(summary_file)
    relations = summary["relations"]
    log(f"  - Loaded {len(relations)} relations.")

    dot = [
        'digraph ER {',
        '  graph [bgcolor="#ECEFF1", fontname="Helvetica", fontsize=12, rankdir=LR, splines=ortho];',
        '  node [fontname="Helvetica", fontsize=10, shape=plain];',
        '  edge [fontname="Helvetica", fontsize=9, color="#37474F"];',
        ''
    ]

    # Create Entities
    log("\nCreating entities...")
    for tbl in relations:
        pk_attributes = tbl.get("primary_key", [])
        dot.append(make_entity(tbl["table"], tbl["attributes"], pk_attributes))
        log(f"  - Created entity: {tbl['table']} with PK {pk_attributes}")

    # Create Relationships
    log("\nInferring relationships...")
    relationships = infer_relationships(relations)
    log(f"  - Inferred {len(relationships)} relationships.")
    for rel in relationships:
        from_entity = rel["from"]
        to_entity = rel["to"]
        relationship_type = rel["relationship_type"]

        arrowtail = "normal"
        arrowhead = "normal"

        if relationship_type == "one-to-many":
            arrowhead = "crow"
        elif relationship_type == "many-to-one":
            arrowtail = "crow"
        elif relationship_type == "many-to-many":
            arrowtail = "crow"
            arrowhead = "crow"

        dot.append(f'"{from_entity}" -> "{to_entity}" [arrowtail="{arrowtail}", arrowhead="{arrowhead}"];')
        log(f"  - Created relationship: {from_entity} ({relationship_type}) -> {to_entity}")

    dot.append("}")
    save_dot("\n".join(dot), output_dot)
    log(f"\nSuccessfully saved DOT file to {output_dot}")

    # Convert DOT to PNG
    output_png = output_dot.replace(".dot", ".png")
    try:
        subprocess.run(["dot", "-Tpng", output_dot, "-o", output_png], check=True)
        log(f"Successfully generated ER diagram PNG: {output_png}")
    except subprocess.CalledProcessError as e:
        log(f"Error generating PNG from DOT: {e}")
    except FileNotFoundError:
        log("Error: 'dot' command not found. Please install Graphviz.")
    
    return messages

def main():
    parser = argparse.ArgumentParser(
        description="Generate a styled Chen/Crow's Foot ER diagram from 3NF decomposition.")
    parser.add_argument("--summary_file", required=True,
                        help="JSON summary file listing relations and candidate keys")
    parser.add_argument("--output_dot", required=True,
                        help="Output DOT filename")
    args = parser.parse_args()

    messages = run_er_export(args.summary_file, args.output_dot)
    for message in messages:
        print(message)


if __name__ == "__main__":
    main()
