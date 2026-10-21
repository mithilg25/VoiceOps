#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from src.agent import Agent

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac"}

def run_voice(audio_dir: str, out_dir: str, lang: str):
    from src.voice import transcribe, speak
    in_dir = Path(audio_dir)
    out_dir = Path(out_dir)
    (out_dir / "audio").mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in in_dir.iterdir() if p.suffix.lower() in AUDIO_EXTS)
    results = []

    for audio in files:
        agent = Agent(voice=True, tag=f"batch_{audio.stem}")
        heard = transcribe(str(audio), lang)
        
        if not heard:
            reply, meta = "Sorry, I didn't catch that. Could you say it again?", {"sources": []}
        else:
            reply, meta = agent.respond(heard)

        reply_wav = out_dir / "audio" / f"{audio.stem}.reply.wav"
        speak(reply, str(reply_wav), lang=lang)
        
        (out_dir / "audio" / f"{audio.stem}.reply.txt").write_text(reply, encoding="utf-8")
        results.append({
            "input": audio.name, "heard": heard, "reply": reply,
            "reply_audio": str(reply_wav.relative_to(out_dir)), "sources": meta.get("sources", []),
        })

    (out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(results)} results to {out_dir}")

def run_text(text: str):
    agent = Agent(voice=False)
    reply, meta = agent.respond(text)
    print("\nUSER :", text)
    print("AGENT:", reply)
    print("SRC  :", ", ".join(meta.get("sources", [])))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio_dir")
    ap.add_argument("--out_dir", default="sample_outputs")
    ap.add_argument("--lang", default="en-IN")
    ap.add_argument("--text")
    a = ap.parse_args()

    if a.text:
        run_text(a.text)
    elif a.audio_dir:
        run_voice(a.audio_dir, a.out_dir, a.lang)
    else:
        ap.error("Provide --audio_dir or --text")