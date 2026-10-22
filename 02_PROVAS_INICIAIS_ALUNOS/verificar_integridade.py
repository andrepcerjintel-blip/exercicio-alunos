from pathlib import Path
import hashlib,sys
root=Path(__file__).resolve().parent
expected={}
for line in (root/'SHA256.txt').read_text().splitlines():
 if line.strip():
  digest,name=line.split('  ',1);expected[name]=digest
bad=[]
for name,digest in expected.items():
 p=root/name
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:bad.append(name)
actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and not any(part.startswith('.') for part in p.relative_to(root).parts) and p!=root/'SHA256.txt' and '__pycache__' not in p.parts}
if actual!=set(expected):bad+=sorted(actual.symmetric_difference(set(expected)))
print('APROVADO: '+str(len(expected))+' arquivos' if not bad else 'DIVERGÊNCIAS: '+str(bad))
sys.exit(1 if bad else 0)
