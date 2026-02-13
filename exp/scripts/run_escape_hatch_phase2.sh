#!/bin/bash
# Phase 2: Resume utility eval + HarmBench classifier eval.
# Uses 2 GPUs: GPU 0 for target model (utility), GPU 1 for classifier.
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate
cd $PROJ

echo "=== Starting Llama-3.1-8B-Instruct (port 8001, GPU 0) ==="
CUDA_VISIBLE_DEVICES=0 vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --port 8001 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
TARGET_PID=$!

echo "=== Starting HarmBench classifier (port 8003, GPU 1) ==="
CUDA_VISIBLE_DEVICES=1 vllm serve cais/HarmBench-Llama-2-13b-cls \
    --port 8003 \
    --max-model-len 2048 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
CLS_PID=$!

echo "=== Waiting for target server ==="
for i in $(seq 1 180); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "Target server ready after ${i}s"
        break
    fi
    if [ $i -eq 180 ]; then
        echo "ERROR: Target server failed to start"
        kill $TARGET_PID $CLS_PID 2>/dev/null
        exit 1
    fi
    sleep 5
done

echo "=== Waiting for classifier server ==="
for i in $(seq 1 180); do
    if curl -s http://localhost:8003/health > /dev/null 2>&1; then
        echo "Classifier ready after ${i}s"
        break
    fi
    if [ $i -eq 180 ]; then
        echo "ERROR: Classifier failed to start"
        kill $TARGET_PID $CLS_PID 2>/dev/null
        exit 1
    fi
    sleep 5
done

echo "=== Resuming utility eval on JSONSchemaBench (Github_easy) ==="
python $PROJ/scripts/run_escape_hatch_utility.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --output-dir $PROJ/outputs/escape_hatch_llama31/utility \
    --result-output $PROJ/results/escape_hatch_llama31_utility.json \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Stopping target server ==="
kill $TARGET_PID 2>/dev/null
wait $TARGET_PID 2>/dev/null || true

echo "=== Running HarmBench ASR evaluation ==="
python $PROJ/scripts/run_escape_hatch_eval.py \
    --cls-endpoint http://localhost:8003/v1 \
    --cls-model cais/HarmBench-Llama-2-13b-cls \
    --harmbench-dir $PROJ/outputs/escape_hatch_llama31/harmbench \
    --harmbench-prompts $PROJ/data/harmbench_prompts.json \
    --strongreject-dir $PROJ/outputs/escape_hatch_llama31/strongreject \
    --strongreject-prompts $PROJ/data/strongreject_prompts.json \
    --output $PROJ/results/escape_hatch_llama31_harmbench_asr.json

echo "=== Stopping classifier ==="
kill $CLS_PID 2>/dev/null
wait $CLS_PID 2>/dev/null || true

echo "=== Running StrongREJECT rubric scoring ==="
python $PROJ/scripts/run_escape_hatch_strongreject.py \
    --output-dir $PROJ/outputs/escape_hatch_llama31/strongreject \
    --prompts $PROJ/data/strongreject_prompts.json \
    --result-output $PROJ/results/escape_hatch_llama31_strongreject.json

echo "=== All phases complete ==="
