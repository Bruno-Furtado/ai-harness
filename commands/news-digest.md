---
description: Build the personal news digest and deliver it as one short message.
---

Follow the `news-digest` skill and run it end to end, from collection to the delivered message.

`$ARGUMENTS` may name sections to include, for example `cloud ia`. When empty, cover every section in the user's configured sources.

Deliver the renderer's stdout exactly as printed, with no preamble, no process note and no summary of your own around it. The rendered message is the deliverable.

If the `news-digest` skill is not available in this tool, say so and stop. Do not improvise the procedure.
