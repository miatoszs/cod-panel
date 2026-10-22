#!/usr/bin/env bash
# =============================================================================
#  COD Panel - MCP szerver beállítása a Claude klienshez (a saját gépeden)
#
#  Használat:
#      bash setup-mcp.sh                        # interaktív (URL + token bekérés)
#      bash setup-mcp.sh --url http://10.0.0.50:8080
#      bash setup-mcp.sh --url ... --target project
#
#  A tokent rejtett beírással kéri, és nem írja ki sehova a konzolra.
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${CODPANEL_PYTHON:-$REPO_DIR/.venv/bin/python}"
PANEL_URL=""
TOKEN="${CODPANEL_TOKEN:-}"
TARGET="desktop"          # desktop | project | print
NAME="codpanel"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) PANEL_URL="$2"; shift 2 ;;
    --token) TOKEN="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    --name) NAME="$2"; shift 2 ;;
    --python) PYTHON="$2"; shift 2 ;;
    -h|--help) grep '^#' "$0" | cut -c3-; exit 0 ;;
    *) echo "Ismeretlen paraméter: $1"; exit 1 ;;
  esac
done

say() { printf '\n\033[1;33m==>\033[0m %s\n' "$*"; }

# --- 1. Python + MCP SDK ------------------------------------------------------
say "Futtatókörnyezet ellenőrzése"
if [[ ! -x "$PYTHON" ]]; then
  echo "   Nincs venv itt: $PYTHON — létrehozom."
  python3 -m venv "$REPO_DIR/.venv"
  PYTHON="$REPO_DIR/.venv/bin/python"
  "$PYTHON" -m pip install -q --upgrade pip
fi
if ! "$PYTHON" -c "import mcp" 2>/dev/null; then
  echo "   MCP SDK telepítése..."
  "$PYTHON" -m pip install -q 'mcp>=2,<3'
fi
echo "   python: $PYTHON"
echo "   mcp:    $("$PYTHON" -c "import importlib.metadata as m;print(m.version('mcp'))")"

# --- 2. Panel elérhetősége ----------------------------------------------------
if [[ -z "$PANEL_URL" ]]; then
  read -rp "A panel címe (pl. http://10.0.0.50:8080): " PANEL_URL
fi
PANEL_URL="${PANEL_URL%/}"

say "Panel elérése: $PANEL_URL"
VERSION="$(curl -fsS --max-time 10 "$PANEL_URL/api/version" 2>/dev/null || true)"
if [[ -z "$VERSION" ]]; then
  echo "   NEM érem el a panelt itt: $PANEL_URL" >&2
  echo "   Fut a konténerben a codpanel szolgáltatás? Jó az IP és a port?" >&2
  exit 1
fi
echo "   válasz: $VERSION"

# --- 3. Token -----------------------------------------------------------------
if [[ -z "$TOKEN" ]]; then
  echo
  echo "   A tokent a panelen készítheted: Beállítások -> AI vezérlés -> Token készítése"
  read -rsp "   Illeszd be a tokent (nem jelenik meg): " TOKEN
  echo
fi
[[ -n "$TOKEN" ]] || { echo "   Üres token, kilépek." >&2; exit 1; }

say "Token ellenőrzése"
CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
        -H "Authorization: Bearer $TOKEN" "$PANEL_URL/api/instances")"
if [[ "$CODE" != "200" ]]; then
  echo "   A panel elutasította a tokent (HTTP $CODE). Készíts újat a Beállításokban." >&2
  exit 1
fi
echo "   rendben, a token működik"

# --- 4. MCP szerver próbaindítása --------------------------------------------
say "MCP szerver próbája"
PYTHONPATH="$REPO_DIR" CODPANEL_URL="$PANEL_URL" CODPANEL_TOKEN="$TOKEN" \
  "$PYTHON" - <<'PY'
import asyncio, sys
sys.path.insert(0, __import__("os").environ["PYTHONPATH"])
from panel import mcp_server
tools = asyncio.run(mcp_server.server.list_tools())
print(f"   {len(tools)} eszköz betöltve: " + ", ".join(t.name for t in tools[:5]) + " ...")
PY

# --- 5. Konfiguráció írása ----------------------------------------------------
write_config() {
  local target_file="$1"
  PANEL_URL="$PANEL_URL" TOKEN="$TOKEN" REPO_DIR="$REPO_DIR" PYTHON="$PYTHON" \
  NAME="$NAME" TARGET_FILE="$target_file" "$PYTHON" - <<'PY'
import json, os, pathlib, shutil, time

path = pathlib.Path(os.environ["TARGET_FILE"])
entry = {
    "command": os.environ["PYTHON"],
    "args": ["-m", "panel.mcp_server"],
    "env": {
        "PYTHONPATH": os.environ["REPO_DIR"],
        "CODPANEL_URL": os.environ["PANEL_URL"],
        "CODPANEL_TOKEN": os.environ["TOKEN"],
    },
}
data = {}
if path.exists():
    try:
        data = json.loads(path.read_text() or "{}")
    except ValueError:
        raise SystemExit(f"   A meglévő {path} nem érvényes JSON, nem nyúlok hozzá.")
    backup = path.with_suffix(path.suffix + f".bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(path, backup)
    print(f"   biztonsági másolat: {backup}")
path.parent.mkdir(parents=True, exist_ok=True)
servers = data.setdefault("mcpServers", {})
existed = os.environ["NAME"] in servers
servers[os.environ["NAME"]] = entry
path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
path.chmod(0o600)
print(f"   {'frissítve' if existed else 'hozzáadva'}: {os.environ['NAME']} -> {path}")
print(f"   a fájlban {len(servers)} MCP szerver van: {', '.join(servers)}")
PY
}

case "$TARGET" in
  desktop)
    say "Claude kliens konfigurálása"
    write_config "$HOME/.config/Claude/claude_desktop_config.json"
    echo
    echo "   Indítsd újra a Claude alkalmazást, hogy betöltse."
    ;;
  project)
    say "Projekt szintű .mcp.json írása"
    write_config "$REPO_DIR/.mcp.json"
    grep -qxF '.mcp.json' "$REPO_DIR/.gitignore" 2>/dev/null \
      || echo '.mcp.json' >> "$REPO_DIR/.gitignore"
    echo "   (.gitignore-ba felvéve, hogy a token ne kerüljön a repóba)"
    ;;
  print)
    say "Beállítás blokk (másold a kliensed konfigjába)"
    cat <<JSON
{
  "mcpServers": {
    "$NAME": {
      "command": "$PYTHON",
      "args": ["-m", "panel.mcp_server"],
      "env": {
        "PYTHONPATH": "$REPO_DIR",
        "CODPANEL_URL": "$PANEL_URL",
        "CODPANEL_TOKEN": "<a tokened>"
      }
    }
  }
}
JSON
    ;;
  *) echo "Ismeretlen --target: $TARGET (desktop | project | print)"; exit 1 ;;
esac

say "Kész"
echo "   Próbáld ki az AI-ban: \"listázd a COD szervereket\" vagy"
echo "   \"válts mapot a cod2 szerveren Toujane-ra\""
