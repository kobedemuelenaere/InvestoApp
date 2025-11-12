# Investo - Portfolio Analyzer for Degiro

Investo is a powerful portfolio analysis tool designed specifically for Degiro investors. It allows you to visualize your portfolio performance, track historical values of your investments, and analyze your returns over time.

## Features

- **Portfolio Visualization**: View your portfolio performance in intuitive, interactive charts
- **Multiple Chart Types**: Analyze your data with specialized views:
  - Value & Deposits: Track your portfolio value against your deposits
  - Holdings: See individual stock performance with ticker symbols
  - Performance: Measure your percentage returns over time
- **Ticker Management**: Easily map your Degiro stock names to Yahoo Finance tickers
- **Currency Handling**: Automatic conversion of USD stocks to EUR for consistent reporting
- **Interactive Charts**: Zoom, pan, and export visualizations as needed
- **Historical Analysis**: Track your portfolio performance from the beginning of your investment journey

## Installation

### Requirements

- Python 3.8 or higher
- Tkinter (usually included with Python installation)

### Setup

1. Clone this repository or download the source code
2. Install required dependencies:

```bash
python -m pip install -r requirements.txt
```

## Usage

### Running the Application

```bash
python InvestoApp.py
```

### Complete Workflow

1. **Start Screen**: Launch the application and click "Start Analysis"

2. **Account Data**: 
   - The application will check for an existing Degiro account file
   - If none exists, or you want to update, follow the on-screen instructions to obtain and select your Degiro CSV export

3. **Ticker Configuration**:
   - Map each stock in your portfolio to its correct ticker symbol
   - Check the "USD" box for stocks traded in US dollars
   - Use the "Check All Tickers" button to validate your selections
   - Click "Save" when complete

4. **Analysis**:
   - The application will process your data, fetch current prices, and generate visualizations
   - Navigate between different chart tabs to explore your portfolio from different angles
   - Use the toolbar below each chart for zooming, panning, and saving images

## How to Obtain Your Degiro Account Data

1. Log in to your Degiro account
2. Go to Inbox > Account Statements (rekeningenoverzicht)
3. Update the start date to the earliest date of your account
4. Click 'Download as CSV'
5. Select the downloaded file in the Investo application

## Ticker Selection Guide

When configuring tickers:

- Make sure you select the correct ticker for each stock
- You can find tickers on Yahoo Finance (finance.yahoo.com)
- Beware that stocks on different exchanges have different tickers
- Example: HIMS & Hers on NYSE is 'HIMS', but on Tradegate it is '82W.BE'
- Check the 'USD' box for stocks traded in US dollars

## File Structure

- `InvestoApp.py`: Main application file
- `investo_utils/`: Directory containing utility modules:
  - `data_loader.py`: Functions for loading and processing data
  - `portfolio.py`: Portfolio calculation logic
  - `visualization.py`: Chart creation and visualization tools
  - `ticker_manager.py`: Ticker mapping functionality
- `requirements.txt`: Required Python packages
- `Account.csv`: Your Degiro account data (after you import it)
- `tickers.csv`: Saved ticker mappings

## Troubleshooting

### Common Issues

1. **"Error loading data"**: Make sure your Degiro CSV file is in the correct format
2. **Ticker validation fails**: Verify the ticker symbol on Yahoo Finance
3. **Missing stock prices**: Some stocks may not be available on Yahoo Finance or may have different ticker formats

### Data Backup

The application automatically creates backups of your Account.csv file when you import a new one, in case you need to revert to a previous version.

## License

This project is available under the MIT license.

## Acknowledgments

- Yahoo Finance for providing stock data
- Matplotlib and Seaborn for visualization capabilities
- Tkinter for the GUI framework
