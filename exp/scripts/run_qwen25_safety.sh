#!/bin/bash
# Qwen2.5-7B-Instruct safety pipeline: no-defense + DeLex-JSON + HarmBench eval + StrongREJECT.
# Reuses all Python scripts from Llama pipeline, only changes model ID.
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate
export WANDB_MODE=offline

MODEL=Qwen/Qwen2.5-7B-Instruct

echo "=== Phase 1: Starting Qwen2.5-7B-Instruct (port 8001) ==="
vllm serve $MODEL \
    --port 8001 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
TARGET_PID=$!

echo "=== Waiting for target server ==="
for i in $(seq 1 180); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "Target server ready after ${i}s"
        break
    fi
    if [ $i -eq 180 ]; then
        echo "ERROR: Target server failed to start within 180s"
        kill $TARGET_PID 2>/dev/null
        exit 1
    fi
    sleep 5
done

echo "=== Phase 1a: No-defense EnumAttack on HarmBench ==="
python $PROJ/scripts/run_enum_attack.py \
    --endpoint http://localhost:8001/v1 \
    --model $MODEL \
    --prompts $PROJ/data/harmbench_prompts.json \
    --output-dir $PROJ/outputs/no_defense_qwen25/harmbench \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Phase 1b: No-defense EnumAttack on StrongREJECT ==="
python $PROJ/scripts/run_enum_attack.py \
    --endpoint http://localhost:8001/v1 \
    --model $MODEL \
    --prompts $PROJ/data/strongreject_prompts.json \
    --output-dir $PROJ/outputs/no_defense_qwen25/strongreject \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Phase 1c: DeLex-JSON on HarmBench ==="
python $PROJ/scripts/run_delex_experiment.py \
    --endpoint http://localhost:8001/v1 \
    --model $MODEL \
    --prompts $PROJ/data/harmbench_prompts.json \
    --output-dir $PROJ/outputs/delex_qwen25/harmbench \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Phase 1d: DeLex-JSON on StrongREJECT ==="
python $PROJ/scripts/run_delex_experiment.py \
    --endpoint http://localhost:8001/v1 \
    --model $MODEL \
    --prompts $PROJ/data/strongreject_prompts.json \
    --output-dir $PROJ/outputs/delex_qwen25/strongreject \
    --temperature 0.6 \
    --max-tokens 1024

echo "=== Stopping target server ==="
kill $TARGET_PID 2>/dev/null
wait $TARGET_PID 2>/dev/null || true
sleep 5

echo "=== Phase 2: Starting HarmBench classifier (port 8003) ==="
vllm serve cais/HarmBench-Llama-2-13b-cls \
    --port 8003 \
    --max-model-len 2048 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
CLS_PID=$!

echo "=== Waiting for classifier ==="
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

echo "=== Phase 2a: HarmBench ASR for no-defense ==="
python $PROJ/scripts/run_harmbench_eval.py \
    --endpoint http://localhost:8003/v1 \
    --model cais/HarmBench-Llama-2-13b-cls \
    --harmbench-dir $PROJ/outputs/no_defense_qwen25/harmbench \
    --harmbench-prompts $PROJ/data/harmbench_prompts.json \
    --strongreject-dir $PROJ/outputs/no_defense_qwen25/strongreject \
    --strongreject-prompts $PROJ/data/strongreject_prompts.json \
    --output $PROJ/results/no_defense_qwen25_harmbench_asr.json

echo "=== Phase 2b: HarmBench ASR for DeLex-JSON ==="
python $PROJ/scripts/run_delex_eval.py \
    --cls-endpoint http://localhost:8003/v1 \
    --cls-model cais/HarmBench-Llama-2-13b-cls \
    --harmbench-dir $PROJ/outputs/delex_qwen25/harmbench \
    --harmbench-prompts $PROJ/data/harmbench_prompts.json \
    --strongreject-dir $PROJ/outputs/delex_qwen25/strongreject \
    --strongreject-prompts $PROJ/data/strongreject_prompts.json \
    --output $PROJ/results/delex_qwen25_harmbench_asr.json

echo "=== Stopping classifier ==="
kill $CLS_PID 2>/dev/null
wait $CLS_PID 2>/dev/null || true

echo "=== Phase 3a: StrongREJECT scoring for no-defense ==="
python $PROJ/scripts/run_strongreject_eval.py \
    --output-dir $PROJ/outputs/no_defense_qwen25/strongreject \
    --prompts $PROJ/data/strongreject_prompts.json \
    --result-output $PROJ/results/no_defense_qwen25_strongreject.json

echo "=== Phase 3b: StrongREJECT scoring for DeLex-JSON ==="
python $PROJ/scripts/run_delex_strongreject.py \
    --output-dir $PROJ/outputs/delex_qwen25/strongreject \
    --prompts $PROJ/data/strongreject_prompts.json \
    --result-output $PROJ/results/delex_qwen25_strongreject.json

echo "=== Safety pipeline complete ==="
echo "No-defense HarmBench: $(ls $PROJ/outputs/no_defense_qwen25/harmbench/*.json 2>/dev/null | wc -l)"
echo "No-defense StrongREJECT: $(ls $PROJ/outputs/no_defense_qwen25/strongreject/*.json 2>/dev/null | wc -l)"
echo "DeLex HarmBench: $(ls $PROJ/outputs/delex_qwen25/harmbench/*.json 2>/dev/null | wc -l)"
echo "DeLex StrongREJECT: $(ls $PROJ/outputs/delex_qwen25/strongreject/*.json 2>/dev/null | wc -l)"
