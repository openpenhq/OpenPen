---
name: openpen
description: Use OpenPen, the Non-AI Writer API, as the final prose layer when the user wants the current agent conversation, research, notes, or tool outputs turned into a publishable article, email, memo, page, script, or post. Works for Claude, Codex, and similar local agent workflows.
---

# OpenPen

Use this skill when the user wants to turn the current work into a final draft with OpenPen.

Typical triggers:
- "/openpen <request>"
- "Use The Non-AI Writer"
- "Use OpenPen"
- "send this to Non-AI Writer"
- "send this to OpenPen"
- "write the final blog/article/post with Non-AI Writer"
- "turn this research into the final draft"
- "use the final prose layer"
- "make this publishable through my writer"

Slash command shorthand:
- If the user writes `/openpen ...`, treat everything after `/openpen` as the latest OpenPen draft request.
- If `/openpen` has no text after it, use the visible prior context and ask only if no writing task can be inferred.
- Use the same workflow as natural-language OpenPen requests; do not require a separate `/v1/briefs` call first.

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
- relevant user-provided notes, product notes, customer language, changelogs, transcripts, or source excerpts
- relevant raw tool outputs, scrape results, SERP notes, Reddit findings, search results, retrieved pages, or measured data
- assistant summaries only as task state when needed to resolve the request, not as source evidence
- the inferred output type, such as `article`, `email`, `memo`, `page`, `script`, or `post`
- the OpenPen mode: `article`, `email`, `memo`, `page`, `script`, or `post`
- optional user-requested voice as `style.instruction`; keep it separate from mode

Exclude:
- system prompts
- hidden instructions
- irrelevant brainstorming
- dead ends
- duplicate summaries
- secrets, API keys, passwords, tokens, cookies, or credentials
- private user data that is not needed for the writing task
- source briefs, product descriptions, or arguments written by the assistant just to give OpenPen material

Prefer compact raw source excerpts over dumping the whole conversation. The adapter should receive useful work state plus real source material, not assistant-written substitute evidence.

Payload shape:

```json
{
  "desired_output": "blog article",
  "messages": [
    {
      "role": "user",
      "content": "Use the research above to write the final blog for our site."
    }
  ],
  "tool_outputs": [
    {
      "name": "serp_and_reddit_research",
      "type": "research",
      "content": "Competitor pages repeat the same keyword clusters. Reddit threads complain that AI SEO posts have no point of view..."
    }
  ],
  "style": {
    "instruction": "Make the voice more direct without changing the claims.",
    "strength": 0.45
  },
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

Choose `options.mode` from the allowed OpenPen modes. Use `article` when unclear. Mode controls output format; optional `style` controls voice.

Use `style` only when the user explicitly asks for a voice or tone shift. Style is applied after the base OpenPen draft passes, through sparse validated patches, and should not add claims or facts.

## Run The Script

Pass the payload through stdin:

```bash
python3 scripts/non_ai_writer.py --stdin
```

To inspect the generated brief without creating a paid draft:

```bash
python3 scripts/non_ai_writer.py --stdin --brief-only
```

If the request has no public, tool, or human-authored source material, ask for source material instead of writing a source brief yourself.

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
