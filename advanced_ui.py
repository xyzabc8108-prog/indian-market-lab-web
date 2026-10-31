"""Advanced Streamlit research sections. Imports pure calculation modules only."""
from __future__ import annotations
from datetime import datetime,timezone
from io import BytesIO
import math
import pandas as pd
import streamlit as st
from research_engine import (normalize_symbol, validate_ohlcv, technical_snapshot,
    planning_levels, position_budget, scenario_simulation, explore_setups, option_long_budget, future_budget)
from news_radar import read_public_headlines, OFFICIAL_LINKS,impact_hypotheses

@st.cache_data(ttl=600,show_spinner=False)
def cached_headlines(topic):
    return read_public_headlines(topic)

def get_daily(symbol, history, demo):
    file=st.session_state.get('advanced_csv')
    if file is not None:
        return validate_ohlcv(pd.read_csv(BytesIO(file))), 'USER-IMPORTED CSV — verify date, source, corporate actions and intervals'
    d, origin=history(symbol,'1d','2y',demo)
    return validate_ohlcv(d),origin

def headline_time(ts):
    if ts is None:return 'Published time unverified'
    return ts.astimezone(__import__('zoneinfo').ZoneInfo('Asia/Kolkata')).strftime('%d %b %Y %I:%M %p IST')

def render_features(stock_tab, scenario_tab, budget_tab, fo_tab, news_tab, history, mode, symbols):
    demo=mode=='Synthetic demo'
    with stock_tab:
        st.subheader('Stock Decision Lab — enter one NSE stock or index')
        st.caption('Evidence-led scenarios. The tool does not know tomorrow’s price or produce calibrated buy/sell probabilities.')
        a,b=st.columns([2,1])
        stock_input=a.text_input('Name or NSE symbol','RELIANCE',help='e.g. RELIANCE, INFY, HDFC BANK, NIFTY 50')
        atr_multiple=b.slider('Stop distance (ATR multiple)',0.5,4.0,1.5,0.25)
        csv=st.file_uploader('Optional: import your own daily OHLCV CSV (time/date, open, high, low, close, volume)',
                             type=['csv'],key='advanced_upload')
        if csv is not None:
            if csv.size>5_000_000:st.error('Maximum CSV size for this dashboard is 5 MB.');st.session_state.pop('advanced_csv',None)
            else:st.session_state.advanced_csv=csv.getvalue()
        else:st.session_state.pop('advanced_csv',None)
        if st.button('Analyze stock',type='primary',key='analyze_adv'):
            try:
                symbol=normalize_symbol(stock_input)
                df,source=get_daily(symbol,history,demo)
                snap=technical_snapshot(df);plan=planning_levels(snap,atr_multiple=atr_multiple)
                st.session_state.stock_analysis=(symbol,mode, bool(csv), snap,plan,source)
            except (ValueError,KeyError,TypeError,ZeroDivisionError) as exc:st.error(str(exc))
        data=st.session_state.get('stock_analysis')
        if data:
            sym,src_mode,was_csv,snap,plan,source=data
            if src_mode!=mode or was_csv!=bool(csv):
                st.info('Data source changed. Click Analyze stock again.')
            else:
                st.caption('Symbol: '+sym+'  |  Data source: '+source)
                asof=snap['asof'];asof=asof.tz_convert('Asia/Kolkata') if asof.tzinfo else asof
                st.caption('Last available daily candle: '+str(asof)+' — not necessarily a current tradable quote')
                cols=st.columns(5)
                for col,(label,value) in zip(cols,[('Historical close',f"₹{snap['price']:,.2f}"),('ATR(14)',f"₹{snap['atr14']:,.2f}"),
                            ('RSI(14)',f"{snap['rsi14']:.1f}"),('Support (20)',f"₹{snap['support20']:,.2f}"),
                            ('Resistance (20)',f"₹{snap['resistance20']:,.2f}")]):col.metric(label,value)
                st.write('**Evidence:** '+snap['bias'])
                for obs in snap['observations']:st.write('• '+obs)
                st.write('**Hypothetical long-plan reference levels** (not an order or guarantee)')
                a,b,c,d=st.columns(4)
                a.metric('Reference entry',f"₹{plan['entry']:,.2f}")
                b.metric('Stop reference',f"₹{plan['stop']:,.2f}")
                c.metric('Target reference',f"₹{plan['target']:,.2f}")
                d.metric('Reward / planned loss',f"{plan['rr']:.1f}:1")
                st.caption(plan['reason']+'. Stops can gap and fill at worse prices. Waiting for confirmation or not trading can be appropriate.')
                st.write('**Favorable factors:** a confirmed trend, strong earnings verified from filings, manageable volatility, and alignment with the broader market.')
                st.write('**Key risks:** stale data, earnings/news gaps, false breakouts, slippage, concentration, and changes in market regime.')
    with scenario_tab:
        st.subheader('Historical Scenario Engine — up to 100,000 paths')
        st.caption('Resamples past daily returns. The output is a property of the model, NOT the actual chance of a stock rising/falling.')
        a,b=st.columns([2,1]); sym_input=a.text_input('NSE stock or index','TCS',key='sim_sym')
        horizon=b.select_slider('Trading-day horizon',options=[1,2,3,5,10,15,20,30,60],value=10)
        c,d,e=st.columns(3)
        n=c.select_slider('Number of scenarios',options=[1000,5000,10000,25000,50000,100000],value=10000)
        stress=d.slider('Volatility sensitivity',0.5,3.0,1.0,0.25)
        stop_mult=e.slider('Stop (ATR multiple)',0.5,4.0,1.5,0.25,key='sim_atr')
        if st.button('Run historical simulations',type='primary'):
            try:
                symbol=normalize_symbol(sym_input)
                df,origin=get_daily(symbol,history,demo);snap=technical_snapshot(df)
                plan=planning_levels(snap,atr_multiple=stop_mult)
                result=scenario_simulation(df,plan['entry'],plan['stop'],plan['target'],horizon,n,stress=stress)
                st.session_state.sim_run=(symbol,mode,bool(st.session_state.get('advanced_csv')),origin,plan,result,stress)
            except (ValueError,KeyError,TypeError,MemoryError) as exc:st.error(str(exc))
        result_data=st.session_state.get('sim_run')
        if result_data:
            sym,src,using_csv,origin,plan,result,stress_used=result_data
            if src!=mode or using_csv!=bool(st.session_state.get('advanced_csv')) or sym_input.strip().upper().replace('.NS','') not in sym:
                st.info('Inputs changed. Run simulations again before using these figures.')
            else:
                st.caption('For '+sym+' | '+origin+' | simulated paths: '+format(result['paths'],',')+
                           f" | {result['horizon']} trading days | volatility factor: {stress_used:.2f}×")
                a,b,c=st.columns(3)
                a.metric('Stop first (model)',f"{result['p_stop_first']*100:.1f}%")
                b.metric('Target first (model)',f"{result['p_target_first']*100:.1f}%")
                c.metric('Neither (model)',f"{result['p_neither']*100:.1f}%")
                a,b,c=st.columns(3)
                a.metric('5th percentile P&L',f"{result['p05_pct']:+.2f}%")
                b.metric('Median P&L',f"{result['median_pct']:+.2f}%")
                c.metric('95th percentile P&L',f"{result['p95_pct']:+.2f}%")
                st.caption(f"Historical candles: {result['sample_bars']} · Model downside tail mean: {result['avg_bad_5pct']:.2f}% · Monte Carlo-only stop frequency standard error: ±{result['stop_sampling_se_pct']:.2f} percentage points")
                st.warning('Historical resampling cannot capture regime shifts, changes in volatility, order-book liquidity, or realistic intraday stop execution. Daily CLOSE barriers and fixed exit levels were assumed. Do not use the percentages as genuine forecast odds.')
        st.divider()
        st.write('**1,000-configuration explorer** — 10 ATR stop distances × 10 reward targets × 10 holding periods. Evaluates 2,000 historical-resampled paths per setup (2 million path/setup comparisons).')
        if st.button('Compare 1,000 hypothetical setups'):
            try:
                symbol=normalize_symbol(sym_input)
                df,origin=get_daily(symbol,history,demo)
                grid=explore_setups(df)
                st.session_state.setup_grid=(symbol,mode,bool(st.session_state.get('advanced_csv')),origin,grid)
            except (ValueError,KeyError,TypeError,MemoryError) as exc:st.error(str(exc))
        saved=st.session_state.get('setup_grid')
        if saved:
            sm,src,csv_state,origin,grid=saved
            if src==mode and csv_state==bool(st.session_state.get('advanced_csv')):
                st.caption('Compared '+str(len(grid))+' setups using '+origin+'; ranking is in-sample and vulnerable to overfitting.')
                st.dataframe(grid.sort_values('Model mean return %',ascending=False).head(15),use_container_width=True,hide_index=True)
                st.download_button('Download all 1,000 configurations CSV',grid.to_csv(index=False),'setup_explorer.csv','text/csv')
                st.warning('Do not interpret the top row as the best real trade. Reusing the same resampled data to select setups creates selection bias. Test independently out of sample before relying on any pattern.')
            else:st.info('Inputs changed; rerun setup explorer.')
    with budget_tab:
        st.subheader('Fixed-budget position and loss planning')
        st.caption('Cash-equity long example; calculations are before possible gaps and actual fees.')
        a,b,c=st.columns(3)
        capital=a.number_input('Total trading capital ₹',1000.0,100000000.0,50000.0,step=1000.0,key='budget_c')
        risk_pct=b.number_input('Per-trade maximum planned loss %',0.1,5.0,0.5,step=0.1)
        allocation=c.number_input('Max capital allocated to one stock %',1.0,100.0,20.0)
        a,b,c=st.columns(3)
        entry=a.number_input('Entry price ₹',0.01,1000000.0,1000.0)
        stop=b.number_input('Stop reference ₹',0.01,1000000.0,970.0)
        target=c.number_input('Target ₹',0.01,1000000.0,1090.0)
        a,b,c=st.columns(3)
        friction=a.number_input('Estimated round-trip fees ₹ per share',0.0,10000.0,0.5)
        slip=b.number_input('Slippage % per side',0.0,10.0,0.1,step=0.05)
        daily_limit=c.number_input('Daily maximum planned loss %',0.1,10.0,1.5)
        try:
            result=position_budget(capital,risk_pct,allocation,entry,stop,target,friction,slip)
            cols=st.columns(4)
            cols[0].metric('Maximum shares',str(result['shares']))
            cols[1].metric('Cost at entry',f"₹{result['investment']:,.0f}")
            cols[2].metric('Modeled stop loss',f"₹{result['planned_loss']:,.0f}")
            cols[3].metric('Modeled reward',f"₹{result['estimated_reward']:,.0f}")
            st.caption(f"Risk budget ₹{result['risk_budget']:,.0f}; stop risks are estimates only. Daily stop threshold: ₹{capital*daily_limit/100:,.0f} (consider stopping paper trading at that loss).")
            if result['no_trade']:st.warning('No whole share fits BOTH your risk limit and allocation cap; skip this hypothetical trade.')
            st.write('**Trading plan checklist:** identify catalyst and trend; wait for a defined entry trigger; calculate position size first; avoid averaging into a losing position; account for charges; journal every outcome.')
        except ValueError as exc:st.warning(str(exc))
    with fo_tab:
        st.subheader('F&O budget and contract-risk desk (education only)')
        st.warning('Futures and options can cause rapid or complete loss of premium; futures can lose more than posted margin. No market option chain, Greeks, current lot size, or contract quotes are connected. Verify expiry/lot/margin with NSE and your broker.')
        a,b,c=st.columns(3)
        budget=a.number_input('Capital available ₹',1000.0,100000000.0,50000.0,key='fo_capital')
        risk=b.number_input('Maximum risk allocated to one F&O idea %',0.1,10.0,1.0,step=0.1,key='fo_risk')
        alloc=c.number_input('Maximum capital committed %',1.0,100.0,20.0,key='fo_alloc')
        product=st.radio('Instrument',['Long call (CE)','Long put (PE)','Futures (long illustration)'],horizontal=True)
        st.caption('Enter actual contract details from the current exchange contract file. Never assume historical lots are current.')
        a,b,c=st.columns(3)
        lot=a.number_input('Verified contract lot size',1,200000,65,step=1)
        expiry=b.date_input('Actual expiry (verify)',value=datetime.now().date(),key='fo_expiry')
        underlying=c.text_input('Underlying symbol (for notes)','NIFTY')
        if 'Long' in product:
            a,b,c=st.columns(3)
            premium=a.number_input('Actual option premium ₹',0.05,1000000.0,100.0)
            strike=b.number_input('Actual strike ₹',1.0,10000000.0,25000.0)
            spot=c.number_input('Underlying level (example) ₹',1.0,10000000.0,25000.0)
            per_lot_fee=st.number_input('Estimated total fee per lot ₹',0.0,10000.0,25.0)
            try:
                kind='Call (CE)' if product=='Long call (CE)' else 'Put (PE)'
                result=option_long_budget(budget,risk,alloc,premium,lot,strike,spot,kind,per_lot_fee)
                c1,c2,c3=st.columns(3)
                c1.metric('Lots within risk budget',str(result['lots']))
                c2.metric('Max premium at risk + specified fees',f"₹{result['max_loss_before_extra_fees']:,.0f}")
                c3.metric('Expiry breakeven (ignoring fees)',f"₹{result['break_even_expiry']:,.2f}")
                st.caption(f"Risk cap ₹{result['risk_budget']:,.0f}. A purchased option can expire worthless. Time decay and implied-volatility changes are NOT modeled.")
                if result['not_enough_budget']:st.warning('No full lot fits your limits. A zero-lot plan means no trade.')
            except ValueError as exc:st.warning(str(exc))
        else:
            a,b,c=st.columns(3)
            fprice=a.number_input('Actual futures price ₹',0.01,10000000.0,25000.0)
            margin=b.number_input('Broker-estimated margin per lot ₹',1.0,10000000.0,150000.0)
            stoppts=c.number_input('Planned stop distance in points ₹',0.01,1000000.0,150.0)
            fees=st.number_input('Estimated costs per lot ₹',0.0,10000.0,100.0,key='fut_fee')
            try:
                result=future_budget(budget,risk,alloc,fprice,lot,margin,stoppts,fees)
                a,b,c=st.columns(3)
                a.metric('Lots allowed',str(result['lots']))
                b.metric('Notional exposure',f"₹{result['notional']:,.0f}")
                c.metric('Loss at stop, if filled',f"₹{result['loss_at_stop_before_gaps']:,.0f}")
                st.caption('Futures risk is not bounded by the deposit/margin and may exceed your account equity in extreme cases.')
                if result['not_enough_budget']:st.warning('No complete futures lot fits both margin and risk budgets. Skip this trade.')
            except ValueError as exc:st.warning(str(exc))
        st.link_button('Verify derivatives lot sizes / permitted contracts at NSE',
                       'https://www.nseindia.com/static/products-services/equity-derivatives-contract-information')
    with news_tab:
        st.subheader('News Radar — market headlines & exposure hypotheses')
        st.caption('Google News RSS may be blocked on free cloud hosting. Headlines are fetched on demand and refreshed at most every 10 minutes.')
        topic=st.selectbox('News category',['Indian stock market','Company results','Economy & RBI',
                                             'F&O / derivatives','Global & crude','Banking','Technology'])
        if st.button('Fetch current headlines',type='primary'):
            try:st.session_state.news_data=(topic,cached_headlines(topic),datetime.now(timezone.utc))
            except RuntimeError as exc:st.error(str(exc))
        r=st.session_state.get('news_data')
        if r and r[0]==topic:
            _,rows,fetch_time=r
            st.caption('Feed requested at '+headline_time(fetch_time)+f' · {len(rows)} articles · headlines may be delayed')
            if not rows:st.info('Feed returned no articles. See the official source links below.')
            for i,item in enumerate(rows):
                with st.expander(item['title'],expanded=i<2):
                    st.caption(item['source']+' · '+headline_time(item['published_utc']))
                    st.link_button('Read the source article',item['url'])
                    mapping=item['mapping'];
                    if mapping['named_stocks']:st.write('Companies named: '+', '.join(mapping['named_stocks']))
                    if mapping['themes']:
                        for m in mapping['themes']:
                            st.write('**Possible affected theme:** '+m['theme'])
                            st.write('Related indices: '+', '.join(m['indices']))
                            if m['stocks']:st.write('Example related stocks: '+', '.join(m['stocks']))
                    else:st.write('No reliable sector association inferred from the headline alone.')
                    st.write('**Headline wording:** '+mapping['headline_tone'])
                    st.caption('This does NOT establish actual market direction or causation. Verify the full story, price data and exchange filings.')
        st.write('**Official sources for verification**')
        for label,url in OFFICIAL_LINKS.items():st.link_button(label,url)
        st.write('**How to use news responsibly:** read the underlying release, check announcement time and financial materiality, compare peer performance, then test price/volume before forming a trading hypothesis. News can already be priced in, and positive news can accompany a price decline.')