# Curation criteria

How to rank candidates, what to drop and what to emit. The scripts do no editorial work; every judgment below is made by the agent at digest time.

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

Obvious stories are dropped unless the user's `profile.md` explicitly wants that beat. When a saturated story is truly unavoidable, prefer the tier-1 version.

## Drop: repeated stories

- Same event covered by multiple outlets: keep one item, prefer the lowest tier number, then the earliest publication.
- Same story already shown in a previous digest: dropped by the scripts through `seen.json`; the agent must also catch near-duplicates the hashes miss, such as follow-ups that add nothing.

## Keep: relevant and under-reported

Boost stories that are:

- Primary-source only: official post, paper or release note that mainstream outlets have not picked up yet.
- High impact for the reader per `profile.md`: affects their tools, costs, stack or city.
- Consequential but quiet: policy, pricing, deprecations, security advisories, infrastructure changes.

## Language is not a selection criterion

Sources may be in any language, and the source language is never a reason to prefer or drop a candidate. A tier-1 post in Chinese outranks a tier-2 rewrite in the reader's own language. The translation happens at write time, below.

## Against the bubble

A digest that always draws from the same five feeds trains the reader to expect one worldview. On a tie in relevance, take the candidate whose source has gone longest without appearing. `stats.json` records `last_shown` per feed, so this is a lookup, not a hunch, and `run_digest.py` passes the stalest sources into the selection prompt.

This breaks ties only. It never promotes a weak story over a strong one: variety is a tiebreaker, not a quota.

## Sections have an intent, not just a name

An item's section comes from the feed that carried it, never from its content, and feeds are often broader than the section they sit in. A construction industry feed placed under a home financing section will offer workplace safety rules: correctly filed, and wrong for the reader.

Each section in `sources.yaml` may carry a `focus` line saying what it is for and what it is not for. A candidate that does not match its section's focus is dropped. It cannot be moved, because moving it would invent a section assignment the feed does not support, so a misfit is always a drop.

## Politics: what counts as relevant

Keep what changes a rule, a tax, an interest rate, a contract, a public price or the technology sector, and what a reader would act on. Leave out electoral horse race, poll movement and backroom manoeuvring, which are abundant and change nothing for the reader by tomorrow.

## Ranking procedure

1. Drop the obvious and the repeated per above.
2. Score what remains: profile match first, tier second, novelty third, source staleness as the tiebreaker.
3. Select up to `max_per_section` per section and never more than `max_items` in total, both from `config.yaml`. Fewer is fine; an empty section is omitted, never padded. When the two caps collide, `max_items` wins and the weakest sections lose their slot.

## Output contract

The agent does not write the digest. It emits one selection line per chosen item, in ranked order, and `render_digest.py` produces both the delivered message and the archive:

```
<id>|<title>|<why>
```

- `<id>` is the id from the compact shortlist, copied exactly. An id that is not in the shortlist is dropped by the renderer.
- `<title>` is the headline rewritten in `digest_language`, at most about 60 characters. It becomes the link text, so it carries the news by itself.
- `<why>` is the concrete consequence for this reader, at most 12 words. The renderer truncates anything longer.

Nothing else goes to stdout: no urls, no preamble, no section headers, no closing note, no code fence. The renderer resolves url, source, tier and section from the id, which is why an invented link cannot reach the reader.

Writing rules, enforced by the renderer and worth following at the source:

- Everything is written in `digest_language`, whatever language the source used. Do not leave the original headline in, not even in parentheses. Proper nouns, product names and acronyms stay as they are.
- No em dash, and no hyphen used as punctuation. A hyphen inside a word is fine.
- No emoji anywhere.
- "Why" names a concrete consequence. If there is none, the item does not belong in the digest, and a filler line like "important for the sector" is worse than dropping the item.

## Feedback syntax

- `+2 -1` marks the item numbered 2 relevant and the item numbered 1 irrelevant. The numbers are the ones printed in the delivered message, resolved through `.last_digest.json`.
- Free text ("more cost topics", "less startup gossip") is recorded once as a general note.
- Both forms go in through `state.py feedback --from-last "<the reply>"`.

## Validation handoff

Send the validator the selection lines and the compact shortlist they came from, nothing else. Link, tier and section correctness are mechanical now, so the validator judges what the renderer cannot: duplicates, obvious stories, filler rationales, wrong section, and translations that leaked the source language or lost the meaning. It runs on a model different from the drafter's model; if that cannot be guaranteed, the final output must disclose it.
