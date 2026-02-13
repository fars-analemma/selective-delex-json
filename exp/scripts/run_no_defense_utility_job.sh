#!/bin/bash
# Job B: No-defense utility baseline on Glaiveai2K + Github_easy.
# Uses outlines backend to avoid xgrammar memory leak crash.
PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

echo "=== Starting Llama-3.1-8B-Instruct (outlines backend, port 8001) ==="
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --port 8001 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto \
    --structured-outputs-config '{"backend":"outlines"}' &
TARGET_PID=$!

for i in $(seq 1 180); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "Server ready after ${i}s"
        break
    fi
    [ $i -eq 180 ] && { echo "ERROR: server start timeout"; kill $TARGET_PID 2>/dev/null; exit 1; }
    sleep 5
done

echo "=== No-defense utility baseline ==="
python $PROJ/scripts/run_no_defense_utility.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --output-dir $PROJ/outputs/no_defense_llama31/utility \
    --result-output $PROJ/results/no_defense_llama31_utility.json \
    --temperature 0.6 \
    --max-tokens 1024
UTIL_RC=$?

kill $TARGET_PID 2>/dev/null
wait $TARGET_PID 2>/dev/null || true

echo "=== Job B complete ==="
echo "Utility exit code: $UTIL_RC"
echo "No-def Glaiveai2K: $(ls $PROJ/outputs/no_defense_llama31/utility/Glaiveai2K/*.json 2>/dev/null | wc -l)"
echo "No-def Github_easy: $(ls $PROJ/outputs/no_defense_llama31/utility/Github_easy/*.json 2>/dev/null | wc -l)"
