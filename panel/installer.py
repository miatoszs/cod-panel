"""One-click install of the dedicated server files (LinuxGSM mirrors)."""
from __future__ import annotations

import hashlib
import shutil
import tarfile
import threading
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from . import config, db, games, instances

UA = "codpanel/1.0 (+https://github.com)"

progress: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def state(gid: str) -> dict[str, Any]:
    g = games.GAMES[gid]
    base = instances.serverfiles_dir(gid)
    info = progress.get(gid, {"status": "idle", "percent": 0, "message": ""})
    if g.get("install_mode") == "manual" and info["status"] == "idle":
        info = {"status": "manual", "percent": 0,
                "message": "Saját játékfájlok szükségesek (MW2 + IW4x)."}
    size = 0
    if base.exists():
        size = sum(f.stat().st_size for f in base.rglob("*") if f.is_file())
    return {
        "game": gid,
        "install_mode": g.get("install_mode", "download"),
        "installed": instances.game_installed(gid),
        "path": str(base),
        "size_mb": round(size / 1024 / 1024, 1),
        "archive_url": g["archive_url"],
        **info,
    }


def _set(gid: str, status: str, percent: float = 0, message: str = "") -> None:
    progress[gid] = {"status": status, "percent": round(percent, 1), "message": message}


def download_file(url: str, dest: Path, gid: str | None = None,
                  label: str = "letöltés") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed mirrors / user URL
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as fh:
            while True:
                chunk = resp.read(262144)
                if not chunk:
                    break
                fh.write(chunk)
                done += len(chunk)
                if gid:
                    pct = (done / total * 100) if total else 0
                    _set(gid, "downloading", pct,
                         f"{label}: {done // 1048576} MB"
                         + (f" / {total // 1048576} MB" if total else ""))
    return dest


def md5sum(path: Path) -> str:
    h = hashlib.md5()  # noqa: S324 - matches LinuxGSM published checksums
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_extract(archive: Path, target: Path) -> None:
    """Extract tar.*/zip without escaping the target directory."""
    target.mkdir(parents=True, exist_ok=True)
    target = target.resolve()
    if archive.name.endswith((".zip", ".pk3")):
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                out = (target / member.filename).resolve()
                if not str(out).startswith(str(target)):
                    continue
                if member.is_dir():
                    out.mkdir(parents=True, exist_ok=True)
                else:
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(out, "wb") as dst:
                        shutil.copyfileobj(src, dst)
        return
    with tarfile.open(archive) as tf:
        members = []
        for m in tf.getmembers():
            out = (target / m.name).resolve()
            if not str(out).startswith(str(target)) or m.issym() or m.islnk():
                continue
            members.append(m)
        try:
            tf.extractall(target, members=members, filter="data")
        except TypeError:  # Python < 3.12
            tf.extractall(target, members=members)  # noqa: S202 - members pre-filtered


def install(gid: str, force: bool = False) -> None:
    """Blocking install; call via install_async."""
    g = games.GAMES[gid]
    if g.get("install_mode") == "manual":
        _set(gid, "manual", 0, "Ehhez a játékhoz saját fájlok kellenek (nincs letölthető csomag).")
        return
    base = instances.serverfiles_dir(gid)
    if instances.game_installed(gid) and not force:
        _set(gid, "done", 100, "Már telepítve.")
        return
    archive = config.DOWNLOAD_DIR / g["archive_name"]
    try:
        if not (archive.exists() and md5sum(archive) == g["archive_md5"]):
            _set(gid, "downloading", 0, "letöltés indul...")
            download_file(g["archive_url"], archive, gid, "szerverfájlok")
            _set(gid, "verifying", 100, "MD5 ellenőrzés...")
            got = md5sum(archive)
            if got != g["archive_md5"]:
                archive.unlink(missing_ok=True)
                raise RuntimeError(f"Hibás MD5 ({got}), a letöltés sérült.")
        _set(gid, "extracting", 100, "kibontás...")
        safe_extract(archive, base)
        exe = base / g["executable"]
        if not exe.exists():
            # some archives nest the files one level deep
            for cand in base.rglob(g["executable"]):
                src = cand.parent
                for item in src.iterdir():
                    shutil.move(str(item), str(base / item.name))
                break
        if exe.exists():
            exe.chmod(0o755)
        for extra in base.glob("*.so*"):
            extra.chmod(0o755)
        if not exe.exists():
            raise RuntimeError(f"A futtatható fájl nem található a csomagban: {g['executable']}")
        _set(gid, "done", 100, f"{g['name']} telepítve.")
        db.log_event("install", f"{g['name']} szerverfájlok telepítve", gid)
    except Exception as exc:
        _set(gid, "error", 0, str(exc))
        db.log_event("error", f"{g['name']} telepítési hiba: {exc}", gid)


def install_async(gid: str, force: bool = False) -> None:
    with _lock:
        cur = progress.get(gid, {}).get("status")
        if cur in ("downloading", "extracting", "verifying"):
            raise RuntimeError("A telepítés már folyamatban van.")
        _set(gid, "downloading", 0, "indítás...")
    threading.Thread(target=install, args=(gid, force), daemon=True).start()


def remove(gid: str) -> None:
    base = instances.serverfiles_dir(gid)
    if base.exists():
        shutil.rmtree(base)
    _set(gid, "idle", 0, "")
    db.log_event("install", f"{games.GAMES[gid]['name']} szerverfájlok törölve", gid)
