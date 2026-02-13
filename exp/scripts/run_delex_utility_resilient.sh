#!/bin/bash
# Resilient DeLex utility eval: restarts vLLM every BATCH_SIZE schemas
# to work around xgrammar memory leak. All outputs cached to disk.
PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

BATCH_SIZE=250
MAX_RESTARTS=20

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

for restart in $(seq 1 $MAX_RESTARTS); do
    start_server $restart || exit 1

    echo "=== DeLex utility eval (batch $restart, limit $BATCH_SIZE) ==="
    python $PROJ/scripts/run_delex_utility.py \
        --endpoint http://localhost:8001/v1 \
        --model meta-llama/Llama-3.1-8B-Instruct \
        --output-dir $PROJ/outputs/delex_llama31/utility \
        --result-output $PROJ/results/delex_llama31_utility.json \
        --temperature 0.6 \
        --max-tokens 1024 \
        --batch-limit $BATCH_SIZE
    RC=$?

    stop_server

    if [ $RC -eq 0 ]; then
        echo "=== Utility eval completed successfully ==="
        break
    elif [ $RC -eq 2 ]; then
        echo "=== Batch limit reached, restarting server ==="
        continue
    elif [ $RC -eq 3 ]; then
        echo "=== Server died, restarting ==="
        continue
    else
        echo "=== Script failed with code $RC, restarting ==="
        continue
    fi
done

echo "=== Starting server for IFEval ==="
start_server "ifeval" || exit 1

python $PROJ/scripts/run_delex_ifeval.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --result-output $PROJ/results/delex_ifeval_llama31.json \
    --temperature 0.6 \
    --max-tokens 1024

stop_server

echo "=== DeLex Glaiveai2K: $(ls $PROJ/outputs/delex_llama31/utility/Glaiveai2K/*.json 2>/dev/null | wc -l) ==="
echo "=== DeLex Github_easy: $(ls $PROJ/outputs/delex_llama31/utility/Github_easy/*.json 2>/dev/null | wc -l) ==="
echo "=== Job complete ==="
