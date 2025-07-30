import tkinter as tk
from tkinter import ttk
import threading
from investo_utils.ticker_manager import get_ticker_currency

class TickerFrame(ttk.Frame):
    """Frame for ticker configuration"""
    def __init__(self, parent, stock_data, on_save_callback, on_cancel_callback):
        super().__init__(parent)
        self.parent = parent
        self.stock_data = stock_data
        self.on_save = on_save_callback
        self.on_cancel = on_cancel_callback
        self.result = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # Title
        title_label = ttk.Label(self, text="Configure Stock Tickers", font=('Arial', 14, 'bold'))
        title_label.pack(pady=10)
        
        # Instructions for ticker selection
        instruction_frame = ttk.LabelFrame(self, text="Ticker Selection Guide")
        instruction_frame.pack(fill=tk.X, padx=10, pady=5)
        
        instructions = (
            "• Make sure you select the correct ticker for each stock\n"
            "• You can find tickers on Yahoo Finance (finance.yahoo.com)\n"
            "• Beware that stocks on different exchanges have different tickers\n"
            "• Example: HIMS & Hers on NYSE is 'HIMS', but on Tradegate it is '82W.BE'\n"
            "• Check the 'USD' box for stocks traded in US dollars"
        )
        
        ttk.Label(instruction_frame, text=instructions, justify=tk.LEFT, padding=5).pack(fill=tk.X)
        
        # Create a scrollable frame
        self.canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Headers
        ttk.Label(self.scrollable_frame, text="Stock Name", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Label(self.scrollable_frame, text="Ticker Symbol", font=('Arial', 10, 'bold')).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(self.scrollable_frame, text="USD", font=('Arial', 10, 'bold')).grid(row=0, column=2, padx=5, pady=5, sticky='w')
        ttk.Label(self.scrollable_frame, text="Last Price", font=('Arial', 10, 'bold')).grid(row=0, column=3, padx=5, pady=5, sticky='w')
        ttk.Label(self.scrollable_frame, text="Status", font=('Arial', 10, 'bold')).grid(row=0, column=4, padx=5, pady=5, sticky='w')
        ttk.Label(self.scrollable_frame, text="Currency", font=('Arial', 10, 'bold')).grid(row=0, column=5, padx=5, pady=5, sticky='w')
        
        # Add stock entries
        self.ticker_entries = []
        self.usd_vars = []
        self.price_labels = []
        self.status_labels = []
        self.currency_labels = []
        
        for i, stock in enumerate(self.stock_data):
            # Stock name (read-only)
            ttk.Label(self.scrollable_frame, text=stock['Product']).grid(row=i+1, column=0, padx=5, pady=2, sticky='w')
            
            # Ticker entry
            ticker_entry = ttk.Entry(self.scrollable_frame, width=20)
            ticker_entry.insert(0, stock['Ticker'])
            ticker_entry.grid(row=i+1, column=1, padx=5, pady=2)
            
            # Bind validation to entry field
            ticker_entry.bind("<FocusOut>", lambda e, idx=i: self.validate_ticker(idx))
            ticker_entry.bind("<Return>", lambda e, idx=i: self.validate_ticker(idx))
            
            self.ticker_entries.append(ticker_entry)
            
            # USD checkbox
            usd_var = tk.BooleanVar()
            usd_var.set(stock['USD'])
            
            usd_check = ttk.Checkbutton(self.scrollable_frame, variable=usd_var, command=lambda idx=i: self.usd_changed(idx))
            usd_check.grid(row=i+1, column=2, padx=5, pady=2)
            
            # Make sure the checkbox shows correct state
            if stock['USD']:
                usd_check.state(['selected'])
            
            self.usd_vars.append(usd_var)
            
            # Price label
            price_label = ttk.Label(self.scrollable_frame, text="--")
            price_label.grid(row=i+1, column=3, padx=5, pady=2)
            self.price_labels.append(price_label)
            
            # Status label
            status_label = ttk.Label(self.scrollable_frame, text="Not checked")
            status_label.grid(row=i+1, column=4, padx=5, pady=2)
            self.status_labels.append(status_label)
            
            # Currency label
            currency_label = ttk.Label(self.scrollable_frame, text="--")
            currency_label.grid(row=i+1, column=5, padx=5, pady=2)
            self.currency_labels.append(currency_label)
        
        # Buttons
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        
        ttk.Button(self.button_frame, text="Check All Tickers", command=self.check_all_tickers).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Auto-Detect Currencies", command=self.detect_all_currencies).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.button_frame, text="Save", command=self.save_mappings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(self.button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=5)
        
        # Start validating existing tickers in background
        self.after(500, self.check_all_tickers)
    
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
        self.update_idletasks()  # Refresh UI
        
        # Check ticker validity in a separate thread
        def check_and_update():
            is_valid, price, price_value = self.check_ticker_validity(ticker)
            
            # Update UI with results
            self.after(0, lambda: self.update_ticker_status(idx, is_valid, price, price_value))
        
        threading.Thread(target=check_and_update).start()
    
    def check_ticker_validity(self, ticker):
        """Check if a ticker is valid and get its last price"""
        try:
            if not ticker or ticker.strip() == '':
                return False, 0.0, "No ticker"
                
            import yfinance_cache as yf
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
        self.update_idletasks()  # Refresh UI
        
        # Get currency in a separate thread
        def check_and_update_currency():
            currency = get_ticker_currency(ticker)
            
            # Update UI with results
            self.after(0, lambda: self.update_currency_status(idx, currency))
        
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
        """Save mappings and call the callback"""
        updated_data = []
        
        for i, stock in enumerate(self.stock_data):
            is_usd = self.usd_vars[i].get()
            
            updated_data.append({
                'Product': stock['Product'],
                'Ticker': self.ticker_entries[i].get().strip(),
                'USD': bool(is_usd)
            })
        
        self.result = updated_data
        if self.on_save:
            self.on_save(updated_data)
    
    def cancel(self):
        """Cancel and call the callback"""
        if self.on_cancel:
            self.on_cancel() 