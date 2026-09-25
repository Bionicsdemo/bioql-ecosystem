"""Modal <-> Brev switching (modal_compute_layer + brev_client).

What must hold:
  * the policy picks the backend by health, and says why;
  * an infrastructure failure moves the job to the other backend in the same call;
  * the function's own exception is raised as is, never re-run elsewhere;
  * a job Brev may still be running is never started a second time;
  * the bearer token never shows up in an error or a routing record.

A fake `modal` module and an in-process fake Brev job server stand in for both
backends: nothing here reaches Modal, Brev or a GPU.
"""

import json
import sys
import time
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src" / "backend"))
sys.path.insert(0, str(HERE))

from fake_brev_server import TOKEN, FakeBrevServer  # noqa: E402

APP = "bioql-test-app"


def make_fake_modal(registry):
    """registry: {"app::fn" or "app::Cls.method": callable or exception instance}."""
    calls = []
    exc = types.ModuleType("modal.exception")

    class Error(Exception):
        pass

    exc.Error = Error
    for name in (
        "NotFoundError",
        "ResourceExhaustedError",
        "AuthError",
        "InvalidError",
        "SerializationError",
        "DeserializationError",
        "RequestSizeError",
        "ServiceError",
        "InternalError",
        "ConflictError",
    ):
        setattr(exc, name, type(name, (Error,), {}))
    exc.TimeoutError = type("TimeoutError", (Error,), {})
    exc.FunctionTimeoutError = type("FunctionTimeoutError", (exc.TimeoutError,), {})

    class FakeCall:
        object_id = "fc-test"

        def __init__(self, fn, args, kwargs):
            self.fn, self.args, self.kwargs = fn, args, kwargs

        def get(self, timeout=None):
            return self.fn._run(self.args, self.kwargs)

    class FakeFunction:
        def __init__(self, key):
            self.key = key

        def hydrate(self):
            if self.key not in registry:
                raise exc.NotFoundError(f"{self.key} not found")
            return self

        def _run(self, args, kwargs):
            calls.append((self.key, args, kwargs))
            target = registry[self.key]
            if isinstance(target, BaseException):
                raise target
            return target(*args, **kwargs)

        def remote(self, *args, **kwargs):
            return self._run(args, kwargs)

        def spawn(self, *args, **kwargs):
            return FakeCall(self, args, kwargs)

        def map(self, *its, kwargs=None, order_outputs=True, return_exceptions=False):
            for a in zip(*its):
                yield self._run(a, kwargs or {})

    class FakeCls:
        def __init__(self, app, name):
            self.app, self.name = app, name

        def hydrate(self):
            if not any(k.startswith(f"{self.app}::{self.name}.") for k in registry):
                raise exc.NotFoundError(f"{self.app}::{self.name} not found")
            return self

        def __call__(self, *a, **k):
            outer = self

            class Instance:
                def __getattr__(self, m):
                    return FakeFunction(f"{outer.app}::{outer.name}.{m}")

            return Instance()

    mod = types.ModuleType("modal")
    mod.__path__ = []  # a package, so `import modal.exception` resolves
    mod.exception = exc
    mod.Function = types.SimpleNamespace(from_name=lambda app, name: FakeFunction(f"{app}::{name}"))
    mod.Cls = types.SimpleNamespace(from_name=lambda app, name: FakeCls(app, name))
    return mod, exc, calls


@pytest.fixture
def world(monkeypatch):
    import brev_client
    import modal_compute_layer as M

    servers = []

    def build(modal=None, brev=None, classes=None, prefer="auto", brev_on=True):
        fake, exc, calls = make_fake_modal(modal or {})
        monkeypatch.setitem(sys.modules, "modal", fake)
        monkeypatch.setitem(sys.modules, "modal.exception", exc)
        monkeypatch.setenv("BIOQL_MODAL_ENABLED", "1")
        monkeypatch.setenv("BIOQL_COMPUTE_PREFER", prefer)
        monkeypatch.setenv("BIOQL_BREV_HEALTH_TTL_S", "0")
        monkeypatch.setenv("BIOQL_BREV_POLL_S", "0.01")
        monkeypatch.setenv("BIOQL_BREV_TOKEN", TOKEN)
        srv = None
        if brev_on:
            srv = FakeBrevServer(functions=brev or {}, classes=classes or {}).start()
            servers.append(srv)
            monkeypatch.setenv("BIOQL_BREV_URL", srv.url)
        else:
            monkeypatch.delenv("BIOQL_BREV_URL", raising=False)
        brev_client.forget_health()
        M.reset_memory()
        return types.SimpleNamespace(M=M, srv=srv, calls=calls, exc=exc)

    yield build
    for s in servers:
        s.stop()
    brev_client.forget_health()
    M.reset_memory()


def spawned(srv):
    return [p for m, p in srv.requests if p == "/v1/spawn"]


# -- choosing ------------------------------------------------------------------
def test_auto_sends_the_job_to_a_free_brev_instance(world):
    w = world(
        modal={f"{APP}::f": lambda x: {"on": "modal"}},
        brev={f"{APP}::f": lambda x: {"on": "brev", "x": x}},
    )
    res, info = w.M.dispatch(APP, "f", (3,))
    assert info["backend"] == "brev" and res["on"] == "brev" and res["x"] == 3
    assert "free GPU slot" in info["routing"]["why"]
    assert res["compute_provenance"]["instance"] == "fake-instance"
    assert res["compute_provenance"]["job_id"] == info["provenance"]["job_id"]
    assert w.calls == [], "Modal must not be called when Brev took the job"


def test_auto_goes_to_modal_when_brev_has_no_free_slot(world):
    w = world(
        modal={f"{APP}::f": lambda: {"on": "modal"}}, brev={f"{APP}::f": lambda: {"on": "brev"}}
    )
    w.srv.busy = 1
    res, info = w.M.dispatch(APP, "f")
    assert info["backend"] == "modal" and res == {
        "on": "modal"
    }, "a Modal result is returned untouched"
    assert "busy" in info["routing"]["why"]
    assert info["routing"]["order"] == ["modal", "brev"]


def test_a_function_brev_has_not_loaded_goes_to_modal_and_demotes_nothing_else(world):
    w = world(
        modal={f"{APP}::f": lambda: "modal-f", f"{APP}::g": lambda: "modal-g"},
        brev={f"{APP}::g": lambda: "brev-g"},
    )
    assert w.M.dispatch(APP, "f")[0] == "modal-f"
    assert w.M.dispatch(APP, "g")[0] == "brev-g"
    assert "not loaded" in w.M.plan(APP, "f")[1]["skipped"]["brev"]


def test_modal_is_skipped_when_disabled_and_brev_is_skipped_when_off(world, monkeypatch):
    w = world(modal={f"{APP}::f": lambda: 1}, brev_on=False)
    monkeypatch.setenv("BIOQL_MODAL_ENABLED", "0")
    order, routing = w.M.plan(APP, "f")
    assert order == []
    assert "BIOQL_MODAL_ENABLED=0" in routing["skipped"]["modal"]
    assert "BIOQL_BREV_URL" in routing["skipped"]["brev"]
    with pytest.raises(w.M.ComputeUnavailable, match="no compute backend available"):
        w.M.dispatch(APP, "f")


# -- failing over --------------------------------------------------------------
def test_modal_out_of_budget_moves_the_job_to_brev_in_the_same_call(world):
    w = world(prefer="modal", brev={f"{APP}::f": lambda: {"on": "brev"}})
    w_exc = w.exc.ResourceExhaustedError("workspace spend limit reached")
    sys.modules["modal"].Function = types.SimpleNamespace(
        from_name=lambda app, name: types.SimpleNamespace(
            hydrate=lambda: None, remote=lambda *a, **k: (_ for _ in ()).throw(w_exc)
        )
    )
    res, info = w.M.dispatch(APP, "f")
    assert info["backend"] == "brev" and res["on"] == "brev"
    first = info["routing"]["tried"][0]
    assert first["backend"] == "modal" and first["ok"] is False and first["failure"] == "backend"
    assert "spend limit" in first["why"]
    # remembered: in auto mode Modal now goes last even though Brev is busy
    w.srv.busy = 1
    order, routing = w.M.plan(APP, "f", prefer="auto")
    assert order == ["brev", "modal"] and "modal" in routing["cooling"]


def test_brev_down_means_modal(world):
    w = world(modal={f"{APP}::f": lambda: "from-modal"}, brev={f"{APP}::f": lambda: "from-brev"})
    w.srv.stop()
    res, info = w.M.dispatch(APP, "f")
    assert info["backend"] == "modal" and res == "from-modal"
    assert info["routing"]["skipped"]["brev"]


def test_pinned_brev_that_is_unreachable_fails_over_and_cools_down(world):
    w = world(
        prefer="brev", modal={f"{APP}::f": lambda: "from-modal"}, brev={f"{APP}::f": lambda: "x"}
    )
    w.srv.stop()
    res, info = w.M.dispatch(APP, "f")
    assert res == "from-modal"
    brev_try = info["routing"]["tried"][0]
    assert (
        brev_try["backend"] == "brev"
        and brev_try["transient"] is True
        and brev_try["failure"] == "backend"
    )
    assert w.M._cooling("brev", APP, "f")


def test_a_dead_brev_worker_is_rerun_on_modal(world):
    w = world(modal={f"{APP}::f": lambda: "from-modal"}, brev={f"{APP}::f": lambda: "never"})
    w.srv.infra_fail.add(f"{APP}::f")
    res, info = w.M.dispatch(APP, "f")
    assert res == "from-modal" and info["routing"]["tried"][0]["failure"] == "call"
    assert not w.M._cooling("brev", APP, "f"), "one dead job says nothing lasting about Brev"


def test_a_job_brev_may_still_be_running_is_not_started_again(world, monkeypatch):
    import brev_client

    w = world(modal={f"{APP}::f": lambda: "from-modal"}, brev={f"{APP}::f": lambda: "x"})

    def lost(job_id, timeout_s=None, poll_s=None):
        raise brev_client.BrevUnavailable(
            "no contact for 900 s", transient=True, job_id=job_id, in_flight=True
        )

    monkeypatch.setattr(brev_client, "wait", lost)
    with pytest.raises(brev_client.BrevUnavailable) as ei:
        w.M.dispatch(APP, "f")
    assert ei.value.in_flight and w.calls == []


# -- the function's own errors ---------------------------------------------------
def test_an_error_raised_by_the_function_on_brev_is_not_retried_on_modal(world):
    def bad(smiles):
        raise ValueError(f"unparseable SMILES {smiles!r}")

    w = world(modal={f"{APP}::f": lambda s: "never"}, brev={f"{APP}::f": bad})
    with pytest.raises(ValueError, match="unparseable SMILES") as ei:
        w.M.dispatch(APP, "f", ("C1CC",))
    assert ei.value.bioql_origin == "function" and ei.value.bioql_backend == "brev"
    assert ei.value.bioql_routing["chosen"] == "brev"
    assert "Traceback" in ei.value.bioql_remote_traceback
    assert w.calls == []


def test_an_error_raised_by_the_function_on_modal_is_not_retried_on_brev(world):
    w = world(
        prefer="modal",
        modal={f"{APP}::f": KeyError("chain B")},
        brev={f"{APP}::f": lambda: "never"},
    )
    with pytest.raises(KeyError):
        w.M.dispatch(APP, "f")
    assert spawned(w.srv) == []


def test_a_non_builtin_remote_error_keeps_its_name(world):
    class PocketError(Exception):
        pass

    def bad():
        raise PocketError("no pocket within 8 A")

    w = world(brev={f"{APP}::f": bad}, prefer="brev-only")
    import brev_client

    with pytest.raises(brev_client.BrevFunctionError, match="PocketError: no pocket") as ei:
        w.M.dispatch(APP, "f")
    assert ei.value.remote_type == "PocketError"


# -- secrets -------------------------------------------------------------------
def test_the_token_never_reaches_an_error_or_a_routing_record(world):
    w = world(prefer="brev-only", brev={f"{APP}::f": lambda: 1})
    w.srv.echo_auth_on_500 = True
    w.srv.fail_next_spawn_with = 500
    with pytest.raises(w.M.ComputeUnavailable) as ei:
        w.M.dispatch(APP, "f")
    assert "***" in str(ei.value), "the server did echo the header; it must arrive redacted"
    assert TOKEN not in str(ei.value)
    assert TOKEN not in json.dumps(ei.value.routing)


def test_a_wrong_token_is_an_infrastructure_failure(world, monkeypatch):
    w = world(
        prefer="brev", modal={f"{APP}::f": lambda: "from-modal"}, brev={f"{APP}::f": lambda: 1}
    )
    monkeypatch.setenv("BIOQL_BREV_TOKEN", "wrong")
    res, info = w.M.dispatch(APP, "f")
    assert res == "from-modal" and "401" in info["routing"]["tried"][0]["why"]


# -- drop-in handles -------------------------------------------------------------
def test_spawn_and_get_on_brev(world):
    def slow(x):
        time.sleep(0.3)
        return {"x": x}

    w = world(brev={f"{APP}::f": slow, f"{APP}::g": lambda x: {"x": x}}, prefer="brev-only")
    call = w.M.function(APP, "g").spawn(7)
    assert call.backend == "brev" and call.object_id.startswith("brev-")
    assert call.get()["x"] == 7
    with pytest.raises(TimeoutError):
        w.M.function(APP, "f").spawn(1).get(timeout=0.05)


def test_map_on_brev_keeps_input_order_and_can_return_exceptions(world):
    def sq(x):
        time.sleep(0.05 * (3 - x))
        if x == 0:
            raise ValueError("zero")
        return x * x

    w = world(brev={f"{APP}::sq": sq}, prefer="brev-only")
    fn = w.M.function(APP, "sq")
    assert list(fn.map([3, 1, 2])) == [9, 1, 4]
    out = list(fn.map([2, 0], return_exceptions=True))
    assert out[0] == 4 and isinstance(out[1], ValueError)


def test_map_on_modal_is_modals_own_map(world):
    w = world(modal={f"{APP}::sq": lambda x: x * x}, brev_on=False)
    assert list(w.M.function(APP, "sq").map([1, 2, 3])) == [1, 4, 9]


def test_a_class_runs_on_brev_with_its_init_arguments(world):
    class Model:
        def __init__(self, scale=1):
            self.scale = scale

        def predict(self, x):
            return {"y": x * self.scale}

    w = world(classes={f"{APP}::Model": Model}, prefer="brev-only")
    out = w.M.cls(APP, "Model")(scale=3).predict.remote(2)
    assert out["y"] == 6 and out["compute_provenance"]["backend"] == "brev"


def test_hydrate_says_why_nothing_resolves(world):
    w = world(brev={}, modal={})
    with pytest.raises(w.M.ComputeUnavailable, match="not resolvable on any backend"):
        w.M.function(APP, "missing").hydrate()
    w2 = world(brev={f"{APP}::f": lambda: 1})
    assert w2.M.function(APP, "f").hydrate() is not None


# -- the existing contracts ----------------------------------------------------------
def test_run_keeps_its_contract_when_brev_runs_the_job(world):
    w = world(
        brev={"bioql-quantum-gpu::cudaq_statevector": lambda spec, shots: {"counts": {"00": shots}}}
    )
    r = w.M.run("quantum_gpu", {"n_qubits": 2}, 10)
    assert r["available"] and r["where_it_ran"] == "brev" and r["is_degraded"] is False
    assert w.M.ran_remotely(r) and r["provenance"]["backend"] == "brev"
    assert r["result"]["counts"] == {"00": 10}


def test_run_falls_back_locally_and_says_why(world, monkeypatch):
    w = world(brev_on=False)
    monkeypatch.setenv("BIOQL_MODAL_ENABLED", "0")
    r = w.M.run("quantum_gpu", {}, 1, local_fn=lambda spec, shots: "cpu")
    assert r["where_it_ran"] == "local" and r["is_degraded"] is True and r["result"] == "cpu"
    assert "BIOQL_MODAL_ENABLED=0" in r["why"] and "BIOQL_BREV_URL" in r["why"]
    assert not w.M.ran_remotely(r)


def test_the_retry_helper_routes_and_reports(world, monkeypatch):
    import modal_retry

    world(brev={f"{APP}::f": lambda x: {"x": x}})
    r = modal_retry.call_modal_with_retry(APP, "f", 5)
    assert r["success"] and r["backend"] == "brev" and r["result"]["x"] == 5
    assert r["call_ref"] and r["routing"]["chosen"] == "brev"

    world(brev_on=False)
    monkeypatch.setenv("BIOQL_MODAL_ENABLED", "0")
    r = modal_retry.call_modal_with_retry(APP, "f", 5, base_delay_s=0)
    assert r["success"] is False and r["attempts"] == 0 and "no compute backend" in r["error"]


def test_the_retry_helper_does_not_retry_the_functions_own_error(world):
    import modal_retry

    def bad():
        raise ValueError("bad input")

    w = world(brev={f"{APP}::f": bad}, prefer="brev-only")
    r = modal_retry.call_modal_with_retry(APP, "f", base_delay_s=0)
    assert r["success"] is False and r["attempts"] == 1 and r["transient"] is False
    assert len(spawned(w.srv)) == 1


def test_health_is_asked_once_per_ttl(world, monkeypatch):
    w = world(brev={f"{APP}::f": lambda: 1})
    monkeypatch.setenv("BIOQL_BREV_HEALTH_TTL_S", "60")
    for _ in range(3):
        w.M.plan(APP, "f")
    assert sum(1 for _, p in w.srv.requests if p == "/health") == 1


def test_modal_only_never_touches_brev(world):
    w = world(
        prefer="modal-only", modal={f"{APP}::f": lambda: "m"}, brev={f"{APP}::f": lambda: "b"}
    )
    assert w.M.dispatch(APP, "f")[0] == "m"
    assert w.srv.requests == []


def test_a_label_that_names_modal_is_corrected_when_brev_ran_it(world):
    w = world(
        brev={
            f"{APP}::f": lambda: {
                "backend": "CUDA-Q cuStateVec (Modal A100)",
                "note": "deploy on Modal first",
            }
        }
    )
    res, info = w.M.dispatch(APP, "f")
    assert res["backend"] == "CUDA-Q cuStateVec (Brev FAKE-GPU)"
    assert res["compute_provenance"]["relabeled_from"] == {
        "backend": "CUDA-Q cuStateVec (Modal A100)"
    }
    assert res["note"] == "deploy on Modal first", "only label fields are touched, never prose"


def test_a_modal_result_is_never_relabeled(world):
    w = world(
        modal={f"{APP}::f": lambda: {"backend": "CUDA-Q cuStateVec (Modal A100)"}}, brev_on=False
    )
    res, _ = w.M.dispatch(APP, "f")
    assert res == {"backend": "CUDA-Q cuStateVec (Modal A100)"}


def test_a_spawned_brev_job_can_be_collected_later_by_its_id(world):
    w = world(brev={f"{APP}::f": lambda x: {"x": x}}, prefer="brev-only")
    ident = w.M.function(APP, "f").spawn(4).object_id
    assert ident.startswith("brev-")
    assert w.M.call_from_id(ident).get(timeout=5)["x"] == 4


def test_a_modal_call_id_is_collected_from_modal(world):
    w = world(brev_on=False)
    got = {}

    class FC:
        object_id = "fc-abc"

        def get(self, timeout=None):
            return "from-modal"

    sys.modules["modal"].FunctionCall = types.SimpleNamespace(
        from_id=lambda i: got.setdefault("id", i) and FC()
    )
    assert w.M.call_from_id("fc-abc").get() == "from-modal" and got["id"] == "fc-abc"
