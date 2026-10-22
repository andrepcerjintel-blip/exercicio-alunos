import http.cookiejar
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
import integrar_kit

class PortalCase(unittest.TestCase):
 def setUp(self):
  self.old_data=app.DATA;self.tmp=tempfile.TemporaryDirectory();app.DATA=Path(self.tmp.name)
  self.report=integrar_kit.integrate()
  self.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.App)
  threading.Thread(target=self.server.serve_forever,daemon=True).start()
  self.url='http://127.0.0.1:'+str(self.server.server_port)
  self.teacher=self.client();self.a=self.client();self.b=self.client();self.a2=self.client()
  password=(app.DATA/'acesso-inicial.txt').read_text().split('Senha: ')[1].strip()
  self.post(self.teacher,'login',{'name':'instrutor','password':password})
  for c,name,team in [(self.a,'Ana','Alfa'),(self.a2,'Bruno','Alfa'),(self.b,'Carla','Bravo')]:
   self.post(c,'register',{'name':name,'team':team,'password':'senha-pessoal-123','team_code':'codigo-equipe-123'})
   self.post(c,'login',{'name':name,'password':'senha-pessoal-123'})
 def tearDown(self):
  self.server.shutdown();self.server.server_close();app.DATA=self.old_data;self.tmp.cleanup()
 def client(self):return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def get(self,c,path):
  try:
   with c.open(self.url+path) as r:return r.status,r.read()
  except urllib.error.HTTPError as e:return e.code,e.read()
 def state(self,c):return json.loads(self.get(c,'/api/state')[1])
 def post(self,c,route,data,status=200):
  csrf=self.state(c)['csrf'] if route not in ['login','register'] else ''
  req=urllib.request.Request(self.url+'/api/'+route,json.dumps(data).encode(),headers={'Content-Type':'application/json','X-CSRF':csrf})
  try:
   with c.open(req) as r:actual,raw=r.status,r.read()
  except urllib.error.HTTPError as e:actual,raw=e.code,e.read()
  self.assertEqual(actual,status,raw.decode())
  return json.loads(raw) if raw else {}
 def team(self,c):return next(g for g in self.state(self.teacher)['groups'] if g['name']==self.state(c)['user']['team'])
 def material(self,code):return next(m for m in self.state(self.teacher)['materials'] if m['code']==code)
 def hashes(self,c):
  for r in self.state(self.teacher)['hash_references']:
   if r['name'] in self.state(c)['inventory']:self.post(c,'hash',{'name':r['name'],'sha256':r['sha256']})
 def request(self,c,recipient='Discord',body='Pedido simulado com objeto, intervalo, fundamento e autorização para avaliação.'):
  self.post(c,'request',{'recipient':recipient,'body':body})
  return self.state(c)['requests'][-1]
 def approve_request(self,r):self.post(self.teacher,'request-review',{'id':r['id'],'status':'approved','feedback':'Texto avaliado individualmente para esta plataforma.'})
 def release(self,c,code,request=None):
  data={'id':self.material(code)['id'],'team_id':self.team(c)['id']}
  if request:data['request_id']=request['id']
  self.post(self.teacher,'release',data)
 def analysis(self,c,code='A08',value='SIM-CONTA-TESTE'):
  data={'response_id':self.material(code)['id'],'identifier_type':'ID de conta','identifier_value':value,'findings':'O retorno vincula um registro a uma conta; avaliar escopo e origem.','limits':'Conta e titularidade não comprovam autoria da conduta.','next_step':'Solicitar a diligência justificada para confirmar o vínculo.','next_recipient':'Equipe territorial','legal_basis':'Fundamentação e autorização a serem avaliadas pelo instrutor.'}
  self.post(c,'analysis',data)
  return self.state(c)['analyses'][-1]
 def pericia(self,c):
  request=self.request(c,'Perícia','Pedido de exame e arrecadação no local, delimitado e fundamentado para avaliação.')
  self.approve_request(request);self.release(c,'A16',request);self.release(c,'LOCAL-A21-A22',request);self.hashes(c)
  for code in ['A16','LOCAL-A21-A22']:
   item=self.analysis(c,code,value='SIM-IDENTIFICADOR-'+code)
   self.post(self.teacher,'analysis-review',{'id':item['id'],'status':'approved'})
 def advance(self,c):
  phase=self.state(c)['phase']
  if phase==1:self.hashes(c)
  if phase==2:
   r=self.request(c);self.approve_request(r)
  if phase==3:
   r=next(r for r in self.state(c)['requests'] if r['recipient']=='Discord');self.release(c,'A08',r)
   item=self.analysis(c);self.post(self.teacher,'analysis-review',{'id':item['id'],'status':'approved'});self.pericia(c)
  if phase==4:
   r=self.request(c,'NetSul Fibra');self.approve_request(r)
  self.post(c,'submit',{'body':'Entrega nominal de teste para verificar a fase '+str(phase+1)})
  delivery=self.state(c)['deliveries'][-1]
  self.post(self.teacher,'review',{'id':delivery['id'],'status':'approved'})
  gate=self.post(self.teacher,'gate',{'team_id':self.team(c)['id']})
  self.post(c,'unlock',{'code':gate['code']})
