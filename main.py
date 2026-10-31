import os
import requests
import feedparser
from ics import Calendar
from google import genai
from datetime import datetime
import arrow

# ==========================================
# 1. CONFIGURATION & SECRETS
# ==========================================
# The script will now pull these securely from GitHub Actions
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
CALENDAR_ICS_URL = os.environ.get("CALENDAR_ICS_URL")

# Quick sanity check
if not all([GEMINI_API_KEY, NOTION_TOKEN, NOTION_DATABASE_ID, CALENDAR_ICS_URL]):
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
    You are my personal AI assistant writing a morning update to my Notion workspace.
    
    RAW DATA:
    - Weather Today: {weather}
    - Upcoming Agenda: {agenda}
    - News items: {news}
    
    FORMATTING RULES FOR NOTION:
    1. Do NOT use any Markdown formatting (no asterisks **, no pound signs ###, no brackets).
    2. Do NOT use HTML tags. 
    3. Use emojis as section headers (e.g., 🌤️ Weather, 📅 Agenda, 🌍 Top News).
    4. For the news section, provide EXACTLY 3 items:
       - The most important WORLD NEWS story.
       - The top TECH NEWS story.
    5. Format each news item as: "Title \n 1 sentence summary."
    6. Ensure every distinct point or paragraph is on a new line.
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
def create_notion_page(message):
    print("Sending to Notion...")
    NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        print(message)
        return

    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2026-03-11"
    }

    # STEP 1: Query the database to find all existing briefings
    query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    try:
        query_response = requests.post(query_url, headers=headers)
        query_response.raise_for_status()
        existing_pages = query_response.json().get("results", [])
        
        # STEP 2: Archive (delete) each existing page
        for page in existing_pages:
            archive_url = f"https://api.notion.com/v1/pages/{page['id']}"
            requests.patch(archive_url, headers=headers, json={"archived": True})
            
    except Exception as e:
        print(f"Failed to clear old database entries: {e}")

    # STEP 3: Create the new daily briefing page
    url = "https://api.notion.com/v1/pages"
    
    blocks = []
    for line in message.split('\n'):
        if line.strip():
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line.strip()}}]
                }
            })

    today_str = datetime.now().strftime("%Y-%m-%d")
    
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {
                "title": [
                    {"text": {"content": f"Morning Briefing: {today_str}"}}
                ]
            }
        },
        "children": blocks
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print("Briefing delivered to Notion successfully!")
    except Exception as e:
        print(f"Failed to send to Notion: {e}")
        if 'response' in locals():
            print(f"Notion API Response: {response.text}")