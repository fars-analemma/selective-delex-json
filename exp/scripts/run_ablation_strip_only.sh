#!/bin/bash
# Ablation: strip_only variant -- safety (HarmBench) + utility (GlaiveAI-2K + Github_easy)
PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate
export WANDB_MODE=offline
set -e

BATCH_SIZE=250
MAX_RESTARTS=20
MODE=strip_only

start_server() {
    echo "=== Starting vLLM (attempt $1) ==="
    vllm serve meta-llama/Llama-3.1-8B-Instruct \
        --port 8001 \
        --max-model-len 3072 \
        --gpu-memory-utilization 0.9 \
        --dtype auto &
    SERVER_PID=$!
    for i in $(seq 1 120); do
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            echo "Server ready after ${i}s"
            return 0
        fi
        sleep 5
    done
    echo "ERROR: server timeout"
    kill $SERVER_PID 2>/dev/null
    return 1
}

stop_server() {
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null || true
    sleep 3
}

echo "=== Phase 1: Safety eval ($MODE) ==="
start_server 1 || exit 1

python $PROJ/scripts/run_ablation_experiment.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --prompts $PROJ/data/harmbench_prompts.json \
    --output-dir $PROJ/outputs/ablation_${MODE}/harmbench \
    --delex-mode $MODE \
    --temperature 0.6 --max-tokens 1024

stop_server

echo "=== Phase 2: Utility eval ($MODE) ==="
for restart in $(seq 1 $MAX_RESTARTS); do
    start_server "util-$restart" || exit 1

    set +e
    python $PROJ/scripts/run_ablation_utility.py \
        --endpoint http://localhost:8001/v1 \
        --model meta-llama/Llama-3.1-8B-Instruct \
        --output-dir $PROJ/outputs/ablation_${MODE}/utility \
        --result-output $PROJ/results/ablation_${MODE}_utility.json \
        --delex-mode $MODE \
        --temperature 0.6 --max-tokens 1024 \
        --batch-limit $BATCH_SIZE
    RC=$?
    set -e
    stop_server

    if [ $RC -eq 0 ]; then
        echo "=== Utility eval completed ==="
        break
    elif [ $RC -eq 2 ]; then
        echo "=== Batch limit reached, restarting ==="
        continue
    else
        echo "=== Script failed with code $RC, restarting ==="
        continue
    fi
done

echo "=== $MODE pipeline complete ==="
