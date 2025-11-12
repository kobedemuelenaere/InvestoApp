"""
Standalone script to generate a CSV file with all transactions grouped by EOD date.
This shows all transactions (stock buys/sells, deposits/withdrawals) for each day.

Output CSV format:
- Date (EOD), Transaction_Time, Type, Ticker, Name, Description, Shares, Price_Per_Share_EUR, Amount_EUR, Cash_Balance_EUR
- Multiple rows per date (one per transaction)
"""

import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import re

# Import utility modules
from investo_utils.data_loader import (
    prepare_account_csv,
    load_ticker_mappings,
    load_transaction_data,
    get_historical_eur_usd_rates
)

# Default USD to EUR conversion rate as fallback
USD_TO_EUR = 0.97

def extract_transaction_price(omschrijving, mutatie_amount, aantal, fx_rate=None):
    """
    Extract price per share from transaction description.
    Returns price in EUR.
    """
    # Try to extract price from description like "Koop 9 @ 35,4 USD" or "Koop 1 @ 35,4 USD"
    price_match = re.search(r'@\s*([\d,]+)', omschrijving)
    if price_match:
        price_str = price_match.group(1).replace(',', '.')
        try:
            price = float(price_str)
            # If USD stock, convert to EUR
            if fx_rate is not None:
                price_eur = price * fx_rate
            else:
                price_eur = price
            return price_eur
        except:
            pass
    
    # Fallback: calculate from MutatieAmount / Aantal
    if aantal and aantal != 0 and mutatie_amount:
        price = abs(mutatie_amount) / abs(aantal)
        return price
    
    return None

def get_fx_rate_for_transaction(row, eur_usd_rates):
    """Get FX rate for a transaction"""
    if pd.notna(row.get('FX')):
        try:
            fx_str = str(row['FX']).replace(',', '.')
            fx_rate = float(fx_str)
            # FX column appears to be USD/EUR rate, so for USD to EUR conversion we use 1/FX
            # Actually, looking at the data, FX seems to be the conversion rate used
            # Let's check: if Mutatie is USD and we have FX, then FX is likely USD/EUR
            # But we need USD to EUR, so it might be 1/FX or just FX depending on format
            # From the data: FX="1,1443" for USD transaction, MutatieAmount in USD
            # So FX is likely EUR/USD (how many EUR per USD), which means we multiply USD price by FX
            return fx_rate
        except:
            pass
    
    # Use historical rate if available
    if eur_usd_rates is not None and pd.notna(row.get('Datum_Tijd')):
        rate = eur_usd_rates.asof(row['Datum_Tijd'])
        if pd.notna(rate):
            return rate
    
    return USD_TO_EUR

def generate_transactions_eod_csv(
    account_file='Account.csv',
    ticker_file='tickers.csv',
    output_file='portfolio_daily_eod.csv'
):
    """
    Generate a CSV file with all transactions grouped by EOD date.
    
    Args:
        account_file: Path to Account.csv
        ticker_file: Path to tickers.csv
        output_file: Path to output CSV file
    """
    print("="*60)
    print("Transactions EOD CSV Generator")
    print("="*60)
    
    # Step 1: Load data
    print("\n[1/4] Loading account data and ticker mappings...")
    prepare_account_csv(account_file)
    ticker_map, usd_stocks = load_ticker_mappings(ticker_file)
    
    # Load full transaction data (not filtered)
    print("Loading full transaction data...")
    df_full = pd.read_csv(account_file)
    
    # Convert numeric columns
    df_full['MutatieAmount'] = pd.to_numeric(
        df_full['MutatieAmount'].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    )
    df_full['SaldoAmount'] = pd.to_numeric(
        df_full['SaldoAmount'].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    )
    
    # Convert dates
    df_full['Datum'] = pd.to_datetime(df_full['Datum'], format='%d-%m-%Y')
    df_full['Tijd'] = df_full['Tijd'].fillna('00:00')
    df_full['Datum_Tijd'] = pd.to_datetime(
        df_full['Datum'].dt.strftime('%Y-%m-%d') + ' ' + df_full['Tijd']
    )
    
    # Filter out zero-value Flatex Interest Income entries
    df_full = df_full[~((df_full['Omschrijving'] == 'Flatex Interest Income') & 
                        (df_full['MutatieAmount'] == 0.00))]
    
    # Step 2: Fetch EUR/USD conversion rates
    print("\n[2/4] Fetching EUR/USD conversion rates...")
    start_date = df_full['Datum_Tijd'].min()
    end_date = pd.Timestamp.now()
    eur_usd_rates = get_historical_eur_usd_rates(start_date, end_date)
    if eur_usd_rates is None:
        print(f"  Using fallback USD to EUR conversion rate of {USD_TO_EUR}")
        eur_usd_rates = pd.Series(
            USD_TO_EUR,
            index=pd.date_range(start_date.date(), end_date.date())
        )
    
    # Step 3: Process transactions
    print("\n[3/4] Processing transactions...")
    rows = []
    
    # Get all unique dates (filter out NaT)
    df_full_clean = df_full[df_full['Datum'].notna()].copy()
    unique_dates = df_full_clean['Datum'].dt.date.unique()
    unique_dates = sorted([d for d in unique_dates if d is not None])
    
    print(f"Processing {len(unique_dates)} unique dates...")
    
    for date in unique_dates:
        # Get all transactions for this date
        date_transactions = df_full_clean[df_full_clean['Datum'].dt.date == date].copy()
        
        # Sort by time (earliest first)
        date_transactions = date_transactions.sort_values('Datum_Tijd')
        
        # EOD timestamp for grouping
        eod_timestamp = pd.Timestamp.combine(date, pd.Timestamp("23:59:59").time())
        
        # Process stock transactions (Koop/Verkoop)
        stock_transactions = date_transactions[
            date_transactions['ISIN'].notna() & 
            date_transactions['Omschrijving'].str.contains('Koop|Verkoop', na=False)
        ]
        
        # Deduplicate by Order Id - keep the one with the latest timestamp (most recent state)
        if 'Order Id' in stock_transactions.columns and not stock_transactions.empty:
            stock_transactions = stock_transactions.sort_values('Datum_Tijd', ascending=False)
            stock_transactions = stock_transactions.drop_duplicates(subset=['Order Id', 'Omschrijving'], keep='first')
            stock_transactions = stock_transactions.sort_values('Datum_Tijd', ascending=True)  # Re-sort chronologically
        
        for _, trans in stock_transactions.iterrows():
            product = trans['Product']
            omschrijving = trans['Omschrijving']
            
            # Extract shares from description
            shares_match = re.search(r'(?:Koop|Verkoop)\s+(\d+)', omschrijving)
            shares = float(shares_match.group(1)) if shares_match else 0
            
            # Make sells negative
            if 'Verkoop' in omschrijving:
                shares = -shares
            
            # Get FX rate for this transaction
            fx_rate = get_fx_rate_for_transaction(trans, eur_usd_rates)
            
            # Extract or calculate price per share
            price_per_share = extract_transaction_price(
                omschrijving, 
                trans['MutatieAmount'], 
                shares,
                fx_rate if product in usd_stocks else None
            )
            
            # Get transaction amount in EUR
            # For USD stocks, find the EUR debitering transaction
            amount_eur = None
            if product in usd_stocks:
                # Find corresponding EUR transaction (Valuta Debitering)
                order_id = trans.get('Order Id', '')
                if order_id:
                    eur_trans = date_transactions[
                        (date_transactions['Order Id'] == order_id) &
                        (date_transactions['Omschrijving'].str.contains('Valuta Debitering', na=False))
                    ]
                    if not eur_trans.empty:
                        amount_eur = abs(eur_trans.iloc[0]['MutatieAmount'])
            else:
                amount_eur = abs(trans['MutatieAmount'])
            
            if amount_eur is None:
                # Fallback: use MutatieAmount and convert if needed
                if product in usd_stocks and fx_rate:
                    amount_eur = abs(trans['MutatieAmount']) * fx_rate
                else:
                    amount_eur = abs(trans['MutatieAmount'])
            
            # Get cash balance (SaldoAmount from the transaction)
            cash_balance = trans['SaldoAmount'] if pd.notna(trans['SaldoAmount']) else None
            
            rows.append({
                'Date': date.strftime('%Y-%m-%d'),
                'Transaction_Time': trans['Datum_Tijd'].strftime('%H:%M:%S'),
                'Type': 'BUY' if 'Koop' in omschrijving else 'SELL',
                'Ticker': ticker_map.get(product, 'N/A'),
                'Name': product,
                'Description': omschrijving,
                'Shares': shares,
                'Price_Per_Share_EUR': round(price_per_share, 4) if price_per_share else None,
                'Amount_EUR': round(amount_eur, 2),
                'Cash_Balance_EUR': round(cash_balance, 2) if cash_balance is not None else None
            })
        
        # Process cash transactions (deposits, withdrawals, transfers)
        cash_transactions = date_transactions[
            date_transactions['ISIN'].isna() &
            (
                date_transactions['Omschrijving'].str.contains('deposit|Deposit|Overboeking|Degiro Cash Sweep', case=False, na=False) |
                (date_transactions['MutatieAmount'].notna() & date_transactions['MutatieAmount'] != 0)
            )
        ]
        
        # Filter out currency conversion transactions (Valuta Creditering/Debitering) and fees
        cash_transactions = cash_transactions[
            ~cash_transactions['Omschrijving'].str.contains(
                'Valuta Creditering|Valuta Debitering|Transactiebelasting|DEGIRO Transactiekosten',
                case=False, na=False
            )
        ]
        
        for _, trans in cash_transactions.iterrows():
            omschrijving = trans['Omschrijving']
            mutatie_amount = trans['MutatieAmount']
            
            # Skip if no amount
            if pd.isna(mutatie_amount) or mutatie_amount == 0:
                continue
            
            # Determine type
            if 'deposit' in omschrijving.lower() or 'Overboeking' in omschrijving:
                trans_type = 'DEPOSIT'
            elif 'withdraw' in omschrijving.lower() or mutatie_amount < 0:
                trans_type = 'WITHDRAWAL'
            else:
                trans_type = 'CASH_TRANSFER'
            
            # Get cash balance
            cash_balance = trans['SaldoAmount'] if pd.notna(trans['SaldoAmount']) else None
            
            rows.append({
                'Date': date.strftime('%Y-%m-%d'),
                'Transaction_Time': trans['Datum_Tijd'].strftime('%H:%M:%S'),
                'Type': trans_type,
                'Ticker': 'CASH',
                'Name': 'Cash',
                'Description': omschrijving,
                'Shares': None,
                'Price_Per_Share_EUR': None,
                'Amount_EUR': round(mutatie_amount, 2),
                'Cash_Balance_EUR': round(cash_balance, 2) if cash_balance is not None else None
            })
    
    # Step 4: Create DataFrame and save
    print("\n[4/4] Generating CSV file...")
    result_df = pd.DataFrame(rows)
    
    # Sort by date and time
    result_df = result_df.sort_values(['Date', 'Transaction_Time'])
    
    # Save to CSV
    result_df.to_csv(output_file, index=False)
    
    print(f"\n[SUCCESS] Successfully generated {output_file}")
    print(f"  Total transactions: {len(result_df)}")
    print(f"  Date range: {result_df['Date'].min()} to {result_df['Date'].max()}")
    print(f"  Unique dates: {result_df['Date'].nunique()}")
    print(f"  Transaction types: {result_df['Type'].value_counts().to_dict()}")
    
    return result_df

if __name__ == "__main__":
    # Allow command line arguments
    account_file = sys.argv[1] if len(sys.argv) > 1 else 'Account.csv'
    ticker_file = sys.argv[2] if len(sys.argv) > 2 else 'tickers.csv'
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'portfolio_daily_eod.csv'
    
    # Check if files exist
    if not os.path.exists(account_file):
        print(f"Error: {account_file} not found!")
        sys.exit(1)
    
    if not os.path.exists(ticker_file):
        print(f"Error: {ticker_file} not found!")
        sys.exit(1)
    
    try:
        result_df = generate_transactions_eod_csv(account_file, ticker_file, output_file)
        print("\n" + "="*60)
        print("Done!")
        print("="*60)
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

