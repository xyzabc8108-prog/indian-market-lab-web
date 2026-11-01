# Phase 1 — Full-Market Scanner (NSE cash equities)

This is a **historical end-of-day, research-only** scanner for Indian Market Lab. It does not scrape live quotes, place trades, connect to a broker, or promise returns.

## Open in Streamlit

Go to **Full-Market Scanner** on your existing dashboard at https://indian-market-lab-rohan.streamlit.app/.

1. **Universe (recommended):** Upload the original `NSE.zip` that contains `EQUITY_L.csv`, `SME_EQUITY_L.csv` and related reference listings. The parser keeps the mainboard/SME **EQ series** only. It does *not* imply that all symbols have available history.
2. **Price history:** Download **CM-UDiFF Common Bhavcopy Final (ZIP)** for many trading sessions from [NSE daily reports](https://www.nseindia.com/all-reports). Upload the price ZIPs or CSVs through the Full-Market Scanner tab. A single daily ZIP is insufficient for technical indicators: aim for **at least 60 distinct trading days for each covered symbol**. You may also use your own historical daily OHLCV CSV with `date,symbol,open,high,low,close,volume`. Historical data is not bundled with this public repo.
3. **Paper budget:** Defaults: capital **₹50,000**, maximum planned loss **1% (₹500)** per idea, and maximum position allocation **25% (₹12,500)**. Change these only to test alternative hypothetical budgets.
4. Click **Validate files & scan eligible NSE stocks**, inspect coverage metrics, filter rankings, examine score components and export results.

### Data integrity, eligibility and reasons

- Recognizes common NSE historical headers (both `TckrSymb`/`OpnPric`/`TtlTradgVol` and `SYMBOL`/`OPEN`/`TOTTRDQTY`). Daily ZIPs can carry a `YYYYMMDD` date in their filename if the CSV lacks a trading-date column.
- Filters `EQ` series, non-positive/invalid OHLCV, future-dated bars, and conflicting duplicate symbol/day records; keeps matching non-conflicting duplicates once.
- A security needs **60 distinct daily sessions** and a recent bar within **7 calendar days of the uploaded snapshot's most recent date**. The app warns when the **whole snapshot** is old relative to today.
- Full-market *coverage* is disclosed in the UI. Without the NSE directory, scanning is limited to the uploaded price symbols. The supplied NSE ZIP contains listings, **not** candles.
- Score is **descriptive** 0–100, defined exactly as:
  - Trend (close > 20-SMA > 50-SMA): 25; partial trend: 12.
  - Momentum (20-session return >=5%): 20; positive return: 10.
  - 20-session average turnover >=₹2 crore: 15; >= minimum configured threshold: 8.
  - 14-session RSI in [45,70]: 10; nearby: 5.
  - Closing breakout above preceding 20-session high: 15; within 3% below high: 8.
  - Today's volume >=1.5× 20-session average: 15; >=1×: 8.
- Eligible **REVIEW CANDIDATE** requires score >=65, selected liquidity minimum, positive momentum, price above 20-SMA, and at least 1 paper share fitting both risk and capital caps. Everything else is **WATCH / NO PAPER ENTRY**. Neither status is an instruction to buy/sell.
- Illustrative long paper stop is close − 2×ATR14; target is a hypothetical 2R. Whole shares are `min(floor(₹500/stop_distance), floor(₹12,500/entry))` at default settings. There is **no leverage** and **no F&O** in this phase.

### Important limitations

This is **not** a current or real-time market scanner unless you supply current and complete price history. The model does not know future prices; a 100-point score is not a 100% success probability. No transaction fees, full market impact, dividends/corporate-action adjustments, gap execution, or orders are included. Research results may be biased by missing or delisted instruments, data errors or selection bias; verify NSE data rights before any public redistribution. Review the [NSE reports page](https://www.nseindia.com/all-reports) and applicable [NSE data policy](https://www.nseindia.com/static/market-data/nse-data-policy).

### Run tests

```bash
python -m unittest -v test_full_market_scanner
```

Tests use *explicitly synthetic* OHLCV fixtures, never live prices.