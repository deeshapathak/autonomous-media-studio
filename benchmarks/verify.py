"""Verify committed evidence without a GPU or third-party Python dependencies."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "examples/environment/workflow.json": "66b52613ae2c6f5769aa81720e34b6eae9147178005098916d49ea442176d79f",
    "examples/environment/output.mp4": "0359c6a9f2370c6b0dced48c2935cd2c8ca6496424d0ddf6d65aedc93de01a51",
}


def main():
    for name, expected in EXPECTED.items():
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"Hash mismatch: {name}")
        print(f"PASS SHA-256 {name}")
    if not shutil.which("ffprobe"):
        print("SKIP media metadata: install FFprobe to verify")
        return
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                             str(ROOT / "examples/environment/output.mp4")], check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    video = next(s for s in data["streams"] if s["codec_type"] == "video")
    audio = next(s for s in data["streams"] if s["codec_type"] == "audio")
    if (video["width"], video["height"], video["r_frame_rate"], video["nb_frames"], video["codec_name"]) != (352, 608, "24/1", "124", "h264"):
        raise SystemExit("Unexpected video metadata")
    if (audio["codec_name"], audio["channels"], audio["sample_rate"]) != ("aac", 2, "32000"):
        raise SystemExit("Unexpected audio metadata")
    if abs(float(data["format"]["duration"]) - 5.167) > 0.001:
        raise SystemExit("Unexpected duration")
    print("PASS media metadata")


if __name__ == "__main__":
    main()
