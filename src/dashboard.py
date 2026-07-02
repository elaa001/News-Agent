import streamlit as st
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import sys


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_FEEDS = [
    "https://news.google.com/rss/search?q=factory+relocation+Europe&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=plant+closure+Europe&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=manufacturing+investment+Europe&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=factory+expansion+Germany+OR+France+OR+Poland+OR+Italy&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=automotive+plant+closure+Europe&hl=en&gl=US&ceid=US:en",
]

FEEDS_FILE = "data/rss_feeds.json"

def load_feeds():
    if os.path.exists(FEEDS_FILE):
        with open(FEEDS_FILE, encoding="utf-8") as f:
            feeds = json.load(f)
        if feeds:  # only return if not empty
            return feeds
    # If file doesn't exist or is empty, write defaults and return them
    save_feeds(DEFAULT_FEEDS.copy())
    return DEFAULT_FEEDS.copy()

def save_feeds(feeds):
    if not feeds:  # never save an empty list
        st.warning("Cannot remove all feeds — at least one feed is required.")
        return
    with open(FEEDS_FILE, "w", encoding="utf-8") as f:
        json.dump(feeds, f, indent=2, ensure_ascii=False)

def translate_text(text: str, target_lang: str) -> str:
    if not text or target_lang == "English":
        return text
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": f"Translate the following text to {target_lang}. Return only the translation, nothing else."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except:
        return text

def translate_event(event: dict, target_lang: str) -> dict:
    if target_lang == "English":
        return event
    e = event.copy()
    e["title"]     = translate_text(event.get("title", ""), target_lang)
    e["rationale"] = translate_text(event.get("rationale", ""), target_lang)
    e["sector"]    = translate_text(event.get("sector", ""), target_lang)
    e["event_type"] = translate_text(event.get("event_type", ""), target_lang)
    return e

@st.cache_data
def load_data():
    if os.path.exists("data/top10_events.json"):
        with open("data/top10_events.json", encoding="utf-8") as f:
            return json.load(f)
    return None

st.set_page_config(
    page_title="PROSICHT — Industrial Relocation Agent",
    page_icon="🏭",
    layout="wide"
)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")

    language = st.radio("Output language", ["English", "Turkish"], index=0)

    st.divider()

    # ── RSS Feed Manager ───────────────────────────────────────────────────────
    st.subheader("RSS Feeds")

    st.session_state.feeds = DEFAULT_FEEDS.copy()
    save_feeds(DEFAULT_FEEDS.copy())

    # List existing feeds with delete buttons
    for i, feed in enumerate(st.session_state.feeds):
        col_feed, col_del = st.columns([5, 1])
        col_feed.caption(feed[:55] + "..." if len(feed) > 55 else feed)
        if col_del.button("✕", key=f"del_{i}"):
            st.session_state.feeds.pop(i)
            save_feeds(st.session_state.feeds)
            st.rerun()
            
    # Add new feed
    new_feed = st.text_input("Add RSS link", placeholder="https://...")
    if st.button("Add feed", use_container_width=True):
        if new_feed and new_feed.startswith("http"):
            # Reload from disk first to get the latest state
            current_feeds = load_feeds()
            st.session_state.feeds = current_feeds
            
            if new_feed not in st.session_state.feeds:
                st.session_state.feeds.append(new_feed)
                save_feeds(st.session_state.feeds)
                st.success("Feed added!")
                st.rerun()
            else:
                st.warning("Feed already exists.")
        else:
            st.error("Please enter a valid URL.")

    st.divider()

    st.subheader("Email Alerts")
    st.caption("Receive an email when a BIOS score exceeds 75.")

    # Load saved emails
    EMAILS_FILE = "data/alert_emails.json"

    def load_emails():
        if os.path.exists(EMAILS_FILE):
            with open(EMAILS_FILE) as f:
                return json.load(f)
        return []

    def save_emails(emails):
        with open(EMAILS_FILE, "w") as f:
            json.dump(emails, f, indent=2)

    if "alert_emails" not in st.session_state:
        st.session_state.alert_emails = load_emails()

    # Show subscribed emails with delete button
    for i, email in enumerate(st.session_state.alert_emails):
        col_e, col_d = st.columns([5, 1])
        col_e.caption(email)
        if col_d.button("✕", key=f"del_email_{i}"):
            st.session_state.alert_emails.pop(i)
            save_emails(st.session_state.alert_emails)
            st.rerun()

    # Add new email
    new_email = st.text_input("Add email", placeholder="name@email.com", key="new_email_input")
    if st.button("Subscribe", use_container_width=True):
        if new_email and "@" in new_email:
            if new_email not in st.session_state.alert_emails:
                st.session_state.alert_emails.append(new_email)
                save_emails(st.session_state.alert_emails)
                st.success(f"Subscribed: {new_email}")
                st.rerun()
            else:
                st.warning("Email already subscribed.")
        else:
            st.error("Please enter a valid email address.")

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from news_fetch import run_fetch

    if st.button("Run fetch now", use_container_width=True):
        with st.spinner("Fetching and scoring articles... this may take 1-2 minutes, please wait."):
            run_fetch()
            st.cache_data.clear()
        st.success("Done! Results updated.")
        st.rerun()
        
    if st.button("Clear cache & refetch all", use_container_width=True):
        if os.path.exists("data/seen_urls.json"):
            os.remove("data/seen_urls.json")
            st.success("Cache cleared!")
        with st.spinner("Fetching and scoring articles... this may take 1-2 minutes, please wait."):
            run_fetch(feeds=st.session_state.feeds)
            st.cache_data.clear()
        st.success("Done! Results updated.")
        st.rerun()   
        
    if st.button("Reset to default feeds", use_container_width=True):
        st.session_state.feeds = DEFAULT_FEEDS.copy()
        save_feeds(DEFAULT_FEEDS.copy())
        st.success("Feeds reset to defaults!")
        st.rerun()

# ─── Main content ─────────────────────────────────────────────────────────────
st.title("PROSICHT — Industrial Relocation Agent")

data = load_data()

if not data:
    st.error("No data found. Please run news_fetch.py first.")
    st.stop()

st.caption(f"Last run: {data.get('generated_at', 'unknown')}  ·  Total scanned: {data.get('total_scanned', 0)} events")

events = data.get("top_10", [])

# ─── Metrics ──────────────────────────────────────────────────────────────────
reach_out    = sum(1 for e in events if e.get("recommended_action") == "reach_out")
monitor      = sum(1 for e in events if e.get("recommended_action") == "monitor")
tender_watch = sum(1 for e in events if e.get("recommended_action") == "tender_watch")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total in top 10", len(events))
col2.metric("Reach out" if language == "English" else "İletişime Geç", reach_out)
col3.metric("Monitor" if language == "English" else "İzle", monitor)
col4.metric("Tender watch" if language == "English" else "İhale Takip", tender_watch)

st.divider()

heading = "Top 10 Opportunities" if language == "English" else "En İyi 10 Fırsat"
st.subheader(heading)

ACTION_BADGE = {
    "reach_out":    ("🟢", "reach_out"),
    "monitor":      ("🟡", "monitor"),
    "tender_watch": ("⚪", "tender_watch"),
}

COUNTRY_TR = {
    "Germany": "Almanya", "France": "Fransa", "Poland": "Polonya",
    "Italy": "İtalya", "Spain": "İspanya", "Netherlands": "Hollanda",
    "Belgium": "Belçika", "Sweden": "İsveç", "Austria": "Avusturya",
    "Czech Republic": "Çek Cumhuriyeti", "Hungary": "Macaristan",
    "Romania": "Romanya", "Slovakia": "Slovakya", "Denmark": "Danimarka",
    "Finland": "Finlandiya", "Portugal": "Portekiz", "Switzerland": "İsviçre",
    "Norway": "Norveç", "United Kingdom": "Birleşik Krallık", "UK": "Birleşik Krallık",
    "Turkey": "Türkiye", "Serbia": "Sırbistan", "Croatia": "Hırvatistan",
    "Bulgaria": "Bulgaristan", "Greece": "Yunanistan", "Ireland": "İrlanda",
    "Slovenia": "Slovenya", "Estonia": "Estonya", "Latvia": "Letonya",
    "Lithuania": "Litvanya", "Luxembourg": "Lüksemburg", "Ukraine": "Ukrayna",
    "United States": "Amerika Birleşik Devletleri", "USA": "ABD",
    "China": "Çin", "Japan": "Japonya", "South Korea": "Güney Kore",
    "India": "Hindistan", "Europe": "Avrupa",
}

def translate_country(country: str, language: str) -> str:
    if not country or language == "English":
        return country or "—"
    return COUNTRY_TR.get(country, country)

LABELS = {
    "English": {
        "company": "Company", "sector": "Sector", "event_type": "Event type",
        "from": "From", "to": "To", "investment": "Investment",
        "rationale": "Rationale", "read": "Read article", "score": "BIOS Score","summary": "Summary" 
    },
    "Turkish": {
        "company": "Şirket", "sector": "Sektör", "event_type": "Olay Tipi",
        "from": "Çıkış", "to": "Varış", "investment": "Yatırım",
        "rationale": "Gerekçe", "read": "Habere git", "score": "BIOS Skoru","summary": "Özet"
    }
}

lbl = LABELS[language]

# ─── Event cards ──────────────────────────────────────────────────────────────
for event in events:
    e = translate_event(event, language) if language == "Turkish" else event

    action  = event.get("recommended_action", "")
    score   = event.get("bios_score", 0)
    icon, _ = ACTION_BADGE.get(action, ("⚪", action))
    inv     = f"${event['investment_usd']:,}" if event.get("investment_usd") else "—"

    with st.container(border=True):
        # Title row
        st.markdown(f"### {e.get('title', '')}")

        # Score + action badge inline
        st.markdown(f"{icon} **{lbl['score']}:** {score}/100 &nbsp;&nbsp; **Action:** `{action}`")

        st.divider()

        # Details grid
        col_a, col_b, col_c = st.columns(3)
        col_a.markdown(f"**{lbl['company']}:** {event.get('company') or '—'}")
        col_b.markdown(f"**{lbl['sector']}:** {e.get('sector') or '—'}")
        col_c.markdown(f"**{lbl['event_type']}:** {e.get('event_type') or '—'}")

        col_d, col_e, col_f = st.columns(3)
        col_d.markdown(f"**{lbl['from']}:** {translate_country(event.get('from_country'), language)}")
        col_e.markdown(f"**{lbl['to']}:** {translate_country(event.get('to_country'), language)}")
        col_f.markdown(f"**{lbl['investment']}:** {inv}")

        st.markdown(f"**{lbl['rationale']}:** {e.get('rationale') or '—'}")
        
        summary_raw  = event.get("article_summary") or event.get("title", "—")
        summary_text = translate_text(summary_raw, language) if language == "Turkish" else summary_raw
        st.markdown(f"**{lbl['summary']}:** {summary_text}")
        
        st.markdown(f"[{lbl['read']}]({event.get('source_url', '#')})")