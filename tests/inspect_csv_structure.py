"""
Inspect the CSV file structure to understand why SaldoAmount and MutatieAmount are NaN.
"""

import pandas as pd
import os

# Get parent directory for CSV files
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNT_CSV = os.path.join(PARENT_DIR, 'Account.csv')

def inspect_csv():
    """Inspect the Account.csv file structure"""
    if not os.path.exists(ACCOUNT_CSV):
        print(f"ERROR: Account.csv not found at {ACCOUNT_CSV}!")
        return
    
    print("="*60)
    print("INSPECTING Account.csv STRUCTURE")
    print("="*60)
    
    # Read raw CSV first
    print("\n1. Reading raw CSV (first 20 lines):")
    with open(ACCOUNT_CSV, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines[:20]):
            print(f"Line {i}: {line.strip()}")
    
    # Read as DataFrame
    print("\n2. Reading as DataFrame:")
    df_raw = pd.read_csv(ACCOUNT_CSV)
    print(f"Shape: {df_raw.shape}")
    print(f"Columns: {df_raw.columns.tolist()}")
    
    # Check SaldoAmount column
    print("\n3. SaldoAmount column analysis:")
    print(f"  Data type: {df_raw['SaldoAmount'].dtype}")
    print(f"  Sample values:")
    print(df_raw[['Datum', 'Omschrijving', 'Saldo', 'SaldoAmount']].head(10).to_string())
    
    # Check what values are actually in SaldoAmount
    print(f"\n  Unique SaldoAmount values (first 20):")
    unique_values = df_raw['SaldoAmount'].unique()[:20]
    for val in unique_values:
        print(f"    '{val}' (type: {type(val).__name__})")
    
    # Try to convert to numeric
    print("\n4. Converting SaldoAmount to numeric:")
    saldo_numeric = pd.to_numeric(df_raw['SaldoAmount'], errors='coerce')
    print(f"  NaN count after conversion: {saldo_numeric.isna().sum()}")
    print(f"  Non-NaN count: {(~saldo_numeric.isna()).sum()}")
    
    if (~saldo_numeric.isna()).sum() > 0:
        print(f"  Sample non-NaN values:")
        non_nan = saldo_numeric[~saldo_numeric.isna()]
        print(f"    {non_nan.head(10).tolist()}")
    
    # Check MutatieAmount column
    print("\n5. MutatieAmount column analysis:")
    print(f"  Data type: {df_raw['MutatieAmount'].dtype}")
    print(f"  Sample values:")
    print(df_raw[['Datum', 'Omschrijving', 'Mutatie', 'MutatieAmount']].head(10).to_string())
    
    # Check what values are actually in MutatieAmount
    print(f"\n  Unique MutatieAmount values (first 20):")
    unique_values = df_raw['MutatieAmount'].unique()[:20]
    for val in unique_values:
        print(f"    '{val}' (type: {type(val).__name__})")
    
    # Try to convert to numeric
    print("\n6. Converting MutatieAmount to numeric:")
    mutatie_numeric = pd.to_numeric(df_raw['MutatieAmount'], errors='coerce')
    print(f"  NaN count after conversion: {mutatie_numeric.isna().sum()}")
    print(f"  Non-NaN count: {(~mutatie_numeric.isna()).sum()}")
    
    if (~mutatie_numeric.isna()).sum() > 0:
        print(f"  Sample non-NaN values:")
        non_nan = mutatie_numeric[~mutatie_numeric.isna()]
        print(f"    {non_nan.head(10).tolist()}")
    
    # Check if there's a pattern in the Omschrijving that might help
    print("\n7. Checking Omschrijving patterns for cash-related transactions:")
    cash_related = df_raw[df_raw['Omschrijving'].str.contains('Deposit|deposit|Saldo|saldo', case=False, na=False)]
    if len(cash_related) > 0:
        print(f"  Found {len(cash_related)} cash-related transactions")
        print(f"  Sample:")
        print(cash_related[['Datum', 'Omschrijving', 'Saldo', 'SaldoAmount', 'MutatieAmount']].head(10).to_string())
    
    # Check the actual CSV format - maybe there's a delimiter issue
    print("\n8. Checking CSV delimiter:")
    with open(ACCOUNT_CSV, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        print(f"  First line: {first_line}")
        print(f"  Number of commas: {first_line.count(',')}")
        print(f"  Number of semicolons: {first_line.count(';')}")
        print(f"  Number of tabs: {first_line.count(chr(9))}")
        
        # Try different delimiters
        for delim in [',', ';', '\t']:
            parts = first_line.split(delim)
            print(f"  Split by '{delim}': {len(parts)} parts")
            if len(parts) > 10:
                print(f"    First few parts: {parts[:5]}")

if __name__ == "__main__":
    inspect_csv()

