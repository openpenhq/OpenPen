# The Non-AI Writer Agent Skill

This package makes The Non-AI Writer usable from Claude, Codex, and similar local agent workflows.

It does not ask the user to manually rewrite their prompt. The agent gathers the relevant current conversation and tool context, passes that compact context to the script, and the script runs the full API flow:

```txt
agent conversation / research / tool outputs
  -> POST /v1/briefs
  -> POST /v1/drafts
  -> GET /v1/drafts/:id
  -> final draft
```

## Setup

Set these environment variables where the skill script runs:

```bash
export NON_AI_WRITER_API_KEY="naiw_live_..."
export NON_AI_WRITER_API_BASE_URL="https://your-production-domain.com"
```

Do not hardcode API keys inside `SKILL.md` or scripts.

## Test Locally

From this directory:

```bash
python3 scripts/non_ai_writer.py --input examples/blog-context.json --dry-run
python3 scripts/non_ai_writer.py --input examples/blog-context.json --brief-only
python3 scripts/non_ai_writer.py --input examples/blog-context.json
```

Use `--brief-only` to verify the adapter output without consuming a draft credit.

## Claude Or Codex Usage

Once this skill is installed, the user can say:

```txt
Use The Non-AI Writer to turn this research into the final blog post.
```

The agent should:

1. Extract the relevant visible conversation context.
2. Summarize tool/research outputs into `tool_outputs`.
3. Infer `desired_output`.
4. Run `scripts/non_ai_writer.py --stdin`.
5. Return the final draft and run id.

The script cannot privately fetch a Claude or Codex conversation on its own. The agent must pass the visible context into the script. That is what the skill instructions enforce.

## Output Contract

Successful full run:

```json
{
  "ok": true,
  "mode": "draft",
  "brief": {},
  "run": {
    "id": "...",
    "status": "succeeded",
    "draft": {
      "text": "...",
      "format": "markdown"
    }
  }
}
```

Brief-only run:

```json
{
  "ok": true,
  "mode": "brief",
  "brief": {
    "ready": true,
    "draft_request": {}
  }
}
```

If `ready` is false, ask the returned `clarification_question`.
