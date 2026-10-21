"""Catalog of supported Call of Duty dedicated servers.

Binaries, start parameters, archive URLs and MD5 sums match the LinuxGSM
defaults (codserver / cod2server / coduoserver / cod4server / codwawserver),
so a panel install behaves like a LinuxGSM install without the CLI.
"""
from __future__ import annotations

from typing import Any

# --- reusable dvar form groups -------------------------------------------------

def _basic(default_hostname: str) -> dict[str, Any]:
    return {
        "title": "Alapok",
        "fields": [
            {"key": "sv_hostname", "label": "Szerver neve", "type": "text",
             "default": default_hostname, "help": "Color kódok: ^1 piros, ^2 zöld, ^3 sárga ..."},
            {"key": "rcon_password", "label": "RCON jelszó", "type": "password", "default": ""},
            {"key": "g_password", "label": "Belépési jelszó (privát szerver)", "type": "password", "default": ""},
            {"key": "sv_privateClients", "label": "Privát slotok", "type": "int", "default": "0"},
            {"key": "sv_privatePassword", "label": "Privát slot jelszó", "type": "password", "default": ""},
            {"key": "sv_maxPing", "label": "Max ping (0 = ki)", "type": "int", "default": "0"},
            {"key": "sv_minPing", "label": "Min ping", "type": "int", "default": "0"},
        ],
    }


_NETWORK_Q3 = {
    "title": "Hálózat és letöltés",
    "fields": [
        {"key": "sv_maxRate", "label": "sv_maxRate", "type": "int", "default": "25000"},
        {"key": "sv_floodProtect", "label": "Flood védelem", "type": "bool", "default": "1"},
        {"key": "sv_timeout", "label": "Timeout (s)", "type": "int", "default": "240"},
        {"key": "sv_reconnectlimit", "label": "Reconnect limit", "type": "int", "default": "3"},
        {"key": "sv_pure", "label": "sv_pure (fájl ellenőrzés)", "type": "bool", "default": "1"},
        {"key": "sv_allowDownload", "label": "Beépített letöltés engedélyezése", "type": "bool", "default": "1"},
        {"key": "sv_wwwDownload", "label": "HTTP (fast) download", "type": "bool", "default": "0"},
        {"key": "sv_wwwBaseURL", "label": "HTTP download URL", "type": "text", "default": "",
         "help": "Pl. http://1.2.3.4/cod2 — ide töltsd fel a custom .iwd fájlokat"},
        {"key": "sv_wwwDlDisconnected", "label": "Letöltés disconnectelve", "type": "bool", "default": "0"},
    ],
}

_ADMIN = {
    "title": "Admin és szavazás",
    "fields": [
        {"key": "g_allowVote", "label": "Szavazás engedélyezése", "type": "bool", "default": "1"},
        {"key": "g_log", "label": "Log fájl neve", "type": "text", "default": "games_mp.log"},
        {"key": "g_logSync", "label": "Log szinkron írás", "type": "bool", "default": "1"},
        {"key": "logfile", "label": "Konzol log (0-3)", "type": "int", "default": "2"},
        {"key": "sv_punkbuster", "label": "PunkBuster", "type": "bool", "default": "0"},
    ],
}


def _gameplay_ww2() -> dict[str, Any]:
    return {
        "title": "Játékmenet",
        "fields": [
            {"key": "scr_friendlyfire", "label": "Friendly fire", "type": "select", "default": "0",
             "options": [["0", "Ki"], ["1", "Be"], ["2", "Reflect"], ["3", "Shared"]]},
            {"key": "scr_killcam", "label": "Killcam", "type": "bool", "default": "1"},
            {"key": "scr_drawfriend", "label": "Csapattárs ikonok", "type": "bool", "default": "1"},
            {"key": "scr_teambalance", "label": "Auto team balance", "type": "bool", "default": "0"},
            {"key": "scr_forcerespawn", "label": "Kényszerített respawn", "type": "bool", "default": "0"},
            {"key": "scr_allow_vote", "label": "In-game vote", "type": "bool", "default": "1"},
            {"key": "g_gravity", "label": "Gravitáció", "type": "int", "default": "800"},
            {"key": "g_speed", "label": "Mozgás sebesség", "type": "int", "default": "190"},
            {"key": "g_knockback", "label": "Knockback", "type": "int", "default": "1000"},
            {"key": "g_deadchat", "label": "Halott chat", "type": "bool", "default": "1"},
            {"key": "g_inactivity", "label": "Inaktivitás kick (s, 0=ki)", "type": "int", "default": "0"},
        ],
    }


_GAMEPLAY_MODERN = {
    "title": "Játékmenet",
    "fields": [
        {"key": "scr_team_fftype", "label": "Friendly fire", "type": "select", "default": "0",
         "options": [["0", "Ki"], ["1", "Be"], ["2", "Reflect"], ["3", "Shared"]]},
        {"key": "scr_game_killcam", "label": "Killcam", "type": "bool", "default": "1"},
        {"key": "scr_team_teamkillspawndelay", "label": "Teamkill spawn delay", "type": "int", "default": "20"},
        {"key": "scr_game_allowkillcam", "label": "Killcam engedélyezés", "type": "bool", "default": "1"},
        {"key": "scr_game_hardpoints", "label": "Killstreak jutalmak", "type": "bool", "default": "1"},
        {"key": "scr_game_onlyheadshots", "label": "Csak headshot", "type": "bool", "default": "0"},
        {"key": "scr_game_forceuav", "label": "Állandó UAV", "type": "bool", "default": "0"},
        {"key": "scr_game_spectatetype", "label": "Spectate", "type": "select", "default": "1",
         "options": [["0", "Tiltva"], ["1", "Csak csapattárs"], ["2", "Bárki"]]},
        {"key": "scr_team_respawntime", "label": "Respawn idő (s)", "type": "int", "default": "0"},
        {"key": "scr_player_maxhealth", "label": "Max életerő (%)", "type": "int", "default": "100"},
        {"key": "scr_player_sprinttime", "label": "Sprint idő (s)", "type": "int", "default": "4"},
        {"key": "g_deadChat", "label": "Halott chat", "type": "bool", "default": "1"},
    ],
}


GAMES: dict[str, dict[str, Any]] = {
    "cod": {
        "name": "Call of Duty",
        "short": "COD",
        "lgsm": "codserver",
        "engine": "idtech3",
        "executable": "cod_lnxded",
        "moddir": "main",
        "asset_ext": [".iwd", ".pk3"],
        "archive_url": "https://linuxgsm.download/CallOfDuty/cod-lnxded-1.5b-full.tar.xz",
        "archive_md5": "ee0ad1ccbfa1fd27fde01a4a431a5c2f",
        "archive_name": "cod-lnxded-1.5b-full.tar.xz",
        "default_port": 28960,
        "default_map": "mp_carentan",
        "default_gametype": "dm",
        "default_maxplayers": 20,
        "needs_32bit": True,
        "gametypes": [
            ["dm", "Deathmatch"], ["tdm", "Team Deathmatch"], ["sd", "Search & Destroy"],
            ["re", "Retrieval"], ["bel", "Behind Enemy Lines"], ["hq", "Headquarters"],
        ],
        "stock_maps": [
            "mp_brecourt", "mp_carentan", "mp_chateau", "mp_dawnville", "mp_depot",
            "mp_harbor", "mp_hurtgen", "mp_neuville", "mp_pavlov", "mp_powcamp",
            "mp_railyard", "mp_rocket", "mp_ship", "mp_stalingrad", "mp_tigertown",
        ],
        "limit_dvars": ["timelimit", "scorelimit", "roundlimit"],
    },
    "coduo": {
        "name": "Call of Duty: United Offensive",
        "short": "COD:UO",
        "lgsm": "coduoserver",
        "engine": "idtech3",
        "executable": "coduo_lnxded",
        "moddir": "uo",
        "asset_ext": [".iwd", ".pk3"],
        "archive_url": "https://linuxgsm.download/CallOfDutyUnitedOffensive/coduo-lnxded-1.51b-full.tar.xz",
        "archive_md5": "35cabccd67adcda44aaebc59405915b9",
        "archive_name": "coduo-lnxded-1.51b-full.tar.xz",
        "default_port": 28960,
        "default_map": "mp_cassino",
        "default_gametype": "dm",
        "default_maxplayers": 20,
        "needs_32bit": True,
        "gametypes": [
            ["dm", "Deathmatch"], ["tdm", "Team Deathmatch"], ["sd", "Search & Destroy"],
            ["re", "Retrieval"], ["bel", "Behind Enemy Lines"], ["ctf", "Capture the Flag"],
            ["dom", "Domination"], ["bas", "Base Assault"],
        ],
        "stock_maps": [
            "mp_arnhem", "mp_berlin", "mp_cassino", "mp_foy", "mp_italy", "mp_kharkov",
            "mp_kursk", "mp_ponyri", "mp_rhinevalley", "mp_sicily", "mp_uo_stanjel",
            "mp_peaks", "mp_streets", "mp_uo_carentan", "mp_uo_dawnville", "mp_uo_depot",
            "mp_uo_harbor", "mp_uo_hurtgen", "mp_uo_powcamp",
        ],
        "limit_dvars": ["timelimit", "scorelimit", "roundlimit"],
    },
    "cod2": {
        "name": "Call of Duty 2",
        "short": "COD2",
        "lgsm": "cod2server",
        "engine": "iw2.0",
        "executable": "cod2_lnxded",
        "moddir": "main",
        "asset_ext": [".iwd"],
        "archive_url": "https://linuxgsm.download/CallOfDuty2/cod2-lnxded-1.3-full.tar.xz",
        "archive_md5": "b8c4c611f01627dd43348e78478a3d41",
        "archive_name": "cod2-lnxded-1.3-full.tar.xz",
        "default_port": 28960,
        "default_map": "mp_leningrad",
        "default_gametype": "dm",
        "default_maxplayers": 20,
        "needs_32bit": True,
        "gametypes": [
            ["dm", "Deathmatch"], ["tdm", "Team Deathmatch"], ["sd", "Search & Destroy"],
            ["hq", "Headquarters"], ["ctf", "Capture the Flag"],
        ],
        "stock_maps": [
            "mp_breakout", "mp_brecourt", "mp_burgundy", "mp_carentan", "mp_dawnville",
            "mp_decoy", "mp_downtown", "mp_farmhouse", "mp_leningrad", "mp_matmata",
            "mp_railyard", "mp_toujane", "mp_trainstation", "mp_harbor", "mp_rhine",
        ],
        "limit_dvars": ["timelimit", "scorelimit", "roundlimit"],
    },
    "cod4": {
        "name": "Call of Duty 4: Modern Warfare",
        "short": "COD4",
        "lgsm": "cod4server",
        "engine": "iw3.0",
        "executable": "cod4x18_dedrun",
        "moddir": "main",
        "asset_ext": [".iwd", ".ff"],
        "archive_url": "https://linuxgsm.download/CallOfDuty4/cod4x18_lnxded.tar.xz",
        "archive_md5": "d255b59b9756d7dbead67718208512ee",
        "archive_name": "cod4x18_lnxded.tar.xz",
        "default_port": 28960,
        "default_map": "mp_backlot",
        "default_gametype": "war",
        "default_maxplayers": 32,
        "needs_32bit": True,
        "extra_params": '+set fs_homepath "{basepath}" +set sv_authorizemode "-1"',
        "gametypes": [
            ["war", "Team Deathmatch (War)"], ["dm", "Free for All"], ["dom", "Domination"],
            ["koth", "Headquarters"], ["sab", "Sabotage"], ["sd", "Search & Destroy"],
            ["ctf", "Capture the Flag (CoD4X/mod)"],
        ],
        "stock_maps": [
            "mp_backlot", "mp_bloc", "mp_bog", "mp_broadcast", "mp_carentan", "mp_cargoship",
            "mp_citystreets", "mp_convoy", "mp_countdown", "mp_crash", "mp_crash_snow",
            "mp_creek", "mp_crossfire", "mp_district", "mp_downpour", "mp_farm",
            "mp_killhouse", "mp_overgrown", "mp_pipeline", "mp_shipment", "mp_showdown",
            "mp_strike", "mp_vacant",
        ],
        "limit_dvars": ["timelimit", "scorelimit", "roundlimit"],
    },
    "codwaw": {
        "name": "Call of Duty: World at War",
        "short": "COD:WaW",
        "lgsm": "codwawserver",
        "engine": "iw3.0",
        "executable": "codwaw_lnxded",
        "moddir": "main",
        "asset_ext": [".iwd", ".ff"],
        "archive_url": "https://linuxgsm.download/CallOfDutyWorldAtWar/codwaw-lnxded-1.7-full.tar.xz",
        "archive_md5": "2c6be1bb66ea631b9b2e7ae6216c6680",
        "archive_name": "codwaw-lnxded-1.7-full.tar.xz",
        "default_port": 28960,
        "default_map": "mp_castle",
        "default_gametype": "war",
        "default_maxplayers": 32,
        "needs_32bit": True,
        "gametypes": [
            ["war", "Team Deathmatch (War)"], ["dm", "Free for All"], ["dom", "Domination"],
            ["koth", "Headquarters"], ["sab", "Sabotage"], ["sd", "Search & Destroy"],
            ["ctf", "Capture the Flag"], ["twar", "War (frontvonal)"],
        ],
        "stock_maps": [
            "mp_airfield", "mp_asylum", "mp_castle", "mp_cliffside", "mp_courtyard",
            "mp_dome", "mp_downfall", "mp_hangar", "mp_makin", "mp_makin_day",
            "mp_outskirts", "mp_roundhouse", "mp_seelow", "mp_shrine", "mp_suburban",
            "mp_drum", "mp_kneedeep", "mp_bgate", "mp_docks", "mp_kwai", "mp_subway",
            "mp_nachtfeuer", "mp_vodka", "mp_stalingrad",
        ],
        "limit_dvars": ["timelimit", "scorelimit", "roundlimit"],
    },
}

# Start parameter template shared by every supported title (LinuxGSM compatible).
START_TEMPLATE = (
    '+set sv_punkbuster 0 +set fs_basepath "{basepath}" +set dedicated 2 '
    '+set net_ip {ip} +set net_port {port} +set sv_maxclients {maxplayers}'
)


def dvar_groups(gid: str) -> list[dict[str, Any]]:
    """Form definition for the web UI: every dvar that matters, grouped."""
    g = GAMES[gid]
    modern = gid in ("cod4", "codwaw")
    groups = [_basic(f"^3{g['short']} ^7szerver"),
              _GAMEPLAY_MODERN if modern else _gameplay_ww2(),
              _NETWORK_Q3, _ADMIN]
    if modern:
        groups.append({
            "title": "CoD4/WaW extrák",
            "fields": [
                {"key": "sv_disableClientConsole", "label": "Kliens konzol tiltása", "type": "bool", "default": "0"},
                {"key": "sv_kickBanTime", "label": "Kick ban idő (s)", "type": "int", "default": "300"},
                {"key": "sv_voice", "label": "Voice chat", "type": "bool", "default": "0"},
                {"key": "scr_game_graceperiod", "label": "Grace period (s)", "type": "int", "default": "15"},
                {"key": "scr_intermission_time", "label": "Intermission (s)", "type": "int", "default": "15"},
            ],
        })
    return groups


def default_dvars(gid: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for group in dvar_groups(gid):
        for f in group["fields"]:
            if f.get("default") != "":
                out[f["key"]] = str(f.get("default", ""))
    return out


def catalog() -> list[dict[str, Any]]:
    items = []
    for gid, g in GAMES.items():
        items.append({
            "id": gid,
            "name": g["name"],
            "short": g["short"],
            "lgsm": g["lgsm"],
            "engine": g["engine"],
            "executable": g["executable"],
            "moddir": g["moddir"],
            "default_port": g["default_port"],
            "default_map": g["default_map"],
            "default_gametype": g["default_gametype"],
            "default_maxplayers": g["default_maxplayers"],
            "gametypes": g["gametypes"],
            "stock_maps": g["stock_maps"],
            "asset_ext": g["asset_ext"],
            "archive_url": g["archive_url"],
        })
    return items
