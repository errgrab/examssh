"""Exercise definitions and private grading cases."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Exercise:
    slug: str
    level: int
    source: str
    description: str
    function_harness: str | None = None
    function_expected: str | None = None
    cases: tuple[tuple[tuple[str, ...], str], ...] = ()


EXERCISES = (
    Exercise(
        slug="ft_strlen",
        level=1,
        source="ft_strlen.c",
        description="Implemente ft_strlen para retornar o número de caracteres da string, sem contar o byte nulo final.",
        function_harness=(
            '#include <stdio.h>\n'
            'int ft_strlen(char *str);\n'
            'int main(void) { printf("%d\\n%d\\n", ft_strlen(""), ft_strlen("42 school")); return 0; }\n'
        ),
        function_expected="0\n9\n",
    ),
    Exercise(
        slug="ft_swap",
        level=1,
        source="ft_swap.c",
        description="Implemente ft_swap para trocar os valores apontados pelos dois ponteiros recebidos.",
        function_harness=(
            '#include <stdio.h>\n'
            'void ft_swap(int *a, int *b);\n'
            'int main(void) { int a = -3, b = 42; ft_swap(&a, &b); printf("%d %d\\n", a, b); return 0; }\n'
        ),
        function_expected="42 -3\n",
    ),
    Exercise(
        slug="first_word",
        level=1,
        source="first_word.c",
        description="Escreva um programa que imprima a primeira palavra do argumento, ignorando espaços e tabulações antes dela.",
        cases=(
            (("  hello   world",), "hello"),
            (("\t42 school",), "42"),
            (("   ",), ""),
        ),
    ),
    Exercise(
        slug="last_word",
        level=2,
        source="last_word.c",
        description="Escreva um programa que imprima a última palavra do argumento, ignorando espaços e tabulações ao redor.",
        cases=(
            (("hello   world  ",), "world"),
            (("one",), "one"),
            ((" \t ",), ""),
        ),
    ),
    Exercise(
        slug="wdmatch",
        level=2,
        source="wdmatch.c",
        description="Imprima a primeira string apenas quando todos os seus caracteres aparecem, na mesma ordem, na segunda string.",
        cases=(
            (("faya", "f this is a test y a"), "faya"),
            (("abc", "acb"), ""),
            (("42", "4--2"), "42"),
        ),
    ),
)


def by_slug(slug: str) -> Exercise:
    for exercise in EXERCISES:
        if exercise.slug == slug:
            return exercise
    raise KeyError(slug)

