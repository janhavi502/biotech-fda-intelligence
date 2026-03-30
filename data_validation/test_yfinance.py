import yfinance as yf
import json
import os

BIOTECH_TICKERS = ["MRNA", "BNTX", "REGN", "BIIB", "GILD"]

def test_stock_history(ticker):
    print(f"Fetching stock history for {ticker}...")
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1mo")
    print(f"Records returned: {len(hist)}")
    print(f"Date range: {hist.index[0].date()} to {hist.index[-1].date()}")
    print(f"Latest close price: ${hist['Close'].iloc[-1]:.2f}")
    return hist

def test_stock_info(ticker):
    print(f"\nFetching company info for {ticker}...")
    stock = yf.Ticker(ticker)
    info = stock.info
    print(f"Company: {info.get('longName', 'N/A')}")
    print(f"Sector: {info.get('sector', 'N/A')}")
    print(f"Market Cap: ${info.get('marketCap', 0):,}")
    print(f"52 Week High: ${info.get('fiftyTwoWeekHigh', 'N/A')}")
    return info

def save_output(data, filename):
    os.makedirs("sample_outputs", exist_ok=True)
    filepath = f"sample_outputs/{filename}"
    data.to_csv(filepath)
    print(f"Saved to {filepath}")

if __name__ == "__main__":
    summary = {}

    for ticker in BIOTECH_TICKERS:
        hist = test_stock_history(ticker)
        info = test_stock_info(ticker)
        summary[ticker] = {
            "company": info.get("longName", "N/A"),
            "market_cap": info.get("marketCap", "N/A"),
            "latest_close": round(hist["Close"].iloc[-1], 2),
            "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "52_week_low": info.get("fiftyTwoWeekLow", "N/A")
        }
        print("---")

    # save summary as json
    with open("sample_outputs/yfinance_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # save full history of MRNA as csv sample
    mrna = yf.Ticker("MRNA")
    save_output(mrna.history(period="3mo"), "yfinance_sample.csv")

    print("\nAll yfinance tests passed.")