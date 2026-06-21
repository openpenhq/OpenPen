# OpenPen

The Non-AI Writer for Claude and ChatGPT.

Your agent does the research. OpenPen sends the visible working context to the Non-AI Writer API and returns the final article, email, memo, page, script, or post. Optional voice instructions are applied after the source-backed draft passes.

```txt
agent conversation / research / tool outputs
  -> POST /v1/drafts
     (OpenPen resolves the writing brief internally)
  -> GET /v1/drafts/:id
  -> final draft
```

The skill is public. The API is private beta. You need an OpenPen account, API beta access, and an API key. API draft runs do not spend Playground credits during beta.

## Install

Ask your coding agent to install it:

```txt
Install OpenPen.

1. Clone https://github.com/openpenhq/OpenPen
2. Install the openpen skill for this agent.
3. Use it when I ask for a final article, email, memo, page, script, or post.
```

Or clone it yourself:

```bash
git clone https://github.com/openpenhq/OpenPen
```

Then install the `openpen/` folder in the skills directory your agent uses.

## Configure

Set these where the skill script runs:

```bash
export OPENPEN_API_KEY="naiw_live_..."
export OPENPEN_API_BASE_URL="https://your-openpen-domain.com"
```

The legacy `NON_AI_WRITER_API_KEY` and `NON_AI_WRITER_API_BASE_URL` names also work. Do not paste API keys into prompts, `SKILL.md`, or checked-in files.

## Test

From the cloned repo:

```bash
python3 openpen/scripts/non_ai_writer.py \
  --input openpen/examples/blog-context.json \
  --dry-run

python3 openpen/scripts/non_ai_writer.py \
  --input openpen/examples/blog-context.json \
  --brief-only
```

`--brief-only` calls `/v1/briefs` and does not create a draft run.

To create a real draft:

```bash
python3 openpen/scripts/non_ai_writer.py \
  --input openpen/examples/blog-context.json
```

## Use

After Claude or Codex has researched, planned, or gathered context, ask:

```txt
Use OpenPen to turn this research into the final article.
```

The agent should package visible conversation context and tool outputs, run the skill script, and return the final draft plus run id.

## Modes

OpenPen uses `mode` as the output format:

```txt
article
email
memo
page
script
post
```

If the user does not specify a mode, the skill defaults to `article`. If the user asks for a voice shift, pass it as `style.instruction`.

## What The Script Does

1. Normalizes visible agent context.
2. Calls `POST /v1/drafts` with that context.
3. Polls `GET /v1/drafts/:id`.
4. Prints the final JSON result.

`--brief-only` still calls `POST /v1/briefs` when you want to inspect the context adapter without creating a draft.

The script cannot privately read a Claude or Codex conversation by itself. The agent must pass the relevant visible context into the script.

## Requirements

- Python 3.10+
- OpenPen API key with API beta access

No Python dependencies are required.
