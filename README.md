# The Non-AI Writer Agent Skill

Give Claude or Codex a final writing layer.

Your agent does the research. This skill sends the visible working context to The Non-AI Writer and returns the final article, SEO brief, landing page section, newsletter, email, script, memo, or post.

```txt
agent conversation / research / tool outputs
  -> POST /v1/briefs
  -> POST /v1/drafts
  -> GET /v1/drafts/:id
  -> final draft
```

The skill is public. The API is private beta. You need a Non-AI Writer account, credits, API beta access, and an API key.

## Install

Ask your coding agent to install it:

```txt
Install The Non-AI Writer Agent Skill.

1. Clone https://github.com/CKaps1/non-ai-writer-agent-skill
2. Install the non-ai-writer skill for this agent.
3. Use it when I ask for a final article, SEO brief, landing page section, newsletter, email, script, memo, or post.
```

Or clone it yourself:

```bash
git clone https://github.com/CKaps1/non-ai-writer-agent-skill
```

Then install the `non-ai-writer/` folder in the skills directory your agent uses.

## Configure

Set these where the skill script runs:

```bash
export NON_AI_WRITER_API_KEY="naiw_live_..."
export NON_AI_WRITER_API_BASE_URL="https://your-non-ai-writer-domain.com"
```

Do not paste API keys into prompts, `SKILL.md`, or checked-in files.

## Test

From the cloned repo:

```bash
python3 non-ai-writer/scripts/non_ai_writer.py \
  --input non-ai-writer/examples/blog-context.json \
  --dry-run

python3 non-ai-writer/scripts/non_ai_writer.py \
  --input non-ai-writer/examples/blog-context.json \
  --brief-only
```

`--brief-only` calls `/v1/briefs` and does not spend a draft credit.

To create a real draft:

```bash
python3 non-ai-writer/scripts/non_ai_writer.py \
  --input non-ai-writer/examples/blog-context.json
```

## Use

After Claude or Codex has researched, planned, or gathered context, ask:

```txt
Use The Non-AI Writer to turn this research into the final article.
```

The agent should package visible conversation context and tool outputs, run the skill script, and return the final draft plus run id.

## What The Script Does

1. Normalizes visible agent context.
2. Calls `POST /v1/briefs`.
3. Sends the returned `draft_request` to `POST /v1/drafts`.
4. Polls `GET /v1/drafts/:id`.
5. Prints the final JSON result.

The script cannot privately read a Claude or Codex conversation by itself. The agent must pass the relevant visible context into the script.

## Requirements

- Python 3.10+
- The Non-AI Writer API key
- API beta access
- Credits for real draft runs

No Python dependencies are required.
