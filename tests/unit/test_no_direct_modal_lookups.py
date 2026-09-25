"""Every remote call goes through modal_compute_layer, so it can run on Modal or Brev.

A direct `modal.Function.from_name(...)` (or `Cls.from_name`, `FunctionCall.from_id`)
in backend code pins that call to Modal: when Modal is out of budget the job fails
even with a Brev instance up, and its result never says where it ran. On 2026-09-24
all 53 such lookups were routed through the layer; this guard keeps it that way.

Checked on the AST, so a docstring or comment that mentions from_name is not a hit.
Code that runs INSIDE a Modal container (an @app.function body) may still look up
another app directly -- there the Brev worker's shim resolves it in-process.
"""

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROUTER = {"src/backend/modal_compute_layer.py"}
LOOKUPS = {
    ("Function", "from_name"),
    ("Function", "lookup"),
    ("Cls", "from_name"),
    ("Cls", "lookup"),
    ("FunctionCall", "from_id"),
}
REMOTE_DECORATORS = {"function", "cls", "method", "asgi_app", "web_endpoint", "fastapi_endpoint"}


def _runs_in_container(node, parents):
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for d in node.decorator_list:
                t = d.func if isinstance(d, ast.Call) else d
                if isinstance(t, ast.Attribute) and t.attr in REMOTE_DECORATORS:
                    return True
    return False


def _direct_lookups(root=REPO):
    hits = []
    for base in ("src/backend", "src/mcp"):
        for p in sorted((root / base).rglob("*.py")):
            rel = str(p.relative_to(root))
            if rel in ROUTER:
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError) as e:
                if p.parent.name == "scripts" and p.name.startswith("bioql_job_"):
                    continue  # generated per-job execution scripts, saved as submitted; nothing imports them
                # Any other unreadable file is unchecked, not clean: say so instead of skipping it.
                hits.append(f"{rel}: not checked ({type(e).__name__})")
                continue
            parents = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
            for n in ast.walk(tree):
                if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
                    continue
                b = n.func.value
                owner = b.attr if isinstance(b, ast.Attribute) else getattr(b, "id", None)
                if (owner, n.func.attr) in LOOKUPS and not _runs_in_container(n, parents):
                    hits.append(f"{rel}:{n.lineno} {owner}.{n.func.attr}")
    return hits


def test_no_backend_code_looks_up_a_modal_function_directly():
    hits = _direct_lookups()
    assert not hits, (
        "use modal_compute_layer.function / .cls / .call_from_id instead, so the call "
        "can run on Modal or Brev and report where it ran:\n  " + "\n  ".join(hits)
    )


def test_the_guard_sees_a_real_lookup_and_ignores_prose_and_container_code(tmp_path):
    backend = tmp_path / "src" / "backend"
    backend.mkdir(parents=True)
    (backend / "caller.py").write_text(
        '"""Docs may say modal.Function.from_name(a, b) freely."""\n'
        "import modal\n"
        "# and so may comments: modal.Cls.from_name(a, b)\n"
        "def f():\n"
        "    return modal.Function.from_name('app', 'fn').remote()\n"
    )
    (backend / "modal_app.py").write_text(
        "import modal\n"
        "app = modal.App('x')\n"
        "@app.function()\n"
        "def body():\n"
        "    return modal.Function.from_name('other', 'fn').remote()\n"
    )
    assert _direct_lookups(tmp_path) == ["src/backend/caller.py:5 Function.from_name"]
