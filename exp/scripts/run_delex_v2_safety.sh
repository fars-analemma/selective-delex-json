#!/bin/bash
# DeLex-JSON v2 safety pipeline: re-run with conjunction-based suspicion function.
# Phase 1: Serve Llama-3.1-8B, run DeLex attack on HarmBench + StrongREJECT
# Phase 2: Swap to HarmBench classifier, run ASR eval
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate
export WANDB_MODE=offline

echo "=== Phase 1a: Starting Llama-3.1-8B-Instruct (port 8001) ==="
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --port 8001 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
TARGET_PID=$!

echo "=== Waiting for target server ==="
for i in $(seq 1 180); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "Target server ready after ${i}s"
        break
    fi
    if [ $i -eq 180 ]; then
        echo "ERROR: Target server failed to start within 180s"
        kill $TARGET_PID 2>/dev/null
        exit 1
    fi
    sleep 5
done

echo "=== Phase 1b: Running DeLex-JSON v2 experiment on HarmBench ==="
python $PROJ/scripts/run_delex_experiment.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --prompts $PROJ/data/harmbench_prompts.json \
    --output-dir $PROJ/outputs/delex_v2_llama31/harmbench \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Phase 1c: Running DeLex-JSON v2 experiment on StrongREJECT ==="
python $PROJ/scripts/run_delex_experiment.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --prompts $PROJ/data/strongreject_prompts.json \
    --output-dir $PROJ/outputs/delex_v2_llama31/strongreject \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Stopping target server ==="
kill $TARGET_PID 2>/dev/null
wait $TARGET_PID 2>/dev/null || true
sleep 5

echo "=== Phase 2: Starting HarmBench classifier (port 8003) ==="
vllm serve cais/HarmBench-Llama-2-13b-cls \
    --port 8003 \
    --max-model-len 2048 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
CLS_PID=$!

echo "=== Waiting for classifier ==="
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

echo "=== Phase 2: Running HarmBench ASR evaluation ==="
python $PROJ/scripts/run_delex_eval.py \
    --cls-endpoint http://localhost:8003/v1 \
    --cls-model cais/HarmBench-Llama-2-13b-cls \
    --harmbench-dir $PROJ/outputs/delex_v2_llama31/harmbench \
    --harmbench-prompts $PROJ/data/harmbench_prompts.json \
    --strongreject-dir $PROJ/outputs/delex_v2_llama31/strongreject \
    --strongreject-prompts $PROJ/data/strongreject_prompts.json \
    --output $PROJ/results/delex_v2_llama31_harmbench_asr.json

echo "=== Stopping classifier ==="
kill $CLS_PID 2>/dev/null
wait $CLS_PID 2>/dev/null || true

echo "=== Safety pipeline complete ==="
echo "HarmBench outputs: $(ls $PROJ/outputs/delex_v2_llama31/harmbench/*.json 2>/dev/null | wc -l)"
echo "StrongREJECT outputs: $(ls $PROJ/outputs/delex_v2_llama31/strongreject/*.json 2>/dev/null | wc -l)"
echo "ASR results: $PROJ/results/delex_v2_llama31_harmbench_asr.json"
