# Executável local

O gerador `python scripts/empacotar.py` cria dois artefatos fora do checkout, em `/workspace/entregas`:

- `Operacao_LUA.pyz`: aplicação Python portátil. Exige Python 3.12 ou superior; verifica os arquivos, prepara uma pasta versionada em `~/OperacaoLUA`, integra o kit e abre o navegador.
- `Operacao_LUA_Portatil.zip`: aplicação em pasta, com iniciadores `INICIAR_WINDOWS.cmd` e `INICIAR_MAC_LINUX.sh`, além de `LEIA_PRIMEIRO.txt`.

No Windows, extraia o ZIP e abra `INICIAR_WINDOWS.cmd`. Em macOS/Linux, execute `bash INICIAR_MAC_LINUX.sh` na pasta extraída. Ambos exigem Python 3.12 ou superior. Também é possível executar `python3 Operacao_LUA.pyz` (Windows: `py -3 Operacao_LUA.pyz`). Não é um `.exe` nativo de Windows.

O terminal informa o caminho do acesso inicial do instrutor. O servidor é local; mantenha o terminal aberto e use Ctrl+C para encerrá-lo. Se a porta 8000 estiver ocupada, o iniciador escolhe outra porta disponível. O progresso é salvo localmente.

O pacote não inclui credenciais, banco de dados, equipes ou histórico da instância de desenvolvimento. Contém o kit completo, inclusive gabaritos; é destinado ao instrutor e não deve ser distribuído integralmente aos alunos.

A inicialização do `.pyz` foi validada em Linux, em pasta limpa: servidor HTTP respondeu, acesso anônimo foi bloqueado, login do instrutor funcionou e os 21 materiais foram cadastrados. O iniciador Windows foi incluído, mas não executado em Windows neste ambiente.
