import {api,h,money,num,loading,error,formatDateTime} from '../api.js';
export function render(){return `<div class="page-head"><span class="eyebrow">FIND STOCKS / COMPARE RESULTS</span><h1>Market Scanner — Synthetic Demo</h1><p>Explore how historical indicators work using fabricated price series. No real stock prices or trading signals are provided.</p></div>
<div class="notice"><strong>Scanner Safety Mode:</strong> Public stock-price file uploads are paused while data rights and regulatory classification are reviewed. Use the synthetic demonstration below; all numbers are fictional.</div>
<section class="panel"><div class="panel-title"><h2>Synthetic indicator demonstration</h2><span class="data-label">FICTIONAL DATA ONLY</span></div><p class="muted">Two invented price sequences, 85 example sessions each. Shows indicator mathematics without actual NSE prices, stock-specific entry/stop/target values, or trading orders.</p><button id="scanner-demo-button" class="button">Run fictional scanner demo →</button></section><section class="panel" id="scanner-upload-panel" hidden><div class="panel-title"><h2>Authorized historical file research</h2><span class="data-label">PRICE FILES</span></div><div class="field-grid cols-3"><label class="grow">Select NSE daily price files<input id="scan-files" type="file" accept=".csv,.zip" multiple></label><label>Paper account ₹<input type="number" id="scan-capital" value="50000" min="1000" max="50000000"></label><label>Risk per idea %<input type="number" id="scan-risk" value="1" min="0.1" max="5" step="0.1"></label></div><button class="button" id="scan-go">Compare stocks →</button><p class="muted">Files are processed for this scan, not permanently saved. Only stocks with enough uploaded history can be compared.</p><a class="text-link" href="https://www.nseindia.com/all-reports" target="_blank" rel="noopener noreferrer">Official NSE daily reports ↗</a></section>
<div id="scan-out"><div class="empty-state"><div class="empty-icon">◎</div><h3>Ready for synthetic demonstration</h3><p>Click Run fictional scanner demo. Public uploads of actual market-price files remain disabled unless separately approved.</p></div></div>`;}
export function mount(root){
 const demoButton=root.querySelector('#scanner-demo-button');
 const out=root.querySelector('#scan-out');
 demoButton.addEventListener('click',async()=>{
   out.innerHTML=loading('Computing indicators from fictional demo numbers…');
   try{
     const demo=await api('/api/scanner/demo');
     if(demo.synthetic!==true || demo.no_trade_levels!==true)throw new Error('Synthetic safety verification failed.');
     const tr=(demo.items||[]).map(x=>'<tr><td>'+h(x['Fictional series'])+'</td><td>'+num(x['Observations'])+'</td><td>'+h(x['Example score /100'])+'</td><td>'+h(x['SMA20 (demo units)'])+'</td><td>'+h(x['SMA50 (demo units)'])+'</td><td>'+h(x['RSI14 (demo)'])+'</td><td>'+h(x['20-step change %'])+'</td></tr>').join('');
     out.innerHTML='<section class="panel"><div class="panel-title"><h2>Fictional indicator comparison</h2><span class="data-label">SYNTHETIC · NOT STOCK DATA</span></div><div class="metrics-row"><div class="metric"><span>Made-up observations</span><strong>'+num(demo.observations)+'</strong></div><div class="metric"><span>Fictional series</span><strong>'+num(demo.fictional_series_count)+'</strong></div></div><div class="table-scroll"><table><thead><tr><th>Invented series</th><th>Bars</th><th>Example score</th><th>SMA20</th><th>SMA50</th><th>RSI14</th><th>20-step %</th></tr></thead><tbody>'+tr+'</tbody></table></div><p class="muted">Synthetic demonstration only. No NSE prices, named securities, trading levels or real orders. Results have no investing significance.</p></section>';
   }catch(e){out.innerHTML=error(e.message);}
 });
 api('/api/scanner/status').then(s=>{
   if(s.public_upload_enabled===true){
     root.querySelector('#scanner-upload-panel').hidden=false;
   }
 }).catch(()=>{});
 root.querySelector('#scan-go').addEventListener('click',async()=>{
 const files=root.querySelector('#scan-files').files,out=root.querySelector('#scan-out');if(!files.length){out.innerHTML=error('Choose dated CSV or ZIP price-history files before scanning.');return;}
 const data=new FormData();for(const f of files)data.append('files',f,f.name);
 const q=new URLSearchParams({capital:root.querySelector('#scan-capital').value,risk_pct:root.querySelector('#scan-risk').value});
 out.innerHTML=loading('Checking prices and comparing stocks…');
 try{const result=await api('/api/scanner/import?'+q,{method:'POST',body:data});const rows=result.top||[];out.innerHTML=`<section class="panel"><div class="panel-title"><h2>Ranked securities</h2><span class="data-label">${num(result.eligible_count)} STOCKS COMPARED</span></div><div class="metrics-row"><div class="metric"><span>Price records checked</span><strong>${num(result.quality?.['Price rows'])}</strong></div><div class="metric"><span>Stocks with price history</span><strong>${num(result.quality?.['Symbols with some data'])}</strong></div><div class="metric"><span>Latest price date</span><strong>${h(formatDateTime(result.summary?.['Latest market date in upload'],true))}</strong></div></div><div class="table-scroll"><table><thead><tr><th>Stock</th><th>Score /100</th><th>Price</th><th>Status</th><th>Paper qty</th><th>Planned loss</th><th>Explanation</th></tr></thead><tbody>${rows.map(x=>`<tr><td><a href="#/stocks?symbol=${encodeURIComponent(x.Symbol)}">${h(x.Symbol)}</a></td><td><strong>${h(x['Score /100'])}</strong></td><td>${money(x['Paper entry ref ₹'])}</td><td>${h(x.Status)}</td><td>${num(x['Paper shares'])}</td><td>${money(x['Max planned loss ₹'])}</td><td class="tiny">${h(x.Reasons)}</td></tr>`).join('')}</tbody></table></div><p class="muted">Results use uploaded historical prices and are for practice only. They do not predict future returns.</p></section>`;
 }catch(e){out.innerHTML=error(e.message);}
 });}
