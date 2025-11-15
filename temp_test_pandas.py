import pandas as pd
import sys

try:
    file_path = "C:\\dbms_2\\dbms_project\\scripts\\etl_pipeline\\university_records.csv"
    df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    print(f"Successfully read file. Shape: {df.shape}")
except FileNotFoundError:
    print(f"Error: File not found at {file_path}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

