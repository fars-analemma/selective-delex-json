#!/bin/bash
# HarmBench classifier eval for all 3 ablation variants.
set -e
PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate
export WANDB_MODE=offline

echo "=== Starting HarmBench classifier ==="
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
        echo "ERROR: classifier timeout"
        kill $CLS_PID 2>/dev/null
        exit 1
    fi
    sleep 5
done

for MODE in strip_only delex_all heuristic_only; do
    HARMBENCH_DIR=$PROJ/outputs/ablation_${MODE}/harmbench
    if [ ! -d "$HARMBENCH_DIR" ] || [ -z "$(ls $HARMBENCH_DIR/*.json 2>/dev/null)" ]; then
        echo "=== Skipping $MODE (no outputs found) ==="
        continue
    fi

    echo "=== Evaluating $MODE ==="
    python $PROJ/scripts/run_delex_eval.py \
        --cls-endpoint http://localhost:8003/v1 \
        --cls-model cais/HarmBench-Llama-2-13b-cls \
        --harmbench-dir $HARMBENCH_DIR \
        --harmbench-prompts $PROJ/data/harmbench_prompts.json \
        --strongreject-dir $HARMBENCH_DIR \
        --strongreject-prompts $PROJ/data/harmbench_prompts.json \
        --output $PROJ/results/ablation_${MODE}_harmbench_asr.json
done

kill $CLS_PID 2>/dev/null
wait $CLS_PID 2>/dev/null || true

echo "=== Classifier eval complete for all variants ==="
