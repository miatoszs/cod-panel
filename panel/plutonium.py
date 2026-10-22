"""Plutonium futtatókörnyezet (T4/T5/T6/IW5 szerverek).

A Plutonium a saját frissítőjével tölti le és tartja naprakészen a kliens- és
szerverfájlokat. A panel a hivatalos Linux updater binárist szerzi be, és a
data/plutonium könyvtárba telepíti a futtatókörnyezetet. A játékfájlokat
(pl. a World at War telepítést) a felhasználó adja - azt nem töltjük le.

Indítás a Plutonium saját mintája szerint:
    wine bin/plutonium-bootstrapper-win32.exe t4mp "<játékfájlok>" -dedicated \\
        +set key <szerver kulcs> +exec <cfg> +set net_port <port> +map_rotate
"""
from __future__ import annotations

import io
import shutil
import subprocess
import tarfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

from . import config, db

UPDATER_URL = ("https://github.com/mxve/plutonium-updater.rs/releases/latest/"
               "download/plutonium-updater-x86_64-unknown-linux-gnu.tar.gz")
BOOTSTRAPPER = "bin/plutonium-bootstrapper-win32.exe"
UA = "codpanel/1.2"

progress: dict[str, Any] = {"status": "idle", "message": "", "percent": 0}
_lock = threading.Lock()


def runtime_dir() -> Path:
    path = config.DATA_DIR / "plutonium"
    path.mkdir(parents=True, exist_ok=True)
    return path


def bootstrapper_path() -> Path:
    return runtime_dir() / BOOTSTRAPPER


def updater_path() -> Path:
    return runtime_dir() / "plutonium-updater"


def installed() -> bool:
    return bootstrapper_path().exists()


def status() -> dict[str, Any]:
    base = runtime_dir()
    size = 0
    files = 0
    if base.exists():
        for item in base.rglob("*"):
            if item.is_file():
                files += 1
                size += item.stat().st_size
    return {
        "installed": installed(),
        "path": str(base),
        "bootstrapper": str(bootstrapper_path()),
        "updater": updater_path().exists(),
        "files": files,
        "size_mb": round(size / 1048576, 1),
        "wine": bool(shutil.which("wine")),
        **progress,
    }


def _set(state: str, message: str, percent: float = 0) -> None:
    progress.update({"status": state, "message": message, "percent": round(percent, 1)})


def _fetch_updater() -> Path:
    """A hivatalos Linux updater binárist szedi le (GitHub release)."""
    target = updater_path()
    _set("downloading", "plutonium-updater letöltése...", 5)
    req = urllib.request.Request(UPDATER_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 - rögzített URL
        blob = resp.read()
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        member = next((m for m in tf.getmembers()
                       if m.isfile() and Path(m.name).name == "plutonium-updater"), None)
        if member is None:
            raise RuntimeError("A csomagban nincs plutonium-updater bináris.")
        src = tf.extractfile(member)
        if src is None:
            raise RuntimeError("Nem tudom kibontani az updatert.")
        with open(target, "wb") as fh:
            shutil.copyfileobj(src, fh)
    target.chmod(0o755)
    return target


def install(force: bool = False) -> None:
    """Blokkoló telepítés/frissítés; az install_async hívja háttérszálon."""
    base = runtime_dir()
    try:
        if force or not updater_path().exists():
            _fetch_updater()
        _set("updating", "Plutonium fájlok letöltése (ez eltarthat pár percig)...", 30)
        result = subprocess.run(
            [str(updater_path()), "-d", str(base), "--quiet"],
            cwd=str(base), capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            tail = (result.stderr or result.stdout or "").strip()[-300:]
            raise RuntimeError(f"A plutonium-updater hibára futott: {tail}")
        if not installed():
            raise RuntimeError(
                f"A frissítő lefutott, de nincs meg a {BOOTSTRAPPER}. Kimenet: "
                f"{(result.stdout or '')[-200:]}")
        _set("done", f"Plutonium telepítve ({status()['size_mb']} MB).", 100)
        db.log_event("install", "Plutonium futtatókörnyezet telepítve/frissítve", "plutonium")
    except Exception as exc:
        _set("error", str(exc))
        db.log_event("error", f"Plutonium telepítési hiba: {exc}", "plutonium")


def install_async(force: bool = False) -> None:
    with _lock:
        if progress.get("status") in ("downloading", "updating"):
            raise RuntimeError("A Plutonium telepítés már folyamatban van.")
        _set("downloading", "indítás...", 0)
    threading.Thread(target=install, args=(force,), daemon=True).start()


def remove() -> None:
    base = runtime_dir()
    if base.exists():
        shutil.rmtree(base)
    _set("idle", "")
