import json, sqlite3, secrets, hashlib, hmac, time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'.runtime'
DATA.mkdir(exist_ok=True)
PHASES=['Denúncia','Recebimento e preservação','Triagem e pedidos','Respostas e diligências','Atualização posterior','Consolidação']
def db():
 c=sqlite3.connect(DATA/'lua.db');c.row_factory=sqlite3.Row;return c
def digest(p,s):return hashlib.scrypt(p.encode(),salt=bytes.fromhex(s),n=16384,r=8,p=1).hex()
def init():
 with db() as c:
  c.executescript('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT UNIQUE,role TEXT,salt TEXT,password TEXT);CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY,phase INTEGER);INSERT OR IGNORE INTO state VALUES(1,0);CREATE TABLE IF NOT EXISTS deliveries(id INTEGER PRIMARY KEY,user_id INTEGER,phase INTEGER,body TEXT,status TEXT,feedback TEXT,created REAL);CREATE TABLE IF NOT EXISTS sessions(token TEXT,uid INTEGER,csrf TEXT,expires REAL);CREATE TABLE IF NOT EXISTS materials(id INTEGER PRIMARY KEY,title TEXT,phase INTEGER,path TEXT UNIQUE,sha256 TEXT,released INTEGER DEFAULT 0);CREATE TABLE IF NOT EXISTS gates(team_id INTEGER,phase INTEGER,salt TEXT,hash TEXT,failures INTEGER DEFAULT 0,blocked REAL DEFAULT 0,PRIMARY KEY(team_id,phase));CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor INTEGER,action TEXT,created REAL);')
  columns={r['name'] for r in c.execute('PRAGMA table_info(users)')}
  for name,definition in [('team_id','INTEGER'),('phase','INTEGER DEFAULT 0'),('completed','INTEGER DEFAULT 0')]:
   if name not in columns:c.execute(f'ALTER TABLE users ADD COLUMN {name} {definition}')
  c.execute("UPDATE users SET team_id=id WHERE role='group' AND team_id IS NULL")
  if not c.execute('SELECT 1 FROM users').fetchone():
   p=secrets.token_urlsafe(18);s=secrets.token_hex(16);c.execute('INSERT INTO users(name,role,salt,password) VALUES(?,?,?,?)',('instrutor','instructor',s,digest(p,s)))
   f=DATA/'acesso-inicial.txt';f.write_text('Usuário: instrutor\nSenha: '+p+'\n');f.chmod(0o600)
class App(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,status,obj,kind='application/json'):
  b=json.dumps(obj,ensure_ascii=False).encode() if kind=='application/json' else obj
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b)
 def user(self,c):
  cookie=SimpleCookie(self.headers.get('Cookie',''));t=cookie['lua'].value if 'lua' in cookie else ''
  return c.execute('SELECT u.*,s.csrf FROM users u JOIN sessions s ON u.id=s.uid WHERE s.token=? AND s.expires>?',(t,time.time())).fetchone()
 def do_GET(self):
  if self.path in ['/','/app.js','/style.css']:
   p=ROOT/'static'/('index.html' if self.path=='/' else self.path[1:]);return self.send(200,p.read_bytes(),{'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css'}[p.suffix[1:]])
  with db() as c:
   u=self.user(c)
   if not u:return self.send(401,{'error':'Entre com seu acesso'})
   if self.path.startswith('/material/'):
    try: m=c.execute('SELECT * FROM materials WHERE id=?',(int(self.path.split('/')[-1]),)).fetchone()
    except ValueError: m=None
    phase=c.execute('SELECT phase FROM users WHERE id=?',(u['team_id'] or u['id'],)).fetchone()[0]
    if not m or (u['role']!='instructor' and (not m['released'] or m['phase']>phase)):return self.send(403,{'error':'Material reservado'})
    return self.send(200,Path(m['path']).read_bytes(),'application/octet-stream')
   if self.path!='/api/state':return self.send(404,{'error':'Não encontrado'})
   teacher=u['role']=='instructor'
   ds=c.execute('SELECT d.*,u.name FROM deliveries d JOIN users u ON u.id=d.user_id'+('' if teacher else ' WHERE d.user_id=?'),() if teacher else (u['team_id'] or u['id'],)).fetchall()
   groups=[dict(x) for x in c.execute("SELECT id,name,phase,completed FROM users WHERE role='group'")] if teacher else []
   self.send(200,dict(user={'name':u['name'],'role':u['role'],'team':(c.execute('SELECT name FROM users WHERE id=?',(u['team_id'],)).fetchone()[0] if u['team_id'] else None)},csrf=u['csrf'],phase=c.execute('SELECT phase FROM users WHERE id=?',(u['team_id'] or u['id'],)).fetchone()[0],completed=bool(c.execute('SELECT completed FROM users WHERE id=?',(u['team_id'] or u['id'],)).fetchone()[0]),scenario=json.loads((ROOT/'roteiro.json').read_text())[c.execute('SELECT phase FROM users WHERE id=?',(u['team_id'] or u['id'],)).fetchone()[0]],phases=PHASES,materials=[dict(x) for x in c.execute('SELECT id,title,phase,released FROM materials') if teacher or (x['released'] and x['phase']<=c.execute('SELECT phase FROM users WHERE id=?',(u['team_id'] or u['id'],)).fetchone()[0])],groups=groups,deliveries=[dict(x) for x in ds]))
 def do_POST(self):
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n>1000000:return self.send(413,{'error':'Entrega muito grande'})
   data=json.loads(self.rfile.read(n))
   with db() as c:
    if self.path=='/api/register':
     c.execute('BEGIN IMMEDIATE')
     name=data['name'].strip();team=data['team'].strip();pw=data['password'];code=data['team_code']
     if not name or not team or len(pw)<10 or len(code)<10:raise ValueError('Informe nome, equipe e senhas de ao menos dez caracteres')
     g=c.execute("SELECT * FROM users WHERE name=? AND role='group'",(team,)).fetchone()
     if g:
      if not hmac.compare_digest(digest(code,g['salt']),g['password']):raise ValueError('Código de equipe inválido')
      tid=g['id']
     else:
      salt=secrets.token_hex(16);cur=c.execute('INSERT INTO users(name,role,salt,password) VALUES(?,?,?,?)',(team,'group',salt,digest(code,salt)));tid=cur.lastrowid
      c.execute('UPDATE users SET team_id=id WHERE id=?',(tid,))
     salt=secrets.token_hex(16);c.execute('INSERT INTO users(name,role,salt,password,team_id) VALUES(?,?,?,?,?)',(name,'student',salt,digest(pw,salt),tid))
     c.execute('INSERT INTO audit(actor,action,created) VALUES(?,?,?)',(tid,'registration',time.time()))
     c.commit();return self.send(200,{'ok':True})
    if self.path=='/api/login':
     u=c.execute('SELECT * FROM users WHERE name=?',(data['name'],)).fetchone()
     if not u or not hmac.compare_digest(digest(data['password'],u['salt']),u['password']):return self.send(401,{'error':'Acesso inválido'})
     t=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(t,u['id'],secrets.token_urlsafe(32),time.time()+28800));c.commit()
     self.send_response(200);self.send_header('Set-Cookie',f'lua={t}; HttpOnly; SameSite=Strict; Path=/');self.end_headers();return
    u=self.user(c)
    if not u:return self.send(401,{'error':'Entre com seu acesso'})
    if not hmac.compare_digest(self.headers.get('X-CSRF',''),u['csrf']):return self.send(403,{'error':'Sessão inválida'})
    teacher=u['role']=='instructor';tid=u['team_id'] or u['id'];phase=c.execute('SELECT phase FROM users WHERE id=?',(tid,)).fetchone()[0]
    if self.path=='/api/submit' and not teacher:
     if c.execute('SELECT completed FROM users WHERE id=?',(tid,)).fetchone()[0]:raise ValueError('Exercício concluído')
     if not data['body'].strip():raise ValueError('Preencha a entrega')
     c.execute('INSERT INTO deliveries(user_id,phase,body,status,feedback,created) VALUES(?,?,?,?,?,?)',(tid,phase,data['body'],'submitted','',time.time()))
    elif self.path=='/api/unlock' and not teacher:
     c.execute('BEGIN IMMEDIATE')
     if c.execute('SELECT completed FROM users WHERE id=?',(tid,)).fetchone()[0]:raise ValueError('Exercício já concluído')
     latest=c.execute('SELECT status FROM deliveries WHERE user_id=? AND phase=? ORDER BY id DESC LIMIT 1',(tid,phase)).fetchone()
     if not latest or latest['status']!='approved':raise ValueError('A última entrega precisa estar aprovada')
     gate=c.execute('SELECT * FROM gates WHERE team_id=? AND phase=?',(tid,phase)).fetchone()
     if not gate:raise ValueError('Solicite a senha desta etapa ao instrutor')
     if gate['blocked']>time.time():return self.send(429,{'error':'Aguarde cinco minutos antes de tentar novamente'})
     if not hmac.compare_digest(digest(data.get('code',''),gate['salt']),gate['hash']):
      failures=gate['failures']+1;c.execute('UPDATE gates SET failures=?,blocked=? WHERE team_id=? AND phase=?',(failures,time.time()+300 if failures%5==0 else 0,tid,phase));c.commit()
      return self.send(400,{'error':'Senha da fase inválida'})
     if phase<5:c.execute('UPDATE users SET phase=phase+1 WHERE id=?',(tid,))
     else:c.execute('UPDATE users SET completed=1 WHERE id=?',(tid,))
     c.execute('DELETE FROM gates WHERE team_id=? AND phase=?',(tid,phase))
    elif not teacher:return self.send(403,{'error':'Acesso exclusivo do instrutor'})
    elif self.path=='/api/group':
     if len(data['password'])<10:raise ValueError('Senha deve ter 10 caracteres ou mais')
     s=secrets.token_hex(16);cur=c.execute('INSERT INTO users(name,role,salt,password) VALUES(?,?,?,?)',(data['name'],'group',s,digest(data['password'],s)));c.execute('UPDATE users SET team_id=id WHERE id=?',(cur.lastrowid,))
    elif self.path=='/api/release':
     m=c.execute('SELECT * FROM materials WHERE id=?',(data['id'],)).fetchone()
     if not m:raise ValueError('Material inexistente')
     c.execute('UPDATE materials SET released=1 WHERE id=?',(m['id'],))
    elif self.path=='/api/gate':
     c.execute('BEGIN IMMEDIATE')
     group=c.execute("SELECT * FROM users WHERE id=? AND role='group'",(data['team_id'],)).fetchone()
     if not group or group['completed']:raise ValueError('Equipe indisponível')
     latest=c.execute('SELECT status FROM deliveries WHERE user_id=? AND phase=? ORDER BY id DESC LIMIT 1',(group['id'],group['phase'])).fetchone()
     if not latest or latest['status']!='approved':raise ValueError('Aprove a última entrega antes de emitir a senha')
     code=secrets.token_hex(5).upper();salt=secrets.token_hex(16)
     c.execute('INSERT OR REPLACE INTO gates(team_id,phase,salt,hash) VALUES(?,?,?,?)',(group['id'],group['phase'],salt,digest(code,salt)))
     c.execute('INSERT INTO audit(actor,action,created) VALUES(?,?,?)',(u['id'],'issue_gate',time.time()));c.commit()
     return self.send(200,{'code':code,'team':group['name'],'phase':group['phase']+1})
    elif self.path=='/api/review':
     c.execute('BEGIN IMMEDIATE')
     if data['status'] not in ['approved','correction']:raise ValueError('Situação inválida')
     delivery=c.execute('SELECT * FROM deliveries WHERE id=?',(data['id'],)).fetchone()
     if not delivery:raise ValueError('Entrega inexistente')
     group=c.execute('SELECT * FROM users WHERE id=?',(delivery['user_id'],)).fetchone()
     latest=c.execute('SELECT id FROM deliveries WHERE user_id=? AND phase=? ORDER BY id DESC LIMIT 1',(group['id'],group['phase'])).fetchone()
     if delivery['phase']!=group['phase'] or not latest or latest['id']!=delivery['id']:raise ValueError('Avalie apenas a última entrega da fase atual')
     c.execute('UPDATE deliveries SET status=?,feedback=? WHERE id=?',(data['status'],data.get('feedback',''),data['id']))
     c.execute('DELETE FROM gates WHERE team_id=? AND phase=?',(group['id'],group['phase']))
    elif self.path=='/api/advance':
     raise ValueError('A progressão agora é por equipe, após aprovação da entrega')
    else:return self.send(404,{'error':'Não encontrado'})
    c.execute('INSERT INTO audit(actor,action,created) VALUES(?,?,?)',(u['id'],self.path,time.time()))
   self.send(200,{'ok':True})
  except (ValueError,KeyError,TypeError,sqlite3.IntegrityError) as e:self.send(400,{'error':str(e)})
if __name__=='__main__':
 init();ThreadingHTTPServer(('127.0.0.1',8000),App).serve_forever()
