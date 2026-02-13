#!/bin/bash
# Full pipeline: input guard defense against EnumAttack + HarmBench eval.
# Requires 4 GPUs: GPU0=LlamaGuard, GPU1=Llama-3.1-8B, GPU2=HarmBench classifier.
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

echo "=== Phase 1: Starting Llama Guard 3 (port 8002, GPU 0) ==="
CUDA_VISIBLE_DEVICES=0 vllm serve meta-llama/Llama-Guard-3-8B \
    --port 8002 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
GUARD_PID=$!

echo "=== Phase 1: Starting Llama-3.1-8B-Instruct (port 8001, GPU 1) ==="
CUDA_VISIBLE_DEVICES=1 vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --port 8001 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
TARGET_PID=$!

echo "=== Waiting for servers to be ready ==="
for i in $(seq 1 180); do
    GUARD_OK=false
    TARGET_OK=false
    curl -s http://localhost:8002/health > /dev/null 2>&1 && GUARD_OK=true
    curl -s http://localhost:8001/health > /dev/null 2>&1 && TARGET_OK=true
    if $GUARD_OK && $TARGET_OK; then
        echo "Both servers ready after ${i}s"
        break
    fi
    if [ $i -eq 180 ]; then
        echo "ERROR: Servers failed to start within 180s"
        echo "Guard: $GUARD_OK, Target: $TARGET_OK"
        kill $GUARD_PID $TARGET_PID 2>/dev/null
        exit 1
    fi
    sleep 5
done

echo "=== Phase 2: Running input guard experiment on HarmBench ==="
python $PROJ/scripts/run_input_guard_experiment.py \
    --target-endpoint http://localhost:8001/v1 \
    --target-model meta-llama/Llama-3.1-8B-Instruct \
    --guard-endpoint http://localhost:8002/v1 \
    --guard-model meta-llama/Llama-Guard-3-8B \
    --prompts $PROJ/data/harmbench_prompts.json \
    --output-dir $PROJ/outputs/input_guard_llama31/harmbench \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Phase 2: Running input guard experiment on StrongREJECT ==="
python $PROJ/scripts/run_input_guard_experiment.py \
    --target-endpoint http://localhost:8001/v1 \
    --target-model meta-llama/Llama-3.1-8B-Instruct \
    --guard-endpoint http://localhost:8002/v1 \
    --guard-model meta-llama/Llama-Guard-3-8B \
    --prompts $PROJ/data/strongreject_prompts.json \
    --output-dir $PROJ/outputs/input_guard_llama31/strongreject \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Phase 3: Running false positive rate evaluation ==="
python $PROJ/scripts/run_input_guard_fpr.py \
    --guard-endpoint http://localhost:8002/v1 \
    --guard-model meta-llama/Llama-Guard-3-8B \
    --output $PROJ/results/input_guard_llama31_fpr.json

echo "=== Stopping guard and target servers ==="
kill $GUARD_PID $TARGET_PID 2>/dev/null
wait $GUARD_PID 2>/dev/null || true
wait $TARGET_PID 2>/dev/null || true

echo "=== Phase 4: Starting HarmBench classifier (port 8003, GPU 2) ==="
CUDA_VISIBLE_DEVICES=2 vllm serve cais/HarmBench-Llama-2-13b-cls \
    --port 8003 \
    --max-model-len 2048 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
CLS_PID=$!

echo "=== Waiting for classifier to be ready ==="
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

echo "=== Phase 5: Running HarmBench ASR evaluation ==="
python $PROJ/scripts/run_input_guard_eval.py \
    --cls-endpoint http://localhost:8003/v1 \
    --cls-model cais/HarmBench-Llama-2-13b-cls \
    --harmbench-dir $PROJ/outputs/input_guard_llama31/harmbench \
    --harmbench-prompts $PROJ/data/harmbench_prompts.json \
    --strongreject-dir $PROJ/outputs/input_guard_llama31/strongreject \
    --strongreject-prompts $PROJ/data/strongreject_prompts.json \
    --output $PROJ/results/input_guard_llama31_harmbench_asr.json

echo "=== Stopping classifier server ==="
kill $CLS_PID 2>/dev/null
wait $CLS_PID 2>/dev/null || true

echo "=== Pipeline complete ==="
echo "HarmBench outputs: $(ls $PROJ/outputs/input_guard_llama31/harmbench/*.json 2>/dev/null | wc -l)"
echo "StrongREJECT outputs: $(ls $PROJ/outputs/input_guard_llama31/strongreject/*.json 2>/dev/null | wc -l)"
