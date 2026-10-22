# Prévia visual dos portais

A prévia pública mostra capturas reais do teste dos portais, organizadas por papel e fase. Não é um portal de turma: não envia respostas e não contém controles de autoaprovação.

Para executar o serviço autenticado, consulte `README.md` e use `python servidor.py` em uma hospedagem apropriada. O aluno acessa `/aluno`, o professor `/professor`.

O teste completo é reproduzido por `python scripts/demonstrar.py`. A prévia é gerada por `python scripts/gerar_demo_navegador.py` e validada por `python scripts/testar_demo_navegador.py`. Requerem Playwright e Chromium para os testes de navegador; a aplicação Python não depende desses pacotes.
