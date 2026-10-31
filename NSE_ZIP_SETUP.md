# NSE.zip import — Indian Market Lab

The **All Stocks & Indices** tab accepts an NSE securities ZIP directly. No ZIP extraction, command line or brokerage account is needed.

## Steps

1. Open https://indian-market-lab-rohan.streamlit.app/
2. Select **All Stocks & Indices** and activate **Load directory and market tools**.
3. Expand **Directory source / upload NSE.zip, equity CSV or index CSV**.
4. Upload your `NSE.zip` with the ZIP uploader.
5. Choose **NSE securities**, filter by asset type and search by symbol or company name.
6. Select an instrument to request available historical research prices and use paper replay.

## Verified contents of the uploaded archive

| Type | Entries |
|---|---:|
| Mainboard equities | 2,620 |
| SME equities | 581 |
| ETFs | 358 |
| Closed-end mutual funds | 111 |
| InvITs | 5 |
| REITs | 3 |
| **Total** | **3,678** |

Historical symbol-change and name-change CSVs are not current listings and are intentionally excluded. The ZIP contains **no full index directory, historical OHLC, current quote feed, F&O contract-chain data or live prices**.

## Data handling

The ZIP is parsed in the app session and is **not committed** to the public GitHub repo. The user needs to upload the ZIP each new Streamlit session if needed. Current market prices are not inferred from this ZIP. Yahoo data requests may be delayed, blocked or unsupported for some security types.

Check rights before publishing exchange market data: https://www.nseindia.com/static/market-data/nse-data-policy

Official securities page: https://www.nseindia.com/static/market-data/securities-available-for-trading
