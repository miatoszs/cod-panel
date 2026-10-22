"""Instance model: defaults, validation, server.cfg generation, start command."""
from __future__ import annotations

import os
import re
import shlex
import shutil
import uuid
from pathlib import Path
from typing import Any

from . import config, db, games, plutonium

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,31}$")


def serverfiles_dir(gid: str) -> Path:
    return config.SERVERFILES_DIR / gid


def game_installed(gid: str) -> bool:
    g = games.GAMES[gid]
    if g.get("platform") == "plutonium":
        # kell a Plutonium futtatókörnyezet ÉS a felhasználó játékfájljai
        return plutonium.installed() and (serverfiles_dir(gid) / g["moddir"]).is_dir()
    return (serverfiles_dir(gid) / g["executable"]).exists()


def game_files_dir(inst: dict[str, Any]) -> Path:
    """A játék saját fájljai (Plutoniumnál máshová is mutathat, pl. a meglévő WaW-ra)."""
    custom = (inst.get("gamefiles") or "").strip()
    if custom:
        path = Path(custom)
        return path if path.is_absolute() else (config.DATA_DIR / path)
    return serverfiles_dir(inst["game"])


def work_dir(inst: dict[str, Any]) -> Path:
    """A folyamat munkakönyvtára: Plutoniumnál a futtatókörnyezet könyvtára."""
    if games.GAMES[inst["game"]].get("platform") == "plutonium":
        return plutonium.runtime_dir()
    return serverfiles_dir(inst["game"])


def effective_moddir(inst: dict[str, Any]) -> str:
    mod = (inst.get("mod") or "").strip().strip("/")
    return mod or games.GAMES[inst["game"]]["moddir"]


def mod_path(inst: dict[str, Any]) -> Path:
    return game_files_dir(inst) / effective_moddir(inst)


def cfg_name(inst: dict[str, Any]) -> str:
    return f"{inst['id']}.cfg"


def cfg_path(inst: dict[str, Any]) -> Path:
    return mod_path(inst) / cfg_name(inst)


def log_path(inst: dict[str, Any]) -> Path:
    return config.LOG_DIR / f"{inst['id']}.console.log"


def new_instance(data: dict[str, Any]) -> dict[str, Any]:
    gid = data.get("game")
    if gid not in games.GAMES:
        raise ValueError("Ismeretlen játék.")
    g = games.GAMES[gid]
    name = (data.get("name") or f"{g['short']} szerver").strip()
    iid = (data.get("id") or _slug(name) or uuid.uuid4().hex[:8])[:32]
    if not ID_RE.match(iid):
        raise ValueError("Az azonosító csak kisbetű, szám, - és _ lehet (2-32 karakter).")
    if db.get_instance(iid):
        raise ValueError(f"Már létezik szerver ezzel az azonosítóval: {iid}")

    dvars = games.default_dvars(gid)
    dvars["g_log"] = f"{iid}.log"
    dvars.update(data.get("dvars") or {})
    # minden dvar külön be/kikapcsolható; alapból az üres, opcionális mezők vannak kikapcsolva
    off = set(data.get("dvars_off") if data.get("dvars_off") is not None
              else games.default_disabled(gid))
    if data.get("hostname"):
        dvars["sv_hostname"] = data["hostname"]
    if data.get("rcon_password"):
        dvars["rcon_password"] = data["rcon_password"]
        off.discard("rcon_password")
    off.discard("sv_hostname")

    inst = {
        "id": iid,
        "name": name,
        "game": gid,
        "ip": data.get("ip") or "0.0.0.0",
        "port": int(data.get("port") or g["default_port"]),
        "maxplayers": int(data.get("maxplayers") or g["default_maxplayers"]),
        "gametype": data.get("gametype") or g["default_gametype"],
        "map": data.get("map") or g["default_map"],
        "mod": data.get("mod") or "",
        "gamefiles": data.get("gamefiles") or "",
        "rotation": data.get("rotation") or [],
        "limits": data.get("limits") or {},
        "dvars": dvars,
        "dvars_off": sorted(off),
        "gametype_enabled": bool(data.get("gametype_enabled", True)),
        "extra_params": data.get("extra_params") or "",
        "autostart": bool(data.get("autostart", False)),
        "autorestart": bool(data.get("autorestart", True)),
    }
    validate(inst)
    return inst


def update_instance(inst: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    for key in ("name", "ip", "gametype", "map", "mod", "extra_params", "gamefiles"):
        if key in data and data[key] is not None:
            inst[key] = data[key]
    for key in ("port", "maxplayers"):
        if data.get(key):
            inst[key] = int(data[key])
    for key in ("autostart", "autorestart", "gametype_enabled"):
        if key in data:
            inst[key] = bool(data[key])
    if "dvars_off" in data:
        inst["dvars_off"] = sorted({str(k) for k in (data["dvars_off"] or [])})
    if "rotation" in data:
        inst["rotation"] = data["rotation"] or []
    if "limits" in data:
        inst["limits"] = data["limits"] or {}
    if "dvars" in data:
        merged = dict(inst.get("dvars") or {})
        for k, v in (data["dvars"] or {}).items():
            if v is None:
                merged.pop(k, None)
            else:
                merged[str(k)] = str(v)
        inst["dvars"] = merged
    validate(inst)
    return inst


def validate(inst: dict[str, Any]) -> None:
    if not 1 <= inst["port"] <= 65535:
        raise ValueError("Érvénytelen port.")
    if not 1 <= inst["maxplayers"] <= 64:
        raise ValueError("A játékosszám 1 és 64 között legyen.")
    for other in db.list_instances():
        if other["id"] != inst["id"] and other["port"] == inst["port"] and other["ip"] == inst["ip"]:
            raise ValueError(f"A {inst['port']} portot már használja: {other['name']}")
    if not re.fullmatch(r"[A-Za-z0-9_.+-]*", inst.get("mod") or ""):
        raise ValueError("Érvénytelen mod könyvtárnév.")


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:32] or ""


# --- config file ---------------------------------------------------------------

def disabled_dvars(inst: dict[str, Any]) -> set[str]:
    """Dvars the user switched off - these are left out of the cfg entirely."""
    value = inst.get("dvars_off")
    if value is None:
        value = games.default_disabled(inst["game"])
    return {str(k) for k in value}


def gametype_enabled(inst: dict[str, Any]) -> bool:
    return bool(inst.get("gametype_enabled", True))


def rotation_string(inst: dict[str, Any]) -> str:
    parts = []
    for entry in inst.get("rotation") or []:
        gt = (entry.get("gametype") or inst["gametype"]).strip()
        mp = (entry.get("map") or "").strip()
        if not mp:
            continue
        parts.append(f"gametype {gt} map {mp}")
    return " ".join(parts)


def render_cfg(inst: dict[str, Any]) -> str:
    g = games.GAMES[inst["game"]]
    lines = [
        f"// {g['name']} - generálva a COD Panel által",
        f"// szerver: {inst['name']} ({inst['id']}) - kézi módosítás felülíródik mentéskor",
        "",
    ]
    dvars = dict(inst.get("dvars") or {})
    dvars.setdefault("g_log", f"{inst['id']}.log")
    off = disabled_dvars(inst)

    pluto = games.GAMES[inst["game"]].get("platform") == "plutonium"
    lines.append("// --- alap beállítások ---")
    for key in sorted(dvars):
        val = dvars[key]
        if key in off or val is None or val == "":
            continue
        if pluto and key == "key":
            lines.append("// a Plutonium szerver kulcs az indítási parancsban megy át")
            continue
        lines.append(f'set {key} "{val}"')
    skipped = sorted(k for k in off if dvars.get(k))
    if skipped:
        lines.append("// kikapcsolt dvar-ok (a panelben lehet visszakapcsolni): "
                     + ", ".join(skipped))

    lines.append("")
    lines.append("// --- játékmód és limitek ---")
    if gametype_enabled(inst):
        lines.append(f'set g_gametype "{inst["gametype"]}"')
    else:
        lines.append(f'// g_gametype kikapcsolva a panelben (a mod/cfg dönti el) '
                     f'- a panel {inst["gametype"]} módot feltételez')
    for key in sorted(inst.get("limits") or {}):
        val = (inst["limits"] or {})[key]
        if val not in (None, ""):
            lines.append(f'set {key} "{val}"')

    rot = rotation_string(inst)
    lines.append("")
    lines.append("// --- map rotáció ---")
    if rot:
        lines.append(f'set sv_mapRotation "{rot}"')
        lines.append('set sv_mapRotationCurrent ""')
    else:
        lines.append(f'// nincs rotáció beállítva, induló map: {inst["map"]}')

    extra = (inst.get("extra_cfg") or "").strip()
    if extra:
        lines += ["", "// --- egyéni cfg sorok ---", extra]
    lines.append("")
    return "\n".join(lines)


def write_cfg(inst: dict[str, Any]) -> Path:
    path = cfg_path(inst)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_cfg(inst), encoding="utf-8")
    return path


# --- start command -------------------------------------------------------------

def _wine_binary(g: dict[str, Any]) -> str:
    wine = os.environ.get("CODPANEL_WINE", "wine")
    if not shutil.which(wine):
        raise FileNotFoundError(
            f"A {g['name']} Windows bináris, a futtatásához wine kell, de nincs telepítve. "
            "A konténerben: dpkg --add-architecture i386 && apt install -y wine wine32:i386")
    return wine


def _plutonium_command(inst: dict[str, Any], g: dict[str, Any]) -> list[str]:
    """wine bin/plutonium-bootstrapper-win32.exe <mode> <játékfájlok> -dedicated ..."""
    exe = plutonium.bootstrapper_path()
    if not exe.exists():
        raise FileNotFoundError(
            "A Plutonium futtatókörnyezet nincs telepítve. A Játékfájlok oldalon a "
            "'Plutonium telepítése' gombbal pótolható.")
    gamefiles = game_files_dir(inst)
    if not (gamefiles / g["moddir"]).is_dir():
        raise FileNotFoundError(
            f"A játékfájlok nincsenek a helyükön: {gamefiles} (hiányzik a "
            f"{g['moddir']}/ könyvtár). Másold ide a saját World at War telepítésedet, "
            "vagy állítsd át a 'Játékfájlok könyvtára' mezőt a Beállításoknál.")
    cmd = [_wine_binary(g), str(exe), g["pluto_mode"], str(gamefiles), "-dedicated"]
    key = (inst.get("dvars") or {}).get("key", "").strip()
    if key and "key" not in disabled_dvars(inst):
        cmd += ["+set", "key", key]
    mod = (inst.get("mod") or "").strip()
    if mod:
        cmd += ["+set", "fs_game", mod]
    cmd += ["+set", "net_port", str(inst["port"]),
            "+set", "sv_maxclients", str(inst["maxplayers"])]
    if gametype_enabled(inst):
        cmd += ["+set", "g_gametype", inst["gametype"]]
    if inst.get("extra_params"):
        cmd += shlex.split(inst["extra_params"])
    cmd += ["+exec", cfg_name(inst)]
    cmd += ["+map_rotate"] if rotation_string(inst) else ["+map", inst["map"]]
    return cmd


def build_command(inst: dict[str, Any]) -> list[str]:
    gid = inst["game"]
    g = games.GAMES[gid]
    if g.get("platform") == "plutonium":
        return _plutonium_command(inst, g)
    base = serverfiles_dir(gid)
    exe = base / g["executable"]
    if not exe.exists():
        if g.get("install_mode") == "manual":
            raise FileNotFoundError(
                f"A {g['name']} fájljai hiányoznak. Másold a saját MW2 + IW4x "
                f"telepítésedet ide: {base} (a {g['executable']} a gyökerébe kerüljön).")
        raise FileNotFoundError(
            f"A {g['name']} szerverfájlok nincsenek telepítve ({exe}). "
            "Telepítsd a 'Játékfájlok' fülön.")
    cmd = [_wine_binary(g), str(exe)] if g.get("wine") else [str(exe)]
    template = g.get("start_template", games.START_TEMPLATE)
    cmd += shlex.split(template.format(
        basepath=str(base), ip=inst["ip"], port=inst["port"], maxplayers=inst["maxplayers"]))
    if g.get("extra_params"):
        cmd += shlex.split(g["extra_params"].format(basepath=str(base)))
    mod = (inst.get("mod") or "").strip()
    if mod:
        cmd += ["+set", "fs_game", mod]
    if gametype_enabled(inst):
        cmd += ["+set", "g_gametype", inst["gametype"]]
    if inst.get("extra_params"):
        cmd += shlex.split(inst["extra_params"])
    cmd += ["+exec", cfg_name(inst)]
    if rotation_string(inst):
        cmd += ["+map_rotate"]
    else:
        cmd += ["+map", inst["map"]]
    return cmd


def command_preview(inst: dict[str, Any]) -> str:
    try:
        return " ".join(shlex.quote(c) for c in build_command(inst))
    except FileNotFoundError:
        g = games.GAMES[inst["game"]]
        fake = dict(inst)
        return (f"{serverfiles_dir(inst['game'])}/{g['executable']} ... "
                f"(a szerverfájlok telepítése után látható a teljes parancs)")
