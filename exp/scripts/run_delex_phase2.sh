#!/bin/bash
# Phase 2+: Utility eval (DeLex + no-defense) + IFEval + HarmBench classifier + StrongREJECT.
# Resumes from where the full pipeline crashed. Safety outputs already complete.
# More resilient: restarts vLLM if it crashes during long utility runs.
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

start_target_server() {
    echo "=== Starting Llama-3.1-8B-Instruct (port 8001) ==="
    vllm serve meta-llama/Llama-3.1-8B-Instruct \
        --port 8001 \
        --max-model-len 3072 \
        --gpu-memory-utilization 0.9 \
        --dtype auto &
    TARGET_PID=$!

    for i in $(seq 1 180); do
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            echo "Target server ready after ${i}s"
            return 0
        fi
        if [ $i -eq 180 ]; then
            echo "ERROR: Target server failed to start within 180s"
            kill $TARGET_PID 2>/dev/null
            return 1
        fi
        sleep 5
    done
}

stop_target_server() {
    echo "=== Stopping target server ==="
    kill $TARGET_PID 2>/dev/null
    wait $TARGET_PID 2>/dev/null || true
    sleep 5
}

run_with_restart() {
    local script_name="$1"
    shift
    local max_restarts=5
    local restart_count=0

    while [ $restart_count -lt $max_restarts ]; do
        echo "=== Running $script_name (attempt $((restart_count+1))/$max_restarts) ==="
        if python "$@"; then
            echo "=== $script_name completed successfully ==="
            return 0
        else
            echo "=== $script_name failed, checking if server is alive ==="
            restart_count=$((restart_count + 1))
            if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
                echo "=== Server crashed, restarting... ==="
                stop_target_server
                start_target_server || return 1
            else
                echo "=== Server still alive, script error ==="
                return 1
            fi
        fi
    done
    echo "=== $script_name failed after $max_restarts restarts ==="
    return 1
}

start_target_server || exit 1

echo "=== Phase 2: DeLex-JSON utility eval (resumes from existing outputs) ==="
run_with_restart "delex_utility" \
    $PROJ/scripts/run_delex_utility.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --output-dir $PROJ/outputs/delex_llama31/utility \
    --result-output $PROJ/results/delex_llama31_utility.json \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Phase 3: No-defense utility baseline ==="
run_with_restart "no_defense_utility" \
    $PROJ/scripts/run_no_defense_utility.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --output-dir $PROJ/outputs/no_defense_llama31/utility \
    --result-output $PROJ/results/no_defense_llama31_utility.json \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Phase 4: IFEval JSON subset eval ==="
run_with_restart "delex_ifeval" \
    $PROJ/scripts/run_delex_ifeval.py \
    --endpoint http://localhost:8001/v1 \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --result-output $PROJ/results/delex_ifeval_llama31.json \
    --temperature 0.6 \
    --max-tokens 1024

stop_target_server

echo "=== Phase 5: Starting HarmBench classifier (port 8003) ==="
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
        echo "ERROR: Classifier failed to start"
        kill $CLS_PID 2>/dev/null
        exit 1
    fi
    sleep 5
done

echo "=== Phase 5: Running HarmBench ASR evaluation ==="
python $PROJ/scripts/run_delex_eval.py \
    --cls-endpoint http://localhost:8003/v1 \
    --cls-model cais/HarmBench-Llama-2-13b-cls \
    --harmbench-dir $PROJ/outputs/delex_llama31/harmbench \
    --harmbench-prompts $PROJ/data/harmbench_prompts.json \
    --strongreject-dir $PROJ/outputs/delex_llama31/strongreject \
    --strongreject-prompts $PROJ/data/strongreject_prompts.json \
    --output $PROJ/results/delex_llama31_harmbench_asr.json

kill $CLS_PID 2>/dev/null
wait $CLS_PID 2>/dev/null || true

echo "=== Phase 6: Running StrongREJECT rubric scoring ==="
python $PROJ/scripts/run_delex_strongreject.py \
    --output-dir $PROJ/outputs/delex_llama31/strongreject \
    --prompts $PROJ/data/strongreject_prompts.json \
    --result-output $PROJ/results/delex_llama31_strongreject.json

echo "=== All phases complete ==="
