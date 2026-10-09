# Demo walkthrough

## A two-minute reviewer tour

1. Open `examples/environment/output.mp4` and play it with sound. The clip is the original local output, not a newly staged demo.
2. Open `examples/environment/workflow.json`: inspect the prompt, seed 170911, dimensions 352 × 608, length 124, and 12 steps.
3. Run `media-studio plan`. Explain that editor metadata is removed before submission, and optional seed/prompt changes are explicit.
4. Show `src/media_studio/pipeline.py`: successful completion, execution failure, missing output, and timeout are separate cases. Submission is never automatically retried.
5. Run `python benchmarks/verify.py` to connect the files to their recorded checksums.

No screen recording of these steps is included. The video itself is a verified generated artifact.

## Local rendering prerequisites

Use a separately installed ComfyUI server with the following classes available: `VAELoader`, `UNETLoader`, `CLIPLoader`, `MiniMaxH3ImageToVideo`, `RandomNoise`, `KSamplerSelect`, `BasicScheduler`, `BasicGuider`, `SamplerCustomAdvanced`, `VAEDecode`, `VAEDecodeAudio`, `CreateVideo`, and `SaveVideo`.

The historical graph selects these exact files:

- `minimax_h3_video_vae_fp16.safetensors`
- `minimax_h3_audio_vae_fp32.safetensors`
- `minimax_h3_fl2va_pruned_int8_convrot.safetensors`
- `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`

Model installation and license acceptance are outside this package. This repository does not download them. Match filenames against your own installation and run preflight before rendering. Renaming a different model to match is not sufficient.

The historical environment did not preserve a complete dependency lock or ComfyUI commit alongside the report. Therefore these instructions are a compatibility check for an existing local installation, not a claim of a reproducible clean-machine installation. A seed alone does not ensure identical output across GPU/runtime versions. Preflight checks class presence and loader choices; it does not prove sufficient GPU memory or all input-schema compatibility.

From the repository root:

```sh
python -m pip install -e .
media-studio preflight
media-studio render --out runs/demo-001 --timeout 2700
```

Inspect `runs/demo-001/manifest.json` and play every returned MP4 before using it. Client wall time includes queueing, execution, polling delay, and transfer. It is not isolated model inference time. The wrapper accepts loopback endpoints only; it is intended for a single-user local ComfyUI setup.

For a new benchmark, record hardware, software versions, model hashes, warm/cold state, queue state, workflow hash, and repeated trials. Collect peak GPU memory separately. Do not compare the historical single run with an unqualified new number.
