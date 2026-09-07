const $ = id => document.getElementById(id);
const esc = text => String(text ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let activeCase = null, sources = [], timer = null, noticeTimer;
async function api(path, options={}) {
  const r = await fetch(path, {headers:{'Content-Type':'application/json'}, ...options});
  const data = await r.json();
  if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check the brief fields and source limits.');
  return data;
}
function notify(message) { $('notice').textContent=message; $('notice').hidden=false; clearTimeout(noticeTimer); noticeTimer=setTimeout(()=>$('notice').hidden=true,7500); }
async function refreshStatus() {
  try { const d=await api('/api/status'); $('model-status').textContent=d.available ? `${d.model} · local model ready` : 'Local model offline'; $('model-status').classList.toggle('ready', d.available); return d; }
  catch { $('model-status').textContent='App unavailable'; }
}
async function listCases() {
  const list=await api('/api/cases');
  $('case-list').innerHTML=list.length ? list.map(c=>`<button class="case-button ${c.id===activeCase?.id?'active':''}" data-case="${esc(c.id)}">${esc(c.title)}<small>${c.questions} questions · ${esc(c.status.replaceAll('_',' '))}</small></button>`).join('') : '<p class="empty">Your research briefs will appear here.</p>';
  document.querySelectorAll('[data-case]').forEach(b=>b.onclick=()=>openCase(b.dataset.case));
}
function syncSources() {
  document.querySelectorAll('.source-input').forEach((node,i)=>{ sources[i]={title:node.querySelector('[data-title]').value,url:node.querySelector('[data-url]').value,text:node.querySelector('[data-text]').value}; });
}
function renderSourceInputs() {
  $('sources').innerHTML=sources.map((s,i)=>`<details class="source-input" open><summary><span>S${i+1}</span><strong>${esc(s.title||'New source')}</strong><button type="button" class="remove-source" data-remove="${i}" aria-label="Remove source ${i+1}">Remove</button></summary><div class="source-fields"><div><label>Source title<input data-title value="${esc(s.title)}" maxlength="200" required></label></div><div><label>Publication URL<input data-url value="${esc(s.url)}" type="url" required></label></div></div><label>Source text<textarea data-text rows="5" required minlength="20" maxlength="30000">${esc(s.text)}</textarea></label><p class="micro">Blank lines separate snapshot paragraphs. Keep enough original context for a fair reading.</p></details>`).join('');
  document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=e=>{ e.preventDefault();syncSources();sources.splice(+b.dataset.remove,1);renderSourceInputs(); });
}
function newBrief() { clearInterval(timer);activeCase=null; $('intake').hidden=false;$('workspace').hidden=true;listCases(); }
$('new-case').onclick=newBrief;
$('add-source').onclick=()=>{syncSources();if(sources.length>=6){notify('A brief supports up to six focused sources.');return;}sources.push({title:'',url:'https://',text:''});renderSourceInputs();};
$('load-example').onclick=async()=>{try{const d=await api('/api/sample');$('brief-title').value=d.title;$('questions').value=d.questions.join('\n');sources=d.sources;renderSourceInputs();notify('Loaded excerpts captured from official Strands documentation, plus three real adoption questions.');}catch(e){notify(e.message);}};
$('fetch-source').onclick=async()=>{syncSources();if(sources.length>=6){notify('A brief supports up to six sources.');return;}const b=$('fetch-source');b.disabled=true;b.textContent='Capturing…';try{const d=await api('/api/fetch',{method:'POST',body:JSON.stringify({url:$('fetch-url').value})});sources.push({title:d.title,url:d.url,text:d.text});renderSourceInputs();$('fetch-url').value='';notify(d.truncated?'Captured first 30,000 characters by paragraph. Narrow the excerpt to relevant context.':d.intake_note);}catch(e){notify(e.message);}finally{b.disabled=false;b.textContent='Capture public docs';}};
$('brief-form').onsubmit=async e=>{e.preventDefault();syncSources();const b=$('create-button');b.disabled=true;try{const d=await api('/api/cases',{method:'POST',body:JSON.stringify({title:$('brief-title').value,questions:$('questions').value.split('\n').map(q=>q.trim()).filter(Boolean),sources})});await openCase(d.id);await startRun(d.id);}catch(e){notify(e.message);}finally{b.disabled=false;}};
async function startRun(id) {try{await api(`/api/cases/${id}/run`,{method:'POST'});await openCase(id);}catch(e){notify(e.message);await openCase(id);}}
async function openCase(id) {
  clearInterval(timer);activeCase=await api(`/api/cases/${id}`);$('intake').hidden=true;$('workspace').hidden=false;renderCase();listCases();
  if(['running','queued'].includes(activeCase.status)) timer=setInterval(async()=>{try{activeCase=await api(`/api/cases/${id}`);renderCase();if(!['running','queued'].includes(activeCase.status)){clearInterval(timer);listCases();refreshStatus();}}catch(e){clearInterval(timer);notify(e.message);}},1800);
}
function renderCase() {
  const c=activeCase, busy=['queued','running'].includes(c.status), completed=c.status.startsWith('completed');
  $('case-title').textContent=c.title;$('case-meta').textContent=`${c.id} · ${c.sources.length} sealed sources · ${new Date(c.created_at).toLocaleString()}`;
  $('export').disabled=busy;
  if(busy)$('run-banner').innerHTML='<div class="banner pulse">Your local Strands agent is checking the brief. Findings will appear as tools finish.</div>';
  else if(c.status==='ready'){$('run-banner').innerHTML='<div class="banner">Sources captured. The agent has not run yet. <button id="start-now" class="quiet">Run local agent →</button></div>';$('start-now').onclick=()=>startRun(c.id);}
  else $('run-banner').innerHTML=`<div class="banner ${c.error?'warn':''}">${completed ? 'Run complete. Review the interpretation before sharing.' : esc(c.status)} ${c.error?esc(c.error):''}</div>`;
  const latest=Object.fromEntries(c.reviews.map(r=>[r.question_id,r]));
  const verified=c.findings.filter(f=>f.citation.status==='verified').length, gaps=c.findings.filter(f=>f.assessment==='unresolved').length;
  $('metrics').innerHTML=[[c.questions.length,'Questions in scope'],[verified,'Source anchors verified'],[gaps,'Unresolved findings'],[Object.values(latest).filter(r=>r.decision!=='needs_review'&&r.reviewer_type).length,'Attributed decisions recorded']].map(([n,l])=>`<div class="metric"><strong>${n}</strong><span>${l}</span></div>`).join('');
  $('findings').innerHTML=c.questions.map(q=>{
    const f=c.findings.find(x=>x.question_id===q.id), r=latest[q.id];
    if(!f)return `<article class="finding"><div class="finding-head"><span class="question-id">${q.id}</span><span class="badge">${busy?'Pending agent':'Not analyzed'}</span></div><h3>${esc(q.text)}</h3></article>`;
    const cite=f.citation;
    return `<article class="finding"><div class="finding-head"><span class="question-id">${q.id}</span><span class="badge ${esc(f.assessment)}">AI: ${esc(f.assessment)}</span><span class="badge">${cite.status==='verified'?'Anchor verified':'No verified anchor'}</span></div><h3>${esc(q.text)}</h3><p class="explanation">${esc(f.explanation)}</p>${cite.status==='verified'?`<div class="quote"><p>“${esc(cite.quote)}”</p><small>${esc(cite.source_id)} · snapshot paragraph ${cite.paragraph} · exact text match</small><button class="citation-open" data-source="${esc(cite.source_id)}" data-paragraph="${cite.paragraph}">Inspect the source context ↗</button></div>`:`<p class="micro">${esc(cite.reason)}</p>`}${f.next_step?`<p class="gap"><b>Next evidence:</b> ${esc(f.next_step)}</p>`:''}${completed?`<details class="review-form"><summary>${r?'Update':'Add'} your review</summary><p class="micro">Your decision is stored separately. The original agent finding stays unchanged.</p><div class="source-fields"><label>Reviewer type<select id="reviewer-type-${q.id}" required><option value="">Choose explicitly…</option><option value="human">Human</option><option value="automated">Automated</option></select></label><label>Reviewer name<input id="reviewer-name-${q.id}" maxlength="100" required placeholder="e.g. Jane Smith or Codex"></label></div><textarea id="note-${q.id}" rows="2" minlength="3" maxlength="2000" aria-label="Review note for ${q.id}" placeholder="Explain what you checked, or what remains unresolved."></textarea><div class="review-controls"><select id="decision-${q.id}" aria-label="Decision for ${q.id}"><option value="needs_review">Still needs review</option value="accept">Accept interpretation</option><option value="inference">Keep as inference</option><option value="reject">Reject interpretation</option></select><button class="secondary" data-review="${q.id}">Save review</button></div></details>`:''}${r?`<p class="review-record">${esc(r.reviewer_type||'unspecified')} review · ${esc(r.reviewer_name||'name not recorded')}: ${esc(r.decision.replaceAll('_',' '))} — ${esc(r.note)}</p>`:''}</article>`;
  }).join('');
  $('source-register').innerHTML=c.sources.map(s=>`<div class="source-item"><strong>${esc(s.id)} · ${esc(s.title)}</strong><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(new URL(s.url).hostname)} ↗</a><small>SHA-256 ${esc(s.sha256.slice(0,20))}…<br>${s.paragraphs.length} snapshot paragraphs</small></div>`).join('');
  const events=c.events.filter(e=>['question_started','tool_search','tool_record','model_json_validated','question_error'].includes(e.kind));
  $('activity').innerHTML=events.length?events.map(e=>`<div class="event"><strong>${esc(e.question_id)} · ${({'question_started':'Question opened','tool_search':'Searched source snapshots','tool_record':'Recorded finding via tool','model_json_validated':'Validated actual model JSON','question_error':'Execution limit'})[e.kind]}</strong><span>${e.kind==='tool_search'?`${e.detail.matches.length} passages returned`:['tool_record','model_json_validated'].includes(e.kind)?`Citation: ${esc(e.detail.finding.citation.status)}`:esc(new Date(e.at).toLocaleTimeString())}</span></div>`).join(''):'<p class="micro">No model calls have been made.</p>';
  $('source-paragraphs').innerHTML=c.sources.map(s=>`<h3 class="source-heading">${esc(s.id)} · ${esc(s.title)}</h3><p class="micro">${esc(s.url)}<br>Snapshot SHA-256: ${esc(s.sha256)}</p>${s.paragraphs.map(p=>`<div class="paragraph" id="${s.id}-p${p.number}"><small>${s.id} · paragraph ${p.number}</small><p>${esc(p.text)}</p></div>`).join('')}`).join('');
  document.querySelectorAll('[data-source]').forEach(b=>b.onclick=()=>{$('source-view').open=true;document.querySelectorAll('.paragraph').forEach(p=>p.classList.remove('highlight'));const p=$(`${b.dataset.source}-p${b.dataset.paragraph}`);p.classList.add('highlight');p.scrollIntoView({behavior:'smooth',block:'center'});});
  document.querySelectorAll('[data-review]').forEach(b=>b.onclick=async()=>{const qid=b.dataset.review,note=$(`note-${qid}`).value,reviewer_type=$(`reviewer-type-${qid}`).value,reviewer_name=$(`reviewer-name-${qid}`).value.trim();if(!reviewer_type||!reviewer_name){notify('Choose human or automated and identify the reviewer.');return;}if(note.trim().length<3){notify('Add a short note explaining your review.');return;}b.disabled=true;try{activeCase=await api(`/api/cases/${c.id}/review`,{method:'POST',body:JSON.stringify({question_id:qid,decision:$(`decision-${qid}`).value,note,reviewer_type,reviewer_name})});renderCase();notify('Review saved. Original agent output preserved.');}catch(e){notify(e.message);b.disabled=false;}});
}
$('export').onclick=()=>{if(activeCase)window.location.href=`/api/cases/${activeCase.id}/packet.zip`;};
refreshStatus();listCases();
