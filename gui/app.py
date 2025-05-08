import tkinter as tk
from tkinter import ttk
import threading
import sys
import pandas as pd
import os.path

# Import utility modules 
from investo_utils.data_loader import (
    prepare_account_csv,
    load_ticker_mappings,
    load_transaction_data,
    get_stock_prices
)
from investo_utils.portfolio import calculate_daily_holdings_and_values
from investo_utils.visualization import create_embedded_plots
from investo_utils.ticker_manager import get_stock_names_from_account, get_existing_ticker_mappings, merge_stock_lists

# Import GUI components
from gui.file_selection import FileSelectionFrame
from gui.ticker_frame import TickerFrame
from gui.dashboard import PortfolioDashboardWindow
from utils.text_redirector import TextRedirector

# Default USD to EUR conversion rate as fallback
USD_TO_EUR = 0.97

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
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
                
                # Value chart
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