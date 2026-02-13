# Run StrongREJECT scoring on EnumAttack outputs via LEMMA MaaS API.
# No GPU needed -- uses LLM-as-judge through API.

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from evaluation.strongreject_eval import evaluate_strongreject


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prompts", required=True)
    parser.add_argument("--result-output", required=True)
    parser.add_argument("--judge-model", default="deepseek-ai/DeepSeek-V3")
    args = parser.parse_args()

    base_url = f"http://{os.environ['LEMMA_MAAS_BASE_URL']}/v1"
    api_key = os.environ["LEMMA_MAAS_API_KEY"]

    print(f"Judge model: {args.judge_model}")
    print(f"API base: {base_url}")

    results = evaluate_strongreject(
        output_dir=args.output_dir,
        prompts_file=args.prompts,
        judge_base_url=base_url,
        judge_api_key=api_key,
        judge_model=args.judge_model,
    )

    print(f"\n=== StrongREJECT Results ===")
    print(f"Mean score: {results['strongreject_score_mean']:.4f}")
    print(f"ASR (score > 0): {results['strongreject_asr']*100:.1f}%")
    print(f"Total scored: {results['total_scored']}, NaN: {results['total_nan']}")
    for cat, v in sorted(results["per_category"].items()):
        print(f"  {cat}: mean={v['mean_score']:.4f}, asr={v['asr']*100:.1f}%, n={v['count']}")

    os.makedirs(os.path.dirname(args.result_output), exist_ok=True)
    with open(args.result_output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {args.result_output}")


if __name__ == "__main__":
    main()
