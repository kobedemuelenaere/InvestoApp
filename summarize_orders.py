"""
Script to analyze Account.csv and create a summary grouped by Order ID.
Summarizes each order with ticker, shares, type, costs, etc.
"""

import pandas as pd
import sys
import os
import re

# Import utility modules
from investo_utils.data_loader import (
    prepare_account_csv,
    load_ticker_mappings
)

def summarize_orders_by_id(
    account_file='Account.csv',
    ticker_file='tickers.csv',
    output_file='orders_summary.csv'
):
    """
    Analyze Account.csv and create a summary grouped by Order ID.
    
    Args:
        account_file: Path to Account.csv
        ticker_file: Path to tickers.csv
        output_file: Path to output CSV file
    """
    print("="*60)
    print("Order Summary Generator")
    print("="*60)
    
    # Step 1: Load data
    print("\n[1/3] Loading account data and ticker mappings...")
    prepare_account_csv(account_file)
    ticker_map, usd_stocks = load_ticker_mappings(ticker_file)
    
    # Load Account.csv
    print(f"Loading {account_file}...")
    df = pd.read_csv(account_file)
    
    # Convert numeric columns
    df['MutatieAmount'] = pd.to_numeric(
        df['MutatieAmount'].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    )
    
    # Convert dates
    df['Datum'] = pd.to_datetime(df['Datum'], format='%d-%m-%Y')
    df['Tijd'] = df['Tijd'].fillna('00:00')
    df['Datum_Tijd'] = pd.to_datetime(
        df['Datum'].dt.strftime('%Y-%m-%d') + ' ' + df['Tijd']
    )
    
    # Filter out zero-value Flatex Interest Income entries
    df = df[~((df['Omschrijving'] == 'Flatex Interest Income') & 
              (df['MutatieAmount'] == 0.00))]
    
    # Filter for stock transactions only (those with Order Id)
    df_stocks = df[df['Order Id'].notna() & (df['Order Id'] != '')].copy()
    
    print(f"  Found {df_stocks['Order Id'].nunique()} unique orders")
    
    # Step 2: Group by Order ID and summarize
    print("\n[2/3] Analyzing and summarizing orders...")
    
    orders_summary = []
    unique_order_ids = df_stocks['Order Id'].unique()
    
    for order_id in unique_order_ids:
        order_rows = df_stocks[df_stocks['Order Id'] == order_id].copy()
        order_rows = order_rows.sort_values('Datum_Tijd')
        
        # Get main transaction (Koop/Verkoop)
        main_trans = order_rows[
            order_rows['Omschrijving'].str.contains('Koop|Verkoop', na=False)
        ]
        
        if main_trans.empty:
            continue
        
        main_trans = main_trans.iloc[0]
        product = main_trans['Product']
        omschrijving = main_trans['Omschrijving']
        
        # Extract shares and determine type
        shares_match = re.search(r'(?:Koop|Verkoop)\s+(\d+)', omschrijving)
        shares = float(shares_match.group(1)) if shares_match else 0
        
        is_buy = 'Koop' in omschrijving
        trans_type = 'BUY' if is_buy else 'SELL'
        
        # Extract price from description
        price_match = re.search(r'@\s*([\d,]+)', omschrijving)
        price_str = price_match.group(1).replace(',', '.') if price_match else None
        price_per_share = float(price_str) if price_str else None
        
        # Get ticker
        ticker = ticker_map.get(product, 'N/A')
        
        # Calculate costs and fees
        # Transaction costs (DEGIRO Transactiekosten)
        transaction_costs = order_rows[
            order_rows['Omschrijving'].str.contains('DEGIRO Transactiekosten', na=False)
        ]['MutatieAmount'].sum()
        transaction_costs = abs(transaction_costs) if pd.notna(transaction_costs) else 0
        
        # Transaction tax (Transactiebelasting)
        transaction_tax = order_rows[
            order_rows['Omschrijving'].str.contains('Transactiebelasting', na=False)
        ]['MutatieAmount'].sum()
        transaction_tax = abs(transaction_tax) if pd.notna(transaction_tax) else 0
        
        # Currency conversion costs - there's no separate cost for currency conversion
        # The FX rate is applied directly, so currency_costs = 0
        currency_costs = 0
        
        # Total costs (only transaction costs and taxes)
        total_costs = transaction_costs + transaction_tax
        
        # Get transaction amount in EUR
        # For USD stocks, use Valuta Debitering EUR amount
        # For EUR stocks, use the main transaction MutatieAmount
        if product in usd_stocks:
            eur_amount_row = order_rows[
                (order_rows['Omschrijving'].str.contains('Valuta Debitering', na=False)) &
                (order_rows['Saldo'] == 'EUR')
            ]
            if not eur_amount_row.empty:
                transaction_amount_eur = abs(eur_amount_row.iloc[0]['MutatieAmount'])
            else:
                # Fallback: use main transaction amount
                transaction_amount_eur = abs(main_trans['MutatieAmount']) if pd.notna(main_trans['MutatieAmount']) else 0
        else:
            transaction_amount_eur = abs(main_trans['MutatieAmount']) if pd.notna(main_trans['MutatieAmount']) else 0
        
        # Total amount including costs
        if is_buy:
            total_amount_eur = transaction_amount_eur + total_costs
        else:
            total_amount_eur = transaction_amount_eur - total_costs
        
        # Get date and time
        date = main_trans['Datum'].strftime('%Y-%m-%d') if pd.notna(main_trans['Datum']) else ''
        time = main_trans['Tijd'] if pd.notna(main_trans['Tijd']) else ''
        
        orders_summary.append({
            'Order_ID': order_id,
            'Date': date,
            'Time': time,
            'Ticker': ticker,
            'Product': product,
            'Type': trans_type,
            'Shares': shares,
            'Price_Per_Share': price_per_share,
            'Transaction_Amount_EUR': round(transaction_amount_eur, 2),
            'Transaction_Costs_EUR': round(transaction_costs, 2),
            'Transaction_Tax_EUR': round(transaction_tax, 2),
            'Currency_Costs_EUR': round(currency_costs, 2),
            'Total_Costs_EUR': round(total_costs, 2),
            'Total_Amount_EUR': round(total_amount_eur, 2),
            'Currency': 'USD' if product in usd_stocks else 'EUR'
        })
    
    # Step 3: Create DataFrame and save
    print("\n[3/3] Generating summary CSV...")
    result_df = pd.DataFrame(orders_summary)
    
    # Sort by date (newest first)
    result_df = result_df.sort_values(['Date', 'Time'], ascending=[False, False])
    
    # Save to CSV
    result_df.to_csv(output_file, index=False)
    
    print(f"\n[SUCCESS] Successfully generated {output_file}")
    print(f"  Total orders: {len(result_df)}")
    print(f"  BUY orders: {len(result_df[result_df['Type'] == 'BUY'])}")
    print(f"  SELL orders: {len(result_df[result_df['Type'] == 'SELL'])}")
    print(f"  Total transaction costs: €{result_df['Transaction_Costs_EUR'].sum():.2f}")
    print(f"  Total transaction tax: €{result_df['Transaction_Tax_EUR'].sum():.2f}")
    print(f"  Total currency costs: €{result_df['Currency_Costs_EUR'].sum():.2f}")
    print(f"  Total costs: €{result_df['Total_Costs_EUR'].sum():.2f}")
    
    return result_df

if __name__ == "__main__":
    # Allow command line arguments
    account_file = sys.argv[1] if len(sys.argv) > 1 else 'Account.csv'
    ticker_file = sys.argv[2] if len(sys.argv) > 2 else 'tickers.csv'
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'orders_summary.csv'
    
    # Check if files exist
    if not os.path.exists(account_file):
        print(f"Error: {account_file} not found!")
        sys.exit(1)
    
    if not os.path.exists(ticker_file):
        print(f"Error: {ticker_file} not found!")
        sys.exit(1)
    
    try:
        result_df = summarize_orders_by_id(account_file, ticker_file, output_file)
        print("\n" + "="*60)
        print("Done!")
        print("="*60)
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

