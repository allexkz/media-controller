"""Controle de mídia: SMTC do Windows + fallback por teclado para o Stremio."""
from datetime import datetime, timedelta, timezone

import asyncio
import os

import psutil
from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as Manager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status,
)

import audio
import keys

STREMIO_ID = "stremio"
STREMIO_PROCESS = "stremio-shell-ng.exe"
# "post" = manda a tecla direto pra janela (sem foco); "focus" = traz a janela pra frente e simula teclado
STREMIO_INPUT = os.environ.get("MC_STREMIO_INPUT", "post")

_manager = None


async def _get_manager():
    global _manager
    if _manager is None:
        _manager = await Manager.request_async()
    return _manager


def _pretty_app(app_id):
    name = app_id.split("!")[-1].split("\\")[-1]
    return name.removesuffix(".exe").removesuffix(".EXE")


def _stremio_running():
    return any(p.info["name"] == STREMIO_PROCESS for p in psutil.process_iter(["name"]))


def _live_position(session, tl):
    """O SMTC só atualiza a posição de tempos em tempos; extrapola se estiver tocando."""
    pos = tl.position
    if session.get_playback_info().playback_status == Status.PLAYING and tl.last_updated_time.year > 1601:
        elapsed = datetime.now(timezone.utc) - tl.last_updated_time
        if timedelta(0) < elapsed < timedelta(hours=24):
            pos += elapsed
    return pos


def _youtube_window(title, windows=None):
    """Janela do navegador com a aba do YouTube desse vídeo em primeiro plano.

    O título da janela do navegador é o da aba ativa ("<vídeo> - YouTube - ..."),
    então só encontra se a aba do vídeo for a aba ativa da janela.
    """
    if not title:
        return None
    if windows is None:
        windows = keys.windows_with_title("YouTube")
    for hwnd, text in windows:
        if title in text:
            return hwnd
    return None


async def list_sessions():
    sessions = []
    yt_windows = keys.windows_with_title("YouTube")
    mgr = await _get_manager()
    current = mgr.get_current_session()
    current_id = current.source_app_user_model_id if current else None
    for s in mgr.get_sessions():
        try:
            props = await s.try_get_media_properties_async()
            info = s.get_playback_info()
            tl = s.get_timeline_properties()
        except Exception:
            continue
        sessions.append({
            "id": s.source_app_user_model_id,
            "app": _pretty_app(s.source_app_user_model_id),
            "title": props.title or "",
            "artist": props.artist or "",
            "playing": info.playback_status == Status.PLAYING,
            "position": _live_position(s, tl).total_seconds(),
            "duration": tl.end_time.total_seconds(),
            "can_seek": bool(info.controls.is_playback_position_enabled),
            "current": s.source_app_user_model_id == current_id,
            "can_fullscreen": _youtube_window(props.title, yt_windows) is not None,
        })
    if _stremio_running():
        sessions.append({
            "id": STREMIO_ID,
            "app": "Stremio",
            "title": "",
            "artist": "",
            "playing": await asyncio.to_thread(audio.is_playing, "stremio"),
            "position": None,
            "duration": None,
            "can_seek": True,
            "current": False,
            "can_fullscreen": True,
        })
    return sessions


def pick_default(sessions):
    """Prefere o que está tocando; empate → sessão 'atual' do Windows."""
    if not sessions:
        return None
    ranked = sorted(sessions, key=lambda s: (not s["playing"], not s["current"]))
    return ranked[0]["id"]


async def _find(session_id):
    mgr = await _get_manager()
    for s in mgr.get_sessions():
        if s.source_app_user_model_id == session_id:
            return s
    return None


async def _resolve(session_id):
    if session_id:
        return session_id
    return pick_default(await list_sessions())


async def _stremio_key(key):
    send = keys.post_to if STREMIO_INPUT == "post" else keys.send_to
    await asyncio.to_thread(send, STREMIO_PROCESS, key)


async def control(action, session_id=None):
    """action: toggle | play | pause."""
    sid = await _resolve(session_id)
    if sid is None:
        keys.tap(keys.VK["media_play_pause"])
        return {"target": "media-key"}
    if sid == STREMIO_ID:
        if action != "toggle" and (action == "play") == await asyncio.to_thread(audio.is_playing, "stremio"):
            return {"target": sid}
        await _stremio_key("space")
        return {"target": sid}
    s = await _find(sid)
    if s is None:
        return {"error": "sessão não encontrada"}
    if action == "play":
        await s.try_play_async()
    elif action == "pause":
        await s.try_pause_async()
    else:
        await s.try_toggle_play_pause_async()
    return {"target": sid}


async def seek(seconds, session_id=None):
    sid = await _resolve(session_id)
    if sid is None:
        return {"error": "nenhuma mídia ativa"}
    if sid == STREMIO_ID:
        # Stremio: cada seta = 10s
        key = "right" if seconds > 0 else "left"
        for _ in range(max(1, round(abs(seconds) / 10))):
            await _stremio_key(key)
        return {"target": sid}
    s = await _find(sid)
    if s is None:
        return {"error": "sessão não encontrada"}
    tl = s.get_timeline_properties()
    target = _live_position(s, tl) + timedelta(seconds=seconds)
    target = max(timedelta(0), min(target, tl.end_time)) if tl.end_time else max(timedelta(0), target)
    ok = await s.try_change_playback_position_async(int(target.total_seconds() * 10_000_000))
    return {"target": sid, "ok": bool(ok)}


async def fullscreen(session_id=None):
    """Alterna tela cheia (tecla F) no YouTube ou no Stremio, trazendo a janela pra frente."""
    sid = await _resolve(session_id)
    if sid is None:
        return {"error": "nenhuma mídia ativa"}
    if sid == STREMIO_ID:
        hwnd = await asyncio.to_thread(keys.find_window, STREMIO_PROCESS)
    else:
        s = await _find(sid)
        if s is None:
            return {"error": "sessão não encontrada"}
        props = await s.try_get_media_properties_async()
        hwnd = await asyncio.to_thread(_youtube_window, props.title)
    if not hwnd:
        return {"error": "janela do vídeo não encontrada"}
    await asyncio.to_thread(keys.press_in, hwnd, "f")
    return {"target": sid}
