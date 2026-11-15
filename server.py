"""Media Controller — controle volume e mídia do PC pelo celular."""
import json
import secrets
import socket
import sys
import time
from pathlib import Path
from typing import Optional

import qrcode
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

import audio
import media

ROOT = Path(__file__).parent
CONFIG = ROOT / "config.json"
PORT = 8765


def load_config():
    if CONFIG.exists():
        return json.loads(CONFIG.read_text())
    cfg = {"token": secrets.token_urlsafe(12), "port": PORT}
    CONFIG.write_text(json.dumps(cfg, indent=2))
    return cfg


cfg = load_config()
app = FastAPI(title="Media Controller")


@app.middleware("http")
async def log_requests(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    if request.method == "POST":
        ms = (time.perf_counter() - start) * 1000
        print(f"{time.strftime('%H:%M:%S')} {request.client.host} {request.url.path} -> {response.status_code} ({ms:.0f} ms)")
    return response


def auth(x_token: Optional[str] = Header(default=None)):
    if x_token != cfg["token"]:
        raise HTTPException(401, "token inválido")


class VolumeBody(BaseModel):
    volume: Optional[int] = None
    mute: Optional[bool] = None


class ControlBody(BaseModel):
    session: Optional[str] = None


class SeekBody(BaseModel):
    seconds: float
    session: Optional[str] = None


@app.get("/api/state", dependencies=[Depends(auth)])
async def state():
    sessions = await media.list_sessions()
    return {
        "master": await run_in_threadpool(audio.get_master),
        "apps": await run_in_threadpool(audio.list_apps),
        "sessions": sessions,
        "default_session": media.pick_default(sessions),
    }


@app.post("/api/master", dependencies=[Depends(auth)])
async def master(body: VolumeBody):
    await run_in_threadpool(audio.set_master, body.volume, body.mute)
    return await run_in_threadpool(audio.get_master)


@app.post("/api/app/{name}", dependencies=[Depends(auth)])
async def app_volume(name: str, body: VolumeBody):
    if not await run_in_threadpool(audio.set_app, name, body.volume, body.mute):
        raise HTTPException(404, "app sem sessão de áudio")
    return {"ok": True}


@app.post("/api/media/{action}", dependencies=[Depends(auth)])
async def media_control(action: str, body: ControlBody):
    if action not in ("toggle", "play", "pause"):
        raise HTTPException(400, "ação inválida")
    return await media.control(action, body.session)


@app.post("/api/seek", dependencies=[Depends(auth)])
async def media_seek(body: SeekBody):
    return await media.seek(body.seconds, body.session)


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


def local_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    port = cfg.get("port", PORT)
    url = f"http://{local_ip()}:{port}/?t={cfg['token']}"
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    try:
        qr.print_ascii(invert=True)
    except Exception:
        pass
    print(f"\n  Abra no celular: {url}\n")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
