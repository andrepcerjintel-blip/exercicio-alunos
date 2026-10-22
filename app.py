import json, sqlite3, secrets, hashlib, hmac, time, mimetypes, os, zipfile
from urllib.parse import unquote
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('LUA_DATA', ROOT/'.runtime'))
DATA.mkdir(parents=True,exist_ok=True)
PHASES=['Denúncia','Recebimento e preservação','Triagem e pedidos','Respostas e diligências','Atualização posterior','Consolidação']
def db():
 c=sqlite3.connect(DATA/'lua.db');c.row_factory=sqlite3.Row;return c
def digest(p,s):return hashlib.scrypt(p.encode(),salt=bytes.fromhex(s),n=16384,r=8,p=1).hex()
def init():
 with db() as c:
  c.executescript('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT UNIQUE,role TEXT,salt TEXT,password TEXT);CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY,phase INTEGER);INSERT OR IGNORE INTO state VALUES(1,0);CREATE TABLE IF NOT EXISTS deliveries(id INTEGER PRIMARY KEY,user_id INTEGER,phase INTEGER,body TEXT,status TEXT,feedback TEXT,created REAL);CREATE TABLE IF NOT EXISTS sessions(token TEXT,uid INTEGER,csrf TEXT,expires REAL);CREATE TABLE IF NOT EXISTS materials(id INTEGER PRIMARY KEY,title TEXT,phase INTEGER,path TEXT UNIQUE,sha256 TEXT,released INTEGER DEFAULT 0);CREATE TABLE IF NOT EXISTS gates(team_id INTEGER,phase INTEGER,salt TEXT,hash TEXT,failures INTEGER DEFAULT 0,blocked REAL DEFAULT 0,PRIMARY KEY(team_id,phase));CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor INTEGER,action TEXT,created REAL);')
  c.executescript('''CREATE TABLE IF NOT EXISTS analyses(id INTEGER PRIMARY KEY,team_id INTEGER,actor_id INTEGER,response_id INTEGER,identifier_type TEXT,identifier_value TEXT,findings TEXT,limits TEXT,next_step TEXT,next_recipient TEXT,legal_basis TEXT,status TEXT DEFAULT 'submitted',feedback TEXT DEFAULT '',reviewer_id INTEGER,created REAL,reviewed REAL);
CREATE TABLE IF NOT EXISTS hash_targets(name TEXT PRIMARY KEY,sha256 TEXT,material_id INTEGER);
CREATE TABLE IF NOT EXISTS gate_messages(id INTEGER PRIMARY KEY,team_id INTEGER,phase INTEGER,code TEXT,sender_id INTEGER,created REAL);
CREATE TABLE IF NOT EXISTS material_grants(material_id INTEGER,team_id INTEGER,request_id INTEGER,PRIMARY KEY(material_id,team_id));
CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY,team_id INTEGER,actor_id INTEGER,phase INTEGER,recipient TEXT,body TEXT,created REAL);
CREATE TABLE IF NOT EXISTS hash_records(id INTEGER PRIMARY KEY,team_id INTEGER,actor_id INTEGER,name TEXT,sha256 TEXT,matched INTEGER,created REAL);''')
  analysis_columns={r['name'] for r in c.execute('PRAGMA table_info(analyses)')}
  if 'superseded_by' not in analysis_columns:c.execute('ALTER TABLE analyses ADD COLUMN superseded_by INTEGER')
  request_columns={r['name'] for r in c.execute('PRAGMA table_info(requests)')}
  for name,definition in [('status',"TEXT DEFAULT 'submitted'"),('feedback',"TEXT DEFAULT ''"),('reviewer_id','INTEGER'),('reviewed','REAL')]:
   if name not in request_columns:c.execute(f'ALTER TABLE requests ADD COLUMN {name} {definition}')
  delivery_columns={r['name'] for r in c.execute('PRAGMA table_info(deliveries)')}
  if 'actor_id' not in delivery_columns:c.execute('ALTER TABLE deliveries ADD COLUMN actor_id INTEGER')
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
def is_teacher(u):return u['role'] in ['instructor','evaluator']

def visible(c,m,u):
 if is_teacher(u):return True
 if m['kind']=='teacher':return False
 tid=u['team_id'] or u['id']
 phase=c.execute('SELECT phase FROM users WHERE id=?',(tid,)).fetchone()[0]
 if m['phase']>phase:return False
 if m['kind']=='response':return bool(c.execute('SELECT 1 FROM material_grants WHERE material_id=? AND team_id=?',(m['id'],tid)).fetchone())
 return bool(m['released'])

def missing_hashes(c,tid,material_ids=None):
 targets={r['name']:r['sha256'] for r in c.execute('SELECT name,sha256,material_id FROM hash_targets ORDER BY name') if material_ids is None or r['material_id'] in material_ids}
 records={r['name']:r['sha256'] for r in c.execute('SELECT name,sha256 FROM hash_records WHERE team_id=? ORDER BY id',(tid,))}
 return [name for name,expected in targets.items() if not hmac.compare_digest(records.get(name,''),expected)]

def check_hashes(c,tid,phase):
 if phase==1:
  if not c.execute('SELECT 1 FROM hash_targets').fetchone():raise ValueError('Kit de imagens ainda não cadastrado pelo professor')
  ids={r[0] for r in c.execute("SELECT id FROM materials WHERE code='IMAGENS-FASE-02'")}
  missing=missing_hashes(c,tid,ids)
  if missing:raise ValueError(f'Registre hashes correspondentes ao manifesto: {len(missing)} arquivos pendentes ou divergentes')

def visible_target_names(c,u):
 phase=c.execute('SELECT phase FROM users WHERE id=?',(u['team_id'] or u['id'],)).fetchone()[0]
 return [r['name'] for r in c.execute('SELECT h.name,m.* FROM hash_targets h JOIN materials m ON m.id=h.material_id ORDER BY h.name').fetchall() if r['phase']==phase and visible(c,r,u)]

RECIPIENTS=['Discord','Google','Instagram','Telegram','Rede de vídeos','NetSul Fibra','Equipe territorial','Perícia']
RESPONSE_RECIPIENT={'A08':'Discord','A23':'Discord','A10-A10B':'Google','A11':'Instagram','A13':'Telegram','A26':'Rede de vídeos','A09':'NetSul Fibra','A24':'NetSul Fibra','A12':'Equipe territorial','A16':'Perícia','LOCAL-A21-A22':'Perícia'}

def check_requests(c,tid,phase):
 if phase not in [2,3,4]:return
 requests=c.execute('SELECT * FROM requests WHERE team_id=? AND phase=? ORDER BY id',(tid,phase)).fetchall()
 latest={r['recipient']:r for r in requests}
 if phase==2 and not latest:raise ValueError('Registre os pedidos por plataforma para avaliação')
 if phase==4 and 'NetSul Fibra' not in latest:raise ValueError('O novo acesso exige pedido específico à NetSul Fibra nesta fase')
 pending=[name for name,r in latest.items() if r['status']!='approved']
 if pending:raise ValueError('Pedidos ainda não aprovados: '+', '.join(pending))

IDENTIFIER_TYPES=['ID de conta','E-mail','IP','Porta','Data/hora e fuso','Dispositivo','Titularidade','Outro']

def check_analyses(c,tid,phase):
 if phase!=3:return
 responses={r[0] for r in c.execute("SELECT m.id FROM materials m JOIN material_grants g ON g.material_id=m.id WHERE g.team_id=? AND m.phase=3 AND m.kind='response'",(tid,))}
 if not responses:raise ValueError('Receba os retornos liberados antes de concluir a análise')
 local=c.execute("SELECT id FROM materials WHERE code='LOCAL-A21-A22'").fetchone()
 if not local or local['id'] not in responses:raise ValueError('Conclua a diligência de perícia e arrecadação com liberação do professor')
 if missing_hashes(c,tid,{local['id']}):raise ValueError('Envie os hashes das duas imagens da perícia e do ZIP recebido')
 latest={}
 for r in c.execute('SELECT * FROM analyses WHERE team_id=? AND superseded_by IS NULL ORDER BY id',(tid,)):
  latest[(r['response_id'],r['identifier_type'],r['identifier_value'])]=r
 pending=[r for r in latest.values() if r['status']!='approved']
 covered={r['response_id'] for r in latest.values() if r['status']=='approved'}
 if pending:raise ValueError(f'{len(pending)} análise(s) por identificador ainda precisam de aprovação')
 if responses-covered:raise ValueError('Há resposta recebida sem análise aprovada dos identificadores')

def state_for(c,u):
 teacher=is_teacher(u);tid=u['team_id'] or u['id']
 group=c.execute('SELECT * FROM users WHERE id=?',(tid,)).fetchone()
 ds=[dict(x) for x in c.execute('SELECT d.*,u.name,a.name AS student_name FROM deliveries d JOIN users u ON u.id=d.user_id LEFT JOIN users a ON a.id=d.actor_id'+('' if teacher else ' WHERE d.user_id=?')+' ORDER BY d.id',() if teacher else (tid,))]
 groups=[dict(x) for x in c.execute("SELECT id,name,phase,completed FROM users WHERE role='group'")] if teacher else []
 materials=[]
 for m in c.execute('SELECT * FROM materials ORDER BY phase,id').fetchall():
  if visible(c,m,u):
   item={k:m[k] for k in ['id','title','phase','released','kind','code','filename']}
   if teacher:item['condition']=m['condition'];item['teams']=[x[0] for x in c.execute('SELECT team_id FROM material_grants WHERE material_id=?',(m['id'],))]
   if m['kind']=='phase' and m['code']!='IMAGENS-FASE-02':
    with zipfile.ZipFile(m['path']) as z:item['previews']=[name for name in z.namelist() if Path(name).suffix.lower() in ['.png','.mp4']]
   materials.append(item)
 requests=[dict(x) for x in c.execute('SELECT r.*,u.name,a.name AS student_name,v.name AS reviewer_name FROM requests r JOIN users u ON u.id=r.team_id LEFT JOIN users a ON a.id=r.actor_id LEFT JOIN users v ON v.id=r.reviewer_id'+('' if teacher else ' WHERE r.team_id=?')+' ORDER BY r.id',() if teacher else (tid,))]
 hashes=[dict(x) for x in c.execute('SELECT h.*,u.name AS team_name,a.name AS student_name FROM hash_records h JOIN users u ON u.id=h.team_id LEFT JOIN users a ON a.id=h.actor_id'+('' if teacher else ' WHERE h.team_id=?')+' ORDER BY h.id',() if teacher else (tid,))]
 inventory=visible_target_names(c,u) if group['phase']>=1 and not teacher else []
 if not teacher:hashes=[r for r in hashes if r['name'] in inventory]
 references=[dict(r) for r in c.execute('SELECT name,sha256,material_id FROM hash_targets ORDER BY name')] if teacher else []
 messages=[dict(r) for r in c.execute('SELECT id,phase,code,created FROM gate_messages WHERE team_id=? AND phase=? ORDER BY id DESC LIMIT 1',(tid,group['phase']))] if not teacher else []

 analyses=[dict(r) for r in c.execute('SELECT x.*,u.name AS team_name,a.name AS student_name,m.title AS response_title,m.code AS response_code,v.name AS reviewer_name FROM analyses x JOIN users u ON u.id=x.team_id LEFT JOIN users a ON a.id=x.actor_id JOIN materials m ON m.id=x.response_id LEFT JOIN users v ON v.id=x.reviewer_id'+('' if teacher else ' WHERE x.team_id=?')+' ORDER BY x.id',() if teacher else (tid,))]
 return dict(analyses=analyses,identifier_types=IDENTIFIER_TYPES,hash_references=references,messages=messages,hash_pending=[n for n in missing_hashes(c,tid) if n in inventory] if not teacher and group['phase']>=1 else [],inventory=inventory,recipients=RECIPIENTS,user={'name':u['name'],'role':u['role'],'team':group['name'] if not teacher else None},csrf=u['csrf'],phase=group['phase'],completed=bool(group['completed']),scenario=json.loads((ROOT/'roteiro.json').read_text())[group['phase']],phases=PHASES,materials=materials,groups=groups,deliveries=ds,requests=requests,hashes=hashes)

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
  if self.path=='/':
   self.send_response(302);self.send_header('Location','/aluno');self.end_headers();return
  if self.path in ['/aluno','/professor','/app.js','/style.css'] or self.path.startswith('/aluno/fase/') or self.path.startswith('/professor/fase/'):
   p=ROOT/'static'/('index.html' if self.path in ['/aluno','/professor'] or self.path.startswith('/aluno/fase/') or self.path.startswith('/professor/fase/') else self.path[1:]);payload=p.read_bytes();payload=payload.replace(b'__PORTAL__',b'instructor' if self.path.startswith('/professor') else b'student');return self.send(200,payload,{'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css'}[p.suffix[1:]])
  with db() as c:
   u=self.user(c)
   if not u:return self.send(401,{'error':'Entre com seu acesso'})
   if self.path.startswith('/asset/'):
    parts=self.path.split('/',3)
    try:m=c.execute('SELECT * FROM materials WHERE id=?',(int(parts[2]),)).fetchone()
    except (ValueError,IndexError):m=None
    if not m or not visible(c,m,u):return self.send(403,{'error':'Material reservado'})
    if m['code'] in ['IMAGENS-FASE-02','LOCAL-A21-A22']:return self.send(403,{'error':'Faça o download do ZIP original para examinar as imagens'})
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
     if not u or u['role']=='group' or not hmac.compare_digest(digest(data['password'],u['salt']),u['password']):return self.send(401,{'error':'Acesso inválido'})
     t=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(t,u['id'],secrets.token_urlsafe(32),time.time()+28800));c.commit()
     self.send_response(200);self.send_header('Set-Cookie',f'lua={t}; HttpOnly; SameSite=Strict; Path=/');self.end_headers();return
    u=self.user(c)
    if not u:return self.send(401,{'error':'Entre com seu acesso'})
    if not hmac.compare_digest(self.headers.get('X-CSRF',''),u['csrf']):return self.send(403,{'error':'Sessão inválida'})
    teacher=is_teacher(u);tid=u['team_id'] or u['id'];phase=c.execute('SELECT phase FROM users WHERE id=?',(tid,)).fetchone()[0]
    if self.path=='/api/analysis' and not teacher:
     if phase!=3:raise ValueError('As fichas de análise são entregues na fase 4')
     response=c.execute("SELECT * FROM materials WHERE id=? AND kind='response' AND phase=3",(data.get('response_id'),)).fetchone()
     if not response or not visible(c,response,u):raise ValueError('Selecione uma resposta já recebida pela sua equipe')
     parent=None
     if data.get('revision_of'):
      parent=c.execute('SELECT * FROM analyses WHERE id=? AND team_id=? AND superseded_by IS NULL',(data['revision_of'],tid)).fetchone()
      if not parent:raise ValueError('A ficha a corrigir não pertence à equipe ou já foi substituída')
     fields=['identifier_type','identifier_value','findings','limits','next_step','next_recipient','legal_basis']
     if data.get('identifier_type') not in IDENTIFIER_TYPES or any(not isinstance(data.get(k),str) or not data[k].strip() for k in fields):raise ValueError('Preencha identificador, análise, limites e encaminhamento justificado')
     new_analysis=c.execute('INSERT INTO analyses(team_id,actor_id,response_id,identifier_type,identifier_value,findings,limits,next_step,next_recipient,legal_basis,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(tid,u['id'],response['id'],*(data[k].strip() for k in fields),time.time()))
     if parent:c.execute('UPDATE analyses SET superseded_by=? WHERE id=?',(new_analysis.lastrowid,parent['id']))
     c.execute('DELETE FROM gates WHERE team_id=? AND phase=?',(tid,phase))
     c.execute('DELETE FROM gate_messages WHERE team_id=? AND phase=?',(tid,phase))
    elif self.path=='/api/request' and not teacher:
     if phase<2 or phase>4:raise ValueError('Pedidos disponíveis nas fases 3, 4 e 5')
     if data.get('recipient','').strip() not in RECIPIENTS or not data.get('body','').strip():raise ValueError('Informe plataforma/provedor válido e o texto fundamentado')
     c.execute('INSERT INTO requests(team_id,actor_id,phase,recipient,body,created) VALUES(?,?,?,?,?,?)',(tid,u['id'],phase,data['recipient'].strip(),data['body'].strip(),time.time()))
     c.execute('DELETE FROM gates WHERE team_id=? AND phase=?',(tid,phase))
     c.execute('DELETE FROM gate_messages WHERE team_id=? AND phase=?',(tid,phase))
    elif self.path=='/api/hash' and not teacher:
     if phase not in [1,3] or c.execute('SELECT completed FROM users WHERE id=?',(tid,)).fetchone()[0]:raise ValueError('O envio de hashes está disponível nas etapas de recebimento e perícia')
     name=data.get('name','');value=data.get('sha256','').lower()
     if len(value)!=64 or any(ch not in '0123456789abcdef' for ch in value):raise ValueError('Informe SHA-256 válido')
     target=c.execute('SELECT h.sha256 AS target_hash,m.* FROM hash_targets h JOIN materials m ON m.id=h.material_id WHERE h.name=?',(name,)).fetchone()
     if not target or target['phase']!=phase or not visible(c,target,u):raise ValueError('Selecione uma imagem ou ZIP já liberado à sua equipe')
     matched=hmac.compare_digest(target['target_hash'],value)
     c.execute('INSERT INTO hash_records(team_id,actor_id,name,sha256,matched,created) VALUES(?,?,?,?,?,?)',(tid,u['id'],name,value,int(matched),time.time()))
    elif self.path=='/api/submit' and not teacher:
     if c.execute('SELECT completed FROM users WHERE id=?',(tid,)).fetchone()[0]:raise ValueError('Exercício concluído')
     if not data['body'].strip():raise ValueError('Preencha a entrega')
     check_hashes(c,tid,phase)
     c.execute('INSERT INTO deliveries(user_id,phase,body,status,feedback,created,actor_id) VALUES(?,?,?,?,?,?,?)',(tid,phase,data['body'],'submitted','',time.time(),u['id']))
     c.execute('DELETE FROM gates WHERE team_id=? AND phase=?',(tid,phase))
     c.execute('DELETE FROM gate_messages WHERE team_id=? AND phase=?',(tid,phase))
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
     check_requests(c,tid,phase)
     check_analyses(c,tid,phase)
     if phase<5:c.execute('UPDATE users SET phase=phase+1 WHERE id=?',(tid,))
     else:c.execute('UPDATE users SET completed=1 WHERE id=?',(tid,))
     c.execute('DELETE FROM gates WHERE team_id=? AND phase=?',(tid,phase))
     c.execute('DELETE FROM gate_messages WHERE team_id=? AND phase=?',(tid,phase))
    elif not teacher:return self.send(403,{'error':'Acesso exclusivo do instrutor'})
    elif self.path=='/api/evaluator':
     if u['role']!='instructor':return self.send(403,{'error':'Somente o instrutor responsável cadastra avaliadores'})
     if not data.get('name','').strip() or len(data.get('password',''))<10:raise ValueError('Informe nome e senha de pelo menos dez caracteres')
     salt=secrets.token_hex(16)
     c.execute('INSERT INTO users(name,role,salt,password) VALUES(?,?,?,?)',(data['name'].strip(),'evaluator',salt,digest(data['password'],salt)))
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
      if m['code']=='LOCAL-A21-A22':
       pericia=c.execute("SELECT 1 FROM material_grants g JOIN materials m ON m.id=g.material_id WHERE g.team_id=? AND m.code='A16'",(group['id'],)).fetchone()
       if not pericia:raise ValueError('Libere primeiro o retorno pericial A16 após avaliar o pedido')
      request_id=data.get('request_id')
      if m['code'] not in ['A15','A25']:
       request=c.execute('SELECT * FROM requests WHERE id=? AND team_id=?',(request_id,group['id'])).fetchone()
       if not request:raise ValueError('Vincule o pedido da própria equipe que justifica este retorno')
       if request['recipient']!=RESPONSE_RECIPIENT.get(m['code']):raise ValueError('O pedido deve corresponder à plataforma/provedor deste retorno')
       latest=c.execute('SELECT id FROM requests WHERE team_id=? AND recipient=? ORDER BY id DESC LIMIT 1',(group['id'],request['recipient'])).fetchone()
       if request['status']!='approved' or latest['id']!=request['id']:raise ValueError('A última versão do pedido deste provedor precisa estar aprovada pelo avaliador')
       if m['code']=='A24' and request['phase']!=4:raise ValueError('A24 exige pedido referente à atualização da fase 5')
      c.execute('INSERT OR REPLACE INTO material_grants(material_id,team_id,request_id) VALUES(?,?,?)',(m['id'],group['id'],request_id))
     else:c.execute('UPDATE materials SET released=1 WHERE id=?',(m['id'],))
    elif self.path=='/api/gate':
     c.execute('BEGIN IMMEDIATE')
     group=c.execute("SELECT * FROM users WHERE id=? AND role='group'",(data['team_id'],)).fetchone()
     if not group or group['completed']:raise ValueError('Equipe indisponível')
     latest=c.execute('SELECT status FROM deliveries WHERE user_id=? AND phase=? ORDER BY id DESC LIMIT 1',(group['id'],group['phase'])).fetchone()
     if not latest or latest['status']!='approved':raise ValueError('Aprove a última entrega antes de emitir a senha')
     check_hashes(c,group['id'],group['phase'])
     check_requests(c,group['id'],group['phase'])
     check_analyses(c,group['id'],group['phase'])
     code=secrets.token_hex(5).upper();salt=secrets.token_hex(16)
     c.execute('INSERT OR REPLACE INTO gates(team_id,phase,salt,hash) VALUES(?,?,?,?)',(group['id'],group['phase'],salt,digest(code,salt)))
     c.execute('DELETE FROM gate_messages WHERE team_id=? AND phase=?',(group['id'],group['phase']))
     c.execute('INSERT INTO gate_messages(team_id,phase,code,sender_id,created) VALUES(?,?,?,?,?)',(group['id'],group['phase'],code,u['id'],time.time()))
     c.execute('INSERT INTO audit(actor,action,created) VALUES(?,?,?)',(u['id'],'issue_gate',time.time()));c.commit()
     return self.send(200,{'code':code,'team':group['name'],'phase':group['phase']+1})
    elif self.path=='/api/analysis-review':
     c.execute('BEGIN IMMEDIATE')
     if data.get('status') not in ['approved','correction']:raise ValueError('Situação inválida')
     item=c.execute('SELECT * FROM analyses WHERE id=?',(data['id'],)).fetchone()
     if not item:raise ValueError('Análise inexistente')
     if item['superseded_by']:raise ValueError('Esta ficha foi substituída por uma correção')
     latest=c.execute('SELECT id FROM analyses WHERE team_id=? AND response_id=? AND identifier_type=? AND identifier_value=? ORDER BY id DESC LIMIT 1',(item['team_id'],item['response_id'],item['identifier_type'],item['identifier_value'])).fetchone()
     group=c.execute('SELECT phase FROM users WHERE id=?',(item['team_id'],)).fetchone()
     if latest['id']!=item['id'] or group['phase']!=3:raise ValueError('Avalie a última versão de uma análise da fase atual')
     if data['status']=='correction' and not data.get('feedback','').strip():raise ValueError('Informe o motivo da correção')
     c.execute('UPDATE analyses SET status=?,feedback=?,reviewer_id=?,reviewed=? WHERE id=?',(data['status'],data.get('feedback','').strip(),u['id'],time.time(),item['id']))
     c.execute('DELETE FROM gates WHERE team_id=? AND phase=3',(item['team_id'],))
     c.execute('DELETE FROM gate_messages WHERE team_id=? AND phase=3',(item['team_id'],))
    elif self.path=='/api/request-review':
     c.execute('BEGIN IMMEDIATE')
     if data.get('status') not in ['approved','correction']:raise ValueError('Situação inválida')
     request=c.execute('SELECT * FROM requests WHERE id=?',(data['id'],)).fetchone()
     if not request:raise ValueError('Pedido inexistente')
     latest=c.execute('SELECT id FROM requests WHERE team_id=? AND recipient=? ORDER BY id DESC LIMIT 1',(request['team_id'],request['recipient'])).fetchone()
     if latest['id']!=request['id']:raise ValueError('Avalie a última versão enviada para esta plataforma/provedor')
     if data['status']=='correction' and not data.get('feedback','').strip():raise ValueError('Informe o motivo da correção')
     c.execute('UPDATE requests SET status=?,feedback=?,reviewer_id=?,reviewed=? WHERE id=?',(data['status'],data.get('feedback','').strip(),u['id'],time.time(),request['id']))
     group=c.execute('SELECT phase FROM users WHERE id=?',(request['team_id'],)).fetchone()
     c.execute('DELETE FROM gates WHERE team_id=? AND phase=?',(request['team_id'],group['phase']))
     c.execute('DELETE FROM gate_messages WHERE team_id=? AND phase=?',(request['team_id'],group['phase']))
    elif self.path=='/api/review':
     c.execute('BEGIN IMMEDIATE')
     if data['status'] not in ['approved','correction']:raise ValueError('Situação inválida')
     delivery=c.execute('SELECT * FROM deliveries WHERE id=?',(data['id'],)).fetchone()
     if not delivery:raise ValueError('Entrega inexistente')
     group=c.execute('SELECT * FROM users WHERE id=?',(delivery['user_id'],)).fetchone()
     latest=c.execute('SELECT id FROM deliveries WHERE user_id=? AND phase=? ORDER BY id DESC LIMIT 1',(group['id'],group['phase'])).fetchone()
     if delivery['phase']!=group['phase'] or not latest or latest['id']!=delivery['id']:raise ValueError('Avalie apenas a última entrega da fase atual')
     if data['status']=='approved':
      check_hashes(c,group['id'],group['phase'])
      check_requests(c,group['id'],group['phase'])
      check_analyses(c,group['id'],group['phase'])
     c.execute('UPDATE deliveries SET status=?,feedback=? WHERE id=?',(data['status'],data.get('feedback',''),data['id']))
     c.execute('DELETE FROM gates WHERE team_id=? AND phase=?',(group['id'],group['phase']))
     c.execute('DELETE FROM gate_messages WHERE team_id=? AND phase=?',(group['id'],group['phase']))
    elif self.path=='/api/advance':
     raise ValueError('A progressão agora é por equipe, após aprovação da entrega')
    else:return self.send(404,{'error':'Não encontrado'})
    c.execute('INSERT INTO audit(actor,action,created) VALUES(?,?,?)',(u['id'],self.path,time.time()))
   self.send(200,{'ok':True,**({'matched':matched} if self.path=='/api/hash' else {})})
  except (ValueError,KeyError,TypeError,sqlite3.IntegrityError) as e:self.send(400,{'error':str(e)})
if __name__=='__main__':
 init();ThreadingHTTPServer((os.environ.get('HOST','127.0.0.1'),int(os.environ.get('PORT','8000'))),App).serve_forever()
