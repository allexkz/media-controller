"""Volume do sistema e por aplicativo (Core Audio via pycaw)."""
from functools import wraps

import comtypes
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation


def com(fn):
    """Garante COM inicializado na thread atual (uvicorn usa threadpool)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        comtypes.CoInitialize()
        try:
            return fn(*args, **kwargs)
        finally:
            comtypes.CoUninitialize()
    return wrapper


def _endpoint():
    return AudioUtilities.GetSpeakers().EndpointVolume


@com
def get_master():
    ep = _endpoint()
    return {
        "volume": round(ep.GetMasterVolumeLevelScalar() * 100),
        "mute": bool(ep.GetMute()),
    }


def _clamp(v):
    return max(0, min(100, v))


@com
def set_master(volume=None, mute=None, delta=None):
    ep = _endpoint()
    if delta is not None:
        volume = round(ep.GetMasterVolumeLevelScalar() * 100) + delta
    if volume is not None:
        ep.SetMasterVolumeLevelScalar(_clamp(volume) / 100, None)
    if mute is not None:
        ep.SetMute(int(mute), None)


def _peak(session):
    try:
        meter = session._ctl.QueryInterface(IAudioMeterInformation)
        return meter.GetPeakValue()
    except Exception:
        return 0.0


@com
def list_apps():
    """Apps com sessão de áudio, agrupados pelo nome do processo."""
    apps = {}
    for s in AudioUtilities.GetAllSessions():
        if not s.Process:
            continue
        name = s.Process.name()
        vol = s.SimpleAudioVolume
        app = apps.setdefault(name, {
            "name": name,
            "volume": round(vol.GetMasterVolume() * 100),
            "mute": bool(vol.GetMute()),
            "active": False,
        })
        app["active"] = app["active"] or _peak(s) > 0.001
    return sorted(apps.values(), key=lambda a: a["name"].lower())


@com
def set_app(name, volume=None, mute=None, delta=None):
    found = False
    for s in AudioUtilities.GetAllSessions():
        if s.Process and s.Process.name().lower() == name.lower():
            found = True
            vol = s.SimpleAudioVolume
            target = volume
            if delta is not None:
                target = round(vol.GetMasterVolume() * 100) + delta
            if target is not None:
                vol.SetMasterVolume(_clamp(target) / 100, None)
            if mute is not None:
                vol.SetMute(int(mute), None)
    return found


@com
def is_playing(process_prefix):
    return any(
        s.Process and s.Process.name().lower().startswith(process_prefix) and _peak(s) > 0.001
        for s in AudioUtilities.GetAllSessions()
    )
