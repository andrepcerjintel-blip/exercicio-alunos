"""Gera uma demonstração independente de servidor, sem gabaritos ou credenciais reais."""
import base64,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
scenes=json.loads((ROOT/'roteiro.json').read_text())
assets=[]
for name in ['01_DENUNCIA_WHATSAPP/anexos/A01_Denuncia_Inicial.png','02_PROVAS_INICIAIS_ALUNOS/anexos/A02.png','02_PROVAS_INICIAIS_ALUNOS/anexos/A03.png']:
 raw=(ROOT/name).read_bytes();assets.append(dict(name=Path(name).name,url='data:image/png;base64,'+base64.b64encode(raw).decode(),hash=hashlib.sha256(raw).hexdigest()))
script=(ROOT/'static/demo-offline.js').read_text().replace('__SCENES__',json.dumps(scenes,ensure_ascii=False)).replace('__ASSETS__',json.dumps(assets))
css=(ROOT/'static/style.css').read_text()
html='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Operação LUA — teste no navegador</title><style>'''+css+'''</style><body><header><div class="brand-icon">☾</div><div><span class="eyebrow">TESTE INTERATIVO · SEM INSTALAÇÃO</span><h1>Operação LUA</h1></div><span class="badge">DEMONSTRAÇÃO LOCAL</span></header><main><section><h2>Teste o jogo no seu navegador</h2><p>Esta demonstração funciona neste arquivo HTML, sem Python ou iniciadores Windows. Você simula os papéis de equipe e instrutor para testar as seis fases, entregas, hashes e senhas. Inclui uma amostra de evidências. Não é o sistema completo para uma turma com múltiplos acessos.</p><p>As informações digitadas ficam somente neste navegador, quando o armazenamento local estiver disponível. Nenhum dado é enviado a um servidor.</p></section><div id="message" role="status" aria-live="polite"></div><section id="begin"><h2>Entrar na demonstração</h2><form id="setup"><label>Seu nome<input name="student" required></label><label>Nome da equipe<input name="team" required></label><button>Iniciar investigação →</button></form></section><div id="workspace" hidden></div><footer>Simulação fictícia · Validação pedagógica e jurídica pelo instrutor · Demonstração para avaliação da interface.</footer></main><script>'''+script.replace('</script','<\\/script')+'''</script></body></html>'''
out=ROOT/'distribuicao/Operacao_LUA_Teste_Navegador.html';out.write_text(html)
print(out.name,out.stat().st_size,'bytes')
