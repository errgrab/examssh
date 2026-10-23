# Plano do projeto: ExamShell Rank 02

## Objetivo

Construir em Python um simulador local do fluxo do ExamShell/Grademe usado para praticar o Exam Rank 02 da 42. O candidato entra por SSH, lê uma introdução, inicia o exame com `examshell`, recebe o exercício atual e envia a solução pelo Git. Ao executar `grademe`, o sistema valida a revisão enviada e libera a questão seguinte quando ela passar.

O simulador reproduz o fluxo de estudo; não é um serviço oficial da 42 nem integra com a Moulinette.

## Escopo inicial (MVP)

- Uma sessão SSH em container, com Python e Git instalados.
- Na entrada, mostrar somente o `README.md` de boas-vindas e o prompt de shell.
- A conexão SSH inicia diretamente o prompt ExamShell, imprime o guia e mostra exercício/URL; não é necessário executar `examshell` manualmente.
- Comando `grademe` pergunta se o candidato já fez `git push`; após confirmação, clona o repositório em diretório temporário e avalia o último envio.
- Um exame fixo de cinco exercícios do conjunto público de Exam Rank 02, em progressão de dificuldade:
  1. `ft_strlen` — Level 1
  2. `ft_swap` — Level 1
  3. `first_word` — Level 1
  4. `last_word` — Level 2
  5. `wdmatch` — Level 2
- Os exercícios pedem implementações em C, para manter a prática alinhada ao exame; Python será usado para construir o simulador e o avaliador.
- `finish` encerra a sessão e exibe o resultado final.

Os nomes e níveis acima aparecem em repositórios públicos de preparação para o Exam Rank 02. Os enunciados do MVP serão mantidos em arquivos próprios e concisos, descrevendo requisitos e exemplos sem copiar soluções de terceiros.

## Fluxo do candidato

1. Conectar por SSH ao container com a conta de prática. O SSH força a entrada no prompt ExamShell e imprime o guia inicial.
2. No terminal normal da máquina do candidato, clonar uma vez o URL Git mostrado pelo ExamShell e trabalhar em `rendu/exam/<nome>/`. Consultar o enunciado em `subjects/subject/<nome>/README.md`.
3. Fazer `git add`, `git commit` e `git push` para esse mesmo repositório na máquina local.
4. Voltar à conexão SSH e executar `grademe`. Após confirmação, o avaliador clona o último push em diretório temporário, compila/executa os testes e informa aprovação ou erros.
6. Em caso de aprovação, o sistema adiciona o próximo enunciado em `subjects/subject/`, faz commit e push no repositório compartilhado e anuncia a questão seguinte no ExamShell. O candidato executa `git pull --rebase`. Em caso de reprovação, fica na questão atual e pode tentar novamente.
7. Após a quinta aprovação, informar conclusão; `finish` encerra a tentativa.

## Organização dos repositórios Git

O servidor expõe um único repositório bare, `exam.git`, clonado pelo candidato uma vez. Na raiz ficam `subjects/subject/<exercicio>/README.md` e `rendu/exam/<exercicio>/<arquivo>`. No início, somente o primeiro enunciado é publicado. Após uma aprovação, o ExamShell clona o mesmo repositório em área temporária, adiciona o próximo enunciado em `subjects/subject/`, faz commit e push de volta.

## Arquitetura proposta

- **`examshell` (Python CLI):** máquina de estados e prompt interativo para comandos do exame; persistência do estado da tentativa.
- **Catálogo de questões:** configuração declarativa com identificador, nível, caminho do enunciado, arquivos esperados, comando de compilação e suíte de testes.
- **Grademe:** pede confirmação do push, clona o repositório único em diretório temporário, compila e executa testes com limites básicos; após aprovação, publica o próximo enunciado via commit/push.
- **Servidor Git:** repositório bare único servido por Git daemon no ambiente local; a raiz contém `subjects/` e `rendu/`.
- **Container SSH:** imagem Docker com usuário de desenvolvimento, senha local, Python, Git e cliente C. O SSH força o comando ExamShell; o mesmo container executa o Git daemon e persiste os dados necessários.
- **Testes das questões:** casos do enunciado mais casos de borda, mantidos no código do avaliador. Este MVP local não trata os casos como segredo contra o usuário do container.

## Estrutura de arquivos prevista

```text
src/examshell/          # CLI, sessão, catálogo e avaliador
subjects/<id>/          # README.md e casos de avaliação por questão
deploy/                 # Dockerfile, configuração SSH e provisionamento Git
tests/                  # testes do simulador, Git e transições de sessão
README.md               # instalação e uso pelo mantenedor
PROJECT_PLAN.md         # este planejamento
```

O repositório inicial é gerado a partir do primeiro enunciado. Cada aprovação publica o próximo `subjects/<id>/README.md` no mesmo histórico onde ficam as submissões em `rendu/`.

## Fases de implementação

1. **Contrato do MVP:** fechar fluxo, comandos, nomes das pastas e critérios de aprovação; registrar casos de teste das cinco questões.
2. **CLI e sessão:** implementar `examshell`, estado persistente, apresentação de questão, `status` e `finish`.
3. **Git local:** provisionar um único `exam.git` com `subjects/` e `rendu/`; identificar commits enviados para a questão corrente.
4. **Grademe:** pedir confirmação, clonar o repositório enviado, testar em subprocesso com limites e publicar o próximo subject somente após aprovação.
5. **SSH e Docker Compose:** empacotar ambiente, README de entrada, usuário sem privilégios e instruções para os dois terminais.
6. **Validação ponta a ponta:** simular conexão SSH, clone, submissão aprovada, submissão reprovada, retry, progressão e conclusão.

## Estado do projeto

O MVP contém o container SSH, um repositório Git bare único com `subjects/` e `rendu/`, confirmação interativa do `grademe`, avaliação por clone temporário e publicação do próximo enunciado após aprovação. A validação ponta a ponta ainda precisa ser feita em um host com Docker Compose; o container não foi iniciado nesta etapa.

## Critérios de aceite

- Uma pessoa consegue entrar por SSH e entender o fluxo apenas pelo README inicial.
- `examshell` apresenta questão atual e URLs Git válidas no ambiente iniciado.
- Uma submissão sem `git push` não é avaliada como nova.
- `grademe` avalia o commit enviado, informa sucesso/falha e nunca avança em falha.
- Cada aprovação libera exatamente uma questão seguinte; ao concluir cinco, a sessão termina corretamente.
- A avaliação compila e executa em diretório temporário, com limites básicos de CPU, memória, tempo e tamanho de arquivo. Os casos ficam no código do MVP local e não devem ser tratados como segredo contra o próprio usuário do container.
- O ambiente pode ser inicializado e reiniciado de forma reproduzível por Docker Compose.

## Decisões e riscos em aberto

- **Isolamento do código submetido:** Docker sozinho não basta se o container de avaliação compartilhar permissões excessivas. Antes de aceitar código de terceiros, usar usuário sem privilégios, filesystem temporário, limites de CPU/memória/tempo e rede desativada no processo de teste.
- **Acesso Git:** para o MVP local, usar chaves por usuário ou credenciais de desenvolvimento documentadas; não reutilizar credenciais pessoais.
- **Persistência:** guardar estado da tentativa fora do container efêmero, associado ao usuário SSH e aos commits avaliados.
- **Autenticidade dos exercícios:** os cinco nomes são candidatos do Exam Rank 02; os requisitos funcionais devem ser revistos contra enunciados autorizados/disponíveis antes da implementação dos testes.
- **Modelo de uso:** o desenho assume prática local com Docker Compose e um único host. Hospedagem pública, múltiplos candidatos concorrentes e contas públicas ficam fora do MVP.

## Referências consultadas

- [Lista pública de exercícios por nível do Exam Rank 02](https://github.com/alexhiguera/Exam_Rank_02_42_School) — referência comunitária para nomes e níveis.
- [Exemplo público de fluxo ExamShell/Grademe e diretórios subject/Rendu](https://github.com/42-Yerevan-Armenia/Exam_Rank_02) — referência comunitária para o fluxo de comandos e submissão Git.


