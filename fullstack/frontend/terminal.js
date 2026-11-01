import {api,h,money,pct,formatDateTime} from './api.js';

const RANGES={
 '1m':['1d','5d'], '5m':['5d','1mo'],'15m':['5d','1mo'],
 '1h':['5d','1mo'],'1d':['3mo','6mo','1y','2y','5y'],'1wk':['6mo','1y','2y','5y']
};
const RANGE_LABELS={'1d':'1 day','5d':'5 days','1mo':'1 month','3mo':'3 months','6mo':'6 months','1y':'1 year','2y':'2 years','5y':'5 years'};
const POPULAR=[
 ['RELIANCE','Reliance Industries'],['TCS','Tata Consultancy Services'],['INFY','Infosys'],
 ['HDFCBANK','HDFC Bank'],['ICICIBANK','ICICI Bank'],['SBIN','State Bank of India'],
 ['BHARTIARTL','Bharti Airtel'],['ITC','ITC'],['LT','Larsen & Toubro'],
 ['TATASTEEL','Tata Steel'],['WIPRO','Wipro'],['MARUTI','Maruti Suzuki'],
 ['SUNPHARMA','Sun Pharma'],['ONGC','ONGC'],['AXISBANK','Axis Bank']
].map(([Symbol,Company])=>({Symbol,Company,Series:'EQ'}));
const $=id=>document.getElementById(id);
const fmt=n=>money(n);
const state={symbol:'RELIANCE',interval:'1d',lookback:'6mo',horizon:10,
            watchMode:'all',search:'',offset:0,watchSeq:0,seq:0,latest:null,
            chart:null,resizeObserver:null,series:null,selectedFromList:false};
let symbolTimer=null;
function clock(){
 $('ist-clock').textContent=formatDateTime(new Date().toISOString())+' IST';
}
clock();setInterval(clock,30000);

function resetHistory(){
 const select=$('chart-lookback'),ranges=RANGES[state.interval];
 const remembered=ranges.includes(state.lookback)?state.lookback:
                  (state.interval==='1d'?'6mo':ranges[0]);
 state.lookback=remembered;
 select.innerHTML=ranges.map(v=>'<option value="'+v+'"'+(v===remembered?' selected':'')+'>'+RANGE_LABELS[v]+'</option>').join('');
}
function watchCards(items,append=false){
 const holder=$('terminal-watch-items');
 if(!append)holder.innerHTML='';
 if(!items.length&&!append){holder.innerHTML='<div class="terminal-skeleton">No matching stocks. Try a symbol such as TCS.</div>';return;}
 for(const item of items){
   const symbol=String(item.Symbol||'').toUpperCase();
   const button=document.createElement('button');
   button.type='button';button.className='watch-item'+(symbol===state.symbol?' active':'');
   button.innerHTML='<strong>'+h(symbol)+'</strong><small>'+h(item.Company||'NSE equity')+'</small>';
   button.addEventListener('click',()=>choose(symbol,item.Company||symbol));
   holder.append(button);
 }
}
function choose(sym,company=''){
 state.symbol=String(sym||'').toUpperCase().trim();
 $('terminal-symbol').value=state.symbol;
 document.querySelectorAll('.watch-item').forEach(b=>b.classList.toggle('active',b.querySelector('strong')?.textContent===state.symbol));
 $('instrument-name').textContent=company && company!==state.symbol?state.symbol+' · '+company:state.symbol;
 loadTerminal();
}
async function loadWatch(append=false){
 const seq=++state.watchSeq;
 if(state.watchMode==='popular'){
   const q=state.search.toLowerCase();
   const filtered=POPULAR.filter(item=>item.Symbol.toLowerCase().includes(q)||item.Company.toLowerCase().includes(q));
   watchCards(filtered);
   $('universe-source').textContent='Popular Indian stocks · examples only';
   $('watch-more').hidden=true;
   return;
 }
 if(!append)state.offset=0;
 const q=state.search.trim();
 try{
   const d=await api('/api/terminal/universe?'+new URLSearchParams({q,limit:60,offset:state.offset}));
   if(seq!==state.watchSeq)return;
   watchCards(d.items,append);
   state.offset+=d.items.length;
   $('watch-more').hidden=!d.has_more;
   $('universe-source').textContent=
     (d.loaded_count>100?'Search '+d.loaded_count.toLocaleString('en-IN')+' NSE listed entries':'Limited NSE directory available')+
     ' · '+d.total.toLocaleString('en-IN')+' matching';
 }catch(e){
   if(seq!==state.watchSeq)return;
   if(!append)watchCards(POPULAR);
   $('universe-source').textContent='Market directory unavailable. Enter any valid NSE symbol directly.';
   $('watch-more').hidden=true;
 }
}
function toggleWatch(mode){
 state.watchMode=mode;state.offset=0;
 $('watch-all').classList.toggle('selected',mode==='all');
 $('watch-favorites').classList.toggle('selected',mode==='popular');
 loadWatch();
}
$('watch-all').addEventListener('click',()=>toggleWatch('all'));
$('watch-favorites').addEventListener('click',()=>toggleWatch('popular'));
$('watch-more').addEventListener('click',()=>loadWatch(true));
$('terminal-symbol').addEventListener('input',()=>{
 clearTimeout(symbolTimer);
 state.search=$('terminal-symbol').value.trim();
 symbolTimer=setTimeout(()=>loadWatch(),350);
});
$('terminal-symbol').addEventListener('keydown',e=>{
 if(e.key==='Enter'){
   e.preventDefault();clearTimeout(symbolTimer);
   const symbol=$('terminal-symbol').value.trim().toUpperCase();
   if(/^[A-Z0-9][A-Z0-9&.-]{0,24}$/.test(symbol))choose(symbol);
   else $('universe-source').textContent='Select a symbol from the list, or type a valid NSE symbol.';
 }
});
$('candle-interval').addEventListener('change',()=>{
 state.interval=$('candle-interval').value;
 resetHistory();loadTerminal();
});
$('chart-lookback').addEventListener('change',()=>{
 state.lookback=$('chart-lookback').value;loadTerminal();
});
$('future-horizon').addEventListener('change',()=>{
 state.horizon=Number($('future-horizon').value);loadTerminal();
});
$('reload-terminal').addEventListener('click',()=>loadTerminal());
for(const id of ['show-sma20','show-sma50','show-ema20']){
 $(id).addEventListener('change',()=>{if(state.latest)drawCandles(state.latest.bars)});
}
function cleanupChart(){
 if(state.resizeObserver){state.resizeObserver.disconnect();state.resizeObserver=null;}
 if(state.chart){state.chart.remove();state.chart=null;}
}
function fallbackCandles(rows){
 const subset=rows.slice(-100);if(!subset.length)return '<div class="chart-placeholder">No candles were returned.</div>';
 const low=Math.min(...subset.map(r=>r.low)),high=Math.max(...subset.map(r=>r.high)),span=Math.max(.0001,high-low);
 const w=960,hh=410,margin=22,step=(w-margin*2)/subset.length;
 const y=value=>Math.round(30+(high-value)/span*330);
 const shapes=subset.map((r,i)=>{
   const x=(margin+i*step+step/2).toFixed(1);
   const color=r.close>=r.open?'#00e676':'#ff3158';
   const top=y(Math.max(r.open,r.close)),bottom=y(Math.min(r.open,r.close));
   return '<line x1="'+x+'" x2="'+x+'" y1="'+y(r.high)+'" y2="'+y(r.low)+'" stroke="'+color+'" stroke-width="1.1"/>'+
          '<rect x="'+(Number(x)-Math.max(1,step*.28)).toFixed(1)+'" y="'+top+'" width="'+Math.max(2,step*.55).toFixed(1)+'" height="'+Math.max(1,bottom-top)+'" fill="'+color+'"/>';
 }).join('');
 return '<svg class="fallback-chart" role="img" aria-label="Candlestick prices" viewBox="0 0 960 410" preserveAspectRatio="none">'+
  '<g stroke="#262626" stroke-width="1"><line x1="0" x2="960" y1="110" y2="110"/><line x1="0" x2="960" y1="210" y2="210"/><line x1="0" x2="960" y1="310" y2="310"/></g>'+shapes+'</svg>';
}
function drawCandles(rows){
 cleanupChart();
 const host=$('candle-chart');host.innerHTML='';
 const lib=window.LightweightCharts;
 if(!lib||typeof lib.createChart!=='function'||!lib.CandlestickSeries){
   host.innerHTML=fallbackCandles(rows);
   $('chart-timeframe').textContent='Candlesticks · Basic chart view';
   return;
 }
 try{
   const width=Math.max(300,host.clientWidth);
   const chart=lib.createChart(host,{
     width,height:host.clientHeight||480,
     layout:{background:{type:'solid',color:'#070707'},textColor:'#c2c2c2',
             fontFamily:'DM Sans, sans-serif',attributionLogo:true},
     grid:{vertLines:{color:'#1f1f1f'},horzLines:{color:'#1f1f1f'}},
     crosshair:{mode:lib.CrosshairMode?.Normal??0},
     rightPriceScale:{borderColor:'#3a3a3a'},
     timeScale:{borderColor:'#3a3a3a',timeVisible:true,secondsVisible:false,rightOffset:4},
     localization:{timeFormatter:time=>new Date(Number(time)*1000).toLocaleString('en-GB',
       {timeZone:'Asia/Kolkata',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'})},
   });
   state.chart=chart;
   const candles=chart.addSeries(lib.CandlestickSeries,{
     upColor:'#00e676',downColor:'#ff3158',borderVisible:false,
     wickUpColor:'#00e676',wickDownColor:'#ff3158',
     priceLineVisible:true,
   });
   candles.setData(rows.map(r=>({time:r.time,open:r.open,high:r.high,low:r.low,close:r.close})));
   const histogram=chart.addSeries(lib.HistogramSeries,{
     priceFormat:{type:'volume'},priceScaleId:'volume',
     priceLineVisible:false,lastValueVisible:false
   });
   histogram.priceScale().applyOptions({scaleMargins:{top:.78,bottom:0}});
   histogram.setData(rows.map(r=>({time:r.time,value:r.volume,
     color:r.close>=r.open?'#00c85366':'#ff315866'})));
   for(const [id,key,color] of [['show-sma20','sma20','#00e676'],
                                ['show-sma50','sma50','#c5c5c5'],
                                ['show-ema20','ema20','#ff3158']]){
     if(!$(id).checked)continue;
     const dataset=rows.filter(r=>r[key]!==null&&Number.isFinite(r[key]))
       .map(r=>({time:r.time,value:r[key]}));
     if(!dataset.length)continue;
     const line=chart.addSeries(lib.LineSeries,{color,lineWidth:2,
       priceLineVisible:false,lastValueVisible:false,title:key.toUpperCase()});
     line.setData(dataset);
   }
   chart.timeScale().fitContent();
   state.resizeObserver=new ResizeObserver(entries=>{
     if(state.chart&&entries[0])state.chart.applyOptions({
       width:Math.max(300,Math.floor(entries[0].contentRect.width)),
       height:Math.max(250,Math.floor(entries[0].contentRect.height))
     });
   });
   state.resizeObserver.observe(host);
 }catch(e){
   cleanupChart();host.innerHTML=fallbackCandles(rows);
   $('chart-timeframe').textContent='Candlesticks · Basic chart view';
 }
}
function scenarioChart(scenario){
 const bands=scenario.bands||[];
 if(!bands.length)return '<div class="empty-radar">Not enough history for scenario bands.</div>';
 const all=bands.flatMap(b=>[b.low,b.high]);all.push(scenario.anchor);
 const minimum=Math.min(...all),maximum=Math.max(...all),span=Math.max(.01,maximum-minimum);
 const w=920,height=210,left=55,right=16,top=18,bottom=33;
 const x=i=>left+(i+1)/(bands.length+1)*(w-left-right);
 const y=v=>top+(maximum-v)/span*(height-top-bottom);
 const line=(field,color)=>'<polyline fill="none" stroke="'+color+'" stroke-width="2.2" points="'+bands.map((b,i)=>x(i).toFixed(2)+','+y(b[field]).toFixed(2)).join(' ')+'"/>';
 const shade=bands.map((b,i)=>x(i).toFixed(2)+','+y(b.high).toFixed(2)).join(' ')+
             ' '+bands.slice().reverse().map((b,k)=>x(bands.length-k-1).toFixed(2)+','+y(b.low).toFixed(2)).join(' ');
 const ticks=[0,.5,1].map(t=>{
   const yy=top+t*(height-top-bottom);
   return '<line x1="'+left+'" y1="'+yy+'" x2="'+(w-right)+'" y2="'+yy+'" stroke="#242424" stroke-dasharray="3 5"/>'+
          '<text x="4" y="'+(yy+3)+'" font-size="11" fill="#a0a0a0">'+h(fmt(maximum-t*span))+'</text>';
 }).join('');
 const caption='<text x="'+left+'" y="'+(height-8)+'" fill="#a0a0a0" font-size="11">Next candle 1</text>'+
  '<text x="'+(w-right)+'" y="'+(height-8)+'" fill="#a0a0a0" font-size="11" text-anchor="end">Next candle '+scenario.horizon+'</text>';
 const dots=bands.map((b,i)=>'<circle cx="'+x(i)+'" cy="'+y(b.mid)+'" r="8" fill="transparent"><title>Candle '+(i+1)+' | Lower '+fmt(b.low)+' | Mid '+fmt(b.mid)+' | Upper '+fmt(b.high)+'</title></circle>').join('');
 return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '+w+' '+height+'" role="img" aria-label="Illustrative scenario range for future candles">'+ticks+
  '<polygon points="'+shade+'" fill="#00e676" fill-opacity=".13"/>'+
  line('low','#ff3158')+line('high','#00e676')+line('mid','#e8e8e8')+
  dots+caption+'</svg>';
}
function renderPatterns(patterns,library){
 $('pattern-total').textContent=patterns.length+' spotted';
 $('pattern-results').innerHTML=patterns.length
  ?patterns.map(p=>{
    const icon=/bullish|upward|bottom|hammer|morning|soldiers|piercing/i.test(p.tendency+' '+p.name)?'🐂':
               /bearish|downward|top|star|crows/i.test(p.tendency+' '+p.name)?'🐻':'◆';
    const tone=icon==='🐂'?' bull':icon==='🐻'?' bear':'';
    return '<div class="pattern-item'+tone+'"><span class="symbol">'+icon+'</span><div><strong>'+h(p.name)+'</strong><small>'+h(p.category)+' · '+h(p.tendency)+' · '+h(formatDateTime(p.time))+'</small><p>'+h(p.reason)+'</p></div></div>';
   }).join('')
  :'<div class="empty-radar">No supported pattern candidates spotted in the recent candles. That is a valid outcome.</div>';
 $('pattern-library-count').textContent='('+library.length+')';
 $('pattern-library').innerHTML=library.map(p=>'<div><strong>'+h(p.name)+'</strong><small>'+h(p.tendency)+'</small></div>').join('');
}
function display(data){
 state.latest=data;
 $('instrument-name').textContent=data.symbol.replace(/\.NS$/,'');
 $('last-price').textContent=fmt(data.last_price);
 $('last-change').textContent=(data.change_pct>0?'+':'')+pct(data.change_pct)+' · previous candle';
 $('last-change').className=data.change_pct>=0?'positive':'negative';
 $('last-update').textContent='Last candle: '+formatDateTime(data.latest_time)+' IST · Historical data may be delayed';
 const mood=$('terminal-direction');mood.textContent=(data.trend==='Bullish'?'🐂 BULLISH':data.trend==='Bearish'?'🐻 BEARISH':'↔ SIDEWAYS');
 mood.className='trend-tag '+data.trend.toLowerCase();
 $('chart-candles').textContent=data.bars.length.toLocaleString('en-IN')+' historical candles · '+data.interval;
 $('chart-timeframe').textContent='NSE · '+data.interval+' interval · '+RANGE_LABELS[data.lookback];
 $('scenario-window').textContent='Next '+data.scenario.horizon+' candles';
 $('scenario-metrics').innerHTML=
  '<div class="scenario-card bear"><span>🐻 BEAR CASE · LOWER RANGE</span><strong>'+fmt(data.scenario.downside)+'</strong></div>'+
  '<div class="scenario-card"><span>↔ MIDDLE PATH</span><strong>'+fmt(data.scenario.middle)+'</strong></div>'+
  '<div class="scenario-card bull"><span>🐂 BULL CASE · UPPER RANGE</span><strong>'+fmt(data.scenario.upside)+'</strong></div>';
 $('forecast-chart').innerHTML=scenarioChart(data.scenario);
 $('bull-price').textContent=fmt(data.scenario.upside);
 $('bear-price').textContent=fmt(data.scenario.downside);
 $('desk-trend').textContent=data.trend==='Bullish'?'🐂 Bullish trend':data.trend==='Bearish'?'🐻 Bearish trend':'↔ Sideways trend';
 $('desk-pattern').textContent=data.patterns.length?data.patterns.slice(0,2).map(x=>x.name).join(' · '):'No clear recent candle formation in the supported library.';
 $('model-share').textContent=data.scenario.modeled_above_reference_pct.toFixed(1)+'%';
 renderPatterns(data.patterns,data.pattern_library);
 drawCandles(data.bars);
}
function showError(message){
 cleanupChart();state.latest=null;
 $('candle-chart').innerHTML='<div class="chart-placeholder">⚠ '+h(message)+'</div>';
 $('last-price').textContent='—';$('last-change').textContent='Data not available';
 $('last-update').textContent='Choose a different interval or retry. Nothing has been simulated as a quote.';
 $('scenario-metrics').innerHTML='<div class="empty-radar">Historical price data is required before scenarios can be calculated.</div>';
 $('forecast-chart').innerHTML='';
 $('pattern-results').innerHTML='<div class="empty-radar">Pattern analysis will appear when valid candles are available.</div>';
 $('pattern-total').textContent='0 spotted';
 $('model-share').textContent='—';$('bear-price').textContent='—';$('bull-price').textContent='—';
 $('desk-trend').textContent='No data';
}
async function loadTerminal(){
 const seq=++state.seq;
 const symbol=state.symbol;
 $('reload-terminal').disabled=true;
 $('last-update').textContent='Checking '+symbol+' historical prices…';
 $('candle-chart').innerHTML='<div class="chart-placeholder">Loading price candles and chart patterns…</div>';
 // Preserve a user-selected range only when valid for the candle interval.
 if(!RANGES[state.interval].includes(state.lookback))resetHistory();
 try{
  const q=new URLSearchParams({interval:state.interval,lookback:state.lookback,horizon:String(state.horizon)});
  const data=await api('/api/terminal/'+encodeURIComponent(symbol)+'?'+q);
  if(seq!==state.seq)return;
  display(data);
 }catch(e){if(seq===state.seq)showError(e.message);}
 finally{if(seq===state.seq)$('reload-terminal').disabled=false;}
}
resetHistory();
loadWatch();
loadTerminal();
