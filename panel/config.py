"""Paths and global settings for the COD panel."""
import os
import secrets
from pathlib import Path

PANEL_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PANEL_DIR.parent

DATA_DIR = Path(os.environ.get("CODPANEL_DATA", PROJECT_DIR / "data")).resolve()
SERVERFILES_DIR = DATA_DIR / "serverfiles"   # <game>/ -> extracted game files
DOWNLOAD_DIR = DATA_DIR / "downloads"        # archives + custom map downloads
LOG_DIR = DATA_DIR / "logs"
BACKUP_DIR = DATA_DIR / "backups"
DB_PATH = DATA_DIR / "panel.db"

HOST = os.environ.get("CODPANEL_HOST", "0.0.0.0")
PORT = int(os.environ.get("CODPANEL_PORT", "8080"))

# Console ring buffer size per instance (lines kept in memory)
CONSOLE_BUFFER = int(os.environ.get("CODPANEL_CONSOLE_BUFFER", "800"))

SESSION_COOKIE = "codpanel_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7


def ensure_dirs() -> None:
    for d in (DATA_DIR, SERVERFILES_DIR, DOWNLOAD_DIR, LOG_DIR, BACKUP_DIR):
        d.mkdir(parents=True, exist_ok=True)


def secret_key() -> bytes:
    """Persistent secret used to sign session cookies."""
    ensure_dirs()
    path = DATA_DIR / "secret.key"
    if not path.exists():
        path.write_text(secrets.token_hex(32))
        path.chmod(0o600)
    return path.read_text().strip().encode()
