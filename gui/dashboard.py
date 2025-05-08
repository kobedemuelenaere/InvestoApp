import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import pandas as pd

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