# ExamShell Rank 02 — ambiente local de prática

Esta conexão SSH já é o ExamShell. Ela inicia diretamente o exame e mostra este guia; não é preciso executar `examshell` manualmente. A conta de acesso é `exam` e a senha padrão local é `exam`.

## Como funciona

- O prompt `examshell>` aceita `grademe`, `status`, `finish`, `help` e `exit`.
- Os enunciados e suas soluções ficam em um único repositório Git, organizado nas pastas `subjects/` e `rendu/`.
- O clone e a edição acontecem no terminal normal da sua máquina, fora desta conexão SSH.
- O comando `grademe` pergunta se você já fez `git push`. Responda `Y` para confirmar. O avaliador clona o repositório, testa a solução e retorna o resultado.
- Após aprovação, o ExamShell publica o próximo enunciado no mesmo repositório e apresenta a questão seguinte.

## Preparar o repositório na sua máquina

Copie o URL mostrado abaixo e execute no terminal normal do computador:

```sh
git clone git://localhost:9418/exam.git
cd exam
```

Na pasta clonada, leia `subjects/subject/<exercicio>/README.md` e crie a solução no caminho `rendu/exam/<exercicio>/` indicado pelo ExamShell. Depois faça commit e push:

```sh
git add rendu/exam/<exercicio>
git commit -m "solve <exercicio>"
git push origin master
```

Volte a esta conexão SSH e digite `grademe`. Se a questão passar, atualize o clone na sua máquina antes de começar a próxima:

```sh
git pull --rebase
```

Este simulador é um projeto independente, não oficial da 42. Use somente no ambiente local de prática fornecido pelo Docker Compose.

