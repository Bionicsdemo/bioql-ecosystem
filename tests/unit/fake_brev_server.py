"""In-process stand-in for the BioQL Brev job server, for tests.

It implements the wire contract the real server (bioql-brev/server/worker.py) was
asked to match -- /livez, /health, /v1/spawn, /v1/jobs/{id}, /v1/jobs/{id}/cancel,
/v1/call, bearer auth, brev_wire payloads -- with plain Python callables standing in
for the Modal app bodies. Nothing here touches Brev, Modal or a GPU.
"""

import hmac
import json
import sys
import threading
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "backend"))
import brev_wire  # noqa: E402

TOKEN = "test-token-7f3a9c"  # nosec B105 -- fake credential for the fake server


class FakeBrevServer:
    def __init__(self, functions=None, classes=None, token=TOKEN, slots=1, gpu=None):
        # functions: {"app::fn": callable}; classes: {"app::Cls": class}
        self.functions = dict(functions or {})
        self.classes = dict(classes or {})
        self.token = token
        self.slots = slots
        self.busy = 0
        self.queue = 0
        self.gpu = gpu if gpu is not None else {"name": "FAKE-GPU", "count": 1, "memory_gb": 80}
        self.jobs = {}
        self.requests = []  # (method, path) for assertions
        self.health_ok = True
        self.fail_next_spawn_with = None  # an HTTP status to answer the next spawn with
        self.echo_auth_on_500 = False
        self.infra_fail = set()  # "app::fn" whose jobs die as infrastructure failures
        self.lock = threading.Lock()
        self._httpd = None
        self._thread = None

    # -- lifecycle ---------------------------------------------------------
    def start(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, status, body):
                raw = json.dumps(body, allow_nan=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _authorized(self):
                got = self.headers.get("Authorization", "")
                return hmac.compare_digest(got, f"Bearer {server.token}")

            def _body(self):
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n) or b"{}")

            def do_GET(self):
                server.requests.append(("GET", self.path))
                if self.path == "/livez":
                    return self._send(200, {"ok": True})
                if not self._authorized():
                    return self._send(
                        401, {"error": {"type": "Unauthorized", "message": "bad token"}}
                    )
                if self.path == "/health":
                    return self._send(200, server.health_body())
                if self.path.startswith("/v1/jobs/"):
                    job = server.jobs.get(self.path.rsplit("/", 1)[-1])
                    if job is None:
                        return self._send(
                            404, {"error": {"type": "NotFound", "message": "no such job"}}
                        )
                    return self._send(200, job)
                return self._send(404, {"error": {"type": "NotFound", "message": self.path}})

            def do_POST(self):
                server.requests.append(("POST", self.path))
                if not self._authorized():
                    return self._send(
                        401, {"error": {"type": "Unauthorized", "message": "bad token"}}
                    )
                if self.path in ("/v1/spawn", "/v1/call"):
                    if server.fail_next_spawn_with:
                        status, server.fail_next_spawn_with = server.fail_next_spawn_with, None
                        msg = "upstream exploded"
                        if server.echo_auth_on_500:
                            msg += f" (request had {self.headers.get('Authorization')})"
                        return self._send(
                            status, {"error": {"type": "ServerError", "message": msg}}
                        )
                    body = self._body()
                    ref = server.ref_of(body)
                    if ref is None:
                        return self._send(
                            404,
                            {
                                "error": {
                                    "type": "NotFound",
                                    "message": f"{body.get('app')}::{body.get('cls') or body.get('function')} not loaded",
                                    "origin": "infrastructure",
                                    "transient": False,
                                }
                            },
                        )
                    job_id = server.submit(body)
                    if self.path == "/v1/call":
                        while server.jobs[job_id]["status"] in ("queued", "running"):
                            time.sleep(0.01)
                        return self._send(200, server.jobs[job_id])
                    return self._send(202, {"job_id": job_id, "status": "queued"})
                if self.path.startswith("/v1/jobs/") and self.path.endswith("/cancel"):
                    job = server.jobs.get(self.path.split("/")[3])
                    if job is None:
                        return self._send(
                            404, {"error": {"type": "NotFound", "message": "no such job"}}
                        )
                    if job["status"] in ("queued", "running"):
                        job["status"] = "cancelled"
                    return self._send(200, {"job_id": job["job_id"], "status": job["status"]})
                return self._send(404, {"error": {"type": "NotFound", "message": self.path}})

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        )
        self._thread.start()
        return self

    def stop(self):
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    @property
    def url(self):
        host, port = self._httpd.server_address[:2]
        return f"http://{host}:{port}"

    # -- behaviour ---------------------------------------------------------
    def health_body(self):
        return {
            "ok": self.health_ok,
            "server": "bioql-brev-jobs",
            "api": brev_wire.API_VERSION,
            "instance": "fake-instance",
            "gpu": self.gpu,
            "worker_image": "fake-image:1",
            "git_sha": "0000000",
            "functions": sorted(self.functions),
            "classes": sorted(self.classes),
            "web": [],
            "slots": {"total": self.slots, "busy": self.busy},
            "queue": self.queue,
            "uptime_s": 1.0,
            "mode": "local",
        }

    def ref_of(self, body):
        if body.get("cls"):
            key = f"{body.get('app')}::{body['cls']}"
            return key if key in self.classes else None
        key = f"{body.get('app')}::{body.get('function')}"
        return key if key in self.functions else None

    def submit(self, body):
        job_id = uuid.uuid4().hex[:12]
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        job = {
            "job_id": job_id,
            "status": "queued",
            "app": body.get("app"),
            "function": body.get("method") if body.get("cls") else body.get("function"),
            "cls": body.get("cls"),
            "submitted_at": now,
            "started_at": None,
            "finished_at": None,
            "elapsed_s": None,
            "instance": "fake-instance",
            "gpu": self.gpu,
            "worker_image": "fake-image:1",
            "git_sha": "0000000",
        }
        self.jobs[job_id] = job
        threading.Thread(target=self._run, args=(job, body), daemon=True).start()
        return job_id

    def _run(self, job, body):
        t0 = time.time()
        job["status"] = "running"
        job["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        ref = self.ref_of(body)
        try:
            args = brev_wire.decode(body.get("args") or [], allow_pickle=True)
            kwargs = brev_wire.decode(body.get("kwargs") or {}, allow_pickle=True)
            if ref in self.infra_fail:
                raise MemoryError("worker process was OOM-killed")
            if body.get("cls"):
                init = body.get("init") or {}
                obj = self.classes[ref](
                    *brev_wire.decode(init.get("args") or [], allow_pickle=True),
                    **brev_wire.decode(init.get("kwargs") or {}, allow_pickle=True),
                )
                res = getattr(obj, body["method"])(*args, **kwargs)
            else:
                res = self.functions[ref](*args, **kwargs)
            if job["status"] == "cancelled":
                return
            job["result"] = brev_wire.encode(res, allow_pickle=True)
            job["status"] = "succeeded"
        except Exception as e:
            infra = ref in self.infra_fail
            job["error"] = {
                "type": type(e).__name__,
                "module": type(e).__module__,
                "message": str(e),
                "traceback": traceback.format_exc(),
                "origin": "infrastructure" if infra else "function",
                "transient": infra,
            }
            job["status"] = "failed"
        finally:
            job["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            job["elapsed_s"] = round(time.time() - t0, 3)
