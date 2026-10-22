"""MCP szerver a COD Panelhez - AI-ból vezérelhető szerverkezelés.

Indítás:
    CODPANEL_URL=http://127.0.0.1:8080 CODPANEL_TOKEN=codp_... \\
        python -m panel.mcp_server

A panel REST API-ját hívja API tokennel (Beállítások -> AI vezérlés fülön
készíthető), ezért futhat a konténerben és távolról is.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

try:
    from mcp.server.mcpserver import MCPServer
    # a ToolError üzenete eljut a klienshez, a többi kivételt az SDK elrejti
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Hiányzik az MCP SDK. Telepítsd a panel virtualenv-jébe:\n"
        "    /opt/codpanel/venv/bin/pip install 'mcp>=2,<3'\n"
        f"({exc})"
    ) from exc

PANEL_URL = os.environ.get("CODPANEL_URL", "http://127.0.0.1:8080").rstrip("/")
PANEL_TOKEN = os.environ.get("CODPANEL_TOKEN", "")
TIMEOUT = float(os.environ.get("CODPANEL_TIMEOUT", "60"))

server = MCPServer(
    name="codpanel",
    instructions=(
        "Call of Duty szerverek vezérlése a COD Panelen keresztül (CoD, CoD:UO, CoD2, "
        "CoD4, CoD:WaW eredeti és Plutonium, MW2). Szerverek indítása/leállítása, élő map- és játékmódváltás, "
        "új példány létrehozása, map rotáció, custom mapok telepítése és hibakeresés a "
        "szerver konzoljából. Hibakeresésnél először a console() és a system_status() "
        "eszközt nézd meg. Az azonosító (server_id) a példány rövid neve, pl. 'cod2-fun'."
    ),
)


# --- HTTP réteg ---------------------------------------------------------------

def _request(method: str, path: str, body: Any = None,
             raw: bool = False) -> Any:
    url = f"{PANEL_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if data:
        headers["Content-Type"] = "application/json"
    if PANEL_TOKEN:
        headers["Authorization"] = f"Bearer {PANEL_TOKEN}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310
            payload = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail).get("detail", detail)
        except ValueError:
            pass
        if exc.code == 401:
            raise ToolError(
                "A panel elutasította a tokent. Ellenőrizd a CODPANEL_TOKEN értékét "
                "(Beállítások -> AI vezérlés -> Token készítése)."
            ) from exc
        raise ToolError(f"A panel hibát adott ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise ToolError(
            f"Nem érem el a panelt itt: {PANEL_URL} ({exc.reason}). "
            "Fut a codpanel szolgáltatás? A CODPANEL_URL helyes?"
        ) from exc
    if raw:
        return payload
    try:
        return json.loads(payload) if payload else {}
    except ValueError:
        return {"raw": payload}


def _instance(server_id: str) -> dict[str, Any]:
    return _request("GET", f"/api/instances/{urllib.parse.quote(server_id)}")


def _slim(inst: dict[str, Any]) -> dict[str, Any]:
    st = inst.get("status") or {}
    return {
        "id": inst["id"],
        "name": inst["name"],
        "game": inst.get("game_short") or inst.get("game"),
        "address": f"{inst['ip']}:{inst['port']}",
        "state": st.get("state", "stopped"),
        "map": st.get("map") or inst.get("map"),
        "gametype": st.get("gametype") or inst.get("gametype"),
        "players": f"{st.get('players', 0) or 0}/{inst.get('maxplayers')}",
        "uptime_sec": st.get("uptime", 0),
        "memory_mb": st.get("rss_mb"),
        "missing_lib": st.get("missing_lib") or None,
        "game_files_installed": inst.get("installed", True),
    }


# --- áttekintés és hibakeresés -------------------------------------------------

@server.tool(description="Az összes szerver példány listája élő állapottal "
                         "(fut-e, melyik map, hány játékos).")
def list_servers() -> dict[str, Any]:
    data = _request("GET", "/api/instances")
    return {"servers": [_slim(i) for i in data], "count": len(data)}


@server.tool(description="Egy szerver részletes adatai: beállítások, dvar-ok, map rotáció, "
                         "elérhető mapok, generált cfg és az indítási parancs.")
def server_details(server_id: str) -> dict[str, Any]:
    inst = _instance(server_id)
    return {
        "summary": _slim(inst),
        "mod": inst.get("mod") or None,
        "autostart": inst.get("autostart"),
        "autorestart": inst.get("autorestart"),
        "rotation": inst.get("rotation") or [],
        "limits": inst.get("limits") or {},
        "dvars": inst.get("dvars") or {},
        "disabled_dvars": inst.get("dvars_off") or [],
        "available_maps": [{"map": m["map"], "name": m.get("label")}
                           for m in inst.get("maps", [])],
        "gametypes": inst.get("gametypes", []),
        "cfg_path": inst.get("cfg_path"),
        "start_command": inst.get("command"),
        "players": (inst.get("status") or {}).get("playerlist", []),
    }


@server.tool(description="A szerver konzoljának utolsó sorai - hibakereséshez ezt nézd meg "
                         "először (indulási hibák, hiányzó fájlok, összeomlás oka).")
def console(server_id: str, lines: int = 60) -> dict[str, Any]:
    data = _request("GET", f"/api/instances/{urllib.parse.quote(server_id)}"
                           f"/console?limit={max(1, min(lines, 400))}")
    return {"server_id": server_id, "lines": data.get("lines", [])}


@server.tool(description="A panel és a gép állapota: szabad memória, lemez, futó szerverek, "
                         "és hogy megvannak-e a 32 bites futtatókörnyezet könyvtárai.")
def system_status() -> dict[str, Any]:
    sys_info = _request("GET", "/api/system")
    libs = sys_info.get("libs") or {}
    return {
        "panel_version": sys_info.get("version"),
        "servers_running": sys_info.get("running"),
        "servers_total": sys_info.get("instances"),
        "memory_free_mb": sys_info.get("mem_free_mb"),
        "disk_free_gb": sys_info.get("disk_free_gb"),
        "load": sys_info.get("load"),
        "lib32_ok": sys_info.get("lib32"),
        "missing_libraries": libs.get("missing", []),
        "data_dir": sys_info.get("data_dir"),
    }


@server.tool(description="A panel eseménynaplója (indítások, összeomlások, telepítések).")
def panel_events(limit: int = 40) -> dict[str, Any]:
    data = _request("GET", f"/api/events?limit={max(1, min(limit, 200))}")
    return {"events": [{"time": e["ts"], "kind": e["kind"], "ref": e.get("ref"),
                        "text": e["text"]} for e in data]}


# --- vezérlés ------------------------------------------------------------------

@server.tool(description="Szerver indítása.")
def start_server(server_id: str) -> dict[str, Any]:
    _request("POST", f"/api/instances/{urllib.parse.quote(server_id)}/start")
    return {"ok": True, "status": _slim(_instance(server_id))}


@server.tool(description="Szerver leállítása (előbb 'quit' a konzolon, aztán jelek).")
def stop_server(server_id: str) -> dict[str, Any]:
    _request("POST", f"/api/instances/{urllib.parse.quote(server_id)}/stop")
    return {"ok": True, "status": _slim(_instance(server_id))}


@server.tool(description="Szerver újraindítása (a mentett cfg-vel indul újra).")
def restart_server(server_id: str) -> dict[str, Any]:
    _request("POST", f"/api/instances/{urllib.parse.quote(server_id)}/restart")
    return {"ok": True, "status": _slim(_instance(server_id))}


@server.tool(description="Azonnali map- és játékmódváltás élőben, a futó szerveren. "
                         "A cfg nem módosul, újraindítás után a régi beállítás jön vissza. "
                         "A map kódnevét add meg (pl. mp_toujane); a list_maps adja a listát.")
def change_map(server_id: str, map_name: str, gametype: str | None = None) -> dict[str, Any]:
    command = f"map {map_name}" if not gametype else f"g_gametype {gametype}; map {map_name}"
    path = f"/api/instances/{urllib.parse.quote(server_id)}/command"
    try:
        _request("POST", path, {"command": command, "via": "stdin"})
    except ValueError:
        _request("POST", path, {"command": command, "via": "rcon"})
    return {"ok": True, "sent": command,
            "note": "Tartós változtatáshoz használd az update_server eszközt."}


@server.tool(description="Tetszőleges parancs küldése a szerver konzoljára vagy RCON-on "
                         "(pl. 'status', 'say Hello', 'map_rotate', 'clientkick 3').")
def send_command(server_id: str, command: str, via: str = "stdin") -> dict[str, Any]:
    if via not in ("stdin", "rcon"):
        raise ToolError("A 'via' értéke csak 'stdin' vagy 'rcon' lehet.")
    result = _request("POST", f"/api/instances/{urllib.parse.quote(server_id)}/command",
                      {"command": command, "via": via})
    return {"ok": True, "reply": result.get("reply", "")}


# --- létrehozás és beállítás ---------------------------------------------------

@server.tool(description="Új szerver példány létrehozása. A game értéke: cod, coduo, cod2, "
                         "cod4, codwaw vagy mw2. A port alapból 28960, több szervernél "
                         "növekvő (28961, 28962 ...). Létrehozás után a start_server indítja.")
def create_server(game: str, name: str, port: int | None = None,
                  maxplayers: int | None = None, gametype: str | None = None,
                  map_name: str | None = None, rcon_password: str | None = None,
                  server_id: str | None = None, mod: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"game": game, "name": name, "hostname": name}
    for key, value in (("port", port), ("maxplayers", maxplayers), ("gametype", gametype),
                       ("map", map_name), ("rcon_password", rcon_password),
                       ("id", server_id), ("mod", mod)):
        if value is not None:
            body[key] = value
    inst = _request("POST", "/api/instances", body)
    return {"ok": True, "server_id": inst["id"], "summary": _slim(_instance(inst["id"]))}


@server.tool(description="Szerver beállításainak tartós módosítása (cfg újraírásával). "
                         "Csak a megadott mezők változnak. A dvars egy objektum, pl. "
                         "{'sv_hostname': '^1Teszt', 'scr_friendlyfire': '1'}. "
                         "Újraindítás után lép életbe, vagy restart_server=true-val azonnal.")
def update_server(server_id: str, name: str | None = None, gametype: str | None = None,
                  map_name: str | None = None, maxplayers: int | None = None,
                  port: int | None = None, mod: str | None = None,
                  autostart: bool | None = None, autorestart: bool | None = None,
                  dvars: dict[str, str] | None = None,
                  restart_server: bool = False) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for key, value in (("name", name), ("gametype", gametype), ("map", map_name),
                       ("maxplayers", maxplayers), ("port", port), ("mod", mod),
                       ("autostart", autostart), ("autorestart", autorestart),
                       ("dvars", dvars)):
        if value is not None:
            body[key] = value
    if not body:
        raise ToolError("Nem adtál meg módosítandó beállítást.")
    _request("PATCH", f"/api/instances/{urllib.parse.quote(server_id)}", body)
    if restart_server:
        _request("POST", f"/api/instances/{urllib.parse.quote(server_id)}/restart")
    return {"ok": True, "restarted": restart_server,
            "summary": _slim(_instance(server_id))}


@server.tool(description="Map rotáció beállítása. A bejegyzések 'jatekmod:map' alakúak, "
                         "pl. ['tdm:mp_toujane', 'sd:mp_carentan']. Üres lista törli a "
                         "rotációt (ilyenkor az induló mapon marad a szerver).")
def set_rotation(server_id: str, entries: list[str],
                 restart_server: bool = False) -> dict[str, Any]:
    rotation = []
    for item in entries:
        if ":" not in item:
            raise ToolError(f"Hibás bejegyzés: {item!r} - 'jatekmod:map' alak kell.")
        gametype, map_name = item.split(":", 1)
        rotation.append({"gametype": gametype.strip(), "map": map_name.strip()})
    _request("PATCH", f"/api/instances/{urllib.parse.quote(server_id)}",
             {"rotation": rotation})
    if restart_server:
        _request("POST", f"/api/instances/{urllib.parse.quote(server_id)}/restart")
    return {"ok": True, "rotation": rotation, "restarted": restart_server}


@server.tool(description="Szerver példány törlése. Visszafordíthatatlan, ezért a confirm "
                         "paramétert kifejezetten true-ra kell állítani. A játékfájlok és "
                         "a mapok megmaradnak.")
def delete_server(server_id: str, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        raise ToolError("A törléshez confirm=true kell. Kérdezd meg előbb a felhasználót.")
    _request("DELETE", f"/api/instances/{urllib.parse.quote(server_id)}")
    return {"ok": True, "deleted": server_id}


# --- tartalom ------------------------------------------------------------------

@server.tool(description="A támogatott játékok és a szerverfájljaik állapota.")
def list_games() -> dict[str, Any]:
    data = _request("GET", "/api/games")
    return {"games": [{
        "id": g["id"], "name": g["name"], "installed": g["installed"],
        "install_mode": g.get("install_mode"), "size_mb": g.get("size_mb"),
        "default_port": g["default_port"],
        "gametypes": [gt[0] for gt in g.get("gametypes", [])],
        "missing_libraries": g.get("missing_libs", []),
        "status": g.get("status"), "message": g.get("message"),
    } for g in data]}


@server.tool(description="Egy játék elérhető mapjai: kódnév, emberi név és hogy alap vagy "
                         "custom map-e. A change_map és a set_rotation a kódnevet kéri.")
def list_maps(game: str, mod: str | None = None) -> dict[str, Any]:
    query = f"?mod={urllib.parse.quote(mod)}" if mod else ""
    data = _request("GET", f"/api/games/{urllib.parse.quote(game)}/maps{query}")
    return {"game": game, "maps": [{"map": m["map"], "name": m.get("label"),
                                    "source": m["source"], "has_image": m.get("image")}
                                   for m in data.get("maps", [])],
            "gametypes": [gt[0] for gt in data.get("gametypes", [])]}


@server.tool(description="Játék szerverfájljainak telepítése a LinuxGSM tükrökről. "
                         "Háttérben fut; az állapotot a list_games mutatja.")
def install_game(game: str) -> dict[str, Any]:
    state = _request("POST", f"/api/games/{urllib.parse.quote(game)}/install", {})
    return {"ok": True, "status": state.get("status"), "message": state.get("message"),
            "note": "A letöltés a háttérben fut, kérdezd le a list_games eszközzel."}


@server.tool(description="Custom map telepítése URL-ről (.iwd, .pk3, .ff vagy .zip). "
                         "Telepítés után a map azonnal kiválasztható.")
def install_custom_map(game: str, url: str, mod: str | None = None) -> dict[str, Any]:
    result = _request("POST", f"/api/games/{urllib.parse.quote(game)}/maps/url",
                      {"url": url, "mod": mod})
    return {"ok": True, "files": result.get("installed", []),
            "new_maps": result.get("maps", [])}


@server.tool(description="A hiányzó 32 bites rendszerkönyvtárak pótlása (libstdc++.so.5). "
                         "Ezt akkor kell futtatni, ha a szerver 127-es kóddal azonnal kilép.")
def install_missing_libs(game: str | None = None) -> dict[str, Any]:
    result = _request("POST", "/api/libs/install", {"game": game} if game else {})
    return {"ok": True, "installed": [i["lib"] for i in result.get("installed", [])],
            "failed": result.get("failed", {}),
            "still_missing": (result.get("status") or {}).get("missing", [])}


def main() -> None:
    import sys
    if not PANEL_TOKEN:
        print("Figyelem: nincs CODPANEL_TOKEN, a panel el fogja utasítani a hívásokat.",
              file=sys.stderr)
    transport = os.environ.get("CODPANEL_MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        server.run(transport="stdio")
        return
    # hálózati mód: a kliens URL-lel csatlakozik (pl. a konténerben futtatva)
    host = os.environ.get("CODPANEL_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("CODPANEL_MCP_PORT", "8765"))
    print(f"MCP szerver: {transport} a következőn: {host}:{port}", file=sys.stderr)
    server.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    main()
