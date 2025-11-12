# Test Files for Investo Portfolio Analyzer

This folder contains diagnostic and test scripts used to identify and fix NaN value issues in the portfolio calculations.

## Overview

These test scripts were created to diagnose a critical issue where NaN values were being introduced during portfolio calculations, causing the total portfolio value to display as NaN. The root cause was identified as European number format (comma as decimal separator) in the CSV files that wasn't being properly converted to numeric values.

## Test Files

### 1. `diagnose_nan.py`
**Purpose:** Comprehensive diagnostic tool that traces through the entire calculation pipeline to identify where NaN values are introduced.

**Usage:**
```bash
python tests/diagnose_nan.py
```

**What it does:**
- Loads transaction data and ticker mappings
- Fetches stock price data
- Tests individual calculation functions (`get_cash_at_date`, `get_total_deposits_at_date`, `get_holdings_at_date`)
- Runs full portfolio calculation with detailed tracing
- Reports NaN values at each step of the calculation process
- Calculates and displays final portfolio totals

**Output:** Detailed diagnostic report showing where NaN values occur in the calculation pipeline.

---

### 2. `test_nan_sources.py`
**Purpose:** Focused tests on individual functions that could introduce NaN values.

**Usage:**
```bash
python tests/test_nan_sources.py
```

**What it does:**
- Tests `get_cash_at_date()` function specifically
- Tests `get_total_deposits_at_date()` function specifically
- Tests `get_holdings_at_date()` function specifically
- Shows sample data and conversion results for each function
- Verifies that numeric conversions are working correctly

**Output:** Function-by-function analysis showing data types, NaN counts, and sample values.

---

### 3. `inspect_csv_structure.py`
**Purpose:** Inspects the CSV file structure to understand data format issues.

**Usage:**
```bash
python tests/inspect_csv_structure.py
```

**What it does:**
- Reads raw CSV file content
- Analyzes column data types
- Checks for European number format (comma as decimal separator)
- Shows sample values before and after conversion
- Identifies delimiter and formatting issues

**Output:** Detailed CSV structure analysis showing data format, conversion issues, and sample values.

---

### 4. `test_number_conversion.py`
**Purpose:** Verifies the number conversion fix for European format numbers.

**Usage:**
```bash
python tests/test_number_conversion.py
```

**What it does:**
- Tests conversion of European format numbers (e.g., "1055,91" → 1055.91)
- Compares broken vs fixed conversion methods
- Tests with actual CSV data
- Shows conversion success rates

**Output:** Verification that European number format conversion is working correctly.

---

### 5. `NAN_ISSUE_DIAGNOSIS.md`
**Purpose:** Documentation of the NaN issue, root cause, and solution.

**Contents:**
- Problem summary
- Root cause analysis
- Evidence and test results
- Solution details
- Files modified
- Next steps

---

## Issue Fixed

### Problem
The CSV files exported from Degiro use European number format with commas as decimal separators (e.g., "1055,91" instead of "1055.91"). When `pd.to_numeric()` tried to convert these strings, it failed because it expects dots as decimal separators, resulting in all values being converted to NaN.

### Impact
- `SaldoAmount`: All values converted to NaN
- `MutatieAmount`: All values converted to NaN
- `get_cash_at_date()`: Returned NaN
- Total portfolio value: Displayed as NaN

### Solution
Modified `investo_utils/data_loader.py` to replace commas with dots before converting to numeric:

```python
# Before (broken):
cash_df['SaldoAmount'] = pd.to_numeric(cash_df['SaldoAmount'], errors='coerce')

# After (fixed):
cash_df['SaldoAmount'] = pd.to_numeric(
    cash_df['SaldoAmount'].astype(str).str.replace(',', '.', regex=False),
    errors='coerce'
)
```

### Results After Fix
- `SaldoAmount`: 0 NaN (was 424/424 before)
- `MutatieAmount`: 61 NaN (expected for rows without amounts)
- `get_cash_at_date()`: Returns proper values (e.g., 1055.91, 1299.0)
- `get_total_deposits_at_date()`: Returns proper values (e.g., 9700.0)
- Total portfolio value: Calculates correctly

---

## Running Tests

All test scripts are designed to be run from the project root directory. They automatically locate the `Account.csv` and `tickers.csv` files in the parent directory.

### Prerequisites
- Python 3.8 or higher
- Required packages: pandas, numpy, tqdm
- `Account.csv` file in the project root
- `tickers.csv` file in the project root (optional, but recommended)

### Example Usage

From the project root directory:

```bash
# Run comprehensive diagnostic
python tests/diagnose_nan.py

# Run focused function tests
python tests/test_nan_sources.py

# Inspect CSV structure
python tests/inspect_csv_structure.py

# Test number conversion
python tests/test_number_conversion.py
```

---

## Notes

- All test scripts automatically handle path resolution to find CSV files in the parent directory
- Test scripts import from `investo_utils` modules, so they need to be run from the project root
- The tests modify the `Account.csv` file (via `prepare_account_csv()`), so make sure you have a backup if needed
- Some tests may take a while to run if they fetch stock price data from Yahoo Finance

---

## Maintenance

These test files can be used to:
- Verify fixes are working correctly
- Diagnose new NaN issues if they arise
- Test changes to data loading or calculation functions
- Understand the data format and structure

If you encounter NaN values in your portfolio calculations, start with `diagnose_nan.py` to get a comprehensive overview of where the issue occurs.

