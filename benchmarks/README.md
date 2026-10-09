# Evidence, not a performance leaderboard

The original local benchmark report dated August 11, 2026 recorded the following:

| Field | Historical record |
| --- | --- |
| GPU | NVIDIA GeForce RTX 5070 Ti 16 GB |
| Runtime | 96.03 seconds |
| Workflow SHA-256 | `66b52613ae2c6f5769aa81720e34b6eae9147178005098916d49ea442176d79f` |
| MP4 SHA-256 | `0359c6a9f2370c6b0dced48c2935cd2c8ca6496424d0ddf6d65aedc93de01a51` |

During curation, both hashes were recomputed and matched the report. FFprobe confirmed 352 × 608 H.264 video, 124 frames at 24 fps, duration 5.167 seconds, and AAC stereo at 32 kHz. FFmpeg decoded the full file without errors. The machine-readable probe is in `media-probe.json`.

The raw timing trace for the 96.03-second run was not found. That number is retained only as a **historical reported measurement**, not an independently reproduced benchmark or necessarily pure inference time. GPU capacity is not measured peak VRAM. There are no repeated trials, warm/cold breakdown, peak-memory observations, or quality-rate statistics in this release.

Run `python benchmarks/verify.py` from the repository root to verify hashes and, when FFprobe is available, the media metadata. This script makes no model calls and measures no inference performance.
