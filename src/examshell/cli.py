#!/usr/bin/env python3
"""Command-line interface for the local Rank 02 practice exam."""

import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# sshd starts ForceCommand with a restricted environment and may drop PYTHONPATH.
# Resolve this entry point through the symlink so the package remains importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from examshell.catalog import EXERCISES
from examshell.grading import (
    GIT_URL,
    REPOSITORY,
    GradeError,
    grade,
    latest_commit,
    publish_next_subject,
)
from examshell.state import load_state, save_state


USERNAME = re.sub(r"[^a-zA-Z0-9_-]", "", os.environ.get("USER", "exam")) or "exam"
WELCOME = Path(__file__).with_name("ssh-README.md")


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or "Falha ao consultar o repositório Git.")
    return result


def _show_exercise(index: int) -> None:
    exercise = EXERCISES[index]
    print(f"\nQuestão {index + 1}/{len(EXERCISES)} — {exercise.slug} (Level {exercise.level})")
    print(exercise.description)
    print(f"\nEnunciado: subjects/subject/{exercise.slug}/README.md")
    print(f"Arquivo a enviar: rendu/{USERNAME}/{exercise.slug}/{exercise.source}")
    print(f"Repositório Git: {GIT_URL}")
    print("No terminal normal da sua máquina, clone/edite/envie o repositório; volte a esta conexão SSH para executar grademe.")
    print("Faça git add, git commit e git push antes de executar grademe.")
    if index > 0:
        print("Após a publicação do novo enunciado, atualize seu clone com: git pull --rebase")
    print()


def _start_exam() -> int:
    if WELCOME.is_file():
        print(WELCOME.read_text(encoding="utf-8"))
    if not REPOSITORY.is_dir():
        raise RuntimeError("O repositório do exame ainda não foi inicializado.")
    head = latest_commit()
    if head is None:
        raise RuntimeError("O repositório do exame não tem um commit inicial.")
    state = load_state()
    if state is None or state.get("finished"):
        state = {
            "username": USERNAME,
            "index": 0,
            "graded_commit": head,
            "finished": False,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        save_state(state)
        print("ExamShell Rank 02 iniciado. Boa prova!")
    if state["index"] >= len(EXERCISES):
        print("Todas as questões foram aprovadas. Execute finish para encerrar.")
        return 0
    _show_exercise(state["index"])
    return 0


def examshell() -> int:
    if _start_exam() != 0:
        return 1
    print("Digite grademe para avaliar, status para ver o progresso, finish para encerrar ou exit para sair do ExamShell.")
    while True:
        try:
            command = input("examshell> ").strip()
        except EOFError:
            print("\nSaindo do ExamShell. A sessão continua salva; reconecte por SSH para retornar.")
            return 0
        if command == "grademe":
            grademe()
        elif command == "status":
            status()
        elif command == "finish":
            finish()
            return 0
        elif command in {"exit", "quit"}:
            print("Saindo do ExamShell. A sessão continua salva; reconecte por SSH para retornar.")
            return 0
        elif command in {"help", "?"}:
            print("Comandos: grademe, status, finish, help, exit")
        elif command:
            print(f"Comando desconhecido: {command}. Digite help para ver os comandos disponíveis.")


def _confirm_grade() -> bool:
    try:
        answer = input("Verify that you made git push. Do you want to continue? [Y/N] ").strip()
    except EOFError:
        print("\nAvaliação cancelada.")
        return False
    if answer in {"Y", "y"}:
        return True
    print("Avaliação cancelada. Nenhum teste foi executado.")
    return False


def grademe() -> int:
    if not _confirm_grade():
        return 0
    state = load_state()
    if state is None or state.get("finished"):
        print("Nenhum exame ativo. Execute examshell primeiro.")
        return 1
    if state["index"] >= len(EXERCISES):
        print("Exame concluído. Execute finish para encerrar.")
        return 0

    commit = latest_commit()
    if commit is None:
        print("Ainda não há commit enviado. Faça git commit e git push antes de executar grademe.")
        return 1
    if commit == state.get("graded_commit"):
        print("Não encontrei um push novo desde a última avaliação. Envie sua solução com git push.")
        return 1

    exercise = EXERCISES[state["index"]]
    required_path = f"rendu/{USERNAME}/{exercise.slug}/{exercise.source}"
    changed = _git(
        "git", f"--git-dir={REPOSITORY}", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit
    ).stdout.splitlines()
    if required_path not in changed:
        print(f"O último commit enviado não contém {required_path}.")
        print("Adicione o arquivo ao repositório, faça commit e execute git push novamente.")
        return 1

    print(f"Clonando o repositório e avaliando {exercise.slug} no commit {commit[:8]}...")
    try:
        passed, feedback = grade(USERNAME, commit, exercise, GIT_URL)
    except GradeError as error:
        print(f"Não foi possível concluir a avaliação: {error}")
        return 1
    print(feedback)
    if not passed:
        print("Questão não aprovada. Corrija, faça um novo commit, envie com git push e tente novamente.")
        return 1

    next_index = state["index"] + 1
    if next_index < len(EXERCISES):
        next_slug = EXERCISES[next_index].slug
        try:
            published_commit = publish_next_subject(next_slug, GIT_URL)
        except GradeError as error:
            print(f"Solução aprovada, mas não consegui publicar o próximo subject: {error}")
            print("Execute grademe novamente para tentar concluir a publicação.")
            return 1
        state["graded_commit"] = published_commit
        state["index"] = next_index
        save_state(state)
        print(f"Questão aprovada. O subject {next_slug} foi enviado ao repositório Git.")
        _show_exercise(next_index)
        return 0

    state["graded_commit"] = commit
    state["index"] = next_index
    save_state(state)
    print("Parabéns! Você aprovou as cinco questões. Execute finish para encerrar.")
    return 0


def status() -> int:
    state = load_state()
    if state is None:
        print("Nenhum exame iniciado. Execute examshell.")
    elif state.get("finished"):
        print("Exame encerrado.")
    elif state["index"] >= len(EXERCISES):
        print(f"Exame concluído: {len(EXERCISES)}/{len(EXERCISES)} questões aprovadas.")
    else:
        print(f"Progresso: {state['index']}/{len(EXERCISES)} questões aprovadas.")
        print(f"Questão atual: {EXERCISES[state['index']].slug}.")
    return 0


def finish() -> int:
    state = load_state()
    if state is None:
        print("Nenhum exame iniciado.")
        return 0
    state["finished"] = True
    state["finished_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    print(f"Exame encerrado: {state['index']}/{len(EXERCISES)} questões aprovadas.")
    return 0


def main() -> int:
    command = Path(sys.argv[0]).name
    if command == "cli.py":
        command = sys.argv[1] if len(sys.argv) > 1 else "help"
    commands = {"examshell": examshell, "grademe": grademe, "status": status, "finish": finish}
    if command not in commands:
        print("Comandos disponíveis: examshell, grademe, status, finish")
        return 0 if command == "help" else 2
    try:
        return commands[command]()
    except (OSError, RuntimeError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

