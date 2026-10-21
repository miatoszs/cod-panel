#!/usr/bin/env bash
# =============================================================================
#  COD Panel - LXC konténer létrehozása Proxmox HOST-on (nem a konténerben!)
#
#  Példa:
#    bash proxmox-lxc.sh --ctid 150 --hostname codpanel --storage local-lvm \
#         --disk 40 --ram 4096 --cores 4 --bridge vmbr0 --ip dhcp
#
#  Utána a script a konténerbe belépve lefuttatja az install.sh-t.
# =============================================================================
set -euo pipefail

CTID=""; HOSTNAME="codpanel"; STORAGE="local-lvm"; TEMPLATE_STORAGE="local"
DISK="40"; RAM="4096"; CORES="4"; BRIDGE="vmbr0"; IPCONF="dhcp"; PASSWORD=""
TEMPLATE=""   # üresen: a legfrissebb elérhető Debian template
REPO="https://github.com/miatoszs/cod-panel"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ctid) CTID="$2"; shift 2 ;;
    --hostname) HOSTNAME="$2"; shift 2 ;;
    --storage) STORAGE="$2"; shift 2 ;;
    --template-storage) TEMPLATE_STORAGE="$2"; shift 2 ;;
    --template) TEMPLATE="$2"; shift 2 ;;
    --disk) DISK="$2"; shift 2 ;;
    --ram) RAM="$2"; shift 2 ;;
    --cores) CORES="$2"; shift 2 ;;
    --bridge) BRIDGE="$2"; shift 2 ;;
    --ip) IPCONF="$2"; shift 2 ;;
    --password) PASSWORD="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    -h|--help) grep '^#' "$0" | cut -c3-; exit 0 ;;
    *) echo "Ismeretlen paraméter: $1"; exit 1 ;;
  esac
done

trap 'echo "HIBA: a script a(z) ${LINENO}. sorban állt le (kód: $?)" >&2' ERR

# Véletlen jelszó SIGPIPE-mentesen: a "tr </dev/urandom | head -c N" minta
# set -o pipefail mellett 141-es kóddal némán megöli a scriptet.
rand_pw() {
  local len="${1:-16}" out
  out="$(head -c 96 /dev/urandom | base64 | LC_ALL=C tr -dc 'A-Za-z0-9')"
  printf '%s' "${out:0:len}"
}

command -v pct >/dev/null || { echo "Ez a script a Proxmox HOST-on fut (pct nem található)."; exit 1; }
[[ -n "$CTID" ]] || { CTID="$(pvesh get /cluster/nextid)"; echo "Automatikus CTID: $CTID"; }
[[ -n "$PASSWORD" ]] || PASSWORD="$(rand_pw 16)"

# A template-ek verziója folyamatosan változik, ezért nem drótozzuk be:
# a pveam katalógusból választjuk a legfrissebb Debian 13/12 standard image-et.
pick_template() {
  local avail pat found
  avail="$(pveam available --section system 2>/dev/null | awk '{print $NF}' || true)"
  for pat in '^debian-13-standard_.*_amd64\.tar\.(zst|gz|xz)$' \
             '^debian-12-standard_.*_amd64\.tar\.(zst|gz|xz)$'; do
    found="$(grep -E "$pat" <<<"$avail" | sort -V | tail -n 1)"
    [[ -n "$found" ]] && { printf '%s' "$found"; return 0; }
  done
  return 1
}

echo "==> Debian template ellenőrzése"
pveam update >/dev/null 2>&1 || echo "   (figyelem: a pveam update nem futott le, a gyorsítótárazott listát használom)"

if [[ -z "$TEMPLATE" ]]; then
  if ! TEMPLATE="$(pick_template)"; then
    echo "Nem találtam Debian standard template-et. Elérhető rendszer-template-ek:" >&2
    pveam available --section system | awk '{print "   " $NF}' >&2
    echo "Adj meg egyet kézzel: --template <fájlnév>" >&2
    exit 1
  fi
  echo "   választott template: $TEMPLATE"
fi

DOWNLOADED="$(pveam list "$TEMPLATE_STORAGE" 2>/dev/null || true)"
if grep -q "$TEMPLATE" <<<"$DOWNLOADED"; then
  echo "   már le van töltve"
else
  echo "   letöltés: $TEMPLATE"
  pveam download "$TEMPLATE_STORAGE" "$TEMPLATE"
fi

echo "==> Konténer létrehozása: CTID=$CTID hostname=$HOSTNAME"
pct create "$CTID" "${TEMPLATE_STORAGE}:vztmpl/${TEMPLATE}" \
  --hostname "$HOSTNAME" \
  --cores "$CORES" --memory "$RAM" --swap 512 \
  --rootfs "${STORAGE}:${DISK}" \
  --net0 "name=eth0,bridge=${BRIDGE},ip=${IPCONF}" \
  --features nesting=1 \
  --onboot 1 --unprivileged 1 \
  --password "$PASSWORD" \
  --description "COD Panel - Call of Duty game server web admin"

pct start "$CTID"
echo "==> Várakozás a hálózatra..."
for _ in $(seq 1 30); do pct exec "$CTID" -- getent hosts deb.debian.org &>/dev/null && break; sleep 2; done

echo "==> Panel telepítése a konténerben"
pct exec "$CTID" -- bash -lc "apt-get update -qq && apt-get install -y -qq git ca-certificates"
pct exec "$CTID" -- bash -lc "rm -rf /tmp/cod-panel && git clone --depth 1 '$REPO' /tmp/cod-panel && bash /tmp/cod-panel/install.sh"

IP="$(pct exec "$CTID" -- hostname -I | awk '{print $1}')"
cat <<BANNER

  ============================================================
   Kész. LXC CTID: $CTID  (root jelszó: $PASSWORD)
   Panel: http://${IP}:8080
   Belépés a konténerbe: pct enter $CTID
  ============================================================

  Megjegyzés: a COD szerverek UDP 28960+ portot használnak.
  Port forward a hoston (ha NAT-olt hálózat van), pl.:
     iptables -t nat -A PREROUTING -i vmbr0 -p udp --dport 28960 \
       -j DNAT --to ${IP}:28960

BANNER
