"""Catalog of supported Call of Duty dedicated servers.

Binaries, start parameters, archive URLs and MD5 sums match the LinuxGSM
defaults (codserver / cod2server / coduoserver / cod4server / codwawserver),
so a panel install behaves like a LinuxGSM install without the CLI.
"""
from __future__ import annotations

from typing import Any

# --- reusable dvar form groups -------------------------------------------------
# Minden mező: key (dvar), label, type, default, desc (mit csinál), help (extra tipp).

def _basic(default_hostname: str) -> dict[str, Any]:
    return {
        "title": "Alapok",
        "fields": [
            {"key": "sv_hostname", "label": "Szerver neve", "type": "text",
             "default": default_hostname,
             "desc": "Ez a név jelenik meg a szerverböngészőben a játékosoknál.",
             "help": "Színkódok: ^1 piros, ^2 zöld, ^3 sárga, ^4 kék, ^7 fehér."},
            {"key": "rcon_password", "label": "RCON jelszó", "type": "password", "default": "",
             "desc": "Távoli adminisztráció jelszava: ezzel lehet a játékból vagy külső "
                     "eszközből parancsot küldeni a szervernek. Üresen / kikapcsolva nincs RCON."},
            {"key": "g_password", "label": "Belépési jelszó", "type": "password", "default": "",
             "desc": "Ha be van kapcsolva és van értéke, csak az tud csatlakozni, aki tudja "
                     "a jelszót (privát szerver)."},
            {"key": "sv_privateClients", "label": "Privát slotok", "type": "int", "default": "0",
             "desc": "Ennyi hely van fenntartva azoknak, akik ismerik a privát jelszót. "
                     "A maradék slot a nyilvános játékosoké."},
            {"key": "sv_privatePassword", "label": "Privát slot jelszó", "type": "password", "default": "",
             "desc": "A fenntartott (privát) slotok jelszava — ezzel akkor is be lehet lépni, "
                     "ha a szerver tele van."},
            {"key": "sv_maxPing", "label": "Max ping", "type": "int", "default": "0",
             "desc": "Ennél nagyobb pingű játékost nem enged be a szerver. 0 = nincs korlát."},
            {"key": "sv_minPing", "label": "Min ping", "type": "int", "default": "0",
             "desc": "Ennél kisebb pingű játékost nem enged be (ritkán használt). Általában 0."},
        ],
    }


_NETWORK_Q3 = {
    "title": "Hálózat és letöltés",
    "fields": [
        {"key": "sv_maxRate", "label": "Max sávszélesség", "type": "int", "default": "25000",
         "desc": "Játékosonkénti maximális adatforgalom bájt/mp-ben. Alap: 25000. "
                 "Alacsonyabb érték spórol a sávszélességgel, de akadozást okozhat."},
        {"key": "sv_floodProtect", "label": "Flood védelem", "type": "bool", "default": "1",
         "desc": "Megakadályozza, hogy valaki chat- vagy parancsözönnel terhelje a szervert."},
        {"key": "sv_timeout", "label": "Timeout", "type": "int", "default": "240",
         "desc": "Hány másodpercig vár a szerver egy válaszolni nem tudó játékosra, "
                 "mielőtt kidobja."},
        {"key": "sv_reconnectlimit", "label": "Reconnect korlát", "type": "int", "default": "3",
         "desc": "Ennyi másodpercig nem csatlakozhat vissza ugyanaz a kliens kilépés után."},
        {"key": "sv_pure", "label": "Fájl ellenőrzés (sv_pure)", "type": "bool", "default": "1",
         "desc": "Ellenőrzi, hogy a játékos fájljai megegyeznek-e a szerveréivel. Kiszűri a "
                 "módosított fájlokat, de saját kliensoldali tartalomnál néha ki kell kapcsolni."},
        {"key": "sv_allowDownload", "label": "Beépített letöltés", "type": "bool", "default": "1",
         "desc": "A hiányzó mapokat/modokat a játékos közvetlenül a szerverről töltheti le. "
                 "Működik, de lassú és terheli a szervert."},
        {"key": "sv_wwwDownload", "label": "HTTP (fast) letöltés", "type": "bool", "default": "0",
         "desc": "A hiányzó fájlokat a játékos egy webszerverről tölti le — sokkal gyorsabb, "
                 "mint a beépített letöltés. Kell hozzá a lenti URL."},
        {"key": "sv_wwwBaseURL", "label": "HTTP letöltés URL", "type": "text", "default": "",
         "desc": "Annak a webszervernek a címe, ahol a map fájlok (.iwd) elérhetők.",
         "help": "Pl. http://1.2.3.4/cod2 — a mod könyvtár szerkezetét kell tükröznie."},
        {"key": "sv_wwwDlDisconnected", "label": "Letöltés lecsatlakozva", "type": "bool", "default": "0",
         "desc": "A játékos a letöltés idejére lelép a szerverről, és utána lép vissza. "
                 "Nem foglal slotot letöltés közben."},
    ],
}

_ADMIN = {
    "title": "Admin, szavazás és naplózás",
    "fields": [
        {"key": "g_allowVote", "label": "Szavazás engedélyezése", "type": "bool", "default": "1",
         "desc": "A játékosok szavazással kezdeményezhetnek map- vagy beállításváltást."},
        {"key": "g_log", "label": "Játék log fájl", "type": "text", "default": "games_mp.log",
         "desc": "A játékmenet naplója (ölések, chat, csatlakozások). A statisztika-rendszerek "
                 "(pl. B3, HLstatsX) ezt a fájlt olvassák."},
        {"key": "g_logSync", "label": "Log azonnali írása", "type": "bool", "default": "1",
         "desc": "A naplósorok azonnal lemezre kerülnek pufferelés nélkül. Élő statisztikához kell."},
        {"key": "logfile", "label": "Konzol log szint", "type": "select", "default": "2",
         "options": [["0", "Nincs"], ["1", "Pufferelt"], ["2", "Folyamatos"], ["3", "Részletes"]],
         "desc": "Mennyit írjon ki a szerver a konzol naplójába. A panel konzolja ettől "
                 "függetlenül mindig mutatja a kimenetet."},
        {"key": "sv_punkbuster", "label": "PunkBuster anticheat", "type": "bool", "default": "0",
         "desc": "A régi PunkBuster anticheat. A legtöbb COD szerveren ki van kapcsolva, "
                 "mert a szolgáltatás már nem működik."},
    ],
}


def _gameplay_ww2() -> dict[str, Any]:
    return {
        "title": "Játékmenet",
        "fields": [
            {"key": "scr_friendlyfire", "label": "Csapattárs sebzése", "type": "select", "default": "0",
             "options": [["0", "Ki"], ["1", "Be"], ["2", "Reflect"], ["3", "Shared"]],
             "desc": "Lehet-e sebezni a saját csapattársat. Reflect = a sebzés visszaszáll a lövőre, "
                     "Shared = mindkettő sérül."},
            {"key": "scr_killcam", "label": "Killcam", "type": "bool", "default": "1",
             "desc": "Halál után visszajátssza, ki és honnan ölte meg a játékost."},
            {"key": "scr_drawfriend", "label": "Csapattárs ikonok", "type": "bool", "default": "1",
             "desc": "Látszik-e név/ikon a csapattársak feje fölött a pályán."},
            {"key": "scr_teambalance", "label": "Automatikus csapatkiegyenlítés", "type": "bool", "default": "0",
             "desc": "A szerver automatikusan átrak játékosokat, ha az egyik csapat létszáma "
                     "jóval nagyobb."},
            {"key": "scr_forcerespawn", "label": "Kényszerített újraéledés", "type": "bool", "default": "0",
             "desc": "A játékos automatikusan újraéled, nem kell gombot nyomnia hozzá."},
            {"key": "scr_allow_vote", "label": "Szavazás a játékban", "type": "bool", "default": "1",
             "desc": "A játékon belüli szavazó menü (map váltás, kick) engedélyezése."},
            {"key": "g_gravity", "label": "Gravitáció", "type": "int", "default": "800",
             "desc": "Mennyire húz lefelé a gravitáció. Alap: 800. Kisebb érték = holdbéli, "
                     "magas ugrások."},
            {"key": "g_speed", "label": "Mozgási sebesség", "type": "int", "default": "190",
             "desc": "A játékos alap mozgási sebessége. Alap: 190. Nagyobb érték = gyorsabb játék."},
            {"key": "g_knockback", "label": "Visszalökés", "type": "int", "default": "1000",
             "desc": "Mennyire lökik hátra a játékost a találatok. Alap: 1000."},
            {"key": "g_deadchat", "label": "Halottak chatje", "type": "bool", "default": "1",
             "desc": "A már kiesett játékosok üzenetét látják-e az élők."},
            {"key": "g_inactivity", "label": "Tétlenség miatti kirúgás", "type": "int", "default": "0",
             "desc": "Ennyi másodperc mozdulatlanság után kirúgja a játékost. 0 = kikapcsolva."},
        ],
    }


_GAMEPLAY_MODERN = {
    "title": "Játékmenet",
    "fields": [
        {"key": "scr_team_fftype", "label": "Csapattárs sebzése", "type": "select", "default": "0",
         "options": [["0", "Ki"], ["1", "Be"], ["2", "Reflect"], ["3", "Shared"]],
         "desc": "Lehet-e sebezni a saját csapattársat. Reflect = a sebzés visszaszáll a lövőre, "
                 "Shared = mindkettő sérül."},
        {"key": "scr_game_allowkillcam", "label": "Killcam", "type": "bool", "default": "1",
         "desc": "Halál után visszajátssza, ki és honnan ölte meg a játékost."},
        {"key": "scr_team_teamkillspawndelay", "label": "Teamkill büntetés", "type": "int", "default": "20",
         "desc": "Hány másodperc extra várakozás jár az újraéledésig, ha valaki csapattársat öl."},
        {"key": "scr_game_hardpoints", "label": "Killstreak jutalmak", "type": "bool", "default": "1",
         "desc": "UAV, légicsapás és helikopter (killstreak jutalmak) engedélyezése."},
        {"key": "scr_game_onlyheadshots", "label": "Csak fejlövés", "type": "bool", "default": "0",
         "desc": "Csak fejlövéssel lehet ölni — snipe/hardcore jellegű szerverekhez."},
        {"key": "scr_game_forceuav", "label": "Állandó UAV", "type": "bool", "default": "0",
         "desc": "Mindenki folyamatosan látja az ellenfeleket a radaron."},
        {"key": "scr_game_spectatetype", "label": "Megfigyelés (spectate)", "type": "select", "default": "1",
         "options": [["0", "Tiltva"], ["1", "Csak csapattárs"], ["2", "Bárki"]],
         "desc": "Kit nézhet a halott vagy megfigyelő játékos."},
        {"key": "scr_team_respawntime", "label": "Újraéledési idő", "type": "int", "default": "0",
         "desc": "Fix várakozás másodpercben az újraéledés előtt. 0 = a játékmód alapértelmezése."},
        {"key": "scr_player_maxhealth", "label": "Életerő", "type": "int", "default": "100",
         "desc": "Életerő százalékban. 100 = alap, 30 körüli érték = hardcore mód."},
        {"key": "scr_player_sprinttime", "label": "Sprint idő", "type": "int", "default": "4",
         "desc": "Hány másodpercig lehet egyhuzamban sprintelni."},
        {"key": "g_deadChat", "label": "Halottak chatje", "type": "bool", "default": "1",
         "desc": "A már kiesett játékosok üzenetét látják-e az élők."},
    ],
}

_MODERN_EXTRA = {
    "title": "CoD4 / WaW extrák",
    "fields": [
        {"key": "sv_disableClientConsole", "label": "Kliens konzol tiltása", "type": "bool", "default": "0",
         "desc": "Letiltja a játékosok saját konzolját, így nem tudnak parancsokat beírni."},
        {"key": "sv_kickBanTime", "label": "Kick utáni tiltás", "type": "int", "default": "300",
         "desc": "Kirúgás után ennyi másodpercig nem csatlakozhat vissza a játékos."},
        {"key": "sv_voice", "label": "Hangchat (voice)", "type": "bool", "default": "0",
         "desc": "Beszélhetnek-e a játékosok mikrofonon keresztül a szerveren."},
        {"key": "scr_game_graceperiod", "label": "Felkészülési idő", "type": "int", "default": "15",
         "desc": "A kör elején ennyi másodpercig nem lehet lőni (felkészülés, csapatválasztás)."},
        {"key": "scr_intermission_time", "label": "Körök közti szünet", "type": "int", "default": "15",
         "desc": "Map vége és a következő kezdete közti eredményhirdetés hossza másodpercben."},
    ],
}

# A játékmód (g_gametype) külön kezelt mező: indítási paraméter és cfg sor is lesz belőle.
GAMETYPE_DESC = ("A játékmód, amiben a szerver indul (pl. tdm = csapat deathmatch). "
                 "Kikapcsolva a panel nem írja elő — a mod vagy a saját cfg dönti el.")

LIMIT_DESC = {
    "timelimit": "A map maximális hossza percben. 0 = nincs időkorlát.",
    "scorelimit": "Ennyi pont elérésekor véget ér a map. 0 = nincs pontkorlát.",
    "roundlimit": "Ennyi megnyert kör után ér véget a mérkőzés (kör alapú módoknál). 0 = nincs korlát.",
}


GAMES: dict[str, dict[str, Any]] = {
    "cod": {
        "legacy_libs": ["libstdc++.so.5"],
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
        "legacy_libs": ["libstdc++.so.5"],
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
        "legacy_libs": ["libstdc++.so.5"],
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
            "mp_creek", "mp_crossfire", "mp_farm", "mp_killhouse", "mp_overgrown",
            "mp_pipeline", "mp_shipment", "mp_showdown", "mp_strike", "mp_vacant",
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
    "mw2": {
        "legacy_libs": [],
        "name": "Call of Duty: Modern Warfare 2 (IW4x)",
        "short": "MW2",
        "lgsm": None,
        "engine": "iw4.0",
        "executable": "iw4x.exe",
        "wine": True,            # Windows bináris, Wine-nal fut
        "install_mode": "manual",  # a játékfájlokat a felhasználó hozza (saját MW2 + IW4x)
        "moddir": "userraw",
        "map_dirs": ["zone/english", "zone", "usermaps"],
        "asset_ext": [".iwd", ".ff"],
        "archive_url": "",
        "archive_md5": "",
        "archive_name": "",
        "default_port": 28960,
        "default_map": "mp_rust",
        "default_gametype": "war",
        "default_maxplayers": 18,
        "needs_32bit": False,
        # az IW4x Windows bináris: nincs fs_basepath/dedicated 2, a -dedicated kapcsoló
        # indítja fejnélküli módban, a -stdout pedig a panel konzoljára írat
        "start_template": ("-dedicated -stdout +set net_port {port} "
                           "+set sv_maxclients {maxplayers} +set party_enable 0"),
        "gametypes": [
            ["war", "Team Deathmatch"], ["dm", "Free for All"], ["dom", "Domination"],
            ["dd", "Demolition"], ["sab", "Sabotage"], ["sd", "Search & Destroy"],
            ["koth", "Headquarters"], ["ctf", "Capture the Flag"],
            ["oneflag", "One Flag CTF"], ["gtnw", "Global Thermonuclear War"],
        ],
        "stock_maps": [
            "mp_afghan", "mp_boneyard", "mp_brecourt", "mp_checkpoint", "mp_derail",
            "mp_estate", "mp_favela", "mp_highrise", "mp_invasion", "mp_nightshift",
            "mp_quarry", "mp_rundown", "mp_rust", "mp_subbase", "mp_terminal",
            "mp_underpass", "mp_complex", "mp_compact", "mp_storm", "mp_abandon",
            "mp_fuel2", "mp_strike", "mp_trailerpark", "mp_vacant", "mp_crash",
            "mp_overgrown",
        ],
        "limit_dvars": ["timelimit", "scorelimit", "roundlimit"],
    },
}

# Start parameter template shared by every supported title (LinuxGSM compatible).
START_TEMPLATE = (
    '+set sv_punkbuster 0 +set fs_basepath "{basepath}" +set dedicated 2 '
    '+set net_ip {ip} +set net_port {port} +set sv_maxclients {maxplayers}'
)



# Emberi nevek a map fájlnevekhez - a kódnevekből nem lehet rájuk ismerni.
MAP_NAMES: dict[str, dict[str, str]] = {
    "cod": {
        "mp_brecourt": "Brecourt", "mp_carentan": "Carentan", "mp_chateau": "Chateau",
        "mp_dawnville": "Ste. Mère-Église", "mp_depot": "Depot", "mp_harbor": "Harbor",
        "mp_hurtgen": "Hurtgen", "mp_neuville": "Neuville", "mp_pavlov": "Pavlov",
        "mp_powcamp": "POW Camp", "mp_railyard": "Railyard", "mp_rocket": "Rocket",
        "mp_ship": "Ship", "mp_stalingrad": "Stalingrad", "mp_tigertown": "Tigertown",
    },
    "coduo": {
        "mp_arnhem": "Arnhem", "mp_berlin": "Berlin", "mp_cassino": "Cassino",
        "mp_foy": "Foy", "mp_italy": "Italy", "mp_kharkov": "Kharkov",
        "mp_kursk": "Kursk", "mp_ponyri": "Ponyri", "mp_rhinevalley": "Rhine Valley",
        "mp_sicily": "Sicily", "mp_uo_stanjel": "Stanjel", "mp_peaks": "Peaks",
        "mp_streets": "Streets", "mp_uo_carentan": "Carentan",
        "mp_uo_dawnville": "Ste. Mère-Église", "mp_uo_depot": "Depot",
        "mp_uo_harbor": "Harbor", "mp_uo_hurtgen": "Hurtgen", "mp_uo_powcamp": "POW Camp",
    },
    "cod2": {
        "mp_breakout": "Villers-Bocage", "mp_brecourt": "Brecourt", "mp_burgundy": "Burgundy",
        "mp_carentan": "Carentan", "mp_dawnville": "St. Mere Eglise", "mp_decoy": "El Alamein",
        "mp_downtown": "Moscow", "mp_farmhouse": "Beltot", "mp_leningrad": "Leningrad",
        "mp_matmata": "Matmata", "mp_railyard": "Stalingrad", "mp_toujane": "Toujane",
        "mp_trainstation": "Caen", "mp_harbor": "Rostov", "mp_rhine": "Wallendar",
    },
    "cod4": {
        "mp_backlot": "Backlot", "mp_bloc": "Bloc", "mp_bog": "Bog",
        "mp_broadcast": "Broadcast", "mp_carentan": "Chinatown", "mp_cargoship": "Wet Work",
        "mp_citystreets": "District", "mp_convoy": "Ambush", "mp_countdown": "Countdown",
        "mp_crash": "Crash", "mp_crash_snow": "Winter Crash", "mp_creek": "Creek",
        "mp_crossfire": "Crossfire", "mp_farm": "Downpour", "mp_killhouse": "Killhouse",
        "mp_overgrown": "Overgrown", "mp_pipeline": "Pipeline", "mp_shipment": "Shipment",
        "mp_showdown": "Showdown", "mp_strike": "Strike", "mp_vacant": "Vacant",
    },
    "codwaw": {
        "mp_airfield": "Airfield", "mp_asylum": "Asylum", "mp_castle": "Castle",
        "mp_cliffside": "Cliffside", "mp_courtyard": "Courtyard", "mp_dome": "Dome",
        "mp_downfall": "Downfall", "mp_hangar": "Hangar", "mp_makin": "Makin",
        "mp_makin_day": "Makin Day", "mp_outskirts": "Outskirts",
        "mp_roundhouse": "Roundhouse", "mp_seelow": "Seelow", "mp_suburban": "Upheaval",
        "mp_drum": "Banzai", "mp_kneedeep": "Knee Deep", "mp_bgate": "Breach",
        "mp_docks": "Sub Pens", "mp_subway": "Station", "mp_nachtfeuer": "Nightfire",
        "mp_vodka": "Corrosion",
    },
    "mw2": {
        "mp_afghan": "Afghan", "mp_boneyard": "Scrapyard", "mp_brecourt": "Wasteland",
        "mp_checkpoint": "Karachi", "mp_derail": "Derail", "mp_estate": "Estate",
        "mp_favela": "Favela", "mp_highrise": "Highrise", "mp_invasion": "Invasion",
        "mp_nightshift": "Skidrow", "mp_quarry": "Quarry", "mp_rundown": "Rundown",
        "mp_rust": "Rust", "mp_subbase": "Sub Base", "mp_terminal": "Terminal",
        "mp_underpass": "Underpass", "mp_complex": "Bailout", "mp_compact": "Salvage",
        "mp_storm": "Storm", "mp_abandon": "Carnival", "mp_fuel2": "Fuel",
        "mp_strike": "Strike", "mp_trailerpark": "Trailer Park", "mp_vacant": "Vacant",
        "mp_crash": "Crash", "mp_overgrown": "Overgrown",
    },
}


def map_label(gid: str, mapname: str) -> str:
    """Emberi név, ha ismerjük; különben a kódnévből csinálunk olvashatót."""
    known = MAP_NAMES.get(gid, {}).get(mapname)
    if known:
        return known
    base = mapname[3:] if mapname.startswith("mp_") else mapname
    return base.replace("_", " ").strip().title() or mapname


def dvar_groups(gid: str) -> list[dict[str, Any]]:
    """Form definition for the web UI: every dvar that matters, grouped."""
    g = GAMES[gid]
    modern = gid in ("cod4", "codwaw")
    groups = [_basic(f"^3{g['short']} ^7szerver"),
              _GAMEPLAY_MODERN if modern else _gameplay_ww2(),
              _NETWORK_Q3, _ADMIN]
    if modern:
        groups.append(_MODERN_EXTRA)
    return groups


def default_dvars(gid: str) -> dict[str, str]:
    """Starting values for a new instance (empty optional fields included)."""
    out: dict[str, str] = {}
    for group in dvar_groups(gid):
        for f in group["fields"]:
            out[f["key"]] = str(f.get("default", ""))
    return out


def default_disabled(gid: str) -> list[str]:
    """Dvars that start switched OFF: the optional ones with no default value.

    Everything with a sensible default (sv_hostname, g_gametype, ...) starts ON
    and can be switched off one by one in the web UI.
    """
    off: list[str] = []
    for group in dvar_groups(gid):
        for f in group["fields"]:
            if str(f.get("default", "")) == "":
                off.append(f["key"])
    return off


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
            "map_names": {m: map_label(gid, m) for m in g["stock_maps"]},
            "install_mode": g.get("install_mode", "download"),
            "wine": bool(g.get("wine")),
            "asset_ext": g["asset_ext"],
            "archive_url": g["archive_url"],
        })
    return items
