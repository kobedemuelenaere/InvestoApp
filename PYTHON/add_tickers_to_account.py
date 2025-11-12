"""
Script to add ticker names to Account.csv and save as a new CSV file.
"""

import pandas as pd
import sys
import os

# Import utility modules
from investo_utils.data_loader import (
    prepare_account_csv,
    load_ticker_mappings
)

def add_tickers_to_account(
    account_file='Account.csv',
    ticker_file='tickers.csv',
    output_file='Account_with_tickers.csv'
):
    """
    Add ticker names to Account.csv and save as a new CSV.
    
    Args:
        account_file: Path to Account.csv
        ticker_file: Path to tickers.csv
        output_file: Path to output CSV file
    """
    print("="*60)
    print("Adding Tickers to Account CSV")
    print("="*60)
    
    # Step 1: Load data
    print("\n[1/2] Loading account data and ticker mappings...")
    prepare_account_csv(account_file)
    ticker_map, usd_stocks = load_ticker_mappings(ticker_file)
    
    # Load Account.csv
    print(f"Loading {account_file}...")
    df = pd.read_csv(account_file)
    
    print(f"  Loaded {len(df)} rows")
    
    # Step 2: Add ticker column
    print("\n[2/2] Adding ticker column...")
    
    # Map Product names to tickers
    df['Ticker'] = df['Product'].map(ticker_map)
    
    # For rows without a Product (cash transactions), leave ticker as empty
    df['Ticker'] = df['Ticker'].fillna('')
    
    # Reorder columns to put Ticker after Product
    cols = list(df.columns)
    # Remove Ticker from its current position
    cols.remove('Ticker')
    # Find Product index
    product_idx = cols.index('Product')
    # Insert Ticker after Product
    cols.insert(product_idx + 1, 'Ticker')
    df = df[cols]
    
    # Save to CSV
    print(f"Saving to {output_file}...")
    df.to_csv(output_file, index=False)
    
    # Show statistics
    print(f"\n[SUCCESS] Successfully generated {output_file}")
    print(f"  Total rows: {len(df)}")
    print(f"  Rows with tickers: {df['Ticker'].ne('').sum()}")
    print(f"  Rows without tickers (cash transactions): {df['Ticker'].eq('').sum()}")
    
    # Show sample of tickers added
    print(f"\n  Sample tickers added:")
    sample = df[df['Ticker'].ne('')][['Product', 'Ticker']].drop_duplicates().head(10)
    for _, row in sample.iterrows():
        print(f"    {row['Product']} -> {row['Ticker']}")
    
    return df

if __name__ == "__main__":
    # Allow command line arguments
    account_file = sys.argv[1] if len(sys.argv) > 1 else 'Account.csv'
    ticker_file = sys.argv[2] if len(sys.argv) > 2 else 'tickers.csv'
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'Account_with_tickers.csv'
    
    # Check if files exist
    if not os.path.exists(account_file):
        print(f"Error: {account_file} not found!")
        sys.exit(1)
    
    if not os.path.exists(ticker_file):
        print(f"Error: {ticker_file} not found!")
        sys.exit(1)
    
    try:
        result_df = add_tickers_to_account(account_file, ticker_file, output_file)
        print("\n" + "="*60)
        print("Done!")
        print("="*60)
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

