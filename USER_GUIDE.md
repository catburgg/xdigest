# XDigest User Guide

## Quick Start

### First Time Setup (15 minutes)

1. **Install dependencies**
   ```bash
   conda create -n xdigest python=3.13
   conda activate xdigest
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your email and followed accounts
   ```

3. **Store credentials**
   ```bash
   python setup_credentials.py
   ```
   You'll need:
   - Your X username and password
   - [Google Gemini API key](https://aistudio.google.com/app/apikey) (free)
   - [Gmail App Password](https://myaccount.google.com/apppasswords)

4. **Login to X**
   ```bash
   python main.py --login
   ```
   A browser opens. Log in manually (handle CAPTCHA/2FA). Close browser when done.

5. **Test run**
   ```bash
   python main.py
   ```
   Check your email for the digest!

6. **Install scheduler** (optional)
   ```bash
   ./install_scheduler.sh
   ```

Done! You'll now receive digests at 7 AM and 7 PM daily.

---

## Understanding XDigest

### What It Does

XDigest monitors X accounts you care about and sends you a clean, summarized email digest twice daily. No more doomscrolling!

**Example workflow:**
1. You follow @OpenAI, @karpathy, @AnthropicAI
2. At 7 AM, XDigest scrapes their latest posts
3. For each post with a link, it fetches the full article
4. Gemini AI summarizes each post in 2-3 sentences
5. You get a beautiful HTML email with all summaries

### What Gets Included

- **Text posts** — Summarized by Gemini
- **Posts with links** — Article text extracted and summarized
- **Posts with videos** — Transcript extracted (if available) and summarized
- **Posts with images** — Image analyzed by Gemini (multimodal)

### What Gets Excluded

- Retweets (only original posts)
- Replies (only top-level posts)
- Posts you've already seen (tracked by timestamp)

---

## Configuration

### Choosing Accounts to Follow

Edit `FOLLOW_ACCOUNTS` in `.env`:

```bash
FOLLOW_ACCOUNTS=OpenAI,karpathy,AnthropicAI,lexfridman
```

**Tips:**
- Use exact X usernames (no @ symbol)
- No spaces between accounts
- 10-20 accounts recommended (more = longer processing time)
- Mix of news sources and thought leaders works well

### Email Settings

For Gmail (recommended):

```bash
EMAIL_TO=your-email@gmail.com
EMAIL_FROM=your-email@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
```

**Important:** Use a [Gmail App Password](https://myaccount.google.com/apppasswords), not your regular password.

For other providers:
- **Outlook:** `smtp.office365.com:587`
- **Yahoo:** `smtp.mail.yahoo.com:587`
- **Custom SMTP:** Update host and port accordingly

### Scheduling

Default: 7 AM and 7 PM daily

To change times, edit `scheduler/com.xdigest.plist`:

```xml
<!-- Example: 9 AM and 6 PM -->
<dict>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
<dict>
    <key>Hour</key>
    <integer>18</integer>
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

Then reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.xdigest.plist
launchctl load ~/Library/LaunchAgents/com.xdigest.plist
```

---

## Common Tasks

### View Recent Digests

```bash
sqlite3 ~/.xdigest/xdigest.db "SELECT * FROM digests ORDER BY sent_at DESC LIMIT 5;"
```

### Check What's Being Scraped

```bash
# Run in non-headless mode to see the browser
# Edit .env: HEADLESS=false
python main.py
```

### Re-login to X

If you change your X password or cookies expire:

```bash
python main.py --login
```

### Test Without Sending Email

Comment out the email sending in `main.py` temporarily, or check logs to see what would be sent:

```bash
tail -f ~/.xdigest/logs/xdigest_$(date +%Y%m%d).log
```

### Reset Everything

```bash
# Remove database (starts fresh)
rm -rf ~/.xdigest/xdigest.db

# Re-login
python main.py --login

# Run again
python main.py
```

---

## Understanding Costs

### Free Tier Limits

- **Gemini API:** 15 requests/minute, 1M tokens/month (free)
- **Gmail:** 500 emails/day (free)
- **X:** No API used (scraping is free)

### Typical Usage

For 14 followed accounts, 2 digests/day:
- ~30-50 posts per digest
- ~50 Gemini API calls per digest (posts + overview)
- ~100 API calls/day
- **Well within free tier limits**

### If You Hit Limits

Gemini rate limit (15 RPM):
- Reduce followed accounts
- Increase `API_DELAY` in `summarizer/gemini_summarizer.py`
- Upgrade to paid tier ($0.075 per 1M tokens)

---

## Troubleshooting

### "No new posts found"

**This is normal!** It means:
- All accounts checked
- No posts since last digest
- Try again later

### Email not received

1. Check spam folder
2. Verify Gmail App Password: `python setup_credentials.py`
3. Check logs: `tail ~/.xdigest/logs/xdigest_*.log`
4. Test SMTP manually:
   ```python
   from email_service.sender import EmailSender
   sender = EmailSender(...)
   sender.send_digest([{'account': 'test', 'content': 'test'}])
   ```

### X login fails or gets blocked

**Method 1: Standard Login (Persistent Context)**

1. Set `HEADLESS=false` in `.env`
2. Run `python main.py --login`
3. Complete CAPTCHA/2FA manually
4. Set `HEADLESS=true` back

**Method 2: Using Real Chrome (Most Reliable)**

If X blocks the automated login, use your real Chrome browser:

**Step 1: Launch Chrome with Remote Debugging**

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-xdigest"
```

**Step 2: Log into X Manually**

In the Chrome window that opened, go to x.com and log in normally.

**Step 3: Run XDigest with --use-chrome**

```bash
conda activate xdigest
python main.py --use-chrome
```

The script will connect to your Chrome and use your logged-in session.

**Step 4: Keep Chrome Running**

Leave Chrome open while XDigest runs. You can minimize it.

**Why This Works**

X cannot detect automation because you're using your real Chrome browser with:
- Your real browsing history
- Your installed extensions
- Your normal browser fingerprint
- Your actual logged-in session

**Note:** You only need to log in once in Chrome. The session persists in the `chrome-xdigest` profile.

### Scheduler not running

```bash
# Check if loaded
launchctl list | grep xdigest

# View logs
tail -f ~/Library/Logs/xdigest.log

# Reload
launchctl unload ~/Library/LaunchAgents/com.xdigest.plist
launchctl load ~/Library/LaunchAgents/com.xdigest.plist
```

---

## Advanced Usage

### Custom Summarization Prompts

Edit prompts in `summarizer/gemini_summarizer.py`:

```python
POST_SUMMARY_PROMPT = """Your custom prompt here..."""
DIGEST_OVERVIEW_PROMPT = """Your custom overview prompt..."""
```

### Custom Email Template

Edit `templates/digest.html` to customize the email design.

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific module
python -m pytest tests/test_x_scraper.py -v
```

### Database Schema

```sql
-- View schema
sqlite3 ~/.xdigest/xdigest.db ".schema"

-- Useful queries
SELECT COUNT(*) FROM posts;
SELECT account, COUNT(*) FROM posts GROUP BY account;
SELECT * FROM state;
```

---

## Privacy & Security

### What's Stored

- **Database:** Post IDs, timestamps, content (local only)
- **Keychain:** X password, Gemini API key, SMTP password
- **Logs:** Scraping activity, errors (no passwords)

### What's Sent

- **To Gemini:** Post text, article text, video transcripts
- **To Email:** Summaries only (not raw content)

### What's NOT Stored

- No passwords in files or git
- No API keys in code
- No session cookies in plain text

---

## Getting Help

1. Check logs: `~/.xdigest/logs/`
2. Review this guide
3. Check [GitHub Issues](https://github.com/catburgg/xdigest/issues)
4. Open a new issue with logs attached

---

## Tips for Best Results

1. **Curate your follow list** — Quality over quantity
2. **Check spam folder** — First email might land there
3. **Run manually first** — Test before scheduling
4. **Monitor logs** — Catch issues early
5. **Update regularly** — `git pull` for bug fixes

Enjoy your distraction-free news digests! 📰
