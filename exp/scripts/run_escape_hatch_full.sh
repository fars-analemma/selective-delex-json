#!/bin/bash
# Full pipeline: escape-hatch defense against EnumAttack + eval.
# Phase 1-2: escape-hatch + constrained decoding (1 GPU for target model)
# Phase 3: Utility evaluation on JSONSchemaBench (same server)
# Phase 4: HarmBench classifier eval (1 GPU)
# Phase 5: StrongREJECT rubric scoring (API only, no GPU)
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

echo "=== Phase 1: Starting Llama-3.1-8B-Instruct (port 8001, GPU 0) ==="
CUDA_VISIBLE_DEVICES=0 vllm serve meta-llama/Llama-3.1-8B-Instruct \
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

echo "=== Phase 2a: Running escape-hatch experiment on HarmBench ==="
python $PROJ/scripts/run_escape_hatch_experiment.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --prompts $PROJ/data/harmbench_prompts.json \
    --output-dir $PROJ/outputs/escape_hatch_llama31/harmbench \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Phase 2b: Running escape-hatch experiment on StrongREJECT ==="
python $PROJ/scripts/run_escape_hatch_experiment.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --prompts $PROJ/data/strongreject_prompts.json \
    --output-dir $PROJ/outputs/escape_hatch_llama31/strongreject \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Phase 3: Running utility eval on JSONSchemaBench ==="
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

echo "=== Phase 4: Starting HarmBench classifier (port 8003, GPU 0) ==="
CUDA_VISIBLE_DEVICES=0 vllm serve cais/HarmBench-Llama-2-13b-cls \
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

echo "=== Phase 4: Running HarmBench ASR evaluation ==="
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

echo "=== Phase 5: Running StrongREJECT rubric scoring ==="
python $PROJ/scripts/run_escape_hatch_strongreject.py \
    --output-dir $PROJ/outputs/escape_hatch_llama31/strongreject \
    --prompts $PROJ/data/strongreject_prompts.json \
    --result-output $PROJ/results/escape_hatch_llama31_strongreject.json

echo "=== Pipeline complete ==="
echo "HarmBench outputs: $(ls $PROJ/outputs/escape_hatch_llama31/harmbench/*.json 2>/dev/null | wc -l)"
echo "StrongREJECT outputs: $(ls $PROJ/outputs/escape_hatch_llama31/strongreject/*.json 2>/dev/null | wc -l)"
echo "Utility outputs: $(find $PROJ/outputs/escape_hatch_llama31/utility -name '*.json' 2>/dev/null | wc -l)"
