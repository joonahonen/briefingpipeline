# Briefing Pipeline

A Python pipeline that builds a daily AI-generated morning briefing and delivers it to a Notion database. It combines weather (Oulu), world news, and technology news before using Google Gemini API to format the final briefing for a mobile screen. The delivery was formerly done through a Telegram bot, code has been modified to support Notion.

## What it does

The pipeline:

1. Fetches today's high and low temperatures from Open-Meteo.
2. Downloads and parses calendar events from an ICS URL.
3. Reads world news from The Guardian's world RSS feed.
4. Reads technology news from TechCrunch's RSS feed.
5. Uses Google Gemini to select and summarize:
   - The two most important world-news articles.
   - The top technology-news article.
6. Sends the formatted briefing to a Telegram chat.

## Project structure

```text
.
├── main.py                         # Data collection, AI generation, and Notion delivery
├── requirements.txt                # Python dependencies
└── .github/
    └── workflows/
        └── daily_briefing.yml      # Scheduled GitHub Actions workflow
```

## Requirements

- Python 3.11 or newer
- A Google Gemini API key
- A Notion API token
- A Database ID
- An optional publicly accessible calendar ICS URL

## Configuration

The application reads configuration from environment variables:

| Variable | Required | Description |
|---|---:|---|
| `GEMINI_API_KEY` | Yes | API key used to access Google Gemini |
| `NOTION_TOKEN` | Yes for Notion delivery | Token for the Notion API |
| `NOTION_DATABASE_ID` | Yes for Notion delivery | Notion database that receives the briefing |
| `CALENDAR_ICS_URL` | No | URL of an ICS calendar feed |

The weather location is currently fixed in `main.py` to the coordinates of Oulu, Finland:

- Latitude: `65.01`
- Longitude: `25.47`

These coordinates are used by Open-Meteo to retrieve the forecast.


## Limitations and potential improvements

- The weather coordinates are hard-coded in `main.py`.
- The news feeds are fixed to The Guardian and TechCrunch.
- The calendar collector includes the first three events beginning today or later.
- The pipeline depends on external APIs and RSS feeds being reachable.
- The Gemini model name is configured directly in `main.py`.