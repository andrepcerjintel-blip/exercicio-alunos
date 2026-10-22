"""Cadastro local de material; não executa arquivos importados."""
import argparse, shutil, hashlib
from pathlib import Path
import app
p=argparse.ArgumentParser();p.add_argument('arquivo',type=Path);p.add_argument('--fase',type=int,required=True,choices=range(1,7));p.add_argument('--titulo',required=True);a=p.parse_args()
app.init();folder=app.DATA/'materiais';folder.mkdir(exist_ok=True)
h=hashlib.file_digest(a.arquivo.open('rb'),'sha256').hexdigest();dest=folder/(h+a.arquivo.suffix)
if not dest.exists():shutil.copyfile(a.arquivo,dest)
with app.db() as c:c.execute('INSERT OR IGNORE INTO materials(title,phase,path,sha256) VALUES(?,?,?,?)',(a.titulo,a.fase-1,str(dest),h))
print('Material cadastrado como reservado. SHA-256:',h)
