import {ChatMemory} from './memory.js';
const select = id => document.getElementById(id);
const memory = new ChatMemory();
let busy = false;
function setBusy(value) { busy=value; select('question').disabled=value; select('messages').setAttribute('aria-busy',String(value)); counter(); }
function counter() { select('send').disabled=busy||!memory.opened||!select('question').value.trim(); select('count').textContent=`${select('question').value.length.toLocaleString()} / 2,000`; }
function scroll() { const area=select('conversation'); area.scrollTop=area.scrollHeight; }
function addMessage(role, text, sources=[]) {
  const article=document.createElement('article'); article.className=`message ${role}`;
  const label=document.createElement('div'); label.className='role'; label.textContent=role==='user'?'YOU':'AGENTGUARD SUPPORT';
  const body=document.createElement('p'); body.textContent=text; article.append(label,body);
  for (const source of sources) {
    let url; try {url=new URL(source.url);} catch {continue;}
    if(url.origin!=='https://ag-dev.actaclad.com'||!url.pathname.startsWith('/docs/')) continue;
    const card=document.createElement('div'); card.className='source';
    const link=document.createElement('a'); link.href=url.href; link.target='_blank'; link.rel='noopener noreferrer'; link.textContent=`[${source.id}] ${source.title}`;
    const sdk=document.createElement('span'); sdk.className='sdk'; sdk.textContent=source.language==='py'?'Python':source.language==='node'?'Node.js':'General';
    const details=document.createElement('details'); details.open=true;
    const summary=document.createElement('summary'); summary.textContent='Original documentation section';
    const excerpt=document.createElement('pre'); excerpt.className='excerpt'; excerpt.textContent=source.excerpt;
    details.append(summary,excerpt); card.append(link,sdk,details); article.append(card);
  }
  select('messages').append(article); scroll(); return article;
}
async function submit(event) {
  event?.preventDefault(); const question=select('question').value.trim();
  if(!question||busy||!memory.opened) return;
  const request=memory.begin(); select('error').hidden=true; select('welcome').hidden=true; setBusy(true);
  const user=addMessage('user',question);
  const pending=document.createElement('p'); pending.className='pending'; pending.textContent='Searching documentation...'; select('messages').append(pending); scroll();
  try {
    const reply=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,history:request.history}),signal:AbortSignal.any([request.controller.signal,AbortSignal.timeout(15000)])});
    const result=await reply.json();
    if(!memory.current(request)) return;
    if(!reply.ok) throw new Error(result.error||'Search is unavailable.');
    pending.remove(); addMessage('assistant',result.answer,result.sources); memory.remember(request,question,result.answer); select('question').value=''; counter();
  } catch(error) {
    if(!memory.current(request)) return;
    user.remove(); pending.remove(); select('error').textContent=error.name==='TimeoutError'?'Search took too long. Please retry.':error.message; select('error').hidden=false;
    if(!select('messages').children.length) select('welcome').hidden=false;
  } finally { if(memory.current(request)){setBusy(false); select('question').focus();} }
}
function reset(open) {
  memory.reset(open); setBusy(false); select('messages').replaceChildren(); select('question').value=''; counter(); select('error').hidden=true; select('error').textContent=''; select('welcome').hidden=false;
  select('panel').hidden=!open; select('closed').hidden=open; select('new').hidden=!open; select('close').hidden=!open;
  if(open) select('question').focus();
}
select('form').addEventListener('submit',submit);
select('question').addEventListener('input',counter);
select('question').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();submit();}});
select('suggestions').addEventListener('click',event=>{const button=event.target.closest('[data-query]'); if(button&&!busy){select('question').value=button.dataset.query;counter();submit();}});
select('new').addEventListener('click',()=>reset(true)); select('close').addEventListener('click',()=>reset(false)); select('open').addEventListener('click',()=>reset(true));
window.addEventListener('pagehide',()=>reset(false));
window.addEventListener('pageshow',event=>{if(event.persisted)reset(false);});
counter();
try {const reply=await fetch('/api/status');if(!reply.ok)throw new Error();const status=await reply.json();select('notice').textContent=`Documentation ready - ${status.pages} guides - ${status.sections} searchable sections.`;}catch{select('notice').textContent='The local server is unavailable. Start the project and reload.';}
