# Sources

What each source measures, what it needs and what it costs. `scripts/sources.py status` reports the live state of all of them.

Every transport marked as verified was exercised from a real machine on 2026-08-06. The rest are implemented from the provider documentation and the reference implementation, and are marked as unverified until a run with credentials confirms them.

## No credential

| Source | Signal | Verified | Notes |
| --- | --- | :---: | --- |
| Hacker News | points and comments | yes | Algolia search API. Generous limits, the most reliable source here. |
| GitHub | stars, open issues | yes | Unauthenticated REST search, roughly 10 requests per minute. Repositories only, filtered by last push inside the window. |
| arXiv | none, ranked by recency | yes | Atom API over https. Throttles per address and answers 429 then 503 when pushed, so this collector waits longer between attempts. |
| Polymarket | dollars of volume | yes | Gamma public-search, open markets only. Money committed is the signal. Markets carry no date in this feed and are kept regardless of the window, because an open market is current by definition. |
| Reddit | none on the public feed | yes | `search.rss` and `top.rss`. Rate limits after a request or two from the same address, and carries no score at all. |

## Credential

| Source | Signal | Needs | Verified |
| --- | --- | --- | :---: |
| Reddit, API | score and comments | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | no |
| Bluesky | likes, reposts, replies | `BSKY_HANDLE`, `BSKY_APP_PASSWORD` | no |
| X | likes and reposts, as reported by the model | `XAI_API_KEY`, `XAI_MODEL` | no |
| TikTok | likes and comments | `SCRAPECREATORS_API_KEY` | no |
| Instagram | likes and comments | `SCRAPECREATORS_API_KEY` | no |

Reddit is the one worth configuring first: a free script app at `reddit.com/prefs/apps` turns the least reliable source into one that reports real scores. Bluesky needs an app password, never the account password. X is model mediated by design, so its items arrive with counts the model reported rather than counts an API measured, and `XAI_MODEL` is your choice because nothing in this repository pins a model.

Unauthenticated Bluesky search was tried and refused with 403, which is why it sits in this table rather than the one above.

## Binary

| Source | Signal | Needs | Verified |
| --- | --- | --- | :---: |
| YouTube | views | `yt-dlp` on the PATH | no |

Search only. This skill never downloads a video and never fetches a transcript.

## Storing a credential

Never on a command line, where it lands in the shell history and in the process list:

```
printf %s "$VALUE" | python3 scripts/sources.py set-credential REDDIT_CLIENT_SECRET
```

Resolution order is process environment, then `~/.config/topic-research/credentials.env` at mode 600, then the macOS keychain under the service name `topic-research-<KEY>`. The environment wins so a single run can override without touching disk. The keychain comes last because it is the only lookup that can block on a system prompt.

## Ranking

Engagement numbers are not comparable across sources: 300 upvotes and 300 views measure different things, and a dollar of market volume measures a third. So each source is ranked inside itself and the position becomes a 0 to 100 score. Items with no engagement signal are ranked by recency and capped at 60, so a source that cannot measure anything never outranks one that can.

The consequence to keep in mind while judging: the top item of every source gets a score near 100, however small its raw number. Read the raw number before calling anything popular.

## Deliberately absent

No browser cookie extraction, on any platform. No first run wizard that installs binaries. No publishing to any external service. No hosted search backend. These exist in the project this skill borrowed its ideas from, [last30days-skill](https://github.com/mvanhorn/last30days-skill), MIT, and each of them was left out on purpose.
