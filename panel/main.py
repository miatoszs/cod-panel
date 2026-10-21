"""FastAPI application: REST API + live console websocket + static web UI."""
from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, auth, config, db, games, installer, instances, maps, rcon, runner

app = FastAPI(title="COD Panel", version=__version__, docs_url="/api/docs")

OPEN_PATHS = {"/api/me", "/api/login", "/api/setup", "/api/version"}


@app.on_event("startup")
async def _startup() -> None:
    config.ensure_dirs()
    db.init()
    if os.environ.get("CODPANEL_ADMIN_PASSWORD") and not auth.has_user():
        auth.create_user(os.environ.get("CODPANEL_ADMIN_USER", "admin"),
                         os.environ["CODPANEL_ADMIN_PASSWORD"])
    runner.autostart_all()


@app.on_event("shutdown")
async def _shutdown() -> None:
    runner.manager.stop_all()


@app.middleware("http")
async def require_login(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and path not in OPEN_PATHS:
        user = auth.read_token(request.cookies.get(config.SESSION_COOKIE))
        if not user:
            return JSONResponse({"detail": "Bejelentkezés szükséges."}, status_code=401)
        request.state.user = user
    return await call_next(request)


# --- helpers -------------------------------------------------------------------

def _inst(iid: str) -> dict[str, Any]:
    inst = db.get_instance(iid)
    if not inst:
        raise HTTPException(404, "Nincs ilyen szerver.")
    return inst


def _game(gid: str) -> dict[str, Any]:
    if gid not in games.GAMES:
        raise HTTPException(404, "Nincs ilyen játék.")
    return games.GAMES[gid]


async def _body(request: Request) -> dict[str, Any]:
    try:
        data = await request.json()
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


# --- auth ----------------------------------------------------------------------

@app.get("/api/version")
async def api_version() -> dict[str, Any]:
    return {"version": __version__, "needs_setup": not auth.has_user()}


@app.get("/api/me")
async def api_me(request: Request) -> dict[str, Any]:
    user = auth.read_token(request.cookies.get(config.SESSION_COOKIE))
    return {"user": user, "needs_setup": not auth.has_user(), "version": __version__}


@app.post("/api/setup")
async def api_setup(request: Request) -> dict[str, Any]:
    if auth.has_user():
        raise HTTPException(400, "A panel már be van állítva.")
    data = await _body(request)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if len(username) < 3 or len(password) < 8:
        raise HTTPException(400, "A felhasználónév min. 3, a jelszó min. 8 karakter legyen.")
    auth.create_user(username, password)
    resp = JSONResponse({"ok": True, "user": username})
    _set_cookie(resp, auth.make_token(username))
    return resp


@app.post("/api/login")
async def api_login(request: Request):
    data = await _body(request)
    username = (data.get("username") or "").strip()
    if not auth.check_login(username, data.get("password") or ""):
        raise HTTPException(401, "Hibás felhasználónév vagy jelszó.")
    resp = JSONResponse({"ok": True, "user": username})
    _set_cookie(resp, auth.make_token(username))
    return resp


@app.post("/api/logout")
async def api_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(config.SESSION_COOKIE)
    return resp


@app.post("/api/password")
async def api_password(request: Request) -> dict[str, Any]:
    data = await _body(request)
    user = request.state.user
    if not auth.change_password(user, data.get("old") or "", data.get("new") or ""):
        raise HTTPException(400, "A régi jelszó nem megfelelő.")
    if len(data.get("new") or "") < 8:
        raise HTTPException(400, "A jelszó min. 8 karakter legyen.")
    return {"ok": True}


def _set_cookie(resp: JSONResponse, token: str) -> None:
    resp.set_cookie(config.SESSION_COOKIE, token, max_age=config.SESSION_MAX_AGE,
                    httponly=True, samesite="lax")


# --- games / server files ------------------------------------------------------

@app.get("/api/games")
async def api_games() -> list[dict[str, Any]]:
    out = []
    for item in games.catalog():
        out.append({**item, **installer.state(item["id"])})
    return out


@app.get("/api/games/{gid}/dvars")
async def api_game_dvars(gid: str) -> dict[str, Any]:
    _game(gid)
    return {"groups": games.dvar_groups(gid), "limit_dvars": games.GAMES[gid]["limit_dvars"]}


@app.post("/api/games/{gid}/install")
async def api_game_install(gid: str, request: Request) -> dict[str, Any]:
    _game(gid)
    data = await _body(request)
    try:
        installer.install_async(gid, bool(data.get("force")))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    return installer.state(gid)


@app.get("/api/games/{gid}/install")
async def api_game_install_state(gid: str) -> dict[str, Any]:
    _game(gid)
    return installer.state(gid)


@app.delete("/api/games/{gid}/install")
async def api_game_remove(gid: str) -> dict[str, Any]:
    _game(gid)
    for inst in db.list_instances():
        if inst["game"] == gid and runner.manager.get(inst["id"]).is_alive():
            raise HTTPException(409, "Előbb állítsd le a játék futó szervereit.")
    installer.remove(gid)
    return installer.state(gid)


# --- maps ----------------------------------------------------------------------

@app.get("/api/games/{gid}/maps")
async def api_maps(gid: str, mod: str | None = None) -> dict[str, Any]:
    _game(gid)
    return {
        "game": gid,
        "mods": maps.mod_dirs(gid),
        "mod": mod or games.GAMES[gid]["moddir"],
        "maps": maps.detect_maps(gid, mod),
        "assets": maps.asset_files(gid, mod),
        "gametypes": games.GAMES[gid]["gametypes"],
        "installed": instances.game_installed(gid),
    }


@app.post("/api/games/{gid}/maps/url")
async def api_maps_url(gid: str, request: Request) -> dict[str, Any]:
    _game(gid)
    data = await _body(request)
    url = (data.get("url") or "").strip()
    try:
        return await asyncio.to_thread(maps.install_from_url, gid, data.get("mod"), url)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Letöltési hiba: {exc}") from exc


@app.post("/api/games/{gid}/maps/upload")
async def api_maps_upload(gid: str, file: UploadFile = File(...),
                          mod: str | None = Form(None)) -> dict[str, Any]:
    _game(gid)
    config.ensure_dirs()
    tmp = Path(tempfile.mkstemp(dir=config.DOWNLOAD_DIR, suffix=Path(file.filename or "").suffix)[1])
    try:
        with open(tmp, "wb") as fh:
            shutil.copyfileobj(file.file, fh)
        return await asyncio.to_thread(maps.install_asset, gid, mod, tmp, file.filename or tmp.name)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        tmp.unlink(missing_ok=True)


@app.delete("/api/games/{gid}/maps")
async def api_maps_delete(gid: str, rel: str) -> dict[str, Any]:
    _game(gid)
    try:
        maps.delete_asset(gid, rel)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True}


# --- instances -----------------------------------------------------------------

@app.get("/api/instances")
async def api_instances(query: bool = True) -> list[dict[str, Any]]:
    out = []
    for inst in db.list_instances():
        status = runner.manager.summary(inst, query=query)
        out.append({**inst, "status": status,
                    "game_name": games.GAMES[inst["game"]]["name"],
                    "game_short": games.GAMES[inst["game"]]["short"],
                    "installed": instances.game_installed(inst["game"])})
    return out


@app.post("/api/instances")
async def api_instance_create(request: Request) -> dict[str, Any]:
    data = await _body(request)
    try:
        inst = instances.new_instance(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    db.save_instance(inst)
    if instances.game_installed(inst["game"]):
        instances.write_cfg(inst)
    db.log_event("create", f"{inst['name']} létrehozva ({inst['game']})", inst["id"])
    return inst


@app.get("/api/instances/{iid}")
async def api_instance(iid: str) -> dict[str, Any]:
    inst = _inst(iid)
    gid = inst["game"]
    return {
        **inst,
        "status": runner.manager.summary(inst),
        "game_name": games.GAMES[gid]["name"],
        "game_short": games.GAMES[gid]["short"],
        "installed": instances.game_installed(gid),
        "gametypes": games.GAMES[gid]["gametypes"],
        "maps": maps.detect_maps(gid, inst.get("mod")),
        "mods": maps.mod_dirs(gid),
        "dvar_groups": games.dvar_groups(gid),
        "limit_dvars": games.GAMES[gid]["limit_dvars"],
        "cfg_path": str(instances.cfg_path(inst)),
        "cfg": instances.render_cfg(inst),
        "command": instances.command_preview(inst),
    }


@app.patch("/api/instances/{iid}")
async def api_instance_update(iid: str, request: Request) -> dict[str, Any]:
    inst = _inst(iid)
    data = await _body(request)
    if "extra_cfg" in data:
        inst["extra_cfg"] = data["extra_cfg"] or ""
    try:
        inst = instances.update_instance(inst, data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    db.save_instance(inst)
    if instances.game_installed(inst["game"]):
        instances.write_cfg(inst)
    db.log_event("update", f"{inst['name']} beállításai mentve", iid)
    return await api_instance(iid)


@app.delete("/api/instances/{iid}")
async def api_instance_delete(iid: str) -> dict[str, Any]:
    inst = _inst(iid)
    r = runner.manager.get(iid)
    if r.is_alive():
        await asyncio.to_thread(r.stop)
    cfg = instances.cfg_path(inst)
    if cfg.exists():
        cfg.unlink()
    db.delete_instance(iid)
    db.log_event("delete", f"{inst['name']} törölve", iid)
    return {"ok": True}


@app.post("/api/instances/{iid}/{action}")
async def api_instance_action(iid: str, action: str, request: Request) -> dict[str, Any]:
    inst = _inst(iid)
    r = runner.manager.get(iid)
    if action == "start":
        try:
            r.start(inst)
        except FileNotFoundError as exc:
            raise HTTPException(409, str(exc)) from exc
        except (RuntimeError, OSError) as exc:
            raise HTTPException(409, str(exc)) from exc
    elif action == "stop":
        await asyncio.to_thread(r.stop)
    elif action == "restart":
        await asyncio.to_thread(runner.manager.restart, inst)
    elif action == "command":
        data = await _body(request)
        cmd = (data.get("command") or "").strip()
        if not cmd:
            raise HTTPException(400, "Üres parancs.")
        via = data.get("via") or "stdin"
        if via == "rcon":
            try:
                reply = await asyncio.to_thread(
                    rcon.rcon, inst["ip"], inst["port"],
                    (inst.get("dvars") or {}).get("rcon_password", ""), cmd)
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
            r.emit(f"[rcon>] {cmd}")
            for line in (reply or "").splitlines():
                r.emit(f"[rcon] {line}")
            return {"ok": True, "reply": reply}
        try:
            r.send_stdin(cmd)
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc
    elif action == "writecfg":
        instances.write_cfg(inst)
    else:
        raise HTTPException(404, "Ismeretlen művelet.")
    return {"ok": True, "status": runner.manager.summary(inst)}


@app.get("/api/instances/{iid}/status")
async def api_instance_status(iid: str) -> dict[str, Any]:
    inst = _inst(iid)
    return runner.manager.summary(inst)


@app.get("/api/instances/{iid}/console")
async def api_instance_console(iid: str, limit: int = 400) -> dict[str, Any]:
    _inst(iid)
    return {"lines": runner.manager.get(iid).console(limit)}


@app.get("/api/instances/{iid}/logfile", response_class=PlainTextResponse)
async def api_instance_logfile(iid: str, tail: int = 500) -> str:
    inst = _inst(iid)
    path = instances.log_path(inst)
    if not path.exists():
        return "(még nincs log fájl)"
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return "".join(fh.readlines()[-tail:])


@app.websocket("/api/instances/{iid}/console/ws")
async def ws_console(ws: WebSocket, iid: str) -> None:
    if not auth.read_token(ws.cookies.get(config.SESSION_COOKIE)):
        await ws.close(code=4401)
        return
    await ws.accept()
    r = runner.manager.get(iid)
    r._loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    r.subs.add(queue)
    try:
        for line in r.console(200):
            await ws.send_text(line)
        while True:
            await ws.send_text(await queue.get())
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        r.subs.discard(queue)


# --- system --------------------------------------------------------------------

@app.get("/api/events")
async def api_events(limit: int = 80) -> list[dict[str, Any]]:
    return db.list_events(limit)


@app.get("/api/system")
async def api_system() -> dict[str, Any]:
    total, used, free = shutil.disk_usage(config.DATA_DIR)
    mem_total = mem_avail = 0
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1]) // 1024
                elif line.startswith("MemAvailable:"):
                    mem_avail = int(line.split()[1]) // 1024
    except OSError:
        pass
    load = os.getloadavg()
    running = sum(1 for i in db.list_instances() if runner.manager.get(i["id"]).is_alive())
    return {
        "version": __version__,
        "data_dir": str(config.DATA_DIR),
        "disk_total_gb": round(total / 1024 ** 3, 1),
        "disk_free_gb": round(free / 1024 ** 3, 1),
        "mem_total_mb": mem_total,
        "mem_free_mb": mem_avail,
        "load": [round(x, 2) for x in load],
        "instances": len(db.list_instances()),
        "running": running,
        "lib32": _lib32_present(),
    }


def _lib32_present() -> bool:
    patterns = ("/lib/i386-linux-gnu/libstdc++.so.6", "/usr/lib32/libstdc++.so.6",
                "/lib32/libstdc++.so.6", "/usr/lib/i386-linux-gnu/libstdc++.so.6")
    return any(Path(p).exists() for p in patterns)


# --- static web UI -------------------------------------------------------------

STATIC = config.PANEL_DIR / "static"
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/favicon.ico")
async def favicon() -> FileResponse:
    return FileResponse(STATIC / "favicon.svg", media_type="image/svg+xml")
