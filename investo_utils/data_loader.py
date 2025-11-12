import pandas as pd
import yfinance_cache as yf
from datetime import datetime, timedelta
import pytz
from tqdm import tqdm

def prepare_account_csv(file_path='Account.csv'):
    """Prepare the account CSV file by fixing the header row."""
    print("Preparing CSV file...")
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Define the header we want
    new_header = "Datum,Tijd,Valutadatum,Product,ISIN,Omschrijving,FX,Mutatie,MutatieAmount,Saldo,SaldoAmount,Order Id\n"

    # Replace the first line with our header
    lines[0] = new_header

    # Write the modified content back to file
    with open(file_path, 'w') as file:
        file.writelines(lines)
        
    return file_path

def load_ticker_mappings(file_path='tickers.csv'):
    """Load ticker mappings from CSV file."""
    print("Loading ticker mappings...")
    ticker_df = pd.read_csv(file_path)

    # Create ticker mapping dictionary
    ticker_map = dict(zip(ticker_df['Product'], ticker_df['Ticker']))

    # Create USD stocks set
    usd_stocks = set(ticker_df[ticker_df['USD'] == True]['Product'])
    
    return ticker_map, usd_stocks

def load_transaction_data(file_path='Account.csv'):
    """Load and preprocess transaction data."""
    print("Loading transaction data...")
    df = pd.read_csv(file_path)
    
    # Filter out Flatex Interest Income entries with 0.00 amounts
    print("Filtering out zero-value Flatex Interest Income entries...")
    initial_rows = len(df)
    
    # Convert numeric columns to handle the filtering
    # Handle European number format (comma as decimal separator) by replacing with dot
    df['MutatieAmount'] = pd.to_numeric(
        df['MutatieAmount'].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    )
    
    # Filter out the unwanted rows
    df = df[~((df['Omschrijving'] == 'Flatex Interest Income') & 
              (df['MutatieAmount'] == 0.00))]
    
    filtered_rows = initial_rows - len(df)
    print(f"Removed {filtered_rows} zero-value Flatex Interest Income entries")
    
    # Create a separate dataframe for cash transactions
    cash_df = df.copy()

    # Convert numeric columns, handling missing values (MutatieAmount already converted above)
    # Handle European number format (comma as decimal separator) by replacing with dot
    cash_df['SaldoAmount'] = pd.to_numeric(
        cash_df['SaldoAmount'].astype(str).str.replace(',', '.', regex=False),
        errors='coerce'
    )

    # Convert date and time columns to datetime
    df['Datum'] = pd.to_datetime(df['Datum'], format='%d-%m-%Y')
    cash_df['Datum'] = pd.to_datetime(cash_df['Datum'], format='%d-%m-%Y')

    # Handle time column
    df['Tijd'] = df['Tijd'].fillna('00:00')
    cash_df['Tijd'] = cash_df['Tijd'].fillna('00:00')

    # Combine date and time into a single datetime column
    df['Datum_Tijd'] = pd.to_datetime(df['Datum'].dt.strftime('%Y-%m-%d') + ' ' + df['Tijd'])
    cash_df['Datum_Tijd'] = pd.to_datetime(cash_df['Datum'].dt.strftime('%Y-%m-%d') + ' ' + cash_df['Tijd'])

    # Remove rows with NaT values but keep original order
    cash_df = cash_df.dropna(subset=['Datum_Tijd'])

    # Filter for actual stock transactions (rows with ISIN and 'Koop' or 'Verkoop' in Omschrijving)
    df = df[df['ISIN'].notna() & (df['Omschrijving'].str.contains('Koop|Verkoop', na=False))]

    # Extract quantity from Omschrijving using regex
    df['Aantal'] = df['Omschrijving'].str.extract(r'(?:Koop|Verkoop) (\d+)').astype(float)
    # Make sells negative
    df.loc[df['Omschrijving'].str.contains('Verkoop', na=False), 'Aantal'] *= -1
    
    return df, cash_df

def get_stock_prices(ticker, start_date, end_date):
    """Fetch historical stock prices for a given ticker"""
    try:
        stock = yf.Ticker(ticker)
        
        # Convert to datetime if needed
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
        
        # Get daily data
        hist = stock.history(start=start_date, end=end_date + timedelta(days=1))
        
        if hist.empty:
            print(f"  Warning: No price data found for {ticker}")
            return None
            
        # Use Close price for the values
        prices = hist['Close']
        # Convert index to timezone-naive datetime
        prices.index = prices.index.tz_localize(None)
        print(f"  Successfully fetched {len(prices)} days of data for {ticker}")
        
        return prices
        
    except Exception as e:
        print(f"  Error fetching data for {ticker}: {str(e)}")
        return None

def get_historical_eur_usd_rates(start_date, end_date):
    """Fetch historical EUR/USD conversion rates"""
    print("\nFetching historical EUR/USD rates...")
    try:
        # Get EUR/USD data
        eur_usd = yf.Ticker("EURUSD=X")
        
        # Get daily data
        hist = eur_usd.history(start=start_date, end=end_date + timedelta(days=1))
        
        if hist.empty:
            print("  Warning: No EUR/USD rate data found")
            return None
            
        # Use Close price for the rates
        rates = hist['Close']
        # Convert index to timezone-naive datetime
        rates.index = rates.index.tz_localize(None)
        
        # Convert to USD/EUR (reciprocal)
        # IMPORTANT: Yahoo Finance EURUSD=X gives how many USD for 1 EUR
        # For USD to EUR conversion, we need the reciprocal (1/rate)
        rates = 1 / rates
        
        print(f"  Successfully fetched {len(rates)} days of EUR/USD rates")
        print(f"  Sample rate: 1 USD = {rates.iloc[-1]:.4f} EUR")
        
        return rates
        
    except Exception as e:
        print(f"  Error fetching EUR/USD rates: {str(e)}")
        return None 