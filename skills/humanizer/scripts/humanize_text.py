#!/usr/bin/env python3
"""
Humanize text using TextHumanize library.
Usage: python humanize_text.py <input_file> [--intensity 70] [--output <output_file>]
       python humanize_text.py --text "Some AI-sounding text" [--intensity 70]

Reads text, runs it through TextHumanize, prints or writes the result.
"""
import argparse
import sys

try:
    from texthumanize import humanize, analyze
except ImportError:
    print("ERROR: texthumanize not installed. Run: pip install git+https://github.com/ksanyok/TextHumanize.git", file=sys.stderr)
    sys.exit(1)


def process_text(text: str, intensity: int = 70) -> dict:
    """Humanize text and return result with metrics."""
    analysis = analyze(text, lang="en")
    result = humanize(text, intensity=intensity, lang="en")
    return {
        "original": text,
        "humanized": result.text,
        "change_ratio": getattr(result, "change_ratio", None),
        "ai_score_before": getattr(analysis, "ai_score", None),
    }


def main():
    parser = argparse.ArgumentParser(description="Humanize AI-generated text")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("input_file", nargs="?", help="Input text file")
    group.add_argument("--text", "-t", help="Direct text input")
    parser.add_argument("--intensity", "-i", type=int, default=70,
                        help="Humanization intensity 0-100 (default: 70)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--metrics", "-m", action="store_true",
                        help="Print metrics to stderr")
    args = parser.parse_args()

    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        text = args.text

    result = process_text(text, args.intensity)

    if args.metrics:
        print(f"Change ratio: {result['change_ratio']}", file=sys.stderr)
        print(f"AI score (before): {result['ai_score_before']}", file=sys.stderr)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result["humanized"])
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(result["humanized"])


if __name__ == "__main__":
    main()
