# COD Panel

Webes admin felület Call of Duty dedikált szerverekhez — LinuxGSM-kompatibilis binárisok és
indítási paraméterek, de **CLI helyett böngészőből** kezelhetően. Proxmox LXC konténerre szabva.

![status](https://img.shields.io/badge/python-3.9%2B-blue) ![license](https://img.shields.io/badge/license-MIT-green)

## Mit tud

| | |
|---|---|
| **5 játék** | Call of Duty, CoD: United Offensive, Call of Duty 2, Call of Duty 4 (CoD4X), CoD: World at War |
| **Több szerver** | Egy panelből korlátlan számú példány, mindegyiknek saját port, cfg, log, konzol |
| **Egy kattintásos játékfájl-telepítés** | A LinuxGSM tükrökről, MD5 ellenőrzéssel |
| **Egy kattintásos custom map** | URL-ről letöltve vagy fájlból feltöltve (.iwd / .pk3 / .ff / .zip), utána azonnal kiválasztható |
| **Minden beállítás űrlapon** | gamemode, map, slotok, friendly fire, killcam, limitek, rcon, fast download, sv_pure, gravitáció… |
| **Map rotáció szerkesztő** | sorrend, játékmód maponként, `sv_mapRotation` generálás |
| **Élő konzol** | WebSocket, közvetlen stdin + RCON, játékoslista, kick, azonnali map váltás |
| **Felügyelet** | automatikus indítás boot-kor, automatikus újraindítás összeomlás után, RAM/uptime/játékosszám |

A panel ugyanazokat a binárisokat és indítási paramétereket használja, mint a LinuxGSM
`codserver` / `coduoserver` / `cod2server` / `cod4server` / `codwawserver` scriptek,
így a meglévő tudás és a community cfg-k változtatás nélkül működnek.

## Telepítés

### A) Proxmox host-ról, egy lépésben (konténer létrehozásával)

A **Proxmox host shelljében**:

```bash
git clone https://github.com/miatoszs/cod-panel /tmp/cod-panel
bash /tmp/cod-panel/proxmox-lxc.sh --ctid 150 --hostname codpanel --disk 40 --ram 4096 --cores 4
```

Létrehoz egy Debian 12 unprivileged LXC-t, feltelepíti a panelt, és kiírja a web felület
címét + a generált admin jelszót.

### B) Meglévő LXC konténerben / VM-ben

A **konténeren belül, root-ként**:

```bash
apt update && apt install -y git
git clone https://github.com/miatoszs/cod-panel /opt/cod-panel-src
bash /opt/cod-panel-src/install.sh
```

Opciók: `--port 8080`, `--admin admin`, `--password sajatjelszo`, `--prefix /opt/codpanel`.

A telepítő elintézi:
- 32 bites futtatókörnyezet (`lib32gcc-s1`, `lib32stdc++6`) — a COD szerverek 32 bites binárisok,
- `codpanel` rendszerfelhasználó, Python venv, függőségek,
- systemd service (`codpanel`), automatikus indítással,
- admin felhasználó (jelszó generálva, ha nem adod meg).

### C) Fejlesztéshez / kipróbáláshoz (bármilyen Linuxon)

```bash
./run.sh          # venv létrehozás + indítás: http://localhost:8080
```

Első belépésnél a panel megkér, hogy adj meg admin felhasználót és jelszót.

## Használat

1. **Játékfájlok** fül → a kívánt COD verziónál *Szerverfájlok telepítése*
   (letöltés + MD5 ellenőrzés + kibontás, folyamatjelzővel).
2. **Szerverek → Új szerver** → játék, név, port, slotok, játékmód, induló map, mod.
3. A szerver lapon:
   - **Beállítások** — minden dvar űrlapon (a „Egyéni dvar-ok” mezőbe bármilyen extra cfg sor mehet),
   - **Map rotáció** — sorrend + játékmód maponként,
   - **Mapok** — custom tartalom telepítése,
   - **Konzol** — élő kimenet, parancsküldés (konzol vagy RCON),
   - **cfg / parancs** — a generált `<id>.cfg` és a teljes indítási parancs.
4. **Indítás** gomb. Minden mentés újraírja a cfg-t; az „Mentés + újraindítás” azonnal alkalmazza.

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
| `Error: Couldn't load default.cfg` | A játékfájlok nem bontódtak ki teljesen — *Újratelepítés* a Játékfájlok fülön |
| A szerver nem látszik a böngészőben | UDP 28960 nincs nyitva / továbbítva; `sv_hostname` és `net_port` a cfg-ben a panelből jön |
| CoD4 „authorizemode” hiba | A csomag a CoD4X 1.8 szervert tartalmazza, ami `sv_authorizemode -1`-gyel offline is fut (a panel ezt automatikusan beállítja) |
| Panel nem indul | `journalctl -u codpanel -f` |

## Licenc

MIT. A játék szerverfájlok az Activision tulajdonát képezik, azokat a LinuxGSM nyilvános
tükreiről töltjük le — a játék birtoklása a te felelősséged.
