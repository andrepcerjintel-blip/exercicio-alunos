import re,json,threading
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(root/'distribuicao')))
threading.Thread(target=server.serve_forever,daemon=True).start()
errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1400,'height':1000})
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:'+str(server.server_port)+'/Operacao_LUA_Teste_Navegador.html')
 page.locator('#setup [name=student]').fill('Teste local')
 page.locator('#setup [name=team]').fill('Aurora')
 page.locator('#setup button').click()
 for phase in range(6):
  if phase==1:
   page.locator('#delivery textarea').fill('Tentativa sem hash')
   page.locator('#delivery button').click()
   assert 'hash' in page.locator('#message').inner_text()
   page.locator('#evidence').set_input_files(str(root/'02_PROVAS_INICIAIS_ALUNOS/anexos/A02.png'))
   page.locator('#message').filter(has_text='SHA-256 conferido').wait_for()
  if phase==2:
   page.locator('#request textarea').fill('Pedido fictício para testar o registro.')
   page.locator('#request button').click()
  page.locator('#delivery textarea').fill('Entrega de teste da fase '+str(phase+1))
  page.locator('#delivery button').click()
  page.locator('#approve').click()
  page.locator('#issue').click()
  code=page.locator('#demoCode').inner_text().split(': ')[1]
  page.locator('#unlock input').fill('ERRADA')
  page.locator('#unlock button').click()
  assert 'bloqueada' in page.locator('#message').inner_text()
  page.locator('#unlock input').fill(code)
  page.locator('#unlock button').click()
 assert page.get_by_role('heading',name='Exercício de demonstração concluído').is_visible()
 page.reload()
 assert page.get_by_role('heading',name='Exercício de demonstração concluído').is_visible()
 assert not errors,errors
 browser.close()
 print(json.dumps({'status':'aprovado','abertura':'HTML no Chromium via HTTP local de teste','fases':6,'senha_incorreta':'bloqueada','hash':'conferido no navegador','persistencia':'verificada','erros_javascript':errors},ensure_ascii=False))

server.shutdown();server.server_close()
