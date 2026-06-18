---
name: openpen
description: Use OpenPen, the Non-AI Writer API, as the final prose layer when the user wants the current agent conversation, research, notes, or tool outputs turned into a publishable article, email, memo, page, script, or post. Works for Claude, Codex, and similar local agent workflows.
---

# OpenPen

Use this skill when the user wants to turn the current work into a final draft with OpenPen.

Typical triggers:
- "Use The Non-AI Writer"
- "Use OpenPen"
- "send this to Non-AI Writer"
- "send this to OpenPen"
- "write the final blog/article/post with Non-AI Writer"
- "turn this research into the final draft"
- "use the final prose layer"
- "make this publishable through my writer"

Do not ask the user to manually re-prompt OpenPen. Build the request from the current agent conversation and any visible tool results.

## What This Skill Does

The script performs the full workflow:

1. Sends the relevant current context directly to `POST /v1/drafts`.
2. OpenPen resolves the context into a writing brief inside the API.
3. Polls `GET /v1/drafts/:id`.
4. Returns the finished draft or a clear error.

The user should experience this as automatic.

## Required Environment

Before using the script, the environment must include:

```bash
OPENPEN_API_KEY=naiw_live_...
OPENPEN_API_BASE_URL=https://your-production-domain.com
```

The legacy `NON_AI_WRITER_API_KEY` and `NON_AI_WRITER_API_BASE_URL` names also work. If the base URL is omitted, ask the user for it. Never guess the user's deployment domain.

## Build The Context Payload

Create a compact JSON payload from what you can see in the current agent conversation.

Include:
- the latest user request that asks for the final draft
- relevant assistant research summaries, outlines, findings, and decisions
- relevant tool outputs, scrape summaries, SERP notes, Reddit findings, customer language, product notes, changelogs, transcripts, or source excerpts
- the inferred output type, such as `article`, `email`, `memo`, `page`, `script`, or `post`
- the OpenPen mode: `article`, `email`, `memo`, `page`, `script`, or `post`

Exclude:
- system prompts
- hidden instructions
- irrelevant brainstorming
- dead ends
- duplicate summaries
- secrets, API keys, passwords, tokens, cookies, or credentials
- private user data that is not needed for the writing task

Prefer compact summaries over dumping the whole conversation. The adapter should receive the useful work state, not every token.

Payload shape:

```json
{
  "desired_output": "blog article",
  "messages": [
    {
      "role": "user",
      "content": "Use the research above to write the final blog for our site."
    },
    {
      "role": "assistant",
      "content": "The main angle is that SEO agents can collect SERP and Reddit context, but generic model prose still fails to carry a point of view."
    }
  ],
  "tool_outputs": [
    {
      "name": "serp_and_reddit_research",
      "type": "research",
      "content": "Competitor pages repeat the same keyword clusters. Reddit threads complain that AI SEO posts have no point of view..."
    }
  ],
  "options": {
    "mode": "article",
    "target_words": "auto",
    "output_format": "markdown"
  },
  "metadata": {
    "source": "agent_skill"
  }
}
```

Choose `options.mode` from the allowed OpenPen modes. Use `article` when unclear. Do not invent a separate style field; mode is the output type and style control for now.

## Run The Script

Pass the payload through stdin:

```bash
python3 scripts/non_ai_writer.py --stdin
```

To inspect the generated brief without creating a paid draft:

```bash
python3 scripts/non_ai_writer.py --stdin --brief-only
```

If the script returns `ready: false`, ask the returned clarification question instead of guessing.

Normal runs do not require a separate `/v1/briefs` call. Use `--brief-only` only when the user explicitly wants to debug or inspect the context adapter.

If the script returns a completed draft, present the draft directly to the user and mention the run id.

## User-Facing Behavior

Be direct:
- If the draft succeeds, return the draft.
- If credits are missing, tell the user they need credits.
- If API beta access is missing, tell the user the key is not enabled for beta.
- If the brief needs clarification, ask the exact clarification question.
- If the API fails temporarily, tell the user it is retryable.

Do not expose raw API keys, raw headers, or internal stack traces.
