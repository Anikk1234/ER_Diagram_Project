import pandas as pd
import os

def modify_hr_data(input_csv_path, output_csv_path):
    df = pd.read_csv(input_csv_path, dtype=str, keep_default_na=False)

    # Create a unique identifier for each department based on department_name, city, country
    df['department_key'] = df['department_name'] + '_' + df['city'] + '_' + df['country']
    
    # Create a mapping from department_key to a new department_id
    unique_departments = df[['department_name', 'city', 'country']].drop_duplicates().reset_index(drop=True)
    unique_departments['department_id'] = 'dept_' + (unique_departments.index + 1).astype(str)

    # Merge the new department_id back to the original DataFrame
    df = pd.merge(df, unique_departments, on=['department_name', 'city', 'country'], how='left')

    # Drop the temporary department_key column
    df = df.drop(columns=['department_key'])

    # Reorder columns to place department_id after employee_id for clarity
    cols = ['employee_id', 'department_id'] + [col for col in df.columns if col not in ['employee_id', 'department_id']]
    df = df[cols]

    # Save the modified DataFrame
    df.to_csv(output_csv_path, index=False)
    print(f"Modified data saved to {output_csv_path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(current_dir, '..', '..') # Adjust based on actual project structure
    
    input_path = os.path.join(project_root, 'data', 'cleaned', 'hr_cleaned.csv')
    output_path = os.path.join(project_root, 'data', 'cleaned', 'hr_cleaned.csv') # Overwrite original

    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    modify_hr_data(input_path, output_path)
