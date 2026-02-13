#!/bin/bash
# DeLex-JSON: HarmBench classifier evaluation + StrongREJECT rubric scoring.
# Serves HarmBench classifier on port 8003, classifies DeLex outputs,
# then runs StrongREJECT scoring via MaaS API (no GPU needed).
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

echo "=== Starting HarmBench classifier (port 8003) ==="
vllm serve cais/HarmBench-Llama-2-13b-cls \
    --port 8003 \
    --max-model-len 2048 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
CLS_PID=$!

for i in $(seq 1 180); do
    if curl -s http://localhost:8003/health > /dev/null 2>&1; then
        echo "Classifier ready after ${i}s"
        break
    fi
    if [ $i -eq 180 ]; then
        echo "ERROR: Classifier failed to start"
        kill $CLS_PID 2>/dev/null
        exit 1
    fi
    sleep 5
done

echo "=== Running HarmBench ASR evaluation ==="
python $PROJ/scripts/run_delex_eval.py \
    --cls-endpoint http://localhost:8003/v1 \
    --cls-model cais/HarmBench-Llama-2-13b-cls \
    --harmbench-dir $PROJ/outputs/delex_llama31/harmbench \
    --harmbench-prompts $PROJ/data/harmbench_prompts.json \
    --strongreject-dir $PROJ/outputs/delex_llama31/strongreject \
    --strongreject-prompts $PROJ/data/strongreject_prompts.json \
    --output $PROJ/results/delex_llama31_harmbench_asr.json

echo "=== Stopping classifier ==="
kill $CLS_PID 2>/dev/null
wait $CLS_PID 2>/dev/null || true

echo "=== Running StrongREJECT rubric scoring (via MaaS API) ==="
python $PROJ/scripts/run_delex_strongreject.py \
    --output-dir $PROJ/outputs/delex_llama31/strongreject \
    --prompts $PROJ/data/strongreject_prompts.json \
    --result-output $PROJ/results/delex_llama31_strongreject.json

echo "=== All evaluation complete ==="
