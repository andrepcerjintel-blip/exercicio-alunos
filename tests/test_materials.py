import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import http.cookiejar
import zipfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
import integrar_kit

class Materials(unittest.TestCase):
 def setUp(self):
  self.old=app.DATA;self.tmp=tempfile.TemporaryDirectory();app.DATA=Path(self.tmp.name)
  self.report=integrar_kit.integrate()
  self.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.App)
  threading.Thread(target=self.server.serve_forever,daemon=True).start()
  self.url='http://127.0.0.1:'+str(self.server.server_port)
  self.teacher=self.client()
  pw=(app.DATA/'acesso-inicial.txt').read_text().split('Senha: ')[1].strip()
  self.call(self.teacher,'login',{'name':'instrutor','password':pw})
  self.a=self.client();self.b=self.client()
  for c,name in [(self.a,'Alfa'),(self.b,'Bravo')]:
   self.call(c,'register',{'name':'Aluno '+name,'team':name,'password':'pessoal-12345','team_code':'equipe-12345'})
   self.call(c,'login',{'name':'Aluno '+name,'password':'pessoal-12345'})
 def tearDown(self):
  self.server.shutdown();self.server.server_close();app.DATA=self.old;self.tmp.cleanup()
 def client(self):return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def get(self,c,path):
  try:
   with c.open(self.url+path) as r:return r.status,r.read()
  except urllib.error.HTTPError as e:return e.code,e.read()
 def state(self,c):return json.loads(self.get(c,'/api/state')[1])
 def call(self,c,route,data,status=200):
  csrf=self.state(c).get('csrf','') if route not in ['login','register'] else ''
  req=urllib.request.Request(self.url+'/api/'+route,json.dumps(data).encode(),headers={'Content-Type':'application/json','X-CSRF':csrf})
  try:
   with c.open(req) as r:actual,body=r.status,r.read()
  except urllib.error.HTTPError as e:actual,body=e.code,e.read()
  self.assertEqual(actual,status,body.decode())
  return json.loads(body) if body else {}
 def advance(self,c):
  st=self.state(c)
  if st['phase']==1:
   for line in (app.ROOT/'02_PROVAS_INICIAIS_ALUNOS/SHA256.txt').read_text().splitlines():
    value,name=line.split(maxsplit=1);self.call(c,'hash',{'name':name,'sha256':value})
  self.call(c,'submit',{'body':'Produto documentado desta fase'})
  delivery=self.state(c)['deliveries'][-1]
  self.call(self.teacher,'review',{'id':delivery['id'],'status':'approved'})
  name=st['user']['team'];team=next(x for x in self.state(self.teacher)['groups'] if x['name']==name)
  gate=self.call(self.teacher,'gate',{'team_id':team['id']})
  self.call(c,'unlock',{'code':gate['code']})
 def material(self,code):return next(x for x in self.state(self.teacher)['materials'] if x['code']==code)
 def test_catalog_integrity_and_reimport(self):
  self.assertEqual(self.report['verified_files'],30);self.assertEqual(self.report['materials'],21)
  before=len(self.state(self.teacher)['materials']);integrar_kit.integrate()
  self.assertEqual(len(self.state(self.teacher)['materials']),before)
  for m in self.state(self.teacher)['materials']:
   status,raw=self.get(self.teacher,'/material/'+str(m['id']));self.assertEqual(status,200)
   if m['kind']=='response':
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
     self.assertTrue(z.namelist());self.assertFalse(any('LEIA_PROFESSOR' in n or 'GABARITO' in n for n in z.namelist()))
 def test_future_and_teacher_materials_are_blocked(self):
  codes={m['code'] for m in self.state(self.a)['materials']};self.assertEqual(codes,{'FASE-01'})
  for code in ['FASE-02','A08','PROFESSOR','RESERVADO-Guia_Instrutor_LUA']:
   m=self.material(code)
   self.assertEqual(self.get(self.a,'/material/'+str(m['id']))[0],403)
   self.assertEqual(self.get(self.a,'/asset/'+str(m['id'])+'/imagens/A08.png')[0],403)
  first=self.material('FASE-01')
  status,raw=self.get(self.a,'/asset/'+str(first['id'])+'/anexos/A01_Denuncia_Inicial.png')
  self.assertEqual(status,200);self.assertTrue(raw.startswith(b'\x89PNG'))
  private=self.material('PROFESSOR');self.call(self.teacher,'release',{'id':private['id']},400)
  self.advance(self.a)
  self.assertIn('FASE-02',{m['code'] for m in self.state(self.a)['materials']})
  self.assertNotIn('FASE-02',{m['code'] for m in self.state(self.b)['materials']})
 def test_responses_require_own_request_and_team_grant(self):
  self.call(self.a,'request',{'recipient':'Discord','body':'Pedido'},400)
  for _ in range(3):self.advance(self.a);self.advance(self.b)
  self.call(self.a,'request',{'recipient':'Discord','body':'Pedido fundamentado sobre identificador ROOK, período e fuso definidos.'})
  self.call(self.b,'request',{'recipient':'Discord','body':'Pedido da equipe Bravo'})
  t=self.state(self.teacher);alpha=next(g for g in t['groups'] if g['name']=='Alfa');bravo=next(g for g in t['groups'] if g['name']=='Bravo')
  req=self.state(self.a)['requests'][-1]['id'];response=self.material('A08')
  self.call(self.teacher,'release',{'id':response['id'],'team_id':alpha['id']},400)
  self.call(self.teacher,'release',{'id':response['id'],'team_id':bravo['id'],'request_id':req},400)
  self.call(self.teacher,'release',{'id':response['id'],'team_id':alpha['id'],'request_id':req})
  self.assertEqual(self.get(self.a,'/material/'+str(response['id']))[0],200)
  self.assertEqual(self.get(self.b,'/material/'+str(response['id']))[0],403)
  self.assertEqual(len(self.state(self.b)['requests']),1)
  later=self.material('A15');self.call(self.teacher,'release',{'id':later['id'],'team_id':alpha['id']},400)
  self.advance(self.a);self.call(self.teacher,'release',{'id':later['id'],'team_id':alpha['id']})
  self.assertEqual(self.get(self.a,'/material/'+str(later['id']))[0],200)
 def test_hash_registration_correct_and_incorrect(self):
  self.call(self.a,'hash',{'name':'anexos/A02.png','sha256':'0'*64},400)
  self.advance(self.a)
  self.call(self.a,'hash',{'name':'anexos/A02.png','sha256':'0'*64})
  value=next(line.split()[0] for line in (app.ROOT/'02_PROVAS_INICIAIS_ALUNOS/SHA256.txt').read_text().splitlines() if 'anexos/A02.png' in line)
  self.call(self.a,'hash',{'name':'anexos/A02.png','sha256':value})
  hashes=self.state(self.a)['hashes'];self.assertEqual([h['matched'] for h in hashes],[0,1])
  self.assertEqual(self.state(self.b)['hashes'],[])
  self.call(self.a,'hash',{'name':'fora-do-inventario','sha256':value},400)

if __name__=='__main__':unittest.main()
