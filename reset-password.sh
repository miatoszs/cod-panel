#!/usr/bin/env bash
# =============================================================================
#  COD Panel - admin jelszó beállítása / visszaállítása
#
#  A KONTÉNEREN BELÜL:   bash reset-password.sh [felhasznalo] [uj-jelszo]
#  A PROXMOX HOSTRÓL:    pct exec <CTID> -- bash /opt/codpanel/app/reset-password.sh
#
#  Jelszó nélkül generál egyet és kiírja.
# =============================================================================
set -euo pipefail

PREFIX="${CODPANEL_PREFIX:-/opt/codpanel}"
PANEL_USER="${CODPANEL_USER:-codpanel}"
NAME="${1:-admin}"
PASS="${2:-}"

rand_pw() {
  local len="${1:-14}" out
  out="$(head -c 96 /dev/urandom | base64 | LC_ALL=C tr -dc 'A-Za-z0-9')"
  printf '%s' "${out:0:len}"
}

[[ -x "$PREFIX/venv/bin/python" ]] || {
  echo "Nem találom a panelt itt: $PREFIX (CODPANEL_PREFIX-szel megadható)" >&2
  exit 1
}
[[ -n "$PASS" ]] || { PASS="$(rand_pw 14)"; GENERATED=1; }
[[ ${#PASS} -ge 8 ]] || { echo "A jelszó legyen legalább 8 karakter." >&2; exit 1; }

CODPANEL_DATA="$PREFIX/data" PYTHONPATH="$PREFIX/app" "$PREFIX/venv/bin/python" -c '
import sys
from panel import auth, db
db.init()
auth.create_user(sys.argv[1], sys.argv[2])
' "$NAME" "$PASS"

# a panel a saját felhasználójaként fut, a root által írt WAL fájlok elrontanák
chown -R "$PANEL_USER:$PANEL_USER" "$PREFIX/data" 2>/dev/null || true
systemctl restart codpanel 2>/dev/null || true

cat <<BANNER

  ============================================================
   Admin belépés frissítve
     felhasználó : ${NAME}
     jelszó      : ${PASS}${GENERATED:+   (generált - mentsd el!)}
  ============================================================

BANNER
