# Curation criteria

How to rank candidates, what to drop and how to format the digest. The scripts do no editorial work; every judgment below is made by the agent at digest time.

## Source tiers

| Tier | Meaning | Trust handling |
| --- | --- | --- |
| 1 | Primary or official source: vendor blogs, release notes, papers, official statements | Claims accepted as stated by the source |
| 2 | Major outlet with editorial process | Accepted; check for saturation below |
| 3 | Niche, curated or aggregator | High-signal but verify before bold claims; no unverified superlatives |

## Drop: obvious stories

A story is obvious when any of these holds:

- It is saturated: covered by several tier-2 outlets in the same window, so the reader has seen it everywhere.
- It is launch hype without substance: a product announcement with no technical detail, no numbers and no independent angle.
- It is recycled: a rewrite of an older story with no new fact.

Obvious stories are dropped unless the user's `profile.md` explicitly wants that beat. When a saturated story is truly unavoidable, keep it to one line and prefer the tier-1 version.

## Drop: repeated stories

- Same event covered by multiple outlets: keep one item, prefer the lowest tier number, then the earliest publication.
- Same story already shown in a previous digest: dropped by the scripts through `seen.json`; the agent must also catch near-duplicates the hashes miss, such as follow-ups that add nothing.

## Keep: relevant and under-reported

Boost stories that are:

- Primary-source only: official post, paper or release note that mainstream outlets have not picked up yet.
- High impact for the reader per `profile.md`: affects their tools, costs, stack or city.
- Consequential but quiet: policy, pricing, deprecations, security advisories, infrastructure changes.

## Ranking procedure

1. Drop the obvious and the repeated per above.
2. Score what remains: profile match first, tier second, novelty third.
3. Select up to `max_per_section` per section, from `config.yaml`. Fewer is fine; an empty section is omitted, never padded.

## Output template

Write in the user's language. One file per day, saved to `digests/YYYY-MM-DD.md`:

```markdown
# Digest — <weekday, date>

## <Section name as in sources.yaml>
1. **<Title>** — <one sentence: what happened>
   Why it matters: <specific consequence for this reader, never generic filler>
   Source: <feed name>, tier <n> — <link>

...
Feedback: reply with "+<n> -<n>" or free text, for example "more of item 2's kind".
```

Rules:

- "Why it matters" must name a concrete consequence. If none exists, the item should not be in the digest.
- Every item keeps the `id` from the shortlist internally so feedback and `mark-shown` can reference it.
- No section invented by the agent: sections mirror the user's `sources.yaml`.

## Feedback syntax

- `+2 -1` marks item 2 relevant and item 1 irrelevant.
- Free text ("more cost topics", "less startup gossip") goes to the same feedback log as a note on the closest items, or as a general note when no item fits.

## Validation handoff

Send the validator the draft, the raw shortlist it came from and this file's rules. The validator checks traceability, tiers, duplicates, obvious stories and rationale quality. It runs on a model different from the drafter's model; if that cannot be guaranteed, the final output must disclose it.
