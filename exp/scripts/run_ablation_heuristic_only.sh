#!/bin/bash
# Ablation: heuristic_only variant -- safety only (utility identical to full DeLex-JSON)
set -e
PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate
export WANDB_MODE=offline

MODE=heuristic_only

echo "=== Starting vLLM ==="
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --port 8001 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
SERVER_PID=$!

for i in $(seq 1 120); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "Server ready after ${i}s"
        break
    fi
    if [ $i -eq 120 ]; then
        echo "ERROR: server timeout"
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
    sleep 5
done

echo "=== Safety eval ($MODE) ==="
python $PROJ/scripts/run_ablation_experiment.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --prompts $PROJ/data/harmbench_prompts.json \
    --output-dir $PROJ/outputs/ablation_${MODE}/harmbench \
    --delex-mode $MODE \
    --temperature 0.6 --max-tokens 1024

kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null || true

echo "=== $MODE safety pipeline complete ==="
echo "Note: utility eval skipped -- identical to full DeLex-JSON method"
