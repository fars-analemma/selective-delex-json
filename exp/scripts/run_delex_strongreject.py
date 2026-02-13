# StrongREJECT rubric scoring for DeLex-JSON defense outputs.
# DeLex-JSON never refuses -- all outputs scored via API.
# Uses original (pre-DeLex) schema for free-text extraction.

import argparse
import json
import math
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from openai import OpenAI
from evaluation.field_extractor import extract_free_text
from evaluation.strongreject_eval import score_single, _load_prompt_template


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prompts", required=True)
    parser.add_argument("--result-output", required=True)
    parser.add_argument("--judge-model", default="deepseek-ai/DeepSeek-V3")
    args = parser.parse_args()

    base_url = f"http://{os.environ['LEMMA_MAAS_BASE_URL']}/v1"
    api_key = os.environ["LEMMA_MAAS_API_KEY"]
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=120)
    template = _load_prompt_template()

    with open(args.prompts) as f:
        prompts = json.load(f)
    prompt_map = {p["id"]: p for p in prompts}

    output_files = sorted(glob.glob(os.path.join(args.output_dir, "*.json")))
    total = len(output_files)
    print(f"Scoring {total} outputs with StrongREJECT (DeLex-JSON defense)")
    print(f"Judge model: {args.judge_model}")

    results = []

    for idx, fpath in enumerate(output_files):
        with open(fpath) as f:
            record = json.load(f)

        pid = record["id"]
        behavior = record["behavior"]
        cat = record.get("category", prompt_map.get(pid, {}).get("category", ""))

        schema = record.get("original_response_format", record.get("response_format", {}))
        rf_schema = schema.get("json_schema", {}).get("schema", schema)
        free_text = extract_free_text(record["response"], rf_schema)

        sr = score_single(client, args.judge_model, behavior, free_text, template)
        results.append({
            "id": pid,
            "category": cat,
            "score": sr.score,
            "refusal": sr.refusal,
            "convincing": sr.convincing,
            "specific": sr.specific,
            "model_refused": False,
            "schema_modified": record.get("schema_modified", False),
        })

        if (idx + 1) % 10 == 0 or idx == 0:
            valid = [r for r in results if not math.isnan(r["score"])]
            mean = sum(r["score"] for r in valid) / len(valid) if valid else 0
            print(f"  [{idx+1}/{total}] mean_score={mean:.4f}", flush=True)

    valid = [r for r in results if not math.isnan(r["score"])]
    mean_score = sum(r["score"] for r in valid) / len(valid) if valid else 0.0
    asr = sum(1 for r in valid if r["score"] > 0) / len(valid) if valid else 0.0

    cat_scores = {}
    for r in results:
        cat = r["category"]
        if cat not in cat_scores:
            cat_scores[cat] = []
        if not math.isnan(r["score"]):
            cat_scores[cat].append(r)

    per_category = {}
    for cat, items in cat_scores.items():
        scores = [i["score"] for i in items]
        per_category[cat] = {
            "mean_score": sum(scores) / len(scores) if scores else 0.0,
            "asr": sum(1 for s in scores if s > 0) / len(scores) if scores else 0.0,
            "count": len(scores),
        }

    output_data = {
        "strongreject_score_mean": mean_score,
        "strongreject_asr": asr,
        "total_scored": len(valid),
        "total_nan": len(results) - len(valid),
        "model_refused_count": 0,
        "model_refusal_rate": 0.0,
        "per_category": per_category,
        "per_sample": results,
    }

    print(f"\n=== StrongREJECT Results (DeLex-JSON) ===")
    print(f"Mean score: {mean_score:.4f}")
    print(f"ASR (score > 0): {asr*100:.1f}%")
    for cat, v in sorted(per_category.items()):
        print(f"  {cat}: mean={v['mean_score']:.4f}, asr={v['asr']*100:.1f}%")

    os.makedirs(os.path.dirname(args.result_output), exist_ok=True)
    with open(args.result_output, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nResults saved to {args.result_output}")


if __name__ == "__main__":
    main()
