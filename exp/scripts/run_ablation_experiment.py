# Run EnumAttack with ablation DeLex-JSON variants on HarmBench.
# Supports --delex-mode: strip_only, delex_all, heuristic_only.
# Same pipeline as run_delex_experiment.py but uses delexicalize_schema_ablation().

import argparse
import json
import os
import sys
import time

from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from attacks.enum_attack import generate_enum_attack
from defenses.delex import delexicalize_schema_ablation


def run_ablation_attack(
    client: OpenAI,
    model: str,
    prompts: list,
    output_dir: str,
    delex_mode: str,
    temperature: float = 0.6,
    max_tokens: int = 1024,
):
    os.makedirs(output_dir, exist_ok=True)
    total = len(prompts)
    modified_count = 0
    t0 = time.time()

    for i, p in enumerate(prompts):
        pid = p["id"]
        behavior = p["behavior"]
        out_path = os.path.join(output_dir, f"{pid}.json")

        if os.path.exists(out_path):
            print(f"[{i+1}/{total}] Skipping {pid} (already exists)")
            continue

        user_prompt, response_format = generate_enum_attack(behavior)
        sanitized_format, mapping, delex_report = delexicalize_schema_ablation(
            response_format, delex_mode=delex_mode
        )

        schema_modified = len(mapping) > 0
        if schema_modified:
            modified_count += 1

        content = None
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": user_prompt}],
                    response_format=sanitized_format,
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
            "original_response_format": response_format,
            "sanitized_response_format": sanitized_format,
            "placeholder_mapping": mapping,
            "delex_report": delex_report,
            "delex_mode": delex_mode,
            "schema_modified": schema_modified,
            "response": content,
            "model_refused": False,
        }
        with open(out_path, "w") as f:
            json.dump(record, f, indent=2)

        status = "MODIFIED" if schema_modified else "UNCHANGED"
        print(f"[{i+1}/{total}] {pid}: {status} placeholders={len(mapping)} ({len(content)} chars)")

    elapsed = time.time() - t0
    print(f"\nDone ({delex_mode}). {total} prompts -> {output_dir} ({elapsed:.1f}s)")
    print(f"Schema modified: {modified_count}/{total} ({modified_count/total*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--prompts", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--delex-mode", required=True, choices=["strip_only", "delex_all", "heuristic_only"])
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--api-key", default="dummy")
    args = parser.parse_args()

    with open(args.prompts) as f:
        prompts = json.load(f)

    client = OpenAI(base_url=args.endpoint, api_key=args.api_key)
    run_ablation_attack(
        client, args.model, prompts, args.output_dir,
        args.delex_mode, args.temperature, args.max_tokens,
    )


if __name__ == "__main__":
    main()
