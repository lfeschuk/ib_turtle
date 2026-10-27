"""HTTP server for the phone app: a small JSON API plus the installable web app (PWA) files.

It listens on localhost only. `tailscale serve` publishes it with HTTPS to devices on your own tailnet.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

from typing import TYPE_CHECKING

from .auth import (CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE, SESSION_LIFETIME_S, AuthStore, LoginLimiter, TokenBucket,
                   csrf_ok, new_csrf_token)
from .config import LiveConfig
from .service import BotService

if TYPE_CHECKING:
    from .bwb_service import BwbBotService

log = logging.getLogger(__name__)

WEB_DIR = Path(__file__).with_name("web")
_STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/sw.js": ("sw.js", "text/javascript; charset=utf-8"),
    "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
    "/icon.svg": ("icon.svg", "image/svg+xml"),
    "/icon-192.png": ("icon-192.png", "image/png"),
    "/icon-512.png": ("icon-512.png", "image/png"),
}
_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
        "manifest-src 'self'; worker-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
        "form-action 'self'")
_SECURITY_HEADERS = {
    "Content-Security-Policy": _CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000",
}
_MAX_BODY = 4096
_SYMBOL = re.compile(r"^([A-Z][A-Z0-9.]{0,9}|(SPXW|XSP)( \d+/\d+/\d+P)?)$")


class PasswordBody(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class CloseBody(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=256)


def _set_cookie(resp: Response, key: str, value: str, httponly: bool, max_age: int | None = None) -> None:
    resp.set_cookie(key, value, max_age=max_age, path="/", secure=True, httponly=httponly, samesite="strict")


def create_app(service: BotService, cfg: LiveConfig, auth: AuthStore, web_dir: Path = WEB_DIR,
               bwb_service: BwbBotService | None = None) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    files = {route: ((web_dir / name).read_bytes(), media) for route, (name, media) in _STATIC.items()}
    bucket = TokenBucket()
    login_limiter = LoginLimiter()

    def _svc(request: Request):
        strat = (request.query_params.get("strategy") or "gapshort").lower()
        if strat == "gapshort":
            return service
        if strat == "bwb":
            if bwb_service is None:
                raise HTTPException(status_code=404, detail="0DTE BWB strategy not enabled")
            return bwb_service
        raise HTTPException(status_code=422, detail="bad strategy")

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "POST"):
            resp = PlainTextResponse("Method not allowed", status_code=405)
        elif request.url.path.startswith("/api/") and not bucket.allow():
            resp = JSONResponse({"error": "too many requests"}, status_code=429)
        elif request.method == "POST" and int(request.headers.get("content-length") or 0) > _MAX_BODY:
            resp = JSONResponse({"error": "request too large"}, status_code=413)
        else:
            resp = await call_next(request)
        for k, v in _SECURITY_HEADERS.items():
            resp.headers[k] = v
        resp.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
        return resp

    @app.exception_handler(Exception)
    async def on_error(request: Request, exc: Exception):
        log.exception("request failed: %s", request.url.path)
        return JSONResponse({"error": "internal error"}, status_code=500)

    def require_session(request: Request) -> None:
        if not auth.valid_session(request.cookies.get(SESSION_COOKIE)):
            raise HTTPException(status_code=401, detail="login required")

    def require_csrf(request: Request) -> None:
        if not csrf_ok(request.cookies.get(CSRF_COOKIE), request.headers.get(CSRF_HEADER)):
            raise HTTPException(status_code=403, detail="bad or missing CSRF token")

    def require_password(password: str) -> None:
        if login_limiter.blocked():
            raise HTTPException(status_code=429, detail="too many wrong passwords, try later",
                                headers={"Retry-After": str(login_limiter.retry_after_s())})
        if not auth.check_password(password):
            login_limiter.failure()
            raise HTTPException(status_code=401, detail="wrong password")
        login_limiter.success()

    def static(route: str):
        async def handler(request: Request) -> Response:
            body, media = files[route]
            resp = Response(content=body, media_type=media)
            if route == "/" and not request.cookies.get(CSRF_COOKIE):
                _set_cookie(resp, CSRF_COOKIE, new_csrf_token(), httponly=False)
            return resp
        return handler

    for route in _STATIC:
        app.add_api_route(route, static(route), methods=["GET"], include_in_schema=False)

    # ------------------------------------------------------------------ session
    @app.get("/api/session")
    async def session(request: Request):
        resp = JSONResponse({"authenticated": auth.valid_session(request.cookies.get(SESSION_COOKIE)),
                             "mode": cfg.mode,
                             "bwb_enabled": bwb_service is not None})
        if not request.cookies.get(CSRF_COOKIE):
            _set_cookie(resp, CSRF_COOKIE, new_csrf_token(), httponly=False)
        return resp

    @app.post("/api/login")
    async def login(request: Request, body: PasswordBody):
        require_csrf(request)
        require_password(body.password)
        resp = JSONResponse({"ok": True})
        auth.end_session(request.cookies.get(SESSION_COOKIE))
        _set_cookie(resp, SESSION_COOKIE, auth.create_session(), httponly=True, max_age=SESSION_LIFETIME_S)
        _set_cookie(resp, CSRF_COOKIE, new_csrf_token(), httponly=False)
        service.journal.event("info", "login", "App login")
        return resp

    @app.post("/api/logout")
    async def logout(request: Request):
        require_csrf(request)
        auth.end_session(request.cookies.get(SESSION_COOKIE))
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="strict")
        return resp

    # ------------------------------------------------------------------ read
    @app.get("/api/overview")
    async def overview(request: Request):
        require_session(request)
        gs_status = await service.status()
        gs_eq = service.journal.equity(400)
        strats: dict = {"gapshort": {"status": gs_status, "equity": gs_eq}}
        gs_init = float(gs_status.get("initial_capital") or cfg.initial_capital)
        gs_nlv = float(gs_status.get("net_liquidation") or gs_init)
        comb_init = gs_init
        comb_nlv = gs_nlv
        comb_day = float(gs_status.get("day_pnl") or 0.0)
        comb_pos = int(gs_status.get("positions") or 0)
        shared_cap = False

        if bwb_service is not None:
            bwb_status = await bwb_service.status()
            bwb_eq = bwb_service.journal.equity(400)
            strats["bwb"] = {"status": bwb_status, "equity": bwb_eq}
            b_init = float(bwb_status.get("initial_capital") or cfg.bwb.initial_capital)
            b_nlv = float(bwb_status.get("net_liquidation") or b_init)
            shared_cap = (not cfg.isolated_capital) and (not cfg.bwb.isolated_capital)
            if shared_cap:
                # Single shared $100k pool: bwb_status.net_liquidation already incorporates shared equity
                comb_init = gs_init
                comb_nlv = b_nlv
            else:
                comb_init += b_init
                comb_nlv += b_nlv
            comb_day += float(bwb_status.get("day_pnl") or 0.0)
            comb_pos += int(bwb_status.get("positions") or 0)

        return {
            "combined": {
                "initial_capital": comb_init,
                "net_liquidation": comb_nlv,
                "total_return_pct": (comb_nlv / comb_init - 1.0) * 100.0 if comb_init > 0 else 0.0,
                "day_pnl": comb_day,
                "positions": comb_pos,
                "shared_capital": shared_cap,
            },
            "strategies": strats,
        }

    @app.get("/api/status")
    async def status(request: Request):
        require_session(request)
        return await _svc(request).status()

    @app.get("/api/positions")
    async def positions(request: Request):
        require_session(request)
        return {"positions": await _svc(request).positions_view()}

    @app.get("/api/orders")
    async def orders(request: Request):
        require_session(request)
        return {"orders": await _svc(request).orders_view()}

    @app.get("/api/signals")
    async def signals(request: Request):
        require_session(request)
        return _svc(request).signals_view()

    @app.get("/api/trades")
    async def trades(request: Request):
        require_session(request)
        return {"trades": _svc(request).journal.recent_trades(50)}

    @app.get("/api/equity")
    async def equity(request: Request):
        require_session(request)
        return {"equity": _svc(request).journal.equity(400)}

    @app.get("/api/events")
    async def events(request: Request):
        require_session(request)
        return {"events": _svc(request).journal.events(60)}

    @app.get("/api/report")
    async def report(request: Request):
        require_session(request)
        return _svc(request).report_view()

    # ------------------------------------------------------------------ actions
    @app.post("/api/pause")
    async def pause(request: Request):
        require_session(request)
        require_csrf(request)
        await _svc(request).pause()
        return {"ok": True}

    @app.post("/api/resume")
    async def resume(request: Request):
        require_session(request)
        require_csrf(request)
        await _svc(request).resume()
        return {"ok": True}

    @app.post("/api/close")
    async def close(request: Request, body: CloseBody):
        require_session(request)
        require_csrf(request)
        require_password(body.password)
        symbol = body.symbol.upper()
        if not _SYMBOL.match(symbol):
            raise HTTPException(status_code=422, detail="bad symbol")
        try:
            how = await _svc(request).close_position(symbol)
        except LookupError:
            raise HTTPException(status_code=404, detail="no open position in that symbol")
        return {"ok": True, "order_type": how}

    @app.post("/api/flatten")
    async def flatten(request: Request, body: PasswordBody):
        require_session(request)
        require_csrf(request)
        require_password(body.password)
        n = await _svc(request).flatten()
        return {"ok": True, "covered": n}

    return app
