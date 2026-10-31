"""Fresh headline retrieval and transparent rule-based exposure mapping.
No fabricated stories, no price causality claims, no arbitrary URL fetches.
"""
from __future__ import annotations
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
import re
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen, Request
from xml.etree import ElementTree as ET

CATEGORIES={
 'Banking / credit':{'words':('rbi','repo rate','bank','credit','npa','loan','liquidity'),
                     'indices':('NIFTY BANK','NIFTY 50'),'stocks':('HDFCBANK','ICICIBANK','SBIN','AXISBANK','KOTAKBANK')},
 'Information technology':{'words':('it services','software','ai spending','outsourcing','us tech','nasdaq','dollar'),
                     'indices':('NIFTY IT','NIFTY 50'),'stocks':('TCS','INFY','WIPRO','HCLTECH','TECHM')},
 'Oil & energy':{'words':('oil','brent','crude','opec','refinery','fuel','gas','petroleum'),
                     'indices':('NIFTY ENERGY','NIFTY 50'),'stocks':('RELIANCE','ONGC','BPCL','IOC')},
 'Auto':{'words':('auto sales','vehicle','ev sales','automobile','car sales','two-wheeler'),
                     'indices':('NIFTY AUTO','NIFTY 50'),'stocks':('MARUTI','TATAMOTORS','M&M','BAJAJ-AUTO')},
 'Pharma':{'words':('pharma','drug approval','fda','medicine','clinical trial'),
                     'indices':('NIFTY PHARMA','NIFTY 50'),'stocks':('SUNPHARMA','DRREDDY','CIPLA')},
 'Broad market / macro':{'words':('inflation','budget','fii','dii','nifty','sensex','gdp','fed rate','bond yields','trade tariff'),
                     'indices':('NIFTY 50','NIFTY BANK'),'stocks':()},
}
ENTITIES={'RELIANCE':('reliance','ril'), 'TCS':('tcs','tata consultancy'),
 'INFY':('infosys','infy'),'HDFCBANK':('hdfc bank',),'ICICIBANK':('icici bank',),
 'SBIN':('sbi','state bank of india'),'BHARTIARTL':('bharti airtel','airtel'),
 'ITC':('itc ltd','itc shares'),'MARUTI':('maruti suzuki',),
 'TATAMOTORS':('tata motors',),'SUNPHARMA':('sun pharma',)}
POSITIVE=('beats estimates','strong profit','record revenue','order win','rate cut','earnings beat',
          'higher guidance','approval granted','growth accelerates','dividend announced')
NEGATIVE=('profit warning','downgrade','earnings miss','fraud','regulatory probe','rate hike',
          'weak guidance','recall','lower forecast','default')

def _matches(text,term):
    return bool(re.search(r'(?<![a-z\d])'+re.escape(term.lower())+r'(?![a-z\d])',text))

def impact_hypotheses(headline:str)->dict:
    text=headline.lower()
    exposed=[]
    for title,entry in CATEGORIES.items():
        if any(_matches(text,word) for word in entry['words']):
            exposed.append({'theme':title,'indices':entry['indices'], 'stocks':entry['stocks']})
    named=[s for s,aliases in ENTITIES.items() if any(_matches(text,a) for a in aliases)]
    good=[x for x in POSITIVE if x in text];bad=[x for x in NEGATIVE if x in text]
    if good and not bad:context='Positive wording — effect unconfirmed'
    elif bad and not good:context='Negative wording — effect unconfirmed'
    else:context='Mixed or neutral wording — direction unknown'
    return {'themes':exposed,'named_stocks':named,'headline_tone':context,
            'warning':'These are potential exposures, not causal evidence or return forecasts. Verify the full article and market reaction.'}

def read_public_headlines(topic:str='Indian stock market',max_items:int=15)->list:
    allowed_topics={'Indian stock market':'NSE NIFTY Indian stock market',
                    'Company results':'NSE India quarterly earnings results',
                    'Economy & RBI':'India RBI policy inflation GDP',
                    'F&O / derivatives':'NSE derivatives SEBI F&O',
                    'Global & crude':'India market crude oil OPEC USD INR',
                    'Banking':'Indian banking RBI NIFTY BANK',
                    'Technology':'India IT services TCS Infosys earnings'}
    if topic not in allowed_topics:raise ValueError('Unsupported news category')
    q=allowed_topics[topic]+' when:7d'
    url='https://news.google.com/rss/search?'+urlencode({'q':q,'hl':'en-IN','gl':'IN','ceid':'IN:en'})
    req=Request(url,headers={'User-Agent':'Mozilla/5.0 (research RSS reader)'})
    try:
        with urlopen(req,timeout=9) as response:
            data=response.read(900000)
    except Exception as exc:
        raise RuntimeError('News feed is unavailable from this host. Try the official source links below.') from exc
    try:root=ET.fromstring(data)
    except ET.ParseError as exc:raise RuntimeError('News provider did not return a valid feed') from exc
    rows=[]
    for it in root.findall('.//item')[:max_items]:
        title=(it.findtext('title') or '').strip();link=(it.findtext('link') or '').strip()
        if not title or urlsplit(link).scheme!='https':continue
        pub=it.findtext('pubDate') or ''
        try: dt=parsedate_to_datetime(pub).astimezone(timezone.utc)
        except (TypeError,ValueError,OverflowError):dt=None
        src=it.find('source')
        rows.append({'title':title[:240], 'url':link,'published_utc':dt,
                     'source':src.text.strip() if src is not None and src.text else 'Google News RSS',
                     'mapping':impact_hypotheses(title)})
    return rows

OFFICIAL_LINKS={
 'NSE corporate announcements':'https://www.nseindia.com/companies-listing/corporate-filings-announcements',
 'NSE RSS feeds':'https://www.nseindia.com/static/rss-feed',
 'SEBI media releases':'https://www.sebi.gov.in/media-and-notifications/press-releases.html',
 'RBI press releases':'https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx',
}