"""Integrity of the ablation arms.

No API key, no runs: these check that each arm is the released artifact with exactly one
mechanism removed, so a mis-applied patch cannot reach a paid experiment. Structure is
checked on the parsed AST rather than by grepping text, because a comment or a string
mentioning a mechanism is not the mechanism.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ABLATION = ROOT / "experiments" / "ablation"
ARMS = ABLATION / "arms"
UPSTREAM = ABLATION / "upstream" / "artifact" / "agent.py"

ARM_NAMES = ("full", "no_bootstrap", "no_haiku_json", "no_cancelled", "baseline")

needs_arms = pytest.mark.skipif(
    not (ARMS / "full" / "agent.py").exists(),
    reason="run `make arms` to fetch upstreams and build the arms",
)


def tree(arm: str) -> ast.Module:
    return ast.parse((ARMS / arm / "agent.py").read_text())


def find_function(module: ast.Module, name: str) -> ast.AsyncFunctionDef | ast.FunctionDef:
    for node in ast.walk(module):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"{name} not found")


def counts_cancelled(module: ast.Module) -> int:
    return sum(
        1
        for node in ast.walk(module)
        if isinstance(node, ast.Attribute)
        and node.attr == "CancelledError"
        and isinstance(node.value, ast.Name)
        and node.value.id == "asyncio"
    )


def has_json_str_decode(module: ast.Module, variable: str = "cmds") -> bool:
    """The Haiku fix: `if isinstance(cmds, str): ... json.loads(cmds)`.

    The subject variable is matched explicitly. A looser test also catches the unrelated
    `isinstance(arguments_str, str)` block a few lines above, which decodes tool-call
    arguments and must survive every arm.
    """
    for node in ast.walk(module):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            isinstance(test, ast.Call)
            and isinstance(test.func, ast.Name)
            and test.func.id == "isinstance"
            and len(test.args) == 2
            and isinstance(test.args[0], ast.Name)
            and test.args[0].id == variable
            and isinstance(test.args[1], ast.Name)
            and test.args[1].id == "str"
        ):
            if any(
                isinstance(n, ast.Attribute) and n.attr == "loads" for n in ast.walk(node)
            ):
                return True
    return False


@needs_arms
@pytest.mark.parametrize("arm", ARM_NAMES)
def test_every_arm_is_valid_python(arm):
    tree(arm)


@needs_arms
def test_full_arm_is_byte_identical_to_upstream():
    assert (ARMS / "full" / "agent.py").read_bytes() == UPSTREAM.read_bytes()


@needs_arms
@pytest.mark.parametrize("arm", ARM_NAMES)
def test_every_arm_keeps_the_entry_point(arm):
    classes = {n.name for n in ast.walk(tree(arm)) if isinstance(n, ast.ClassDef)}
    assert "AgentHarness" in classes, "harbor imports agent:AgentHarness"


@needs_arms
def test_bootstrap_is_off_before_any_await():
    """The ablated snapshot must short-circuit, not merely be unused."""
    fn = find_function(tree("no_bootstrap"), "_gather_env_snapshot")
    body = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]

    first = body[0]
    assert isinstance(first, ast.Return), "first statement should be an unconditional return"
    assert isinstance(first.value, ast.Constant) and first.value.value == ""

    # Nothing may execute before it -- an await here would still cost a sandbox round trip.
    preceding = ast.Module(body=[first], type_ignores=[])
    assert not any(isinstance(n, ast.Await) for n in ast.walk(preceding))


@needs_arms
def test_bootstrap_remains_live_in_other_arms():
    for arm in ("full", "no_haiku_json", "no_cancelled"):
        fn = find_function(tree(arm), "_gather_env_snapshot")
        assert any(isinstance(n, ast.Await) for n in ast.walk(fn)), f"{arm} lost bootstrapping"


@needs_arms
def test_haiku_fix_present_only_where_expected():
    assert has_json_str_decode(tree("full"))
    assert not has_json_str_decode(tree("no_haiku_json"))
    assert not has_json_str_decode(tree("baseline"))
    assert has_json_str_decode(tree("no_bootstrap")), "unrelated arm must keep it"


@needs_arms
def test_cancelled_handling_present_only_where_expected():
    assert counts_cancelled(tree("full")) == 2
    assert counts_cancelled(tree("no_cancelled")) == 0
    assert counts_cancelled(tree("baseline")) == 0
    assert counts_cancelled(tree("no_bootstrap")) == 2


@needs_arms
def test_baseline_has_all_three_mechanisms_off():
    module = tree("baseline")
    fn = find_function(module, "_gather_env_snapshot")
    assert isinstance(fn.body[1], ast.Return)
    assert counts_cancelled(module) == 0
    assert not has_json_str_decode(module)


@needs_arms
def test_patches_refuse_to_apply_to_modified_upstream(tmp_path):
    """A silently mis-applied patch is the failure mode that would poison a paid run."""
    fake = tmp_path / "upstream" / "artifact"
    fake.mkdir(parents=True)
    (fake / "prompt-templates").mkdir()
    (fake / "prompt-templates" / "terminus-kira.txt").write_text("x")
    (fake / "anthropic_caching.py").write_text("")
    (fake / "pyproject.toml").write_text("")
    (fake / "agent.py").write_text("class AgentHarness:\n    pass\n")

    result = subprocess.run(
        [sys.executable, str(ABLATION / "make_arms.py"),
         "--upstream", str(tmp_path / "upstream"), "--out", str(tmp_path / "arms")],
        capture_output=True, text=True,
    )

    assert result.returncode != 0
    assert "Upstream has changed" in (result.stdout + result.stderr)


@needs_arms
def test_unrelated_argument_decoding_survives_every_arm():
    """The adjacent `isinstance(arguments_str, str)` block is not part of any mechanism."""
    for arm in ARM_NAMES:
        assert has_json_str_decode(tree(arm), variable="arguments_str"), arm


@needs_arms
def test_ablated_arms_carry_no_comment_for_a_removed_mechanism():
    """A stale comment would mislead anyone auditing which arm is which."""
    for arm in ("no_haiku_json", "baseline"):
        text = (ARMS / arm / "agent.py").read_text()
        assert "Haiku sometimes double-encodes" not in text, arm
