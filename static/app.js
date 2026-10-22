let state;
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const message=t=>{$('#message').textContent=t;};
async function api(path,data){
 const r=await fetch('/api/'+path,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF':state?.csrf||''},body:JSON.stringify(data)});
 if(!r.ok)throw Error((await r.json()).error);
 return ['login','logout'].includes(path)?{}:r.json();
}
const criteria=[['Abordagem à fonte','Avaliação de risco','Providências iniciais'],['Inventário e recebimento','Registro de hashes','Cadeia de custódia'],['Identificadores e competência','Pedidos fundamentados'],['Respostas e diligências','Cadeias e limites de atribuição'],['Atualização e novo pedido','Hipóteses revisadas'],['Dossiê final','Limites e medidas cabíveis']];
const labelStatus={submitted:'Em avaliação',approved:'Aprovada',correction:'Correção solicitada'};
const time=t=>new Date(t*1000).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'});
const teamOptions=()=>state.groups.filter(g=>!g.completed).map(g=>`<option value="${g.id}">${esc(g.name)} · fase ${g.phase+1}</option>`).join('');
const requestOptions=(team)=>'<option value="">Selecione o pedido que justifica o retorno</option>'+state.requests.filter(r=>r.team_id===Number(team)).map(r=>`<option value="${r.id}">#${r.id} · ${esc(r.recipient)}</option>`).join('');
function materialCard(m,teacher){
 let content=`<div class="material"><span class="tag">${esc(m.code||'ARQUIVO')} · ${m.kind==='teacher'?'EXCLUSIVO DO INSTRUTOR':'FASE '+(m.phase+1)}</span><h3>${esc(m.title)}</h3><a class="button secondary" href="/material/${m.id}" download>Baixar ${m.filename?.endsWith('.zip')?'pacote':'arquivo'} ↓</a>`;
 if(teacher&&m.kind==='response'){
  content+=`<p>${esc(m.condition)}</p><small>Pedidos vinculados devem ser avaliados pelo instrutor antes da liberação.</small><form data-api="release" data-material="${m.id}"><label>Equipe<select name="team_id" class="grant-team" required><option value="">Selecione a equipe</option>${teamOptions()}</select></label><label>Pedido correspondente<select name="request_id"><option value="">${['A15','A25'].includes(m.code)?'Atualização sem pedido prévio':'Selecione primeiro uma equipe'}</option></select></label><button>Liberar para esta equipe</button></form><small>${m.teams.length?'Liberado para: '+m.teams.map(id=>esc(state.groups.find(g=>g.id===id)?.name||id)).join(', '):'Ainda não liberado para equipes'}</small>`;
 }
 if(m.previews?.length&&!teacher){content+='<details class="evidence"><summary>Visualizar evidências ('+m.previews.length+')</summary><div class="evidence-gallery">'+m.previews.map(name=>{
 const src='/asset/'+m.id+'/'+name.split('/').map(encodeURIComponent).join('/');
 return `<figure>${name.endsWith('.mp4')?`<video controls preload="none" src="${src}"></video>`:`<a href="${src}" target="_blank" rel="noopener"><img loading="lazy" src="${src}" alt="Evidência simulada ${esc(name)}"></a>`}<figcaption>${esc(name)}</figcaption></figure>`;
 }).join('')+'</div></details>';}
 return content+'</div>';
}
function render(){
 const teacher=state.user.role==='instructor';const p=state.phase;
 $('#access').hidden=true;$('.welcome').hidden=true;$('#logout').hidden=false;const w=$('#workspace');w.hidden=false;
 const sidebar=`<aside class="steps"><div class="step-title">PERCURSO DO CASO</div>${state.phases.map((name,i)=>`<div class="step ${!teacher&&i===p?'active':!teacher&&i<p?'done':''}"><span>${String(i+1).padStart(2,'0')}</span>${esc(name)}</div>`).join('')}</aside>`;
 let html=`<div class="casebar"><div><span class="eyebrow">${teacher?'CENTRAL DE CONDUÇÃO':'EQUIPE '+esc(state.user.team)}</span><h2>${teacher?'Painel do instrutor':esc(state.user.name)}</h2></div><button class="ghost" data-action="refresh">Atualizar</button></div>`;
 if(teacher){
  html+=`<section><span class="eyebrow">ACOMPANHAMENTO</span><h2>Equipes em campo</h2>${state.groups.map(g=>`<div class="team-row"><div><strong>${esc(g.name)}</strong><p>${g.completed?'Exercício concluído':'Fase '+(g.phase+1)+' · '+esc(state.phases[g.phase])}</p></div>${g.completed?'<span class="badge">CONCLUÍDO</span>':`<button data-action="gate" data-team="${g.id}">Emitir senha da fase ${g.phase+1}</button>`}</div>`).join('')||'<p>Os alunos criam suas equipes pelo cadastro inicial.</p>'}<details><summary>Cadastrar equipe pelo instrutor</summary><form data-api="group"><label>Nome da equipe<input name="name" required></label><label>Código de entrada<input name="password" type="password" minlength="10" required></label><button>Cadastrar equipe</button></form></details></section>`;
  html+=`<section><span class="eyebrow">ACERVO INTEGRADO</span><h2>Materiais das seis fases</h2><p>Estes pacotes aparecem para a equipe somente quando ela desbloqueia a fase correspondente.</p><div class="materials-grid">${state.materials.filter(m=>m.kind==='phase'||m.kind==='manual').map(m=>materialCard(m,true)).join('')}</div></section>`;
  html+=`<section><h2>Pedidos recebidos</h2>${renderRequests()}</section>`;
  html+=`<section><span class="eyebrow">RETORNOS SOB CONTROLE DO INSTRUTOR</span><h2>Respostas de provedores e diligências</h2><div class="materials-grid">${state.materials.filter(m=>m.kind==='response').map(m=>materialCard(m,true)).join('')}</div></section>`;
  html+=`<section><h2>Área reservada do professor</h2><p>Estes arquivos não são disponibilizados aos alunos.</p><div class="materials-grid">${state.materials.filter(m=>m.kind==='teacher').map(m=>materialCard(m,true)).join('')}</div></section>`;
 }else{
  const s=state.scenario;
  html+=`<section class="mission"><span class="eyebrow">MISSÃO ${String(p+1).padStart(2,'0')} / 06</span><h2>${esc(s.titulo)}</h2><p>${esc(s.contexto)}</p><ol>${s.acoes.map(a=>`<li>${esc(a)}</li>`).join('')}</ol><div class="deliverable"><strong>Produto esperado</strong><p>${esc(s.entrega)}</p></div></section>`;
  html+=`<section><span class="eyebrow">ACERVO DA EQUIPE</span><h2>Materiais disponíveis</h2><div class="materials-grid">${state.materials.map(m=>materialCard(m,false)).join('')||'<p>Nenhum material disponível.</p>'}</div></section>`;
  if(p>=1){
   html+=`<section><span class="eyebrow">INTEGRIDADE DOS VESTÍGIOS</span><h2>Registrar SHA-256</h2><p><strong>${state.inventory.length-state.hash_pending.length} de ${state.inventory.length} arquivos conferidos.</strong> A entrega da fase 2 exige todos os hashes correspondentes ao manifesto.</p><p>Calcule com sua ferramenta ou use o apoio local abaixo. O arquivo selecionado não é enviado ao servidor; somente nome e hash são registrados.</p><label>Calcular e registrar uma pasta extraída<input id="hashfolder" type="file" webkitdirectory multiple></label><label>Arquivo para cálculo local<input id="hashfile" type="file"></label><form data-api="hash"><label>Nome no inventário<select name="name" id="hashname">${state.inventory.map(n=>`<option>${esc(n)}</option>`).join('')}</select></label><label>SHA-256 calculado<input name="sha256" id="hashvalue" required pattern="[a-fA-F0-9]{64}" placeholder="64 caracteres hexadecimais"></label><button>Registrar e conferir hash</button></form>${renderHashes()}</section>`;
  }
  if(p>=2&&p<=4&&!state.completed){
   html+=`<section><span class="eyebrow">COMUNICAÇÕES DA INVESTIGAÇÃO</span><h2>Enviar pedido ou diligência</h2><form data-api="request"><label>Destinatário<select name="recipient"><option>Discord</option><option>Google</option><option>Instagram</option><option>Telegram</option><option>Rede de vídeos</option><option>NetSul Fibra</option><option>Equipe territorial</option><option>Perícia</option></select></label><label>Objeto, identificadores, período, fundamento e autorização necessária<textarea name="body" required placeholder="Redija e justifique a medida proposta."></textarea></label><button>Encaminhar ao instrutor</button></form><h3>Pedidos da equipe</h3>${renderRequests()}</section>`;
  }
  if(!state.completed){
   html+=`<section><span class="eyebrow">CHECKPOINT DA FASE</span><h2>Entrega para avaliação</h2><p>${criteria[p].map(x=>esc(x)).join(' · ')}</p><form data-api="submit"><label>Resposta e registros da equipe<textarea name="body" required placeholder="Organize aqui o produto desta fase e as referências às evidências."></textarea></label><button>Enviar entrega →</button></form></section><section class="unlock"><span class="eyebrow">PASSAGEM CONTROLADA</span><h2>${p===5?'Concluir o exercício':'Desbloquear a próxima fase'}</h2><p>${esc(s.liberacao)} A senha só funciona após a aprovação da última entrega.</p><form data-api="unlock"><label>Senha fornecida pelo instrutor<input name="code" type="password" required autocomplete="off"></label><button>${p===5?'Confirmar encerramento':'Desbloquear fase →'}</button></form></section>`;
  }else html+='<section class="unlock"><h2>Exercício concluído</h2><p>Dossiê aprovado e encerramento confirmado. O acervo e o histórico continuam disponíveis.</p></section>';
 }
 html+=`<section><span class="eyebrow">TRILHA DA INVESTIGAÇÃO</span><h2>Entregas e devolutivas</h2>${renderDeliveries(teacher)}</section>`;
 if(teacher)html+=`<section><h2>Registros de integridade recebidos</h2>${renderHashes()}</section>`;
 w.innerHTML=`<div class="layout">${sidebar}<div>${html}</div></div>`;
}
function renderRequests(){return state.requests.map(r=>`<article class="request-box"><small>Pedido #${r.id} · ${esc(r.name)} · fase ${r.phase+1} · ${time(r.created)}</small><h3>${esc(r.recipient)}</h3><pre>${esc(r.body)}</pre></article>`).join('')||'<p>Nenhum pedido registrado.</p>';}
function renderHashes(){return state.hashes.map(h=>`<details><summary class="${h.matched?'hash-ok':'hash-bad'}">${h.matched?'✓ Confere':'! Divergente'} · ${esc(h.name)}</summary><code>${esc(h.sha256)}</code><p>${time(h.created)}</p></details>`).join('')||'<p>Nenhum hash registrado.</p>';}
function renderDeliveries(teacher){return [...state.deliveries].reverse().map(d=>`<article><small>${esc(d.name)} · fase ${d.phase+1} · ${time(d.created)}</small><h3>${labelStatus[d.status]}</h3><pre>${esc(d.body)}</pre>${d.feedback?`<p><strong>Devolutiva:</strong> ${esc(d.feedback)}</p>`:''}${teacher?`<form class="review-box" data-api="review" data-delivery="${d.id}"><label>Devolutiva<textarea name="feedback"></textarea></label><button name="status" value="approved">Aprovar entrega</button><button class="secondary" name="status" value="correction">Solicitar correção</button></form>`:''}</article>`).join('')||'<p>Nenhuma entrega nesta investigação.</p>';}
async function load(){const r=await fetch('/api/state');if(!r.ok)return;state=await r.json();render();}
async function run(path,data){try{const result=await api(path,data);if(path==='logout'){location.reload();return;}message(result.code?'Equipe '+result.team+' · fase '+result.phase+'\nSenha de passagem: '+result.code+'\nEntregue somente à equipe correspondente.':path==='register'?'Cadastro concluído. Entre com seu usuário e senha pessoal.':'Operação registrada.');await load();}catch(e){message(e.message);}window.scrollTo({top:0,behavior:'smooth'});}
document.addEventListener('submit',e=>{
 const form=e.target;e.preventDefault();const data=Object.fromEntries(new FormData(form));let path=form.dataset.api;
 if(form.id==='loginForm')path='login';if(form.id==='registerForm')path='register';
 if(path==='release'){data.id=Number(form.dataset.material);data.team_id=Number(data.team_id);data.request_id=data.request_id?Number(data.request_id):null;}
 if(path==='review'){data.id=Number(form.dataset.delivery);data.status=e.submitter.value;}
 if(path)run(path,data);
});
document.addEventListener('click',e=>{const b=e.target.closest('[data-action]');if(!b)return;if(b.dataset.action==='refresh')load();if(b.dataset.action==='gate')run('gate',{team_id:Number(b.dataset.team)});});
document.addEventListener('change',async e=>{
 if(e.target.classList.contains('grant-team')){e.target.form.elements.request_id.innerHTML=requestOptions(e.target.value);}
 if(e.target.id==='hashfolder'){
  try{let count=0;for(const f of e.target.files){const path=state.inventory.find(n=>f.webkitRelativePath.endsWith('/'+n));if(!path)continue;const h=await crypto.subtle.digest('SHA-256',await f.arrayBuffer());const sha256=Array.from(new Uint8Array(h),b=>b.toString(16).padStart(2,'0')).join('');await api('hash',{name:path,sha256});count++;}message(count+' hashes calculados e registrados.');await load();}catch(e){message(e.message);}
 }
 if(e.target.id==='hashfile'){
  const f=e.target.files[0];if(!f)return;try{const h=await crypto.subtle.digest('SHA-256',await f.arrayBuffer());$('#hashvalue').value=Array.from(new Uint8Array(h),b=>b.toString(16).padStart(2,'0')).join('');const path=state.inventory.find(n=>n===f.name||n.endsWith('/'+f.name));if(path)$('#hashname').value=path;}catch(e){message('Não foi possível calcular o hash: '+e.message);}
 }
});
$('#logout').onclick=()=>run('logout',{});
load();
