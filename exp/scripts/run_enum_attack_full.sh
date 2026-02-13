#!/bin/bash
# Full pipeline: serve Llama-3.1-8B-Instruct, run EnumAttack on both datasets.
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

echo "=== Starting vLLM server ==="
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --port 8001 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
VLLM_PID=$!

echo "=== Waiting for server to be ready ==="
for i in $(seq 1 120); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "Server ready after ${i}s"
        break
    fi
    sleep 5
done

if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "ERROR: Server failed to start"
    kill $VLLM_PID 2>/dev/null
    exit 1
fi

echo "=== Running EnumAttack on HarmBench ==="
python $PROJ/scripts/run_enum_attack.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --prompts $PROJ/data/harmbench_prompts.json \
    --output-dir $PROJ/outputs/no_defense_llama31/harmbench \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Running EnumAttack on StrongREJECT ==="
python $PROJ/scripts/run_enum_attack.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --prompts $PROJ/data/strongreject_prompts.json \
    --output-dir $PROJ/outputs/no_defense_llama31/strongreject \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Stopping vLLM server ==="
kill $VLLM_PID 2>/dev/null
wait $VLLM_PID 2>/dev/null || true

echo "=== EnumAttack generation complete ==="
echo "HarmBench outputs: $(ls $PROJ/outputs/no_defense_llama31/harmbench/*.json 2>/dev/null | wc -l)"
echo "StrongREJECT outputs: $(ls $PROJ/outputs/no_defense_llama31/strongreject/*.json 2>/dev/null | wc -l)"
