import os
import requests
import feedparser
from ics import Calendar
from google import genai
import arrow

# ==========================================
# 1. CONFIGURATION & SECRETS
# ==========================================
# The script will now pull these securely from GitHub Actions
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
CALENDAR_ICS_URL = os.environ.get("CALENDAR_ICS_URL")

# Quick sanity check
if not all([GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, CALENDAR_ICS_URL]):
    print("Warning: One or more environment variables are missing.")

# Default coordinates for weather
LATITUDE = "65.01" 
LONGITUDE = "25.47"

# ==========================================
# 2. DATA COLLECTION FUNCTIONS
# ==========================================
def get_weather():
    print("Fetching weather...")
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        max_temp = data["daily"]["temperature_2m_max"][0]
        min_temp = data["daily"]["temperature_2m_min"][0]
        return f"High: {max_temp}°C, Low: {min_temp}°C"
    except Exception as e:
        return f"Weather unavailable: {e}"

def get_calendar_events():
    print("Fetching calendar...")
    if not CALENDAR_ICS_URL:
        return "No calendar configured."
    try:
        response = requests.get(CALENDAR_ICS_URL)
        response.raise_for_status()
        c = Calendar(response.text)

        start_of_today = arrow.now().floor('day')
        upcoming = [e for e in c.events if e.begin and e.begin >= start_of_today]
        events = sorted(upcoming, key=lambda e: e.begin)

        if not events:
            return "No upcoming events."
        agenda = [f"- {e.name} (Start: {e.begin.format('YYYY-MM-DD HH:mm')})" for e in events[:3]]
        return "\n".join(agenda)
    except Exception as e:
        return f"Calendar unavailable: {e}"

def get_news():
    print("Fetching tech and world news...")
    world_url = "https://www.theguardian.com/world/rss"
    tech_url = "https://techcrunch.com/feed/"

    news_items = []

    try:
        world_feed = feedparser.parse(world_url)
        for entry in world_feed.entries[:5]:
            news_items.append(
                f"[CATEGORY: WORLD NEWS]\n"
                f"Title: {entry.title}\n"
                f"Link: {entry.link}\n"
                f"Summary: {entry.get('description', 'No description')}"
            )
    except Exception as e:
        news_items.append(f"World news unavailable: {e}")

    try:
        tech_feed = feedparser.parse(tech_url)
        for entry in tech_feed.entries[:5]:
            news_items.append(
                f"[CATEGORY: TECH NEWS]\n"
                f"Title: {entry.title}\n"
                f"Link: {entry.link}\n"
                f"Summary: {entry.get('description', 'No description')}"
            )
    except Exception as e:
        news_items.append(f"Tech news unavailable: {e}")

    return "\n\n".join(news_items)

# ==========================================
# 3. AI PROCESSING
# ==========================================
def generate_ai_briefing(weather, agenda, news):
    print("Generating AI briefing...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    You are my personal AI assistant sending a morning update to my phone on Telegram.
    
    RAW DATA:
    - Weather Today: {weather}
    - Upcoming Agenda: {agenda}
    - News items: {news}
    
    ORMATTING RULES FOR TELEGRAM:
    1. Do NOT use Markdown (no asterisks **, no markdown headers ###, no divider lines ---).
    2. Use Telegram HTML tags: <b>bold text</b> for emphasis and <a href="URL">Title</a> for links.
    3. Keep it visually clean and compact for a mobile screen using emoji section headers (e.g., 🌤️ <b>Weather</b>, 📅 <b>Agenda</b>, 🌍 <b>Top News</b>).
    4. For the news section, provide EXACTLY 3 items in this order:
       - Item 1: The most important story from [CATEGORY: WORLD NEWS].
       - Item 2: The second most important story from [CATEGORY: WORLD NEWS].
       - Item 3: The top story from [CATEGORY: TECH NEWS] (prefix the headline with a tech tag or emoji, e.g., 💻 [Tech]).
       For each item, format the title as a clickable link (<a href="URL">Title</a>), followed by a 1-sentence summary of why it matters.
    5. Keep the tone warm, clear, and direct.
    """
    
    try:
        # Uses the correct updated interactions API
        response = client.interactions.create(
            model='gemini-3.8-flash',
            input=prompt
        )
        return response.output_text
    except Exception as e:
        return f"AI Generation Failed: {e}"

# ==========================================
# 4. DELIVERY
# ==========================================
def send_telegram_message(message):
    print("Sending to Telegram...")
    if not TELEGRAM_BOT_TOKEN:
        print(message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Briefing delivered successfully!")
    except Exception as e:
        print(f"Failed to send to Telegram: {e}")

if __name__ == "__main__":
    raw_weather = get_weather()
    raw_agenda = get_calendar_events()
    raw_news = get_news()
    
    final_briefing = generate_ai_briefing(raw_weather, raw_agenda, raw_news)
    send_telegram_message(final_briefing)