"""Historical-scenario and capital-risk utilities. Educational; never broker orders."""
from __future__ import annotations
from dataclasses import dataclass
import math
import re
import numpy as np
import pandas as pd

ALIASES = {
    'RELIANCE INDUSTRIES': 'RELIANCE', 'RELIANCE': 'RELIANCE',
    'TATA CONSULTANCY SERVICES': 'TCS', 'TCS':'TCS',
    'INFOSYS': 'INFY', 'INFY':'INFY', 'HDFC BANK':'HDFCBANK',
    'ICICI BANK':'ICICIBANK', 'STATE BANK OF INDIA':'SBIN',
    'SBI':'SBIN', 'BHARTI AIRTEL':'BHARTIARTL',
    'NIFTY 50':'^NSEI', 'NIFTY':'^NSEI', 'BANK NIFTY':'^NSEBANK',
    'BANKNIFTY':'^NSEBANK',
}

def normalize_symbol(raw: str) -> str:
    v = re.sub(r'\s+', ' ', str(raw).strip().upper())
    v = ALIASES.get(v, v)
    if v.startswith('NSE:'):
        v=v[4:]
    if v in ('^NSEI','^NSEBANK'):
        return v
    if v.endswith('.NS'):
        v = v[:-3]
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9&-]{0,19}', v):
        raise ValueError('Enter a valid NSE ticker (e.g. RELIANCE) or a supported company name.')
    return v+'.NS'


def validate_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or not len(frame):
        raise ValueError('No historical candles available.')
    d=frame.copy()
    cols = {str(c).lower().strip():c for c in d.columns}
    for c in ('open','high','low','close'):
        if c not in cols:
            raise ValueError(f'CSV/history must include {c} column.')
        d[c] = pd.to_numeric(d[cols[c]], errors='coerce')
    if 'volume' in cols:
        d['volume']=pd.to_numeric(d[cols['volume']], errors='coerce').fillna(0)
    else:
        d['volume']=0.0
    for k in ('time','date','datetime','timestamp'):
        if k in cols:
            d['time']=pd.to_datetime(d[cols[k]], errors='coerce', utc=True)
            break
    if 'time' not in d.columns:
        raise ValueError('CSV/history must include a time/date column.')
    d=d.dropna(subset=['time','open','high','low','close'])
    d=d[(d['open']>0)&(d['close']>0)&(d['low']>0)&(d['high']>=d['low'])
        &(d['high']>=d[['open','close']].max(axis=1))
        &(d['low']<=d[['open','close']].min(axis=1))]
    d=d.sort_values('time').drop_duplicates('time',keep='last').reset_index(drop=True)
    if len(d)<35:
        raise ValueError('At least 35 valid historical bars are required (90+ recommended).')
    return d[['time','open','high','low','close','volume']]


def technical_snapshot(frame:pd.DataFrame)->dict:
    df=validate_ohlcv(frame)
    c=df['close'].astype(float)
    high,low=df['high'].astype(float),df['low'].astype(float)
    prev=c.shift(1)
    tr=pd.concat([high-low, (high-prev).abs(), (low-prev).abs()],axis=1).max(axis=1)
    atr=float(tr.rolling(14,min_periods=14).mean().iloc[-1])
    delta=c.diff(); up=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    down=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    downs=float(down.iloc[-1]); ups=float(up.iloc[-1])
    rsi = 100.0 if downs<=0 and ups>0 else (50.0 if downs<=0 else float(100-100/(1+ups/downs)))
    sma20=float(c.tail(20).mean())
    sma50=float(c.tail(50).mean()) if len(c)>=50 else None
    sma200=float(c.tail(200).mean()) if len(c)>=200 else None
    momentum=float((c.iloc[-1]/c.iloc[-21]-1)*100) if len(c)>21 else None
    vol=float(c.pct_change().dropna().tail(30).std()*math.sqrt(252)*100)
    price=float(c.iloc[-1]); support=float(low.iloc[-21:-1].min()); resistance=float(high.iloc[-21:-1].max())
    observations=[]
    observations.append('Price above 20-bar average (upward trend evidence)' if price>sma20 else 'Price below 20-bar average (weak trend evidence)')
    if sma50 is not None: observations.append('20-bar average above 50-bar average' if sma20>sma50 else '20-bar average below 50-bar average')
    observations.append('RSI is elevated (>70); reversal risk' if rsi>70 else 'RSI is depressed (<30); downside momentum risk' if rsi<30 else 'RSI is between 30 and 70')
    observations.append('Above prior 20-bar resistance (breakout-like)' if price>resistance else 'Below prior 20-bar support (breakdown-like)' if price<support else 'Inside prior 20-bar range')
    points = int(price>sma20) + (int(sma20>sma50) if sma50 is not None else 0) + int(price>resistance)
    if rsi>75: points-=1
    bias='Upward evidence' if points>=2 else 'Downward evidence' if points<=0 else 'Mixed / wait for confirmation'
    return {'price':price,'asof':df['time'].iloc[-1], 'bars':len(df), 'atr14':atr, 'rsi14':rsi,
            'sma20':sma20,'sma50':sma50,'sma200':sma200,'vol_annual_pct':vol,
            'support20':support,'resistance20':resistance,'momentum20_pct':momentum,
            'bias':bias,'observations':observations}


def planning_levels(snap:dict, direction:str='Long', atr_multiple:float=1.5, target_multiple:float=2.0)->dict:
    """Hypothetical levels derived from the most recent historical closing price."""
    p=float(snap['price']); atr=float(snap['atr14']); dist=max(0.01, atr*atr_multiple)
    direction=direction.title()
    if direction not in ('Long','Short'):
        raise ValueError('Direction must be Long or Short')
    if direction=='Long':
        stop=max(0.01,p-dist);target=p+dist*target_multiple
        reason='ATR-distance below last close; consider waiting for confirmation above resistance'
    else:
        stop=p+dist;target=max(0.01,p-dist*target_multiple)
        reason='ATR-distance above last close; shorting may be restricted and has unbounded theoretical risk'
    return {'entry':p,'stop':stop,'target':target,'unit_risk':abs(p-stop),
            'rr':abs(target-p)/abs(stop-p), 'reason':reason, 'direction':direction}


def position_budget(capital:float,risk_pct:float,allocation_pct:float,entry:float,stop:float,target:float,
                    fees_round_trip_per_unit:float=0.0, slippage_pct_per_side:float=0.0)->dict:
    """Simple cash-long sizing. Fees and gaps can exceed budget; no execution guarantees."""
    vals=[capital,risk_pct,allocation_pct,entry,stop,target,fees_round_trip_per_unit,slippage_pct_per_side]
    if not all(math.isfinite(float(x)) for x in vals):raise ValueError('All fields must be finite.')
    if capital<=0 or not (0<risk_pct<=10) or not (0<allocation_pct<=100) or not (0<stop<entry<target):
        raise ValueError('Require capital>0, risk 0–10%, allocation 0–100%, stop < entry < target.')
    if fees_round_trip_per_unit<0 or not (0<=slippage_pct_per_side<=10):
        raise ValueError('Fees/slippage must not be negative or implausible.')
    friction=fees_round_trip_per_unit + 2*entry*slippage_pct_per_side/100
    loss_per_share=(entry-stop)+friction
    shares=max(0,min(math.floor(capital*risk_pct/100/loss_per_share),
                     math.floor(capital*allocation_pct/100/(entry*(1+slippage_pct_per_side/100)))))
    return {'shares':shares,'investment':shares*entry,
            'planned_loss':shares*loss_per_share,'estimated_reward':shares*max(0,(target-entry)-friction),
            'risk_budget':capital*risk_pct/100,'unit_risk_with_friction':loss_per_share,
            'no_trade':shares<1}


def scenario_simulation(frame:pd.DataFrame,entry:float,stop:float,target:float,
                        horizon:int=10,paths:int=20000,seed:int=2026,stress:float=1.0)->dict:
    """Historical daily-return bootstrap; not forward prediction or calibrated likelihood."""
    df=validate_ohlcv(frame)
    if not all(math.isfinite(x) for x in (entry,stop,target,stress)):
        raise ValueError('Invalid numbers')
    if not (0<stop<entry<target):
        raise ValueError('Simulation uses long plan stop < entry < target')
    if not (1<=horizon<=60 and 1000<=paths<=100000 and 0.5<=stress<=3):
        raise ValueError('Horizon 1–60, paths 1,000–100,000 and stress 0.5–3.')
    returns=df['close'].pct_change().replace([np.inf,-np.inf],np.nan).dropna().to_numpy(dtype=float)
    if len(returns)<34:raise ValueError('Not enough valid returns')
    # Capping a single bad split or error reduces contamination, not crash probability.
    if np.any(returns<=-1):raise ValueError('Invalid historical returns')
    rng=np.random.default_rng(int(seed))
    logret=np.log1p(returns)
    sampled=rng.choice(logret,size=(paths,horizon),replace=True)*stress
    # Log-returns ensure positive paths; stress scaling is an illustrative sensitivity only.
    traj=entry*np.exp(np.cumsum(sampled,axis=1))
    stop_mask=traj<=stop;target_mask=traj>=target
    first_s=np.where(stop_mask.any(axis=1),stop_mask.argmax(axis=1),horizon)
    first_t=np.where(target_mask.any(axis=1),target_mask.argmax(axis=1),horizon)
    # Gaps and intraday ordering are not modelled; daily-closing barrier rule only.
    stopped=first_s<first_t;hit_target=first_t<first_s
    unresolved=~(stopped|hit_target)
    last=traj[:,-1]
    outcomes=np.where(stopped,stop,np.where(hit_target,target,last))
    pnl_pct=(outcomes/entry-1)*100
    return {'paths':paths,'horizon':horizon,'sample_bars':len(df),'returns_sample':len(returns),
            'p_stop_first':float(stopped.mean()),'p_target_first':float(hit_target.mean()),
            'p_neither':float(unresolved.mean()),'p_loss':float((pnl_pct<0).mean()),
            'median_pct':float(np.median(pnl_pct)),'mean_pct':float(pnl_pct.mean()),
            'p05_pct':float(np.percentile(pnl_pct,5)),'p95_pct':float(np.percentile(pnl_pct,95)),
            'avg_bad_5pct':float(pnl_pct[pnl_pct<=np.percentile(pnl_pct,5)].mean()),
            'stop_sampling_se_pct':float(100*math.sqrt(max(1e-12,float(stopped.mean()*(1-stopped.mean()))/paths))),
            'source':'Historical return resampling, independent draws with replacement; daily CLOSE barrier approximation. Model assumptions dominate sampling error.'}


def option_long_budget(capital:float,risk_pct:float,allocation_pct:float,
                       premium:float,lot_size:int,strike:float,spot:float,kind:str,fee_per_lot:float=0)->dict:
    """Long options only. Premium risk all the way to zero, excluding any unexpected execution costs."""
    if kind not in ('Call (CE)','Put (PE)'):raise ValueError('Only long call or long put supported.')
    if not (capital>0 and 0<risk_pct<=10 and 0<allocation_pct<=100 and premium>0 and
            int(lot_size)==lot_size and lot_size>0 and strike>0 and spot>0 and fee_per_lot>=0):
        raise ValueError('Check budget, premium, contract size and strike inputs')
    cost=premium*int(lot_size)+fee_per_lot
    lots=max(0,min(math.floor(capital*risk_pct/100/cost),math.floor(capital*allocation_pct/100/cost)))
    breakeven=strike+premium if kind=='Call (CE)' else strike-premium
    intrinsic=max(0,spot-strike) if kind=='Call (CE)' else max(0,strike-spot)
    return {'lots':lots,'total_premium':lots*cost,'max_loss_before_extra_fees':lots*cost,
            'break_even_expiry':breakeven,'intrinsic_now':intrinsic,'not_enough_budget':lots==0,
            'per_lot_cost':cost,'risk_budget':capital*risk_pct/100}


def future_budget(capital:float,risk_pct:float,allocation_pct:float,
                  futures_price:float,lot_size:int,margin_per_lot:float,stop_points:float,
                  friction_per_lot:float=0)->dict:
    if not (capital>0 and 0<risk_pct<=10 and 0<allocation_pct<=100 and futures_price>0
            and int(lot_size)==lot_size and lot_size>0 and margin_per_lot>0 and stop_points>0 and friction_per_lot>=0):
        raise ValueError('Invalid futures risk inputs')
    unit=lot_size*stop_points+friction_per_lot
    lots=max(0,min(math.floor(capital*risk_pct/100/unit),math.floor(capital*allocation_pct/100/margin_per_lot)))
    return {'lots':lots,'notional':lots*lot_size*futures_price,'margin_estimate':lots*margin_per_lot,
            'loss_at_stop_before_gaps':lots*unit,'risk_budget':capital*risk_pct/100,
            'not_enough_budget':lots==0}


def explore_setups(frame:pd.DataFrame,paths:int=2000,seed:int=2026)->pd.DataFrame:
    """Explore 1,000 illustrative combinations on shared historical-resampling paths.

    Fixed reference entry at last close, 10 ATR stops × 10 target reward multiples ×
    10 horizons. Not validated, not optimized out of sample; NOT a trading recommendation.
    """
    df=validate_ohlcv(frame);snap=technical_snapshot(df)
    entry=snap['price'];atr=snap['atr14']
    if atr<=0:raise ValueError('Cannot compare setups when ATR is zero')
    logret=np.log1p(df['close'].pct_change().dropna().to_numpy(dtype=float))
    rng=np.random.default_rng(int(seed))
    future=entry*np.exp(np.cumsum(rng.choice(logret,size=(paths,30),replace=True),axis=1))
    rows=[]
    # 10 * 10 * 10 = exactly 1,000 configurations (2,000 paths each by default)
    stops=np.linspace(0.75,3.0,10)
    rewards=np.linspace(0.75,3.0,10)
    horizons=(1,2,3,4,5,7,10,14,20,30)
    for horizon in horizons:
        trajectory=future[:,:horizon]
        for stop_atr in stops:
            stop=max(0.01,entry-stop_atr*atr)
            for rr in rewards:
                target=entry+(entry-stop)*rr
                hit_s=trajectory<=stop;hit_t=trajectory>=target
                si=np.where(hit_s.any(axis=1),hit_s.argmax(axis=1),horizon)
                ti=np.where(hit_t.any(axis=1),hit_t.argmax(axis=1),horizon)
                loss=si<ti;profit=ti<si
                outcome=np.where(loss,stop,np.where(profit,target,trajectory[:,-1]))
                ret=(outcome/entry-1)*100
                rows.append({'Days':horizon,'Stop ATR':round(float(stop_atr),2),'Target R':round(float(rr),2),
                             'Stop ₹':round(float(stop),2),'Target ₹':round(float(target),2),
                             'Model target first %':round(float(profit.mean()*100),1),
                             'Model stop first %':round(float(loss.mean()*100),1),
                             'Model mean return %':round(float(ret.mean()),2),
                             'Model worst 5% threshold':round(float(np.percentile(ret,5)),2)})
    return pd.DataFrame(rows)