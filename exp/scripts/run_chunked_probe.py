# Run chunked-payload attack variant against a vLLM-served model.
# For each prompt: generates chunked enum schema, optionally applies DeLex-JSON,
# runs constrained decoding, saves output with suspicion analysis.

import argparse
import json
import os
import sys
import time

from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from attacks.chunked_enum_attack import (
    generate_chunked_enum_attack,
    analyze_chunks_suspicion,
)
from defenses.delex import delexicalize_schema


def run_chunked_attack(
    client: OpenAI,
    model: str,
    prompts: list,
    output_dir: str,
    chunk_size: int = 20,
    defense: str = "none",
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

        user_prompt, response_format = generate_chunked_enum_attack(
            behavior, chunk_size=chunk_size
        )

        suspicion = analyze_chunks_suspicion(response_format)

        if defense == "delex":
            sanitized_format, mapping, delex_report = delexicalize_schema(response_format)
            schema_modified = len(mapping) > 0
        else:
            sanitized_format = response_format
            mapping = {}
            delex_report = []
            schema_modified = False

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
            "chunk_size": chunk_size,
            "defense": defense,
            "user_prompt": user_prompt,
            "original_response_format": response_format,
            "sanitized_response_format": sanitized_format,
            "placeholder_mapping": mapping,
            "delex_report": delex_report,
            "schema_modified": schema_modified,
            "suspicion_analysis": suspicion,
            "response": content,
        }

        with open(out_path, "w") as f:
            json.dump(record, f, indent=2)

        status = f"defense={defense} cs={chunk_size} chunks={suspicion['total_chunks']} flagged={suspicion['flagged_chunks']}"
        print(f"[{i+1}/{total}] {pid}: {status} ({len(content)} chars)")

    print(f"\nDone. {total} prompts -> {output_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", default="meta-llama/Llama-3.1-8B-Instruct")
    parser.add_argument("--prompts", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--chunk-size", type=int, default=20)
    parser.add_argument("--defense", choices=["none", "delex"], default="none")
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--api-key", default="dummy")
    args = parser.parse_args()

    with open(args.prompts) as f:
        prompts = json.load(f)

    client = OpenAI(base_url=args.endpoint, api_key=args.api_key)
    run_chunked_attack(
        client, args.model, prompts, args.output_dir,
        args.chunk_size, args.defense, args.temperature, args.max_tokens,
    )


if __name__ == "__main__":
    main()
