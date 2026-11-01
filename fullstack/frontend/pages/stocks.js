import {api,h,money,pct,num,loading,error,metric,spark,infoSource,formatDateTime} from '../api.js';
export function render(){const q=new URLSearchParams(location.hash.split('?')[1]||'').get('symbol')||'RELIANCE';return `<div class="page-head"><span class="eyebrow">EQUITY ANALYTICS / ONE STOCK AT A TIME</span><h1>Stock Research</h1><p>Choose a symbol. Indicators, risks, entry references and paper sizing update together.</p></div>
<section class="panel"><div class="field-grid cols-4"><label class="grow">NSE symbol / company search<input id="stock-name" list="ticker-results" spellcheck="false" autocomplete="off" value="${h(q)}" placeholder="RELIANCE, INFY, HDFCBANK…"><datalist id="ticker-results"></datalist></label><label>Paper capital ₹<input type="number" id="capital" min="1000" max="50000000" value="50000"></label><label>Risk per idea %<input type="number" id="risk" min="0.1" max="5" step="0.1" value="1"></label><button class="button" id="run-stock" type="button">Refresh analysis</button></div><div id="search-hint" class="muted tiny">Choose a listed ticker or type its NSE symbol. Analysis starts automatically after a short pause.</div></section>
<div id="stock-output">${loading('Preparing historical stock analysis…')}</div>`;}
export async function mount(root){
 const input=root.querySelector('#stock-name'),datalist=root.querySelector('#ticker-results'),out=root.querySelector('#stock-output');
 let searchTimer, analysisTimer, searchId=0, runId=0, lastKey='';
 const hint=root.querySelector('#search-hint');
 input.addEventListener('input',()=>{
   clearTimeout(searchTimer);clearTimeout(analysisTimer);
   const q=input.value.trim();
   if(!q){++runId;lastKey='';out.removeAttribute('aria-busy');out.innerHTML='<div class="empty-state">Type an NSE symbol or choose a company to begin research.</div>';hint.textContent='Enter an NSE ticker or select a company from the list.';return;}
   const id=++searchId;
   searchTimer=setTimeout(async()=>{
     try{
       const data=await api('/api/universe?q='+encodeURIComponent(q)+'&limit=15');
       if(id!==searchId || q!==input.value.trim())return;
       datalist.innerHTML=data.items.map(x=>`<option value="${h(x.Symbol)}" label="${h(x.Company)}">${h(x.Company)}</option>`).join('');
       hint.textContent=data.items.length?'Choose a company from the suggestions, or enter its stock symbol.':'No matching company found. You can still enter a valid NSE symbol.';
       // Accept a full, exact company name as well as its NSE ticker.
       const company=data.items.find(x=>String(x.Company||'').trim().toLowerCase()===q.toLowerCase());
       if(company && String(company.Symbol).toUpperCase()!==q.toUpperCase()){
         input.value=company.Symbol;clearTimeout(analysisTimer);run();
       }
     }catch{if(id===searchId)hint.textContent='Directory search unavailable; you can still enter an exact NSE ticker.';}
   },300);
   // A ticker typed or selected by the user is enough. No mandatory Analyze click.
   if(/^[A-Z0-9][A-Z0-9&.-]{2,24}$/i.test(q)){
     analysisTimer=setTimeout(()=>run(),950);
   }
 });
 async function run(force=false){
   const sym=input.value.trim();if(!sym)return;
   const capital=Number(root.querySelector('#capital').value),risk=Number(root.querySelector('#risk').value);
   if(!/^[A-Z0-9][A-Z0-9&.-]{0,24}$/i.test(sym)){
     hint.textContent='Select an NSE ticker from the suggestions, or enter a valid symbol such as RELIANCE.';
     return;
   }
   if(!Number.isFinite(capital)||capital<1000||capital>50000000||!Number.isFinite(risk)||risk<0.1||risk>5){
     out.innerHTML=error('Enter ₹1,000–₹5 crore capital and a 0.1–5% risk setting.');return;
   }
   const key=sym.toUpperCase()+'|'+capital+'|'+risk;
   if(!force&&key===lastKey)return;
   lastKey=key;const current=++runId;
   out.setAttribute('aria-busy','true');
   out.innerHTML=loading('Checking historical candles and risk budget…');
 try{const params=new URLSearchParams({capital,risk_pct:risk});const data=await api('/api/stock/'+encodeURIComponent(sym)+'/analysis?'+params);
 if(current!==runId)return;
 out.removeAttribute('aria-busy');
 const good=data.decision.startsWith('CONDITIONAL');out.innerHTML=`<div class="status-banner ${good?'favorable':'waiting'}"><span class="status-dot"></span><div><strong>${h(data.decision)}</strong><p>${h(data.symbol.replace(/\.NS$/i,''))} · ${h(data.bias)} · Last price update: ${h(formatDateTime(data.time))}</p></div></div>
 <div class="metrics-row stock-metrics">${metric('Historical close',money(data.price),'May be delayed')}${metric('RSI (14)',num(data.indicators.rsi14),'Momentum reference')}${metric('ATR (14)',money(data.indicators.atr14),'Volatility range')}${metric('20-day momentum',pct(data.indicators.momentum20_pct),'Past performance')}</div>
 <section class="panel"><div class="panel-title"><h2>Historical price path</h2><span class="data-label">Historical prices · ${h(formatDateTime(data.time))}</span></div><div id="stock-chart">${loading('Loading daily bars…')}</div></section>
 <div class="two-col"><section class="panel"><div class="panel-title"><h2>Illustrative paper-trade plan</h2><span class="data-label">LONG / CASH EQUITY</span></div>
 <div class="notice ${good?'':'waiting-note'}">${good?'Conditional research setup, not a recommendation or an order.':'WAIT status: these quantities are a what-if example only. No paper position is opened or suggested.'}</div><div class="plan-grid">${metric('Reference entry',money(data.plan.entry))}${metric('ATR stop',money(data.plan.stop))}${metric('2R target',money(data.plan.target))}</div><div class="hr"></div><div class="plan-grid">${metric('Hypothetical shares',num(data.budget.shares))}${metric('Cash needed',money(data.budget.investment))}${metric('Planned loss',money(data.budget.planned_loss))}</div><p class="muted">Planned risk budget: ${money(data.budget.risk_budget)}. Actual gaps, fees and slippage can exceed the estimate. No orders are placed.</p></section>
 <section class="panel"><div class="panel-title"><h2>Reasoning & risk factors</h2><span class="data-label">HOW THE RESULT WAS CALCULATED</span></div><h3>Conditions observed</h3><ul class="reason-list">${data.observations.map(x=>`<li>${h(x)}</li>`).join('')}</ul><h3>Reasons to be cautious</h3><ul class="reason-list risk-list">${data.risks.map(x=>`<li>${h(x)}</li>`).join('')}</ul></section></div>
 <div class="notice">${h(infoSource)} A wait result means the conditions are not strong enough for a paper-trade setup.</div>`;
 try{
   const history=await api('/api/stock/'+encodeURIComponent(sym)+'/history?period=6mo');
   if(current===runId)root.querySelector('#stock-chart').innerHTML=spark(history.items);
 }catch(e){if(current===runId)root.querySelector('#stock-chart').innerHTML=error(e.message);}
 }catch(e){
   if(current===runId){
     out.removeAttribute('aria-busy');
     out.innerHTML=error(e.message)+`<div class="notice">Price information isn't available right now. Please try again later.</div>`;
     lastKey='';
   }
 }}
 root.querySelector('#run-stock').addEventListener('click',()=>run(true));
 input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();clearTimeout(analysisTimer);run(true);}});
 input.addEventListener('change',()=>{clearTimeout(analysisTimer);run();});
 root.querySelector('#capital').addEventListener('change',()=>run(true));
 root.querySelector('#risk').addEventListener('change',()=>run(true));
 await run();
}
