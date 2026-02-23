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

### 1. Create Conda Environment

```bash
conda create -n xdigest python=3.13
conda activate xdigest
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Set Up Credentials

Run the setup script to store sensitive credentials in macOS Keychain:

```bash
python setup_credentials.py
```

You'll be prompted for:
- X username and password
- Google Gemini API key
- SMTP password (e.g., Gmail app password)

### 5. Test Run

```bash
python main.py
```

### 6. Install Scheduler (Optional)

To run automatically at 7 AM and 7 PM:

```bash
cp scheduler/com.xdigest.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.xdigest.plist
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

## Troubleshooting

### X Login Issues

If X login fails due to CAPTCHA or 2FA:

1. Run with `HEADLESS=false` in `.env` to see the browser
2. Complete login manually
3. Session cookies will be saved for future runs

### Rate Limiting

Gemini free tier: 15 RPM, 1M TPM. For 50-100 posts twice daily, this is sufficient. If you hit limits, the app will retry with exponential backoff.

### Email Deliverability

- Use Gmail app passwords (not your main password)
- Check spam folder on first run
- Ensure `EMAIL_FROM` matches your SMTP account

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
