"""
Test script to verify the number conversion fix for European format numbers.
"""

import pandas as pd
import numpy as np

def test_european_number_conversion():
    """Test converting European format numbers (comma as decimal separator)"""
    print("="*60)
    print("TESTING EUROPEAN NUMBER CONVERSION")
    print("="*60)
    
    # Sample European format numbers from the CSV
    test_values = [
        "1055,91",
        "355,91",
        "635,30",
        "0,00",
        "-318,60",
        "700,00",
        "279,39",
        "-278,42",
        "-0,97"
    ]
    
    print("\n1. Current behavior (pd.to_numeric with comma):")
    for val in test_values:
        result = pd.to_numeric(val, errors='coerce')
        print(f"  '{val}' -> {result} ({'NaN' if pd.isna(result) else 'OK'})")
    
    print("\n2. Fix: Replace comma with dot before conversion:")
    for val in test_values:
        fixed_val = val.replace(',', '.')
        result = pd.to_numeric(fixed_val, errors='coerce')
        print(f"  '{val}' -> '{fixed_val}' -> {result} ({'NaN' if pd.isna(result) else 'OK'})")
    
    print("\n3. Testing with a Series:")
    test_series = pd.Series(["1055,91", "355,91", "635,30", "0,00", "-318,60"])
    print(f"  Original: {test_series.tolist()}")
    
    # Current (broken) method
    broken_result = pd.to_numeric(test_series, errors='coerce')
    print(f"  Current method: {broken_result.tolist()} (NaN count: {broken_result.isna().sum()})")
    
    # Fixed method
    fixed_series = test_series.str.replace(',', '.', regex=False)
    fixed_result = pd.to_numeric(fixed_series, errors='coerce')
    print(f"  Fixed method: {fixed_result.tolist()} (NaN count: {fixed_result.isna().sum()})")
    
    print("\n4. Testing edge cases:")
    edge_cases = [
        "",  # Empty string
        " ",  # Space
        "abc",  # Non-numeric
        "1.234,56",  # Thousand separator (dot) + decimal (comma)
        "1,234.56",  # Thousand separator (comma) + decimal (dot) - US format
    ]
    
    for val in edge_cases:
        # Try simple replace
        simple_fixed = val.replace(',', '.')
        simple_result = pd.to_numeric(simple_fixed, errors='coerce')
        
        # Try more sophisticated (handle thousand separators)
        # For now, just simple replace
        print(f"  '{val}' -> '{simple_fixed}' -> {simple_result} ({'NaN' if pd.isna(simple_result) else 'OK'})")

def test_with_actual_csv_data():
    """Test with actual CSV data structure"""
    print("\n" + "="*60)
    print("TESTING WITH ACTUAL CSV DATA STRUCTURE")
    print("="*60)
    
    import os
    # Get parent directory for CSV files
    PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ACCOUNT_CSV = os.path.join(PARENT_DIR, 'Account.csv')
    
    if not os.path.exists(ACCOUNT_CSV):
        print(f"ERROR: Account.csv not found at {ACCOUNT_CSV}!")
        return
    
    # Read CSV
    df = pd.read_csv(ACCOUNT_CSV)
    
    print(f"\nOriginal SaldoAmount column (first 10 values):")
    print(df['SaldoAmount'].head(10).tolist())
    
    print(f"\nCurrent conversion (broken):")
    broken = pd.to_numeric(df['SaldoAmount'], errors='coerce')
    print(f"  NaN count: {broken.isna().sum()} / {len(broken)}")
    print(f"  Non-NaN count: {(~broken.isna()).sum()}")
    
    print(f"\nFixed conversion (replace comma with dot):")
    fixed = df['SaldoAmount'].str.replace(',', '.', regex=False)
    fixed_numeric = pd.to_numeric(fixed, errors='coerce')
    print(f"  NaN count: {fixed_numeric.isna().sum()} / {len(fixed_numeric)}")
    print(f"  Non-NaN count: {(~fixed_numeric.isna()).sum()}")
    print(f"  Sample converted values:")
    non_nan = fixed_numeric[~fixed_numeric.isna()]
    if len(non_nan) > 0:
        print(f"    {non_nan.head(10).tolist()}")
    
    print(f"\nOriginal MutatieAmount column (first 10 values):")
    print(df['MutatieAmount'].head(10).tolist())
    
    print(f"\nCurrent conversion (broken):")
    broken_mutatie = pd.to_numeric(df['MutatieAmount'], errors='coerce')
    print(f"  NaN count: {broken_mutatie.isna().sum()} / {len(broken_mutatie)}")
    print(f"  Non-NaN count: {(~broken_mutatie.isna()).sum()}")
    
    print(f"\nFixed conversion (replace comma with dot):")
    fixed_mutatie = df['MutatieAmount'].astype(str).str.replace(',', '.', regex=False)
    fixed_mutatie_numeric = pd.to_numeric(fixed_mutatie, errors='coerce')
    print(f"  NaN count: {fixed_mutatie_numeric.isna().sum()} / {len(fixed_mutatie_numeric)}")
    print(f"  Non-NaN count: {(~fixed_mutatie_numeric.isna()).sum()}")
    print(f"  Sample converted values:")
    non_nan_mutatie = fixed_mutatie_numeric[~fixed_mutatie_numeric.isna()]
    if len(non_nan_mutatie) > 0:
        print(f"    {non_nan_mutatie.head(10).tolist()}")

if __name__ == "__main__":
    test_european_number_conversion()
    test_with_actual_csv_data()

