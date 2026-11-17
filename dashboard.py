"""Paste-first dashboard for AutoViral Local.

Run with START_WINDOWS.bat. An authorized direct MP4/MOV/WebM URL can
be pasted and submitted; the local backend downloads, analyzes and renders.
"""
import ipaddress
import json
import socket
import uuid
from pathlib import Path
from urllib.parse import urlparse

import gradio as gr
import requests

from app import OUTPUT, generate

UPLOADS = Path(__file__).resolve().parent / "uploads"
UPLOADS.mkdir(exist_ok=True)
MAX_DOWNLOAD = 1024 * 1024 * 1024  # 1 GiB
EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}
ALLOWED_SCHEMES = {"http", "https"}


def validate_public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES or not parsed.hostname or parsed.username or parsed.password:
        raise gr.Error("Paste a public http(s) direct video-file URL.")
    if parsed.port and parsed.port not in (80, 443):
        raise gr.Error("Only standard web ports 80 and 443 are allowed.")
    if parsed.hostname.lower() in ("localhost", "localhost.localdomain"):
        raise gr.Error("Local network URLs are not supported.")
    try:
        results = socket.getaddrinfo(parsed.hostname, None, type=socket.SOCK_STREAM)
    except OSError:
        raise gr.Error("Could not resolve the linked video host.")
    if not results or any(not ipaddress.ip_address(item[4][0]).is_global for item in results):
        raise gr.Error("Private and non-public IP addresses are blocked.")
    return parsed


def download_video(url):
    url = (url or "").strip()
    if not url:
        raise gr.Error("Paste a direct video file URL or upload a video.")
    host = (urlparse(url).hostname or "").lower()
    if host in {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com", "tiktok.com", "www.tiktok.com"} or host.endswith(".youtube.com"):
        raise gr.Error("YouTube/TikTok watch links cannot be imported directly. Use an authorized local video file or an approved direct MP4 URL.")
    session = requests.Session()
    session.trust_env = False
    response = None
    try:
        for _ in range(6):
            parsed = validate_public_url(url)
            try:
                response = session.get(url, stream=True, allow_redirects=False, timeout=(10, 40), headers={"User-Agent": "AutoViralLocal/1.0"})
            except requests.RequestException as exc:
                raise gr.Error(f"Couldn't access video link: {exc}")
            if response.status_code in (301, 302, 303, 307, 308):
                redirect = response.headers.get("Location", "")
                response.close()
                from urllib.parse import urljoin
                url = urljoin(url, redirect)
                continue
            break
        else:
            raise gr.Error("Too many redirects.")
        response.raise_for_status()
        parsed = urlparse(url)
        ext = Path(parsed.path).suffix.lower()
        if ext not in EXTENSIONS:
            raise gr.Error("Link must point directly to an MP4, MOV, WebM or MKV file. Regular webpage links aren't supported.")
        mime = response.headers.get("Content-Type", "").split(";")[0].lower().strip()
        if mime not in ("application/octet-stream", "binary/octet-stream", "") and not mime.startswith("video/"):
            raise gr.Error("Link returned a webpage or non-video file.")
        size_header = response.headers.get("Content-Length")
        if size_header and int(size_header) > MAX_DOWNLOAD:
            raise gr.Error("Video is over 1 GB. Use local upload instead.")
        out = UPLOADS / (uuid.uuid4().hex + ext)
        size = 0
        try:
            with open(out, "wb") as f:
                for block in response.iter_content(chunk_size=1024 * 1024):
                    if block:
                        size += len(block)
                        if size > MAX_DOWNLOAD:
                            raise gr.Error("Download is over 1 GB. Use local upload instead.")
                        f.write(block)
        except Exception:
            out.unlink(missing_ok=True)
            raise
        if size == 0:
            out.unlink(missing_ok=True)
            raise gr.Error("The link returned an empty video.")
        return str(out)
    except requests.HTTPError as exc:
        raise gr.Error(f"Video download failed: {exc}")
    finally:
        if response is not None:
            response.close()
        session.close()


def run_from_link(url, prompt, clips, length, layout, transcribe, model, credit, progress=gr.Progress()):
    progress(0, desc="Validating video link")
    video_path = download_video(url)
    return generate(video_path, prompt, clips, length, layout, transcribe, model, credit, progress=progress)


def run_from_upload(file_path, prompt, clips, length, layout, transcribe, model, credit, progress=gr.Progress()):
    if not file_path:
        raise gr.Error("Choose a video file.")
    return generate(file_path, prompt, clips, length, layout, transcribe, model, credit, progress=progress)


CSS = """
.gradio-container {max-width:1180px !important; margin:auto !important;}
.hero {text-align:center;padding:30px 10px 18px;}
.hero h1 {font-size:clamp(2.1rem,5vw,3.3rem);background:linear-gradient(100deg,#a78bfa,#38bdf8);color:transparent;background-clip:text;-webkit-background-clip:text;margin:0;}
.hero p {color:#a1a1aa;font-size:1.05rem;}
.card {border:1px solid #393447;border-radius:18px;padding:18px;}
.note {font-size:0.85rem;color:#a1a1aa;}
"""

with gr.Blocks(title="AutoViral AI · Personal Studio", theme=gr.themes.Soft(primary_hue="violet", neutral_hue="slate"), css=CSS) as dashboard:
    gr.HTML('<section class="hero"><h1>✦ AutoViral AI</h1><p>Paste a video file link. Get ready-to-post Shorts. Free, local and private.</p></section>')
    gr.Markdown("🔒 **Your computer does the editing.** No login, subscription or paid AI APIs. Only edit videos you own or have permission to use.")
    with gr.Row(equal_height=False):
        with gr.Column(scale=6):
            gr.Markdown("### ① Add a video")
            with gr.Tabs():
                with gr.Tab("🔗 Paste video link"):
                    link = gr.Textbox(label="Direct video-file URL", placeholder="https://example.com/my-video.mp4", lines=1)
                    gr.Markdown('<span class="note">Press Enter to start automatically. Links must be direct public video files (MP4/MOV/WebM/MKV), not YouTube watch pages.</span>')
                    link_go = gr.Button("✨ Create Shorts from link", variant="primary")
                with gr.Tab("⬆ Upload video"):
                    upload = gr.Video(label="Choose your MP4/MOV video", sources=["upload"], format=None)
                    upload_go = gr.Button("✨ Create Shorts from upload", variant="primary")
            gr.Markdown("### ② Choose editing style")
            prompt = gr.Textbox(label="What should the AI focus on?", value="Find funny reactions and surprising or exciting moments. Make fast-paced 9:16 gaming Shorts with no subtitles.", lines=3)
            with gr.Row():
                clips = gr.Slider(1, 5, value=3, step=1, label="Shorts")
                length = gr.Slider(15, 60, value=30, step=5, label="Duration (seconds)")
            with gr.Accordion("Advanced controls", open=False):
                layout = gr.Radio(["Fill 9:16 (crop sides)", "Fit entire image (no crop)"], value="Fill 9:16 (crop sides)", label="Layout")
                ai = gr.Checkbox(value=True, label="Enable free local Whisper transcription")
                model = gr.Dropdown(["tiny", "base", "small"], value="tiny", label="Speech model")
                credit = gr.Textbox(label="Creator credit (metadata only; no visible watermark)", placeholder="Optional")
        with gr.Column(scale=5):
            gr.Markdown("### ③ Your ready-to-post clips")
            preview = gr.Video(label="Preview first Short")
            downloads = gr.File(label="Download finished MP4s", file_count="multiple")
            report = gr.Markdown("Your titles and captions will appear here after processing.")
            metadata = gr.File(label="Download timestamps and clip metadata")
    gr.Markdown("---\n**What runs automatically?** Once you press Enter on the link field, the backend downloads the authorized direct video file, detects potential highlights, renders vertical clips and prepares basic captions. Keep this local app running until rendering finishes. Ordinary YouTube video links, advanced visual AI editing and automatic posting are not supported yet.")
    shared = [prompt, clips, length, layout, ai, model, credit]
    outputs = [preview, downloads, report, metadata]
    link_go.click(run_from_link, inputs=[link] + shared, outputs=outputs, concurrency_limit=1)
    link.submit(run_from_link, inputs=[link] + shared, outputs=outputs, concurrency_limit=1)
    upload_go.click(run_from_upload, inputs=[upload] + shared, outputs=outputs, concurrency_limit=1)

if __name__ == "__main__":
    dashboard.queue(max_size=8).launch(server_name="127.0.0.1", inbrowser=True, show_error=True, allowed_paths=[str(OUTPUT)])
