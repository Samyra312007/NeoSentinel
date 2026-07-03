# vLLM Worker Template

Production inference worker for NeoSentinel on ARM Graviton4 with KleidiAI-accelerated GEMM kernels.

## Model

- **Model:** Llama 3.2 7B Instruct
- **Quantization:** INT4 (AWQ)
- **Endpoints:** `/v1/completions`, `/metrics`, `/health`

## KleidiAI Build Flags (Graviton4 / c8g)

Build vLLM from source on Ubuntu 24.04 ARM64 with KleidiAI enabled:

```bash
export CMAKE_ARGS="-DGGML_KLEIDIAI=ON -DGGML_NATIVE=ON"
export VLLM_TARGET_DEVICE=cpu
pip install vllm --no-binary vllm \
  --config-settings="--build-option=--cmake-args=${CMAKE_ARGS}"
```

Runtime flags for SVE2-optimized CPU inference:

```bash
export OPENBLAS_CORETYPE=ARMV8SVE
export VLLM_CPU_KVCACHE_SPACE=4
export VLLM_USE_KLEIDIAI=1
```

## Local Development

Use the lightweight mock worker (no GPU/ARM required):

```bash
docker build -f Dockerfile.mock -t neosentinel-vllm-mock .
docker run -p 8000:8000 -e NODE_ID=node-001 neosentinel-vllm-mock
```

## Production (Graviton4)

```bash
docker build -f Dockerfile -t neosentinel-vllm .
docker run --platform linux/arm64 -p 8000:8000 \
  -e VLLM_MODEL=meta-llama/Llama-3.2-7B-Instruct \
  neosentinel-vllm
```
