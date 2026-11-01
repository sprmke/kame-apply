# Spike 5: fastembed on ARM

**Date:** 2026-10-28 · **Decision: KEEP (re-time on the VM)** · Model `BAAI/bge-small-en-v1.5` (384-dim), Apple Silicon laptop, batch 32.

| Metric | Result |
| --- | --- |
| Model download + load | 14.2 s (first run, cached afterwards) |
| 1,000 job-description-sized texts (~180 words) | 19.7 s, ~51 texts/s |
| Peak RSS | ~800 MB |

Planning numbers for a 2-OCPU Neoverse VM: assume 3-5x slower, so ~10-17 texts/s, i.e. 1,000 jobs in 1-2 minutes. That is fine for background embedding in DBOS steps (queue concurrency 1-2) and not fine on the request path. 800 MB RSS means the embedding worker should be a separate, lazily loaded process or a DBOS-queue-limited step so it does not sit beside Chromium on a 12 GB VM at the same time. `onnxruntime` has a linux aarch64 wheel. Re-run on the VM (spike 2) and set the batch size from the result.
