# XDigest

Automated X (Twitter) news aggregation app that scrapes posts from specific accounts, summarizes them using Google Gemini AI, and sends clean HTML email digests twice daily.

## Features

- 🤖 **Automated Scraping**: Uses Playwright to scrape X posts (no API required)
- 🧠 **AI Summarization**: Google Gemini API for multimodal content summarization
- 📧 **Email Digests**: Beautiful HTML emails sent at 7 AM and 7 PM daily
- 🔒 **Secure**: Credentials stored in macOS Keychain
- 📊 **Smart Tracking**: Only includes new posts since last digest
- 🎯 **Content Enrichment**: Fetches and summarizes linked articles and videos

## Architecture

```
xdigest/
├── config/              # Configuration and settings
├── scraper/             # X scraping, article/video fetching
├── summarizer/          # Gemini API integration
├── email_service/       # Email rendering and sending
├── storage/             # SQLite state management
├── scheduler/           # macOS launchd configuration
└── main.py             # Orchestration entry point
```

## Tech Stack

- **Python 3.13** via miniconda
- **Playwright** + playwright-stealth for X scraping
- **Google Gemini API** (gemini-2.0-flash) for summarization
- **trafilatura** + newspaper3k for article extraction
- **yt-dlp** + youtube-transcript-api for video processing
- **SQLite** for state management
- **macOS launchd** for scheduling

## Installation

### Prerequisites

- macOS (for Keychain and launchd)
- Python 3.13+ (via miniconda recommended)
- Google Gemini API key ([get one free](https://aistudio.google.com/app/apikey))
- Gmail account with App Password ([setup guide](https://support.google.com/accounts/answer/185833))

### 1. Clone Repository

```bash
git clone https://github.com/catburgg/xdigest.git
cd xdigest
```

### 2. Create Conda Environment

```bash
conda create -n xdigest python=3.13
conda activate xdigest
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# X Accounts to follow (comma-separated, no spaces)
FOLLOW_ACCOUNTS=OpenAI,AnthropicAI,xAI,a16z,ycombinator,karpathy

# Email Configuration
EMAIL_TO=your-email@gmail.com
EMAIL_FROM=your-email@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com

# Scraping Configuration
HEADLESS=true
SCROLL_PAUSE=2
MAX_SCROLLS=10
```

### 5. Set Up Credentials

Run the setup script to store sensitive credentials in macOS Keychain:

```bash
python setup_credentials.py
```

You'll be prompted for:
- **X username** (your X/Twitter username)
- **X password** (your X/Twitter password)
- **Google Gemini API key** (from Google AI Studio)
- **SMTP password** (Gmail App Password, NOT your regular Gmail password)

### 6. Initial X Login

XDigest needs to log into X once to save session cookies:

```bash
python main.py --login
```

A browser window will open. Complete the login manually (including any CAPTCHA or 2FA). Once logged in, close the browser. Session cookies are now saved for future headless runs.

### 7. Test Run

```bash
python main.py
```

This will:
1. Scrape posts from your followed accounts
2. Fetch and process linked articles/videos
3. Generate summaries with Gemini
4. Send an email digest to your configured address

Check your email (and spam folder) for the digest!

### 8. Install Scheduler (Optional)

To run automatically at 7 AM and 7 PM daily:

```bash
# Install the launchd plist
./install_scheduler.sh

# Verify it's loaded
launchctl list | grep xdigest
```

To uninstall:

```bash
launchctl unload ~/Library/LaunchAgents/com.xdigest.plist
rm ~/Library/LaunchAgents/com.xdigest.plist
```

## Configuration

### Followed Accounts

Edit `FOLLOW_ACCOUNTS` in `.env`:

```
FOLLOW_ACCOUNTS=elonmusk,OpenAI,AndrewYNg,karpathy
```

### Email Settings

Configure SMTP in `.env`:

```
EMAIL_TO=your-email@example.com
EMAIL_FROM=xdigest@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

For Gmail, create an [App Password](https://support.google.com/accounts/answer/185833).

## How It Works

1. **Scrape**: Playwright logs into X and scrapes posts from followed accounts
2. **Enrich**: Fetches full text from linked articles and video transcripts
3. **Summarize**: Gemini API generates concise summaries of each post and overall digest
4. **Email**: Renders HTML email with summaries and sends via SMTP
5. **Track**: Updates SQLite database with timestamp to avoid duplicates

## Security

- All sensitive credentials stored in macOS Keychain (never in code or git)
- `.env` file excluded from git
- Database stored in `~/.xdigest/` (outside project directory)
- Session cookies encrypted in SQLite

## Usage

### Manual Run

```bash
# Activate conda environment
conda activate xdigest

# Run digest generation
python main.py
```

### Re-login to X

If your X session expires (cookies become invalid):

```bash
python main.py --login
```

### View Logs

Logs are stored in `~/.xdigest/logs/`:

```bash
tail -f ~/.xdigest/logs/xdigest_$(date +%Y%m%d).log
```

### Check Database

```bash
sqlite3 ~/.xdigest/xdigest.db

# View recent digests
SELECT * FROM digests ORDER BY sent_at DESC LIMIT 5;

# View recent posts
SELECT account, content, timestamp FROM posts ORDER BY timestamp DESC LIMIT 10;

# Check last sent timestamp
SELECT * FROM state WHERE key = 'last_sent_timestamp';
```

## Troubleshooting

### X Login Issues

**Problem:** Login fails with CAPTCHA or 2FA

**Solution:**
1. Set `HEADLESS=false` in `.env`
2. Run `python main.py --login`
3. Complete CAPTCHA/2FA manually in the browser
4. Session cookies will be saved
5. Set `HEADLESS=true` back in `.env`

**Problem:** "No cookies found" error

**Solution:** Run `python main.py --login` to create a new session.

### Email Issues

**Problem:** Email not received

**Solutions:**
- Check spam folder
- Verify Gmail App Password is correct (not your regular password)
- Ensure `EMAIL_FROM` matches `SMTP_USER`
- Check logs for SMTP errors: `tail ~/.xdigest/logs/xdigest_*.log`

**Problem:** "Authentication failed" SMTP error

**Solution:**
1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
2. Generate a new App Password
3. Run `python setup_credentials.py` and enter the new password

### Gemini API Issues

**Problem:** "API key invalid" error

**Solution:**
1. Get a new API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Run `python setup_credentials.py` and enter the new key

**Problem:** Rate limit errors

**Solution:** Gemini free tier has 15 RPM limit. The app includes 1-second delays between requests. If you still hit limits, reduce the number of followed accounts or upgrade to paid tier.

### No New Posts

**Problem:** "No new posts found" message

**Explanation:** This is normal! It means:
- All followed accounts have been checked
- No posts were found since the last digest
- The app will check again on the next scheduled run

### Scraping Issues

**Problem:** Posts not being scraped

**Solutions:**
1. Check if X changed their HTML structure (run with `HEADLESS=false` to debug)
2. Verify followed accounts exist and are public
3. Check if you're rate-limited by X (wait 1 hour and try again)
4. Re-login: `python main.py --login`

### Scheduler Issues

**Problem:** Scheduled runs not working

**Solutions:**
```bash
# Check if launchd job is loaded
launchctl list | grep xdigest

# View launchd logs
tail -f ~/Library/Logs/xdigest.log

# Reload the job
launchctl unload ~/Library/LaunchAgents/com.xdigest.plist
launchctl load ~/Library/LaunchAgents/com.xdigest.plist
```

**Problem:** Wrong Python environment used

**Solution:** Edit `com.xdigest.plist` and update the Python path to your conda environment:
```bash
which python  # Run this in your activated conda env
# Copy the path and update it in the plist file
```

## Development

### Project Structure

- `config/settings.py` - Configuration loader
- `scraper/x_scraper.py` - Playwright-based X scraper
- `scraper/article_fetcher.py` - Article text extraction
- `scraper/video_processor.py` - Video transcript extraction
- `summarizer/gemini_summarizer.py` - Gemini API integration
- `email_service/sender.py` - SMTP email sender
- `storage/db.py` - SQLite state management
- `main.py` - Orchestration logic

### Running Tests

```bash
# Test X scraping
python -m scraper.x_scraper

# Test article fetching
python -m scraper.article_fetcher

# Test Gemini summarization
python -m summarizer.gemini_summarizer
```

## License

MIT

## Contributing

Pull requests welcome! Please open an issue first to discuss major changes.
