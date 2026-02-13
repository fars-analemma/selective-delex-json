#!/bin/bash
# DeLex-JSON v2 utility evaluation: re-run with conjunction-based suspicion.
# Uses the same resilient restart mechanism as v1 to handle xgrammar memory leak.
# Also re-runs no-defense baseline to ensure fair comparison (same error profile).
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate
export WANDB_MODE=offline

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

echo "=== Phase 1: DeLex-JSON v2 utility eval ==="
for restart in $(seq 1 $MAX_RESTARTS); do
    start_server $restart || exit 1

    echo "=== DeLex v2 utility eval (batch $restart, limit $BATCH_SIZE) ==="
    python $PROJ/scripts/run_delex_utility.py \
        --endpoint http://localhost:8001/v1 \
        --model meta-llama/Llama-3.1-8B-Instruct \
        --output-dir $PROJ/outputs/delex_v2_llama31/utility \
        --result-output $PROJ/results/delex_v2_llama31_utility.json \
        --temperature 0.6 \
        --max-tokens 1024 \
        --batch-limit $BATCH_SIZE
    RC=$?
    stop_server

    if [ $RC -eq 0 ]; then
        echo "=== DeLex v2 utility eval completed ==="
        break
    elif [ $RC -eq 2 ]; then
        echo "=== Batch limit reached, restarting ==="
        continue
    else
        echo "=== Script failed with code $RC, restarting ==="
        continue
    fi
done

echo "=== Phase 2: No-defense utility baseline (fresh re-run) ==="
for restart in $(seq 1 $MAX_RESTARTS); do
    start_server "nodef-$restart" || exit 1

    echo "=== No-defense utility eval (batch $restart, limit $BATCH_SIZE) ==="
    python $PROJ/scripts/run_no_defense_utility.py \
        --endpoint http://localhost:8001/v1 \
        --model meta-llama/Llama-3.1-8B-Instruct \
        --output-dir $PROJ/outputs/no_defense_v2_llama31/utility \
        --result-output $PROJ/results/no_defense_v2_llama31_utility.json \
        --temperature 0.6 \
        --max-tokens 1024 \
        --batch-limit $BATCH_SIZE
    RC=$?
    stop_server

    if [ $RC -eq 0 ]; then
        echo "=== No-defense utility eval completed ==="
        break
    elif [ $RC -eq 2 ]; then
        echo "=== Batch limit reached, restarting ==="
        continue
    else
        echo "=== Script failed with code $RC, restarting ==="
        continue
    fi
done

echo "=== Phase 3: IFEval JSON ==="
start_server "ifeval" || exit 1
python $PROJ/scripts/run_delex_ifeval.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --result-output $PROJ/results/delex_v2_ifeval_llama31.json \
    --temperature 0.6 \
    --max-tokens 1024
stop_server

echo "=== Results ==="
echo "DeLex v2 utility: $(cat $PROJ/results/delex_v2_llama31_utility.json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(f\"validity={d[\"overall_json_validity_rate\"]*100:.1f}% compliance={d[\"overall_schema_compliance_rate\"]*100:.1f}%\")')"
echo "No-defense utility: $(cat $PROJ/results/no_defense_v2_llama31_utility.json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(f\"validity={d[\"overall_json_validity_rate\"]*100:.1f}% compliance={d[\"overall_schema_compliance_rate\"]*100:.1f}%\")')"
echo "=== Job complete ==="
