# XDigest Product Requirements

## Overview
XDigest is an automated X (Twitter) news aggregation system that helps users stay informed without doomscrolling.

---

## User Needs & Insights

### 1. Email Overlap Strategy (Non-Incremental Scraping)
**Date**: 2026-02-25
**Context**: Users may be busy and miss scheduled emails
**User Story**: As a busy professional, I want each digest to contain the last 24 hours of posts, so that even if I miss one email, I won't miss important content.

**Key Insights**:
- Users don't always read emails immediately when they arrive
- Missing one email shouldn't mean missing content permanently
- 12-hour overlap between digests is acceptable (better than missing content)
- Duplicate content in consecutive emails is preferable to gaps

**Implementation**:
- Always scrape posts from last 24 hours (not incremental)
- Remove database deduplication checks
- Clean up all posts after email sent
- Schedule: 7 AM and 7 PM daily (12h overlap)

**Trade-offs**:
- ✅ Users never miss content
- ✅ Simple logic (no complex state management)
- ⚠️ Some duplicate content if user reads both emails
- ⚠️ Slightly more API calls to Gemini (acceptable within free tier)

---

### 2. X Login Detection Bypass (CDP Mode)
**Date**: 2026-02-25
**Context**: X aggressively blocks automated logins, even with stealth mode
**User Story**: As a user, I want to log in once manually and have the scraper use my session, so I don't get blocked by X's anti-bot detection.

**Key Insights**:
- X can detect Playwright even with stealth mode and persistent context
- Users are willing to keep Chrome open if it means reliable scraping
- CDP (Chrome DevTools Protocol) is completely undetectable because it uses real Chrome
- One-time manual login is acceptable for long-term reliability

**Implementation**:
- Add `--use-chrome` flag to connect via CDP
- User launches Chrome with `--remote-debugging-port=9222`
- User logs in manually once
- Script connects to existing Chrome session
- No automation markers visible to X

**Trade-offs**:
- ✅ 100% reliable (X cannot detect)
- ✅ Free solution (no paid APIs)
- ✅ User logs in once, session persists
- ⚠️ Requires Chrome to be running during scraping
- ⚠️ Slightly more complex setup (but documented)

---

### 3. Database Cleanup Strategy
**Date**: 2026-02-25
**Context**: With non-incremental scraping, we don't need historical post data
**User Story**: As a system administrator, I want the database to stay small, so the application remains fast and doesn't consume unnecessary disk space.

**Key Insights**:
- With 24h scraping, we don't need old posts for deduplication
- Only need to track when last email was sent (for monitoring)
- Keep minimal digest history for troubleshooting

**Implementation**:
- Delete ALL posts after successful email send
- Keep only last 5 digest records
- Preserve `last_sent_timestamp` for tracking

**Trade-offs**:
- ✅ Minimal disk usage
- ✅ Fast database operations
- ⚠️ Can't query historical posts (acceptable - they're in emails)

---

## Future Considerations

### Potential Features (Not Yet Implemented)
- **Custom time windows**: Allow users to configure scraping window (12h, 24h, 48h)
- **Account prioritization**: Mark certain accounts as "must include"
- **Content filtering**: Skip posts with certain keywords
- **Digest preview**: Generate preview without sending email
- **Multiple recipients**: Send to multiple email addresses
- **Digest frequency**: Allow custom schedules (not just 7 AM/7 PM)

### Known Limitations
- **Video transcripts**: Only works for YouTube (not X native videos)
- **Image analysis**: Requires Gemini multimodal (implemented but not tested extensively)
- **Rate limits**: Gemini free tier (15 RPM, 1M tokens/month) - sufficient for 14 accounts
- **X rate limits**: Unknown, but CDP mode reduces risk of blocks

---

## Success Metrics

### User Experience
- ✅ User never misses important posts
- ✅ Login works reliably without blocks
- ✅ Emails arrive on schedule (7 AM, 7 PM)
- ✅ Summaries are accurate and concise

### Technical
- ✅ Database stays under 10 MB
- ✅ Scraping completes in < 5 minutes
- ✅ No X blocks or CAPTCHA challenges
- ✅ Email delivery success rate > 99%

---

## Design Principles

1. **Reliability over efficiency**: Better to have overlap than miss content
2. **User control**: Manual login is acceptable if it means no blocks
3. **Simplicity**: Avoid complex state management when simple solutions work
4. **Transparency**: Clear logs and error messages
5. **Fail-safe**: If email fails, don't update timestamp (retry next time)
