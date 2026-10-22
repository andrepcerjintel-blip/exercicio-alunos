"""Importa o kit sem executar scripts recebidos e sem alterar bytes dos anexos."""
import hashlib
import json
import zipfile
from pathlib import Path
import app

RESPONSES = [
 ('Discord/01_Resposta_Inicial_ROOK','A08','Discord · resposta inicial ROOK',3),
 ('Discord/02_Resposta_Complementar','A23','Discord · resposta complementar',3),
 ('Discord/03_Proativo_Posterior','A15','Discord · atualização proativa',4),
 ('Google/01_Cadastros_E_Dispositivo','A10-A10B','Google · cadastros e dispositivo',3),
 ('Meta_Instagram/01_Retorno_Contas','A11','Instagram · retorno de contas',3),
 ('NetSul_Fibra/01_Conexoes_Iniciais','A09','NetSul · conexões iniciais',3),
 ('NetSul_Fibra/02_Conexao_Posterior','A24','NetSul · novo acesso',4),
 ('Rede_De_Videos/01_Retorno_Perfis','A26','Rede de vídeos · retorno de perfis',3),
 ('Telegram/01_Protocolo_Limitado','A13','Telegram · protocolo limitado',3),
]
DILIGENCES=[('01_Qualificacoes_Locais','A12','Diligência · qualificações locais',3),('02_Comunicacao_Pericial','A16','Diligência · comunicação pericial',3),('03_Metadados_Atualizados','A25','Diligência · metadados atualizados',4)]

def checksum(path):
 with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def archive(folder,destination,private=False,exclude=()):
 files=sorted(p for p in folder.rglob('*') if p.is_file() and p.name not in exclude and (private or p.name!='LEIA_PROFESSOR_NAO_ENTREGAR.txt'))
 if not files:raise ValueError(f'Pasta sem documentos: {folder}')
 with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
  for p in files:
   info=zipfile.ZipInfo(p.relative_to(folder).as_posix(),date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
   z.writestr(info,p.read_bytes())
 return files

def integrate():
 app.init();output=app.DATA/'kit';output.mkdir(exist_ok=True)
 verified=0
 for manifest in sorted(app.ROOT.glob('0[1-6]*/SHA256.txt')):
  for line in manifest.read_text().splitlines():
   parts=line.split(maxsplit=1)
   if len(parts)!=2:continue
   expected,name=parts;file=manifest.parent/name.lstrip('*')
   if not file.is_file() or checksum(file)!=expected:raise ValueError(f'Integridade divergente: {file}')
   verified+=1
 catalog=[]
 def add(folder,code,title,phase,kind,condition='',private=False,exclude=()):
  dest=output/(code+'.zip');files=archive(folder,dest,private,exclude)
  value=checksum(dest)
  with app.db() as c:
   existing=c.execute('SELECT id FROM materials WHERE code=?',(code,)).fetchone()
   values=(title,phase,str(dest),value,int(kind=='phase'),kind,code,condition,dest.name)
   if existing:c.execute('UPDATE materials SET title=?,phase=?,path=?,sha256=?,released=?,kind=?,code=?,condition=?,filename=? WHERE id=?',(*values,existing['id']))
   else:c.execute('INSERT INTO materials(title,phase,path,sha256,released,kind,code,condition,filename) VALUES(?,?,?,?,?,?,?,?,?)',values)
  catalog.append(dict(code=code,title=title,phase=phase+1,kind=kind,files=len(files),sha256=value))
 plan=json.loads((app.ROOT/'00_PROFESSOR_RESERVADO/Plano_De_Liberacao.json').read_text())
 for i,entry in enumerate(plan):
  exclusions=tuple(p.name for p in (app.ROOT/entry['folder']).rglob('*') if p.is_file() and (p.suffix.lower() in ['.png','.sha256'] or p.name in ['SHA256.txt','verificar_integridade.py','Caderno_Desta_Entrega.pdf'])) if i==1 else ()
  add(app.ROOT/entry['folder'],f'FASE-{i+1:02}',entry['title'],i,'phase',entry['release'],exclude=exclusions)
 # Separate, immutable download: image bytes only, without an answer manifest.
 images=sorted(p for p in (app.ROOT/'02_PROVAS_INICIAIS_ALUNOS/anexos').glob('*.png') if p.name not in ['A21.png','A22.png'])
 dest=output/'IMAGENS-FASE-02.zip'
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
  for p in images:
   info=zipfile.ZipInfo('anexos/'+p.name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
 with app.db() as c:
  existing=c.execute("SELECT id FROM materials WHERE code='IMAGENS-FASE-02'").fetchone()
  value=checksum(dest)
  if existing:
   material_id=existing['id'];c.execute('UPDATE materials SET path=?,sha256=?,filename=?,released=1 WHERE id=?',(str(dest),value,dest.name,material_id))
  else:
   material_id=c.execute('INSERT INTO materials(title,phase,path,sha256,released,kind,code,filename) VALUES(?,?,?,?,?,?,?,?)',('Imagens originais — baixar ZIP e calcular hashes',1,str(dest),value,1,'phase','IMAGENS-FASE-02',dest.name)).lastrowid
  c.execute('DELETE FROM hash_targets')
  for p in images:c.execute('INSERT INTO hash_targets VALUES(?,?,?)',('anexos/'+p.name,checksum(p),material_id))
  c.execute('INSERT INTO hash_targets VALUES(?,?,?)',(dest.name,value,material_id))
 catalog.append(dict(code='IMAGENS-FASE-02',title='Imagens originais',phase=2,kind='phase',files=len(images),sha256=value))
 # These images belong exclusively to the later crime-scene collection.
 late=output/'LOCAL-A21-A22.zip'
 with zipfile.ZipFile(late,'w',zipfile.ZIP_DEFLATED) as z:
  for name in ['A21.png','A22.png']:
   p=app.ROOT/'02_PROVAS_INICIAIS_ALUNOS/anexos'/name
   info=zipfile.ZipInfo('anexos/'+name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
 with app.db() as c:
  existing=c.execute("SELECT id FROM materials WHERE code='LOCAL-A21-A22'").fetchone();value=checksum(late)
  if existing:
   late_id=existing['id'];c.execute('UPDATE materials SET path=?,sha256=?,filename=? WHERE id=?',(str(late),value,late.name,late_id))
  else:
   late_id=c.execute('INSERT INTO materials(title,phase,path,sha256,released,kind,code,condition,filename) VALUES(?,?,?,?,?,?,?,?,?)',('Perícia e arrecadação — polícia no local e caderno',3,str(late),value,0,'response','LOCAL-A21-A22','Somente após pedido de perícia aprovado, retorno A16 recebido e liberação expressa do professor.',late.name)).lastrowid
  for name in ['A21.png','A22.png']:
   c.execute('INSERT INTO hash_targets VALUES(?,?,?)',('anexos/'+name,checksum(app.ROOT/'02_PROVAS_INICIAIS_ALUNOS/anexos'/name),late_id))
  c.execute('INSERT INTO hash_targets VALUES(?,?,?)',(late.name,value,late_id))
 catalog.append(dict(code='LOCAL-A21-A22',title='Perícia e arrecadação no local',phase=4,kind='response',files=2,sha256=value))

 reserved=app.ROOT/'00_PROFESSOR_RESERVADO'
 for relative,code,title,phase in RESPONSES:
  folder=reserved/'02_RESPOSTAS_PROVEDORES'/relative
  add(folder,code,title,phase,'response',(folder/'LEIA_PROFESSOR_NAO_ENTREGAR.txt').read_text())
 for relative,code,title,phase in DILIGENCES:
  folder=reserved/'03_RETORNOS_DILIGENCIAS'/relative
  add(folder,code,title,phase,'response',(folder/'LEIA_PROFESSOR_NAO_ENTREGAR.txt').read_text())
 add(reserved/'01_GABARITO_E_VALIDACAO','PROFESSOR','Gabaritos, base canônica e validação',0,'teacher',private=True)
 for name,title in [('Guia_Instrutor_LUA.pdf','Guia do instrutor'),('Plano_De_Liberacao.json','Plano de liberação')]:
  p=reserved/name;code='RESERVADO-'+p.stem
  with app.db() as c:
   if not c.execute('SELECT 1 FROM materials WHERE code=?',(code,)).fetchone():
    c.execute('INSERT INTO materials(title,phase,path,sha256,kind,code,filename) VALUES(?,?,?,?,?,?,?)',(title,0,str(p),checksum(p),'teacher',code,name))
  catalog.append(dict(code=code,title=title,kind='teacher',files=1))
 report=dict(verified_files=verified,materials=len(catalog),catalog=catalog)
 (app.DATA/'integracao.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 return report
if __name__=='__main__':
 report=integrate();print(json.dumps({k:v for k,v in report.items() if k!='catalog'},ensure_ascii=False))
