"""Percorre a interface real em Chromium, em banco temporário, e gera evidências visuais."""
import base64
import json
import hashlib
import io
import zipfile
import sys
import tempfile
import threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
import integrar_kit
from playwright.sync_api import sync_playwright

OUTPUT=app.ROOT/'docs/demonstracao'
OUTPUT.mkdir(parents=True,exist_ok=True)

def demonstrate():
 original=app.DATA
 with tempfile.TemporaryDirectory() as tmp:
  app.DATA=Path(tmp);report=integrar_kit.integrate()
  server=app.ThreadingHTTPServer(('127.0.0.1',0),app.App)
  threading.Thread(target=server.serve_forever,daemon=True).start()
  url='http://127.0.0.1:'+str(server.server_port)
  checks=[];images=[];errors=[]
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    teacher=browser.new_page(viewport={'width':1440,'height':1100})
    student=browser.new_page(viewport={'width':1440,'height':1100})
    reserve=browser.new_page()
    for page in [teacher,student,reserve]:page.on('pageerror',lambda e:errors.append(str(e)))
    def state(page):return page.request.get(url+'/api/state').json()
    def post(page,path,data,status=200):
     r=page.request.post(url+'/api/'+path,data=data,headers={'X-CSRF':state(page)['csrf']})
     assert r.status==status,(path,r.status,r.text())
     return r.json()
    def refresh(page):
     page.get_by_role('button',name='Atualizar',exact=True).click();page.wait_for_timeout(100)
    def login(page,name,password,professor=False):
     page.goto(url+('/professor' if professor else '/aluno'))
     page.locator('#loginForm [name=name]').fill(name);page.locator('#loginForm [name=password]').fill(password)
     page.locator('#loginForm button').click();page.locator('#logout').wait_for(state='visible')
    def snapshot(page,name,title,full=True,locator=None):
     page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(100)
     if locator:locator.screenshot(path=str(OUTPUT/(name+'.png')))
     else:page.screenshot(path=str(OUTPUT/(name+'.png')),full_page=full,mask=[page.locator('.inbox code')])
     images.append({'file':name+'.png','title':title})
    def send_request(recipient,body):
     form=student.locator('form[data-api=request]');form.locator('select').select_option(recipient);form.locator('textarea').fill(body);form.locator('button').click();student.wait_for_timeout(100)
     return state(student)['requests'][-1]
    def approve_request(item):
     teacher.goto(url+'/professor/fase/'+str(item['phase']+1));teacher.locator('#logout').wait_for(state='visible');f=teacher.locator(f'form[data-request="{item["id"]}"]');f.locator('textarea').fill('Avaliação demonstrativa do texto específico deste destinatário.');f.get_by_role('button',name='Aprovar pedido de '+item['recipient'],exact=True).click();teacher.wait_for_timeout(100)
     assert next(r for r in state(teacher)['requests'] if r['id']==item['id'])['status']=='approved'
    def grant(code,request=None):
     m=next(m for m in state(teacher)['materials'] if m['code']==code);teacher.goto(url+'/professor/fase/'+str(m['phase']+1));teacher.locator('#logout').wait_for(state='visible');m=next(m for m in state(teacher)['materials'] if m['code']==code);team=next(g for g in state(teacher)['groups'] if g['name']=='Equipe Aurora')
     f=teacher.locator(f'form[data-material="{m["id"]}"]');f.locator('[name=team_id]').select_option(str(team['id']))
     if request:f.locator('[name=request_id]').select_option(str(request['id']))
     f.locator('button').click();teacher.wait_for_timeout(100);refresh(student)
     assert any(m['code']==code for m in state(student)['materials'])
     return m
    def advance():
     phase=state(student)['phase'];f=student.locator('form[data-api=submit]');f.locator('textarea').fill('ENTREGA NOMINAL DE TESTE — fase '+str(phase+1)+'. Verificação da interface; não constitui gabarito.');f.locator('button').click();student.wait_for_timeout(100)
     d=state(student)['deliveries'][-1];assert d['student_name']=='Aluno Demonstração'
     teacher.goto(url+'/professor/fase/'+str(phase+1));teacher.locator('#logout').wait_for(state='visible');f=teacher.locator(f'form[data-delivery="{d["id"]}"]');f.locator('textarea').fill('Avaliação demonstrativa concluída.');f.get_by_role('button',name='Aprovar entrega',exact=True).click();teacher.wait_for_timeout(100)
     assert state(student)['phase']==phase
     teacher.get_by_role('button',name='Enviar senha da fase '+str(phase+1),exact=True).first.click();teacher.wait_for_timeout(100)
     refresh(student);inbox=state(student)['messages'];assert inbox and not state(reserve)['messages']
     code=inbox[0]['code'];f=student.locator('form[data-api=unlock]');f.locator('input').fill('ERRADA');f.locator('button').click();student.locator('#message').filter(has_text='inválida').wait_for()
     checks.append('Fase '+str(phase+1)+': senha incorreta rejeitada; senha enviada pelo professor somente à equipe aprovada')
     f.locator('input').fill(code);f.locator('button').click();student.wait_for_timeout(100)
     assert state(student)['phase']==min(phase+1,5)
    pw=(app.DATA/'acesso-inicial.txt').read_text().split('Senha: ')[1].strip();login(teacher,'instrutor',pw,True)
    for page,name,team in [(student,'Aluno Demonstração','Equipe Aurora'),(reserve,'Aluno Reserva','Equipe Reserva')]:
     page.goto(url+'/aluno');f=page.locator('#registerForm')
     for k,v in {'name':name,'password':'teste-pessoal-123','team':team,'team_code':'teste-equipe-123'}.items():f.locator('[name='+k+']').fill(v)
     f.locator('button').click();page.locator('#message').filter(has_text='Cadastro concluído').wait_for();login(page,name,'teste-pessoal-123')
    assert student.locator('[data-api=review],[data-api=request-review],[data-api=analysis-review],[data-action=gate]').count()==0
    post(student,'gate',{'team_id':1},403);checks.append('Aluno sem controles de aprovação ou emissão; tentativa direta de emitir senha retorna HTTP 403')
    student.locator('details.evidence summary').first.click();snapshot(student,'01-denuncia','Portal do aluno · Denúncia e entrega nominal')
    advance()
    m=next(m for m in state(student)['materials'] if m['code']=='IMAGENS-FASE-02')
    with student.expect_download() as download:student.locator(f'a[href="/material/{m["id"]}"]').click()
    file=Path(tmp)/'imagens.zip';download.value.save_as(file);raw=file.read_bytes()
    values={file_name:hashlib.sha256(payload).hexdigest() for file_name,payload in [(m['filename'],raw)]}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
     assert len(z.namelist())==11 and all(n.endswith('.png') for n in z.namelist())
     values.update({n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()})
    f=student.locator('form[data-api=hash]');f.locator('select').select_option('anexos/A02.png');f.locator('input').fill('0'*64);f.locator('button').click();student.locator('#message').filter(has_text='Hash incorreto').wait_for()
    post(student,'submit',{'body':'Tentativa com hash divergente'},400)
    for name,value in values.items():
     f=student.locator('form[data-api=hash]');f.locator('select').select_option(name);f.locator('input').fill(value);f.locator('button').click();student.wait_for_timeout(70)
    assert not state(student)['hash_pending'] and not state(student)['hash_references']
    checks.append('ZIP baixado pela interface contém 11 imagens sem manifesto; SHA-256 de cada imagem e do ZIP calculado externamente e enviado')
    checks.append('Hash incorreto sinalizado; valores de referência não expostos no portal do aluno')
    snapshot(student,'02-preservacao','Portal do aluno · Hashes das imagens e do ZIP')
    advance()
    discord=send_request('Discord','PEDIDO SIMULADO AO DISCORD — objeto e identificador de conta, período, fuso, finalidade e autorização a serem avaliados pelo professor.')
    google=send_request('Google','PEDIDO SIMULADO AO GOOGLE — texto específico do provedor, com e-mail obtido da fonte e delimitação fundamentada para avaliação.')
    approve_request(discord);approve_request(google)
    teacher.goto(url+'/professor/fase/3');teacher.locator('#logout').wait_for(state='visible');section=teacher.locator('section').filter(has=teacher.get_by_role('heading',name='Pedidos recebidos',exact=True))
    snapshot(teacher,'09-pedidos-professor','Professor · Textos por plataforma, aluno e equipe',locator=section)
    snapshot(student,'03-pedidos','Portal do aluno · Pedidos e devolutivas por provedor')
    checks.append('Avaliador recebeu textos distintos para Discord e Google, com aluno e equipe, e aprovou cada um pela interface')
    advance();response=grant('A08',discord)
    assert reserve.request.get(url+'/material/'+str(response['id'])).status==403
    checks.append('Retorno liberado apenas após aprovação do pedido correspondente e somente à equipe Aurora')
    for identifier_type,value in [('ID de conta','SIM-DIS-U101'),('IP','203.0.113.45')]:
     f=student.locator('form[data-api=analysis]');f.locator('[name=response_id]').select_option(str(response['id']));f.locator('[name=identifier_type]').select_option(identifier_type)
     fields={'identifier_value':value,'findings':'Dado recebido do provedor: registrar origem e pertinência para a hipótese.','limits':'O registro não comprova sozinho identidade civil, uso exclusivo ou autoria.','next_step':'Providência específica para esclarecer o vínculo, com delimitação do registro técnico e justificativa.','next_recipient':'Equipe territorial / provedor competente conforme a medida','legal_basis':'Fundamento e autorização a serem avaliados pelo instrutor; conteúdo demonstrativo.'}
     for k,v in fields.items():f.locator('[name='+k+']').fill(v)
     f.locator('button').click();student.wait_for_timeout(100)
    teacher.goto(url+'/professor/fase/4');teacher.locator('#logout').wait_for(state='visible')
    first=state(student)['analyses'][0]
    review=teacher.locator(f'form[data-analysis="{first["id"]}"]');review.locator('textarea').fill('Detalhe os limites e reenvie a ficha preservando a origem.');review.get_by_role('button',name='Devolver análise para correção',exact=True).click();teacher.wait_for_timeout(100)
    refresh(student);student.locator('[data-action=revise-analysis]').first.click()
    form=student.locator('form[data-api=analysis]');assert form.locator('[name=revision_of]').input_value()==str(first['id'])
    form.locator('[name=limits]').fill('Versão corrigida: conta, conexão, dispositivo e titularidade não demonstram isoladamente autoria nem presença física.');form.locator('button').click();student.wait_for_timeout(100)
    assert state(student)['analyses'][0]['superseded_by']
    checks.append('Ficha devolvida para correção, reaberta pela interface e reenviada com histórico preservado')
    post(student,'submit',{'body':'Síntese aguardando avaliação das fichas.'})
    d=state(student)['deliveries'][-1];post(teacher,'review',{'id':d['id'],'status':'approved'},400)
    teacher.goto(url+'/professor/fase/4');teacher.locator('#logout').wait_for(state='visible')
    for item in state(student)['analyses']:
     if item.get('superseded_by'):continue
     f=teacher.locator(f'form[data-analysis="{item["id"]}"]');f.locator('textarea').fill('Identificador, limites e encaminhamento avaliados nesta demonstração.');f.get_by_role('button',name='Aprovar análise',exact=True).click();teacher.wait_for_timeout(100)
    refresh(student);snapshot(student,'04-respostas','Fase 4 · Identificadores, limites e próximas diligências')
    section=teacher.locator('section').filter(has=teacher.get_by_role('heading',name='Fichas para avaliação',exact=True));snapshot(teacher,'10-analises-professor','Professor · Avaliação individual das análises',locator=section)
    snapshot(teacher,'07-instrutor','Portal do professor · Equipes e envio de senhas',False)
    checks.append('Fase 4 bloqueada com análises pendentes; duas fichas por identificador avaliadas individualmente antes da passagem')
    post(teacher,'review',{'id':d['id'],'status':'approved'},400)
    student.goto(url+'/aluno/fase/4/pericia');student.locator('#logout').wait_for(state='visible')
    assert student.get_by_role('heading',name='Perícia e arrecadação no local',exact=True).is_visible()
    assert not any(m['code']=='LOCAL-A21-A22' for m in state(student)['materials'])
    pericial=send_request('Perícia','PEDIDO PERICIAL SIMULADO — exame e arrecadação no local, com finalidade, objeto e limites para avaliação do professor.')
    approve_request(pericial)
    team=next(g for g in state(teacher)['groups'] if g['name']=='Equipe Aurora')
    local=next(m for m in state(teacher)['materials'] if m['code']=='LOCAL-A21-A22')
    post(teacher,'release',{'id':local['id'],'team_id':team['id'],'request_id':pericial['id']},400)
    grant('A16',pericial);grant('LOCAL-A21-A22',pericial)
    with student.expect_download() as download:student.locator(f'a[href="/material/{local["id"]}"]').click()
    localfile=Path(tmp)/'pericia.zip';download.value.save_as(localfile);raw=localfile.read_bytes()
    values={local['filename']:hashlib.sha256(raw).hexdigest()}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
     assert set(z.namelist())=={'anexos/A21.png','anexos/A22.png'}
     values.update({n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()})
    for name,value in values.items():
     f=student.locator('form[data-api=hash]');f.locator('select').select_option(name);f.locator('input').fill(value);f.locator('button').click();student.wait_for_timeout(70)
    for code,value in [('A16','Exame pericial do local'),('LOCAL-A21-A22','Nomes inscritos no caderno')]:
     response_id=next(m['id'] for m in state(student)['materials'] if m['code']==code)
     f=student.locator('form[data-api=analysis]');f.locator('[name=response_id]').select_option(str(response_id));f.locator('[name=identifier_type]').select_option('Outro')
     fields={'identifier_value':value,'findings':'Vestígio simulado recebido em diligência posterior, com origem registrada.','limits':'A imagem e as inscrições não demonstram, isoladamente, autoria nem participação de cada pessoa.','next_step':'Conferir inscrições e correlações com os outros registros, preservando o material e explicitando as lacunas.','next_recipient':'Equipe de investigação / perícia conforme a diligência','legal_basis':'Justificativa e autorização a serem avaliadas pelo professor; exemplo de teste.'}
     for k,v in fields.items():f.locator('[name='+k+']').fill(v)
     f.locator('button').click();student.wait_for_timeout(100)
    refresh(teacher)
    for item in state(student)['analyses']:
     if item['status']=='approved' or item.get('superseded_by'):continue
     f=teacher.locator(f'form[data-analysis="{item["id"]}"]');f.locator('textarea').fill('Vestígio local, limites e providências avaliados na demonstração.');f.get_by_role('button',name='Aprovar análise',exact=True).click();teacher.wait_for_timeout(100)
    refresh(student);snapshot(student,'11-pericia','Fase 4 · Tela exclusiva de perícia e arrecadação')
    section=teacher.locator('section').filter(has=teacher.get_by_role('heading',name='Fichas para avaliação',exact=True));snapshot(teacher,'12-pericia-professor','Professor · Avaliação dos vestígios do local',locator=section)
    checks.append('A21 e A22 ausentes da entrega inicial e liberadas somente na tela de perícia após pedido aprovado e retorno A16')
    checks.append('Perícia: hashes das duas imagens e do ZIP recebidos e análises avaliadas antes da passagem')
    advance();grant('A15');grant('A25')
    netsul=send_request('NetSul Fibra','PEDIDO SIMULADO DO NOVO ACESSO — delimitar IP, porta, protocolo, instante e fuso, com fundamento a avaliar.');approve_request(netsul);grant('A24',netsul)
    snapshot(student,'05-atualizacao','Fase 5 · Novo pedido e retorno após avaliação')
    advance();snapshot(student,'06-relatorio','Fase 6 · Entrega nominal do relatório')
    advance();assert state(student)['completed'] and state(reserve)['phase']==0
    snapshot(student,'08-conclusao','Encerramento · Seis fases concluídas pela equipe')
    checks.append('Seis fases concluídas; equipe Reserva permanece na fase 1 sem acesso aos trabalhos de Aurora')
    assert not errors,errors;checks.append('Nenhum erro JavaScript no percurso dos dois portais');browser.close()
   result={'status':'passed','catalog':report['materials'],'verified_files':report['verified_files'],'checks':checks,'screenshots':images,'note':'Banco temporário; sem credenciais reais. Entregas demonstrativas não são gabaritos.'}
   (OUTPUT/'resultado.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));render_html(result)
   print(json.dumps({'status':'passed','screenshots':len(images),'checks':len(checks)},ensure_ascii=False))
  finally:server.shutdown();server.server_close();app.DATA=original

def render_html(result):
 body=[]
 for i,item in enumerate(result['screenshots']):
  b64=base64.b64encode((OUTPUT/item['file']).read_bytes()).decode()
  body.append(f'<section id="tela-{i}"><h2>{item["title"]}</h2><img src="data:image/png;base64,{b64}" alt="{item["title"]}"></section>')
 html='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Operação LUA — demonstração executada</title><style>body{margin:0;background:#0b111b;color:#e5edf8;font:16px system-ui}main{max-width:1200px;margin:auto;padding:32px}h1{font-size:34px}p,li{color:#b5c6dc;line-height:1.6}nav{display:flex;gap:10px;flex-wrap:wrap;position:sticky;top:0;padding:14px;background:#102130}a{color:#9bdfce;font-size:13px}img{width:100%;border:1px solid #344961;border-radius:12px}section{scroll-margin-top:90px;margin:40px 0}.status{color:#8adeb3}details{background:#152338;padding:18px;border-radius:10px}</style><main><p>ENTREGA 05 · TESTE REAL NO CHROMIUM</p><h1>Operação LUA em funcionamento</h1><p class="status">Portais separados · 13 imagens + ZIP · avaliação nominal · análise por identificador</p><p>As telas abaixo foram capturadas da aplicação em execução. O teste usa equipes fictícias e um banco temporário. As respostas de teste não são modelos de investigação.</p><nav>'''
 html+=''.join(f'<a href="#tela-{i}">{item["title"].split(" · ")[0]}</a>' for i,item in enumerate(result['screenshots']))+'</nav><details><summary>Ver verificações executadas</summary><ul>'
 html+=''.join('<li>'+x+'</li>' for x in result['checks'])+'</ul></details>'+''.join(body)+'</main></html>'
 (OUTPUT/'demonstracao.html').write_text(html)

if __name__=='__main__':demonstrate()
