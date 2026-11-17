"""AutoViral Local: free local video-to-shorts tool."""
import json
import math
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

import gradio as gr
import numpy as np

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "outputs"
OUTPUT.mkdir(exist_ok=True)

EXCITING = set("wow omg incredible amazing unbelievable funny hilarious crazy insane shock shocked wait what no yes laugh laughing scream screaming win victory fail failed surprise surprising awesome best worst impossible epic".split())
STOP = set("the and this that they then with from were have what when which about there your just like into also really would could should does here okay yeah".split())


def check_tools():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise gr.Error("FFmpeg and FFprobe required. See README.md.")


def command(args):
    res = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode:
        raise RuntimeError((res.stderr or "Command failed")[-1800:])
    return (res.stdout or "").strip()


def get_duration(path):
    raw = command(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    result = float(raw)
    if not math.isfinite(result) or result <= 0:
        raise ValueError("Could not read video duration")
    return result


def timecode(seconds):
    seconds = int(max(0, seconds))
    return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"


def read_energy(path, duration):
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    scores = []
    try:
        while True:
            raw = proc.stdout.read(16000)
            if not raw:
                break
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
            if audio.size:
                scores.append(float(np.sqrt(np.mean((audio / 32768.0) ** 2))))
            if len(scores) >= math.ceil(duration) + 1:
                break
    finally:
        proc.stdout.close()
        if proc.poll() is None:
            proc.terminate()
        proc.wait()
    if not scores:
        return np.zeros(max(1, math.ceil(duration)), dtype=np.float32)
    values = np.asarray(scores, dtype=np.float32)
    base = np.percentile(values, 90)
    return np.clip(values / max(0.015, base), 0, 1.5)


def transcribe(path, model_name, enabled):
    if not enabled:
        return [], "Audio-only highlight detection (transcription disabled)."
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return [], "Transcription unavailable. Install optional package: pip install faster-whisper"
    try:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        raw_segments, info = model.transcribe(str(path), beam_size=1, vad_filter=True)
        segments = [{"start": float(s.start), "end": float(s.end), "text": s.text.strip()} for s in raw_segments]
        return segments, f"Transcript enabled (detected language: {info.language})."
    except Exception as exc:
        return [], f"Transcription failed ({exc}). Audio highlights were used instead."


def make_candidates(duration, target, energy, segments, prompt):
    target = max(10, min(int(target), int(duration)))
    prompt_tokens = set(re.findall(r"[a-z]{3,}", prompt.lower())) - STOP
    step = max(5, min(10, target // 4))
    starts = list(range(0, max(1, math.ceil(duration - target) + 1), step))
    starts.append(max(0, duration - target))
    choices = []
    for start in sorted(set(round(x, 2) for x in starts)):
        end = min(start + target, duration)
        chunk = energy[int(start):max(int(start) + 1, math.ceil(end))]
        loud = float(np.percentile(chunk, 85)) if chunk.size else 0
        rise = float(np.max(np.abs(np.diff(chunk)))) if chunk.size > 1 else 0
        words = " ".join(s["text"] for s in segments if s["end"] > start and s["start"] < end)
        tokens = re.findall(r"[a-z]{3,}", words.lower())
        exciting = sum(t in EXCITING for t in tokens)
        matching = sum(t in prompt_tokens for t in tokens)
        speaking = min(len(tokens) / 90, 1) if segments else 0
        score = loud * 2 + rise * 0.8 + min(exciting, 5) * 0.7 + min(matching, 7) * 0.8 + speaking * 0.35
        choices.append((score, start, end, words))
    choices.sort(reverse=True)
    selected = []
    for candidate in choices:
        _, start, end, _ = candidate
        if all(min(end, e) - max(start, s) <= 0.2 * target for _, s, e, _ in selected):
            selected.append(candidate)
        if len(selected) >= 12:
            break
    return selected


def caption_for(text, prompt, index):
    words = re.findall(r"[A-Za-z][A-Za-z']+", text)
    short = " ".join(words[:10]).strip()
    if short:
        short = short[0].upper() + short[1:]
        title = f"{short}..." if len(words) > 10 else short
    else:
        title = f"The moment you need to see #{index}"
    tags = ["#Shorts", "#Reels", "#Clips"]
    prompt_l = prompt.lower()
    if "gaming" in prompt_l or "gameplay" in prompt_l or "gta" in prompt_l:
        tags += ["#Gaming", "#GamingClips"]
    if "podcast" in prompt_l:
        tags.append("#PodcastClips")
    return title[:95], f"{title[:110]}\n\n{' '.join(tags)}"


def render(source, output, start, duration, layout, credit):
    if layout == "Fit entire image (no crop)":
        vf = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
    else:
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    args = [
        "ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", str(start), "-i", str(source), "-t", str(duration),
        "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        "-metadata", f"comment=Creator credit: {credit.strip()[:80]}" if credit.strip() else "comment=AutoViral Local export",
        str(output)
    ]
    command(args)


def generate(video, instructions, count, length, layout, transcript_enabled, whisper_model, credit, progress=gr.Progress()):
    if not video:
        raise gr.Error("Upload a video first.")
    check_tools()
    source = Path(video)
    duration = get_duration(source)
    if duration < 10:
        raise gr.Error("Upload a video at least 10 seconds long.")
    job = OUTPUT / (datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6])
    job.mkdir(parents=True)
    progress(0.05, desc="Reading video audio")
    energy = read_energy(source, duration)
    progress(0.25, desc="Transcribing spoken content (slower on CPU)")
    segments, transcript_note = transcribe(source, whisper_model, transcript_enabled)
    progress(0.47, desc="Selecting interesting moments")
    candidates = make_candidates(duration, length, energy, segments, instructions or "")[:int(count)]
    if not candidates:
        raise gr.Error("No usable clip segments found.")
    output_files, items = [], []
    for i, (score, start, end, excerpt) in enumerate(candidates, 1):
        progress(0.5 + (i - 1) / len(candidates) * 0.45, desc=f"Rendering short {i} / {len(candidates)}")
        out = job / f"short_{i:02d}.mp4"
        render(source, out, start, end - start, layout, credit or "")
        title, caption = caption_for(excerpt, instructions or "", i)
        output_files.append(str(out))
        items.append({"clip": i, "start": timecode(start), "end": timecode(end), "score": round(score, 2), "title": title, "caption": caption, "file": out.name})
    (job / "clips.json").write_text(json.dumps({"source": source.name, "instructions": instructions, "clips": items, "transcript": segments}, ensure_ascii=False, indent=2), encoding="utf-8")
    notes = [f"### Finished: {len(items)} vertical clips", transcript_note, "Clips are ranked using a rough audio-and-transcript heuristic, not guaranteed viral predictions."]
    for item in items:
        notes.append(f"**Clip {item['clip']}** ({item['start']}–{item['end']}) — {item['title']}\n\n{item['caption']}")
    if credit.strip():
        notes.append("**Credit:** Saved in MP4 metadata, but NOT visibly overlaid.")
    progress(1.0, desc="Finished")
    return str(output_files[0]), output_files, "\n\n".join(notes), str(job / "clips.json")


with gr.Blocks(title="AutoViral Local") as demo:
    gr.Markdown("# 🎬 AutoViral Local\n**Free, open-source, local video → Shorts tool.** No paid API keys or account required. Videos stay on your computer. Use only content you own or have permission to edit.")
    with gr.Row():
        with gr.Column():
            video = gr.Video(label="Upload an MP4 / MOV video", sources=["upload"], format=None)
            prompt = gr.Textbox(label="What should the clips focus on?", value="Find the funniest reactions, exciting moments, and surprises. No subtitles.", lines=3)
            with gr.Row():
                count = gr.Slider(1, 5, value=3, step=1, label="Number of clips")
                length = gr.Slider(15, 60, value=30, step=5, label="Clip length (seconds)")
            layout = gr.Radio(["Fill 9:16 (crop sides)", "Fit entire image (no crop)"], label="Video layout", value="Fill 9:16 (crop sides)")
            transcription = gr.Checkbox(label="Use AI speech transcription (slower, better selection)", value=True)
            model = gr.Dropdown(["tiny", "base", "small"], value="tiny", label="Whisper model (tiny = fastest)")
            credit = gr.Textbox(label="Creator credit (saved as metadata; no visible overlay yet)", placeholder="Optional creator credit")
            submit = gr.Button("✨ Make my Shorts", variant="primary")
        with gr.Column():
            preview = gr.Video(label="First generated Short")
            files = gr.File(label="Download all Shorts", file_count="multiple")
            report = gr.Markdown("Generated clip titles and captions will appear here.")
            metadata = gr.File(label="Clip timestamps and transcript (JSON)")
    submit.click(generate, inputs=[video, prompt, count, length, layout, transcription, model, credit], outputs=[preview, files, report, metadata])
    gr.Markdown("**Current limits:** Not a professional AI editor. No split-screen tracking, automatic publishing, custom effects or guaranteed viral scoring. Long videos may take time.")

if __name__ == "__main__":
    demo.queue(max_size=10).launch(server_name="127.0.0.1", inbrowser=True, show_error=True, allowed_paths=[str(OUTPUT)])
