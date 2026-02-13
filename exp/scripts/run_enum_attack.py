# Run EnumAttack against a vLLM-served model on HarmBench and StrongREJECT prompts.
# Saves per-prompt JSON outputs to the specified output directory.

import argparse
import json
import os
import sys
import time

from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from attacks.enum_attack import generate_enum_attack


def run_attack(
    client: OpenAI,
    model: str,
    prompts: list,
    output_dir: str,
    temperature: float = 0.6,
    max_tokens: int = 1024,
):
    os.makedirs(output_dir, exist_ok=True)
    total = len(prompts)

    for i, p in enumerate(prompts):
        pid = p["id"]
        behavior = p["behavior"]
        out_path = os.path.join(output_dir, f"{pid}.json")

        if os.path.exists(out_path):
            print(f"[{i+1}/{total}] Skipping {pid} (already exists)")
            continue

        user_prompt, response_format = generate_enum_attack(behavior)

        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": user_prompt}],
                    response_format=response_format,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = resp.choices[0].message.content
                break
            except Exception as e:
                print(f"  Attempt {attempt+1} failed for {pid}: {e}")
                if attempt < 2:
                    time.sleep(5)
                else:
                    content = json.dumps({"error": str(e)})

        record = {
            "id": pid,
            "behavior": behavior,
            "category": p.get("category", ""),
            "user_prompt": user_prompt,
            "response_format": response_format,
            "response": content,
        }

        with open(out_path, "w") as f:
            json.dump(record, f, indent=2)

        print(f"[{i+1}/{total}] {pid}: {len(content)} chars")

    print(f"Done. {total} prompts processed -> {output_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True, help="vLLM server base URL")
    parser.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--prompts", required=True, help="Path to prompts JSON")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--api-key", default="dummy")
    args = parser.parse_args()

    with open(args.prompts) as f:
        prompts = json.load(f)

    client = OpenAI(base_url=args.endpoint, api_key=args.api_key)
    run_attack(client, args.model, prompts, args.output_dir, args.temperature, args.max_tokens)


if __name__ == "__main__":
    main()
