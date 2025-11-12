"""
Focused test script to check specific sources of NaN values.
Tests individual functions in isolation.
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from investo_utils.data_loader import load_transaction_data, prepare_account_csv
from investo_utils.portfolio import get_cash_at_date, get_total_deposits_at_date, get_holdings_at_date

# Get parent directory for CSV files
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNT_CSV = os.path.join(PARENT_DIR, 'Account.csv')
TICKERS_CSV = os.path.join(PARENT_DIR, 'tickers.csv')

def test_cash_function():
    """Test get_cash_at_date function specifically"""
    print("="*60)
    print("TESTING: get_cash_at_date")
    print("="*60)
    
    if not os.path.exists(ACCOUNT_CSV):
        print(f"ERROR: Account.csv not found at {ACCOUNT_CSV}!")
        return
    
    prepare_account_csv(ACCOUNT_CSV)
    df, cash_df = load_transaction_data(ACCOUNT_CSV)
    
    print(f"\nCash DataFrame shape: {cash_df.shape}")
    print(f"Cash DataFrame columns: {cash_df.columns.tolist()}")
    
    # Check SaldoAmount column
    print(f"\nSaldoAmount info:")
    print(f"  Total rows: {len(cash_df)}")
    print(f"  NaN count: {cash_df['SaldoAmount'].isna().sum()}")
    print(f"  Data type: {cash_df['SaldoAmount'].dtype}")
    
    # Show sample SaldoAmount values
    print(f"\nSample SaldoAmount values:")
    sample = cash_df[['Datum_Tijd', 'Omschrijving', 'Saldo', 'SaldoAmount']].head(10)
    print(sample.to_string())
    
    # Test get_cash_at_date for different dates
    test_dates = [
        cash_df['Datum_Tijd'].min(),
        cash_df['Datum_Tijd'].max(),
        pd.Timestamp.now()
    ]
    
    print(f"\nTesting get_cash_at_date for different dates:")
    for test_date in test_dates:
        print(f"\n  Date: {test_date}")
        
        # Show what transactions are being filtered
        filtered = cash_df[
            (cash_df['Datum_Tijd'] <= test_date) &
            (~cash_df['Omschrijving'].str.contains('Overboeking|Degiro Cash Sweep Transfer', na=False)) &
            (cash_df['Saldo'] != 'USD')
        ]
        
        print(f"    Filtered transactions: {len(filtered)}")
        if len(filtered) > 0:
            print(f"    First filtered transaction:")
            first = filtered.iloc[0]
            print(f"      Omschrijving: {first.get('Omschrijving', 'N/A')}")
            print(f"      Saldo: {first.get('Saldo', 'N/A')}")
            print(f"      SaldoAmount: {first.get('SaldoAmount', 'N/A')}")
            print(f"      SaldoAmount type: {type(first.get('SaldoAmount'))}")
            print(f"      SaldoAmount is NaN: {pd.isna(first.get('SaldoAmount'))}")
        
        cash = get_cash_at_date(cash_df, test_date)
        print(f"    Result: {cash}")
        print(f"    Result type: {type(cash)}")
        print(f"    Result is NaN: {pd.isna(cash) if cash is not None else 'N/A'}")

def test_deposits_function():
    """Test get_total_deposits_at_date function specifically"""
    print("\n" + "="*60)
    print("TESTING: get_total_deposits_at_date")
    print("="*60)
    
    if not os.path.exists(ACCOUNT_CSV):
        print(f"ERROR: Account.csv not found at {ACCOUNT_CSV}!")
        return
    
    prepare_account_csv(ACCOUNT_CSV)
    df, cash_df = load_transaction_data(ACCOUNT_CSV)
    
    print(f"\nCash DataFrame shape: {cash_df.shape}")
    
    # Check MutatieAmount column
    print(f"\nMutatieAmount info:")
    print(f"  Total rows: {len(cash_df)}")
    print(f"  NaN count: {cash_df['MutatieAmount'].isna().sum()}")
    print(f"  Data type: {cash_df['MutatieAmount'].dtype}")
    
    # Show deposit transactions
    deposits = cash_df[
        cash_df['Omschrijving'].str.contains('deposit', case=False, na=False)
    ]
    print(f"\nDeposit transactions found: {len(deposits)}")
    
    if len(deposits) > 0:
        print(f"\nSample deposit transactions:")
        sample = deposits[['Datum_Tijd', 'Omschrijving', 'MutatieAmount']].head(10)
        print(sample.to_string())
        
        print(f"\nMutatieAmount values in deposits:")
        print(f"  NaN count: {deposits['MutatieAmount'].isna().sum()}")
        print(f"  Sum: {deposits['MutatieAmount'].sum()}")
        print(f"  Sum (with fillna): {deposits['MutatieAmount'].fillna(0).sum()}")
    
    # Test get_total_deposits_at_date for different dates
    test_dates = [
        cash_df['Datum_Tijd'].min(),
        cash_df['Datum_Tijd'].max(),
        pd.Timestamp.now()
    ]
    
    print(f"\nTesting get_total_deposits_at_date for different dates:")
    for test_date in test_dates:
        print(f"\n  Date: {test_date}")
        
        # Show what transactions are being filtered
        filtered = cash_df[cash_df['Datum_Tijd'] <= test_date]
        deposits_filtered = filtered[
            filtered['Omschrijving'].str.contains('deposit', case=False, na=False)
        ]
        
        print(f"    Transactions up to date: {len(filtered)}")
        print(f"    Deposit transactions: {len(deposits_filtered)}")
        
        if len(deposits_filtered) > 0:
            print(f"    MutatieAmount values:")
            mutatie_values = deposits_filtered['MutatieAmount']
            print(f"      NaN count: {mutatie_values.isna().sum()}")
            print(f"      Sum: {mutatie_values.sum()}")
            print(f"      Sum (with fillna): {mutatie_values.fillna(0).sum()}")
        
        deposits_total = get_total_deposits_at_date(cash_df, test_date)
        print(f"    Result: {deposits_total}")
        print(f"    Result type: {type(deposits_total)}")
        print(f"    Result is NaN: {pd.isna(deposits_total) if deposits_total is not None else 'N/A'}")

def test_holdings_function():
    """Test get_holdings_at_date function specifically"""
    print("\n" + "="*60)
    print("TESTING: get_holdings_at_date")
    print("="*60)
    
    if not os.path.exists(ACCOUNT_CSV):
        print(f"ERROR: Account.csv not found at {ACCOUNT_CSV}!")
        return
    
    prepare_account_csv(ACCOUNT_CSV)
    df, cash_df = load_transaction_data(ACCOUNT_CSV)
    
    print(f"\nTransaction DataFrame shape: {df.shape}")
    
    # Check Aantal column
    print(f"\nAantal column info:")
    print(f"  Total rows: {len(df)}")
    print(f"  NaN count: {df['Aantal'].isna().sum()}")
    print(f"  Data type: {df['Aantal'].dtype}")
    
    # Show sample Aantal values
    print(f"\nSample Aantal values:")
    sample = df[['Datum_Tijd', 'Product', 'Omschrijving', 'Aantal']].head(10)
    print(sample.to_string())
    
    # Test get_holdings_at_date for different dates
    test_dates = [
        df['Datum_Tijd'].min(),
        df['Datum_Tijd'].max(),
        pd.Timestamp.now()
    ]
    
    print(f"\nTesting get_holdings_at_date for different dates:")
    for test_date in test_dates:
        print(f"\n  Date: {test_date}")
        
        # Show what transactions are being filtered
        filtered = df[df['Datum_Tijd'] <= test_date]
        print(f"    Transactions up to date: {len(filtered)}")
        
        if len(filtered) > 0:
            print(f"    Aantal values:")
            aantal_values = filtered['Aantal']
            print(f"      NaN count: {aantal_values.isna().sum()}")
            print(f"      Sum: {aantal_values.sum()}")
            print(f"      Sum (with fillna): {aantal_values.fillna(0).sum()}")
        
        holdings = get_holdings_at_date(df, test_date)
        
        if isinstance(holdings, pd.Series):
            print(f"    Holdings result:")
            print(f"      Number of stocks: {len(holdings)}")
            print(f"      NaN count: {holdings.isna().sum()}")
            
            if holdings.isna().sum() > 0:
                print(f"      Stocks with NaN holdings:")
                for stock, holding in holdings.items():
                    if pd.isna(holding):
                        print(f"        {stock}: NaN")
            else:
                print(f"      Sample holdings:")
                for stock, holding in list(holdings.items())[:5]:
                    print(f"        {stock}: {holding}")
        else:
            print(f"    ERROR: holdings is not a Series: {type(holdings)}")

def main():
    """Run all focused tests"""
    print("="*60)
    print("FOCUSED NaN SOURCE TESTS")
    print("="*60)
    
    test_cash_function()
    test_deposits_function()
    test_holdings_function()
    
    print("\n" + "="*60)
    print("TESTS COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()

