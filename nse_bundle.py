"""Parse a user-provided NSE listings ZIP in memory; NO market-price data.

The ZIP is never extracted to disk or stored in a public repository.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import PurePosixPath

import pandas as pd

ALLOWED = {
    'EQUITY_L.csv': 'Mainboard equity',
    'SME_EQUITY_L.csv': 'SME equity',
    'eq_etfseclist.csv': 'ETF',
    'REITS_L.csv': 'REIT',
    'INVITS_L.csv': 'InvIT',
    'mf_close-end.csv': 'Closed-end MF',
}
MAX_ARCHIVE_BYTES = 4_000_000
MAX_MEMBER_BYTES = 6_000_000
MAX_TOTAL_BYTES = 12_000_000
VALID_SYMBOL = re.compile(r'^[A-Z0-9][A-Z0-9&._-]{0,25}$')


def _parse_csv(raw: bytes) -> list[dict[str, str]]:
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('cp1252')
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError('Missing CSV headings')
    def norm(v: str) -> str:
        return ' '.join(str(v or '').replace('_', ' ').strip().upper().split())
    return [{norm(k): str(v or '').strip() for k,v in row.items() if k} for row in reader]


def load_nse_bundle(raw: bytes) -> pd.DataFrame:
    """Return a searchable reference table from the NSE securities ZIP.

    Index prices, OHLC, F&O contracts and timestamps are NOT in the bundle.
    No network access, filesystem extraction, or hidden persistence.
    """
    if not raw or len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError('NSE ZIP must be between 1 byte and 4 MB')
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except (zipfile.BadZipFile, zipfile.LargeZipFile) as e:
        raise ValueError('Not a valid ZIP file') from e
    with zf:
        members = zf.infolist()
        if len(members) > 50 or sum(x.file_size for x in members) > MAX_TOTAL_BYTES:
            raise ValueError('NSE ZIP contains too many or oversized files')
        result = []
        handled = set()
        for member in members:
            filename = PurePosixPath(member.filename.replace('\\','/')).name
            if filename not in ALLOWED or member.is_dir() or filename in handled:
                continue
            if member.file_size > MAX_MEMBER_BYTES:
                raise ValueError('An NSE CSV member exceeds the size limit')
            handled.add(filename)
            category = ALLOWED[filename]
            records = _parse_csv(zf.read(member))
            for row in records[:12000]:
                symbol = row.get('SYMBOL','').strip().upper()
                if not VALID_SYMBOL.fullmatch(symbol):
                    continue
                if category == 'ETF':
                    company = row.get('SECURITYNAME') or row.get('SECURITY NAME') or row.get('UNDERLYING ASSET','')
                    series = 'ETF'
                else:
                    company = row.get('NAME OF COMPANY', '')
                    series = row.get('SERIES', '')
                if not company or (category == 'Mainboard equity' and series not in ('EQ','BE','BZ','SM','ST')):
                    continue
                result.append({
                    'Symbol': symbol,
                    'Company': company[:180],
                    'Series': series[:12],
                    'Asset type': category,
                    'ISIN': (row.get('ISIN NUMBER') or row.get('ISINNUMBER') or '')[:20],
                    'Provider ticker': symbol+'.NS',
                })
    if not result:
        raise ValueError('No recognized NSE securities listings inside ZIP')
    return (pd.DataFrame(result)
            .drop_duplicates(subset=['Asset type','Symbol','Series'])
            .sort_values(['Asset type','Symbol']).reset_index(drop=True))
