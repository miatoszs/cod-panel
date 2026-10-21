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

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
say() { printf '\n\033[1;33m==>\033[0m %s\n' "$*"; }

say "Csomagok telepítése (32 bites futtatókörnyezet is)"
export DEBIAN_FRONTEND=noninteractive
dpkg --add-architecture i386
apt-get update -qq
apt-get install -y -qq \
  python3 python3-venv python3-pip \
  curl wget tar xz-utils unzip ca-certificates \
  lib32gcc-s1 lib32stdc++6 libstdc++6:i386 libcurl4:i386 \
  || apt-get install -y -qq python3 python3-venv python3-pip curl wget tar xz-utils unzip ca-certificates lib32gcc-s1 lib32stdc++6

say "Rendszerfelhasználó: ${PANEL_USER}"
id -u "$PANEL_USER" &>/dev/null || useradd -r -m -d "$PREFIX" -s /usr/sbin/nologin "$PANEL_USER"
mkdir -p "$PREFIX/app" "$PREFIX/data"

say "Panel fájlok másolása: $PREFIX/app"
if [[ "$SRC_DIR" != "$PREFIX/app" ]]; then
  cp -r "$SRC_DIR/panel" "$SRC_DIR/requirements.txt" "$PREFIX/app/"
  [[ -f "$SRC_DIR/README.md" ]] && cp "$SRC_DIR/README.md" "$PREFIX/app/"
fi

say "Python virtualenv + függőségek"
python3 -m venv "$PREFIX/venv"
"$PREFIX/venv/bin/pip" install -q --upgrade pip
"$PREFIX/venv/bin/pip" install -q -r "$PREFIX/app/requirements.txt"

if [[ -z "$ADMIN_PASS" ]]; then
  ADMIN_PASS="$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 14)"
  GENERATED=1
fi

say "Admin felhasználó létrehozása"
CODPANEL_DATA="$PREFIX/data" PYTHONPATH="$PREFIX/app" "$PREFIX/venv/bin/python" -c '
import sys
from panel import auth, db
db.init()
if auth.has_user():
    print("   admin mar letezik, valtozatlan")
else:
    auth.create_user(sys.argv[1], sys.argv[2])
    print("   admin letrehozva:", sys.argv[1])
' "$ADMIN_USER" "$ADMIN_PASS"

chown -R "$PANEL_USER:$PANEL_USER" "$PREFIX"

say "systemd service"
sed -e "s|/opt/codpanel|$PREFIX|g" \
    -e "s|^User=.*|User=$PANEL_USER|" -e "s|^Group=.*|Group=$PANEL_USER|" \
    -e "s|CODPANEL_PORT=8080|CODPANEL_PORT=$PANEL_PORT|" \
    "$SRC_DIR/systemd/codpanel.service" > /etc/systemd/system/codpanel.service
systemctl daemon-reload
systemctl enable --now codpanel.service
sleep 2

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
cat <<BANNER

  ============================================================
   COD Panel telepítve
  ============================================================
   Web felület : http://${IP:-<szerver-ip>}:${PANEL_PORT}
   Admin       : ${ADMIN_USER}
   Jelszó      : ${ADMIN_PASS}${GENERATED:+   (generált - mentsd el!)}

   Szolgáltatás: systemctl status|restart|stop codpanel
   Napló       : journalctl -u codpanel -f
   Adatok      : ${PREFIX}/data  (szerverfájlok, mapok, cfg, DB)

   Következő lépés: a felületen "Játékfájlok" -> telepítsd a kívánt
   COD verziót, majd "Szerverek" -> Új szerver.
  ============================================================

BANNER
