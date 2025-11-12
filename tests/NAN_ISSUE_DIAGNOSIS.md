# NaN Value Issue Diagnosis

## Problem Summary
The portfolio total value is showing as NaN because `SaldoAmount` and `MutatieAmount` columns are not being converted correctly from the CSV file.

## Root Cause
The CSV file uses **European number format** with commas as decimal separators (e.g., "1055,91" instead of "1055.91"). When `pd.to_numeric()` tries to convert these strings, it fails because it expects dots as decimal separators, resulting in all values being converted to NaN.

## Evidence

### Test Results
- **SaldoAmount**: 426 rows, ALL converted to NaN (0 successful conversions)
- **MutatieAmount**: 426 rows, ALL converted to NaN (0 successful conversions)

### Sample Values from CSV
```
SaldoAmount: "1055,91", "355,91", "635,30", "0,00", "-318,60"
MutatieAmount: "700,00", "279,39", "33,02", "-278,42", "-0,97"
```

### Impact
1. `get_cash_at_date()` returns NaN because it returns `past_transactions.iloc[0]['SaldoAmount']` which is NaN
2. This NaN propagates through the calculation, making the total portfolio value NaN
3. `get_total_deposits_at_date()` also affected, though pandas sum() of NaN might return 0.0 in some cases

## Solution
Replace commas with dots before converting to numeric in `data_loader.py`:

### Current Code (BROKEN):
```python
cash_df['SaldoAmount'] = pd.to_numeric(cash_df['SaldoAmount'], errors='coerce')
df['MutatieAmount'] = pd.to_numeric(df['MutatieAmount'], errors='coerce')
```

### Fixed Code:
```python
# Convert European format (comma as decimal separator) to standard format
cash_df['SaldoAmount'] = pd.to_numeric(
    cash_df['SaldoAmount'].astype(str).str.replace(',', '.', regex=False),
    errors='coerce'
)
df['MutatieAmount'] = pd.to_numeric(
    df['MutatieAmount'].astype(str).str.replace(',', '.', regex=False),
    errors='coerce'
)
```

## Test Results After Fix
- **SaldoAmount**: 424/426 successfully converted (2 NaN remain, likely empty strings)
- **MutatieAmount**: 363/426 successfully converted (63 NaN remain, which is expected as some rows legitimately don't have MutatieAmount)

## Files to Modify
1. `investo_utils/data_loader.py` - Fix number conversion in `load_transaction_data()` function

## Test Files Created
1. `diagnose_nan.py` - Comprehensive diagnostic tool
2. `test_nan_sources.py` - Focused tests on individual functions
3. `inspect_csv_structure.py` - CSV structure inspection
4. `test_number_conversion.py` - Number conversion fix verification

## Next Steps
1. Apply the fix to `investo_utils/data_loader.py`
2. Re-run the diagnostic scripts to verify the fix
3. Test the full portfolio calculation to ensure total value is no longer NaN

