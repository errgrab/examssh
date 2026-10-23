# ExamShell Rank 02 — simulador local

MVP em Python para praticar o fluxo ExamShell/Grademe do Exam Rank 02. A sessão acontece em um container acessado por SSH. Um repositório Git contém `subjects/` e `rendu/`: o candidato lê os enunciados, envia a solução e chama `grademe` para avaliar o push.

O conteúdo usa exercícios conhecidos do Exam Rank 02, com enunciados próprios e resumidos. Este projeto não é oficial nem afiliado à 42.

## Requisitos

- Docker Desktop com Docker Compose v2.
- Cliente SSH e Git no computador.

## Iniciar

Na pasta do projeto:

```powershell
docker compose up --build -d
ssh -p 2222 exam@127.0.0.1
```

Na primeira conexão, confirme a chave de host. Use a conta `exam` e a senha local padrão `exam`. Para mudar a senha, defina `EXAM_PASSWORD` antes de iniciar o Compose. O SSH entra diretamente no prompt ExamShell e imprime as instruções; não é necessário executar `examshell`. As portas ficam limitadas ao loopback local.

Em um terminal normal da sua máquina (fora da conexão SSH), clone uma vez o URL Git apresentado pelo ExamShell:

```sh
git clone git://localhost:9418/exam.git
cd exam
```

O repositório contém as pastas `subjects/` e `rendu/`. Leia o enunciado em `subjects/subject/<exercicio>/README.md`. Crie o arquivo C no caminho de submissão indicado pelo `examshell` e envie:

```sh
mkdir -p rendu/exam/ft_strlen
# crie rendu/exam/ft_strlen/ft_strlen.c
git add rendu/exam/ft_strlen
git commit -m "solve ft_strlen"
git push origin master
```

Volte à conexão SSH, que está no prompt `examshell>`, e execute `grademe`. Ele pergunta `Verify that you made git push. Do you want to continue? [Y/N]`. Responda `Y` para o avaliador clonar o repositório em um diretório temporário e testar o último push. Se falhar, corrija, faça novo commit e push no terminal normal da sua máquina. Se passar, o ExamShell publica o próximo enunciado em `subjects/subject/` e apresenta a próxima questão. Atualize o clone local com `git pull --rebase`. O prompt ExamShell aceita `grademe`, `status`, `finish`, `help` e `exit`.

## Questões incluídas

`ft_strlen`, `ft_swap`, `first_word`, `last_word` e `wdmatch`, nessa ordem.

## Parar e apagar os dados

```powershell
docker compose down
```

As submissões e sessões ficam no volume Docker `exam-data` e sobrevivem a esse comando. Para apagar esse volume e os dados locais da prática:

```powershell
docker compose down --volumes
```

## Limites deste MVP

O MVP é para um candidato local por vez. O serviço usa senha de desenvolvimento (`exam` por padrão) e Git daemon sem autenticação para funcionar sem configuração de chaves. Embora as portas estejam limitadas a `127.0.0.1`, não exponha o container na internet nem use para avaliar código de pessoas não confiáveis. O avaliador aplica limites básicos de tempo, memória e tamanho de arquivo, mas ainda executa C no mesmo container. Para hospedagem multiusuário, será necessário separar o worker de avaliação em isolamento mais forte, autenticar o Git e proteger o estado das sessões.

