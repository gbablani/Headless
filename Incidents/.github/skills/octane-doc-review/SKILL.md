---
name: octane-doc-review
description: Multi-agent document review with deliberation. Multiple LLM reviewers analyze a Markdown document in parallel, debate feedback through structured rounds, reach consensus (or bounded disagreement), and produce a revised document with an auditable review report.
metadata:
  author: Lucio Cunha Tinoco
  version: "1.0.0"
---

# Document Review

Multi-agent deliberation workflow for technical documentation review. Uses multiple LLM reviewers with different models to surface issues that any single model would miss, then iterates through structured debate rounds until consensus.

> **This workflow is long-running** — typically 3–10 minutes depending on document length and deliberation rounds. You MUST use `read_file` to load the full conductor skill instructions from the installed conductor skill's `SKILL.md` and follow its execution procedure exactly. **Always launch with `conductor --silent run ... --web-bg`** — this prints a dashboard URL to stdout. **You MUST capture and display the dashboard URL to the user** so they can monitor the workflow in real time.

## Prerequisites

- `conductor` skill — you MUST use `read_file` to load the installed conductor skill's `SKILL.md` for installation and execution details. Check both `~/.copilot/skills/conductor/SKILL.md` (user-level) and `.github/skills/conductor/SKILL.md` (workspace-level). Do NOT run `conductor --version` to check; just run the workflow directly and install only if the command fails.

## Workflow

One workflow template is included in [`assets/`](assets/) (relative to this skill):

| Workflow | Purpose | Key Inputs |
|----------|---------|------------|
| [`doc-review.yaml`](assets/doc-review.yaml) | Multi-agent document review with deliberation | `document_path` (required), optional `focus`, `exclude`, `max_rounds`, `guidelines_path`, `output_dir` |

## Quick Reference

```bash
# Basic review
conductor --silent run assets/doc-review.yaml \
  --input document_path="docs/auth-redesign.md" --web-bg

# Review with focus areas
conductor --silent run assets/doc-review.yaml \
  --input document_path="docs/api-spec.md" \
  --input focus="Focus on security and completeness" --web-bg

# Review with exclusions
conductor --silent run assets/doc-review.yaml \
  --input document_path="docs/design.md" \
  --input exclude='["formatting"]' --web-bg

# Review with custom guidelines
conductor --silent run assets/doc-review.yaml \
  --input document_path="docs/design.md" \
  --input guidelines_path="team/REVIEW_STANDARDS.md" --web-bg

# Review with limited rounds
conductor --silent run assets/doc-review.yaml \
  --input document_path="docs/design.md" \
  --input max_rounds=2 --web-bg

# Custom output directory
conductor --silent run assets/doc-review.yaml \
  --input document_path="docs/design.md" \
  --input output_dir="reviews/" --web-bg
```

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `document_path` | string | Yes | — | Path to the Markdown document to review |
| `focus` | string | No | `""` | Natural language review focus (e.g., `"Focus on security and clarity"`) |
| `exclude` | array | No | `[]` | Aspects to de-prioritize in review |
| `guidelines_path` | string | No | `REVIEW_GUIDELINES.md` | Path to review guidelines file |
| `max_rounds` | number | No | `2` | Maximum deliberation rounds (1-20) |
| `output_dir` | string | No | `""` (same dir as input) | Output directory for artifacts. If empty, writes next to the input document. |

## Review Aspects

Unless restricted via `focus` or `exclude`, reviewers analyze:

| Aspect | What it covers |
|--------|---------------|
| **Structure** | Missing sections, poor organization, unclear audience |
| **Clarity** | Ambiguous language, undefined jargon, unstated assumptions |
| **Completeness** | Gaps in reasoning, missing edge cases, unanswered questions |
| **Accuracy** | Internal contradictions, unsupported claims |
| **Actionability** | Vague next steps, unclear ownership, missing success criteria |
| **Formatting** | Broken links, inconsistent heading levels, markdown issues |

## Architecture

```
dispatcher ──→ initial_review (parallel) ──→ deliberation rounds (sequential)
                  │                              │
                  ├── reviewer_1 (Opus)          ├── delib_reviewer_1 ──→ delib_reviewer_2 ──→ arbitrator
                  └── reviewer_2 (GPT-5.2)      │                                              │
                                                 │    ┌─── consensus? ──→ proofreader ──→ output_writer ──→ $end
                                                 │    │    max rounds? ──→ proofreader ──→ output_writer ──→ $end
                                                 └────┘    otherwise   ──→ loop back to deliberation
```

- **Dispatcher**: Reads document and guidelines via MCP filesystem tools
- **Reviewers**: Analyze document in parallel from different model perspectives
- **Deliberation**: Sequential turn-taking — reviewers respond to each other's feedback
- **Arbitrator**: Evaluates consensus, incorporates agreed changes, decides whether to loop
- **Proofreader**: Final quality pass comparing revised document against original
- **Output Writer**: Writes revised document and review report to disk

## Output

Two artifacts are produced next to the input document by default (or in `output_dir` if specified):

| File | Description |
|------|-------------|
| `<name>.revised.md` | Final proofread document with agreed changes |
| `<name>.review-report.md` | Full review report: round-by-round deliberation, agreed changes, unresolved disagreements, proofreader notes |

## Post-Completion

After the workflow finishes, the output file paths are included in the workflow’s JSON result (`revised_document_path` and `review_report_path`). If you are an agent running this workflow on behalf of a user:

1. **Display the output paths** to the user so they can find the files.
2. **Open both output files** in the user’s editor if you have access to editor commands (e.g., VS Code’s `open file` capability). This gives the user immediate access to the review results without navigating the file tree.
3. If editor integration is not available (e.g., running from CLI or CI), print the absolute paths to stdout.

## Configuration

Place a `.doc-review.yaml` in your repo root or project directory to set defaults. See the template at the repo root for the full schema.

## Guidelines

Create a `REVIEW_GUIDELINES.md` in your repo root with team-specific review criteria. The reviewers will incorporate these guidelines into their analysis. See the example template at the repo root.

## Tips

- **Start with defaults** — the 2-reviewer, 2-round configuration works well for most documents
- **Use focus areas** — narrow the review to specific aspects for faster, more targeted feedback
- **Watch the dashboard** — use `--web-bg` to monitor deliberation progress in real time
- **Custom guidelines** — invest in a good `REVIEW_GUIDELINES.md` for consistent, team-aligned reviews
- **Contentious documents** — lower `max_rounds` to 2-3 if you expect significant disagreement and want faster results
