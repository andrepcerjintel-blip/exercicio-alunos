# Entrega 04 — Kit integrado e jogo executado

Resultado: [demonstração visual das seis fases](demonstracao/demonstracao.html), com oito capturas reais da aplicação em Chromium, incluindo o painel do instrutor e o encerramento. O HTML é um relatório navegável de capturas, não um servidor do jogo.

## O que foi integrado

- Seis pacotes de fase disponíveis conforme o progresso de cada equipe.
- Doze pacotes de respostas e diligências: A08, A23, A15, A10/A10B, A11, A09, A24, A26, A13, A12, A16 e A25.
- Três itens exclusivos do professor: gabaritos/base, guia e plano de liberação.
- Prévias autenticadas das imagens e do vídeo dos pacotes de fase.
- Pedidos por equipe, com destinatário e fundamentação textual.
- Liberação de respostas por equipe, vinculada a um pedido daquela equipe. A15 e A25 são atualizações e dispensam pedido prévio.
- Conferência dos hashes calculados localmente e registro da pessoa que os enviou. O navegador pode calcular toda a pasta extraída, sem enviar os arquivos.
- Bloqueio de entrega, aprovação e senha da fase 2 enquanto houver hashes pendentes ou divergentes nos 18 itens do manifesto. Vale o último hash registrado para cada arquivo.
- Senha exclusiva por equipe e fase, emitida pelo instrutor somente após a aprovação. A última senha confirma o encerramento.

Os pacotes ZIP são reconstruídos de forma determinística a partir das pastas do repositório. Seus hashes são novos; os bytes de cada arquivo interno são preservados. As orientações `LEIA_PROFESSOR_NAO_ENTREGAR.txt` não entram nos pacotes distribuídos. Gabaritos não são expostos aos alunos pela aplicação.

## Validação executada

Cinco testes de integração passaram, cobrindo importação repetível, acesso aos 21 itens, proteção dos arquivos futuros e do professor, isolamento entre equipes, vínculo do retorno ao pedido, registro de hash correto e incorreto, cadastro individual e as seis passagens por senha.

O percurso real no Chromium passou com 18 verificações, incluindo:

1. Cadastro e login pela interface.
2. Denúncia exibida com a imagem original do kit.
3. Senha incorreta rejeitada em cada uma das seis etapas.
4. Aprovação e senha correta necessárias para cada passagem.
5. Hash de A02 calculado no navegador e conferido no servidor.
6. Tentativa de entregar a fase 2 com inventário incompleto rejeitada.
7. Dezoito hashes calculados a partir da pasta local e registrados pela interface.
8. Pedido ao Discord enviado pela interface e resposta A08 liberada pelo instrutor somente para a equipe Aurora.
9. Tentativa da equipe Reserva de baixar A08 rejeitada com HTTP 403.
10. Conclusão após a sexta senha, enquanto a equipe Reserva continua na fase 1.
11. Nenhum erro JavaScript no percurso.

O teste usa banco temporário e entregas fictícias de teste. Essas entregas não são gabaritos e o teste não atesta a correção jurídica de documentos investigativos.

## Executar novamente

```sh
python integrar_kit.py
python -m unittest discover -s tests -v
python app.py
```

A demonstração requer Playwright para Python e Chromium. Nesta máquina ambos já estavam disponíveis:

```sh
python scripts/demonstrar.py
```

Saídas: `docs/demonstracao/resultado.json`, oito PNGs e `demonstracao.html` autossuficiente. Nenhuma credencial real ou senha de passagem é incluída no relatório.

## Limites atuais

A avaliação jurídica e a adequação de cada pedido ao retorno continuam com o instrutor. O sistema exige pedido da própria equipe para liberar uma resposta, mas não interpreta juridicamente seu texto nem comprova automaticamente todos os vínculos e dependências do gabarito. As entregas finais são textuais; anexos enviados pelos alunos e a operação final ainda não estão implementados. A integridade dos arquivos não comprova por si só origem ou autoria.

O controle de acesso descrito vale para a aplicação. Quem tiver acesso ao repositório GitHub também terá acesso aos materiais reservados que foram enviados ao próprio repositório.
