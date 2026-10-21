"""Run the panel: python -m panel"""
import uvicorn

from . import config

if __name__ == "__main__":
    config.ensure_dirs()
    uvicorn.run("panel.main:app", host=config.HOST, port=config.PORT, log_level="info")
