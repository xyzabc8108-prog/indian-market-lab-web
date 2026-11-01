export const h = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
export const money = value => Number.isFinite(Number(value)) ? '₹'+Number(value).toLocaleString('en-IN',{maximumFractionDigits:2,minimumFractionDigits:2}) : '—';
export const pct = value => value===null||value===undefined||!Number.isFinite(Number(value))?'—':Number(value).toFixed(2)+'%';
export const num = value => Number.isFinite(Number(value))?Number(value).toLocaleString('en-IN',{maximumFractionDigits:2}):'—';
export function loading(message='Loading research…'){return `<div class="loader"><span class="spin"></span>${h(message)}</div>`;}
export function error(message){return `<div class="notice bad"><strong>Data unavailable</strong><p>${h(message)}</p></div>`;}
export function note(message){return `<div class="notice">${h(message)}</div>`;}
export async function api(path, options={}){
  const response=await fetch(path,{...options,headers:{...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),...(options.headers||{})}});
  let data;try{data=await response.json();}catch{throw new Error('Server returned an unreadable response');}
  if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:`Request failed (${response.status})`);
  return data;
}
export function metric(label,value,meta=''){return `<div class="metric"><span>${h(label)}</span><strong>${h(value)}</strong><small>${h(meta)}</small></div>`;}
export function spark(series){
 const values=(series||[]).map(x=>Number(x.close)).filter(x=>Number.isFinite(x));
 if(values.length<2)return '<div class="notice">No valid chart bars.</div>';
 const min=Math.min(...values),max=Math.max(...values),span=Math.max(.00001,max-min);
 const points=values.map((y,i)=>`${(i/(values.length-1)*960).toFixed(1)},${(220-(y-min)/span*188).toFixed(1)}`).join(' ');
 const up=values.at(-1)>=values[0],color=up?'#3bdfb6':'#f59b85';
 return `<svg class="chart-svg" viewBox="0 0 960 245" role="img" aria-label="Historical closing prices"><line x1="0" y1="223" x2="960" y2="223" stroke="#315065"/><polyline fill="none" stroke="${color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" points="${points}"/></svg><div class="chart-foot"><span>Earliest: ${money(values[0])}</span><span>Latest: ${money(values.at(-1))}</span></div>`;
}
export const infoSource='External Yahoo Finance chart endpoints are unofficial and may be delayed or blocked. Nothing here is a guaranteed real-time quote or a trade recommendation.';
