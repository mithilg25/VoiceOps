import os, re
from gnani.stt import GnaniSTTClient
from gnani.tts import GnaniTTSClient

_stt = None
_tts = None

def _get_clients():
    global _tts, _stt
    if _stt is None:
        if not os.getenv("GNANI_API_KEY"):
            raise RuntimeError("Gnani api key is not set")
        _stt = GnaniSTTClient()
        _tts = GnaniTTSClient()
    return _stt, _tts

def transcribe(path: str, lang: str = "en-IN") -> str:
    stt, _ = _get_clients()
    out  = stt.transcribe(path, language_code=lang)
    return (out.get("transcript") or "").strip()

def speak(text: str, out_path: str, voice: str = "Kaveri", lang: str = "en-IN"):
    _, tts = _get_clients()
    tts.synthesize(speechify(text), voice = voice, model = "timbre-v2.5", language = lang, output_file = out_path)

def speechify(text: str) -> str:
    return re.sub(r'(?<!\d)(\d{8})(?!\d)', lambda m: f"{m.group(1)[:4]} {m.group(1)[4:]}", text)    

