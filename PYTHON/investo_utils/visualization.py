import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from tqdm import tqdm

# Set matplotlib to use Agg backend - helps with tkinter integration
matplotlib.use("TkAgg")

def plot_portfolio_and_deposits(all_values, dates, ticker_map, total_deposits):
    """Generate and display portfolio visualization with multiple subplots."""
    print("\nGenerating portfolio visualization...")
    
    # Create figure with 3 subplots vertically stacked
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 16), height_ratios=[1, 1.5, 1])
    
    # Add title to the entire figure
    
    print("Drawing deposits and portfolio value chart...")
    # Top subplot - Total Deposits and Portfolio Value
    deposit_dates, deposit_amounts = zip(*total_deposits)
    sns.lineplot(x=deposit_dates, y=deposit_amounts, 
                label='Total Deposits (EUR)', ax=ax1, color='lightgreen')
    
    # Calculate and plot total portfolio value
    total_values = []
    for i in range(len(dates)):
        total = sum(values[i][1] for values in all_values.values())
        total_values.append(total)
    
    sns.lineplot(x=dates, y=total_values, color='blue', linewidth=2.5,
                label='Total Portfolio Value (EUR)', ax=ax1)
    
    ax1.set_title('Total Deposits and Portfolio Value Over Time', pad=20)
    ax1.set_xlabel('')  # Remove x-label
    ax1.set_ylabel('EUR')
    # Hide x-axis labels and ticks for top plot
    ax1.set_xticklabels([])
    ax1.legend(loc='upper left', bbox_to_anchor=(0.02, 0.98))
    
    print("Drawing individual holdings value chart...")
    # Middle subplot - Individual Holdings Values
    for stock, values in all_values.items():
        dates, amounts = zip(*values)
        if stock == 'Cash':
            sns.lineplot(x=dates, y=amounts, label='Cash (EUR)', ax=ax2,
                        color='green', linestyle='--')
        else:
            ticker = ticker_map.get(stock, 'N/A')
            sns.lineplot(x=dates, y=amounts, 
                        label=f"{ticker} - EUR", ax=ax2)
    
    # Add total portfolio value to middle chart as well
    sns.lineplot(x=dates, y=total_values, color='black', linewidth=2.5, 
                label='Total Portfolio Value (EUR)', ax=ax2)
    
    ax2.set_title('Individual Holdings Values Over Time', pad=20)
    ax2.set_xlabel('')  # Remove x-label
    ax2.set_ylabel('Value (EUR)')
    # Hide x-axis labels and ticks for middle plot
    ax2.set_xticklabels([])
    ax2.legend(loc='upper left', bbox_to_anchor=(0.02, 0.98))
    
    print("Drawing total gain/loss chart...")
    # Bottom subplot - Total Gain/Loss
    # Interpolate deposit amounts to match the dates of total values
    deposit_df = pd.DataFrame({'date': deposit_dates, 'amount': deposit_amounts}).set_index('date')
    interpolated_deposits = [deposit_df.asof(date)['amount'] for date in dates]
    
    # Calculate gain/loss as percentage of total deposits at each point in time
    # This shows performance relative to the amount invested at that specific moment
    gains_percentage = [(tv - d) / d * 100 if d > 0 else 0 for tv, d in zip(total_values, interpolated_deposits)]
    
    # Plot gain/loss percentage line
    sns.lineplot(x=dates, y=gains_percentage, color='black', ax=ax3, linewidth=2.5)
    
    # Add a horizontal line at y=0
    ax3.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    
    # Color the area above/below zero
    ax3.fill_between(dates, gains_percentage, 0, where=[g >= 0 for g in gains_percentage], color='green', alpha=0.2)
    ax3.fill_between(dates, gains_percentage, 0, where=[g < 0 for g in gains_percentage], color='red', alpha=0.2)
    
    ax3.set_title('Portfolio Return vs Total Deposits at Each Point in Time', pad=20)
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Return on Total Deposits (%)')
    ax3.tick_params(axis='x', rotation=45)
    ax3.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d %H:%M'))
    
    # Adjust layout
    plt.tight_layout()
    print("\nDone! Displaying portfolio visualization...")
    plt.show()

def plot_portfolio_for_gui(all_values, dates, ticker_map, total_deposits):
    """Generate portfolio visualization figure for embedding in GUI.
    This version is optimized for tkinter embedding.
    """
    print("\nGenerating portfolio visualization...")
    
    # Create a matplotlib Figure directly (better for tkinter than plt.subplots)
    fig = Figure(figsize=(10, 12), dpi=100, constrained_layout=True)
    
    # Create gridspec for proper subplot spacing
    gs = fig.add_gridspec(3, 1, height_ratios=[1, 1.5, 1], hspace=0.3)
    
    # Create the subplots
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])
    ax3 = fig.add_subplot(gs[2])
    
    # Add title to the entire figure with proper padding
    fig.suptitle('Portfolio Overview', fontsize=16, y=0.98)
    
    print("Drawing deposits and portfolio value chart...")
    # Top subplot - Total Deposits and Portfolio Value
    deposit_dates, deposit_amounts = zip(*total_deposits)
    
    # Use cleaner plot style 
    ax1.plot(deposit_dates, deposit_amounts, color='lightgreen', linewidth=2, label='Total Deposits (EUR)')
    
    # Calculate and plot total portfolio value
    total_values = []
    for i in range(len(dates)):
        total = sum(values[i][1] for values in all_values.values())
        total_values.append(total)
    
    ax1.plot(dates, total_values, color='blue', linewidth=2.5, label='Total Portfolio Value (EUR)')
    
    ax1.set_title('Total Deposits and Portfolio Value Over Time', fontsize=12)
    ax1.set_xlabel('')  # Remove x-label
    ax1.set_ylabel('EUR', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xticklabels([])  # Hide x-axis labels for top plot
    ax1.legend(loc='upper left', fontsize=9)
    
    print("Drawing individual holdings value chart...")
    # Middle subplot - Individual Holdings Values
    # Use a color cycle for better distinction between stocks
    colors = plt.cm.tab10.colors
    color_idx = 0
    
    for stock, values in all_values.items():
        dates_stock, amounts = zip(*values)
        if stock == 'Cash':
            ax2.plot(dates_stock, amounts, label='Cash', 
                    color='green', linestyle='--', linewidth=2)
        else:
            ticker = ticker_map.get(stock, 'N/A')
            ax2.plot(dates_stock, amounts, label=f"{ticker}", 
                    color=colors[color_idx % len(colors)], linewidth=1.5)
            color_idx += 1
    
    # Add total portfolio value to middle chart as well
    ax2.plot(dates, total_values, color='black', linewidth=2.5, label='Total')
    
    ax2.set_title('Individual Holdings Values Over Time', fontsize=12)
    ax2.set_xlabel('')  # Remove x-label
    ax2.set_ylabel('Value (EUR)', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_xticklabels([])  # Hide x-axis labels for middle plot
    
    # Use a legend with smaller font and scrollable if many items
    if len(all_values) > 10:
        ax2.legend(loc='upper left', fontsize=8, ncol=2)
    else:
        ax2.legend(loc='upper left', fontsize=9)
    
    print("Drawing total gain/loss chart...")
    # Bottom subplot - Total Gain/Loss
    # Interpolate deposit amounts to match the dates of total values
    deposit_df = pd.DataFrame({'date': deposit_dates, 'amount': deposit_amounts}).set_index('date')
    interpolated_deposits = [deposit_df.asof(date)['amount'] for date in dates]
    
    # Calculate gain/loss as percentage of total deposits at each point in time
    gains_percentage = [(tv - d) / d * 100 if d > 0 else 0 for tv, d in zip(total_values, interpolated_deposits)]
    
    # Plot gain/loss percentage line
    ax3.plot(dates, gains_percentage, color='black', linewidth=2.5, label='% Return')
    
    # Add a horizontal line at y=0
    ax3.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    
    # Color the area above/below zero
    ax3.fill_between(dates, gains_percentage, 0, where=[g >= 0 for g in gains_percentage], color='green', alpha=0.2)
    ax3.fill_between(dates, gains_percentage, 0, where=[g < 0 for g in gains_percentage], color='red', alpha=0.2)
    
    ax3.set_title('Portfolio Return vs Total Deposits', fontsize=12)
    ax3.set_xlabel('Date', fontsize=10)
    ax3.set_ylabel('Return on Deposits (%)', fontsize=10)
    ax3.tick_params(axis='x', rotation=45)
    ax3.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m-%d'))
    ax3.grid(True, alpha=0.3)
    
    print("\nDone! Visualization ready for display")
    
    # Return the figure instead of showing it
    return fig

def create_embedded_plots(parent_frame, all_values, dates, ticker_map, total_deposits):
    """Create visualizations directly embedded in a tkinter frame.
    This provides a smoother integration with the tkinter UI.
    
    Parameters:
    - parent_frame: tkinter frame to embed visualizations in (can be None to just create figures)
    - all_values, dates, ticker_map, total_deposits: visualization data
    
    Returns:
    - A dictionary of canvases and figures for reference
    """
    print("\nCreating embedded visualizations...")
    
    # Results dictionary to store canvases and figures
    result = {
        'canvases': {},
        'figures': {}
    }
    
    # Function to create a single plot in a given frame
    def create_plot(frame, plot_type):
        """Create a specific type of plot in the given frame"""
        if plot_type == "overview":
            # Create the overview plot (all three subplots)
            fig = plot_portfolio_for_gui(all_values, dates, ticker_map, total_deposits)
            result['figures']['overview'] = fig
            
            # Only create and attach canvas if frame is provided
            if frame is not None:
                canvas = FigureCanvasTkAgg(fig, frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill='both', expand=True)
                result['canvases']['overview'] = canvas
                return canvas
            return fig
            
        elif plot_type == "value":
            # Create just the portfolio value plot
            fig = Figure(figsize=(10, 6), dpi=100)
            ax = fig.add_subplot(111)
            
            # Total value
            total_values = []
            for i in range(len(dates)):
                total = sum(values[i][1] for values in all_values.values())
                total_values.append(total)
                
            # Deposits
            deposit_dates, deposit_amounts = zip(*total_deposits)
            
            # Plot
            ax.plot(deposit_dates, deposit_amounts, color='lightgreen', 
                   label='Total Deposits (EUR)', linewidth=2)
            ax.plot(dates, total_values, color='blue', 
                   label='Portfolio Value (EUR)', linewidth=2.5)
            
            ax.set_title('Portfolio Value vs Deposits', fontsize=14)
            ax.set_ylabel('EUR', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=10)
            
            fig.tight_layout()
            result['figures']['value'] = fig
            
            # Only create and attach canvas if frame is provided
            if frame is not None:
                canvas = FigureCanvasTkAgg(fig, frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill='both', expand=True)
                result['canvases']['value'] = canvas
                return canvas
            return fig
            
        elif plot_type == "holdings":
            # Create just the holdings plot
            fig = Figure(figsize=(10, 6), dpi=100) 
            ax = fig.add_subplot(111)
            
            # Use a color cycle
            colors = plt.cm.tab10.colors
            color_idx = 0
            
            # Calculate total portfolio value
            total_values = []
            for i in range(len(dates)):
                total = sum(values[i][1] for values in all_values.values())
                total_values.append(total)
            
            # Plot each holding
            for stock, values in all_values.items():
                dates_stock, amounts = zip(*values)
                if stock == 'Cash':
                    ax.plot(dates_stock, amounts, label='Cash', 
                           color='green', linestyle='--', linewidth=2)
                else:
                    ticker = ticker_map.get(stock, 'N/A')
                    # Use only ticker symbol as the label
                    ax.plot(dates_stock, amounts, label=f"{ticker}",
                           color=colors[color_idx % len(colors)], linewidth=1.5)
                    color_idx += 1
            
            # Add total portfolio value line
            ax.plot(dates, total_values, color='black', linewidth=2.5, label='Total')
            
            ax.set_title('Individual Holdings', fontsize=14)
            ax.set_ylabel('Value (EUR)', fontsize=12)
            ax.set_xlabel('Date', fontsize=12)
            ax.grid(True, alpha=0.3)
            
            # Make the legend more compact if many items
            if len(all_values) > 8:
                ax.legend(loc='upper left', fontsize=9, ncol=2)
            else:
                ax.legend(loc='upper left', fontsize=10)
                
            fig.tight_layout()
            result['figures']['holdings'] = fig
            
            # Only create and attach canvas if frame is provided
            if frame is not None:
                canvas = FigureCanvasTkAgg(fig, frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill='both', expand=True)
                result['canvases']['holdings'] = canvas
                return canvas
            return fig
            
        elif plot_type == "performance":
            # Create just the performance plot
            fig = Figure(figsize=(10, 6), dpi=100)
            ax = fig.add_subplot(111)
            
            # Calculate gain/loss as percentage
            deposit_dates, deposit_amounts = zip(*total_deposits)
            deposit_df = pd.DataFrame({'date': deposit_dates, 'amount': deposit_amounts}).set_index('date')
            
            total_values = []
            for i in range(len(dates)):
                total = sum(values[i][1] for values in all_values.values())
                total_values.append(total)
                
            interpolated_deposits = [deposit_df.asof(date)['amount'] for date in dates]
            gains_percentage = [(tv - d) / d * 100 if d > 0 else 0 
                               for tv, d in zip(total_values, interpolated_deposits)]
            
            # Plot gain/loss line
            ax.plot(dates, gains_percentage, color='black', linewidth=2.5)
            ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            
            # Color the areas
            ax.fill_between(dates, gains_percentage, 0, 
                           where=[g >= 0 for g in gains_percentage], 
                           color='green', alpha=0.2)
            ax.fill_between(dates, gains_percentage, 0, 
                           where=[g < 0 for g in gains_percentage], 
                           color='red', alpha=0.2)
            
            ax.set_title('Portfolio Performance', fontsize=14)
            ax.set_ylabel('Return on Deposits (%)', fontsize=12)
            ax.set_xlabel('Date', fontsize=12)
            ax.grid(True, alpha=0.3)
            
            fig.tight_layout()
            result['figures']['performance'] = fig
            
            # Only create and attach canvas if frame is provided
            if frame is not None:
                canvas = FigureCanvasTkAgg(fig, frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill='both', expand=True)
                result['canvases']['performance'] = canvas
                return canvas
            return fig
    
    # Create the plots
    if parent_frame is not None:
        # If parent frame is provided, create the overview plot by default
        create_plot(parent_frame, "overview")
    else:
        # If no parent frame, just create all the figure objects
        create_plot(None, "value")
        create_plot(None, "holdings")
        create_plot(None, "performance")
    
    print("Embedded visualizations created successfully")
    return result 