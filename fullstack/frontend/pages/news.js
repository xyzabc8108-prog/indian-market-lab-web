import {api,h,loading,error,formatDateTime} from '../api.js';

export function render(){
  return `<div class="page-head"><span class="eyebrow">VERIFIED SOURCE LINKS</span><h1>News Intelligence</h1>
  <p>Read announcements directly from their source. Automated public headline republication is paused pending content-rights review.</p></div>
  <section class="panel"><div class="panel-title"><h2>Official financial news and announcements</h2><span class="data-label">SOURCE LINKS ONLY</span></div>
  <div class="notice">Third-party content belongs to its publishers. Indian Market Lab currently provides source links rather than copying or republishing Google News RSS headlines. News is not a forecast.</div>
  <div id="news-out">${loading('Loading official source directory…')}</div></section>`;
}

export async function mount(root){
  const out=root.querySelector('#news-out');
  try {
    const d=await api('/api/news');
    const sources=Object.entries(d.official_sources||{});
    const rows=sources.map(([name,url])=>`<article class="news-card"><h3><a href="${h(url)}" target="_blank" rel="noopener noreferrer">${h(name)}</a></h3><p>Read original announcements on the publisher's website.</p></article>`).join('');
    const note=d.feed_paused===true?'<p class="muted">External RSS headline syndication is disabled while publisher and provider permissions are reviewed.</p>':'';
    const feeds=d.feed_paused===false&&Array.isArray(d.items)?d.items.map(item=>`<article class="news-card"><div class="news-meta">${h(item.source)} · ${h(formatDateTime(item.published))}</div><h3><a href="${h(item.url)}" target="_blank" rel="noopener noreferrer">${h(item.title)}</a></h3></article>`).join(''):'';
    out.innerHTML=note+'<div class="news-list">'+rows+feeds+'</div>';
  }catch(e){
    out.innerHTML=error(e.message)+'<p class="muted">You can visit the SEBI, NSE, and RBI official websites directly.</p>';
  }
}
