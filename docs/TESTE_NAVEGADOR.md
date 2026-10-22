# Demonstração interativa no navegador

O arquivo `distribuicao/Operacao_LUA_Teste_Navegador.html` é uma demonstração autossuficiente, sem iniciadores Windows, Python ou servidor da aplicação. Contém interface, roteiro das seis fases e três imagens do kit. Não contém gabaritos, credenciais reais ou os documentos dos provedores.

Baixe o HTML e abra-o em um navegador atualizado. Cadastre um nome e equipe de teste. Em cada fase, envie a entrega, use os controles explicitamente demonstrativos para simular o instrutor, emita a senha e informe-a no campo de passagem. Na fase 2, confira o hash de uma das duas provas da amostra. Na fase 3, registre um pedido.

O progresso fica no armazenamento do navegador, quando disponível. Nenhum dado é enviado ao servidor. Esse modo não implementa autenticação, isolamento entre equipes reais ou avaliação jurídica; serve apenas para avaliar o fluxo. O sistema completo continua sendo a aplicação Python com servidor e controle de acesso.

Não é necessário desativar proteções do Windows. Este é um documento HTML interativo próprio, não um executável renomeado. Sua política institucional ainda pode limitar a abertura de arquivos locais.

Validação: as seis fases foram percorridas no Chromium, com rejeição de senha incorreta em todas as passagens, bloqueio da fase 2 sem hash, conferência local de SHA-256, registro de pedido e persistência após recarregar. Não houve erros JavaScript. O teste serviu o HTML por HTTP local; a navegação `file://` é proibida pela política do navegador deste ambiente e não foi validada aqui. Não foram alteradas as políticas do navegador.

Para regenerar e testar no ambiente de desenvolvimento:

```sh
python scripts/gerar_demo_navegador.py
python scripts/testar_demo_navegador.py
```
