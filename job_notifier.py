#!/usr/bin/env python3
"""
Job Notification Automation for Karthik S Adiga
Searches for fresher Software/Full Stack/Backend/C++ developer jobs in India
Uses Tavily AI Search + Gemini AI analysis → daily email at 8:30 PM IST
"""

import os
import time
import datetime
import requests
import smtplib
import schedule
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ─────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_SENDER   = os.getenv("EMAIL_SENDER")    # Gmail address used to SEND
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # App password (not regular password)
EMAIL_TO       = "karthikadiga79@gmail.com"
TAVILY_API_KEY = os.getenv("fqfu gdqm ttnh fajo")  # free: 1000 searches/month

RESUME_SUMMARY = """
Name: Karthik S Adiga
Location: Bengaluru, India
Experience: Fresher (0 years) – 2025/2026 Graduate
GitHub: https://github.com/Karthik1056
LinkedIn: https://www.linkedin.com/in/karthik-s-adiga-668566228

Skills (inferred from profile):
- Programming: Python, C++, JavaScript
- Web: Full Stack development
- Tools: Git, GitHub
- Platforms: LeetCode (active competitive programmer)
- Interests: Software Engineering, Backend Development, Full Stack

Target Roles: Software Engineer (Fresher), Full Stack Developer,
              Backend Developer, C++ Developer
"""

# Tavily searches all these sources automatically — no need to specify each one
TARGET_QUERIES = [
    "Software Engineer fresher jobs India 2025 apply LinkedIn Naukri",
    "Full Stack Developer entry level jobs India fresher Wellfound Instahyre",
    "Backend Developer fresher jobs Bangalore India 2025",
    "C++ Developer fresher jobs India 0 years experience",
    "Junior Software Developer fresher jobs India remote hybrid 2025",
]

# ─── STEP 1: SEARCH FOR JOBS USING TAVILY ───────────────────────────────────
def search_jobs_tavily(query: str) -> list[dict]:
    """Use Tavily AI Search — built for agents, returns clean structured results."""
    if not TAVILY_API_KEY:
        print("[WARN] TAVILY_API_KEY not set")
        return []

    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        # search_depth="advanced" gives richer snippets; max_results=7 keeps usage low
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=7,
            include_domains=[
                "linkedin.com", "naukri.com", "wellfound.com",
                "instahyre.com", "cutshort.io", "hirist.tech",
                "foundit.in", "indeed.com", "internshala.com"
            ],
            days=7    # only results from the last 7 days
        )

        results = []
        for item in response.get("results", []):
            results.append({
                "title":   item.get("title", ""),
                "link":    item.get("url", ""),
                "snippet": item.get("content", ""),
                "source":  item.get("url", "").split("/")[2] if item.get("url") else ""
            })
        return results

    except Exception as e:
        print(f"[ERROR] Tavily search failed for '{query}': {e}")
        return []


def fetch_all_jobs() -> list[dict]:
    """Run all queries via Tavily, deduplicate results by URL."""
    all_jobs  = []
    seen_links = set()

    for query in TARGET_QUERIES:
        print(f"  🔍 Searching: {query[:60]}...")
        results = search_jobs_tavily(query)

        for job in results:
            link = job.get("link", "")
            if link and link not in seen_links:
                seen_links.add(link)
                job["role_query"] = query
                all_jobs.append(job)

        time.sleep(1)   # gentle on API — Tavily is fast but be polite

    print(f"  ✅ Total unique jobs found: {len(all_jobs)}")
    return all_jobs


# ─── STEP 2: GEMINI AI – SCORE & ANALYSE ────────────────────────────────────
def gemini_analyze(jobs: list[dict]) -> str:
    """
    Send all jobs + resume to Gemini.
    Returns a structured HTML email body.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in .env")

    jobs_text = ""
    for i, job in enumerate(jobs[:20], 1):   # cap at 20 to save tokens
        jobs_text += f"""
Job #{i}
Title:   {job.get('title','')}
Source:  {job.get('source','')}
Link:    {job.get('link','')}
Details: {job.get('snippet','')}
---"""

    prompt = f"""
You are an expert career coach and job analyst.

CANDIDATE PROFILE:
{RESUME_SUMMARY}

TODAY'S JOB LISTINGS:
{jobs_text}

TASK:
1. Filter ONLY jobs relevant to: Software Engineer / Full Stack / Backend / C++ Developer (fresher, 0-2 yrs exp, India/Remote).
2. For each relevant job, give:
   - Job Title & Company (extract from title/snippet)
   - Platform (LinkedIn / Naukri / Wellfound etc.)
   - Location & Work Mode (Remote/Hybrid/Onsite) if mentioned
   - Fit Score out of 10 with one-line reasoning
   - Resume Keywords to ADD for this role (max 5 keywords)
   - Apply Link

3. Pick Top 5 Best Bets with the highest fit scores.

4. At the end, add a "Resume Quick Wins" section with 3-5 universal keyword improvements Karthik should add to his resume TODAY to improve overall match rate for these roles.

FORMAT YOUR RESPONSE AS CLEAN HTML (no markdown, no code blocks).
Use this structure:
- A summary banner at top (total jobs found, strong matches, date)
- A results table with columns: #, Title, Company, Platform, Location, Mode, Fit Score, Apply
- Top 5 Best Bets section with cards
- Resume Quick Wins section
- Keep it professional, mobile-friendly, dark-accent color scheme

Important: Karthik is a FRESHER (0 years experience). Only include roles suitable for freshers or 0-2 year experience.
Today's date: {datetime.date.today().strftime('%B %d, %Y')}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 4096
        }
    }

    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError(f"Gemini returned no candidates: {data}")
    
    text = candidates[0]["content"]["parts"][0]["text"]
    
    # Strip markdown code fences if Gemini wraps in ```html
    text = re.sub(r"^```html\s*", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    
    return text


# ─── STEP 3: SEND EMAIL ──────────────────────────────────────────────────────
def send_email(html_body: str, job_count: int):
    today = datetime.date.today().strftime("%b %d, %Y")
    subject = f"🚀 Daily Job Digest – {job_count} Fresher Roles Found | {today}"

    full_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f0f; color: #e0e0e0; margin:0; padding:0; }}
  .wrapper {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 12px; padding: 28px; text-align: center; margin-bottom: 24px; border: 1px solid #2a2a4a; }}
  .header h1 {{ color: #7c3aed; margin: 0 0 8px 0; font-size: 22px; }}
  .header p {{ color: #9ca3af; margin: 0; font-size: 14px; }}
  .footer {{ text-align: center; color: #6b7280; font-size: 12px; padding: 20px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  th {{ background: #1e1b4b; color: #a78bfa; padding: 10px; text-align: left; font-size: 13px; }}
  td {{ padding: 10px; border-bottom: 1px solid #2a2a3a; font-size: 13px; }}
  tr:hover {{ background: #1a1a2e; }}
  a {{ color: #7c3aed; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; }}
  .score-high {{ background: #065f46; color: #6ee7b7; }}
  .score-mid  {{ background: #78350f; color: #fcd34d; }}
  h2 {{ color: #7c3aed; border-bottom: 1px solid #2a2a4a; padding-bottom: 8px; }}
  .card {{ background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 10px; padding: 16px; margin: 12px 0; }}
  .card h3 {{ margin: 0 0 8px 0; color: #a78bfa; font-size: 15px; }}
  .card p {{ margin: 4px 0; font-size: 13px; color: #9ca3af; }}
  .keyword {{ background: #312e81; color: #c4b5fd; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin: 2px; display: inline-block; }}
  .btn {{ display: inline-block; background: #7c3aed; color: #fff !important; padding: 6px 14px; border-radius: 6px; font-size: 12px; margin-top: 8px; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>🚀 Daily Job Digest for Karthik S Adiga</h1>
    <p>Fresher Software / Full Stack / Backend / C++ Roles · India &amp; Remote · {today}</p>
  </div>
  {html_body}
  <div class="footer">
    <p>Automated by Job Notifier Bot · Running daily at 8:30 PM IST<br>
    Resume: <a href="https://drive.google.com/file/d/1IPpEp5jMExktN5N7Qx9gUgbzIlD908Y-/view">View Resume</a> ·
    GitHub: <a href="https://github.com/Karthik1056">github.com/Karthik1056</a></p>
  </div>
</div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(full_html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_TO, msg.as_string())
        print(f"[OK] Email sent to {EMAIL_TO}")
    except Exception as e:
        print(f"[ERROR] Email failed: {e}")
        raise


# ─── STEP 4: MAIN DAILY JOB ──────────────────────────────────────────────────
def run_daily_job():
    print(f"\n{'='*55}")
    print(f" Job Notifier running at {datetime.datetime.now()}")
    print(f"{'='*55}")

    print("\n[1/3] Fetching jobs...")
    jobs = fetch_all_jobs()

    if not jobs:
        print("[WARN] No jobs found today. Sending empty digest.")
        send_email("<p style='color:#9ca3af;text-align:center'>No new jobs found today. Will check again tomorrow!</p>", 0)
        return

    print(f"\n[2/3] Analysing {len(jobs)} jobs with Gemini AI...")
    html_body = gemini_analyze(jobs)

    print("\n[3/3] Sending email...")
    send_email(html_body, len(jobs))
    print("\n[DONE] Daily job digest sent!")


# ─── SCHEDULER ───────────────────────────────────────────────────────────────
def main():
    print("Job Notifier started. Scheduled for 20:30 IST daily.")
    print("Press Ctrl+C to stop.\n")
    
    # Schedule at 20:30 IST. If your server is UTC, use 15:00 (UTC+5:30 = IST)
    # Adjust the time below based on your server's timezone
    schedule_time = os.getenv("SCHEDULE_TIME", "20:30")  # default 8:30 PM IST
    schedule.every().day.at(schedule_time).do(run_daily_job)
    
    print(f"Next run scheduled at {schedule_time} (server local time)")
    print("Tip: Set SCHEDULE_TIME=15:00 in .env if your server is in UTC\n")
    
    # Uncomment the line below to run ONCE immediately for testing:
    # run_daily_job()
    
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
