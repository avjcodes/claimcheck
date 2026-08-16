#!/usr/bin/env python3
"""claimcheck: editorial QA for AI-assisted content.

Scans a markdown article and flags every checkable claim: numbers,
benchmarks, speed multipliers, version references, superlatives.
Emits a reviewer report so a human editor verifies claims BEFORE
publishing, not after a reader calls one out.

Built for content brands shipping AI-drafted articles at volume,
where the failure mode is never grammar. It is a confident number
nobody checked.

Usage:
    python claimcheck.py article.md              # rule-based scan
    python claimcheck.py article.md --claude     # + Claude Code semantic pass

The --claude flag shells out to the Claude Code CLI (claude -p) to
catch claims the rules miss and to classify each flag as verifiable,
needs-source, or opinion. Rules run first so the tool degrades
gracefully: no API, no network, you still get the mechanical scan.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

# Each rule: (label, regex, why it needs checking)
RULES = [
    ("number-claim", r"\b\d[\d,.]*\s*(?:%|percent|x|times)\b",
     "Percentages and multipliers read as measured. Were they?"),
    ("benchmark", r"\b(?:benchmark|faster|slower|outperform\w*|beats?)\b",
     "Comparative performance claims need a test you can point to."),
    ("count-claim", r"\b\d[\d,]*\+?\s+(?:users?|companies|stars?|downloads?|contacts?|emails?|checks?|tests?)\b",
     "Concrete counts are the first thing a skeptical reader verifies."),
    ("version-ref", r"\b(?:v\d+[\w.\-]*|\d+\.\d+(?:\.\d+)?)\b",
     "Version references go stale; wrong ones break reader trust instantly."),
    ("superlative", r"\b(?:best|fastest|first|largest|leading|state[- ]of[- ]the[- ]art|(?:the\s+)?only\s+(?:way|tool|platform|solution|provider))\b",
     "Superlatives are claims about the whole market. Source or soften."),
    ("token-count", r"\b\d[\d,]*\s*(?:more\s+)?tokens?\b",
     "Token numbers read as measured cost data. Cite the run or cut them."),
    ("date-claim", r"\b(?:20\d{2}|last (?:week|month|year)|recently)\b",
     "Time anchors drift. 'Recently' in an evergreen article rots quietly."),
    ("citation-stub", r"\[(?:cite|source|todo|verify)\]|\bcitation needed\b",
     "The draft itself admits this is unverified."),
]

CLAUDE_PROMPT = (
    "You are an editorial fact-check triager. Below is a markdown article. "
    "List every factual claim a skeptical senior engineer would want verified "
    "before publication. For each, output one JSON object per line: "
    '{"line": <line number>, "claim": "<short quote>", '
    '"class": "verifiable|needs-source|opinion"}. '
    "Output only JSON lines, nothing else.\n\n---\n"
)


def rule_scan(lines):
    flags = []
    in_code = False
    for n, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue  # deliberate: code blocks are demos, not claims
        for label, pattern, why in RULES:
            for m in re.finditer(pattern, line, re.IGNORECASE):
                flags.append({
                    "line": n, "rule": label, "match": m.group(0),
                    "context": line.strip()[:120], "why": why,
                })
    return flags


def claude_scan(text):
    try:
        out = subprocess.run(
            ["claude", "-p", CLAUDE_PROMPT + text],
            capture_output=True, text=True, timeout=120, shell=True,
        )
        items = []
        for ln in out.stdout.splitlines():
            ln = ln.strip()
            if ln.startswith("{"):
                try:
                    items.append(json.loads(ln))
                except json.JSONDecodeError:
                    continue  # one bad line should not sink the pass
        return items, None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return [], f"claude pass skipped: {e.__class__.__name__}"


def report(path, flags, semantic, note):
    print(f"claimcheck report: {path}")
    print(f"{len(flags)} mechanical flag(s)"
          + (f", {len(semantic)} semantic flag(s)" if semantic else "")
          + (f"  [{note}]" if note else ""))
    print("-" * 60)
    for f in flags:
        print(f"L{f['line']:>4}  [{f['rule']}]  \"{f['match']}\"")
        print(f"       {f['context']}")
        print(f"       -> {f['why']}")
    for s in semantic:
        print(f"L{s.get('line', '?'):>4}  [claude:{s.get('class', '?')}]  \"{s.get('claim', '')[:100]}\"")
    print("-" * 60)
    verdict = "CLEAN" if not flags and not semantic else "NEEDS EDITORIAL REVIEW"
    print(f"verdict: {verdict}")
    return 0 if verdict == "CLEAN" else 1


def main():
    args = sys.argv[1:]
    use_claude = "--claude" in args
    paths = [a for a in args if not a.startswith("--")]
    if not paths:
        print("usage: python claimcheck.py <article.md> [--claude]", file=sys.stderr)
        return 2
    path = Path(paths[0])
    if not path.is_file():
        print(f"error: {path} is not a file", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8", errors="replace")
    flags = rule_scan(text.splitlines())
    semantic, note = claude_scan(text) if use_claude else ([], None)
    return report(path.name, flags, semantic, note)


if __name__ == "__main__":
    sys.exit(main())
