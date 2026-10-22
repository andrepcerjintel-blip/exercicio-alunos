import unittest, tempfile, threading, json, urllib.request, urllib.error, http.cookiejar, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
class Workflow(unittest.TestCase):
 def test_team_progression(self):
  with tempfile.TemporaryDirectory() as tmp:
   app.DATA=Path(tmp);app.init()
   server=app.ThreadingHTTPServer(('127.0.0.1',0),app.App)
   threading.Thread(target=server.serve_forever,daemon=True).start()
   url='http://127.0.0.1:'+str(server.server_port)
   def client():return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
   def post(client,path,data,csrf=''):
    req=urllib.request.Request(url+'/api/'+path,json.dumps(data).encode(),headers={'Content-Type':'application/json','X-CSRF':csrf})
    try:
     with client.open(req) as r:return r.status
    except urllib.error.HTTPError as e:return e.code
   def state(c):return json.load(c.open(url+'/api/state'))
   try:
    t=client();pw=(app.DATA/'acesso-inicial.txt').read_text().split('Senha: ')[1].strip()
    self.assertEqual(post(t,'login',{'name':'instrutor','password':pw}),200);csrf=state(t)['csrf']
    for name in ['Alfa','Bravo']:self.assertEqual(post(t,'group',{'name':name,'password':'senha-teste-123'},csrf),200)
    self.assertEqual(post(t,'advance',{},csrf),400)
    a=client();b=client()
    for c,name in [(a,'Alfa'),(b,'Bravo')]:
     self.assertEqual(post(c,'login',{'name':name,'password':'senha-teste-123'}),200)
     self.assertEqual(post(c,'submit',{'body':'Entrega '+name},state(c)['csrf']),200)
    self.assertEqual(len(state(a)['deliveries']),1)
    self.assertEqual(post(a,'advance',{},state(a)['csrf']),403)
    self.assertEqual(post(t,'advance',{}),403)
    def issue(team):
     req=urllib.request.Request(url+'/api/gate',json.dumps({'team_id':team}).encode(),headers={'Content-Type':'application/json','X-CSRF':csrf})
     return json.load(t.open(req))['code']
    teams=state(t)['groups']
    self.assertEqual(post(t,'gate',{'team_id':teams[0]['id']},csrf),400)
    self.assertEqual(post(a,'unlock',{'code':'qualquer'},state(a)['csrf']),400)
    ds=state(t)['deliveries']
    self.assertEqual(post(t,'review',{'id':ds[0]['id'],'status':'approved'},csrf),200)
    self.assertEqual(post(t,'advance',{},csrf),400)
    self.assertEqual(state(a)['phase'],0)
    old=issue(teams[0]['id']);code=issue(teams[0]['id'])
    self.assertEqual(post(a,'unlock',{'code':old},state(a)['csrf']),400)
    self.assertEqual(post(b,'unlock',{'code':code},state(b)['csrf']),400)
    self.assertEqual(post(a,'unlock',{'code':code},state(a)['csrf']),200)
    self.assertEqual(post(a,'unlock',{'code':code},state(a)['csrf']),400)
    self.assertEqual(state(a)['phase'],1);self.assertEqual(state(b)['phase'],0)
    self.assertEqual(post(t,'review',{'id':ds[1]['id'],'status':'approved'},csrf),200)
    self.assertEqual(post(t,'advance',{},csrf),400)
    code=issue(teams[1]['id'])
    self.assertEqual(post(b,'unlock',{'code':'incorreta'},state(b)['csrf']),400)
    self.assertEqual(post(b,'unlock',{'code':code},state(b)['csrf']),200)
    self.assertEqual(state(a)['phase'],1);self.assertEqual(state(b)['phase'],1)
    student=client()
    self.assertEqual(post(student,'register',{'name':'Aluno Um','team':'Alfa','password':'pessoal-12345','team_code':'errado-12345'}),400)
    self.assertEqual(post(student,'register',{'name':'Aluno Um','team':'Alfa','password':'pessoal-12345','team_code':'senha-teste-123'}),200)
    self.assertEqual(post(student,'login',{'name':'Aluno Um','password':'pessoal-12345'}),200)
    self.assertEqual(state(student)['phase'],1)
    self.assertEqual(len(state(student)['deliveries']),1)
    self.assertEqual(post(student,'submit',{'body':'Entrega compartilhada'},state(student)['csrf']),200)
    self.assertEqual(len(state(a)['deliveries']),2)
    self.assertEqual(len(state(b)['deliveries']),1)
    self.assertEqual(post(t,'review',{'id':ds[0]['id'],'status':'approved'},csrf),400)
    newcomer=client()
    self.assertEqual(post(newcomer,'register',{'name':'Aluno Dois','team':'Charlie','password':'pessoal-12345','team_code':'equipe-12345'}),200)
    self.assertEqual(post(newcomer,'login',{'name':'Aluno Dois','password':'pessoal-12345'}),200)
    self.assertEqual(state(newcomer)['phase'],0)
    # Complete the remaining phases, each requiring approval AND its own code.
    for phase in range(1,6):
     self.assertEqual(post(a,'submit',{'body':'Dossiê fase '+str(phase)},state(a)['csrf']),200)
     latest=state(a)['deliveries'][-1]
     self.assertEqual(post(t,'review',{'id':latest['id'],'status':'approved'},csrf),200)
     self.assertEqual(state(a)['phase'],phase)
     code=issue(teams[0]['id'])
     self.assertEqual(post(a,'unlock',{'code':code},state(a)['csrf']),200)
    self.assertTrue(state(a)['completed'])
    self.assertEqual(state(a)['phase'],5)
    self.assertEqual(post(a,'submit',{'body':'Outra'},state(a)['csrf']),400)
    self.assertEqual(post(a,'unlock',{'code':code},state(a)['csrf']),400)
   finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
