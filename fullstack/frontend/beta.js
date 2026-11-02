// Public beta UI: no analytics beacons, tokens or visitor identifiers.
const candles = document.getElementById('candles');
const sample = [150,145,159,154,137,131,139,135,119,123,112,104,110,118,101,98,107,91,96,89,78,84,76,72,83,68,61,72,59,66,52,56];
if (candles) {
  candles.innerHTML = sample.map((y,i)=>{
    const down = i%7===2 || i%7===5;
    const color = down ? '#ff596c' : '#00dc87';
    const x = 10 + i*17.5;
    const body = 10 + (i*13%11);
    const top = down ? y : y+body-5;
    return '<line x1="'+(x+4)+'" y1="'+(y-14)+'" x2="'+(x+4)+'" y2="'+(y+body+18)+'" stroke="'+color+'" stroke-width="1.8"/>'+
      '<rect x="'+x+'" y="'+top+'" width="8" height="'+body+'" fill="'+color+'" rx="1"/>';
  }).join('');
}

const $ = id => document.getElementById(id);
const wait = $('waitlist-form'), feed = $('feedback-form');
let waitOpen=false, feedbackOpen=false;
function notice(el, message, type='') {
  el.className='form-message'+(type?' '+type:'');
  el.textContent=message;
}
function setEnabled(open, submitId, buttonLabel, badgeId, labelId) {
  const btn=$(submitId);
  btn.disabled=!open;
  btn.textContent=open?buttonLabel:(labelId==='wait'?'Registration opening soon':'Feedback opening soon');
  if (badgeId) $(badgeId).textContent=open?'Open now':'Opening soon';
}
async function refreshStatus() {
  try {
    const r=await fetch('/api/beta/status',{cache:'no-store',headers:{'Accept':'application/json'}});
    if(!r.ok)throw new Error('Status not available');
    const s=await r.json();
    waitOpen=s.waitlist_open===true;
    feedbackOpen=s.feedback_open===true;
  }catch{
    waitOpen=false;feedbackOpen=false;
  }
  setEnabled(waitOpen,'wait-submit','Join the early-access list','waitlist-badge','wait');
  setEnabled(feedbackOpen,'feedback-submit','Send feedback',null,'feedback');
  notice($('wait-result'),waitOpen?'Please use an email address where you want beta invitations.':'Early-access registration is not available yet. You can still explore the free beta.');
  notice($('feedback-result'),feedbackOpen?'We read feedback to help choose what to improve next.':'The feedback form is opening soon. You can still explore the app.');
}
refreshStatus();

async function submit(path, data, button, resultEl, successMessage) {
  button.disabled=true;
  notice(resultEl,'Sending...');
  try {
    const r=await fetch(path,{
      method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},
      body:JSON.stringify(data)
    });
    let response={};
    try{response=await r.json();}catch{}
    if(!r.ok)throw new Error(
      r.status===429?'Too many attempts. Please try again later.':
      r.status===503?'Submissions are unavailable right now. Please try again later.':
      r.status===422?'Please check the fields and try again.':
      'Could not send your response. Please try again later.'
    );
    notice(resultEl,successMessage,'good');
    return true;
  }catch(e){
    notice(resultEl,e.message||'Could not send. Please try again.','bad');
    return false;
  }finally{
    button.disabled=false;
  }
}
wait?.addEventListener('submit',async event=>{
  event.preventDefault();
  if(!waitOpen){notice($('wait-result'),'Registration has not opened yet.','bad');return;}
  const btn=$('wait-submit');
  const worked=await submit('/api/beta/interest',{
    email:$('wait-email').value,feature:$('wait-feature').value,
    consent:$('wait-consent').checked,website:$('wait-website').value
  },btn,$('wait-result'),
  'Your interest was received. You will only hear from us about beta updates you requested.');
  if(worked){wait.reset();}
});
feed?.addEventListener('submit',async event=>{
  event.preventDefault();
  if(!feedbackOpen){notice($('feedback-result'),'Feedback submissions have not opened yet.','bad');return;}
  const btn=$('feedback-submit');
  const worked=await submit('/api/beta/feedback',{
    feature:$('feedback-feature').value,
    rating:Number($('feedback-rating').value),
    message:$('feedback-message').value.trim(),
    website:$('feedback-website').value
  },btn,$('feedback-result'),'Thanks! Your feedback was received.');
  if(worked){$('feedback-message').value='';}
});
