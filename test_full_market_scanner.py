"""Deterministic synthetic fixture tests for the NSE Phase 1 research-only scanner."""
import io, unittest, zipfile
from datetime import timedelta
import pandas as pd
from full_market_scanner import parse_daily_csv,parse_price_uploads,scan_market

def history(n=85):
    days=pd.bdate_range(end=pd.Timestamp.now().normalize()-timedelta(days=1),periods=n)
    data=[]
    for sym in ("AAA","BBB"):
        for i,d in enumerate(days):
            p=100+i*.7 if sym=="AAA" else 200-i*.35
            data.append((d.strftime("%Y-%m-%d"),sym,"EQ",p,p+1,p-1,p,100000+i*1000))
    return pd.DataFrame(data,columns=["date","symbol","series","open","high","low","close","volume"])

class FullMarketScannerTests(unittest.TestCase):
    def test_series_filter(self):
        f=history().iloc[:2].copy()
        f.loc[len(f)]=["2026-10-30","ZZZ","BE",20,21,19,20,100]
        r=parse_daily_csv(f.to_csv(index=False).encode())
        self.assertEqual(len(r),2)
    def test_udiff_filename(self):
        csv=b"TckrSymb,SctySrs,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol\nAAA,EQ,10,11,9,10,100\nBBB,BE,10,11,9,10,100\n"
        r=parse_daily_csv(csv,"BhavCopy_NSE_CM_0_0_0_20261030_F_0000.csv")
        self.assertEqual(len(r),1);self.assertEqual(r.symbol.iloc[0],"AAA")
    def test_reject_missing_date(self):
        raw=b"SYMBOL,OPEN,HIGH,LOW,CLOSE,VOLUME\nAAA,10,11,9,10,100\n"
        with self.assertRaises(ValueError):parse_daily_csv(raw)
    def test_reject_bad_ohlc(self):
        f=history().iloc[:2].copy();f.loc[0,"high"]=1
        r=parse_daily_csv(f.to_csv(index=False).encode())
        self.assertEqual(len(r),1)
    def test_conflicting_duplicates(self):
        f=history().iloc[:5].copy()
        change=f.iloc[:1].copy();change["close"]=change["close"]+.2
        p,quality=parse_price_uploads([("a.csv",f.to_csv(index=False).encode()),
                                       ("b.csv",change.to_csv(index=False).encode())])
        self.assertEqual(quality["Conflicting symbol-dates dropped"],1)
        self.assertEqual(len(p),4)
    def test_identical_duplicates(self):
        raw=history().iloc[:4].to_csv(index=False).encode()
        p,q=parse_price_uploads([("a.csv",raw),("b.csv",raw)])
        self.assertEqual(len(p),4)
        self.assertEqual(q["Conflicting symbol-dates dropped"],0)
    def test_udiff_zip(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:
            z.writestr("BhavCopy_NSE_CM_0_0_0_20261030_F_0000.csv",
                      b"TckrSymb,SctySrs,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol\nAAA,EQ,10,11,9,10,100\n")
        data,quality=parse_price_uploads([("nse.zip",b.getvalue())])
        self.assertEqual(len(data),1);self.assertEqual(quality["Files parsed"],1)
    def test_short_history_not_scanned(self):
        p,_=parse_price_uploads([("h.csv",history(12).to_csv(index=False).encode())])
        ranked,summary=scan_market(p)
        self.assertTrue(ranked.empty);self.assertEqual(summary["Insufficient history"],2)
    def test_scoring_and_budget(self):
        p,_=parse_price_uploads([("h.csv",history(85).to_csv(index=False).encode())])
        ranked,summary=scan_market(p,capital=50000,risk_pct=1,allocation_pct=25)
        self.assertEqual(len(ranked),2)
        self.assertTrue((ranked["Max planned loss ₹"]<=500.0001).all())
        self.assertTrue((ranked["Paper allocated ₹"]<=12500.0001).all())
        self.assertTrue((ranked["Score /100"]<=100).all())
        self.assertGreaterEqual(ranked.loc[ranked.Symbol=="AAA","Score /100"].iloc[0],ranked.loc[ranked.Symbol=="BBB","Score /100"].iloc[0])
        self.assertEqual(summary["Risk per idea ₹"],500)
    def test_universe_constraint(self):
        p,_=parse_price_uploads([("h.csv",history().to_csv(index=False).encode())])
        u=pd.DataFrame([{"Symbol":"AAA","Series":"EQ","Company":"Alpha","Asset type":"Mainboard equity"},
                        {"Symbol":"BBB","Series":"BE","Company":"Beta","Asset type":"Mainboard equity"}])
        ranked,_=scan_market(p,universe=u)
        self.assertEqual(ranked.Symbol.tolist(),["AAA"])
    def test_invalid_budget(self):
        p,_=parse_price_uploads([("h.csv",history().to_csv(index=False).encode())])
        with self.assertRaises(ValueError):scan_market(p,risk_pct=0)
        with self.assertRaises(ValueError):scan_market(p,capital=float("nan"))
    def test_stale_symbol(self):
        f=history(90)
        latest=pd.to_datetime(f.date).max()-timedelta(days=9)
        f=f[~((f.symbol=="BBB")&(pd.to_datetime(f.date)>=latest))]
        p,_=parse_price_uploads([("h.csv",f.to_csv(index=False).encode())])
        ranked,summary=scan_market(p)
        self.assertNotIn("BBB",ranked.Symbol.values)
        self.assertEqual(summary["Missing recent bars"],1)
    def test_reject_future_date(self):
        f=history().iloc[:2].copy()
        f.loc[0,"date"]="2099-01-01"
        r=parse_daily_csv(f.to_csv(index=False).encode())
        self.assertEqual(len(r),1)
    def test_no_broker_orders(self):
        import inspect,full_market_scanner
        source=inspect.getsource(full_market_scanner)
        self.assertNotIn("place_order",source)

if __name__=="__main__":unittest.main(verbosity=2)
