# Run EnumAttack with input guard defense on HarmBench and StrongREJECT prompts.
# For each prompt: (1) generate attack schema, (2) run Llama Guard on (prompt+schema),
# (3) if guard refuses -> save refusal, (4) if passes -> run constrained decoding.

import argparse
import json
import os
import sys
import time

from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from attacks.enum_attack import generate_enum_attack
from defenses.input_guard import run_input_guard, REFUSAL_MESSAGE


def run_guarded_attack(
    target_client: OpenAI,
    target_model: str,
    guard_client: OpenAI,
    guard_model: str,
    prompts: list,
    output_dir: str,
    temperature: float = 0.6,
    max_tokens: int = 1024,
):
    os.makedirs(output_dir, exist_ok=True)
    total = len(prompts)
    refused_count = 0

    for i, p in enumerate(prompts):
        pid = p["id"]
        behavior = p["behavior"]
        out_path = os.path.join(output_dir, f"{pid}.json")

        if os.path.exists(out_path):
            print(f"[{i+1}/{total}] Skipping {pid} (already exists)")
            continue

        user_prompt, response_format = generate_enum_attack(behavior)

        guard_result = run_input_guard(guard_client, guard_model, user_prompt, response_format)

        if guard_result["refused"]:
            refused_count += 1
            record = {
                "id": pid,
                "behavior": behavior,
                "category": p.get("category", ""),
                "user_prompt": user_prompt,
                "response_format": response_format,
                "response": REFUSAL_MESSAGE,
                "guard_refused": True,
                "guard_decision": guard_result["decision"],
                "guard_response": guard_result["guard_response"],
            }
            with open(out_path, "w") as f:
                json.dump(record, f, indent=2)
            print(f"[{i+1}/{total}] {pid}: REFUSED by guard")
            continue

        for attempt in range(3):
            try:
                resp = target_client.chat.completions.create(
                    model=target_model,
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
            "guard_refused": False,
            "guard_decision": guard_result["decision"],
            "guard_response": guard_result["guard_response"],
        }

        with open(out_path, "w") as f:
            json.dump(record, f, indent=2)

        print(f"[{i+1}/{total}] {pid}: PASSED guard, {len(content)} chars")

    print(f"\nDone. {total} prompts processed -> {output_dir}")
    print(f"Guard refused: {refused_count}/{total} ({refused_count/total*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-endpoint", required=True)
    parser.add_argument("--target-model", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--guard-endpoint", required=True)
    parser.add_argument("--guard-model", default="meta-llama/Llama-Guard-3-8B")
    parser.add_argument("--prompts", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--api-key", default="dummy")
    args = parser.parse_args()

    with open(args.prompts) as f:
        prompts = json.load(f)

    target_client = OpenAI(base_url=args.target_endpoint, api_key=args.api_key)
    guard_client = OpenAI(base_url=args.guard_endpoint, api_key=args.api_key)

    run_guarded_attack(
        target_client, args.target_model,
        guard_client, args.guard_model,
        prompts, args.output_dir,
        args.temperature, args.max_tokens,
    )


if __name__ == "__main__":
    main()
