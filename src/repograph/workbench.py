"""Explicit local-browser transport; repository services remain transport independent."""

import hmac
import json
import secrets
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError

from repograph.canvas import CanvasRequest, CanvasService
from repograph.canvas_render import render_canvas
from repograph.config import Settings
from repograph.discovery import RepositoryError
from repograph.graph import GraphService
from repograph.readiness import ReadinessService
from repograph.testing import TestIntelligence
from repograph.verification import VerificationService


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PageInput(EmptyInput):
    offset: int = Field(default=0, ge=0, le=1_000_000)
    limit: int = Field(default=200, ge=1, le=200)


class PlanInput(EmptyInput):
    framework: Literal["pytest", "jest", "vitest", "node:test"]
    paths: list[str] | None = Field(default=None, max_length=50)
    scope: Literal["auto", "targeted", "suite"] = "auto"
    timeout_seconds: float | None = Field(default=None, ge=0.1, le=600)


class RunInput(EmptyInput):
    plan_id: str = Field(min_length=1, max_length=200)
    approved: StrictBool = False


class ResultInput(PageInput):
    plan_id: str = Field(min_length=1, max_length=200)


class BrowserCall(EmptyInput):
    name: Literal[
        "get_repository_readiness",
        "index_repository",
        "get_repository_canvas",
        "discover_tests",
        "prepare_verification",
        "verify_changes",
        "get_verification_result",
    ]
    arguments: dict = Field(default_factory=dict)


class StopCall(EmptyInput):
    name: Literal["stop_canvas"]
    arguments: EmptyInput = Field(default_factory=EmptyInput)


def browser_call(settings: Settings, payload: dict) -> dict:
    request = BrowserCall.model_validate(payload)
    arguments = request.arguments
    if request.name in {"get_repository_readiness", "index_repository"}:
        EmptyInput.model_validate(arguments)
        result = (
            ReadinessService(settings).get()
            if request.name == "get_repository_readiness"
            else GraphService(settings).index()
        )
    elif request.name == "get_repository_canvas":
        result = CanvasService(settings).get(**CanvasRequest.model_validate(arguments).model_dump())
    elif request.name == "discover_tests":
        result = TestIntelligence(settings).discover(
            **PageInput.model_validate(arguments).model_dump()
        )
    elif request.name == "prepare_verification":
        result = VerificationService(settings).prepare(
            **PlanInput.model_validate(arguments).model_dump()
        )
    elif request.name == "verify_changes":
        args = RunInput.model_validate(arguments)
        result = VerificationService(settings).verify(args.plan_id, approved=args.approved)
    else:
        args = ResultInput.model_validate(arguments)
        result = VerificationService(settings).result(args.plan_id, args.offset, args.limit)
    return result.model_dump(mode="json")


class WorkbenchServer(ThreadingHTTPServer):
    """IPv4 loopback only, bearer + same-origin protected, bounded concurrent requests."""

    daemon_threads = False
    block_on_close = True
    allow_reuse_address = False

    def __init__(self, settings: Settings, port: int = 0):
        if not 0 <= port <= 65535:
            raise ValueError("Port must be 0..65535")
        self.settings = settings
        self.token = secrets.token_urlsafe(32)
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(("127.0.0.1", port), WorkbenchHandler)
        self.origin = f"http://127.0.0.1:{self.server_port}"
        self.url = self.origin + "/#token=" + self.token
        self.html = render_canvas(None, local=True).encode("utf-8")

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class WorkbenchHandler(BaseHTTPRequestHandler):
    server: WorkbenchServer
    server_version = "RepoGraphCanvas"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *args):
        # Do not log URL fragments, request headers, repository text or test output.
        pass

    def respond(self, status: int, body: bytes, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass

    def error(self, status: int, code: str, message: str):
        self.respond(status, json.dumps({"error": {"code": code, "message": message}}).encode())

    def valid_host(self):
        return self.headers.get("Host") == self.server.origin.removeprefix("http://")

    def do_GET(self):
        if not self.valid_host():
            self.error(403, "invalid_host", "Use the exact loopback URL printed by RepoGraph")
        elif self.path == "/":
            self.respond(200, self.server.html, "text/html; charset=utf-8")
        else:
            self.error(404, "not_found", "Unknown canvas route")

    def do_POST(self):
        if not self.valid_host() or self.headers.get("Origin") != self.server.origin:
            self.error(403, "invalid_origin", "Canvas calls require the same loopback origin")
            return
        authorization = self.headers.get("Authorization", "")
        if not authorization.isascii() or not hmac.compare_digest(
            authorization, "Bearer " + self.server.token
        ):
            self.error(401, "unauthorized", "Open the original canvas launch link")
            return
        if self.path != "/api/call":
            self.error(404, "not_found", "Unknown canvas route")
            return
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            self.error(415, "invalid_content_type", "Canvas calls require application/json")
            return
        lengths = self.headers.get_all("Content-Length", [])
        if (
            len(lengths) != 1
            or len(lengths[0]) > 10
            or not lengths[0].isascii()
            or not lengths[0].isdecimal()
        ):
            self.error(400, "invalid_body", "Provide one bounded Content-Length")
            return
        size = int(lengths[0])
        if size > 8_000_000 or self.headers.get("Transfer-Encoding"):
            self.error(413, "request_limit", "Canvas request exceeds the allowed body limit")
            return
        try:
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise ValueError("Incomplete body")
            payload = json.loads(raw)
            if isinstance(payload, dict) and payload.get("name") == "stop_canvas":
                StopCall.model_validate(payload)
                self.respond(200, b'{"stopped":true}')
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            result = browser_call(self.server.settings, payload)
            body = json.dumps(result, ensure_ascii=True).encode("utf-8")
            if len(body) > 8_000_000:
                self.error(413, "canvas_output_limit", "Narrow the canvas scope or page size")
                return
            self.respond(200, body)
        except RepositoryError as error:
            self.error(400, error.code, str(error))
        except (ValidationError, ValueError, TypeError, RecursionError):
            self.error(400, "invalid_request", "Invalid canvas tool arguments")
        except (TimeoutError, OSError, sqlite3.Error):
            self.error(500, "storage_error", "Repository storage or connection is unavailable")
