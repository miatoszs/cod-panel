"""Map előnézeti képek: a játék saját fájljaiból kinyert loadscreen textúrák.

A kép soha nem a paneltől jön, hanem a felhasználó saját telepítéséből: a .iwd
csomagok (zip) tartalmazzák a loadscreen_<map>.iwi textúrákat, amiket PNG
bélyegképpé alakítunk és gyorsítótárazunk. Ha egy játéknál ez nem elérhető
(pl. a kép .ff fastfile-ban van), saját kép tölthető fel vagy adható meg URL-lel.
"""
from __future__ import annotations

import json
import re
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any

from . import config, games, instances, iwi

CUSTOM_EXT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".gif": "image/gif", ".webp": "image/webp"}
MISS_TTL = 24 * 3600          # ennyi ideig nem keressük újra a meg nem talált képet
_index_cache: dict[str, dict[str, Any]] = {}


def cache_dir(gid: str) -> Path:
    path = config.DATA_DIR / "mapimages" / gid
    path.mkdir(parents=True, exist_ok=True)
    return path


def _iwd_files(gid: str) -> list[Path]:
    base = instances.serverfiles_dir(gid)
    if not base.is_dir():
        return []
    return sorted(p for p in base.rglob("*.iwd") if p.is_file())


def _stamp(files: list[Path]) -> str:
    return ";".join(f"{p.name}:{p.stat().st_size}" for p in files)


def build_index(gid: str, force: bool = False) -> dict[str, list[str]]:
    """{iwi fájlnév (kisbetűs): [iwd útvonal, bejegyzés]} - a .iwd-k zip indexéből."""
    files = _iwd_files(gid)
    stamp = _stamp(files)
    cached = _index_cache.get(gid)
    if cached and cached["stamp"] == stamp and not force:
        return cached["images"]

    index_file = cache_dir(gid) / "index.json"
    if not force and index_file.exists():
        try:
            data = json.loads(index_file.read_text())
            if data.get("stamp") == stamp:
                _index_cache[gid] = data
                return data["images"]
        except (OSError, ValueError):
            pass

    images: dict[str, list[str]] = {}
    for iwd in files:
        try:
            with zipfile.ZipFile(iwd) as zf:
                for entry in zf.namelist():
                    if entry.lower().endswith(".iwi"):
                        key = Path(entry).name.lower()
                        images.setdefault(key, [str(iwd), entry])
        except (zipfile.BadZipFile, OSError):
            continue
    data = {"stamp": stamp, "images": images, "built": int(time.time())}
    _index_cache[gid] = data
    try:
        index_file.write_text(json.dumps(data))
    except OSError:
        pass
    return images


def _candidates(mapname: str) -> list[str]:
    m = mapname.lower()
    return [f"loadscreen_{m}.iwi", f"{m}_loadscreen.iwi", f"levelshot_{m}.iwi",
            f"preview_{m}.iwi", f"{m}.iwi"]


def custom_image(gid: str, mapname: str) -> Path | None:
    for ext in CUSTOM_EXT:
        path = cache_dir(gid) / f"{mapname}.custom{ext}"
        if path.exists():
            return path
    return None


def image_path(gid: str, mapname: str) -> Path | None:
    """A map bélyegképe; szükség esetén kinyeri a játékfájlokból. None = nincs."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", mapname or ""):
        return None
    custom = custom_image(gid, mapname)
    if custom:
        return custom

    png = cache_dir(gid) / f"{mapname}.png"
    if png.exists():
        return png
    miss = cache_dir(gid) / f"{mapname}.miss"
    if miss.exists() and time.time() - miss.stat().st_mtime < MISS_TTL:
        return None

    index = build_index(gid)
    found = None
    for name in _candidates(mapname):
        if name in index:
            found = index[name]
            break
    if not found:
        # tartalék: bármilyen iwi, aminek a nevében szerepel a map neve
        needle = mapname.lower()
        for key, value in index.items():
            if needle in key and "loadscreen" in key:
                found = value
                break
    if not found:
        miss.touch()
        return None

    try:
        with zipfile.ZipFile(found[0]) as zf:
            raw = zf.read(found[1])
        png.write_bytes(iwi.iwi_to_png(raw))
        return png
    except (OSError, zipfile.BadZipFile, iwi.IwiError, ValueError):
        miss.touch()
        return None


def media_type(path: Path) -> str:
    return CUSTOM_EXT.get(path.suffix.lower(), "image/png")


def save_custom(gid: str, mapname: str, data: bytes, filename: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", mapname or ""):
        raise ValueError("Érvénytelen map név.")
    ext = Path(filename or "").suffix.lower()
    if ext not in CUSTOM_EXT:
        raise ValueError("Támogatott képformátumok: PNG, JPG, GIF, WEBP.")
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("A kép legfeljebb 8 MB lehet.")
    for old in CUSTOM_EXT:
        (cache_dir(gid) / f"{mapname}.custom{old}").unlink(missing_ok=True)
    path = cache_dir(gid) / f"{mapname}.custom{ext}"
    path.write_bytes(data)
    (cache_dir(gid) / f"{mapname}.miss").unlink(missing_ok=True)
    return path


def clear_custom(gid: str, mapname: str) -> None:
    for ext in CUSTOM_EXT:
        (cache_dir(gid) / f"{mapname}.custom{ext}").unlink(missing_ok=True)


def have_image(gid: str, mapname: str) -> bool:
    if custom_image(gid, mapname):
        return True
    return (cache_dir(gid) / f"{mapname}.png").exists()


def prepare(gid: str, maps: list[str] | None = None) -> dict[str, Any]:
    """Előre legyártja a bélyegképeket (telepítés után, háttérben)."""
    from . import maps as mapsmod
    names = maps or [m["map"] for m in mapsmod.detect_maps(gid)]
    made, missing = [], []
    for name in names:
        if image_path(gid, name):
            made.append(name)
        else:
            missing.append(name)
    return {"game": gid, "generated": made, "missing": missing}


def reset(gid: str) -> None:
    path = config.DATA_DIR / "mapimages" / gid
    if path.exists():
        shutil.rmtree(path)
    _index_cache.pop(gid, None)
