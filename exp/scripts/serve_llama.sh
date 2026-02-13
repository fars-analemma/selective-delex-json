#!/bin/bash
# Serve Llama-3.1-8B-Instruct via vLLM for EnumAttack generation.
source /mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp/.venv/bin/activate

vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --port 8001 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto
