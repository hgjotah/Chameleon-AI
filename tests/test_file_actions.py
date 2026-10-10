import asyncio
import time
from pathlib import Path

import pytest

from chameleon.core.config import Config
from chameleon.core.context import Context
from chameleon.core.engine import Engine
from chameleon.core.files import apply_file_action
from chameleon.core.intents import local_plan, refine_request
from chameleon.core.schemas import Action, Plan
from chameleon.safety.engine import Risk, RiskEngine


class NoInference:
    async def plan(self, request: str, context: Context) -> Plan:
        pytest.fail("A common file action invoked the model")


@pytest.mark.parametrize("phrase,name,content", [
    ('crea un archivo llamado prueba.txt', 'prueba.txt', ''),
    ('créame un archivo llamado "Niño & 100% !.txt" con contenido "Hola, acción & echo MAL"', 'Niño & 100% !.txt', 'Hola, acción & echo MAL'),
    ('create a file named hello.txt with content "Hello"', 'hello.txt', 'Hello'),
    ('crea un archivo "con espacios.txt" que contenga "uno\ndos"', 'con espacios.txt', 'uno\ndos'),
])
def test_create_literal_without_inference(tmp_path: Path, phrase: str, name: str, content: str) -> None:
    start = time.monotonic()
    plan, risk = asyncio.run(Engine(Config(), NoInference()).plan(phrase, Context(cwd=str(tmp_path))))
    assert time.monotonic() - start < 2
    assert plan.actions[0].kind == 'create' and risk.level == Risk.CONFIRM
    apply_file_action(plan.actions[0])
    assert (tmp_path / name).read_bytes() == content.encode('utf-8')


def test_create_known_directory(tmp_path: Path) -> None:
    desktop = tmp_path / 'Escritorio'
    desktop.mkdir()
    ctx = Context(cwd=str(tmp_path), known_directories={'Desktop': str(desktop)})
    plan = local_plan('crea un archivo llamado notas.txt en el escritorio con texto "hola"', ctx)
    assert plan
    apply_file_action(plan.actions[0])
    assert (desktop / 'notas.txt').read_text() == 'hola'


def test_clarification_preserves_creation(tmp_path: Path) -> None:
    original = 'crea un archivo'
    ctx = Context(cwd=str(tmp_path))
    plan = local_plan(original, ctx)
    assert plan and plan.intent == 'clarify'
    refined = local_plan(refine_request(original, 'test.txt', plan), ctx)
    assert refined and refined.actions[0].kind == 'create'
    assert refined.actions[0].path == str(tmp_path / 'test.txt')


def test_no_overwrite_even_after_approval(tmp_path: Path) -> None:
    target = tmp_path / 'keep.txt'
    action = Action(kind='create', path=str(target), content='new')
    assert RiskEngine().action(action, tmp_path).level == Risk.CONFIRM
    target.write_text('keep')
    assert RiskEngine().action(action, tmp_path).level == Risk.BLOCKED
    with pytest.raises(FileExistsError):
        apply_file_action(action)
    assert target.read_text() == 'keep'


def test_mkdir_copy_move_and_missing_parent(tmp_path: Path) -> None:
    ctx = Context(cwd=str(tmp_path))
    for request in ('crea una carpeta llamada proyecto', 'crea un archivo llamado original.txt con texto "contenido"', 'copia original.txt a proyecto/copia.txt', 'mueve original.txt a renombrado.txt'):
        plan = local_plan(request, ctx)
        assert plan
        apply_file_action(plan.actions[0])
    assert (tmp_path / 'proyecto/copia.txt').read_text() == 'contenido'
    assert (tmp_path / 'renombrado.txt').read_text() == 'contenido'
    assert not (tmp_path / 'original.txt').exists()
    action = Action(kind='create', path=str(tmp_path / 'missing/file.txt'))
    decision = RiskEngine().action(action, tmp_path)
    assert decision.level == Risk.BLOCKED and 'carpeta de destino' in decision.reason


@pytest.mark.parametrize('name', ['CON.txt', 'NUL', 'LPT1.log', 'file:stream', 'bad?.txt', 'trailing.'])
@pytest.mark.windows
def test_invalid_windows_target(tmp_path: Path, name: str) -> None:
    assert RiskEngine().action(Action(kind='create', path=str(tmp_path / name)), tmp_path).level == Risk.BLOCKED


def test_model_admin_flag_cannot_block_normal_file(tmp_path: Path) -> None:
    plan = Plan(intent='execute', shell='cmd', summary='Create a user file', requires_admin=True,
                actions=[Action(kind='create', path=str(tmp_path / 'normal.txt'))])
    decision = RiskEngine().assess(plan, tmp_path)
    assert decision.level == Risk.CONFIRM and not decision.requires_admin


def test_system_creation_blocked(tmp_path: Path) -> None:
    action = Action(kind='create', path='C:\\Windows\\System32\\new.txt')
    assert RiskEngine().action(action, tmp_path).level == Risk.BLOCKED


def test_creation_rejects_conflicting_destination(tmp_path: Path) -> None:
    # The reviewed target and the written file must describe the same path.
    with pytest.raises(ValueError, match="Destination is only valid"):
        Action(kind="create", path='C:\\Windows\\System32\\new.txt',
               destination=str(tmp_path / "other.txt"))


def test_review_escapes_terminal_controls_but_preserves_file_content(tmp_path: Path) -> None:
    from chameleon.platform.windows.shells import describe_action

    action = Action(kind="create", path=str(tmp_path / "literal.html"), content="<b>literal</b>\x1b[2J")
    preview = describe_action(action, tmp_path)
    assert "<b>literal</b>" in preview and "\\x1b[2J" in preview and "\x1b" not in preview
    apply_file_action(action)
    assert (tmp_path / "literal.html").read_text() == action.content
