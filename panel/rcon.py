"""Quake3 / IW engine UDP protocol: rcon commands + server status queries."""
from __future__ import annotations

import socket
from typing import Any

HEADER = b"\xff\xff\xff\xff"


def _send(ip: str, port: int, payload: bytes, timeout: float = 2.5) -> bytes:
    host = "127.0.0.1" if ip in ("0.0.0.0", "", None) else ip
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    chunks = b""
    try:
        sock.sendto(HEADER + payload, (host, int(port)))
        while True:
            try:
                data, _ = sock.recvfrom(65535)
            except socket.timeout:
                break
            chunks += data
            sock.settimeout(0.35)  # collect fragmented replies
    finally:
        sock.close()
    return chunks


def _strip(data: bytes) -> str:
    text = data.replace(HEADER, b"").decode("utf-8", "replace")
    for prefix in ("print\n", "statusResponse\n", "infoResponse\n"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text


def rcon(ip: str, port: int, password: str, command: str, timeout: float = 2.5) -> str:
    if not password:
        raise ValueError("Nincs RCON jelszó beállítva ehhez a szerverhez.")
    raw = _send(ip, port, f'rcon "{password}" {command}'.encode(), timeout)
    if not raw:
        return ""
    return _strip(raw).strip()


def status(ip: str, port: int, timeout: float = 1.5) -> dict[str, Any] | None:
    """getstatus -> serverinfo dvars + player list. None when offline."""
    raw = _send(ip, port, b"getstatus", timeout)
    if not raw:
        return None
    text = _strip(raw)
    lines = text.split("\n")
    info: dict[str, str] = {}
    if lines:
        parts = lines[0].strip("\\").split("\\")
        info = {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}
    players = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        # "<score> <ping> "<name>""
        try:
            score, ping, name = line.split(" ", 2)
            players.append({"score": int(score), "ping": int(ping), "name": name.strip('"')})
        except ValueError:
            continue
    return {"info": info, "players": players}


def clean_color(text: str) -> str:
    out, i = [], 0
    while i < len(text):
        if text[i] == "^" and i + 1 < len(text) and text[i + 1].isdigit():
            i += 2
            continue
        out.append(text[i])
        i += 1
    return "".join(out)
