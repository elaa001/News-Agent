import feedparser   
import requests    
from bs4 import BeautifulSoup 
import unicodedata  
import os  
import json  
import time
import hashlib
from datetime import datetime
from dotenv import load_dotenv   
from openai import OpenAI   
import csv  
#import schedule
import sys
from crm_alert import send_lead_alert
from database import save_event
#from database import create_table, save_event

sys.stdout.reconfigure(encoding='utf-8')


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """Sen, Avrupa’da endüstriyel denetim ve makine görüşü hizmetleri sağlayan BIOS şirketi için fırsatları bulan bir endüstriyel taşınma analizcisisin.

BIOS, fabrikalar taşındığında, büyüdüğünde veya yeni tesis açtığında iş kazanır — çünkü bu durumlarda yeni denetim sistemleri, kalite kontrol ekipmanları ve üretim kurulumu hizmetleri gerekir.

GÖREV: Yapılandırılmış olay verisini çıkar VE BIOS için fırsat puanı hesapla.

BIOS uygunluk puanlama kriterleri (her biri 0-20 puan, toplam 0-100):
- T (Teknik Karmaşıklık): Üretim süreci ne kadar karmaşık? Yüksek teknoloji = daha fazla puan. (yarı iletken=20, otomotiv=16, ilaç=16, gıda=8, içecek=4)
- R (Taşınma Kesinliği): Bu olay doğrulanmış mı yoksa sadece söylenti mi? (doğrulanmış=20, muhtemel=12, söylenti=6)
- G (Coğrafi Uyum): Hedef Avrupa’da mı? (Avrupa=20, Avrupa’ya yakın=10, diğer=4)
- S (Sektör Uyum): BIOS bu sektöre hizmet veriyor mu? (otomotiv/endüstriyel makineler=20, ilaç/yarı iletken=16, gıda/içecek=8, diğer=4)
- U (Zaman): Bu ne kadar acil? (hemen/şu anda=20, 1 yıl içinde=14, uzun vadeli=6)

Toplam puana göre:
- 80-100 → önerilen_aksiyon: "reach_out" (iletişime geç)
- 50-79  → önerilen_aksiyon: "monitor" (takip et)
- 0-49   → önerilen_aksiyon: "tender_watch" (ihale takibi yap)

KURALLAR:
- SADECE geçerli JSON döndür, markdown veya açıklama yazma.
- Eğer bir bilgi bulunamazsa null kullan.
- event_type şu değerlerden biri olmalı:relocation, closure, expansion, greenfield, brownfield, production_transfer, supply_chain, fdi_announcement
- article_summary: Makalenin İngilizce olarak 2-3 cümlelik bir özetini yazın. Neler olduğuna, hangi şirkete, nerede olduğuna ve neden önemli olduğuna odaklanın.

Aşağıdaki yapıyı aynen döndür:
{
    "event_type": "",
    "company": { "name": "", "parent_company": null },
    "from_location": { "city": null, "country": null, "region": null },
    "to_location": { "city": null, "country": null, "region": null },
    "sector": null,
    "investment_size": { "amount": null, "currency": null },
    "jobs": { "created": null, "lost": null },
    "summary": "",
    "article_summary": "",
    "bios_fit": {
        "score": 0,
        "T": 0,
        "R": 0,
        "G": 0,
        "S": 0,
        "U": 0,
        "recommended_action": "monitor",
        "rationale": ""
    }
}
"""

SIGNAL_KEYWORDS = [
    "factory", "plant", "facility", "manufacturing", "production",
    "relocation", "closure", "shutdown", "expansion", "greenfield",
    "brownfield", "investment", "capex", "fdi", "jobs", "workers",
    "assembly", "automotive", "semiconductor", "pharma", "steel"
]

EUROPEAN_KEYWORDS = [
    "germany", "france", "poland", "italy", "spain", "netherlands",
    "belgium", "sweden", "austria", "czech", "hungary", "romania",
    "slovakia", "denmark", "finland", "portugal", "switzerland",
    "norway", "uk", "united kingdom", "turkey", "serbia", "croatia",
    "bulgaria", "greece", "ireland", "europe", "european",
    "slovenia", "estonia", "latvia", "lithuania", "luxembourg",
    "malta", "cyprus", "iceland", "albania", "ukraine"
]

RSS_FEEDS = [
    "https://news.google.com/rss/search?q=factory+relocation+Europe&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=plant+closure+Europe&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=manufacturing+investment+Europe&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=factory+expansion+Germany+OR+France+OR+Poland+OR+Italy&hl=en&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=automotive+plant+closure+Europe&hl=en&gl=US&ceid=US:en",
]

def clean_text(text: str) -> str:   
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = " ".join(text.split())
    return text

def is_europe_relevant(title: str, summary: str) -> bool:
    combined = (title + " " + summary).lower()
    has_signal = any(kw in combined for kw in SIGNAL_KEYWORDS)
    has_europe = any(kw in combined for kw in EUROPEAN_KEYWORDS)
    return has_signal and has_europe

def mentions_europe(event: dict) -> bool:
    to_c      = ((event.get("to_location")   or {}).get("country") or "").lower()
    from_c    = ((event.get("from_location") or {}).get("country") or "").lower()
    to_city   = ((event.get("to_location")   or {}).get("city")    or "").lower()
    from_city = ((event.get("from_location") or {}).get("city")    or "").lower()
    summary   = (event.get("summary") or "").lower()
    combined  = f"{to_c} {from_c} {to_city} {from_city} {summary}"
    return any(kw in combined for kw in EUROPEAN_KEYWORDS)


def url_hash(url: str) -> str:  
    return hashlib.md5(url.encode()).hexdigest()

PAYWALL_PHRASES = [
    "digital access to quality ft journalism",
    "subscribe to read",
    "create a free account",
    "sign in to read",
]

def fetch_article_text(url: str, fallback: str) -> str:   
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = " ".join(p.get_text() for p in soup.find_all("p"))
        text = clean_text(text)
        if len(text) < 100 or any(p in text.lower() for p in PAYWALL_PHRASES):
            return fallback
        return text
    except Exception as e:
        print(f"  [!] Fetch error: {e}")
        return fallback

def extract_event(article_text: str, source_url: str, retries: int = 2) -> dict | None:   
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": article_text[:3000]}
                ]
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            event = json.loads(raw)
            event["source_url"] = source_url
            return event
        except json.JSONDecodeError:
            print(f"  [!] Invalid JSON from AI (attempt {attempt+1})")
        except Exception as e:
            print(f"  [!] API error: {e} (attempt {attempt+1})")
            time.sleep(2 ** attempt)
    return None

def generate_summary(article_text: str, target_lang: str = "English") -> str:
    try:
        lang_instruction = "in Turkish" if target_lang == "Turkish" else "in English"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": f"Write a 2-3 sentence summary of the following news article {lang_instruction}. Focus on: what happened, which company, where, and why it matters. Return only the summary, nothing else."},
                {"role": "user", "content": article_text[:3000]}
            ]
        )
        return response.choices[0].message.content.strip()
    except:
        return ""

# ─── MAIN LOOP ────────────────────────────────────────────────────────────────

def run_fetch(feeds=None):
    
    #create_table()  # creates table if it doesn't exist yet
    
    # Use passed feeds if provided, otherwise fall back to default
    active_feeds = feeds if feeds else RSS_FEEDS
    
    # ── Load seen URLs fresh every time ──────────────────────────────────────
    SEEN_URLS_FILE = "data/seen_urls.json"
    if os.path.exists(SEEN_URLS_FILE):
        with open(SEEN_URLS_FILE) as f:
            seen_urls = set(json.load(f))
        print(f"Loaded {len(seen_urls)} previously seen URLs")
    else:
        seen_urls = set()
        print("No previous seen URLs found, starting fresh")
    
    # Then replace RSS_FEEDS in your loop with active_feeds:
    events = []

    for feed_url in active_feeds:  
        print(f"\nFetching: {feed_url}")
        feed = feedparser.parse(feed_url)   
        print(f"  {len(feed.entries)} entries found")

        for entry in feed.entries[:15]:
            url = entry.get("link", "")  
            uid = url_hash(url)  
            if uid in seen_urls:
                continue
            seen_urls.add(uid)   

            title   = clean_text(entry.get("title", ""))  
            summary = clean_text(BeautifulSoup(           
                entry.get("summary", entry.get("description", "")),
                "html.parser"
            ).get_text())    

            if not is_europe_relevant(title, summary):   
                print(f"  [skip-geo] {title[:70]}")
                continue

            print(f"  [+] {title[:70]}")

            article_text = fetch_article_text(url, fallback=summary)   

            if len(article_text) < 80:
                print("  [skip] too short after fetch")
                continue

            event = extract_event(article_text, source_url=url)   

            if event:                                            
                if not mentions_europe(event):
                    to_c   = (event.get("to_location")   or {}).get("country") or ""
                    from_c = (event.get("from_location") or {}).get("country") or ""
                    print(f"  [skip-geo] Not European: {to_c} / {from_c}")
                    continue

                events.append(event)   
                
                # Save to PostgreSQL
                #save_event(event)

                # Send CRM alert if score is 80+
                send_lead_alert(event)

                bios  = event.get("bios_fit") or {}
                score = bios.get("score", 0)
                action = bios.get("recommended_action", "")
                company = (event.get("company") or {}).get("name", "?")
                print(f"  -> saved: [{score}/100] {action} | {company}")

            time.sleep(0.2)            


    # Save seen URLs so next run skips already-processed articles
    with open(SEEN_URLS_FILE, "w") as f:
        json.dump(list(seen_urls), f)
    print(f"Saved {len(seen_urls)} seen URLs to {SEEN_URLS_FILE}")


    # ─── SAVE JSON ────────────────────────────────────────────────────────────────
    output = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_events": len(events),
        "events": events
    }

    with open("data/industry_events.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # ─── SAVE CSV ─────────────────────────────────────────────────────────────────
    with open("industry_events.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "company", "event_type", "sector",
            "from_country", "to_country",
            "investment_usd", "jobs_created", "jobs_lost",
            "bios_score", "recommended_action", "rationale",
            "summary", "source_url"
        ])
        writer.writeheader()
        for e in events:     
            bios = e.get("bios_fit") or {}
            writer.writerow({
                "company":            (e.get("company") or {}).get("name"),
                "event_type":         e.get("event_type"),
                "sector":             e.get("sector"),
                "from_country":       (e.get("from_location") or {}).get("country"),
                "to_country":         (e.get("to_location") or {}).get("country"),
                "investment_usd":     (e.get("investment_size") or {}).get("amount"),
                "jobs_created":       (e.get("jobs") or {}).get("created"),
                "jobs_lost":          (e.get("jobs") or {}).get("lost"),
                "bios_score":         bios.get("score"),
                "recommended_action": bios.get("recommended_action"),
                "rationale":          bios.get("rationale"),
                "summary":            e.get("summary"),
                "source_url":         e.get("source_url"),
            })

    print(f"\nDone. {len(events)} events saved to industry_events.json and industry_events.csv")

    # ─── CONTENT-BASED DEDUPLICATION ─────────────────────────────────────────────
    # Same company + same event_type + same to_country = same story, keep highest score

    def dedup_key(event):         
        company = (event.get("company") or {}).get("name") or ""
        etype   = event.get("event_type") or ""
        amount  = (event.get("investment_size") or {}).get("amount") or 0
        # Round to nearest billion so "$3B" and "$3bn" match
        amount_b = round(amount / 1_000_000_000) if amount else 0
        # Normalize company name — "Lilly" and "Eli Lilly" should be the same
        company_clean = company.lower().strip()
        company_clean = company_clean.replace("eli ", "").replace("& ", "").strip()
        return (company_clean, etype, amount_b)

    seen_keys = {}   
    for e in events:   # Her olayı sırayla işle, dedup_key fonksiyonunu kullanarak benzersiz bir anahtar oluştur, eğer aynı anahtara sahip bir olay görmediysek veya bu olayın BIOS puanı daha yüksekse, bu olayı sakla
        key = dedup_key(e)
        score = (e.get("bios_fit") or {}).get("score") or 0
        # If we've seen this story before, keep whichever has the higher score
        if key not in seen_keys or score > (seen_keys[key].get("bios_fit") or {}).get("score", 0):
            seen_keys[key] = e

    events = list(seen_keys.values())
    print(f"After content dedup: {len(events)} unique events")

    # ─── TOP 10 BY BIOS-FIT SCORE ─────────────────────────────────────────────────
    def get_score(event):   # Olayın BIOS uygunluk puanını döndür, eğer yoksa 0 döndür, böylece en yüksek puanlı olayları sıralayabiliriz
        return (event.get("bios_fit") or {}).get("score") or 0

    top10 = sorted(events, key=get_score, reverse=True)[:10]

    top10_output = []
    for i, e in enumerate(top10):   # En yüksek puanlı 10 olayı sırayla işle, her biri için ilgili alanları çıkar ve BIOS uygunluk puanı ile önerilen aksiyonu da ekle, böylece bu bilgileri JSON dosyasına kaydedebilir ve konsola yazdırabiliriz
        bios = e.get("bios_fit") or {}
        top10_output.append({
            "rank":               i + 1,
            "title":              e.get("summary"),
            "company":            (e.get("company") or {}).get("name"),
            "event_type":         e.get("event_type"),
            "sector":             e.get("sector"),
            "from_country":       (e.get("from_location") or {}).get("country"),
            "to_country":         (e.get("to_location") or {}).get("country"),
            "investment_usd":     (e.get("investment_size") or {}).get("amount"),
            "bios_score":         bios.get("score"),
            "recommended_action": bios.get("recommended_action"),
            "rationale":          bios.get("rationale"),
            "article_summary":    e.get("article_summary", ""),
            "source_url":         e.get("source_url"),
        })

    with open("data/top10_events.json", "w", encoding="utf-8") as f:
        json.dump({
            "generated_at":  datetime.utcnow().isoformat(),
            "total_scanned": len(events),
            "top_10":        top10_output
        }, f, indent=2, ensure_ascii=False)

    print("\nTOP 10 BY BIOS-FIT SCORE:")
    print("=" * 60)
    for item in top10_output:
        score  = item["bios_score"] or 0
        action = item["recommended_action"] or ""
        company = item["company"] or "?"
        title  = (item["title"] or "")[:55]
        print(f"  #{item['rank']}  [{score:>3}/100]  {action:<14}  {company} — {title}")

    print(f"\nSaved to top10_events.json")
    pass

if __name__ == "__main__":
    run_fetch()
    
    
#def run_daily():
#     print(f"\nRunning scheduled fetch at {datetime.utcnow()}")
#     # wrap your entire main logic in a function and call it here

# schedule.every().day.at("08:00").do(run_daily)

# print("Scheduler started — running every day at 08:00")
# while True:
#     schedule.run_pending()
#     time.sleep(60)