import pandas as pd
import tkinter as tk
from tkinter import ttk
import os
import threading
import yfinance_cache as yf
from datetime import datetime, timedelta

def get_stock_names_from_account(account_file='Account.csv'):
    """Extract unique stock names from the account file"""
    print("Scanning Account.csv for stock names...")
    
    # First prepare the CSV file to ensure it has the right headers
    from investo_utils.data_loader import prepare_account_csv
    prepare_account_csv(account_file)
    
    # Load the data
    df = pd.read_csv(account_file)
    
    # Filter for actual stock transactions (rows with ISIN and 'Koop' or 'Verkoop' in Omschrijving)
    stock_df = df[df['ISIN'].notna() & (df['Omschrijving'].str.contains('Koop|Verkoop', na=False))]
    
    # Get unique stock names
    stock_names = stock_df['Product'].unique().tolist()
    
    print(f"Found {len(stock_names)} unique stocks in Account.csv")
    return stock_names

def get_existing_ticker_mappings(ticker_file='tickers.csv'):
    """Load existing ticker mappings if file exists"""
    if os.path.exists(ticker_file):
        print(f"Loading existing ticker mappings from {ticker_file}")
        try:
            # Read CSV with proper boolean handling
            ticker_df = pd.read_csv(ticker_file, dtype={'Product': str, 'Ticker': str, 'USD': bool})
            return ticker_df
        except Exception as e:
            print(f"Error loading ticker file: {e}")
            return pd.DataFrame(columns=['Product', 'Ticker', 'USD'])
    else:
        print(f"No existing ticker file found at {ticker_file}")
        return pd.DataFrame(columns=['Product', 'Ticker', 'USD'])

def merge_stock_lists(account_stocks, ticker_df):
    """Merge stocks from account and existing ticker mappings"""
    all_stocks = set(account_stocks)
    
    if not ticker_df.empty:
        all_stocks.update(ticker_df['Product'].tolist())
    
    result = []
    for stock in all_stocks:
        # Check if stock exists in ticker_df
        if not ticker_df.empty and stock in ticker_df['Product'].values:
            row = ticker_df[ticker_df['Product'] == stock].iloc[0]
            
            # Convert USD value to boolean, handling different possible formats
            is_usd = False
            if not pd.isna(row['USD']):
                usd_val = str(row['USD'])
                is_usd = usd_val.lower() in ('true', 't', 'yes', 'y', '1')
            
            result.append({
                'Product': stock,
                'Ticker': row['Ticker'],
                'USD': is_usd
            })
        else:
            # New stock found in account but not in ticker file
            print(f"New stock found in account but not in ticker file: {stock}")
            result.append({
                'Product': stock,
                'Ticker': '',
                'USD': False
            })
    
    return result

def check_ticker_validity(ticker):
    """Check if a ticker is valid and get its last price"""
    try:
        if not ticker or ticker.strip() == '':
            return False, 0.0, "No ticker"
            
        stock = yf.Ticker(ticker)
        # Get info to check if ticker exists
        info = stock.history(period="2d")
        
        if info.empty:
            return False, 0.0, "Invalid ticker"
            
        # Get most recent closing price
        last_price = info['Close'].iloc[-1]
        return True, last_price, last_price
    except Exception as e:
        return False, 0.0, f"Error: {str(e)}"

def get_ticker_currency(ticker):
    """Get currency for a given ticker symbol from Yahoo Finance"""
    try:
        if not ticker or ticker.strip() == '':
            return None
            
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        
        if 'currency' in info:
            return info['currency']
        else:
            return None
    except Exception as e:
        print(f"Error getting currency for {ticker}: {str(e)}")
        return None

class TickerConfirmationWindow:
    def __init__(self, master, stock_data):
        self.master = master
        self.stock_data = stock_data
        self.result = None
        
        master.title("Confirm Stock Ticker Mappings")
        master.geometry("1000x600")  # Wider window to accommodate price info
        
        # Create main frame
        main_frame = ttk.Frame(master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a scrollable frame
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Headers
        ttk.Label(scrollable_frame, text="Stock Name", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Label(scrollable_frame, text="Ticker Symbol", font=('Arial', 10, 'bold')).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(scrollable_frame, text="USD", font=('Arial', 10, 'bold')).grid(row=0, column=2, padx=5, pady=5, sticky='w')
        ttk.Label(scrollable_frame, text="Last Price", font=('Arial', 10, 'bold')).grid(row=0, column=3, padx=5, pady=5, sticky='w')
        ttk.Label(scrollable_frame, text="Status", font=('Arial', 10, 'bold')).grid(row=0, column=4, padx=5, pady=5, sticky='w')
        ttk.Label(scrollable_frame, text="Currency", font=('Arial', 10, 'bold')).grid(row=0, column=5, padx=5, pady=5, sticky='w')
        
        # Add stock entries
        self.ticker_entries = []
        self.usd_vars = []
        self.price_labels = []
        self.status_labels = []
        self.currency_labels = []
        
        for i, stock in enumerate(stock_data):
            # Stock name (read-only)
            ttk.Label(scrollable_frame, text=stock['Product']).grid(row=i+1, column=0, padx=5, pady=2, sticky='w')
            
            # Ticker entry
            ticker_entry = ttk.Entry(scrollable_frame, width=20)
            ticker_entry.insert(0, stock['Ticker'])
            ticker_entry.grid(row=i+1, column=1, padx=5, pady=2)
            
            # Bind validation to entry field
            ticker_entry.bind("<FocusOut>", lambda e, idx=i: self.validate_ticker(idx))
            ticker_entry.bind("<Return>", lambda e, idx=i: self.validate_ticker(idx))
            
            self.ticker_entries.append(ticker_entry)
            
            # USD checkbox
            usd_var = tk.BooleanVar()
            usd_var.set(stock['USD'])
            
            usd_check = ttk.Checkbutton(scrollable_frame, variable=usd_var, command=lambda idx=i: self.usd_changed(idx))
            usd_check.grid(row=i+1, column=2, padx=5, pady=2)
            
            # Make sure the checkbox shows correct state
            if stock['USD']:
                usd_check.state(['selected'])
            
            self.usd_vars.append(usd_var)
            
            # Price label
            price_label = ttk.Label(scrollable_frame, text="--")
            price_label.grid(row=i+1, column=3, padx=5, pady=2)
            self.price_labels.append(price_label)
            
            # Status label
            status_label = ttk.Label(scrollable_frame, text="Not checked")
            status_label.grid(row=i+1, column=4, padx=5, pady=2)
            self.status_labels.append(status_label)
            
            # Currency label
            currency_label = ttk.Label(scrollable_frame, text="--")
            currency_label.grid(row=i+1, column=5, padx=5, pady=2)
            self.currency_labels.append(currency_label)
        
        # Buttons
        button_frame = ttk.Frame(master, padding="10")
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Button(button_frame, text="Checky All Tickers", command=self.check_all_tickers).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Auto Detect Currencies", command=self.detect_all_currencies).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Save", command=self.save_mappings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=5)
        
        # Start validating existing tickers in background
        self.master.after(100, self.check_all_tickers)
    
    def usd_changed(self, idx):
        """Update price display when USD checkbox changes"""
        if self.ticker_entries[idx].get().strip():
            self.validate_ticker(idx)
    
    def validate_ticker(self, idx):
        """Validate ticker and update price info"""
        ticker = self.ticker_entries[idx].get().strip()
        
        # Update UI to show we're checking
        self.status_labels[idx].config(text="Checking...", foreground="blue")
        self.price_labels[idx].config(text="--")
        self.master.update_idletasks()  # Refresh UI
        
        # Check ticker validity in a separate thread
        def check_and_update():
            is_valid, price, price_value = check_ticker_validity(ticker)
            
            # Update UI with results
            self.master.after(0, lambda: self.update_ticker_status(idx, is_valid, price, price_value))
        
        threading.Thread(target=check_and_update).start()
    
    def update_ticker_status(self, idx, is_valid, price, price_value):
        """Update the UI with ticker validation results"""
        if is_valid:
            is_usd = self.usd_vars[idx].get()
            currency_symbol = "$" if is_usd else "€"
            
            self.status_labels[idx].config(text="Valid", foreground="green")
            self.price_labels[idx].config(text=f"{currency_symbol}{price_value:.2f}")
        else:
            self.status_labels[idx].config(text=price_value, foreground="red")
            self.price_labels[idx].config(text="--")
    
    def check_all_tickers(self):
        """Check all tickers at once"""
        for idx in range(len(self.ticker_entries)):
            if self.ticker_entries[idx].get().strip():
                self.validate_ticker(idx)
    
    def detect_currency(self, idx):
        """Detect currency for a single ticker"""
        ticker = self.ticker_entries[idx].get().strip()
        if not ticker:
            return
            
        # Update UI to show we're checking
        self.currency_labels[idx].config(text="Checking...", foreground="blue")
        self.master.update_idletasks()  # Refresh UI
        
        # Get currency in a separate thread
        def check_and_update_currency():
            currency = get_ticker_currency(ticker)
            
            # Update UI with results
            self.master.after(0, lambda: self.update_currency_status(idx, currency))
        
        threading.Thread(target=check_and_update_currency).start()
    
    def update_currency_status(self, idx, currency):
        """Update the currency label and USD checkbox based on detected currency"""
        if currency:
            self.currency_labels[idx].config(text=currency, foreground="black")
            
            # Auto-set USD checkbox
            is_usd = currency.upper() == "USD"
            self.usd_vars[idx].set(is_usd)
            
            # Update price display with correct currency
            if self.status_labels[idx].cget("text") == "Valid":
                self.validate_ticker(idx)
        else:
            self.currency_labels[idx].config(text="Unknown", foreground="red")
    
    def detect_all_currencies(self):
        """Detect currencies for all tickers"""
        for idx in range(len(self.ticker_entries)):
            if self.ticker_entries[idx].get().strip():
                self.detect_currency(idx)
    
    def save_mappings(self):
        updated_data = []
        
        for i, stock in enumerate(self.stock_data):
            is_usd = self.usd_vars[i].get()
            
            updated_data.append({
                'Product': stock['Product'],
                'Ticker': self.ticker_entries[i].get().strip(),
                'USD': bool(is_usd)  # Explicitly convert to bool
            })
        
        self.result = updated_data
        self.master.destroy()
    
    def cancel(self):
        self.result = None
        self.master.destroy()

def show_ticker_confirmation(stock_data):
    """Show the ticker confirmation window and return the result"""
    root = tk.Tk()
    app = TickerConfirmationWindow(root, stock_data)
    root.mainloop()
    
    return app.result

def manage_tickers(account_file='Account.csv', ticker_file='tickers.csv'):
    """Main function to manage ticker mappings"""
    # Get stock names from account file
    account_stocks = get_stock_names_from_account(account_file)
    
    # Get existing ticker mappings
    ticker_df = get_existing_ticker_mappings(ticker_file)
    
    # Merge lists and prepare data for confirmation
    merged_stock_data = merge_stock_lists(account_stocks, ticker_df)
    
    # Show confirmation window
    print("Opening ticker confirmation window...")
    confirmed_data = show_ticker_confirmation(merged_stock_data)
    
    if confirmed_data is not None:
        # User confirmed, save to CSV
        print(f"Saving updated ticker mappings to {ticker_file}")
        new_df = pd.DataFrame(confirmed_data)
        
        # Make sure boolean values are correctly saved as True/False
        new_df['USD'] = new_df['USD'].apply(lambda x: bool(x))
        
        new_df.to_csv(ticker_file, index=False)
        return True
    else:
        # User cancelled
        print("Ticker mapping cancelled by user")
        return False 