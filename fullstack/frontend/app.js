import {h,api} from './api.js';
const routes=[
 ['home','Home','house','./pages/home.js'],
 ['stocks','Stock Research','chart','./pages/stocks.js?v=safety21-21'],
 ['scanner','Market Scanner','scan','./pages/scanner.js?v=scanner21-21-9'],
 ['indices','Indices','grid','./pages/indices.js?v=safety21-21'],
 ['derivatives','F&O Planner','layers','./pages/derivatives.js'],
 ['news','News Intelligence','rss','./pages/news.js'],
 ['paper','Paper Portfolio','wallet','./pages/paper.js'],
 ['about','Help & Information','shield','./pages/about.js']
];
const icons={house:'⌂',chart:'↗',scan:'◎',grid:'▦',layers:'≋',rss:'◷',wallet:'▤',shield:'◇'};
const app=document.getElementById('app');
app.innerHTML=`<div class="shell"><aside class="sidebar"><div class="brand"><div class="logo iml-small-pair" aria-hidden="true"><img class="animal-icon bull-mark" src="/icons/bull.svg?v=iml-geom-20261103" alt="" aria-hidden="true" decoding="async"><img class="animal-icon bear-mark" src="/icons/bear.svg?v=iml-geom-20261103" alt="" aria-hidden="true" decoding="async"></div><div><strong>INDIAN MARKET LAB</strong><small>RESEARCH INTELLIGENCE</small></div></div><div class="nav-caption" >YOUR TOOLS</div><nav id="side-nav">${routes.map(([id,title,ico])=>`<a href="#/${id}" data-route="${id}"><span class="nav-icon">${icons[ico]}</span>${h(title)}</a>`).join('')}</nav><div class="sidebar-foot"><span class="pill-dot"></span> Your paper budget<div>₹50,000 · Max planned loss ₹500 per idea</div><small>Practice only — no real trades</small></div></aside><div class="workspace"><header class="topbar"><div class="breadcrumb">INDIAN MARKET LAB <span>/</span> <b id="crumb">HOME</b></div><div class="top-actions"><a class="beta-entry" href="/beta">Explore Beta <span aria-hidden="true">↗</span></a><a class="trader-toggle" href="/terminal" aria-label="Switch to Trader Mode"><span class="trader-mode-icon iml-small-pair" aria-hidden="true"><img class="animal-icon bull-mark" src="/icons/bull.svg?v=iml-geom-20261103" alt="" aria-hidden="true" decoding="async"><img class="animal-icon bear-mark" src="/icons/bear.svg?v=iml-geom-20261103" alt="" aria-hidden="true" decoding="async"></span><span>Trader Mode</span><span class="toggle-track"><span></span></span></a></div></header><div class="global-disclosure" role="note"><strong>Important disclosure:</strong> Historical research and hypothetical price levels are not personalized investment advice. Prices may be delayed and losses can exceed estimates. No real trades. <a href="/terms">Terms &amp; Risk ↗</a></div><div id="market-data-banner" class="global-data-safety" role="status" hidden><strong>Market Data Safety Mode</strong> — Public stock-price charts and ticker-specific scenarios are temporarily paused during data-rights review. You can still <a href="#/scanner">try a fictional scanner demo</a> and use paper-risk tools. No real orders.</div><main id="page" tabindex="-1"></main><footer class="footer">Indian Market Lab · Research and paper trading only · <a href="/terms">Disclaimer &amp; Terms</a> · <a href="/privacy">Privacy</a> · <a href="/third-party-licenses">Licences &amp; Attribution</a></footer></div></div>`;
const page=document.getElementById('page');
let seq=0;
async function navigate(){
 const requested=(location.hash.split('?')[0].replace('#/','')||'home');
 const route=routes.find(x=>x[0]===requested)||routes[0];
 document.querySelectorAll('[data-route]').forEach(a=>a.classList.toggle('active',a.dataset.route===route[0]));
 document.getElementById('crumb').textContent=route[1].toUpperCase();
 const current=++seq;page.innerHTML='<div class="loader"><span class="spin"></span>Opening section…</div>';
 try{const mod=await import(route[3]);if(current!==seq)return;page.innerHTML=await mod.render();if(current!==seq)return;await mod.mount?.(page);}catch(e){if(current===seq)page.innerHTML=`<div class="page-head"><h1>Section unavailable</h1></div><div class="notice bad">${h(e.message)}</div>`;}
 window.scrollTo({top:0,behavior:'instant'});
}
window.addEventListener('hashchange',navigate);
navigate();


async function refreshMarketDataSafetyNotice(){
  let open=false;
  try{
    const status=await api('/api/market-data/status',{timeoutMs:12000});
    open=status.public_price_data_available===true &&
         status.market_data_safety_mode===false;
  }catch{open=false;}
  const banner=document.getElementById('market-data-banner');
  if(banner)banner.hidden=open;
}
refreshMarketDataSafetyNotice();
