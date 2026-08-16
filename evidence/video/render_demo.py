from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
FRAMES = ROOT / "frames"
AUDIO = ROOT / "audio" / "memoryforge-narration.wav"
OUTPUT = ROOT / "render" / "memoryforge-demo.mp4"
SILENT = ROOT / "render" / "memoryforge-demo-silent.mp4"
WIDTH, HEIGHT, FPS = 1920, 1080, 24
GREEN, CYAN, WHITE, MUTED = "#68F7A8", "#60D8FF", "#F5F7FA", "#9AA8B7"
BG, PANEL = "#071016", "#101820"
MEMORY_ID = "c7a7eb57-dd10-4163-8618-88c9232c2678"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / ("segoeuib.ttf" if bold else "segoeui.ttf")), size)


def fit(draw, text, width, size, bold=False):
    f, lines, current = font(size, bold), [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=f)[2] <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines, f


def background(source):
    canvas = source.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(30))
    canvas = ImageEnhance.Brightness(canvas).enhance(0.18).convert("RGBA")
    return Image.alpha_composite(canvas, Image.new("RGBA", canvas.size, (2, 9, 14, 160)))


def scene(image_name, eyebrow, title, rows, accent=GREEN):
    source = Image.open(FRAMES / image_name).convert("RGB")
    canvas = background(source)
    shot = source.resize((1040, 585), Image.Resampling.LANCZOS)
    canvas.paste(shot, (70, 250))
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((1145, 90, 1850, 990), 28, fill=PANEL, outline="#29404F", width=2)
    d.text((90, 75), eyebrow.upper(), font=font(27, True), fill=accent)
    title_lines, tf = fit(d, title, 980, 56, True)
    yy = 118
    for line in title_lines:
        d.text((90, yy), line, font=tf, fill=WHITE)
        yy += 64
    yy = 155
    for label, value in rows:
        d.text((1200, yy), label.upper(), font=font(21, True), fill=MUTED)
        values, vf = fit(d, value, 575, 31, True)
        vy = yy + 32
        for line in values:
            d.text((1200, vy), line, font=vf, fill=accent if label in {"Result", "Action", "Proof"} else WHITE)
            vy += 42
        yy = vy + 38
    return canvas.convert("RGB")


def proof_scene():
    source = Image.open(FRAMES / "aws-proof.png").convert("RGB")
    canvas = background(source)
    d = ImageDraw.Draw(canvas)
    d.text((80, 55), "REAL AWS LAMBDA + COCKROACHDB PROOF", font=font(48, True), fill=WHITE)
    d.text((82, 115), "The same CockroachDB memory ID changes Run 2", font=font(27), fill=CYAN)
    shot = source.resize((1500, 844), Image.Resampling.LANCZOS)
    canvas.paste(shot, (45, 190))
    d.rectangle((45, 190, 1545, 305), fill="#071016")
    d.text((75, 225), "AWS CloudShell · Lambda us-east-1 · CockroachDB Cloud", font=font(28, True), fill=WHITE)
    d.rounded_rectangle((1580, 190, 1870, 1034), 22, fill=PANEL, outline="#29404F", width=2)
    items = [("RUN 1", "FAILED"), ("WRITE", MEMORY_ID[:8]), ("RUN 2", "SUCCESS"), ("ACTION", "CHANGED"), ("CHECK", "TRUE")]
    yy = 245
    for label, value in items:
        d.text((1625, yy), label, font=font(20, True), fill=MUTED)
        d.text((1625, yy + 34), value, font=font(32, True), fill=GREEN)
        yy += 145
    return canvas.convert("RGB")


SCENES = [
    (0, 9, scene("app-initial.png", "Persistent agent memory", "An agent should not repeat the same failure twice.", [("Task", "Deploy and verify health"), ("Stack", "AWS Lambda · Bedrock · CockroachDB")], CYAN)),
    (9, 25, scene("app-failure.png", "Run 1", "The default strategy fails.", [("Strategy", "synchronous_deployment"), ("Outcome", "execution timeout"), ("Result", "FAILURE MEMORY CREATED")], "#FF747B")),
    (25, 43, scene("app-failure.png", "CockroachDB write", "Lambda persists a structured, vector-searchable failure.", [("Stored", "task · decision · outcome · reasoning"), ("Embedding", "Bedrock Titan v2 · 1024 dimensions"), ("Memory ID", MEMORY_ID)], GREEN)),
    (43, 61, scene("app-success.png", "CockroachDB vector recall", "Run 2 retrieves the exact failure memory.", [("Recalled ID", MEMORY_ID), ("Relevance", "confident and actionable"), ("Proof", "adapted_from_memory matches")], CYAN)),
    (61, 80, scene("app-success.png", "Changed action", "The recalled failure changes the next plan.", [("Before", "synchronous_deployment"), ("Action", "async_job_with_health_check"), ("Result", "RUN 2 SUCCESS")], GREEN)),
    (80, 102, proof_scene()),
    (102, 140, scene("app-success.png", "Reproducible submission", "Install, schema, local run, and Lambda deployment are documented.", [("Security", "TLS verified · parameterized SQL"), ("AWS", "reserved concurrency: 2"), ("Proof", "FAIL → WRITE → RECALL → ADAPT → SUCCESS")], GREEN)),
]


def frames():
    for index in range(SCENES[-1][1] * FPS):
        second = index / FPS
        si = next(i for i, (_, end, _) in enumerate(SCENES) if second < end)
        start, _, image = SCENES[si]
        if si and second - start < 0.45:
            image = Image.blend(SCENES[si - 1][2], image, (second - start) / 0.45)
        yield image.tobytes()


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    writer = imageio_ffmpeg.write_frames(str(SILENT), (WIDTH, HEIGHT), fps=FPS, codec="libx264", pix_fmt_in="rgb24", macro_block_size=1, output_params=["-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p"])
    writer.send(None)
    for frame in frames():
        writer.send(frame)
    writer.close()
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-y", "-i", str(SILENT), "-i", str(AUDIO), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(OUTPUT)], check=True)
    with wave.open(str(AUDIO), "rb") as wav:
        print(f"audio_seconds={wav.getnframes() / wav.getframerate():.2f}")
    print(OUTPUT)


if __name__ == "__main__":
    main()
