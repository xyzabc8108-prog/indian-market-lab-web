// Shared beta feedback control. Real submissions only when the backend confirms storage.
(() => {
 const host=document.getElementById('terminal-interactive')||document.body;
 const root=document.createElement('div');root.className='iml-feedback-root';
 root.innerHTML=[
 "<button class='iml-feedback-fab' id='iml-feedback-launch' type='button' aria-haspopup='dialog' aria-controls='iml-feedback-dialog' aria-expanded='false'>✎ Feedback</button>",
 "<div id='iml-feedback-overlay' class='iml-feedback-overlay' hidden><div id='iml-feedback-dialog' class='iml-feedback-dialog' role='dialog' aria-modal='true' aria-labelledby='iml-feedback-heading' tabindex='-1'>",
 "<div class='iml-feedback-head'><div><small>PUBLIC BETA</small><h2 id='iml-feedback-heading'>Help improve Indian Market Lab</h2></div><button id='iml-feedback-close' type='button' class='iml-feedback-close' aria-label='Close feedback'>×</button></div>",
 "<p class='iml-feedback-intro'>Share an improvement idea. Do not include passwords, account numbers or financial credentials.</p>",
 "<div id='iml-feedback-status' class='iml-feedback-status' role='status' aria-live='polite'>Checking whether feedback is open…</div>",
 "<form id='iml-feedback-form'>",
 "<label for='iml-feedback-feature'>Tool used</label><select id='iml-feedback-feature' required><option value='charts'>Trader Terminal / Charts</option><option value='scanner'>Market Scanner</option><option value='backtesting'>Historical Strategy Testing</option><option value='paper-trading'>Paper Portfolio</option><option value='news'>Market News</option><option value='other'>Other / General</option></select>",
 "<label for='iml-feedback-rating'>Rating</label><select id='iml-feedback-rating' required><option value='5'>5 — Excellent</option><option value='4' selected>4 — Good</option><option value='3'>3 — Okay</option><option value='2'>2 — Needs work</option><option value='1'>1 — Difficult</option></select>",
 "<label for='iml-feedback-message'>Your suggestion</label><textarea id='iml-feedback-message' minlength='12' maxlength='1200' rows='4' placeholder='What worked, what was confusing, or what should improve?' required></textarea>",
 "<label class='iml-feedback-hp' aria-hidden='true' for='iml-feedback-website'>Website<input id='iml-feedback-website' type='text' autocomplete='off' tabindex='-1'></label>",
 "<button class='iml-feedback-send' id='iml-feedback-send' type='submit' disabled>Checking availability…</button></form>",
 "<p class='iml-feedback-contact'>Support or private concerns: <a href='mailto:rohanchhaya108@gmail.com'>rohanchhaya108@gmail.com</a> · <a href='/privacy'>Privacy</a></p>",
 "</div></div>"
 ].join('');
 host.append(root);
 const get=id=>root.querySelector('#'+id);
 const launch=get('iml-feedback-launch'),overlay=get('iml-feedback-overlay'),close=get('iml-feedback-close');
 const status=get('iml-feedback-status'),form=get('iml-feedback-form'),send=get('iml-feedback-send');
 let canSend=false,busy=false,priorFocus=null,sequence=0;
 function message(text,kind=''){status.textContent=text;status.className='iml-feedback-status'+(kind?' '+kind:'');}
 async function checkAvailability(){
  const n=++sequence;canSend=false;send.disabled=true;send.textContent='Checking availability…';
  message('Checking secure feedback availability…');
  try {
   const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),8000);
   let response;
   try{response=await fetch('/api/beta/status',{cache:'no-store',signal:controller.signal,headers:{Accept:'application/json'}});}
   finally{clearTimeout(timer);}
   if(!response.ok)throw new Error('Unavailable');
   const data=await response.json();
   if(n!==sequence||overlay.hidden)return;
   canSend=data.feedback_open===true;
  }catch{if(n!==sequence||overlay.hidden)return;canSend=false;}
  send.disabled=!canSend;send.textContent=canSend?'Send feedback':'In-site feedback not open';
  message(canSend?'Feedback is open. Your message is saved only after the server confirms receipt.':
   'In-site feedback is not accepting submissions yet. You can contact support using the email link below.',canSend?'good':'');
 }
 function open(){priorFocus=document.activeElement;overlay.hidden=false;launch.setAttribute('aria-expanded','true');close.focus();checkAvailability();}
 function dismiss(){++sequence;overlay.hidden=true;launch.setAttribute('aria-expanded','false');if(priorFocus?.focus)priorFocus.focus();}
 launch.addEventListener('click',open);close.addEventListener('click',dismiss);
 overlay.addEventListener('click',e=>{if(e.target===overlay)dismiss();});
 overlay.addEventListener('keydown',e=>{
  if(e.key==='Escape'){e.preventDefault();dismiss();}
  if(e.key!=='Tab')return;
  const items=[...overlay.querySelectorAll('button:not([disabled]),select:not([disabled]),textarea:not([disabled]),a[href]')].filter(el=>el.offsetParent!==null);
  if(!items.length)return;
  if(e.shiftKey&&document.activeElement===items[0]){e.preventDefault();items[items.length-1].focus();}
  else if(!e.shiftKey&&document.activeElement===items[items.length-1]){e.preventDefault();items[0].focus();}
 });
 form.addEventListener('submit',async e=>{
  e.preventDefault();if(!canSend||busy)return;
  const text=get('iml-feedback-message').value.trim();
  if(text.length<12){message('Please enter at least 12 characters.','bad');return;}
  busy=true;send.disabled=true;send.textContent='Sending…';
  try{
   const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
   let r;try{r=await fetch('/api/beta/feedback',{method:'POST',signal:controller.signal,
     headers:{'Content-Type':'application/json','Accept':'application/json'},
     body:JSON.stringify({feature:get('iml-feedback-feature').value,rating:Number(get('iml-feedback-rating').value),
       message:text,website:get('iml-feedback-website').value})});}finally{clearTimeout(timer);}
   if(!r.ok)throw new Error(r.status===429?'Too many submissions. Try later.':'Feedback was not saved. Please try again.');
   form.reset();message('Thank you — your feedback was received by the server.','good');
  }catch(err){message(err?.message||'Feedback could not be sent. Please try again.','bad');}
  finally{busy=false;send.disabled=!canSend;send.textContent=canSend?'Send feedback':'In-site feedback not open';}
 });
})();