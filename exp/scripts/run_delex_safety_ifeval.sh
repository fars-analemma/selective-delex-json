#!/bin/bash
# DeLex-JSON safety evaluation + IFEval (short job, ~25 min).
# Serves Llama-3.1-8B-Instruct, runs EnumAttack with DeLex on both datasets, then IFEval.
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

echo "=== Starting Llama-3.1-8B-Instruct (port 8001) ==="
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --port 8001 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
TARGET_PID=$!

for i in $(seq 1 180); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "Server ready after ${i}s"
        break
    fi
    if [ $i -eq 180 ]; then
        echo "ERROR: Server failed to start"
        kill $TARGET_PID 2>/dev/null
        exit 1
    fi
    sleep 5
done

echo "=== Running DeLex-JSON on HarmBench (159 prompts) ==="
python $PROJ/scripts/run_delex_experiment.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --prompts $PROJ/data/harmbench_prompts.json \
    --output-dir $PROJ/outputs/delex_llama31/harmbench \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Running DeLex-JSON on StrongREJECT (313 prompts) ==="
python $PROJ/scripts/run_delex_experiment.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --prompts $PROJ/data/strongreject_prompts.json \
    --output-dir $PROJ/outputs/delex_llama31/strongreject \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Running IFEval JSON subset ==="
python $PROJ/scripts/run_delex_ifeval.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --result-output $PROJ/results/delex_ifeval_llama31.json \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Stopping server ==="
kill $TARGET_PID 2>/dev/null
wait $TARGET_PID 2>/dev/null || true

echo "=== Done ==="
echo "HarmBench outputs: $(ls $PROJ/outputs/delex_llama31/harmbench/*.json 2>/dev/null | wc -l)"
echo "StrongREJECT outputs: $(ls $PROJ/outputs/delex_llama31/strongreject/*.json 2>/dev/null | wc -l)"
