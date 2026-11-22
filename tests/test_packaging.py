"""Revisa que la imagen de Docker lleve todo lo que la API necesita en Lambda.

`.dockerignore` excluye todo (`*`) y vuelve a incluir solo algunos archivos con `!`. Si se
agrega un archivo nuevo a la API y no se permite aquí, funciona en local pero falla en AWS.
"""

from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).resolve().parents[1]


def dockerignore_rules() -> list[tuple[bool, str]]:
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    rules = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    return [(rule.startswith("!"), rule.removeprefix("!")) for rule in rules]


def is_excluded(path: str) -> bool:
    """Igual que Docker: la última regla que coincide gana, y excluir una carpeta excluye
    todo lo que tiene dentro. `*` no cruza carpetas."""
    parts = PurePosixPath(path).parts
    candidates = ["/".join(parts[: i + 1]) for i in range(len(parts))]
    excluded = False
    for negated, pattern in dockerignore_rules():
        if any(PurePosixPath(c).full_match(pattern) for c in candidates):
            excluded = not negated
    return excluded


@pytest.mark.parametrize(
    "path",
    [
        "requirements.txt",
        "requirements-api.txt",
        "src/recommender/pipeline.py",
        "api/main.py",
        "api/handler.py",
        "api/static/index.html",
    ],
)
def test_image_includes_what_the_api_needs(path):
    assert (ROOT / path).exists()
    assert not is_excluded(path)


@pytest.mark.parametrize(
    "path",
    ["models/recommender.joblib", "data/raw/dataset.csv", ".venv/pyvenv.cfg", "infra/main.tf"],
)
def test_image_leaves_out_data_models_and_infra(path):
    assert is_excluded(path)
