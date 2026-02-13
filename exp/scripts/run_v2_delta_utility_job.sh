#!/bin/bash
# Re-generate utility outputs for the 53 schemas where v1 modified but v2 doesn't.
# Then compute combined v2 utility and paired comparison.
PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

echo "=== Starting vLLM server ==="
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
    sleep 5
done

if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "ERROR: server timeout"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "=== Running v2 delta utility eval (53 schemas) ==="
python $PROJ/scripts/run_v2_delta_utility.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --fpr-v1 $PROJ/results/delex_llama31_fpr.json \
    --fpr-v2 $PROJ/results/delex_llama31_fpr_v2.json \
    --v1-output-dir $PROJ/outputs/delex_llama31/utility \
    --v2-output-dir $PROJ/outputs/delex_v2_delta_llama31/utility \
    --result-output $PROJ/results/delex_v2_delta_llama31_utility.json \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Stopping server ==="
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null || true

echo "=== Computing combined v2 utility ==="
python $PROJ/scripts/compute_v2_utility.py \
    --fpr-v1 $PROJ/results/delex_llama31_fpr.json \
    --fpr-v2 $PROJ/results/delex_llama31_fpr_v2.json \
    --v1-output-dir $PROJ/outputs/delex_llama31/utility \
    --v2-delta-dir $PROJ/outputs/delex_v2_delta_llama31/utility \
    --nodef-output-dir $PROJ/outputs/no_defense_llama31/utility \
    --result-output $PROJ/results/delex_v2_llama31_utility.json

echo "=== Job complete ==="
