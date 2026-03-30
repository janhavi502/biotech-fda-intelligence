"""
Stock Market Data Scraper
Fetches historical price data, company info, and financial metrics
for biotech companies using the yfinance library.
Saves output as CSV and JSON files.
"""

import yfinance as yf
import json
import os
import logging
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR = "raw_data/yfinance"

BIOTECH_TICKERS = [
    "MRNA",   # Moderna
    "BNTX",   # BioNTech
    "REGN",   # Regeneron
    "BIIB",   # Biogen
    "GILD",   # Gilead Sciences
    "AMGN",   # Amgen
    "VRTX",   # Vertex Pharmaceuticals
    "ILMN",   # Illumina
    "INCY",   # Incyte
    "SGEN",   # Seagen
    "NVAX",   # Novavax
    "BEAM",   # Beam Therapeutics
    "CRSP",   # CRISPR Therapeutics
    "EDIT",   # Editas Medicine
    "NTLA"    # Intellia Therapeutics
]

HISTORY_PERIOD = "2y"       # 2 years of daily price history

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core utilities
# ---------------------------------------------------------------------------

def save_json(data: dict, folder: str, filename: str):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved JSON to {filepath}")


def save_markdown(records: list, folder: str, filename: str):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# Biotech Stock Intelligence Report\n\n")
        f.write(f"**Generated**: {datetime.today().strftime('%Y-%m-%d')}\n\n")
        f.write("---\n\n")
        for record in records:
            f.write(f"## {record.get('company', record.get('ticker', 'N/A'))}\n\n")
            f.write(f"**Ticker**: {record.get('ticker', 'N/A')}\n")
            f.write(f"**Sector**: {record.get('sector', 'N/A')}\n")
            f.write(f"**Market Cap**: ${record.get('market_cap', 0):,}\n")
            f.write(f"**Latest Close**: ${record.get('latest_close', 'N/A')}\n")
            f.write(f"**52 Week High**: ${record.get('52_week_high', 'N/A')}\n")
            f.write(f"**52 Week Low**: ${record.get('52_week_low', 'N/A')}\n")
            f.write(f"**Average Volume (30d)**: {record.get('avg_volume_30d', 'N/A'):,}\n")
            f.write(f"**Price Change (1M)**: {record.get('price_change_1m_pct', 'N/A')}%\n")
            f.write(f"**Price Change (6M)**: {record.get('price_change_6m_pct', 'N/A')}%\n\n")
            f.write("---\n\n")
    logger.info(f"Saved markdown to {filepath}")

# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

def fetch_stock_data(ticker: str) -> dict:
    """
    Fetch price history, company info, and key financial metrics
    for a given ticker symbol.
    """
    logger.info(f"Fetching data for {ticker}")
    stock = yf.Ticker(ticker)

    try:
        hist = stock.history(period=HISTORY_PERIOD)
        info = stock.info

        if hist.empty:
            logger.warning(f"No price history found for {ticker}")
            return {}

        # calculate price changes
        latest_close = round(hist["Close"].iloc[-1], 2)

        price_1m_ago = hist["Close"].iloc[-22] if len(hist) >= 22 else hist["Close"].iloc[0]
        price_6m_ago = hist["Close"].iloc[-126] if len(hist) >= 126 else hist["Close"].iloc[0]

        change_1m = round(((latest_close - price_1m_ago) / price_1m_ago) * 100, 2)
        change_6m = round(((latest_close - price_6m_ago) / price_6m_ago) * 100, 2)

        avg_volume_30d = int(hist["Volume"].iloc[-22:].mean()) if len(hist) >= 22 else 0

        record = {
            "ticker": ticker,
            "company": info.get("longName", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "latest_close": latest_close,
            "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
            "avg_volume_30d": avg_volume_30d,
            "price_change_1m_pct": change_1m,
            "price_change_6m_pct": change_6m,
            "total_history_days": len(hist),
            "history_start": str(hist.index[0].date()),
            "history_end": str(hist.index[-1].date())
        }

        return record, hist

    except Exception as e:
        logger.error(f"Failed to fetch data for {ticker}: {e}")
        return {}, None

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    today = datetime.today().strftime("%Y-%m-%d")
    output_folder = os.path.join(OUTPUT_DIR, today)
    os.makedirs(output_folder, exist_ok=True)

    all_summaries = []
    price_history_folder = os.path.join(output_folder, "price_history")
    os.makedirs(price_history_folder, exist_ok=True)

    for ticker in BIOTECH_TICKERS:
        result = fetch_stock_data(ticker)

        if not result or result[0] == {}:
            continue

        record, hist = result

        all_summaries.append(record)

        # save individual price history as CSV
        csv_path = os.path.join(price_history_folder, f"{ticker}.csv")
        hist.to_csv(csv_path)
        logger.info(f"Saved price history for {ticker} to {csv_path}")

    # save combined summary
    save_json(
        {t["ticker"]: t for t in all_summaries},
        output_folder,
        "stock_summary.json"
    )
    save_markdown(all_summaries, output_folder, "stock_report.md")

    logger.info(f"Stock scraping complete. {len(all_summaries)} tickers processed.")


if __name__ == "__main__":
    main()