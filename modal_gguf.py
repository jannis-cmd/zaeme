"""Private, scale-to-zero Modal server for Zäme's verified Q4 GGUF.

Upload the model to the private ``zaeme-models`` Volume as ``/qwen.gguf``
before deploying. The browser must never call this endpoint directly.
"""

import os
import subprocess
from pathlib import Path

import modal

MODEL_PATH = Path("/models/qwen.gguf")
PORT = 8000
app = modal.App(os.environ.get("ZAEME_MODAL_APP_NAME", "zaeme-qwen"))
volume = modal.Volume.from_name("zaeme-models", create_if_missing=True)

# Pin the CUDA image after smoke-testing it against the exact IdeaPad file.
image = modal.Image.from_registry(
    "ghcr.io/ggml-org/llama.cpp:server-cuda", add_python="3.12"
).entrypoint([])


@app.server(
    image=image,
    gpu="L4",
    volumes={"/models": volume},
    port=PORT,
    routing_region="eu-west",
    compute_region="eu",
    min_containers=0,
    max_containers=2,
    target_concurrency=1,
    max_concurrency=1,
    scaledown_window=60,
    startup_timeout=600,
    # Authenticated by Modal's proxy unless explicitly made public.
)
class QwenServer:
    @modal.enter()
    def start(self):
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(f"Upload the verified model to {MODEL_PATH}")
        subprocess.Popen(
            [
                "/app/llama-server",
                "--model",
                str(MODEL_PATH),
                "--alias",
                "zaeme-qwen",
                "--host",
                "0.0.0.0",
                "--port",
                str(PORT),
                "--ctx-size",
                "8192",
                "--n-gpu-layers",
                "99",
                "--parallel",
                "1",
                "--reasoning",
                "off",
                "--no-webui",
            ]
        )
