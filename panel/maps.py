"""Map and mod asset management: scan, upload, one-click URL download, delete."""
from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from . import config, db, games, installer, instances

# csak a többjátékos pályák kellenek: ezek mindig mp_ előtaggal vannak
BSP_RE = re.compile(r"maps/(?:mp/)?(mp_[A-Za-z0-9_]+)\.(?:bsp|d3dbsp)$", re.I)
ASSET_EXT = {".iwd", ".pk3", ".ff"}
ARCHIVE_EXT = {".zip"}
KEEP_TREE = ("usermaps/", "main/", "mods/", "uo/", "zone/", "raw/")


def mod_dirs(gid: str) -> list[str]:
    g = games.GAMES[gid]
    base = instances.serverfiles_dir(gid)
    out = [g["moddir"]]
    mods = base / "mods"
    if mods.is_dir():
        out += [f"mods/{d.name}" for d in sorted(mods.iterdir()) if d.is_dir()]
    return out


def _target_dir(gid: str, mod: str | None) -> Path:
    g = games.GAMES[gid]
    mod = (mod or g["moddir"]).strip("/")
    if not re.fullmatch(r"[A-Za-z0-9_./+-]+", mod) or ".." in mod:
        raise ValueError("Érvénytelen mod könyvtár.")
    return instances.serverfiles_dir(gid) / mod


def maps_in_asset(path: Path) -> list[str]:
    """Map names inside an .iwd/.pk3 (zip) package, or from a .ff filename."""
    if path.suffix.lower() == ".ff":
        name = path.stem
        return [] if name.endswith(("_load", "_patch")) else [name]
    try:
        with zipfile.ZipFile(path) as zf:
            found = set()
            for entry in zf.namelist():
                m = BSP_RE.search(entry.replace("\\", "/"))
                if m:
                    found.add(m.group(1))
            return sorted(found)
    except (zipfile.BadZipFile, OSError):
        return []


def asset_files(gid: str, mod: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    base = instances.serverfiles_dir(gid)
    search: list[Path] = [_target_dir(gid, mod)]
    if gid == "cod4":
        usermaps = base / "usermaps"
        if usermaps.is_dir():
            search += [d for d in sorted(usermaps.iterdir()) if d.is_dir()]
    for folder in search:
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.suffix.lower() in ASSET_EXT:
                out.append({
                    "name": f.name,
                    "rel": str(f.relative_to(base)),
                    "size_mb": round(f.stat().st_size / 1048576, 2),
                    "maps": maps_in_asset(f),
                    "stock": _is_stock(gid, f.name),
                })
    return out


def _is_stock(gid: str, filename: str) -> bool:
    stem = filename.lower()
    if gid in ("cod", "cod2", "coduo"):
        return bool(re.match(r"(iw_|localized_|pak)\d*", stem))
    return bool(re.match(r"(iw_|localized_|dlc|patch|common|code_post_gfx|ui_mp|en_)", stem))


def map_dirs(gid: str) -> list[str]:
    """Könyvtárak, ahol .ff alapú mapok lehetnek (CoD4/WaW/MW2)."""
    g = games.GAMES[gid]
    if g.get("map_dirs"):
        return list(g["map_dirs"])
    return ["usermaps"] if gid == "cod4" else []


def detect_maps(gid: str, mod: str | None = None) -> list[dict[str, Any]]:
    """Every map the server can load: stock list + maps found in installed assets."""
    from . import mapimages
    found: dict[str, dict[str, Any]] = {}
    for name in games.GAMES[gid]["stock_maps"]:
        found[name] = {"map": name, "source": "stock", "file": None}
    base = instances.serverfiles_dir(gid)
    for asset in asset_files(gid, mod):
        for name in asset["maps"]:
            if name not in found or found[name]["source"] == "stock":
                found[name] = {"map": name, "source": "custom", "file": asset["name"]}

    for rel in map_dirs(gid):
        folder = base / rel
        if not folder.is_dir():
            continue
        for item in folder.iterdir():
            if item.is_dir() and item.name.startswith("mp_"):
                found.setdefault(item.name, {"map": item.name, "source": "custom",
                                             "file": f"{rel}/{item.name}"})
            elif item.is_file() and item.suffix.lower() == ".ff" \
                    and item.stem.startswith("mp_"):
                name = re.sub(r"(_load|_patch)$", "", item.stem)
                found.setdefault(name, {"map": name, "source": "custom",
                                        "file": f"{rel}/{item.name}"})

    for name, entry in found.items():
        entry["label"] = games.map_label(gid, name)
        entry["image"] = mapimages.have_image(gid, name)
    return sorted(found.values(), key=lambda x: (x["source"] != "custom", x["map"]))


# --- installing custom content -------------------------------------------------

def _place_bare_asset(gid: str, mod: str | None, src: Path, filename: str) -> Path:
    ext = Path(filename).suffix.lower()
    if gid == "cod4" and ext in (".ff", ".iwd") and filename.lower().startswith("mp_"):
        mapname = re.sub(r"(_load|_patch)$", "", Path(filename).stem)
        dest_dir = instances.serverfiles_dir(gid) / "usermaps" / mapname
    else:
        dest_dir = _target_dir(gid, mod)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    shutil.copy2(src, dest)
    return dest


def install_asset(gid: str, mod: str | None, src: Path, filename: str) -> dict[str, Any]:
    """Install a downloaded/uploaded file. Handles .iwd/.pk3/.ff and .zip bundles."""
    filename = Path(filename).name
    ext = Path(filename).suffix.lower()
    installed: list[str] = []
    base = instances.serverfiles_dir(gid)
    if not instances.game_installed(gid):
        raise RuntimeError("Előbb telepítsd a játék szerverfájljait.")

    if ext in ASSET_EXT:
        dest = _place_bare_asset(gid, mod, src, filename)
        installed.append(str(dest.relative_to(base)))
    elif ext in ARCHIVE_EXT:
        with zipfile.ZipFile(src) as zf:
            names = [n.replace("\\", "/").lower() for n in zf.namelist()]
        structured = [n for n in names if any(n.startswith(k) or f"/{k}" in n for k in KEEP_TREE)]
        with tempfile.TemporaryDirectory(dir=config.DOWNLOAD_DIR) as tmp:
            tmpdir = Path(tmp)
            installer.safe_extract(src, tmpdir)
            if structured:
                # keep the original folder layout (usermaps/, main/, mods/, ...)
                for item in tmpdir.rglob("*"):
                    if not item.is_file():
                        continue
                    rel = item.relative_to(tmpdir).as_posix()
                    idx = -1
                    for key in KEEP_TREE:
                        pos = rel.lower().find(key)
                        if pos != -1:
                            idx = pos
                            break
                    if idx == -1:
                        continue
                    target = base / rel[idx:]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)
                    installed.append(rel[idx:])
            else:
                for item in tmpdir.rglob("*"):
                    if item.is_file() and item.suffix.lower() in ASSET_EXT:
                        dest = _place_bare_asset(gid, mod, item, item.name)
                        installed.append(str(dest.relative_to(base)))
    else:
        raise ValueError(f"Nem támogatott fájltípus: {ext or filename} "
                         "(.iwd, .pk3, .ff vagy .zip kell)")

    if not installed:
        raise RuntimeError("A csomagban nem találtam telepíthető map fájlt (.iwd/.ff/.pk3).")
    new_maps = sorted({m for rel in installed for m in maps_in_asset(base / rel)})
    db.log_event("maps", f"{games.GAMES[gid]['short']}: {len(installed)} fájl telepítve "
                         f"({', '.join(new_maps) or 'nincs új mapnév'})", gid)
    return {"installed": installed, "maps": new_maps}


def install_from_url(gid: str, mod: str | None, url: str) -> dict[str, Any]:
    if not re.match(r"^https?://", url):
        raise ValueError("Csak http(s) URL támogatott.")
    filename = Path(url.split("?")[0]).name or "download.zip"
    dest = config.DOWNLOAD_DIR / "custom" / f"{gid}_{filename}"
    installer.download_file(url, dest, None, "custom map")
    try:
        return install_asset(gid, mod, dest, filename)
    finally:
        dest.unlink(missing_ok=True)


def delete_asset(gid: str, rel: str) -> None:
    base = instances.serverfiles_dir(gid).resolve()
    target = (base / rel).resolve()
    if not str(target).startswith(str(base)) or not target.exists():
        raise ValueError("Érvénytelen fájl.")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    db.log_event("maps", f"{games.GAMES[gid]['short']}: {rel} törölve", gid)
