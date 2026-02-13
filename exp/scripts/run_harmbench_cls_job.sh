#!/bin/bash
# Job C: HarmBench classifier eval on DeLex safety outputs.
PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate

echo "=== Starting HarmBench classifier (port 8003) ==="
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
    [ $i -eq 180 ] && { echo "ERROR: classifier start timeout"; kill $CLS_PID 2>/dev/null; exit 1; }
    sleep 5
done

echo "=== Running HarmBench ASR evaluation ==="
python $PROJ/scripts/run_delex_eval.py \
    --cls-endpoint http://localhost:8003/v1 \
    --cls-model cais/HarmBench-Llama-2-13b-cls \
    --harmbench-dir $PROJ/outputs/delex_llama31/harmbench \
    --harmbench-prompts $PROJ/data/harmbench_prompts.json \
    --strongreject-dir $PROJ/outputs/delex_llama31/strongreject \
    --strongreject-prompts $PROJ/data/strongreject_prompts.json \
    --output $PROJ/results/delex_llama31_harmbench_asr.json
EVAL_RC=$?

kill $CLS_PID 2>/dev/null
wait $CLS_PID 2>/dev/null || true

echo "=== Job C complete ==="
echo "Eval exit code: $EVAL_RC"
