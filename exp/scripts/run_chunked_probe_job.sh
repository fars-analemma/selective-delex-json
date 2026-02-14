#!/bin/bash
# GPU job: Run chunked-payload attack probe on Llama-3.1-8B-Instruct.
# 8 conditions: chunk_size {5,10,15,20} x defense {none,delex}.
# Then evaluates all outputs with HarmBench classifier.
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

MODEL="meta-llama/Llama-3.1-8B-Instruct"
CLS_MODEL="cais/HarmBench-Llama-2-13b-cls"
PROMPTS=$PROJ/data/harmbench_prompts_50.json
OUT_BASE=$PROJ/outputs/chunked_probe
RESULTS_DIR=$PROJ/results

echo "=== Starting Llama-3.1-8B-Instruct (port 8001) ==="
vllm serve $MODEL \
    --port 8001 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
LLM_PID=$!

for i in $(seq 1 180); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "LLM ready after ${i}s"
        break
    fi
    [ $i -eq 180 ] && { echo "ERROR: LLM start timeout"; kill $LLM_PID 2>/dev/null; exit 1; }
    sleep 5
done

echo "=== Running chunked-payload attack (8 conditions) ==="
for CS in 5 10 15 20; do
    echo "--- chunk_size=$CS, defense=none ---"
    python $PROJ/scripts/run_chunked_probe.py \
        --endpoint http://localhost:8001/v1 \
        --model $MODEL \
        --prompts $PROMPTS \
        --output-dir $OUT_BASE/no_defense_cs${CS} \
        --chunk-size $CS \
        --defense none \
        --temperature 0.6 \
        --max-tokens 1024

    echo "--- chunk_size=$CS, defense=delex ---"
    python $PROJ/scripts/run_chunked_probe.py \
        --endpoint http://localhost:8001/v1 \
        --model $MODEL \
        --prompts $PROMPTS \
        --output-dir $OUT_BASE/delex_cs${CS} \
        --chunk-size $CS \
        --defense delex \
        --temperature 0.6 \
        --max-tokens 1024
done

echo "=== Stopping LLM ==="
kill $LLM_PID 2>/dev/null
wait $LLM_PID 2>/dev/null || true
sleep 5

echo "=== Starting HarmBench classifier (port 8003) ==="
vllm serve $CLS_MODEL \
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
    [ $i -eq 180 ] && { echo "ERROR: classifier start timeout"; kill $CLS_PID 2>/dev/null; exit 1; }
    sleep 5
done

echo "=== Evaluating all 8 conditions ==="
python $PROJ/scripts/run_chunked_probe_eval.py \
    --cls-endpoint http://localhost:8003/v1 \
    --cls-model $CLS_MODEL \
    --prompts $PROMPTS \
    --output-dirs \
        $OUT_BASE/no_defense_cs5 \
        $OUT_BASE/no_defense_cs10 \
        $OUT_BASE/no_defense_cs15 \
        $OUT_BASE/no_defense_cs20 \
        $OUT_BASE/delex_cs5 \
        $OUT_BASE/delex_cs10 \
        $OUT_BASE/delex_cs15 \
        $OUT_BASE/delex_cs20 \
    --labels \
        no_defense_cs5 \
        no_defense_cs10 \
        no_defense_cs15 \
        no_defense_cs20 \
        delex_cs5 \
        delex_cs10 \
        delex_cs15 \
        delex_cs20 \
    --results-dir $RESULTS_DIR

echo "=== Stopping classifier ==="
kill $CLS_PID 2>/dev/null
wait $CLS_PID 2>/dev/null || true

echo "=== Job complete ==="
