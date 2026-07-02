import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

EMAILS_FILE = "data/alert_emails.json"

def load_alert_emails():
    if os.path.exists(EMAILS_FILE):
        with open(EMAILS_FILE) as f:
            return json.load(f)
    return []

def send_lead_alert(event: dict):
    bios  = event.get("bios_fit") or {}
    score = bios.get("score", 0)

    if score < 75:
        return

    # Get all subscribed emails
    recipients = load_alert_emails()
    
    # Always include the system email as fallback
    system_email = os.getenv("ALERT_EMAIL")
    if system_email and system_email not in recipients:
        recipients.append(system_email)

    if not recipients:
        print("  [CRM] No recipients configured, skipping alert.")
        return

    company   = (event.get("company") or {}).get("name", "Unknown")
    to_c      = (event.get("to_location") or {}).get("country", "Unknown")
    action    = bios.get("recommended_action", "")
    rationale = bios.get("rationale", "")
    summary   = event.get("article_summary", event.get("summary", ""))
    url       = event.get("source_url", "")

    subject = f"[PROSICHT] New Lead: {company} — BIOS Score {score}/100"

    body = f"""
New high-priority industrial relocation opportunity detected!

Company:     {company}
Destination: {to_c}
BIOS Score:  {score}/100
Action:      {action}

Rationale:
{rationale}

Summary:
{summary}

Source: {url}

---
This alert was generated automatically by the PROSICHT Industrial Relocation Agent.
You are receiving this because you subscribed to BIOS score alerts.
    """

    try:
        msg = MIMEMultipart()
        msg["From"]    = os.getenv("ALERT_EMAIL")
        msg["To"]      = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(
                os.getenv("ALERT_EMAIL"),
                os.getenv("ALERT_EMAIL_PASSWORD")
            )
            server.sendmail(
                os.getenv("ALERT_EMAIL"),
                recipients,
                msg.as_string()
            )

        print(f"  [CRM] Alert sent to {len(recipients)} recipient(s) for {company} (score: {score})")

    except Exception as e:
        print(f"  [CRM] Email failed: {e}")