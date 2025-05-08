import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import threading
import sys
import pandas as pd
import os.path
from datetime import datetime

# Import utility modules
from investo_utils.data_loader import (
    prepare_account_csv,
    load_ticker_mappings,
    load_transaction_data,
    get_stock_prices
)
from investo_utils.portfolio import calculate_daily_holdings_and_values
from investo_utils.visualization import plot_portfolio_for_gui, create_embedded_plots
from investo_utils.ticker_manager import get_stock_names_from_account, get_existing_ticker_mappings, merge_stock_lists, get_ticker_currency

# Default USD to EUR conversion rate as fallback
USD_TO_EUR = 0.97

class TextRedirector:
    """Redirects print statements to both console and a tkinter Text widget"""
    def __init__(self, text_widget, original_stdout=None):
        self.text_widget = text_widget
        self.original_stdout = original_stdout or sys.stdout

    def write(self, string):
        self.original_stdout.write(string)
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)  # Auto-scroll to the end
        self.text_widget.update_idletasks()

    def flush(self):
        self.original_stdout.flush()

class PortfolioDashboardWindow(tk.Toplevel):
    """Dashboard window for portfolio visualization with interactive controls"""
    def __init__(self, parent, all_values, dates, ticker_map, total_deposits):
        super().__init__(parent)
        self.parent = parent
        self.all_values = all_values
        self.dates = dates
        self.ticker_map = ticker_map
        self.total_deposits = total_deposits
        
        # Configure window
        self.title("Portfolio Dashboard")
        self.geometry("1400x900")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create widgets
        self.create_widgets()
        
        # Calculate some basic stats
        self.calculate_stats()
        
    def create_widgets(self):
        # Main container frame with padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top stats panel
        self.stats_frame = ttk.LabelFrame(main_frame, text="Portfolio Statistics")
        self.stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a grid of stats
        self.create_stats_panel()
        
        # Create notebook for visualization tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create visualization tabs - removed overview tab
        self.value_tab = ttk.Frame(self.notebook)
        self.holdings_tab = ttk.Frame(self.notebook)
        self.performance_tab = ttk.Frame(self.notebook)
        
        # Add tabs with meaningful names
        self.notebook.add(self.value_tab, text="Value & Deposits")
        self.notebook.add(self.holdings_tab, text="Holdings")
        self.notebook.add(self.performance_tab, text="Performance")
        
        # Create embedded visualizations in each tab
        self.create_visualizations()
        
        # Bottom control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Holdings filter - add to holdings tab instead of main window
        filter_frame = ttk.LabelFrame(self.holdings_tab, text="Display Options")
        filter_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # Holdings filter row
        filter_content = ttk.Frame(filter_frame)
        filter_content.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_content, text="Show Holdings:").pack(side=tk.LEFT, padx=5)
        
        # Create checkbuttons for each holding
        self.holding_vars = {}
        for stock in self.all_values.keys():
            if stock != 'Cash':  # Don't need to filter Cash
                var = tk.BooleanVar(value=True)
                # Use ticker symbol instead of stock name for the checkbutton label
                ticker = self.ticker_map.get(stock, 'N/A')
                ttk.Checkbutton(filter_content, text=ticker, variable=var).pack(side=tk.LEFT, padx=5)
                self.holding_vars[stock] = var
        
        # Button panel
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Export Data", command=self.export_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self.on_closing).pack(side=tk.LEFT, padx=5)
    
    def create_visualizations(self):
        """Create visualizations in each tab"""
        # Create embedded plots in each tab
        self.plots = {}
        
        # Create value chart directly in the value tab
        fig = self.create_value_chart()
        self.plots['value'] = {'figures': {'value': fig}}
        canvas = FigureCanvasTkAgg(fig, self.value_tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.plots['value']['canvases'] = {'value': canvas}
        
        # Add a toolbar for navigation
        toolbar_frame = ttk.Frame(self.value_tab)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=0)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        
        # Holdings chart directly in the holdings tab
        fig = self.create_holdings_chart()
        self.plots['holdings'] = {'figures': {'holdings': fig}}
        canvas = FigureCanvasTkAgg(fig, self.holdings_tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.plots['holdings']['canvases'] = {'holdings': canvas}
        
        # Add a toolbar for navigation
        toolbar_frame = ttk.Frame(self.holdings_tab)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=0)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        
        # Performance chart directly in the performance tab
        fig = self.create_performance_chart()
        self.plots['performance'] = {'figures': {'performance': fig}}
        canvas = FigureCanvasTkAgg(fig, self.performance_tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.plots['performance']['canvases'] = {'performance': canvas}
        
        # Add a toolbar for navigation
        toolbar_frame = ttk.Frame(self.performance_tab)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=0)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
    
    def create_value_chart(self):
        """Create a chart showing portfolio value and deposits"""
        from matplotlib.figure import Figure
        
        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        # Total value
        total_values = []
        for i in range(len(self.dates)):
            total = sum(values[i][1] for values in self.all_values.values())
            total_values.append(total)
            
        # Deposits
        deposit_dates, deposit_amounts = zip(*self.total_deposits)
        
        # Plot
        ax.plot(deposit_dates, deposit_amounts, color='lightgreen', 
               label='Total Deposits (EUR)', linewidth=2)
        ax.plot(self.dates, total_values, color='blue', 
               label='Portfolio Value (EUR)', linewidth=2.5)
        
        ax.set_title('Portfolio Value vs Deposits')
        ax.set_ylabel('EUR')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        fig.tight_layout()
        return fig
    
    def create_holdings_chart(self):
        """Create a chart showing individual holdings"""
        from matplotlib.figure import Figure
        import matplotlib.pyplot as plt
        
        fig = Figure(figsize=(10, 6), dpi=100) 
        ax = fig.add_subplot(111)
        
        # Use a color cycle
        colors = plt.cm.tab10.colors
        color_idx = 0
        
        # Calculate total portfolio value
        total_values = []
        for i in range(len(self.dates)):
            total = sum(values[i][1] for values in self.all_values.values())
            total_values.append(total)
        
        # Plot each holding
        for stock, values in self.all_values.items():
            dates_stock, amounts = zip(*values)
            if stock == 'Cash':
                ax.plot(dates_stock, amounts, label='Cash', 
                       color='green', linestyle='--', linewidth=2)
            else:
                ticker = self.ticker_map.get(stock, 'N/A')
                # Use only ticker symbol as the label
                ax.plot(dates_stock, amounts, label=f"{ticker}",
                       color=colors[color_idx % len(colors)], linewidth=1.5)
                color_idx += 1
        
        # Add total portfolio value line
        ax.plot(self.dates, total_values, color='black', linewidth=2.5, label='Total')
        
        ax.set_title('Individual Holdings', fontsize=14)
        ax.set_ylabel('Value (EUR)', fontsize=12)
        ax.set_xlabel('Date', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # Make the legend more compact if many items
        if len(self.all_values) > 8:
            ax.legend(loc='upper left', fontsize=9, ncol=2)
        else:
            ax.legend(loc='upper left', fontsize=10)
            
        fig.tight_layout()
        return fig
    
    def create_performance_chart(self):
        """Create a chart showing portfolio performance"""
        from matplotlib.figure import Figure
        import pandas as pd
        
        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        # Calculate gain/loss as percentage
        deposit_dates, deposit_amounts = zip(*self.total_deposits)
        deposit_df = pd.DataFrame({'date': deposit_dates, 'amount': deposit_amounts}).set_index('date')
        
        total_values = []
        for i in range(len(self.dates)):
            total = sum(values[i][1] for values in self.all_values.values())
            total_values.append(total)
            
        interpolated_deposits = [deposit_df.asof(date)['amount'] for date in self.dates]
        gains_percentage = [(tv - d) / d * 100 if d > 0 else 0 
                          for tv, d in zip(total_values, interpolated_deposits)]
        
        # Plot gain/loss line
        ax.plot(self.dates, gains_percentage, color='black', linewidth=2.5)
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        
        # Color the areas
        ax.fill_between(self.dates, gains_percentage, 0, 
                       where=[g >= 0 for g in gains_percentage], 
                       color='green', alpha=0.2)
        ax.fill_between(self.dates, gains_percentage, 0, 
                       where=[g < 0 for g in gains_percentage], 
                       color='red', alpha=0.2)
        
        ax.set_title('Portfolio Performance')
        ax.set_ylabel('Return on Deposits (%)')
        ax.set_xlabel('Date')
        ax.grid(True, alpha=0.3)
        
        fig.tight_layout()
        return fig
        
    def create_stats_panel(self):
        """Create the statistics panel with key portfolio metrics"""
        # Create a frame with 4 columns for stats
        for i in range(4):
            self.stats_frame.columnconfigure(i, weight=1)
        
        # Placeholder stats (will be filled in calculate_stats)
        self.total_value_label = self.create_stat_widget(0, 0, "Total Value:", "€0.00")
        self.total_deposit_label = self.create_stat_widget(0, 1, "Total Deposits:", "€0.00")
        self.total_gain_label = self.create_stat_widget(0, 2, "Total Gain/Loss:", "€0.00 (0.00%)")
        self.best_performer_label = self.create_stat_widget(0, 3, "Best Performer:", "None")
        
        self.create_stat_widget(1, 0, "Start Date:", "N/A")
        self.create_stat_widget(1, 1, "End Date:", "N/A")
        self.create_stat_widget(1, 2, "Duration:", "N/A")
        self.create_stat_widget(1, 3, "Holdings:", "0")
    
    def create_stat_widget(self, row, col, label_text, value_text):
        """Helper to create a statistic widget with label and value"""
        frame = ttk.Frame(self.stats_frame, padding="5")
        frame.grid(row=row, column=col, padx=10, pady=5, sticky="nsew")
        
        ttk.Label(frame, text=label_text, font=("Arial", 10)).pack(anchor=tk.W)
        value_label = ttk.Label(frame, text=value_text, font=("Arial", 12, "bold"))
        value_label.pack(anchor=tk.W, pady=5)
        
        return value_label
    
    def calculate_stats(self):
        """Calculate and display portfolio statistics"""
        if not self.all_values or not self.dates:
            return
            
        # Get the latest values
        total_value = sum(values[-1][1] for values in self.all_values.values())
        
        # Get the total deposits (last value in the deposits list)
        total_deposits = self.total_deposits[-1][1] if self.total_deposits else 0
        
        # Calculate gain/loss
        gain_loss = total_value - total_deposits
        gain_loss_pct = (gain_loss / total_deposits * 100) if total_deposits > 0 else 0
        
        # Update the statistics labels
        self.total_value_label.config(text=f"€{total_value:.2f}")
        self.total_deposit_label.config(text=f"€{total_deposits:.2f}")
        
        # Set color for gain/loss
        color = "green" if gain_loss >= 0 else "red"
        sign = "+" if gain_loss >= 0 else ""
        self.total_gain_label.config(
            text=f"{sign}€{gain_loss:.2f} ({sign}{gain_loss_pct:.2f}%)",
            foreground=color
        )
        
        # Find best performer (exclude Cash)
        best_performer = "None"
        best_perf_pct = 0
        
        for stock, values in self.all_values.items():
            if stock == 'Cash' or len(values) < 2:  # Skip cash or stocks with insufficient data
                continue
                
            # Calculate performance
            initial_value = values[0][1]
            final_value = values[-1][1]
            
            if initial_value > 0:
                perf_pct = (final_value - initial_value) / initial_value * 100
                if perf_pct > best_perf_pct:
                    best_perf_pct = perf_pct
                    ticker = self.ticker_map.get(stock, '')
                    # Use ticker symbol instead of stock name
                    best_performer = f"{ticker}: +{best_perf_pct:.2f}%"
        
        self.best_performer_label.config(text=best_performer)
        
    def export_data(self):
        """Export portfolio data to CSV"""
        # This is a placeholder for the export functionality
        print("Export functionality would go here")
        # In a full implementation, you would:
        # 1. Convert data to a DataFrame 
        # 2. Open a file dialog to select save location
        # 3. Save the data as CSV or Excel
    
    def on_closing(self):
        """Handle the window closing event"""
        self.destroy()

class FileSelectionFrame(ttk.Frame):
    """Frame for selecting and validating the Degiro Account.csv file"""
    def __init__(self, parent, on_file_selected, on_cancel):
        super().__init__(parent)
        self.parent = parent
        self.on_file_selected = on_file_selected
        self.on_cancel = on_cancel
        
        self.create_widgets()
        self.check_existing_file()
        
    def create_widgets(self):
        # Title
        title_label = ttk.Label(self, text="Select Your Degiro Account Data", font=('Arial', 18, 'bold'))
        title_label.pack(pady=20)
        
        # Instructions frame
        instruction_frame = ttk.LabelFrame(self, text="How to obtain your Degiro account file")
        instruction_frame.pack(fill=tk.X, padx=20, pady=10)
        
        instructions = (
            "1. Log in to your Degiro account\n"
            "2. Go to Inbox > Account Statements (rekeningenoverzicht)\n"
            "3. Update the start date to the earliest date of your account\n"
            "4. Click 'Download as CSV'\n"
            "5. Select the downloaded file below"
        )
        
        ttk.Label(instruction_frame, text=instructions, justify=tk.LEFT, padding=10).pack(fill=tk.X)
        
        # File selection frame
        self.file_frame = ttk.Frame(self)
        self.file_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Existing file info (will be populated in check_existing_file)
        self.existing_file_frame = ttk.LabelFrame(self.file_frame, text="Existing Account File")
        self.existing_file_frame.pack(fill=tk.X, pady=5)
        
        self.existing_file_info = ttk.Label(self.existing_file_frame, text="Checking for existing file...", padding=10)
        self.existing_file_info.pack(fill=tk.X)
        
        self.existing_file_date_range = ttk.Label(self.existing_file_frame, text="", padding=5)
        self.existing_file_date_range.pack(fill=tk.X)
        
        # File selection buttons
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(fill=tk.X, padx=20, pady=20)
        
        self.select_new_button = ttk.Button(
            self.button_frame, 
            text="Select New Account File", 
            command=self.select_new_file
        )
        self.select_new_button.pack(side=tk.LEFT, padx=5)
        
        self.use_existing_button = ttk.Button(
            self.button_frame, 
            text="Use Existing File", 
            command=self.use_existing_file,
            state=tk.DISABLED
        )
        self.use_existing_button.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = ttk.Button(
            self.button_frame, 
            text="Cancel", 
            command=self.on_cancel
        )
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
    
    def check_existing_file(self):
        """Check if an Account.csv file already exists and get its date range"""
        if os.path.exists('Account.csv'):
            try:
                # Load the CSV file
                df = pd.read_csv('Account.csv', delimiter=',')
                
                # Check if there's a date column (different versions of Degiro CSVs)
                date_col = None
                for col in ['Datum', 'Date', 'Datum_Tijd', 'Date_Time']:
                    if col in df.columns:
                        date_col = col
                        break
                
                if date_col:
                    # Convert dates
                    if 'Tijd' in date_col or 'Time' in date_col:
                        df[date_col] = pd.to_datetime(df[date_col], format='%d-%m-%Y %H:%M')
                    else:
                        df[date_col] = pd.to_datetime(df[date_col], format='%d-%m-%Y')
                    
                    # Get date range
                    min_date = df[date_col].min().strftime('%d-%m-%Y')
                    max_date = df[date_col].max().strftime('%d-%m-%Y')
                    
                    self.existing_file_info.config(
                        text=f"Found existing Account.csv file with {len(df)} transactions"
                    )
                    self.existing_file_date_range.config(
                        text=f"Date range: {min_date} to {max_date}",
                        foreground="green"
                    )
                    
                    # Enable the use existing button
                    self.use_existing_button.config(state=tk.NORMAL)
                else:
                    self.existing_file_info.config(
                        text="Found existing Account.csv file but could not determine its date range"
                    )
                    self.existing_file_date_range.config(
                        text="The file might not be a valid Degiro account statement",
                        foreground="orange"
                    )
            except Exception as e:
                self.existing_file_info.config(
                    text=f"Found existing Account.csv file but encountered an error: {str(e)}"
                )
                self.existing_file_date_range.config(
                    text="The file might be corrupted or in an unexpected format",
                    foreground="red"
                )
        else:
            self.existing_file_info.config(
                text="No existing Account.csv file found"
            )
            self.existing_file_date_range.config(
                text="Please select a new account statement file",
                foreground="blue"
            )
    
    def select_new_file(self):
        """Open file dialog to select a new Account.csv file"""
        file_path = filedialog.askopenfilename(
            title="Select Degiro Account CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        
        if file_path:
            # Check if we should back up the existing file
            if os.path.exists('Account.csv'):
                # Create a backup with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f'Account_backup_{timestamp}.csv'
                
                try:
                    # Copy the existing file to the backup location
                    import shutil
                    shutil.copy2('Account.csv', backup_path)
                    
                    self.existing_file_date_range.config(
                        text=f"Existing file backed up as {backup_path}",
                        foreground="green"
                    )
                except Exception as e:
                    messagebox.showwarning("Backup Failed", 
                                         f"Could not back up existing file: {str(e)}")
            
            try:
                # Copy the selected file to Account.csv
                import shutil
                shutil.copy2(file_path, 'Account.csv')
                
                # Verify the new file
                self.check_existing_file()
                
                # If verification successful, call the callback
                if self.use_existing_button.cget('state') == 'normal':
                    messagebox.showinfo("File Selected", 
                                      "New Account.csv file has been successfully imported")
                    self.on_file_selected()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import the selected file: {str(e)}")
    
    def use_existing_file(self):
        """Use the existing Account.csv file"""
        if os.path.exists('Account.csv'):
            self.on_file_selected()
        else:
            messagebox.showerror("Error", "The Account.csv file could not be found. Please select a new file.")

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
                
            import yfinance as yf
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

class InvestoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Investo - Portfolio Analyzer")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create main container frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initialize variables
        self.analysis_thread = None
        self.running = False
        self.current_frame = None
        self.ticker_frame = None
        self.analysis_frame = None
        self.dashboard_window = None
        self.file_selection_frame = None
        
        # Stored analysis data
        self.all_values = None
        self.dates = None
        self.ticker_map = None
        self.total_deposits = None
        self.plot_objects = None  # Store plot objects and canvases
        
        # Create the analysis frame (empty initially)
        self.create_analysis_frame()
        
        # Start with the start screen
        self.show_start_screen()
        
        # Redirect standard output to both console and text widget
        self.original_stdout = sys.stdout
        # Will be set up when analysis frame is shown

    def create_analysis_frame(self):
        """Create the analysis frame structure"""
        self.analysis_frame = ttk.Frame(self.main_frame)
        
        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.analysis_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create the main workflow tab
        self.workflow_tab = ttk.Frame(self.notebook)
        self.results_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.workflow_tab, text="Portfolio Analysis")
        self.notebook.add(self.results_tab, text="Results")
        
        # Create a progress frame
        self.progress_frame = ttk.LabelFrame(self.workflow_tab, text="Progress")
        self.progress_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create log display area with scrollbar
        self.log_frame = ttk.Frame(self.progress_frame)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_scrollbar = ttk.Scrollbar(self.log_frame)
        self.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_display = tk.Text(self.log_frame, height=10, yscrollcommand=self.log_scrollbar.set)
        self.log_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.log_scrollbar.config(command=self.log_display.yview)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready to start")
        self.status_label = ttk.Label(self.progress_frame, textvariable=self.status_var)
        self.status_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # Control buttons
        self.control_frame = ttk.Frame(self.workflow_tab)
        self.control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.restart_button = ttk.Button(self.control_frame, text="Configure Tickers", command=self.show_file_selection_screen)
        self.restart_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.show_dashboard_button = ttk.Button(
            self.control_frame, 
            text="Show Dashboard", 
            command=self.show_dashboard, 
            state=tk.DISABLED
        )
        self.show_dashboard_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.quit_button = ttk.Button(self.control_frame, text="Quit", command=self.on_closing)
        self.quit_button.pack(side=tk.RIGHT, padx=5, pady=5)

    def show_start_screen(self):
        """Show the start screen"""
        # Clear current frame if any
        if self.current_frame:
            self.current_frame.pack_forget()
        
        # Create start frame
        start_frame = ttk.Frame(self.main_frame)
        
        # Add title
        title_label = ttk.Label(start_frame, text="Investo - Portfolio Analyzer", font=('Arial', 24, 'bold'))
        title_label.pack(pady=40)
        
        subtitle_label = ttk.Label(start_frame, text="Analyze your Degiro portfolio and visualize performance", font=('Arial', 14))
        subtitle_label.pack(pady=10)
        
        # Add start button
        start_button = ttk.Button(start_frame, text="Start Analysis", command=self.show_file_selection_screen)
        start_button.pack(pady=30)
        
        # Display the frame
        start_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = start_frame

    def show_file_selection_screen(self):
        """Show the file selection screen"""
        # Clear current frame
        if self.current_frame:
            self.current_frame.pack_forget()
            
        # Create file selection frame
        self.file_selection_frame = FileSelectionFrame(
            self.main_frame,
            on_file_selected=self.show_ticker_screen,
            on_cancel=self.show_start_screen
        )
        
        # Display the frame
        self.file_selection_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = self.file_selection_frame

    def show_ticker_screen(self):
        """Load stock data and show the ticker configuration screen"""
        # Clear current frame
        if self.current_frame:
            self.current_frame.pack_forget()
            
        # Show a loading screen while we load data
        loading_frame = ttk.Frame(self.main_frame)
        loading_label = ttk.Label(loading_frame, text="Loading stock data...", font=('Arial', 14))
        loading_label.pack(pady=40)
        loading_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = loading_frame
        self.root.update()
        
        # Load stock data
        try:
            account_stocks = get_stock_names_from_account('Account.csv')
            ticker_df = get_existing_ticker_mappings('tickers.csv')
            merged_stock_data = merge_stock_lists(account_stocks, ticker_df)
            
            # Remove loading frame
            loading_frame.pack_forget()
            
            # Create ticker frame
            self.ticker_frame = TickerFrame(
                self.main_frame, 
                merged_stock_data,
                on_save_callback=self.on_ticker_save,
                on_cancel_callback=self.show_file_selection_screen
            )
            
            # Display the frame
            self.ticker_frame.pack(fill=tk.BOTH, expand=True)
            self.current_frame = self.ticker_frame
            
        except Exception as e:
            # Show error
            loading_label.config(text=f"Error loading data: {str(e)}")
            # Add a button to go back
            ttk.Button(loading_frame, text="Back", command=self.show_file_selection_screen).pack(pady=20)

    def on_ticker_save(self, ticker_data):
        """Handle ticker configuration save"""
        # Save ticker mappings
        new_df = pd.DataFrame(ticker_data)
        new_df['USD'] = new_df['USD'].apply(lambda x: bool(x))
        new_df.to_csv('tickers.csv', index=False)
        
        # Show analysis screen and start analysis
        self.show_analysis_screen()
        self.start_analysis()

    def show_analysis_screen(self):
        """Show the analysis screen"""
        # Clear current frame
        if self.current_frame:
            self.current_frame.pack_forget()
            
        # Set up stdout redirection
        sys.stdout = TextRedirector(self.log_display, self.original_stdout)
        
        # Display the analysis frame
        self.analysis_frame.pack(fill=tk.BOTH, expand=True)
        self.current_frame = self.analysis_frame
        
        # Clear log display
        self.log_display.delete(1.0, tk.END)
        
        # Disable dashboard button until analysis is complete
        self.show_dashboard_button.config(state=tk.DISABLED)

    def update_progress(self, value, status=None):
        """Update progress bar and status label"""
        self.progress_var.set(value)
        if status:
            self.status_var.set(status)
        self.root.update_idletasks()

    def start_analysis(self):
        """Start the analysis workflow in a separate thread"""
        if self.running:
            return
            
        self.running = True
        self.restart_button.config(state=tk.DISABLED)
        self.show_dashboard_button.config(state=tk.DISABLED)
        
        # Start analysis in a separate thread
        self.analysis_thread = threading.Thread(target=self.run_analysis)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()

    def run_analysis(self):
        """Run the complete analysis workflow"""
        try:
            self.update_progress(0, "Starting analysis...")
            
            # Step 1: Load data
            self.update_progress(15, "Preparing and loading data...")
            prepare_account_csv('Account.csv')
            ticker_map, usd_stocks = load_ticker_mappings('tickers.csv')
            df, cash_df = load_transaction_data('Account.csv')
            
            # Step 2: Fetch stock price data
            self.update_progress(20, "Fetching stock price data...")
            price_data = {}
            stocks = df['Product'].unique()
            start_date = min(df['Datum_Tijd'].min(), cash_df['Datum_Tijd'].min())
            end_date = pd.Timestamp.now()
            
            # Fetch prices for each stock with progress updates
            for i, stock in enumerate(stocks):
                progress = 20 + (40 * (i + 1) / len(stocks))
                self.update_progress(progress, f"Fetching data for {stock}...")
                
                if stock in ticker_map:
                    ticker = ticker_map[stock]
                    print(f"\nProcessing {stock} ({ticker})")
                    prices = get_stock_prices(ticker, start_date, end_date)
                    if prices is not None:
                        price_data[stock] = prices
                        currency = "USD" if stock in usd_stocks else "EUR"
                        print(f"💰 Last price: {prices.iloc[-1]:.2f} {currency}")
                    else:
                        print(f"⚠️  Failed to fetch prices for {stock}")
            
            # Step 3: Calculate portfolio values
            self.update_progress(60, "Calculating portfolio values...")
            all_values, dates, total_deposits = calculate_daily_holdings_and_values(
                df, cash_df, price_data, ticker_map, usd_stocks, USD_TO_EUR
            )
            
            # Store analysis results for later use
            self.all_values = all_values
            self.dates = dates
            self.ticker_map = ticker_map
            self.total_deposits = total_deposits
            
            # Step 4: Generate visualization
            self.update_progress(90, "Generating portfolio visualization...")
            
            # Create the embedded visualization in the results tab
            def create_plots():
                # Clear any existing plots
                for widget in self.results_tab.winfo_children():
                    widget.destroy()
                
                # Create a notebook for the results tab
                results_notebook = ttk.Notebook(self.results_tab)
                results_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                # Create tabs for each chart type
                value_tab = ttk.Frame(results_notebook)
                holdings_tab = ttk.Frame(results_notebook)
                performance_tab = ttk.Frame(results_notebook)
                
                results_notebook.add(value_tab, text="Value & Deposits")
                results_notebook.add(holdings_tab, text="Holdings")
                results_notebook.add(performance_tab, text="Performance")
                
                # Generate the individual charts
                from matplotlib.figure import Figure
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                
                # Value chart
                from investo_utils.visualization import create_embedded_plots
                charts = create_embedded_plots(None, all_values, dates, ticker_map, total_deposits)
                
                # Value chart
                fig = charts['figures'].get('value')
                if fig:
                    canvas = FigureCanvasTkAgg(fig, value_tab)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                    
                    # Add toolbar
                    toolbar_frame = ttk.Frame(value_tab)
                    toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
                    toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
                    toolbar.update()
                
                # Holdings chart
                fig = charts['figures'].get('holdings')
                if fig:
                    canvas = FigureCanvasTkAgg(fig, holdings_tab)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                    
                    # Add toolbar
                    toolbar_frame = ttk.Frame(holdings_tab)
                    toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
                    toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
                    toolbar.update()
                
                # Performance chart
                fig = charts['figures'].get('performance')
                if fig:
                    canvas = FigureCanvasTkAgg(fig, performance_tab)
                    canvas.draw()
                    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                    
                    # Add toolbar
                    toolbar_frame = ttk.Frame(performance_tab)
                    toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
                    toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
                    toolbar.update()
                
                # Store the plots
                self.plot_objects = charts
                
                # Switch to the results tab
                self.notebook.select(self.results_tab)
            
            # Create plots in the main thread
            self.root.after(0, create_plots)
            
            self.update_progress(100, "Analysis complete!")
            
        except Exception as e:
            print(f"Error during analysis: {str(e)}")
            print(f"Error details: {type(e).__name__}")
            self.update_progress(0, f"Error: {str(e)}")
        
        finally:
            self.running = False
            self.root.after(0, lambda: self.restart_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.show_dashboard_button.config(state=tk.NORMAL))

    def show_dashboard(self):
        """Show the dashboard window if analysis is complete"""
        if self.all_values and self.dates and not self.running:
            if not self.dashboard_window or not self.dashboard_window.winfo_exists():
                # Create new dashboard window with embedded visualization
                self.dashboard_window = PortfolioDashboardWindow(
                    self.root,
                    self.all_values,
                    self.dates,
                    self.ticker_map,
                    self.total_deposits
                )
            else:
                # If dashboard exists, bring to front
                self.dashboard_window.lift()
                self.dashboard_window.focus_force()
        else:
            self.status_var.set("Complete the analysis first to show the dashboard")

    def on_closing(self):
        """Handle window close event"""
        self.running = False
        
        # Close any open dashboard window
        if self.dashboard_window and self.dashboard_window.winfo_exists():
            self.dashboard_window.destroy()
            
        sys.stdout = self.original_stdout  # Restore original stdout
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = InvestoApp(root)
    root.mainloop() 