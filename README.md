# COD Panel

Webes admin felület Call of Duty dedikált szerverekhez — LinuxGSM-kompatibilis binárisok és
indítási paraméterek, de **CLI helyett böngészőből** kezelhetően. Proxmox LXC konténerre szabva.

![status](https://img.shields.io/badge/python-3.9%2B-blue) ![license](https://img.shields.io/badge/license-MIT-green)

## Mit tud

| | |
|---|---|
| **6 játék** | Call of Duty, CoD: United Offensive, Call of Duty 2, Call of Duty 4 (CoD4X), CoD: World at War, Modern Warfare 2 (IW4x) |
| **Több szerver** | Egy panelből korlátlan számú példány, mindegyiknek saját port, cfg, log, konzol |
| **Egy kattintásos játékfájl-telepítés** | A LinuxGSM tükrökről, MD5 ellenőrzéssel |
| **Egy kattintásos custom map** | URL-ről letöltve vagy fájlból feltöltve (.iwd / .pk3 / .ff / .zip), utána azonnal kiválasztható |
| **Képes map választó** | a map loadscreenje a saját játékfájljaidból, emberi névvel (mp_checkpoint → Karachi) |
| **Minden beállítás űrlapon** | gamemode, map, slotok, friendly fire, killcam, limitek, rcon, fast download, sv_pure, gravitáció… |
| **Dvar-onkénti be/ki kapcsoló** | minden beállítás külön kikapcsolható (akkor ki sem kerül a cfg-be), és mindegyik alatt ott a magyar nyelvű magyarázat, hogy mit csinál |
| **Map rotáció szerkesztő** | sorrend, játékmód maponként, `sv_mapRotation` generálás |
| **Élő konzol** | WebSocket, közvetlen stdin + RCON, játékoslista, kick, azonnali map váltás |
| **AI vezérlés (MCP)** | MCP szerver 19 eszközzel: map váltás, szerver indítás/létrehozás, rotáció, konzol a hibakereséshez |
| **Felügyelet** | automatikus indítás boot-kor, automatikus újraindítás összeomlás után, RAM/uptime/játékosszám |

A panel ugyanazokat a binárisokat és indítási paramétereket használja, mint a LinuxGSM
`codserver` / `coduoserver` / `cod2server` / `cod4server` / `codwawserver` scriptek,
így a meglévő tudás és a community cfg-k változtatás nélkül működnek.

## Map előnézeti képek

A map kódnevekből (`mp_nightshift`, `mp_checkpoint`) nehéz felismerni a pályát, ezért a panel
kétféleképpen segít:

- **Emberi nevek**: minden alap maphoz ott a rendes neve (`mp_checkpoint` → *Karachi*,
  `mp_breakout` → *Villers-Bocage*), ismeretlen mapnál a kódnévből képez olvashatót.
- **Bélyegképek**: a panel a játék `.iwd` csomagjaiból kiszedi a map `loadscreen_<map>.iwi`
  textúráját, dekódolja (DXT1/3/5, külső könyvtár nélkül) és PNG bélyegképet készít belőle.
  A képek tehát a **saját telepítésedből** származnak, a panel nem tölt le képet sehonnan.

A map választó innentől egy rácsos, kereshető ablak képekkel — a Beállítások *Induló map*
mezőjénél, a rotáció szerkesztőben és az azonnali map váltásnál is.

Ha egy maphoz nincs kép (pl. a CoD4/WaW/MW2 egyes textúrái `.ff` fastfile-ban vannak, amit nem
bontunk ki), a Map kezelőben a kártya sarkában lévő **kép** gombbal tölthetsz fel sajátot vagy
adhatsz meg kép-URL-t.

## Telepítés

### A) Proxmox host-ról, egy lépésben (konténer létrehozásával)

A **Proxmox host shelljében**:

```bash
rm -rf /tmp/cod-panel && git clone --depth 1 https://github.com/miatoszs/cod-panel /tmp/cod-panel
bash /tmp/cod-panel/proxmox-lxc.sh --ctid 150 --hostname codpanel --disk 40 --ram 4096 --cores 4
```

Újrafuttatható: a `rm -rf` miatt a második próbálkozás sem akad el azon, hogy a
`/tmp/cod-panel` már létezik.

Létrehoz egy unprivileged Debian LXC-t (a pveam katalógus legfrissebb Debian 13, ennek
hiányában Debian 12 standard template-jéből — `--template` kapcsolóval felülírható),
feltelepíti a panelt, és kiírja a web felület címét + a generált admin jelszót.

### B) Meglévő LXC konténerben / VM-ben

A **konténeren belül, root-ként**:

```bash
apt update && apt install -y git
rm -rf /opt/cod-panel-src && git clone --depth 1 https://github.com/miatoszs/cod-panel /opt/cod-panel-src
bash /opt/cod-panel-src/install.sh
```

Opciók: `--port 8080`, `--admin admin`, `--password sajatjelszo`, `--prefix /opt/codpanel`.

A telepítő elintézi:
- 32 bites futtatókörnyezet (`lib32gcc-s1`, `lib32stdc++6`) — a COD szerverek 32 bites binárisok,
- `codpanel` rendszerfelhasználó, Python venv, függőségek,
- systemd service (`codpanel`), automatikus indítással,
- admin felhasználó (jelszó generálva, ha nem adod meg).

### Modern Warfare 2 (IW4x) — eltérő telepítés

Az MW2-höz **nincs hivatalos dedikált szerver** és nincs letölthető szerverfájl-csomag sem:
az Activision annak idején IWNet-es matchmakinggel adta ki. Dedikált szervert a közösségi
[IW4x](https://docs.iw4x.io/hosting/server-hosting/) projekttel lehet üzemeltetni, amihez:

1. a **saját, Steames MW2 telepítésed** fájljai kellenek (a Microsoft Store-os változat nem jó),
2. az IW4x fájljai (`iw4x.dll`, `iw4x-launcher`, `userraw/`, `zone/`), és
3. mivel ez Windows bináris: **wine** a konténerben (`apt install -y wine`).

A fájlokat ide kell másolni: `<data>/serverfiles/mw2/`, úgy hogy az `iw4x.exe` a gyökerében legyen.
A panel innentől ugyanúgy kezeli, mint a többit (indítás, konzol, cfg, rotáció, mapok) —
a szervert `wine iw4x.exe -dedicated -stdout +set net_port ... +exec <id>.cfg` paranccsal indítja,
a cfg a `userraw/` könyvtárba kerül. A panel kb. 12 GB helyet kér ehhez (az IW4x Shrink
eszközzel 7-8 GB-ra csökkenthető).

### C) Fejlesztéshez / kipróbáláshoz (bármilyen Linuxon)

```bash
./run.sh          # venv létrehozás + indítás: http://localhost:8080
```

Első belépésnél a panel megkér, hogy adj meg admin felhasználót és jelszót.

### Elfelejtett admin jelszó

A telepítő a végén kiírja az admin nevet és a generált jelszót. Ha elveszett,
állíts be újat (a panelt is újraindítja):

```bash
# a konténerben
bash /opt/codpanel/app/reset-password.sh admin UjJelszo123

# vagy a Proxmox hostról, jelszó nélkül -> generál egyet és kiírja
pct exec 150 -- bash /opt/codpanel/app/reset-password.sh
```

## Frissítés

Ugyanaz a parancs, mint a telepítés — az adatok (szerverek, mapok, admin jelszó)
megmaradnak, a service pedig újraindul az új kóddal:

```bash
# a konténerben
rm -rf /tmp/cp && git clone --depth 1 https://github.com/miatoszs/cod-panel /tmp/cp && bash /tmp/cp/install.sh

# vagy a Proxmox hostról
pct exec 150 -- bash -lc 'rm -rf /tmp/cp && git clone -q --depth 1 https://github.com/miatoszs/cod-panel /tmp/cp && bash /tmp/cp/install.sh'
```

A böngésződnek nem kell cache-t ürítened: a panel verziószámmal hivatkozik a
saját JS/CSS fájljaira, így frissítés után automatikusan az újat tölti be.

## Használat

1. **Játékfájlok** fül → a kívánt COD verziónál *Szerverfájlok telepítése*
   (letöltés + MD5 ellenőrzés + kibontás, folyamatjelzővel). A csomagok nagyok,
   a CoD2 például 3,6 GB.
2. **Szerverek → Új szerver** → játék, név, port, slotok, játékmód, induló map, mod.
3. A szerver lapon:
   - **Beállítások** — minden dvar űrlapon, egyenként kapcsolható (a „Egyéni dvar-ok” mezőbe bármilyen extra cfg sor mehet),
   - **Map rotáció** — sorrend + játékmód maponként,
   - **Mapok** — custom tartalom telepítése,
   - **Konzol** — élő kimenet, parancsküldés (konzol vagy RCON),
   - **cfg / parancs** — a generált `<id>.cfg` és a teljes indítási parancs.
4. **Indítás** gomb. Minden mentés újraírja a cfg-t; az „Mentés + újraindítás” azonnal alkalmazza.

### Beállítások be- és kikapcsolása

Minden beállítás egy önálló blokk: a neve, mellette a valódi dvar neve (pl. `sv_hostname`),
egy **aktív / kikapcsolva** kapcsoló, és alatta egy mondatban, hogy pontosan mit csinál.

- **Aktív** (alapértelmezett a legtöbb beállításnál, köztük a `sv_hostname` és a `g_gametype`):
  a panel beleírja a generált cfg-be.
- **Kikapcsolva**: a sor egyáltalán nem kerül a cfg-be, így a mod, a saját cfg sorok vagy a
  játék alapértéke dönt. A `g_gametype` kikapcsolva az indítási parancsból is kimarad.

Alapból azok a mezők vannak kikapcsolva, amelyeknek nincs értelmes alapértékük
(jelszavak, HTTP letöltési URL) — ezeket egy kattintással lehet bekapcsolni.

### Custom map egy kattintással

A **Map kezelő** fülön illeszd be a letöltési linket (pl. egy `mp_valami.zip` a CoD2 community
oldalakról), majd *Letöltés és telepítés*. A panel:

- `.iwd` / `.pk3` → a mod könyvtárba (CoD1/UO/CoD2),
- `.ff` / `mp_*.iwd` → `usermaps/<mapnév>/` (CoD4/WaW),
- `.zip` → kibontja; ha `usermaps/`, `main/`, `mods/` szerkezetet talál, megtartja,
- kiolvassa a csomagban lévő `maps/mp/*.bsp` bejegyzéseket, így a **mapnév azonnal megjelenik**
  a map és rotáció választókban (★ jelöli a custom mapokat).

Fontos: hogy a játékosok is letöltsék a mapot, kapcsold be a *Hálózat és letöltés* alatt a
`sv_allowDownload`-ot, nagy forgalomhoz pedig a `sv_wwwDownload` + `sv_wwwBaseURL` (HTTP fast download) párost.

## Régi 32 bites könyvtárak (libstdc++.so.5)

A CoD, CoD2 és CoD:UO dedikált szerverek 2004-2006-os, 32 bites binárisok, amelyek a
GCC 3-as C++ runtime-ot (`libstdc++.so.5`) kérik. Ez Debian 10 óta nincs a tárolókban,
hiánya esetén a szerver **127-es kóddal, azonnal kilép**:

```
error while loading shared libraries: libstdc++.so.5: cannot open shared object file
```

A panel ezt magától kezeli: telepítéskor (és a Játékfájlok oldalon egy gombbal)
kiszedi a könyvtárat a Debian archívumának `libstdc++5:i386` csomagjából
(SHA256-tal ellenőrizve), és a saját `data/lib32` könyvtárába teszi. A szerverek
`LD_LIBRARY_PATH`-ába ez bekerül, a rendszerhez tehát nem kell hozzányúlni.

## AI vezérlés (MCP)

A panelhez tartozik egy **MCP szerver**, amivel AI kliensből (Claude Code, Claude Desktop stb.)
lehet vezérelni a szervereket: „váltsd a cod2 szervert Toujane-ra", „hozz létre egy új
Search & Destroy szervert", „miért nem indul el a szerver?".

### 1. Token készítése

A panelen: **Beállítások → AI vezérlés → Token készítése**. A token csak egyszer látható,
és a panel ki is írja hozzá a kész beállítás-blokkot.

### 2. A kliens beállítása

Az MCP szerver HTTP-n beszél a panellel, ezért futhat a konténerben vagy a saját gépeden is
(ilyenkor a `CODPANEL_URL` a konténer címe legyen).

```json
{
  "mcpServers": {
    "codpanel": {
      "command": "/opt/codpanel/venv/bin/python",
      "args": ["-m", "panel.mcp_server"],
      "env": {
        "PYTHONPATH": "/opt/codpanel/app",
        "CODPANEL_URL": "http://10.0.0.50:8080",
        "CODPANEL_TOKEN": "codp_..."
      }
    }
  }
}
```

A saját gépeden egy paranccsal beállítható (a tokent rejtve kéri be, és
ellenőrzi a panel elérhetőségét is):

```bash
git clone https://github.com/miatoszs/cod-panel ~/cod-panel
bash ~/cod-panel/setup-mcp.sh --url http://<panel-ip>:8080
```

A script létrehozza a venv-et, felteszi az MCP SDK-t, próbát futtat, majd beírja a
Claude kliens konfigjába (a meglévő MCP szerverek megmaradnak, és biztonsági másolat
készül). `--target project` a projekt `.mcp.json`-ját írja, `--target print` csak kiírja
a blokkot.

Claude Code CLI-ben egy paranccsal:

```bash
claude mcp add codpanel --env PYTHONPATH=/opt/codpanel/app \
  --env CODPANEL_URL=http://10.0.0.50:8080 --env CODPANEL_TOKEN=codp_... \
  -- /opt/codpanel/venv/bin/python -m panel.mcp_server
```

Hálózati (stdio helyett HTTP) módhoz: `CODPANEL_MCP_TRANSPORT=streamable-http`,
`CODPANEL_MCP_HOST=0.0.0.0`, `CODPANEL_MCP_PORT=8765`.

### Eszközök

| Terület | Eszközök |
|---|---|
| Áttekintés, hibakeresés | `list_servers`, `server_details`, `console`, `system_status`, `panel_events` |
| Vezérlés | `start_server`, `stop_server`, `restart_server`, `change_map`, `send_command` |
| Beállítás | `create_server`, `update_server`, `set_rotation`, `delete_server` |
| Tartalom | `list_games`, `list_maps`, `install_game`, `install_custom_map`, `install_missing_libs` |

A `change_map` élőben vált (a cfg nem módosul), az `update_server` tartósan ír a cfg-be.
A `delete_server` csak `confirm=true`-val fut le, hogy az AI ne töröljön véletlenül.

## Portok

| Szolgáltatás | Port |
|---|---|
| Panel (HTTP) | 8080/tcp |
| Játékszerver | 28960/udp (példányonként növelve: 28961, 28962 …) |

Proxmox NAT esetén a játékportot UDP-n kell továbbítani a konténerre.
A panelt ne tedd publikus internetre védelem nélkül — tedd reverse proxy (nginx/Caddy) mögé HTTPS-sel,
vagy érd el VPN-en.

## Könyvtárszerkezet

```
/opt/codpanel/
├── app/                  # a panel kódja
├── venv/                 # Python virtualenv
└── data/                 # CODPANEL_DATA
    ├── panel.db          # SQLite: szerverek, beállítások, napló, admin
    ├── serverfiles/<játék>/   # a dedikált szerver fájljai (main/, uo/, usermaps/ …)
    ├── downloads/        # letöltött archívumok (cache)
    └── logs/             # példányonkénti konzol log
```

A generált szerver cfg a játék mod könyvtárába kerül: `serverfiles/<játék>/<moddir>/<szerver-id>.cfg`.

## Architektúra

- **Backend:** Python 3 + FastAPI + uvicorn. A játékszervereket közvetlenül `subprocess`
  felügyeli (nincs screen/tmux), így a stdout élőben streamelhető és a stdin-re parancs írható.
- **Process kezelés:** saját process group, leállítás `quit` → SIGTERM → SIGKILL sorrendben,
  összeomlás után exponenciálisan késleltetett újraindítás.
- **Query/RCON:** natív Quake3/IW protokoll (`getstatus`, `rcon`) UDP-n, külső függőség nélkül.
- **Frontend:** build nélküli vanilla JS SPA (`panel/static`), WebSocket konzol.
- **Adatbázis:** SQLite (stdlib `sqlite3`).

### REST API (session cookie-val)

```
GET    /api/games                      játékok + telepítési állapot
POST   /api/games/{gid}/install        szerverfájlok telepítése
GET    /api/games/{gid}/maps           mapok, mod-ok, telepített fájlok
POST   /api/games/{gid}/maps/url       custom map letöltése URL-ről
POST   /api/games/{gid}/maps/upload    custom map feltöltése (multipart)
GET    /api/instances                  szerverek + élő állapot
POST   /api/instances                  új szerver
PATCH  /api/instances/{id}             beállítások mentése (cfg újraírással)
POST   /api/instances/{id}/start|stop|restart|command|writecfg
GET    /api/instances/{id}/console     konzol buffer
WS     /api/instances/{id}/console/ws  élő konzol
GET    /api/system                     rendszer állapot
```

## Hibaelhárítás

| Jelenség | Megoldás |
|---|---|
| „nem találom a 32 bites libeket” | `dpkg --add-architecture i386 && apt update && apt install -y lib32gcc-s1 lib32stdc++6` |
| A szerver azonnal kilép | Konzol fül → a kimenetben látszik az ok (hiányzó map, hibás cfg, foglalt port) |
| `error while loading shared libraries: libstdc++.so.5` | Játékfájlok oldal → *Hiányzó könyvtárak telepítése* (egy kattintás) |
| `Error: Couldn't load default.cfg` | A játékfájlok nem bontódtak ki teljesen — *Újratelepítés* a Játékfájlok fülön |
| A szerver nem látszik a böngészőben | UDP 28960 nincs nyitva / továbbítva; `sv_hostname` és `net_port` a cfg-ben a panelből jön |
| CoD4 „authorizemode” hiba | A csomag a CoD4X 1.8 szervert tartalmazza, ami `sv_authorizemode -1`-gyel offline is fut (a panel ezt automatikusan beállítja) |
| Panel nem indul | `journalctl -u codpanel -f` |
| Elfelejtett admin jelszó | `bash /opt/codpanel/app/reset-password.sh admin UjJelszo123` |
| `template: no such template` | Régi verzió: be volt drótozva egy template-verzió. A mostani script a katalógusból választ; ha mégis kell, add meg: `--template <fájlnév>` |
| A telepítő szó nélkül kilép | Régi verzió (SIGPIPE hiba a jelszógenerálásnál). Húzd le újra a repót — a mostani scriptek hiba esetén ki is írják, melyik sorban álltak le. |

## Licenc

MIT. A játék szerverfájlok az Activision tulajdonát képezik, azokat a LinuxGSM nyilvános
tükreiről töltjük le — a játék birtoklása a te felelősséged.
