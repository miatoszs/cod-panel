"""Process supervisor: starts/stops game servers, keeps a live console buffer."""
from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import threading
import time
from collections import deque
from typing import Any

from . import config, db, games, instances, legacylibs, rcon

STATE_STOPPED = "stopped"
STATE_STARTING = "starting"
STATE_RUNNING = "running"
STATE_STOPPING = "stopping"
STATE_CRASHED = "crashed"


def _wine_env() -> dict[str, str]:
    """Fejnélküli, csendes wine futtatás saját prefixszel (különben az XDG_RUNTIME_DIR
    és a hiányzó grafikus meghajtó tele szemeteli a konzolt)."""
    prefix = config.DATA_DIR / "wineprefix"
    runtime = config.DATA_DIR / "run"
    for path in (prefix, runtime):
        path.mkdir(parents=True, exist_ok=True)
    runtime.chmod(0o700)
    return {
        "WINEPREFIX": str(prefix),
        "WINEDEBUG": os.environ.get("WINEDEBUG", "-all"),
        "XDG_RUNTIME_DIR": str(runtime),
        "DISPLAY": "",
        "WINEDLLOVERRIDES": os.environ.get("WINEDLLOVERRIDES", "mscoree,mshtml="),
    }

MAX_RESTARTS = 5  # ennyi sikertelen indítás után nem próbálkozunk tovább


class Runner:
    def __init__(self, iid: str) -> None:
        self.iid = iid
        self.proc: subprocess.Popen | None = None
        self.state = STATE_STOPPED
        self.lines: deque[str] = deque(maxlen=config.CONSOLE_BUFFER)
        self.subs: set[asyncio.Queue] = set()
        self.started_at: float | None = None
        self.exit_code: int | None = None
        self.manual_stop = False
        self.restarts = 0
        self.last_error = ""
        self.missing_lib = ""
        self.fatal_hint = ""
        self._restart_timer: threading.Timer | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    # --- console ---------------------------------------------------------
    LIB_ERROR = "error while loading shared libraries"
    FATAL_HINTS = (
        ("does not contain the gamefiles",
         "A Plutonium nem találja a játékfájlokat. Ehhez a TELJES (Windows-os) "
         "játéktelepítés kell - a LinuxGSM dedikált szerver csomag (csak .iwd fájlok) "
         "nem elég. Másold be a teljes játékkönyvtárat, és a Beállításoknál a "
         "'Játékfájlok könyvtára' mezőben mutass rá."),
        ("binkw32.dll",
         "Hiányzik a binkw32.dll, vagyis a játékkönyvtár nem a teljes telepítés. "
         "A Plutoniumhoz a teljes Windows-os játékmappa kell."),
        ("invalid game folder",
         "A megadott játékkönyvtár nem jó a Plutoniumnak - a teljes játéktelepítésre "
         "kell mutatnia."),
    )

    def emit(self, line: str) -> None:
        if self.LIB_ERROR in line:
            missing = line.split(self.LIB_ERROR, 1)[1].lstrip(": ").split(":")[0].strip()
            self.missing_lib = missing or "?"
        if not self.fatal_hint:
            low = line.lower()
            for needle, hint in self.FATAL_HINTS:
                if needle.lower() in low:
                    self.fatal_hint = hint
                    break
        stamped = f"{time.strftime('%H:%M:%S')} {line.rstrip()}"
        self.lines.append(stamped)
        for q in list(self.subs):
            try:
                if self._loop and self._loop.is_running():
                    self._loop.call_soon_threadsafe(q.put_nowait, stamped)
                else:
                    q.put_nowait(stamped)
            except Exception:
                self.subs.discard(q)

    def console(self, limit: int = 400) -> list[str]:
        data = list(self.lines)
        return data[-limit:]

    # --- lifecycle -------------------------------------------------------
    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, inst: dict[str, Any]) -> None:
        with self._lock:
            if self.is_alive():
                raise RuntimeError("A szerver már fut.")
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None
            cmd = instances.build_command(inst)
            instances.write_cfg(inst)
            cwd = instances.work_dir(inst)
            env = dict(os.environ, LD_LIBRARY_PATH=legacylibs.ld_library_path(cwd))
            if games.GAMES[inst["game"]].get("wine"):
                env.update(_wine_env())
            self.manual_stop = False
            self.exit_code = None
            self.last_error = ""
            self.missing_lib = ""
            self.fatal_hint = ""
            self._cancel_restart()
            self.state = STATE_STARTING
            self.emit(f"[panel] indítás: {' '.join(cmd)}")
            try:
                self.proc = subprocess.Popen(
                    cmd, cwd=str(cwd), env=env,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, bufsize=1,
                    universal_newlines=True, errors="replace",
                    start_new_session=True)
            except OSError as exc:
                self.state = STATE_CRASHED
                self.last_error = str(exc)
                self.emit(f"[panel] HIBA: {exc}")
                raise
            self.started_at = time.time()
            self.state = STATE_RUNNING
            threading.Thread(target=self._pump, args=(inst,), daemon=True).start()
            db.log_event("start", f"{inst['name']} elindítva", inst["id"])

    def _pump(self, inst: dict[str, Any]) -> None:
        proc = self.proc
        logfile = instances.log_path(inst)
        logfile.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(logfile, "a", encoding="utf-8", errors="replace") as fh:
                fh.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} start =====\n")
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.emit(line)
                    fh.write(line)
                    fh.flush()
        except Exception as exc:  # pragma: no cover - defensive
            self.emit(f"[panel] konzol olvasási hiba: {exc}")
        code = proc.wait() if proc else -1
        self.exit_code = code
        was_manual = self.manual_stop
        self.state = STATE_STOPPED if was_manual or code == 0 else STATE_CRASHED
        self.emit(f"[panel] a folyamat kilépett (kód: {code})")
        db.log_event("stop" if was_manual else "crash",
                     f"{inst['name']} leállt (kód: {code})", inst["id"])
        ran_for = time.time() - (self.started_at or time.time())
        if ran_for > 60:
            self.restarts = 0            # stabilan futott, tiszta lappal indulunk

        if was_manual or code == 0 or not inst.get("autorestart"):
            return
        if self.fatal_hint:
            self.emit(f"[panel] {self.fatal_hint} Automatikus újraindítás kihagyva.")
            self.state = STATE_CRASHED
            return
        if self.missing_lib:
            self.emit(f"[panel] HIÁNYZÓ RENDSZERKÖNYVTÁR: {self.missing_lib}. "
                      "A Játékfájlok oldalon a 'Hiányzó 32 bites könyvtárak telepítése' "
                      "gombbal pótolható - automatikus újraindítás kihagyva.")
            self.state = STATE_CRASHED
            return
        if self.restarts >= MAX_RESTARTS:
            self.emit(f"[panel] {MAX_RESTARTS} sikertelen indítás után leállítom az "
                      "automatikus újraindítást. Nézd át a fenti hibaüzenetet, "
                      "majd indítsd kézzel.")
            return
        self.restarts += 1
        delay = min(5 * self.restarts, 60)
        self.emit(f"[panel] automatikus újraindítás {delay} másodperc múlva "
                  f"({self.restarts}/{MAX_RESTARTS}. kísérlet)")
        self._cancel_restart()
        self._restart_timer = threading.Timer(delay, self._autorestart, args=(inst["id"],))
        self._restart_timer.daemon = True
        self._restart_timer.start()

    def _cancel_restart(self) -> None:
        if self._restart_timer:
            self._restart_timer.cancel()
            self._restart_timer = None

    def _autorestart(self, iid: str) -> None:
        self._restart_timer = None
        fresh = db.get_instance(iid)
        if not fresh or not fresh.get("autorestart") or self.is_alive():
            return
        try:
            self.start(fresh)
        except Exception as exc:
            self.emit(f"[panel] újraindítás sikertelen: {exc}")

    def stop(self, timeout: float = 12.0) -> None:
        self._cancel_restart()
        if not self.is_alive():
            self.state = STATE_STOPPED
            return
        self.manual_stop = True
        self._cancel_restart()
        self.state = STATE_STOPPING
        self.emit("[panel] leállítás (quit)")
        proc = self.proc
        assert proc is not None
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.write("quit\n")
                proc.stdin.flush()
        except Exception:
            pass
        deadline = time.time() + timeout
        while time.time() < deadline and proc.poll() is None:
            time.sleep(0.25)
        if proc.poll() is None:
            self.emit("[panel] SIGTERM")
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                proc.terminate()
            time.sleep(3)
        if proc.poll() is None:
            self.emit("[panel] SIGKILL")
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                proc.kill()
        self.state = STATE_STOPPED

    def send_stdin(self, command: str) -> None:
        if not self.is_alive() or not self.proc or not self.proc.stdin:
            raise RuntimeError("A szerver nem fut.")
        self.proc.stdin.write(command.rstrip("\n") + "\n")
        self.proc.stdin.flush()
        self.emit(f"[panel>] {command}")

    # --- stats -----------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "state": self.state if self.is_alive() or self.state in (STATE_CRASHED,) else
                     (STATE_CRASHED if self.state == STATE_CRASHED else STATE_STOPPED),
            "pid": self.proc.pid if self.is_alive() and self.proc else None,
            "uptime": int(time.time() - self.started_at) if self.is_alive() and self.started_at else 0,
            "exit_code": self.exit_code,
            "restarts": self.restarts,
            "rss_mb": None,
            "last_error": self.last_error,
            "missing_lib": self.missing_lib,
            "hint": self.fatal_hint,
        }
        if out["pid"]:
            try:
                with open(f"/proc/{out['pid']}/status") as fh:
                    for line in fh:
                        if line.startswith("VmRSS:"):
                            out["rss_mb"] = round(int(line.split()[1]) / 1024, 1)
                            break
            except OSError:
                pass
        return out


class Manager:
    def __init__(self) -> None:
        self.runners: dict[str, Runner] = {}

    def get(self, iid: str) -> Runner:
        if iid not in self.runners:
            self.runners[iid] = Runner(iid)
        return self.runners[iid]

    def start(self, inst: dict[str, Any]) -> None:
        self.get(inst["id"]).start(inst)

    def stop(self, iid: str) -> None:
        self.get(iid).stop()

    def restart(self, inst: dict[str, Any]) -> None:
        r = self.get(inst["id"])
        r.stop()
        time.sleep(1.0)
        r.restarts = 0
        r.start(inst)

    def stop_all(self) -> None:
        for r in self.runners.values():
            if r.is_alive():
                r.stop()

    def summary(self, inst: dict[str, Any], query: bool = True) -> dict[str, Any]:
        r = self.get(inst["id"])
        data = r.stats()
        data["id"] = inst["id"]
        data["players"] = None
        data["map"] = None
        data["gametype"] = None
        data["hostname"] = None
        if query and r.is_alive():
            st = rcon.status(inst["ip"], inst["port"], timeout=0.8)
            if st:
                info = st["info"]
                data["players"] = len(st["players"])
                data["playerlist"] = st["players"]
                data["map"] = info.get("mapname")
                data["gametype"] = info.get("g_gametype") or info.get("gametype")
                data["hostname"] = rcon.clean_color(info.get("sv_hostname", ""))
                data["maxplayers"] = info.get("sv_maxclients")
        return data


manager = Manager()


def autostart_all() -> None:
    for inst in db.list_instances():
        if inst.get("autostart"):
            try:
                manager.start(inst)
            except Exception as exc:
                db.log_event("error", f"{inst['name']} autostart hiba: {exc}", inst["id"])
