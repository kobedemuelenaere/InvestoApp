"""
Standalone script to generate a CSV file with daily portfolio history.
This script uses all the existing functions but doesn't interfere with the app.

Output CSV format:
- Date, Ticker, Name, Shares, Value_Per_Share_EUR, Total_Value_EUR
- One row per day per position (stocks, CASH, PORTFOLIO)
"""

import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Import utility modules
from investo_utils.data_loader import (
    prepare_account_csv,
    load_ticker_mappings,
    load_transaction_data,
    get_stock_prices,
    get_historical_eur_usd_rates
)
from investo_utils.portfolio import (
    get_holdings_at_date,
    get_cash_at_date
)

# Default USD to EUR conversion rate as fallback
USD_TO_EUR = 0.97

def generate_portfolio_history_csv(
    account_file='Account.csv',
    ticker_file='tickers.csv',
    output_file='portfolio_history.csv'
):
    """
    Generate a CSV file with daily portfolio positions and values.
    
    Args:
        account_file: Path to Account.csv
        ticker_file: Path to tickers.csv
        output_file: Path to output CSV file
    """
    print("="*60)
    print("Portfolio History CSV Generator")
    print("="*60)
    
    # Step 1: Load data
    print("\n[1/5] Loading account data and ticker mappings...")
    prepare_account_csv(account_file)
    ticker_map, usd_stocks = load_ticker_mappings(ticker_file)
    df, cash_df = load_transaction_data(account_file)
    
    # Step 2: Determine date range
    print("\n[2/5] Determining date range...")
    start_date = min(df['Datum_Tijd'].min(), cash_df['Datum_Tijd'].min())
    end_date = pd.Timestamp.now()
    
    # Use only dates (one per day)
    start_date = start_date.date()
    end_date = end_date.date()
    
    print(f"Date range: {start_date} to {end_date}")
    
    # Step 3: Fetch stock price data
    print("\n[3/5] Fetching stock price data...")
    price_data = {}
    stocks = df['Product'].unique()
    
    for stock in stocks:
        if stock in ticker_map:
            ticker = ticker_map[stock]
            print(f"  Fetching prices for {stock} ({ticker})...")
            prices = get_stock_prices(ticker, start_date, end_date)
            if prices is not None:
                price_data[stock] = prices
                currency = "USD" if stock in usd_stocks else "EUR"
                print(f"    [OK] Successfully fetched {len(prices)} days of data")
            else:
                print(f"    [FAIL] Failed to fetch prices for {stock}")
        else:
            print(f"  [WARN] No ticker mapping found for {stock}, skipping...")
    
    # Step 4: Fetch EUR/USD conversion rates
    print("\n[4/5] Fetching EUR/USD conversion rates...")
    eur_usd_rates = get_historical_eur_usd_rates(
        pd.Timestamp(start_date),
        pd.Timestamp(end_date)
    )
    if eur_usd_rates is None:
        print(f"  Using fallback USD to EUR conversion rate of {USD_TO_EUR}")
        eur_usd_rates = pd.Series(
            USD_TO_EUR,
            index=pd.date_range(start_date, end_date)
        )
    
    # Step 5: Calculate daily positions and generate CSV
    print("\n[5/5] Calculating daily positions and generating CSV...")
    
    # Prepare list to store all rows
    rows = []
    
    # Generate dates (one per day)
    # Use end of day (23:59:59) to ensure we capture all transactions for that day
    current_date = start_date
    date_count = 0
    
    while current_date <= end_date:
        # Use end of day timestamp to capture all transactions for that day
        date_timestamp = pd.Timestamp.combine(current_date, pd.Timestamp("23:59:59").time())
        date_count += 1
        
        if date_count % 50 == 0:
            print(f"  Processing date {current_date}...")
        
        # Get holdings and cash for this date
        holdings = get_holdings_at_date(df, date_timestamp)
        cash_position = get_cash_at_date(cash_df, date_timestamp)
        
        # Get EUR/USD rate for this date
        eur_usd_rate = eur_usd_rates.asof(date_timestamp)
        if pd.isna(eur_usd_rate):
            eur_usd_rate = USD_TO_EUR
        
        # Calculate total portfolio value
        total_portfolio_value = cash_position
        
        # Process each stock
        for stock in stocks:
            shares = holdings.get(stock, 0)
            
            # Only include positions with non-zero shares
            if shares != 0:
                # Get price for this date
                if stock in price_data:
                    try:
                        price = price_data[stock].asof(date_timestamp)
                        if pd.isna(price):
                            # No price data available, skip this position
                            continue
                        
                        # Convert USD to EUR if needed
                        if stock in usd_stocks:
                            price_eur = price * eur_usd_rate
                        else:
                            price_eur = price
                        
                        total_value = shares * price_eur
                        total_portfolio_value += total_value
                        
                        # Add row for this stock
                        rows.append({
                            'Date': current_date.strftime('%Y-%m-%d'),
                            'Ticker': ticker_map.get(stock, 'N/A'),
                            'Name': stock,
                            'Shares': shares,
                            'Value_Per_Share_EUR': round(price_eur, 4),
                            'Total_Value_EUR': round(total_value, 2)
                        })
                    except Exception as e:
                        print(f"    Error processing {stock} on {current_date}: {str(e)}")
                        continue
        
        # Add CASH row
        rows.append({
            'Date': current_date.strftime('%Y-%m-%d'),
            'Ticker': 'CASH',
            'Name': 'Cash',
            'Shares': 1,  # Not applicable for cash, but keeping format consistent
            'Value_Per_Share_EUR': round(cash_position, 2),
            'Total_Value_EUR': round(cash_position, 2)
        })
        
        # Add PORTFOLIO total row
        rows.append({
            'Date': current_date.strftime('%Y-%m-%d'),
            'Ticker': 'PORTFOLIO',
            'Name': 'Total Portfolio',
            'Shares': 1,  # Not applicable for portfolio total
            'Value_Per_Share_EUR': round(total_portfolio_value, 2),
            'Total_Value_EUR': round(total_portfolio_value, 2)
        })
        
        current_date += timedelta(days=1)
    
    # Create DataFrame and save to CSV
    print(f"\nGenerating CSV file with {len(rows)} rows...")
    result_df = pd.DataFrame(rows)
    
    # Sort by date and then by ticker (CASH first, then stocks alphabetically, then PORTFOLIO)
    def sort_key(row):
        date = row['Date']
        ticker = row['Ticker']
        if ticker == 'CASH':
            return (date, 0)
        elif ticker == 'PORTFOLIO':
            return (date, 999)
        else:
            return (date, 1)
    
    result_df['_sort_key'] = result_df.apply(sort_key, axis=1)
    result_df = result_df.sort_values('_sort_key').drop('_sort_key', axis=1)
    
    # Save to CSV
    result_df.to_csv(output_file, index=False)
    
    print(f"\n[SUCCESS] Successfully generated {output_file}")
    print(f"  Total rows: {len(result_df)}")
    print(f"  Date range: {result_df['Date'].min()} to {result_df['Date'].max()}")
    print(f"  Unique dates: {result_df['Date'].nunique()}")
    print(f"  Unique positions: {result_df['Ticker'].nunique()}")
    
    return result_df

if __name__ == "__main__":
    # Allow command line arguments
    account_file = sys.argv[1] if len(sys.argv) > 1 else 'Account.csv'
    ticker_file = sys.argv[2] if len(sys.argv) > 2 else 'tickers.csv'
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'portfolio_history.csv'
    
    # Check if files exist
    if not os.path.exists(account_file):
        print(f"Error: {account_file} not found!")
        sys.exit(1)
    
    if not os.path.exists(ticker_file):
        print(f"Error: {ticker_file} not found!")
        sys.exit(1)
    
    try:
        result_df = generate_portfolio_history_csv(account_file, ticker_file, output_file)
        print("\n" + "="*60)
        print("Done!")
        print("="*60)
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

