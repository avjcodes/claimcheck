# claimcheck

Editorial QA for AI-assisted content. Scans a markdown article and flags
every claim a skeptical reader would check: numbers, benchmarks, speed
multipliers, version references, superlatives, time anchors, and the
`[cite]` stubs drafts leave behind. Prints a reviewer report and exits
nonzero when review is needed, so it drops straight into CI or a
pre-publish hook.

Built in one sitting for [ctaio.dev](https://ctaio.dev)'s hiring task:
a content brand for agentic-coding practitioners lives or dies on
"verifiable workflow details," and the failure mode of AI-drafted
content at volume is never grammar. It is a confident number nobody
checked before publishing.

## Usage

```
python claimcheck.py article.md              # rule-based scan, stdlib only
python claimcheck.py article.md --claude     # + Claude Code semantic pass
```

No dependencies for the mechanical scan. The `--claude` flag shells out
to the Claude Code CLI (`claude -p`) for a semantic pass that catches
claims the rules miss and classifies each as verifiable, needs-source,
or opinion. Rules run first on purpose: no API key, no network, you
still get the scan.

## Design decisions

- **Rules before model.** The mechanical pass is deterministic,
  instant, and free, so the tool degrades gracefully when the model
  isn't available. The model layer adds judgment, not availability risk.
- **Code blocks are skipped deliberately.** A number inside a fenced
  code block is a demo, not a claim.
- **Exit codes are the API.** `0` clean, `1` needs review, `2` usage
  error. That makes it a pre-publish gate, not just a report.
- **Tuned against its own false positives.** First run flagged bare
  "only" ("only 8 of the 50") as a superlative; the rule now matches
  market-claim shapes ("the only tool that...") instead of the word.

## Sample output

Run against `sample-article.md` (included), a deliberately
overconfident draft:

```
claimcheck report: sample-article.md
10 mechanical flag(s)
------------------------------------------------------------
L   3  [superlative]  "fastest"
       Agent teams are the fastest way to build software today...
       -> Superlatives are claims about the whole market. Source or soften.
L  14  [citation-stub]  "[cite]"
       Most teams see 3x productivity gains after adopting it. [cite]
       -> The draft itself admits this is unverified.
...
verdict: NEEDS EDITORIAL REVIEW
```
