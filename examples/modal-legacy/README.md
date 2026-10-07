# Legacy Modal prototype

This earlier Hearth/Qwen/ElevenLabs experiment is preserved for reference. It is **not connected to the current Zäme interface** and does not use its current communication prompt or multi-person workflow.

- `backend.py`: standalone Modal API.
- `evaluate.py` and `eval_cases.json`: fictional dialogue examples for manual review.

The current optional Modal inference server is [`modal_gguf.py`](../../modal_gguf.py). Main-app setup is documented in the [development guide](../../docs/DEVELOPMENT.md).

Do not deploy this legacy example publicly without a security and privacy review. It uses a shared `HEARTH_ACCESS_CODE`, broad CORS and in-memory limits, not production user authentication or durable quotas. Credentials belong in your own private Modal secret, never in source files. These examples do not establish clinical efficacy.
