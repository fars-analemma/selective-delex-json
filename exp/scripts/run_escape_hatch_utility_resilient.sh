#!/bin/bash
# Resilient utility eval: auto-restarts vLLM server on crash.

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate
cd $PROJ

MAX_ATTEMPTS=15

for attempt in $(seq 1 $MAX_ATTEMPTS); do
    echo "=== Attempt $attempt: Starting Llama-3.1-8B-Instruct ==="
    CUDA_VISIBLE_DEVICES=0 vllm serve meta-llama/Llama-3.1-8B-Instruct \
        --port 8001 \
        --max-model-len 3072 \
        --gpu-memory-utilization 0.9 \
        --dtype auto &
    PID=$!

    echo "=== Waiting for server ==="
    SERVER_UP=0
    for i in $(seq 1 180); do
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            echo "Server ready after ${i}s"
            SERVER_UP=1
            break
        fi
        sleep 5
    done

    if [ "$SERVER_UP" -eq 0 ]; then
        echo "ERROR: Server failed to start on attempt $attempt"
        kill $PID 2>/dev/null
        wait $PID 2>/dev/null || true
        sleep 5
        continue
    fi

    echo "=== Running utility eval ==="
    python $PROJ/scripts/run_escape_hatch_utility.py \
        --endpoint http://localhost:8001/v1 \
        --model meta-llama/Llama-3.1-8B-Instruct \
        --output-dir $PROJ/outputs/escape_hatch_llama31/utility \
        --result-output $PROJ/results/escape_hatch_llama31_utility.json \
        --temperature 0.6 \
        --max-tokens 1024
    EXIT_CODE=$?

    echo "=== Stopping server ==="
    kill $PID 2>/dev/null
    wait $PID 2>/dev/null || true
    sleep 5

    if [ "$EXIT_CODE" -eq 0 ]; then
        echo "=== Utility eval completed successfully ==="
        exit 0
    else
        SAVED=$(find $PROJ/outputs/escape_hatch_llama31/utility -name '*.json' 2>/dev/null | wc -l)
        echo "=== Attempt $attempt failed (exit=$EXIT_CODE). $SAVED files saved so far. Retrying... ==="
    fi
done

echo "=== Max attempts reached. Check outputs. ==="
exit 1
