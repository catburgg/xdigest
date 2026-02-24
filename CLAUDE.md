# XDigest Development Guide

## Project Overview

XDigest is an automated X (Twitter) news aggregation system that scrapes posts from followed accounts, enriches content with articles and videos, summarizes everything using Google Gemini, and sends HTML email digests twice daily.

## Development Methodology

### Phase Planning with DAG (Directed Acyclic Graph)

When planning multi-phase projects, **always draft a DAG first** to identify dependencies and maximize parallel execution.

#### XDigest Phase DAG

```
Phase 1 (Foundation)
    ├─ config/settings.py
    ├─ storage/db.py
    └─ setup_credentials.py
         │
         ├──> Phase 2 (X Scraper) ──┐
         │    └─ scraper/x_scraper.py │
         │                             │
         └──> Phase 3 (Content Enrichment) ──> Phase 4 (Gemini) ──┐
              ├─ scraper/article_fetcher.py    └─ summarizer/      │
              └─ scraper/video_processor.py       gemini_summarizer.py
                                                                    │
              Phase 5 (Email) ─────────────────────────────────────┤
              └─ email_service/sender.py                           │
                                                                    │
              Phase 6 (Orchestration) <───────────────────────────┘
              └─ main.py (wires everything together)
                   │
                   └──> Phase 7 (Deployment)
                        ├─ README.md
                        ├─ launchd plist
                        └─ Documentation
```

#### Dependency Analysis

**Sequential (must run in order):**
- Phase 1 → Phase 2 (scraper needs db/settings)
- Phase 1 → Phase 3 (enrichment needs settings)
- Phase 4 → Phase 6 (orchestration needs summarizer)
- Phase 5 → Phase 6 (orchestration needs email sender)
- Phase 6 → Phase 7 (deployment needs working pipeline)

**Parallel (can run simultaneously):**
- Phase 2 + Phase 3 (after Phase 1 completes)
- Phase 4 + Phase 5 (independent modules)

**Critical Path:** Phase 1 → Phase 3 → Phase 4 → Phase 6 → Phase 7

#### Benefits of DAG Planning

1. **Identify parallelization opportunities** — Phases 2/3 and 4/5 can be built concurrently
2. **Understand blockers** — Phase 6 can't start until 2, 3, 4, 5 are done
3. **Optimize development time** — Critical path determines minimum project duration
4. **Clear communication** — Visual representation helps explain dependencies

### Phase Summary Requirement

Before describing the next phase, always summarize the completed phase with:
- Key accomplishments
- Test counts (new + total)
- Design decisions and rationale
- Any issues encountered and how they were resolved

## Architecture

### Tech Stack

- **Python 3.13** (miniconda)
- **Playwright + playwright-stealth** — X scraping (no API)
- **trafilatura + newspaper3k** — Article extraction
- **yt-dlp + youtube-transcript-api** — Video processing
- **Google Gemini 2.0 Flash** — Multimodal summarization
- **SQLite** — State management
- **Jinja2** — Email templating
- **macOS Keychain** — Credential storage
- **launchd** — Scheduling (7 AM, 7 PM)

### Key Design Decisions

**X Login:** Manual login via visible browser. Session cookies saved to SQLite for headless reuse. User runs `--login` when cookies expire.

**Settings Pattern:** Lazy initialization via `get_settings()` function (not module-level) for proper test mocking.

**Database State:** SQLite tracks `last_sent_timestamp` (cutoff for new posts) and `session_cookies` (persisted browser session).

**Error Handling:** Graceful fallbacks throughout:
- trafilatura → newspaper3k for articles
- transcript → metadata for videos
- API failure → truncated post text for summaries

**Timestamp Update:** Only update `last_sent_timestamp` on successful email delivery to prevent data loss.

## Testing

- All modules have comprehensive unit tests
- Integration tests for main pipeline
- Run tests: `python -m pytest tests/ -v`
- Current: 112 tests passing

## Development Workflow

1. **Plan with DAG** — Identify dependencies before coding
2. **Build phase** — Implement module + tests
3. **Verify** — Run all tests
4. **Summarize** — Document accomplishments
5. **Commit & push** — Clear commit messages
6. **Next phase** — Repeat

## Security

- No secrets in code
- All credentials in macOS Keychain or `.env` (gitignored)
- GitHub token configured in `~/.claude.json`
- SMTP passwords never logged

## Repository

https://github.com/catburgg/xdigest
