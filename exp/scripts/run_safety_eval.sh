#!/bin/bash
# Run HarmBench classifier evaluation on EnumAttack outputs.
# Serves the HarmBench classifier model and runs ASR computation.
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

echo "=== Starting HarmBench classifier server ==="
vllm serve cais/HarmBench-Llama-2-13b-cls \
    --port 8001 \
    --max-model-len 2048 \
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

echo "=== Running HarmBench ASR evaluation ==="
python $PROJ/scripts/run_harmbench_eval.py \
    --endpoint http://localhost:8001/v1 \
    --model cais/HarmBench-Llama-2-13b-cls \
    --harmbench-dir $PROJ/outputs/no_defense_llama31/harmbench \
    --harmbench-prompts $PROJ/data/harmbench_prompts.json \
    --strongreject-dir $PROJ/outputs/no_defense_llama31/strongreject \
    --strongreject-prompts $PROJ/data/strongreject_prompts.json \
    --output $PROJ/results/no_defense_llama31_harmbench_asr.json

echo "=== Stopping classifier server ==="
kill $VLLM_PID 2>/dev/null
wait $VLLM_PID 2>/dev/null || true

echo "=== HarmBench evaluation complete ==="
