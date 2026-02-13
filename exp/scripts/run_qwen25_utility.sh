#!/bin/bash
# Qwen2.5-7B utility eval: no-defense + DeLex-JSON on GlaiveAI-2K subset.
# Uses resilient restart pattern to handle xgrammar memory leak.
PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

MODEL=Qwen/Qwen2.5-7B-Instruct
BATCH_SIZE=250
MAX_RESTARTS=20

start_server() {
    echo "=== Starting vLLM (attempt $1) ==="
    vllm serve $MODEL \
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

echo "=== No-defense utility eval (Glaiveai2K) ==="
for restart in $(seq 1 $MAX_RESTARTS); do
    start_server $restart || exit 1

    python $PROJ/scripts/run_no_defense_utility.py \
        --endpoint http://localhost:8001/v1 \
        --model $MODEL \
        --subsets Glaiveai2K \
        --output-dir $PROJ/outputs/no_defense_qwen25/utility \
        --result-output $PROJ/results/no_defense_qwen25_utility.json \
        --temperature 0.6 \
        --max-tokens 1024 \
        --batch-limit $BATCH_SIZE
    RC=$?

    stop_server

    if [ $RC -eq 0 ]; then
        echo "=== No-defense utility complete ==="
        break
    elif [ $RC -eq 2 ]; then
        echo "=== Batch limit reached, restarting ==="
        continue
    elif [ $RC -eq 3 ]; then
        echo "=== Server died, restarting ==="
        continue
    else
        echo "=== Script failed with code $RC, restarting ==="
        continue
    fi
done

echo "=== DeLex utility eval (Glaiveai2K) ==="
for restart in $(seq 1 $MAX_RESTARTS); do
    start_server $restart || exit 1

    python $PROJ/scripts/run_delex_utility.py \
        --endpoint http://localhost:8001/v1 \
        --model $MODEL \
        --subsets Glaiveai2K \
        --output-dir $PROJ/outputs/delex_qwen25/utility \
        --result-output $PROJ/results/delex_qwen25_utility.json \
        --temperature 0.6 \
        --max-tokens 1024 \
        --batch-limit $BATCH_SIZE
    RC=$?

    stop_server

    if [ $RC -eq 0 ]; then
        echo "=== DeLex utility complete ==="
        break
    elif [ $RC -eq 2 ]; then
        echo "=== Batch limit reached, restarting ==="
        continue
    elif [ $RC -eq 3 ]; then
        echo "=== Server died, restarting ==="
        continue
    else
        echo "=== Script failed with code $RC, restarting ==="
        continue
    fi
done

echo "=== Utility pipeline complete ==="
echo "No-def Glaiveai2K: $(ls $PROJ/outputs/no_defense_qwen25/utility/Glaiveai2K/*.json 2>/dev/null | wc -l)"
echo "DeLex Glaiveai2K: $(ls $PROJ/outputs/delex_qwen25/utility/Glaiveai2K/*.json 2>/dev/null | wc -l)"
echo "=== Job complete ==="
