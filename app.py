import json, sqlite3, secrets, hashlib, hmac, time, mimetypes, os, zipfile
from urllib.parse import unquote
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('LUA_DATA', ROOT/'.runtime'))
DATA.mkdir(exist_ok=True)
PHASES=['Denúncia','Recebimento e preservação','Triagem e pedidos','Respostas e diligências','Atualização posterior','Consolidação']
def db():
 c=sqlite3.connect(DATA/'lua.db');c.row_factory=sqlite3.Row;return c
def digest(p,s):return hashlib.scrypt(p.encode(),salt=bytes.fromhex(s),n=16384,r=8,p=1).hex()
def init():
 with db() as c:
  c.executescript('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT UNIQUE,role TEXT,salt TEXT,password TEXT);CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY,phase INTEGER);INSERT OR IGNORE INTO state VALUES(1,0);CREATE TABLE IF NOT EXISTS deliveries(id INTEGER PRIMARY KEY,user_id INTEGER,phase INTEGER,body TEXT,status TEXT,feedback TEXT,created REAL);CREATE TABLE IF NOT EXISTS sessions(token TEXT,uid INTEGER,csrf TEXT,expires REAL);CREATE TABLE IF NOT EXISTS materials(id INTEGER PRIMARY KEY,title TEXT,phase INTEGER,path TEXT UNIQUE,sha256 TEXT,released INTEGER DEFAULT 0);CREATE TABLE IF NOT EXISTS gates(team_id INTEGER,phase INTEGER,salt TEXT,hash TEXT,failures INTEGER DEFAULT 0,blocked REAL DEFAULT 0,PRIMARY KEY(team_id,phase));CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor INTEGER,action TEXT,created REAL);')
  c.executescript('''CREATE TABLE IF NOT EXISTS material_grants(material_id INTEGER,team_id INTEGER,request_id INTEGER,PRIMARY KEY(material_id,team_id));
CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY,team_id INTEGER,actor_id INTEGER,phase INTEGER,recipient TEXT,body TEXT,created REAL);
CREATE TABLE IF NOT EXISTS hash_records(id INTEGER PRIMARY KEY,team_id INTEGER,actor_id INTEGER,name TEXT,sha256 TEXT,matched INTEGER,created REAL);''')
  material_columns={r['name'] for r in c.execute('PRAGMA table_info(materials)')}
  for name,definition in [('kind',"TEXT DEFAULT 'manual'"),('code',"TEXT DEFAULT ''"),('condition',"TEXT DEFAULT ''"),('filename',"TEXT DEFAULT ''")]:
   if name not in material_columns:c.execute(f'ALTER TABLE materials ADD COLUMN {name} {definition}')
  columns={r['name'] for r in c.execute('PRAGMA table_info(users)')}
  for name,definition in [('team_id','INTEGER'),('phase','INTEGER DEFAULT 0'),('completed','INTEGER DEFAULT 0')]:
   if name not in columns:c.execute(f'ALTER TABLE users ADD COLUMN {name} {definition}')
  c.execute("UPDATE users SET team_id=id WHERE role='group' AND team_id IS NULL")
  if not c.execute('SELECT 1 FROM users').fetchone():
   p=secrets.token_urlsafe(18);s=secrets.token_hex(16);c.execute('INSERT INTO users(name,role,salt,password) VALUES(?,?,?,?)',('instrutor','instructor',s,digest(p,s)))
   f=DATA/'acesso-inicial.txt';f.write_text('Usuário: instrutor\nSenha: '+p+'\n');f.chmod(0o600)
def visible(c,m,u):
 if u['role']=='instructor':return True
 if m['kind']=='teacher':return False
 tid=u['team_id'] or u['id']
 phase=c.execute('SELECT phase FROM users WHERE id=?',(tid,)).fetchone()[0]
 if m['phase']>phase:return False
 if m['kind']=='response':return bool(c.execute('SELECT 1 FROM material_grants WHERE material_id=? AND team_id=?',(m['id'],tid)).fetchone())
 return bool(m['released'])

def missing_hashes(c,tid):
 manifest=ROOT/'02_PROVAS_INICIAIS_ALUNOS/SHA256.txt'
 names=[line.split(maxsplit=1)[1].lstrip('*') for line in manifest.read_text().splitlines() if len(line.split(maxsplit=1))==2]
 records={r['name']:bool(r['matched']) for r in c.execute('SELECT name,matched FROM hash_records WHERE team_id=? ORDER BY id',(tid,))}
 return [name for name in names if not records.get(name)]

def check_hashes(c,tid,phase):
 if phase==1:
  missing=missing_hashes(c,tid)
  if missing:raise ValueError(f'Registre hashes correspondentes ao manifesto: {len(missing)} arquivos pendentes ou divergentes')

def state_for(c,u):
 teacher=u['role']=='instructor';tid=u['team_id'] or u['id']
 group=c.execute('SELECT * FROM users WHERE id=?',(tid,)).fetchone()
 ds=[dict(x) for x in c.execute('SELECT d.*,u.name FROM deliveries d JOIN users u ON u.id=d.user_id'+('' if teacher else ' WHERE d.user_id=?')+' ORDER BY d.id',() if teacher else (tid,))]
 groups=[dict(x) for x in c.execute("SELECT id,name,phase,completed FROM users WHERE role='group'")] if teacher else []
 materials=[]
 for m in c.execute('SELECT * FROM materials ORDER BY phase,id').fetchall():
  if visible(c,m,u):
   item={k:m[k] for k in ['id','title','phase','released','kind','code','filename']}
   if teacher:item['condition']=m['condition'];item['teams']=[x[0] for x in c.execute('SELECT team_id FROM material_grants WHERE material_id=?',(m['id'],))]
   if m['kind']=='phase':
    with zipfile.ZipFile(m['path']) as z:item['previews']=[name for name in z.namelist() if Path(name).suffix.lower() in ['.png','.mp4']]
   materials.append(item)
 requests=[dict(x) for x in c.execute('SELECT r.*,u.name FROM requests r JOIN users u ON u.id=r.team_id'+('' if teacher else ' WHERE r.team_id=?')+' ORDER BY r.id',() if teacher else (tid,))]
 hashes=[dict(x) for x in c.execute('SELECT * FROM hash_records'+('' if teacher else ' WHERE team_id=?')+' ORDER BY id',() if teacher else (tid,))]
 inventory=[]
 if group['phase']>=1 and not teacher:
  inventory=[line.split(maxsplit=1)[1].lstrip('*') for line in (ROOT/'02_PROVAS_INICIAIS_ALUNOS/SHA256.txt').read_text().splitlines() if len(line.split(maxsplit=1))==2]
 return dict(hash_pending=missing_hashes(c,tid) if not teacher and group['phase']>=1 else [],inventory=inventory,user={'name':u['name'],'role':u['role'],'team':group['name'] if not teacher else None},csrf=u['csrf'],phase=group['phase'],completed=bool(group['completed']),scenario=json.loads((ROOT/'roteiro.json').read_text())[group['phase']],phases=PHASES,materials=materials,groups=groups,deliveries=ds,requests=requests,hashes=hashes)

class App(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,status,obj,kind='application/json',filename=None):
  b=obj if isinstance(obj,bytes) else json.dumps(obj,ensure_ascii=False).encode()
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');
  if filename:self.send_header('Content-Disposition', 'attachment; filename="'+filename.replace('"','')+'"')
  self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(b)
 def user(self,c):
  cookie=SimpleCookie(self.headers.get('Cookie',''));t=cookie['lua'].value if 'lua' in cookie else ''
  return c.execute('SELECT u.*,s.csrf FROM users u JOIN sessions s ON u.id=s.uid WHERE s.token=? AND s.expires>?',(t,time.time())).fetchone()
 def do_GET(self):
  if self.path in ['/','/app.js','/style.css']:
   p=ROOT/'static'/('index.html' if self.path=='/' else self.path[1:]);return self.send(200,p.read_bytes(),{'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css'}[p.suffix[1:]])
  with db() as c:
   u=self.user(c)
   if not u:return self.send(401,{'error':'Entre com seu acesso'})
   if self.path.startswith('/asset/'):
    parts=self.path.split('/',3)
    try:m=c.execute('SELECT * FROM materials WHERE id=?',(int(parts[2]),)).fetchone()
    except (ValueError,IndexError):m=None
    if not m or not visible(c,m,u):return self.send(403,{'error':'Material reservado'})
    name=unquote(parts[3]) if len(parts)==4 else ''
    if Path(name).suffix.lower() not in ['.png','.jpg','.jpeg','.mp4','.pdf','.txt']:return self.send(404,{'error':'Prévia não disponível'})
    try:
     with zipfile.ZipFile(m['path']) as z:payload=z.read(name)
    except (KeyError,zipfile.BadZipFile):return self.send(404,{'error':'Arquivo não encontrado'})
    return self.send(200,payload,mimetypes.guess_type(name)[0] or 'application/octet-stream')
   if self.path.startswith('/material/'):
    try: m=c.execute('SELECT * FROM materials WHERE id=?',(int(self.path.split('/')[-1]),)).fetchone()
    except ValueError: m=None
    if not m or not visible(c,m,u):return self.send(403,{'error':'Material reservado'})
    path=Path(m['path'])
    if not path.is_file():return self.send(404,{'error':'Arquivo indisponível'})
    return self.send(200,path.read_bytes(),mimetypes.guess_type(path.name)[0] or 'application/octet-stream',m['filename'] or path.name)
   if self.path!='/api/state':return self.send(404,{'error':'Não encontrado'})
   self.send(200,state_for(c,u))
 def do_POST(self):
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n>1000000:return self.send(413,{'error':'Entrega muito grande'})
   data=json.loads(self.rfile.read(n))
   with db() as c:
    if self.path=='/api/logout':
     u=self.user(c)
     if not u or not hmac.compare_digest(self.headers.get('X-CSRF',''),u['csrf']):return self.send(403,{'error':'Sessão inválida'})
     c.execute('DELETE FROM sessions WHERE uid=?',(u['id'],));c.commit()
     self.send_response(200);self.send_header('Set-Cookie','lua=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict');self.end_headers();return
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
    if self.path=='/api/request' and not teacher:
     if phase<2 or phase>4:raise ValueError('Pedidos disponíveis nas fases 3, 4 e 5')
     if not data.get('recipient','').strip() or not data.get('body','').strip():raise ValueError('Informe destinatário e pedido fundamentado')
     c.execute('INSERT INTO requests(team_id,actor_id,phase,recipient,body,created) VALUES(?,?,?,?,?,?)',(tid,u['id'],phase,data['recipient'].strip(),data['body'].strip(),time.time()))
    elif self.path=='/api/hash' and not teacher:
     if phase<1:raise ValueError('Os arquivos ainda não foram recebidos')
     name=data.get('name','');value=data.get('sha256','').lower()
     if len(value)!=64 or any(ch not in '0123456789abcdef' for ch in value):raise ValueError('Informe SHA-256 válido')
     manifest=ROOT/'02_PROVAS_INICIAIS_ALUNOS'/'SHA256.txt'
     expected={line.split(maxsplit=1)[1].lstrip('*'):line.split(maxsplit=1)[0] for line in manifest.read_text().splitlines() if len(line.split(maxsplit=1))==2}
     if name not in expected:raise ValueError('Selecione um nome do inventário inicial')
     matched=hmac.compare_digest(expected[name],value)
     c.execute('INSERT INTO hash_records(team_id,actor_id,name,sha256,matched,created) VALUES(?,?,?,?,?,?)',(tid,u['id'],name,value,int(matched),time.time()))
    elif self.path=='/api/submit' and not teacher:
     if c.execute('SELECT completed FROM users WHERE id=?',(tid,)).fetchone()[0]:raise ValueError('Exercício concluído')
     if not data['body'].strip():raise ValueError('Preencha a entrega')
     check_hashes(c,tid,phase)
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
     check_hashes(c,tid,phase)
     if phase<5:c.execute('UPDATE users SET phase=phase+1 WHERE id=?',(tid,))
     else:c.execute('UPDATE users SET completed=1 WHERE id=?',(tid,))
     c.execute('DELETE FROM gates WHERE team_id=? AND phase=?',(tid,phase))
    elif not teacher:return self.send(403,{'error':'Acesso exclusivo do instrutor'})
    elif self.path=='/api/group':
     if len(data['password'])<10:raise ValueError('Senha deve ter 10 caracteres ou mais')
     s=secrets.token_hex(16);cur=c.execute('INSERT INTO users(name,role,salt,password) VALUES(?,?,?,?)',(data['name'],'group',s,digest(data['password'],s)));c.execute('UPDATE users SET team_id=id WHERE id=?',(cur.lastrowid,))
    elif self.path=='/api/release':
     c.execute('BEGIN IMMEDIATE')
     m=c.execute('SELECT * FROM materials WHERE id=?',(data['id'],)).fetchone()
     if not m:raise ValueError('Material inexistente')
     if m['kind']=='teacher':raise ValueError('Gabaritos e orientações são exclusivos do instrutor')
     if m['kind']=='response':
      group=c.execute("SELECT * FROM users WHERE id=? AND role='group'",(data.get('team_id'),)).fetchone()
      if not group or group['phase']<m['phase']:raise ValueError('Equipe ainda não alcançou esta fase')
      request_id=data.get('request_id')
      if m['code'] not in ['A15','A25']:
       request=c.execute('SELECT * FROM requests WHERE id=? AND team_id=?',(request_id,group['id'])).fetchone()
       if not request:raise ValueError('Vincule o pedido da própria equipe que justifica este retorno')
      c.execute('INSERT OR REPLACE INTO material_grants(material_id,team_id,request_id) VALUES(?,?,?)',(m['id'],group['id'],request_id))
     else:c.execute('UPDATE materials SET released=1 WHERE id=?',(m['id'],))
    elif self.path=='/api/gate':
     c.execute('BEGIN IMMEDIATE')
     group=c.execute("SELECT * FROM users WHERE id=? AND role='group'",(data['team_id'],)).fetchone()
     if not group or group['completed']:raise ValueError('Equipe indisponível')
     latest=c.execute('SELECT status FROM deliveries WHERE user_id=? AND phase=? ORDER BY id DESC LIMIT 1',(group['id'],group['phase'])).fetchone()
     if not latest or latest['status']!='approved':raise ValueError('Aprove a última entrega antes de emitir a senha')
     check_hashes(c,group['id'],group['phase'])
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
     if data['status']=='approved':check_hashes(c,group['id'],group['phase'])
     c.execute('UPDATE deliveries SET status=?,feedback=? WHERE id=?',(data['status'],data.get('feedback',''),data['id']))
     c.execute('DELETE FROM gates WHERE team_id=? AND phase=?',(group['id'],group['phase']))
    elif self.path=='/api/advance':
     raise ValueError('A progressão agora é por equipe, após aprovação da entrega')
    else:return self.send(404,{'error':'Não encontrado'})
    c.execute('INSERT INTO audit(actor,action,created) VALUES(?,?,?)',(u['id'],self.path,time.time()))
   self.send(200,{'ok':True})
  except (ValueError,KeyError,TypeError,sqlite3.IntegrityError) as e:self.send(400,{'error':str(e)})
if __name__=='__main__':
 init();ThreadingHTTPServer(('127.0.0.1',int(os.environ.get('PORT','8000'))),App).serve_forever()
