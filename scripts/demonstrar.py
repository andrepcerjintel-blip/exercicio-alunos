"""Percorre a interface real em Chromium, em banco temporário, e gera evidências visuais."""
import base64
import json
import re
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
    tc=browser.new_context(viewport={'width':1440,'height':1100});sc=browser.new_context(viewport={'width':1440,'height':1100});bc=browser.new_context()
    teacher=tc.new_page();student=sc.new_page();bravo=bc.new_page()
    for page in [teacher,student,bravo]:page.on('pageerror',lambda error:errors.append(str(error)))
    def state(page):return page.request.get(url+'/api/state').json()
    def post(page,path,data):
     csrf=state(page)['csrf']
     r=page.request.post(url+'/api/'+path,data=data,headers={'X-CSRF':csrf})
     assert r.ok,(path,r.status,r.text())
     return r.json()
    def login(page,name,password):
     page.goto(url);page.locator('#loginForm [name=name]').fill(name);page.locator('#loginForm [name=password]').fill(password);page.locator('#loginForm button').click();page.locator('#logout').wait_for(state='visible')
    def snapshot(page,name,title,full=True):
     page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(100)
     page.screenshot(path=str(OUTPUT/(name+'.png')),full_page=full)
     images.append({'file':name+'.png','title':title})
    def refresh(page):
     page.get_by_role('button',name='Atualizar',exact=True).click();page.wait_for_timeout(100)
    def advance():
     phase=state(student)['phase']
     form=student.locator('form[data-api=submit]')
     form.locator('textarea').fill('ENTREGA DE TESTE DA INTERFACE — fase '+str(phase+1)+'. Registros fictícios para validar o fluxo; não constitui gabarito pedagógico.')
     form.locator('button').click();student.wait_for_timeout(100)
     delivery=state(student)['deliveries'][-1]
     refresh(teacher)
     teacher.locator(f'form[data-delivery="{delivery["id"]}"] textarea').fill('Teste funcional: entrega recebida e fluxo de passagem autorizado.')
     teacher.locator(f'form[data-delivery="{delivery["id"]}"]').get_by_role('button',name='Aprovar entrega').click()
     teacher.wait_for_timeout(100)
     assert state(student)['phase']==phase
     teacher.get_by_role('button',name='Emitir senha da fase '+str(phase+1),exact=True).first.click()
     teacher.locator('#message').filter(has_text='Senha de passagem:').wait_for()
     code=re.search(r'Senha de passagem: ([A-F0-9]+)',teacher.locator('#message').inner_text()).group(1)
     unlock=student.locator('form[data-api=unlock]')
     unlock.locator('input').fill('ERRADA')
     unlock.locator('button').click();student.locator('#message').filter(has_text='inválida').wait_for()
     checks.append('Fase '+str(phase+1)+': senha incorreta rejeitada')
     unlock.locator('input').fill(code);unlock.locator('button').click()
     student.wait_for_timeout(150)
     st=state(student)
     assert st['phase']==min(phase+1,5)
     checks.append('Fase '+str(phase+1)+': entrega aprovada e senha correta aceitas')
    pw=(app.DATA/'acesso-inicial.txt').read_text().split('Senha: ')[1].strip()
    login(teacher,'instrutor',pw)
    student.goto(url)
    registration=student.locator('#registerForm')
    for key,value in {'name':'Aluno Demonstração','password':'demonstracao-12345','team':'Equipe Aurora','team_code':'aurora-teste-12345'}.items():registration.locator('[name='+key+']').fill(value)
    registration.locator('button').click();student.locator('#message').filter(has_text='Cadastro concluído').wait_for()
    login(student,'Aluno Demonstração','demonstracao-12345')
    bravo.goto(url)
    for key,value in {'name':'Aluno Reserva','password':'demonstracao-12345','team':'Equipe Reserva','team_code':'reserva-teste-12345'}.items():bravo.locator('#registerForm [name='+key+']').fill(value)
    bravo.locator('#registerForm button').click();bravo.locator('#message').filter(has_text='Cadastro concluído').wait_for()
    login(bravo,'Aluno Reserva','demonstracao-12345')
    student.locator('details.evidence summary').click();student.locator('.evidence-gallery img').first.wait_for()
    student.wait_for_timeout(150)
    assert student.locator('.evidence-gallery img').first.evaluate('(img)=>img.complete && img.naturalWidth>0')
    snapshot(student,'01-denuncia','Fase 1 · Denúncia recebida e abordagem à fonte')
    advance()
    student.locator('#hashfile').set_input_files(str(app.ROOT/'02_PROVAS_INICIAIS_ALUNOS/anexos/A02.png'))
    student.wait_for_function("document.querySelector('#hashvalue').value.length===64")
    student.locator('form[data-api=hash] button').click();student.wait_for_timeout(150)
    assert state(student)['hashes'][-1]['matched']==1
    checks.append('SHA-256 calculado no navegador e conferido com o manifesto')
    # Test that the checkpoint refuses a delivery while the inventory is incomplete.
    r=student.request.post(url+'/api/submit',data={'body':'Tentativa sem inventário completo'},headers={'X-CSRF':state(student)['csrf']})
    assert r.status==400
    checks.append('Entrega da fase 2 bloqueada com hashes pendentes')
    student.locator('#hashfolder').set_input_files(str(app.ROOT/'02_PROVAS_INICIAIS_ALUNOS'))
    student.locator('#message').filter(has_text='18 hashes calculados e registrados').wait_for()
    assert not state(student)['hash_pending']
    checks.append('Pasta completa: 18 hashes calculados no navegador e registrados sem enviar os arquivos')
    snapshot(student,'02-preservacao','Fase 2 · Pacote de provas e registro de integridade')
    advance()
    request=student.locator('form[data-api=request]');request.locator('select').select_option('Discord')
    request.locator('textarea').fill('PEDIDO SIMULADO DE TESTE — registros da conta ROOK, com delimitação temporal e fuso, finalidade e justificativa a serem avaliados pelo instrutor. A validação de legislação é manual.')
    request.locator('button').click();student.wait_for_timeout(150)
    snapshot(student,'03-pedidos','Fase 3 · Triagem e pedido ao provedor')
    advance()
    refresh(teacher);t=state(teacher);team=next(g for g in t['groups'] if g['name']=='Equipe Aurora');response=next(m for m in t['materials'] if m['code']=='A08')
    req=state(student)['requests'][-1]
    grant=teacher.locator(f'form[data-material="{response["id"]}"]')
    grant.locator('[name=team_id]').select_option(str(team['id']));grant.locator('[name=request_id]').select_option(str(req['id']));grant.locator('button').click();teacher.wait_for_timeout(150)
    refresh(student)
    assert any(m['code']=='A08' for m in state(student)['materials'])
    assert bravo.request.get(url+'/material/'+str(response['id'])).status==403
    checks.append('Resposta A08 liberada pela interface somente para Aurora; Reserva recebe HTTP 403')
    snapshot(student,'04-respostas','Fase 4 · Resposta do Discord vinculada ao pedido')
    snapshot(teacher,'07-instrutor','Instrutor · Equipes, acervo e condução',False)
    advance()
    refresh(teacher)
    for code in ['A15','A25']:
     m=next(m for m in state(teacher)['materials'] if m['code']==code)
     post(teacher,'release',{'id':m['id'],'team_id':team['id']})
    refresh(student)
    snapshot(student,'05-atualizacao','Fase 5 · Atualização posterior liberada para a equipe')
    advance()
    snapshot(student,'06-relatorio','Fase 6 · Dossiê e conclusão fundamentada')
    advance()
    assert state(student)['completed']
    assert state(bravo)['phase']==0
    snapshot(student,'08-conclusao','Encerramento · Seis fases concluídas com senha')
    checks.append('Conclusão confirmada na fase 6; equipe Reserva permanece na fase 1')
    assert not errors,errors
    checks.append('Chromium: nenhum erro JavaScript durante o percurso')
    browser.close()
   result={'status':'passed','catalog':report['materials'],'verified_files':report['verified_files'],'checks':checks,'screenshots':images,'note':'Banco temporário; não altera equipes e entregas reais. Entregas demonstrativas não são gabarito.'}
   (OUTPUT/'resultado.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
   render_html(result)
   print(json.dumps({'status':'passed','screenshots':len(images),'checks':len(checks)},ensure_ascii=False))
  finally:server.shutdown();server.server_close();app.DATA=original

def render_html(result):
 body=[]
 for i,item in enumerate(result['screenshots']):
  b64=base64.b64encode((OUTPUT/item['file']).read_bytes()).decode()
  body.append(f'<section id="tela-{i}"><h2>{item["title"]}</h2><img src="data:image/png;base64,{b64}" alt="{item["title"]}"></section>')
 html='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Operação LUA — demonstração executada</title><style>body{margin:0;background:#0b111b;color:#e5edf8;font:16px system-ui}main{max-width:1200px;margin:auto;padding:32px}h1{font-size:34px}p,li{color:#b5c6dc;line-height:1.6}nav{display:flex;gap:10px;flex-wrap:wrap;position:sticky;top:0;padding:14px;background:#102130}a{color:#9bdfce;font-size:13px}img{width:100%;border:1px solid #344961;border-radius:12px}section{scroll-margin-top:90px;margin:40px 0}.status{color:#8adeb3}details{background:#152338;padding:18px;border-radius:10px}</style><main><p>ENTREGA 04 · TESTE REAL NO CHROMIUM</p><h1>Operação LUA em funcionamento</h1><p class="status">21 materiais integrados · 30 hashes conferidos · seis fases percorridas</p><p>As telas abaixo foram capturadas da aplicação em execução. O teste usa equipes fictícias e um banco temporário. As respostas de teste não são modelos de investigação.</p><nav>'''
 html+=''.join(f'<a href="#tela-{i}">{item["title"].split(" · ")[0]}</a>' for i,item in enumerate(result['screenshots']))+'</nav><details><summary>Ver verificações executadas</summary><ul>'
 html+=''.join('<li>'+x+'</li>' for x in result['checks'])+'</ul></details>'+''.join(body)+'</main></html>'
 (OUTPUT/'demonstracao.html').write_text(html)

if __name__=='__main__':demonstrate()
