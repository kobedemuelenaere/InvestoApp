# Quick Start: Python Price Service for Next.js

## Minimal Setup (5 minutes)

### 1. Create Python Service

```python
# price-service/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance_cache as yf
from datetime import datetime
from typing import List, Optional

app = FastAPI()

# Allow CORS from your Next.js app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/fetch-prices")
async def fetch_prices(tickers: List[str], start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Fetch stock prices - works exactly like your Python code!
    """
    prices = {}
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(
                start=start_date or "2020-01-01",
                end=end_date or datetime.now().strftime("%Y-%m-%d")
            )
            
            if hist.empty:
                prices[ticker] = {"error": "No data"}
                continue
            
            prices[ticker] = {
                "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
                "close": hist["Close"].tolist(),
                "open": hist["Open"].tolist(),
                "high": hist["High"].tolist(),
                "low": hist["Low"].tolist(),
                "volume": hist["Volume"].tolist(),
            }
        except Exception as e:
            prices[ticker] = {"error": str(e)}
    
    return {"prices": prices}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "price-fetcher"}
```

### 2. Requirements File

```txt
# price-service/requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
yfinance-cache==0.2.0
pandas==2.1.3
```

### 3. Deploy to Railway (Free tier available)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize project
cd price-service
railway init

# Deploy
railway up

# Get the URL (something like: https://your-service.railway.app)
railway domain
```

### 4. Use in Next.js

```typescript
// lib/fetch-prices.ts
const PYTHON_SERVICE = process.env.NEXT_PUBLIC_PYTHON_SERVICE_URL!;

export async function fetchPrices(tickers: string[], startDate?: string, endDate?: string) {
  const res = await fetch(`${PYTHON_SERVICE}/api/fetch-prices`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tickers, start_date: startDate, end_date: endDate }),
  });
  
  return res.json();
}
```

### 5. Environment Variable

```bash
# .env.local
NEXT_PUBLIC_PYTHON_SERVICE_URL=https://your-service.railway.app
```

**That's it!** Your Python code now works in Next.js.



