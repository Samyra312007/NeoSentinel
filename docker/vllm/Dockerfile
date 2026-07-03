FROM vllm/vllm-openai:latest

ENV VLLM_MODEL=meta-llama/Llama-3.2-7B-Instruct
ENV VLLM_QUANTIZATION=awq
ENV VLLM_DTYPE=int4
ENV VLLM_MAX_MODEL_LEN=4096
ENV VLLM_GPU_MEMORY_UTILIZATION=0.90

EXPOSE 8000

CMD [
  "python", "-m", "vllm.entrypoints.openai.api_server",
  "--model", "${VLLM_MODEL}",
  "--quantization", "awq",
  "--dtype", "int4",
  "--max-model-len", "4096",
  "--port", "8000",
  "--served-model-name", "llama-3.2-7b-int4"
]
