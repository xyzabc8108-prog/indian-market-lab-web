import {h} from './api.js';
const routes=[
 ['home','Home','house','./pages/home.js'],
 ['stocks','Stock Research','chart','./pages/stocks.js'],
 ['scanner','Market Scanner','scan','./pages/scanner.js'],
 ['indices','Indices','grid','./pages/indices.js'],
 ['derivatives','F&O Planner','layers','./pages/derivatives.js'],
 ['news','News Intelligence','rss','./pages/news.js'],
 ['paper','Paper Portfolio','wallet','./pages/paper.js'],
 ['about','Help & Information','shield','./pages/about.js']
];
const icons={house:'⌂',chart:'↗',scan:'◎',grid:'▦',layers:'≋',rss:'◷',wallet:'▤',shield:'◇'};
const app=document.getElementById('app');
app.innerHTML=`<div class="shell"><aside class="sidebar"><div class="brand"><div class="logo">⌁</div><div><strong>INDIAN MARKET LAB</strong><small>RESEARCH INTELLIGENCE</small></div></div><div class="nav-caption" >YOUR TOOLS</div><nav id="side-nav">${routes.map(([id,title,ico])=>`<a href="#/${id}" data-route="${id}"><span class="nav-icon">${icons[ico]}</span>${h(title)}</a>`).join('')}</nav><div class="sidebar-foot"><span class="pill-dot"></span> Your paper budget<div>₹50,000 · Max planned loss ₹500 per idea</div><small>Practice only — no real trades</small></div></aside><div class="workspace"><header class="topbar"><div class="breadcrumb">INDIAN MARKET LAB <span>/</span> <b id="crumb">HOME</b></div><div class="top-actions"><span class="top-label">Stock research · Paper trading</span></div></header><main id="page" tabindex="-1"></main><footer class="footer">Indian Market Lab · Prices may be delayed · For learning and paper trading only</footer></div></div>`;
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

