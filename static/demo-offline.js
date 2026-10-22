const SCENES=__SCENES__;
const ASSETS=__ASSETS__;
const KEY='lua-demonstracao-browser-v1';
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let game={student:'',team:'',phase:0,deliveries:[],requests:[],hashes:[],approved:false,code:'',done:false};
try{const saved=localStorage.getItem(KEY);if(saved)game=JSON.parse(saved);}catch(e){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(game));}catch(e){notice('O navegador não permitiu salvar o progresso. Mantenha esta aba aberta.');}}
function notice(s){$('#message').textContent=s;}
function render(){
 const p=game.phase;
 $('#begin').hidden=!!game.team;$('#workspace').hidden=!game.team;
 if(!game.team)return;
 $('#workspace').innerHTML=`<div class="layout"><aside class="steps"><div class="step-title">PERCURSO DO CASO</div>${SCENES.map((s,i)=>`<div class="step ${i===p?'active':i<p?'done':''}"><span>${i+1}</span>${['Denúncia','Preservação','Pedidos','Respostas','Atualização','Relatório'][i]}</div>`).join('')}</aside><div><div class="casebar"><div><span class="eyebrow">DEMONSTRAÇÃO INTERATIVA</span><h2>${esc(game.team)} · ${esc(game.student)}</h2></div><button id="reset" class="ghost">Recomeçar teste</button></div>${game.done?'<section class="unlock"><h2>Exercício de demonstração concluído</h2><p>Você percorreu as seis fases. No sistema completo, o instrutor avalia cada equipe e mantém as respostas sob controle de acesso no servidor.</p></section>':`<section class="mission"><span class="eyebrow">FASE ${p+1} / 6</span><h2>${esc(SCENES[p].titulo)}</h2><p>${esc(SCENES[p].contexto)}</p><ol>${SCENES[p].acoes.map(a=>`<li>${esc(a)}</li>`).join('')}</ol><div class="deliverable"><strong>Entrega esperada</strong><p>${esc(SCENES[p].entrega)}</p></div></section>`}
${p===0?`<section><h2>Denúncia recebida no plantão</h2><img alt="Denúncia fictícia recebida pelo WhatsApp" style="max-width:100%;max-height:650px;object-fit:contain" src="${ASSETS[0].url}"></section>`:''}
${p>=1?`<section><h2>Amostra das provas iniciais</h2><p>Esta demonstração inclui duas capturas originais do kit. O sistema completo entrega o pacote integral e exige os 18 hashes.</p><div class="materials-grid">${ASSETS.slice(1).map((a,i)=>`<div class="material"><img style="width:100%;max-height:320px;object-fit:contain" src="${a.url}" alt="${esc(a.name)}"><h3>${esc(a.name)}</h3><a class="button secondary" download="${esc(a.name)}" href="${a.url}">Baixar imagem</a></div>`).join('')}</div>${!game.done&&p===1?`<h3>Registrar integridade</h3><p>Baixe uma das imagens acima e selecione o mesmo arquivo abaixo. O hash será calculado localmente e comparado ao original incluído nesta demonstração.</p><input type="file" id="evidence"><div id="hashResult"></div>`:''}<p>${game.hashes.length?'✓ '+game.hashes.length+' hash(es) conferido(s) nesta demonstração.':'Nenhum hash registrado.'}</p></section>`:''}
${p>=2&&p<=4&&!game.done?`<section><h2>Pedido ou diligência</h2><form id="request"><label>Destinatário<select name="recipient"><option>Discord</option><option>Google</option><option>Instagram</option><option>Telegram</option><option>NetSul Fibra</option><option>Equipe territorial</option><option>Perícia</option></select></label><label>Objeto, identificadores, período, fundamento e autorização necessária<textarea name="body" required></textarea></label><button>Registrar pedido</button></form>${game.requests.map(r=>`<article><small>Fase ${r.phase+1}</small><h3>${esc(r.recipient)}</h3><pre>${esc(r.body)}</pre></article>`).join('')}</section>`:''}
${p===3?`<section><h2>Rodada de respostas</h2><p>O instrutor avalia o pedido e libera apenas o retorno correspondente. Nesta demonstração, ${game.requests.length?'há pedido registrado para avaliação.':'registre primeiro um pedido.'}</p><p>Os PDFs dos provedores e os gabaritos não estão incluídos neste arquivo de demonstração. Eles permanecem no sistema completo.</p></section>`:''}
${p===4?'<section><h2>Atualização posterior</h2><p>Nesta fase entram a atualização A15 e os metadados A25; o retorno A24 depende de pedido sobre o novo acesso. Analise a mudança de cenário e registre as medidas propostas.</p></section>':''}
${!game.done?`<section><h2>Entrega da equipe</h2><form id="delivery"><label>Resposta e registros da fase<textarea name="body" required>${esc(game.deliveries.findLast(d=>d.phase===p)?.body||'')}</textarea></label><button>Enviar entrega</button></form><p>${game.approved?'✓ Última entrega aprovada pelo instrutor demonstrativo.':'Aguardando entrega e avaliação.'}</p></section><section><h2>Simular o papel do instrutor</h2><p>Controle exclusivo desta demonstração: você alterna entre os dois papéis para avaliar o fluxo. Não representa autenticação ou controle de acesso para uma turma real.</p><button id="approve" class="secondary">Simular aprovação da entrega</button><button id="issue" class="secondary">Emitir senha desta fase</button><p id="demoCode">${game.code?'Senha demonstrativa desta fase: '+esc(game.code):''}</p></section><section class="unlock"><h2>${p===5?'Encerrar exercício':'Desbloquear próxima fase'}</h2><form id="unlock"><label>Senha desta fase<input name="code" type="password" required autocomplete="off"></label><button>${p===5?'Concluir':'Desbloquear'}</button></form></section>`:''}
<section><h2>Histórico de entregas</h2>${game.deliveries.map(d=>`<article><small>Fase ${d.phase+1}</small><pre>${esc(d.body)}</pre></article>`).join('')||'<p>Ainda não há entregas.</p>'}<button id="export" class="secondary">Exportar registros do teste</button></section></div></div>`;
}
document.addEventListener('submit',e=>{
 e.preventDefault();const f=e.target;const data=Object.fromEntries(new FormData(f));
 if(f.id==='setup'){game.student=data.student.trim();game.team=data.team.trim();if(!game.student||!game.team)return;}
 if(f.id==='request'){game.requests.push({...data,phase:game.phase});notice('Pedido registrado. A adequação jurídica é avaliada pelo instrutor, não automaticamente.');}
 if(f.id==='delivery'){
  if(game.phase===1&&!game.hashes.length){notice('Registre primeiro o hash de uma das imagens da amostra.');return;}
  if(game.phase===2&&!game.requests.some(r=>r.phase===2)){notice('Registre um pedido antes de entregar esta fase.');return;}
  game.deliveries.push({body:data.body,phase:game.phase});game.approved=false;game.code='';notice('Entrega registrada. Use o painel demonstrativo do instrutor para avaliar e emitir a senha.');
 }
 if(f.id==='unlock'){
  if(!game.approved||!game.code||data.code!==game.code){notice('Passagem bloqueada: é necessária a aprovação da última entrega e a senha correta desta fase.');return;}
  if(game.phase===5)game.done=true;else game.phase++;
  game.approved=false;game.code='';notice(game.done?'Demonstração concluída.':'Nova fase desbloqueada.');
 }
 save();render();window.scrollTo(0,0);
});
document.addEventListener('click',e=>{
 if(e.target.id==='approve'){
  if(!game.deliveries.some(d=>d.phase===game.phase)){notice('Envie a entrega desta fase primeiro.');return;}
  game.approved=true;notice('Aprovação simulada registrada. Agora emita a senha.');save();render();
 }
 if(e.target.id==='issue'){
  if(!game.approved){notice('Aprove a última entrega antes de emitir a senha.');return;}
  const values=new Uint8Array(4);crypto.getRandomValues(values);game.code=Array.from(values,b=>b.toString(16).padStart(2,'0')).join('').toUpperCase();save();render();notice('Senha demonstrativa emitida. Copie-a do painel e informe no campo da passagem.');
 }
 if(e.target.id==='reset'&&confirm('Apagar somente o progresso desta demonstração?')){game={student:'',team:'',phase:0,deliveries:[],requests:[],hashes:[],approved:false,code:'',done:false};save();render();notice('Demonstração reiniciada.');}
 if(e.target.id==='export'){
  const {code,...record}=game;const blob=new Blob([JSON.stringify(record,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='LUA_registros_demonstracao.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
});
document.addEventListener('change',async e=>{
 if(e.target.id!=='evidence'||!e.target.files[0])return;
 const file=e.target.files[0];
 try{
  const value=await crypto.subtle.digest('SHA-256',await file.arrayBuffer());const hash=Array.from(new Uint8Array(value),b=>b.toString(16).padStart(2,'0')).join('');const asset=ASSETS.slice(1).find(a=>a.hash===hash);
  if(!asset){$('#hashResult').textContent='Hash divergente: selecione um dos arquivos originais da amostra.';return;}
  game.hashes=game.hashes.filter(h=>h.name!==asset.name);game.hashes.push({name:asset.name,sha256:hash});save();render();notice('SHA-256 conferido: '+asset.name+'\n'+hash);
 }catch(error){notice('Não foi possível calcular o hash neste navegador: '+error.message);}
});
render();
