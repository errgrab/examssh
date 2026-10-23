#!/usr/bin/env python3
"""Command-line interface for the local Rank 02 practice exam."""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# sshd starts ForceCommand with a restricted environment and may drop PYTHONPATH.
# Resolve this entry point through the symlink so the package remains importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from examshell.profiles import ExamMode, UserProfile, get_exam_mode, get_user_profile
from examshell.grading import (
    REPOSITORY,
    GradeError,
    ensure_user_repository,
    grade,
    git_url_for_user,
    latest_commit,
    publish_next_subject,
    repository_for_user,
)
from examshell.state import load_state, save_state


WELCOME = Path(__file__).with_name("ssh-README.md")
ACTIVE_PROFILE: UserProfile | None = None


def _active_mode() -> ExamMode:
    if ACTIVE_PROFILE is None:
        raise RuntimeError("Faça login antes de usar os comandos do ExamShell.")
    return get_exam_mode(ACTIVE_PROFILE.mode)


def _active_state() -> dict | None:
    if ACTIVE_PROFILE is None:
        return None
    return load_state(ACTIVE_PROFILE.login)


def _active_git_url(*, public: bool = False) -> str:
    if ACTIVE_PROFILE is None:
        raise RuntimeError("Faça login antes de consultar o repositório Git.")
    return git_url_for_user(ACTIVE_PROFILE.login, public=public)


def _login() -> bool:
    global ACTIVE_PROFILE
    while ACTIVE_PROFILE is None:
        try:
            login = input("Login (trial/normal): ").strip()
        except EOFError:
            print("\nLogin cancelado.")
            return False
        profile = get_user_profile(login)
        if profile is None:
            print("Login desconhecido. Use trial ou normal.")
            continue
        ACTIVE_PROFILE = profile
    print(f"Login: {ACTIVE_PROFILE.login} — modo {ACTIVE_PROFILE.mode}.")
    return True


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or "Falha ao consultar o repositório Git.")
    return result


def _commit_exists(repository: Path, commit: str | None) -> bool:
    if not commit:
        return False
    return _git(
        "git", f"--git-dir={repository}", "cat-file", "-e", f"{commit}^{{commit}}", check=False
    ).returncode == 0


def _show_exercise(index: int, exercises: tuple) -> None:
    exercise = exercises[index]
    print(f"\nQuestão {index + 1}/{len(exercises)} — {exercise.slug} (Level {exercise.level})")
    print(exercise.description)
    print(f"\nEnunciado: subjects/{exercise.slug}/subject.en.md")
    print(f"Arquivo a enviar: rendu/{exercise.slug}/{exercise.source}")
    print(f"Repositório Git: {_active_git_url(public=True)}")
    print("No terminal normal da sua máquina, clone/edite/envie o repositório; volte a esta conexão SSH para executar grademe.")
    print("Faça git add, git commit e git push antes de executar grademe.")
    if index > 0:
        print("Após a publicação do novo enunciado, atualize seu clone com: git pull --rebase")
    print()


def _start_exam() -> int:
    if not _login():
        return 1
    if WELCOME.is_file():
        print(WELCOME.read_text(encoding="utf-8"))
    if not REPOSITORY.is_dir():
        raise RuntimeError("O repositório do exame ainda não foi inicializado.")
    user_repository = ensure_user_repository(ACTIVE_PROFILE.login)
    head = latest_commit(user_repository)
    if head is None:
        raise RuntimeError("O repositório do exame não tem um commit inicial.")
    mode = _active_mode()
    state = load_state(ACTIVE_PROFILE.login, migrate_legacy=ACTIVE_PROFILE.login == "trial")
    if state is None or state.get("finished"):
        state = {
            "username": ACTIVE_PROFILE.login,
            "mode": mode.name,
            "index": 0,
            "graded_commit": head,
            "finished": False,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "results": [],
            "attempts": [],
        }
        save_state(state)
        print(f"ExamShell Rank 02 ({mode.name}) iniciado. Boa prova!")
    elif not _commit_exists(user_repository, state.get("graded_commit")):
        state["graded_commit"] = head
        save_state(state)
    _ensure_results(state, mode.exercises)
    if state["index"] >= len(mode.exercises):
        correct = sum(result["passed"] for result in state["results"])
        print(f"Exame concluído: {correct}/{len(mode.exercises)} questões corretas. Execute finish para encerrar.")
        return 0
    _show_exercise(state["index"], mode.exercises)
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


def _ensure_results(state: dict, exercises: tuple) -> None:
    """Backfill sessions created before per-question outcomes were recorded."""
    if "results" not in state:
        state["results"] = [
            {"slug": exercises[index].slug, "passed": True, "commit": None, "feedback": "Aprovada em sessão anterior."}
            for index in range(min(state.get("index", 0), len(exercises)))
        ]
        state.setdefault("attempts", [])
        state.setdefault("mode", ACTIVE_PROFILE.mode if ACTIVE_PROFILE else "trial")
        save_state(state)


def grademe() -> int:
    if not _confirm_grade():
        return 0
    state = _active_state()
    if state is None or state.get("finished"):
        print("Nenhum exame ativo. Execute examshell primeiro.")
        return 1
    mode = _active_mode()
    exercises = mode.exercises
    if state["index"] >= len(exercises):
        print("Exame concluído. Execute finish para encerrar.")
        return 0
    _ensure_results(state, exercises)

    commit = latest_commit(repository_for_user(ACTIVE_PROFILE.login))
    if commit is None:
        print("Ainda não há commit enviado. Faça git commit e git push antes de executar grademe.")
        return 1
    if commit == state.get("graded_commit"):
        print("Não encontrei um push novo desde a última avaliação. Envie sua solução com git push.")
        return 1

    exercise = exercises[state["index"]]
    required_path = f"rendu/{exercise.slug}/{exercise.source}"
    changed = _git(
        "git", f"--git-dir={repository_for_user(ACTIVE_PROFILE.login)}", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit
    ).stdout.splitlines()
    if required_path not in changed:
        print(f"O último commit enviado não contém {required_path}.")
        print("Adicione o arquivo da questão, faça commit e push; a questão continua aberta.")
        return 1

    print(f"Clonando o repositório e avaliando {exercise.slug} no commit {commit[:8]}...")
    try:
        passed, feedback = grade(commit, exercise, _active_git_url())
    except GradeError as error:
        print(f"Não foi possível concluir a avaliação: {error}")
        return 1
    print(feedback)

    next_index = state["index"] + 1
    result_record = {
        "slug": exercise.slug,
        "passed": passed,
        "commit": commit,
        "feedback": feedback,
        "graded_at": datetime.now(timezone.utc).isoformat(),
    }
    attempt_record = dict(result_record)
    state.setdefault("attempts", []).append(attempt_record)
    if not passed and not mode.advance_on_failure:
        state["graded_commit"] = commit
        save_state(state)
        print("Questão não aprovada. O modo normal mantém a questão atual; corrija a solução, faça outro commit e push, e tente novamente.")
        return 0

    if next_index < len(exercises):
        next_slug = exercises[next_index].slug
        try:
            published_commit = publish_next_subject(
                next_slug, _active_git_url(), repository_for_user(ACTIVE_PROFILE.login)
            )
        except GradeError as error:
            outcome = "correta" if passed else "incorreta"
            print(f"Solução avaliada como {outcome}, mas não consegui publicar o próximo subject: {error}")
            print("Execute grademe novamente para concluir a avaliação e avançar.")
            return 1
        state["graded_commit"] = published_commit
        state["index"] = next_index
        state["results"].append(result_record)
        save_state(state)
        if passed:
            print(f"Questão marcada como correta. O subject {next_slug} foi enviado ao repositório Git.")
        else:
            print(f"Questão marcada como errada no modo trial. O subject {next_slug} foi enviado ao repositório Git.")
        _show_exercise(next_index, exercises)
        return 0

    state["graded_commit"] = commit
    state["index"] = next_index
    state["results"].append(result_record)
    save_state(state)
    correct = sum(result["passed"] for result in state["results"])
    print(f"Exame concluído: {correct}/{len(exercises)} questões corretas. Execute finish para encerrar.")
    return 0


def status() -> int:
    state = _active_state()
    if state is None:
        print("Nenhum exame iniciado. Execute examshell.")
    elif state.get("finished"):
        print("Exame encerrado.")
    elif state["index"] >= len(_active_mode().exercises):
        _ensure_results(state, _active_mode().exercises)
        correct, wrong = _score(state)
        print(f"Exame concluído: {correct} corretas, {wrong} erradas de {len(_active_mode().exercises)} questões.")
    else:
        exercises = _active_mode().exercises
        _ensure_results(state, exercises)
        correct, wrong = _score(state)
        print(f"Progresso: {state['index']}/{len(exercises)} avaliadas — {correct} corretas, {wrong} erradas.")
        print(f"Questão atual: {exercises[state['index']].slug}.")
        attempts = [attempt for attempt in state.get("attempts", []) if attempt.get("slug") == exercises[state["index"]].slug]
        if attempts and not _active_mode().advance_on_failure:
            print(f"Tentativas nesta questão: {len(attempts)}.")
    return 0


def _score(state: dict) -> tuple[int, int]:
    results = state.get("results", [])
    correct = sum(bool(result.get("passed")) for result in results)
    return correct, len(results) - correct


def finish() -> int:
    state = _active_state()
    if state is None:
        print("Nenhum exame iniciado.")
        return 0
    state["finished"] = True
    state["finished_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    _ensure_results(state, _active_mode().exercises)
    correct, wrong = _score(state)
    print(f"Exame encerrado: {correct} corretas, {wrong} erradas de {len(state.get('results', []))} questões avaliadas.")
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
    except (OSError, RuntimeError, GradeError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
