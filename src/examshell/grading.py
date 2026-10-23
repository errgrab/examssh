"""Clone the single exam repository, grade a submitted exercise, and publish the next subject."""

import os
import resource
import shutil
import subprocess
import tempfile
from pathlib import Path

from examshell.catalog import Exercise


GIT_ROOT = Path(os.environ.get("EXAMSHELL_GIT_ROOT", "/var/lib/examshell/git"))
REPOSITORY = GIT_ROOT / "exam.git"
SUBJECT_SOURCE_ROOT = Path("/opt/examshell/subjects")
GIT_URL = os.environ.get("EXAMSHELL_GIT_URL", "git://localhost:9418/exam.git")


class GradeError(Exception):
    pass


def latest_commit() -> str | None:
    result = subprocess.run(
        ["git", f"--git-dir={REPOSITORY}", "rev-parse", "--verify", "refs/heads/master"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024, 128 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024, 64 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))


def _run(command: list[str], *, cwd: Path, timeout: float = 4) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            preexec_fn=_limits,
        )
    except subprocess.TimeoutExpired as exc:
        raise GradeError("Tempo limite excedido durante a compilação ou execução.") from exc


def _clone_exam_repo(repository_url: str, destination: Path) -> None:
    result = subprocess.run(
        ["git", "clone", "--branch", "master", "--single-branch", repository_url, str(destination)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode:
        raise GradeError("Não consegui clonar o repositório do exame: " + (result.stderr.strip() or "erro Git"))


def grade(username: str, commit: str, exercise: Exercise, repository_url: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="examshell-grade-") as temp_dir:
        work = Path(temp_dir)
        checkout = work / "exam"
        _clone_exam_repo(repository_url, checkout)
        cloned_commit = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if cloned_commit != commit:
            raise GradeError("O repositório mudou durante a avaliação. Execute grademe novamente.")

        source_path = checkout / "rendu" / username / exercise.slug / exercise.source
        if not source_path.is_file():
            raise GradeError(f"Não encontrei rendu/{username}/{exercise.slug}/{exercise.source} no push.")
        candidate = work / exercise.source
        shutil.copyfile(source_path, candidate)
        binary = work / "candidate"

        if exercise.function_harness is not None:
            harness = work / "grader.c"
            harness.write_text(exercise.function_harness, encoding="utf-8")
            compile_result = _run(
                ["gcc", "-Wall", "-Wextra", "-Werror", str(candidate), str(harness), "-o", str(binary)],
                cwd=work,
            )
            expected = exercise.function_expected or ""
            if compile_result.returncode != 0:
                return False, _short(compile_result.stderr or compile_result.stdout or "Falha de compilação.")
            result = _run([str(binary)], cwd=work)
            if result.returncode != 0:
                return False, f"O programa terminou com código {result.returncode}."
            if result.stdout != expected:
                return False, f"Saída inesperada. Esperado: {expected!r}; recebido: {result.stdout!r}."
            return True, "Todos os casos passaram."

        compile_result = _run(
            ["gcc", "-Wall", "-Wextra", "-Werror", str(candidate), "-o", str(binary)],
            cwd=work,
        )
        if compile_result.returncode != 0:
            return False, _short(compile_result.stderr or compile_result.stdout or "Falha de compilação.")
        for arguments, expected in exercise.cases:
            result = _run([str(binary), *arguments], cwd=work)
            if result.returncode != 0:
                return False, f"O programa terminou com código {result.returncode} no caso {arguments!r}."
            if result.stdout.rstrip("\n") != expected:
                return False, f"Caso {arguments!r}: esperado {expected!r}, recebido {result.stdout!r}."
        return True, f"Todos os {len(exercise.cases)} casos passaram."


def publish_next_subject(slug: str, repository_url: str) -> str:
    """Add the next exercise to subjects/ in a fresh clone and push it to the single repo."""
    source = SUBJECT_SOURCE_ROOT / slug
    with tempfile.TemporaryDirectory(prefix="examshell-publish-") as temp_dir:
        checkout = Path(temp_dir) / "exam"
        _clone_exam_repo(repository_url, checkout)
        destination = checkout / "subjects" / "subject" / slug
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, destination)
            add = subprocess.run(
                ["git", "-C", str(checkout), "add", str(destination.relative_to(checkout))],
                capture_output=True,
                text=True,
                check=False,
            )
            if add.returncode:
                raise GradeError(add.stderr.strip() or "Não consegui preparar o próximo enunciado.")
            commit = subprocess.run(
                ["git", "-C", str(checkout), "commit", "-m", f"Publish subject {slug}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if commit.returncode:
                raise GradeError(commit.stderr.strip() or "Não consegui criar o commit do próximo enunciado.")
            push = subprocess.run(
                ["git", "-C", str(checkout), "push", "origin", "master"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if push.returncode:
                raise GradeError(push.stderr.strip() or "Não consegui enviar o próximo enunciado ao Git.")

    commit_result = subprocess.run(
        ["git", f"--git-dir={REPOSITORY}", "rev-parse", "--verify", "refs/heads/master"],
        capture_output=True,
        text=True,
        check=False,
    )
    if commit_result.returncode:
        raise GradeError("Não consegui ler o commit publicado no repositório.")
    return commit_result.stdout.strip()


def _short(text: str, limit: int = 1200) -> str:
    normalized = text.strip()
    if len(normalized) > limit:
        normalized = normalized[:limit] + "…"
    return normalized

