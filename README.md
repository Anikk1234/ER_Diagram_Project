# Documentation: Database Normalization ETL Pipeline

## 1. Project Overview

This project is a graphical desktop application that provides a full ETL (Extract, Transform, Load) pipeline for database normalization. It allows a user to load a denormalized dataset from a single CSV file and guides them through the process of cleaning the data, discovering functional dependencies, identifying candidate keys, decomposing the schema into Third Normal Form (3NF), and visualizing the final, normalized schema as an Entity-Relationship (ER) Diagram.

The application is built using Python with the PyQt5 framework for the graphical user interface.

---

## 2. Features

*   **Interactive ETL Workflow**: A drag-and-drop canvas to visualize and execute the ETL pipeline step-by-step.
*   **Load CSV Data**: Load a local CSV file as the starting point for the pipeline.
*   **Data Cleaning (1NF)**: Performs basic data cleaning to ensure the data is in First Normal Form.
*   **Functional Dependency (FD) Discovery**: Analyzes the data to find functional dependencies between columns.
*   **Candidate Key (CK) Analysis**: Identifies all candidate keys based on the discovered FDs.
*   **3NF Decomposition**: Decomposes the initial table into a set of smaller tables that satisfy Third Normal Form (3NF).
*   **ER Diagram Generation**: Generates and displays a Chen-notation Entity-Relationship Diagram representing the final, normalized database schema.
*   **Data Export**: Allows downloading the discovered FDs, candidate keys, final decomposed tables (as a ZIP archive), and the ER Diagram image.
*   **Performance Monitoring**: A performance report to track the execution time and status of each ETL step.

---

## 3. GUI Tabs

The application's main window is organized into several tabs, each providing a different view of the ETL process and its results.

*   **Canvas**: This is the main interactive tab where you can drag and drop the ETL steps to build and visualize the workflow. This provides a clear, graphical representation of the pipeline's execution.
*   **Performance Report**: This tab displays a table with performance metrics for each ETL step that has been run. It includes the step name, execution time in seconds, status (Success or Error), and a timestamp.
*   **Functional Dependencies**: After running the "Find FDs" step, this tab will be populated with a table showing the discovered functional dependencies. The table has two columns: "LHS" (Left-Hand Side) and "RHS" (Right-Hand Side) of the dependency.
*   **Candidate Keys**: Once the "Find Candidate Keys" step is complete, this tab will display a list of the candidate keys found in the dataset.
*   **Decomposed Tables**: This tab shows the result of the 3NF decomposition. It displays each of the new, normalized tables as a separate group box, with a list of its attributes. Primary key attributes are highlighted with a key icon (🔑).
*   **ER Diagram**: After the "Generate ERD" step, this tab will display the generated Entity-Relationship Diagram. You can zoom in and out and pan around the diagram to inspect the final database schema.

---

## 4. ETL Workflow

The ETL (Extract, Transform, Load) process in this application is designed as a sequential workflow. Each step builds upon the previous one, and the GUI guides the user through the process.

1.  **Extract: Load CSV**: The first step is to load a denormalized dataset from a CSV file. The application reads the data into a pandas DataFrame, which is the primary data structure used throughout the pipeline.

2.  **Transform: Data Cleaning (1NF)**: The loaded data is cleaned to ensure it conforms to First Normal Form (1NF). This step involves stripping leading and trailing whitespace from all string values to ensure data consistency. The cleaned data is saved to a new CSV file in the `data/cleaned` directory.

3.  **Transform: Functional Dependency Discovery**: The application analyzes the cleaned data to discover functional dependencies (FDs). An FD (e.g., `A -> B`) exists if the value of attribute `A` uniquely determines the value of attribute `B`. This is a computationally intensive step that involves checking combinations of columns. The discovered FDs are saved to a JSON file.

4.  **Transform: Candidate Key Analysis**: Using the discovered FDs, the application identifies the candidate keys of the table. A candidate key is a minimal set of attributes that uniquely identifies each row in the table. This step also analyzes the FDs to detect any violations of Second Normal Form (2NF) and Third Normal Form (3NF). The results are saved to a JSON file.

5.  **Transform: 3NF Decomposition**: Based on the FDs and candidate keys, the original table is decomposed into a set of smaller tables that are in Third Normal Form (3NF). This process eliminates data redundancy and improves data integrity. The decomposed tables are saved as individual CSV files in a dedicated directory, and a summary of the decomposition is saved to a JSON file.

6.  **Load: ER Diagram Generation**: The final step is to visualize the new, normalized database schema. The application generates an Entity-Relationship (ER) Diagram in Chen's notation. The diagram shows the decomposed tables as entities, their attributes, and the relationships between them. The ER diagram is saved as a PNG image.

---

## 5. Project Structure

The project is organized into the following main directories and files:

```
.etl_pipeline/
|-- data/                     # Directory for all data files
|   |-- cleaned/              # Output for cleaned data and analysis files (FDs, CKs)
|   |-- decomposed/           # Output for decomposed 3NF tables and ER diagrams
|   `-- raw/                  # (Optional) For storing original raw data
|-- scripts/                  # Directory for all backend Python scripts
|   |-- step_01_data_cleaning.py
|   |-- step_02_fd_discovery.py
|   |-- step_03_key_nf_analysis.py
|   |-- step_04_3nf_decomposition.py
|   `-- step_05_ER_Chen_Export.py
|-- main_app_qt.py            # The main entry point for the PyQt5 GUI application
|-- requirements.txt          # A list of Python packages required for the project
|-- university_enrollment_sample.csv # A sample CSV file to demonstrate the app
`-- DOCUMENTATION.md          # This documentation file
```

---

## 6. Libraries and Packages

This project relies on the following Python libraries and system packages:

### Python Packages

The required Python packages are listed in the `requirements.txt` file:

*   **pandas**: Used for data manipulation and analysis, primarily for reading and cleaning the CSV data.
*   **faker**: Used to generate fake data, though it is not used in the main application logic.
*   **graphviz**: The Python interface for the Graphviz graph visualization software. Used to generate the ER diagrams.
*   **PyQt5**: A comprehensive set of Python bindings for Qt v5. It is used to build the graphical user interface of the application.

You can install these packages using pip:

```bash
pip install -r requirements.txt
```

### System Dependency

*   **Graphviz**: This is a system-level dependency that must be installed separately. It is used by the `graphviz` Python package to render the ER diagrams.
    *   **Windows**: Download an installer from the official Graphviz website ([https://graphviz.org/download/](https://graphviz.org/download/)). **Important**: During installation, ensure that you select the option to "Add Graphviz to the system PATH".
    *   **macOS**: You can install it using Homebrew: `brew install graphviz`
    *   **Linux (Debian/Ubuntu)**: You can install it using apt: `sudo apt-get install graphviz`

---

## 7. Setup and Installation

To run this project, you need Python 3 and the packages listed in `requirements.txt`. You will also need to install Graphviz, which is a system dependency for generating ER diagrams.

**Step 1: Install Graphviz**

Follow the instructions in the "Libraries and Packages" section to install Graphviz on your operating system.

**Step 2: Set up a Python Virtual Environment (Recommended)**

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

**Step 3: Install Python Packages**

With your virtual environment activated, install the required packages using pip:

```bash
pip install -r requirements.txt
```

---

## 8. How to Run the Application

Once the setup is complete, you can launch the main application by running the `main_app_qt.py` script:

```bash
python main_app_qt.py
```

This will open the "ETL Control Panel" graphical user interface.

---

## 9. Usage Guide

The application is designed to be used in a sequential, step-by-step manner. Buttons in the control panel will become enabled as the required previous steps are completed.

1.  **Load CSV**: Click this button to open a file dialog. Select the CSV file you want to analyze (e.g., `university_enrollment_sample.csv`).
2.  **1. Clean Data (1NF)**: After loading a CSV, click this button to run the initial data cleaning process.
3.  **2. Find FDs**: Once cleaning is complete, this button becomes active. Click it to discover the functional dependencies in your data.
4.  **3. Find Candidate Keys**: After FDs are found, click this to run the key analysis. The results will appear in the "Candidate Keys" tab.
5.  **4. Decompose to 3NF**: With candidate keys identified, click this button to perform the 3NF decomposition. The resulting tables and their attributes will be displayed in the "Decomposed Tables" tab.
6.  **5. Generate ERD**: Finally, click this to generate the ER Diagram for the new 3NF schema. The diagram will be shown in the "ER Diagram" tab.
7.  **Download Buttons**: At each stage, you can use the corresponding "Download" button to save the artifacts (FDs, CKs, tables, ERD) to your local machine.
v
