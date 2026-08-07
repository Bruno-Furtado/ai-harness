---
description: Research what people said about a topic in a recent window, and report it with every claim citing a collected item.
---

Follow the `topic-research` skill and run it end to end, from the archive check to the saved report.

`$ARGUMENTS` is the topic, in any language, optionally with a window in days. When empty, ask for the topic and stop.

Deliver the renderer's stdout as the answer. It owns the references, so never write a url yourself.

If the `topic-research` skill is not available in this tool, say so and stop. Do not improvise the procedure, and do not answer from what you already knew about the topic.
