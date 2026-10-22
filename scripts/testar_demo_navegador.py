"""Valida a prévia pública; avaliações e senhas não são simuladas no cliente."""
import json
import threading
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('http://127.0.0.1:'+str(server.server_port)+'/index.html')
  page.get_by_role('button',name='Ver portal do aluno',exact=True).click()
  assert page.locator('#screenButtons button').count()==7
  for button in page.locator('#screenButtons button').all():
   button.click();assert page.locator('#screen').evaluate('(img)=>img.complete && img.naturalWidth>0')
  page.get_by_role('button',name='Ver portal do professor',exact=True).click()
  assert page.locator('#screenButtons button').count()==4
  for button in page.locator('#screenButtons button').all():
   button.click();assert page.locator('#screen').evaluate('(img)=>img.complete && img.naturalWidth>0')
  assert page.locator('form').count()==0
  assert not errors,errors
  browser.close()
 print(json.dumps({'status':'passed','telas_aluno':7,'telas_professor':4,'autoaprovacao':False},ensure_ascii=False))
finally:server.shutdown();server.server_close()
