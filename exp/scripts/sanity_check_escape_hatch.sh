#!/bin/bash
# Sanity check: test escape-hatch oneOf schema with vLLM
set -e

PROJ=/mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp
source $PROJ/.venv/bin/activate
cd $PROJ

echo "=== Starting Llama-3.1-8B-Instruct ==="
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --port 8001 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
PID=$!

echo "=== Waiting for server ==="
for i in $(seq 1 180); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "Server ready after ${i}s"
        break
    fi
    if [ $i -eq 180 ]; then
        echo "ERROR: Server failed to start"
        kill $PID 2>/dev/null
        exit 1
    fi
    sleep 5
done

echo "=== Running sanity check ==="
python $PROJ/scripts/sanity_check_escape_hatch.py

echo "=== Stopping server ==="
kill $PID 2>/dev/null
wait $PID 2>/dev/null || true
echo "=== Done ==="
