"""
Diagnostic script to find where NaN values are introduced in portfolio calculations.
This script traces through the entire calculation pipeline and reports NaN values at each step.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to the path so we can import investo_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from investo_utils.data_loader import (
    prepare_account_csv,
    load_ticker_mappings,
    load_transaction_data,
    get_stock_prices
)
from investo_utils.portfolio import (
    get_holdings_at_date,
    get_cash_at_date,
    get_total_deposits_at_date,
    calculate_daily_holdings_and_values
)

# Get parent directory for CSV files
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNT_CSV = os.path.join(PARENT_DIR, 'Account.csv')
TICKERS_CSV = os.path.join(PARENT_DIR, 'tickers.csv')

def check_for_nan(df, name):
    """Check for NaN values in a DataFrame and report them"""
    print(f"\n{'='*60}")
    print(f"Checking {name}")
    print(f"{'='*60}")
    
    if df is None:
        print(f"  ERROR: {name} is None!")
        return True
    
    if isinstance(df, pd.DataFrame):
        nan_counts = df.isna().sum()
        total_nans = nan_counts.sum()
        
        if total_nans > 0:
            print(f"  WARNING: Found {total_nans} NaN values in {name}")
            print(f"  NaN breakdown by column:")
            for col, count in nan_counts.items():
                if count > 0:
                    print(f"    - {col}: {count} NaN values")
                    # Show sample rows with NaN
                    nan_rows = df[df[col].isna()]
                    if len(nan_rows) > 0:
                        print(f"      Sample rows with NaN in {col}:")
                        for idx, row in nan_rows.head(3).iterrows():
                            print(f"        Row {idx}: {row.to_dict()}")
            return True
        else:
            print(f"  OK: No NaN values found")
            return False
    elif isinstance(df, pd.Series):
        nan_count = df.isna().sum()
        if nan_count > 0:
            print(f"  WARNING: Found {nan_count} NaN values in {name}")
            print(f"  Sample NaN values:")
            nan_values = df[df.isna()]
            print(f"    {nan_values.head(5).to_dict()}")
            return True
        else:
            print(f"  OK: No NaN values found")
            return False
    else:
        print(f"  INFO: {name} is not a DataFrame or Series (type: {type(df)})")
        return False

def check_value_for_nan(value, name):
    """Check if a single value is NaN"""
    if pd.isna(value):
        print(f"  ERROR: {name} is NaN!")
        return True
    elif isinstance(value, (int, float)) and np.isnan(value):
        print(f"  ERROR: {name} is NaN (numpy)!")
        return True
    else:
        return False

def diagnose_data_loading():
    """Diagnose data loading step"""
    print("\n" + "="*80)
    print("STEP 1: DATA LOADING")
    print("="*80)
    
    # Check if files exist
    if not os.path.exists(ACCOUNT_CSV):
        print(f"ERROR: Account.csv not found at {ACCOUNT_CSV}!")
        return None, None, None, None
    
    if not os.path.exists(TICKERS_CSV):
        print(f"ERROR: tickers.csv not found at {TICKERS_CSV}!")
        return None, None, None, None
    
    # Prepare CSV
    print("\nPreparing Account.csv...")
    prepare_account_csv(ACCOUNT_CSV)
    
    # Load ticker mappings
    print("\nLoading ticker mappings...")
    ticker_map, usd_stocks = load_ticker_mappings(TICKERS_CSV)
    print(f"  Loaded {len(ticker_map)} ticker mappings")
    print(f"  USD stocks: {usd_stocks}")
    
    # Load transaction data
    print("\nLoading transaction data...")
    df, cash_df = load_transaction_data(ACCOUNT_CSV)
    
    # Check for NaN in loaded data
    has_nan = False
    has_nan |= check_for_nan(df, "Transaction DataFrame (df)")
    has_nan |= check_for_nan(cash_df, "Cash DataFrame (cash_df)")
    
    # Check specific columns that are used in calculations
    print("\nChecking critical columns:")
    
    # Check Aantal column
    if 'Aantal' in df.columns:
        aantal_nans = df['Aantal'].isna().sum()
        if aantal_nans > 0:
            print(f"  WARNING: 'Aantal' has {aantal_nans} NaN values")
            print(f"  Rows with NaN in Aantal:")
            nan_aantal = df[df['Aantal'].isna()]
            for idx, row in nan_aantal.head(5).iterrows():
                print(f"    Row {idx}: Product={row.get('Product', 'N/A')}, Omschrijving={row.get('Omschrijving', 'N/A')}")
        else:
            print(f"  OK: 'Aantal' has no NaN values")
    
    # Check SaldoAmount column
    if 'SaldoAmount' in cash_df.columns:
        saldo_nans = cash_df['SaldoAmount'].isna().sum()
        if saldo_nans > 0:
            print(f"  WARNING: 'SaldoAmount' has {saldo_nans} NaN values")
            print(f"  Sample rows with NaN in SaldoAmount:")
            nan_saldo = cash_df[cash_df['SaldoAmount'].isna()]
            for idx, row in nan_saldo.head(5).iterrows():
                print(f"    Row {idx}: Omschrijving={row.get('Omschrijving', 'N/A')}, Saldo={row.get('Saldo', 'N/A')}")
        else:
            print(f"  OK: 'SaldoAmount' has no NaN values")
    
    # Check MutatieAmount column
    if 'MutatieAmount' in cash_df.columns:
        mutatie_nans = cash_df['MutatieAmount'].isna().sum()
        if mutatie_nans > 0:
            print(f"  WARNING: 'MutatieAmount' has {mutatie_nans} NaN values")
        else:
            print(f"  OK: 'MutatieAmount' has no NaN values")
    
    return df, cash_df, ticker_map, usd_stocks

def diagnose_price_loading(df, cash_df, ticker_map, usd_stocks):
    """Diagnose price data loading"""
    print("\n" + "="*80)
    print("STEP 2: PRICE DATA LOADING")
    print("="*80)
    
    stocks = df['Product'].unique()
    start_date = min(df['Datum_Tijd'].min(), cash_df['Datum_Tijd'].min())
    end_date = pd.Timestamp.now()
    
    print(f"\nFetching prices for {len(stocks)} stocks")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    
    price_data = {}
    price_issues = []
    
    for stock in stocks:
        if stock in ticker_map:
            ticker = ticker_map[stock]
            print(f"\n  Processing {stock} ({ticker})...")
            prices = get_stock_prices(ticker, start_date, end_date)
            
            if prices is None:
                print(f"    ERROR: No price data returned for {stock}")
                price_issues.append(f"{stock}: No price data")
            else:
                # Check for NaN in price data
                nan_prices = prices.isna().sum()
                if nan_prices > 0:
                    print(f"    WARNING: {nan_prices} NaN values in price data")
                    price_issues.append(f"{stock}: {nan_prices} NaN prices")
                else:
                    print(f"    OK: {len(prices)} price points, no NaN values")
                    print(f"    Price range: {prices.min():.2f} - {prices.max():.2f}")
                
                price_data[stock] = prices
        else:
            print(f"  WARNING: No ticker mapping for {stock}")
            price_issues.append(f"{stock}: No ticker mapping")
    
    if price_issues:
        print(f"\n  SUMMARY: {len(price_issues)} price loading issues found")
        for issue in price_issues:
            print(f"    - {issue}")
    
    return price_data

def diagnose_calculations(df, cash_df, price_data, ticker_map, usd_stocks):
    """Diagnose calculation functions"""
    print("\n" + "="*80)
    print("STEP 3: CALCULATION FUNCTIONS")
    print("="*80)
    
    # Test get_holdings_at_date
    print("\nTesting get_holdings_at_date...")
    test_date = df['Datum_Tijd'].max()
    holdings = get_holdings_at_date(df, test_date)
    
    if isinstance(holdings, pd.Series):
        nan_holdings = holdings.isna().sum()
        if nan_holdings > 0:
            print(f"  ERROR: {nan_holdings} NaN values in holdings")
            print(f"  Stocks with NaN holdings:")
            for stock, holding in holdings.items():
                if pd.isna(holding):
                    print(f"    - {stock}: NaN")
        else:
            print(f"  OK: No NaN holdings")
            print(f"  Sample holdings:")
            for stock, holding in holdings.head(5).items():
                print(f"    - {stock}: {holding}")
    else:
        print(f"  ERROR: holdings is not a Series: {type(holdings)}")
    
    # Test get_cash_at_date
    print("\nTesting get_cash_at_date...")
    test_dates = [df['Datum_Tijd'].min(), df['Datum_Tijd'].max(), pd.Timestamp.now()]
    cash_issues = []
    
    for test_date in test_dates:
        cash = get_cash_at_date(cash_df, test_date)
        if check_value_for_nan(cash, f"Cash at {test_date}"):
            cash_issues.append(f"Cash at {test_date} is NaN")
        else:
            print(f"  OK: Cash at {test_date}: {cash}")
    
    if cash_issues:
        print(f"\n  SUMMARY: Found {len(cash_issues)} cash NaN issues")
        for issue in cash_issues:
            print(f"    - {issue}")
    
    # Test get_total_deposits_at_date
    print("\nTesting get_total_deposits_at_date...")
    deposit_issues = []
    
    for test_date in test_dates:
        deposits = get_total_deposits_at_date(cash_df, test_date)
        if check_value_for_nan(deposits, f"Deposits at {test_date}"):
            deposit_issues.append(f"Deposits at {test_date} is NaN")
        else:
            print(f"  OK: Deposits at {test_date}: {deposits}")
    
    if deposit_issues:
        print(f"\n  SUMMARY: Found {len(deposit_issues)} deposit NaN issues")
        for issue in deposit_issues:
            print(f"    - {issue}")
    
    return holdings, cash_issues, deposit_issues

def diagnose_full_calculation(df, cash_df, price_data, ticker_map, usd_stocks):
    """Run full calculation and trace NaN values"""
    print("\n" + "="*80)
    print("STEP 4: FULL CALCULATION TRACE")
    print("="*80)
    
    # Run calculation with detailed tracing
    print("\nRunning calculate_daily_holdings_and_values...")
    
    # We'll trace a few dates manually first
    start_date = min(df['Datum_Tijd'].min(), cash_df['Datum_Tijd'].min())
    end_date = pd.Timestamp.now()
    
    # Create test dates (just a few to trace)
    test_dates = []
    current_date = start_date.date()
    end_date_only = end_date.date()
    date_count = 0
    while current_date <= end_date_only and date_count < 5:  # Just test first 5 dates
        test_dates.append(pd.Timestamp.combine(current_date, pd.Timestamp("12:00").time()))
        current_date += timedelta(days=1)
        date_count += 1
    
    print(f"\nTracing calculations for {len(test_dates)} test dates...")
    
    nan_trace = []
    
    for date in test_dates:
        print(f"\n  Date: {date}")
        
        # Get holdings
        holdings = get_holdings_at_date(df, date)
        for stock, holding in holdings.items():
            if pd.isna(holding):
                nan_trace.append(f"Date {date}: Holding for {stock} is NaN")
        
        # Get cash
        cash = get_cash_at_date(cash_df, date)
        if pd.isna(cash):
            nan_trace.append(f"Date {date}: Cash position is NaN")
        
        # Get deposits
        deposits = get_total_deposits_at_date(cash_df, date)
        if pd.isna(deposits):
            nan_trace.append(f"Date {date}: Deposits is NaN")
        
        # Check price calculations
        stocks = df['Product'].unique()
        for stock in stocks:
            if stock in price_data:
                price = price_data[stock].asof(date)
                if pd.isna(price):
                    # This is OK if there's no price data yet
                    pass
                else:
                    holding = holdings.get(stock, 0)
                    if pd.isna(holding):
                        nan_trace.append(f"Date {date}: Holding for {stock} is NaN when calculating value")
                    else:
                        # Calculate value
                        if stock in usd_stocks:
                            # Need EUR/USD rate
                            from investo_utils.data_loader import get_historical_eur_usd_rates
                            eur_usd_rates = get_historical_eur_usd_rates(start_date, end_date)
                            if eur_usd_rates is not None:
                                eur_usd_rate = eur_usd_rates.asof(date)
                                if pd.isna(eur_usd_rate):
                                    nan_trace.append(f"Date {date}: EUR/USD rate is NaN for {stock}")
                                else:
                                    value = holding * price * eur_usd_rate
                                    if pd.isna(value):
                                        nan_trace.append(f"Date {date}: Calculated value is NaN for {stock} (holding={holding}, price={price}, rate={eur_usd_rate})")
                        else:
                            value = holding * price
                            if pd.isna(value):
                                nan_trace.append(f"Date {date}: Calculated value is NaN for {stock} (holding={holding}, price={price})")
    
    if nan_trace:
        print(f"\n  ERROR: Found {len(nan_trace)} NaN issues during trace:")
        for issue in nan_trace[:20]:  # Show first 20
            print(f"    - {issue}")
        if len(nan_trace) > 20:
            print(f"    ... and {len(nan_trace) - 20} more issues")
    else:
        print(f"\n  OK: No NaN issues found in trace")
    
    # Now run the full calculation
    print("\nRunning full calculation...")
    try:
        all_values, dates, total_deposits = calculate_daily_holdings_and_values(
            df, cash_df, price_data, ticker_map, usd_stocks, 0.97
        )
        
        # Check final results
        print("\nChecking final results...")
        
        # Check total_deposits
        deposit_nans = sum(1 for _, dep in total_deposits if pd.isna(dep))
        if deposit_nans > 0:
            print(f"  ERROR: {deposit_nans} NaN values in total_deposits")
        else:
            print(f"  OK: No NaN in total_deposits")
        
        # Check all_values
        nan_values_count = 0
        for stock, values in all_values.items():
            for date, value in values:
                if pd.isna(value):
                    nan_values_count += 1
                    if nan_values_count <= 5:
                        print(f"  ERROR: NaN value found for {stock} on {date}")
        
        if nan_values_count > 0:
            print(f"  ERROR: Found {nan_values_count} NaN values in all_values")
        else:
            print(f"  OK: No NaN in all_values")
        
        # Calculate total portfolio value
        print("\nCalculating total portfolio values...")
        total_values = []
        for i in range(len(dates)):
            total = sum(values[i][1] for values in all_values.values())
            total_values.append(total)
            if pd.isna(total):
                print(f"  ERROR: Total portfolio value is NaN at index {i} (date: {dates[i]})")
                # Show breakdown
                print(f"    Breakdown:")
                for stock, values in all_values.items():
                    val = values[i][1]
                    if pd.isna(val):
                        print(f"      {stock}: NaN")
                    else:
                        print(f"      {stock}: {val}")
        
        nan_totals = sum(1 for tv in total_values if pd.isna(tv))
        if nan_totals > 0:
            print(f"\n  ERROR: {nan_totals} NaN values in total portfolio values")
            print(f"  First few NaN totals:")
            for i, tv in enumerate(total_values[:10]):
                if pd.isna(tv):
                    print(f"    Index {i}: NaN")
        else:
            print(f"\n  OK: No NaN in total portfolio values")
            print(f"  Total portfolio value range: {min(total_values):.2f} - {max(total_values):.2f}")
        
        return all_values, dates, total_deposits
        
    except Exception as e:
        print(f"\n  ERROR during calculation: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None

def main():
    """Main diagnostic function"""
    print("="*80)
    print("NaN DIAGNOSTIC TOOL")
    print("="*80)
    print("\nThis script will trace through the entire calculation pipeline")
    print("to identify where NaN values are introduced.\n")
    
    # Step 1: Data loading
    df, cash_df, ticker_map, usd_stocks = diagnose_data_loading()
    if df is None:
        print("\nERROR: Could not load data. Exiting.")
        return
    
    # Step 2: Price loading
    price_data = diagnose_price_loading(df, cash_df, ticker_map, usd_stocks)
    
    # Step 3: Test calculation functions
    holdings, cash_issues, deposit_issues = diagnose_calculations(df, cash_df, price_data, ticker_map, usd_stocks)
    
    # Step 4: Full calculation trace
    all_values, dates, total_deposits = diagnose_full_calculation(df, cash_df, price_data, ticker_map, usd_stocks)
    
    # Final summary
    print("\n" + "="*80)
    print("DIAGNOSTIC SUMMARY")
    print("="*80)
    
    if all_values is not None:
        # Check final total
        if len(dates) > 0:
            final_total = sum(values[-1][1] for values in all_values.values())
            if pd.isna(final_total):
                print("\n*** CRITICAL ERROR: Final total portfolio value is NaN ***")
                print("\nBreakdown of final values:")
                for stock, values in all_values.items():
                    val = values[-1][1]
                    status = "NaN" if pd.isna(val) else f"{val:.2f}"
                    print(f"  {stock}: {status}")
            else:
                print(f"\nFinal total portfolio value: {final_total:.2f}")
    
    print("\nDiagnostic complete!")

if __name__ == "__main__":
    main()

