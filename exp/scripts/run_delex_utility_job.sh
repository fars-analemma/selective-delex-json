#!/bin/bash
# Job A: Complete DeLex utility eval (Github_easy remaining) + IFEval.
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

echo "=== DeLex utility eval (resumes from cached outputs) ==="
python $PROJ/scripts/run_delex_utility.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --output-dir $PROJ/outputs/delex_llama31/utility \
    --result-output $PROJ/results/delex_llama31_utility.json \
    --temperature 0.6 \
    --max-tokens 1024
DELEX_RC=$?

echo "=== IFEval JSON subset eval ==="
python $PROJ/scripts/run_delex_ifeval.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --result-output $PROJ/results/delex_ifeval_llama31.json \
    --temperature 0.6 \
    --max-tokens 1024
IFEVAL_RC=$?

kill $TARGET_PID 2>/dev/null
wait $TARGET_PID 2>/dev/null || true

echo "=== Job A complete ==="
echo "DeLex utility exit code: $DELEX_RC"
echo "IFEval exit code: $IFEVAL_RC"
echo "DeLex Glaiveai2K: $(ls $PROJ/outputs/delex_llama31/utility/Glaiveai2K/*.json 2>/dev/null | wc -l)"
echo "DeLex Github_easy: $(ls $PROJ/outputs/delex_llama31/utility/Github_easy/*.json 2>/dev/null | wc -l)"
