import pandas as pd
from datetime import datetime, timedelta
from tqdm import tqdm

def get_holdings_at_date(transactions_df, target_date):
    """Calculate holdings for each stock at a specific date"""
    # Filter transactions up to target date
    past_transactions = transactions_df[transactions_df['Datum_Tijd'] <= target_date]
    
    # Group by stock and sum the quantities
    holdings = past_transactions.groupby('Product')['Aantal'].sum()
    return holdings

def get_cash_at_date(cash_transactions_df, target_date):
    """Get cash position at a specific date by finding the last SaldoAmount from newest entries"""
    # Filter transactions up to target date and time, excluding transfers and USD transactions
    past_transactions = cash_transactions_df[
        (cash_transactions_df['Datum_Tijd'] <= target_date) &
        (~cash_transactions_df['Omschrijving'].str.contains('Overboeking|Degiro Cash Sweep Transfer', na=False)) &
        (cash_transactions_df['Saldo'] != 'USD')
    ]
    
    if past_transactions.empty:
        return 0
    
    # Get the first row (newest transaction) since CSV is ordered from new to old
    return past_transactions.iloc[0]['SaldoAmount']

def get_total_deposits_at_date(cash_transactions_df, target_date):
    """Calculate total deposits up to a specific date"""
    # Filter transactions up to target date
    past_transactions = cash_transactions_df[cash_transactions_df['Datum_Tijd'] <= target_date]
    
    if past_transactions.empty:
        return 0
    
    # Filter for deposit transactions (both flatex and sofort)
    deposits = past_transactions[
        past_transactions['Omschrijving'].str.contains('deposit', case=False, na=False)
    ]['MutatieAmount'].sum()
    
    return deposits if pd.notna(deposits) else 0

def calculate_daily_holdings_and_values(df, cash_df, price_data, ticker_map, usd_stocks, usd_to_eur=0.97):
    """Calculate daily holdings and values for the portfolio"""
    # Get start date from first transaction
    start_date = min(df['Datum_Tijd'].min(), cash_df['Datum_Tijd'].min())
    # Use today as end date
    end_date = pd.Timestamp.now()
    
    print(f"\n📅 Analyzing period from {start_date.date()} to {end_date.date()}")
    
    # Fetch historical EUR/USD rates
    from investo_utils.data_loader import get_historical_eur_usd_rates
    eur_usd_rates = get_historical_eur_usd_rates(start_date, end_date)
    if eur_usd_rates is None:
        print(f"⚠️  Using fallback USD to EUR conversion rate of {usd_to_eur}")
        eur_usd_rates = pd.Series(usd_to_eur, index=pd.date_range(start_date, end_date))
    
    # Create a list of all timestamps (every 3 hours from 6:00 to 21:00 for each day)
    dates = []
    current_date = start_date.date()
    end_date = end_date.date()
    
    while current_date <= end_date:
        for hour in [9, 12, 15, 18, 21]:
            dates.append(pd.Timestamp.combine(current_date, pd.Timestamp(f"{hour:02d}:00").time()))
        current_date += timedelta(days=1)
    
    # Dictionary to store holdings and values data for each stock
    all_holdings = {'Cash': []}  # Initialize with cash
    all_values = {'Cash': []}
    total_deposits = []  # Store total deposits for each date
    
    # Get unique stocks
    stocks = df['Product'].unique()
    
    # Initialize dictionaries for each stock
    for stock in stocks:
        all_holdings[stock] = []
        all_values[stock] = []
    
    # Calculate holdings and values for each timestamp
    print("\n🧮 Calculating holdings and values...")
    
    for date in tqdm(dates, desc="Processing values", unit="timestamp"):
        holdings = get_holdings_at_date(df, date)
        cash_position = get_cash_at_date(cash_df, date)
        deposits = get_total_deposits_at_date(cash_df, date)
        
        # Get EUR/USD rate for this date
        eur_usd_rate = eur_usd_rates.asof(date)
        if pd.isna(eur_usd_rate):
            eur_usd_rate = usd_to_eur  # Fallback to default rate if no data
            print(f"⚠️  Warning: No EUR/USD rate data found for {date}, using fallback rate of {usd_to_eur}")
        
        # Store total deposits
        total_deposits.append((date, deposits))
        
        # Add cash position
        all_holdings['Cash'].append((date, cash_position))
        all_values['Cash'].append((date, cash_position))  # Cash value is same as position
        
        # Store holdings and calculate values for each stock
        for stock in stocks:
            holding = holdings.get(stock, 0)  # Get holding or 0 if no holding
            all_holdings[stock].append((date, holding))
            
            # Calculate value if we have price data
            if stock in price_data:
                try:
                    # Get the closest available price (using asof for proper date alignment)
                    price = price_data[stock].asof(date)
                    if pd.isna(price):
                        value = 0
                        print(f"⚠️  Warning: No price data found for {stock} on {date}")
                    else:
                        # Convert USD to EUR using historical rate if needed
                        if stock in usd_stocks:
                            # Historical rate already gives us USD to EUR conversion factor
                            value = holding * price * eur_usd_rate
                            # print(f"💱 Converted USD price to EUR using rate: 1 USD = {eur_usd_rate:.4f} EUR")
                        else:
                            value = holding * price
                except Exception as e:
                    print(f"❌ Error calculating value for {stock} on {date}: {str(e)}")
                    value = 0
            else:
                value = 0
            
            all_values[stock].append((date, value))
    
    return all_values, dates, total_deposits 