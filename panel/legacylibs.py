"""Régi 32 bites rendszerkönyvtárak, amiket a mai disztribúciók már nem csomagolnak.

A CoD / CoD2 / CoD:UO dedikált szerverek 2004-2006-os, 32 bites binárisok, és a
GCC 3-as C++ runtime-ot (libstdc++.so.5) kérik. Ez Debian 10 óta nincs a
tárolókban, ezért a panel a Debian archívumából szedi ki a könyvtárat, és a
saját data/lib32 könyvtárába teszi - a rendszerhez nem nyúl.
"""
from __future__ import annotations

import hashlib
import io
import os
import shutil
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

from . import config, db

UA = "codpanel/1.1"

LEGACY_LIBS: dict[str, dict[str, Any]] = {
    "libstdc++.so.5": {
        "package": "libstdc++5:i386",
        "url": "http://archive.debian.org/debian/pool/main/g/gcc-3.3/"
               "libstdc++5_3.3.6-32_i386.deb",
        "sha256": "ea5232f02e708ec1876d5539ac95b6407aea08954f5914aa548df5c66fa62294",
        "member": "libstdc++.so.5.0.7",
        "note": "GCC 3 C++ runtime (32 bit) - a CoD, CoD2 és CoD:UO szerverek kérik",
    },
}

SYSTEM_LIB_DIRS = (
    "/usr/lib/i386-linux-gnu", "/lib/i386-linux-gnu",
    "/usr/lib32", "/lib32", "/usr/lib", "/usr/local/lib",
)


def lib_dir() -> Path:
    config.ensure_dirs()
    return config.LIB32_DIR


def have_lib(name: str) -> bool:
    if (lib_dir() / name).exists():
        return True
    return any(Path(d, name).exists() for d in SYSTEM_LIB_DIRS)


def required_libs(gid: str) -> list[str]:
    from . import games
    return list(games.GAMES[gid].get("legacy_libs") or [])


def missing_libs(gid: str) -> list[str]:
    return [lib for lib in required_libs(gid) if not have_lib(lib)]


def status(gid: str | None = None) -> dict[str, Any]:
    from . import games
    gids = [gid] if gid else list(games.GAMES)
    out: dict[str, Any] = {"dir": str(lib_dir()), "libs": {}}
    for name, spec in LEGACY_LIBS.items():
        out["libs"][name] = {
            "present": have_lib(name),
            "note": spec["note"],
            "package": spec["package"],
            "needed_by": [g for g in gids if name in required_libs(g)],
        }
    out["missing"] = sorted({lib for g in gids for lib in missing_libs(g)})
    return out


# --- .deb kicsomagolás (ar + tar), külső eszköz nélkül -------------------------

def _ar_members(blob: bytes):
    if blob[:8] != b"!<arch>\n":
        raise RuntimeError("Hibás .deb fájl (nem ar archívum).")
    pos = 8
    while pos + 60 <= len(blob):
        header = blob[pos:pos + 60]
        name = header[0:16].decode("ascii", "replace").strip().rstrip("/")
        try:
            size = int(header[48:58].decode("ascii").strip())
        except ValueError:
            break
        yield name, blob[pos + 60:pos + 60 + size]
        pos += 60 + size + (size % 2)


def install_lib(name: str) -> dict[str, Any]:
    spec = LEGACY_LIBS.get(name)
    if not spec:
        raise ValueError(f"Ismeretlen könyvtár: {name}")
    target_dir = lib_dir()
    req = urllib.request.Request(spec["url"], headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - rögzített URL
        blob = resp.read()
    digest = hashlib.sha256(blob).hexdigest()
    if spec.get("sha256") and digest != spec["sha256"]:
        raise RuntimeError(f"A letöltött csomag ellenőrzőösszege nem egyezik ({digest}).")

    member = spec["member"]
    extracted: Path | None = None
    for ar_name, data in _ar_members(blob):
        if not ar_name.startswith("data.tar"):
            continue
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
            for info in tf.getmembers():
                if info.isfile() and Path(info.name).name == member:
                    src = tf.extractfile(info)
                    if src is None:
                        continue
                    extracted = target_dir / member
                    with open(extracted, "wb") as fh:
                        shutil.copyfileobj(src, fh)
                    extracted.chmod(0o755)
                    break
        if extracted:
            break
    if not extracted:
        raise RuntimeError(f"A csomagban nem találtam ilyen fájlt: {member}")

    link = target_dir / name
    if link.exists() or link.is_symlink():
        link.unlink()
    try:
        link.symlink_to(member)
    except OSError:
        shutil.copy2(extracted, link)
    db.log_event("install", f"{name} telepítve ide: {target_dir}", None)
    return {"lib": name, "path": str(link), "size": extracted.stat().st_size}


def install_missing(gid: str | None = None) -> dict[str, Any]:
    from . import games
    gids = [gid] if gid else list(games.GAMES)
    todo = sorted({lib for g in gids for lib in missing_libs(g)})
    done, failed = [], {}
    for name in todo:
        try:
            done.append(install_lib(name))
        except Exception as exc:
            failed[name] = str(exc)
    return {"installed": done, "failed": failed, "status": status(gid)}


def ld_library_path(base: Path) -> str:
    parts = [str(base), str(lib_dir())]
    current = os.environ.get("LD_LIBRARY_PATH")
    if current:
        parts.append(current)
    return ":".join(parts)
