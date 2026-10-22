#!/usr/bin/env bash
# =============================================================================
#  COD Panel telepítő - Debian 12 / Ubuntu 22.04+ (Proxmox LXC konténerben is)
#  Használat (root-ként a konténerben):
#      bash install.sh
#      bash install.sh --port 8080 --user codpanel --password sajatjelszo
# =============================================================================
set -euo pipefail

PANEL_USER="codpanel"
PANEL_PORT="8080"
ADMIN_USER="admin"
ADMIN_PASS=""
PREFIX="/opt/codpanel"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PANEL_PORT="$2"; shift 2 ;;
    --user) PANEL_USER="$2"; shift 2 ;;
    --admin) ADMIN_USER="$2"; shift 2 ;;
    --password) ADMIN_PASS="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    -h|--help) grep '^#' "$0" | cut -c3-; exit 0 ;;
    *) echo "Ismeretlen paraméter: $1"; exit 1 ;;
  esac
done

[[ $EUID -eq 0 ]] || { echo "Root jogosultság kell (sudo bash install.sh)."; exit 1; }

trap 'echo "HIBA: a telepítő a(z) ${LINENO}. sorban állt le (kód: $?)" >&2' ERR

# Véletlen jelszó SIGPIPE-mentesen: a "tr </dev/urandom | head -c N" minta
# set -o pipefail mellett 141-es kóddal némán megöli a scriptet.
rand_pw() {
  local len="${1:-16}" out
  out="$(head -c 96 /dev/urandom | base64 | LC_ALL=C tr -dc 'A-Za-z0-9')"
  printf '%s' "${out:0:len}"
}


SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
say() { printf '\n\033[1;33m==>\033[0m %s\n' "$*"; }

say "Csomagok telepítése (32 bites futtatókörnyezet is)"
export DEBIAN_FRONTEND=noninteractive
dpkg --add-architecture i386
apt-get update -qq
# kötelező csomagok (a COD binárisok 32 bitesek: lib32gcc + lib32stdc++ nélkül nem indulnak)
apt-get install -y -qq \
  python3 python3-venv python3-pip \
  curl wget tar xz-utils unzip ca-certificates \
  lib32gcc-s1 lib32stdc++6

# opcionális i386 kiegészítők - a csomagnevek disztribúciónként eltérnek
# (Debian 13 / Ubuntu 24.04: a 64 bites time_t átállás miatt "t64" utótag),
# ezért egyenként, hibatűrően telepítjük őket
for pkg in libstdc++6:i386 libstdc++5:i386 libcurl4:i386 libcurl4t64:i386 \
           libtinfo6:i386 zlib1g:i386; do
  apt-get install -y -qq "$pkg" >/dev/null 2>&1 || true
done

say "Rendszerfelhasználó: ${PANEL_USER}"
id -u "$PANEL_USER" &>/dev/null || useradd -r -m -d "$PREFIX" -s /usr/sbin/nologin "$PANEL_USER"
mkdir -p "$PREFIX/app" "$PREFIX/data"

say "Panel fájlok másolása: $PREFIX/app"
if [[ "$SRC_DIR" != "$PREFIX/app" ]]; then
  cp -r "$SRC_DIR/panel" "$SRC_DIR/requirements.txt" "$PREFIX/app/"
  [[ -f "$SRC_DIR/requirements-mcp.txt" ]] && cp "$SRC_DIR/requirements-mcp.txt" "$PREFIX/app/"
  [[ -f "$SRC_DIR/README.md" ]] && cp "$SRC_DIR/README.md" "$PREFIX/app/"
  [[ -f "$SRC_DIR/reset-password.sh" ]] && cp "$SRC_DIR/reset-password.sh" "$PREFIX/app/"
fi

say "Python virtualenv + függőségek"
python3 -m venv "$PREFIX/venv"
"$PREFIX/venv/bin/pip" install -q --upgrade pip
"$PREFIX/venv/bin/pip" install -q -r "$PREFIX/app/requirements.txt"
# MCP szerver (AI vezérlés) - nem kötelező, a panel enélkül is megy
if [[ -f "$PREFIX/app/requirements-mcp.txt" ]]; then
  "$PREFIX/venv/bin/pip" install -q -r "$PREFIX/app/requirements-mcp.txt" \
    || echo "   (az MCP SDK nem települt - az AI vezérlés enélkül nem megy)"
fi

if [[ -z "$ADMIN_PASS" ]]; then
  ADMIN_PASS="$(rand_pw 14)"
  GENERATED=1
fi

say "Admin felhasználó létrehozása"
ADMIN_STATE="$(CODPANEL_DATA="$PREFIX/data" PYTHONPATH="$PREFIX/app" "$PREFIX/venv/bin/python" -c '
import sys
from panel import auth, db
db.init()
if auth.has_user():
    print("exists")
else:
    auth.create_user(sys.argv[1], sys.argv[2])
    print("created")
' "$ADMIN_USER" "$ADMIN_PASS")"
if [[ "$ADMIN_STATE" == "created" ]]; then
  echo "   admin létrehozva: $ADMIN_USER"
else
  echo "   admin már létezik, a jelszava változatlan"
fi

# A CoD/CoD2/CoD:UO binárisok libstdc++.so.5-öt kérnek, ami a mai Debianban már
# nincs csomagban. A panel a Debian archívumából szedi ki a data/lib32 alá.
say "Régi 32 bites könyvtárak ellenőrzése (libstdc++.so.5)"
CODPANEL_DATA="$PREFIX/data" PYTHONPATH="$PREFIX/app" "$PREFIX/venv/bin/python" -c '
from panel import legacylibs
missing = legacylibs.status()["missing"]
if not missing:
    print("   rendben, nincs hianyzo konyvtar")
else:
    r = legacylibs.install_missing()
    for item in r["installed"]:
        print("   telepitve:", item["lib"])
    for lib, err in r["failed"].items():
        print("   SIKERTELEN:", lib, "-", err)
        print("   a panel Jatekfajlok oldalan ujraprobalhato")
' || echo "   (kihagyva - a panelben a Játékfájlok oldalon pótolható)"

chown -R "$PANEL_USER:$PANEL_USER" "$PREFIX"

say "systemd service"
sed -e "s|/opt/codpanel|$PREFIX|g" \
    -e "s|^User=.*|User=$PANEL_USER|" -e "s|^Group=.*|Group=$PANEL_USER|" \
    -e "s|CODPANEL_PORT=8080|CODPANEL_PORT=$PANEL_PORT|" \
    "$SRC_DIR/systemd/codpanel.service" > /etc/systemd/system/codpanel.service
systemctl daemon-reload
systemctl enable codpanel.service
# restart (nem csak start): így az install.sh újrafuttatása frissítésként is működik
systemctl restart codpanel.service
sleep 2

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
# frissítéskor a meglévő jelszó marad érvényben - ne írjunk ki félrevezető újat
if [[ "$ADMIN_STATE" == "created" ]]; then
  PASSWORD_LINE="${ADMIN_PASS}${GENERATED:+   (generált - mentsd el!)}"
else
  PASSWORD_LINE="(változatlan - a korábbi marad)"
fi
cat <<BANNER

  ============================================================
   COD Panel telepítve
  ============================================================
   Web felület : http://${IP:-<szerver-ip>}:${PANEL_PORT}
   Admin       : ${ADMIN_USER}
   Jelszó      : ${PASSWORD_LINE}

   Szolgáltatás: systemctl status|restart|stop codpanel
   Napló       : journalctl -u codpanel -f
   Adatok      : ${PREFIX}/data  (szerverfájlok, mapok, cfg, DB)

   Elfelejtett jelszó: bash ${PREFIX}/app/reset-password.sh

   Következő lépés: a felületen "Játékfájlok" -> telepítsd a kívánt
   COD verziót, majd "Szerverek" -> Új szerver.
  ============================================================

BANNER
