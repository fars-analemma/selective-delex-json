#!/bin/bash
# Smoke test: start vLLM server, send a structured output request, verify response.
source /mnt/bmcpfs-29000zjpjtl6xjmjiifyk/fars/fars-exp/live/exp/selective-delex-json/exp/.venv/bin/activate

echo "=== Starting vLLM server ==="
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --port 8001 \
    --max-model-len 3072 \
    --gpu-memory-utilization 0.9 \
    --dtype auto &
VLLM_PID=$!

echo "=== Waiting for server to be ready ==="
for i in $(seq 1 120); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "Server ready after ${i}s"
        break
    fi
    sleep 5
done

if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "ERROR: Server failed to start after 600s"
    kill $VLLM_PID 2>/dev/null
    exit 1
fi

echo "=== Sending structured output request ==="
python3 -c "
import json
from openai import OpenAI

client = OpenAI(base_url='http://localhost:8001/v1', api_key='dummy')

schema = {
    'type': 'object',
    'properties': {
        'city': {'type': 'string'},
        'country': {'type': 'string'},
        'population': {'type': 'integer'}
    },
    'required': ['city', 'country', 'population'],
    'additionalProperties': False
}

response = client.chat.completions.create(
    model='meta-llama/Llama-3.1-8B-Instruct',
    messages=[{'role': 'user', 'content': 'Give me information about Paris.'}],
    response_format={
        'type': 'json_schema',
        'json_schema': {
            'name': 'city_info',
            'strict': True,
            'schema': schema
        }
    },
    max_tokens=256,
    temperature=0.6
)

content = response.choices[0].message.content
print('=== Raw response ===')
print(content)

parsed = json.loads(content)
print('=== Parsed JSON ===')
print(json.dumps(parsed, indent=2))

assert 'city' in parsed and 'country' in parsed and 'population' in parsed
print('=== SMOKE TEST PASSED ===')
"

RESULT=$?
kill $VLLM_PID 2>/dev/null
wait $VLLM_PID 2>/dev/null
exit $RESULT
