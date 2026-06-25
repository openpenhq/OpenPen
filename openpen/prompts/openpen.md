---
description: Send the request and visible context through OpenPen
argument-hint: "<writing request>"
---

Use the OpenPen skill for this request:

$ARGUMENTS

Treat the text after the command as the latest OpenPen draft request. Build the payload from visible conversation context and tool outputs according to the OpenPen skill instructions.

If the command has no arguments, use the visible prior context and ask only if no writing task can be inferred.

Do not write substitute source material yourself. If the request has no usable public, tool, or human-authored source material, ask for source material instead.
