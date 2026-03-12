#!/usr/bin/env python3
"""
Quick test script — run this BEFORE starting the main notifier.
Tests each component independently so you can verify everything works.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def check_env():
    print("\n── 1. Checking environment variables ──")
    required = ["GROQ_API_KEY", "EMAIL_SENDER", "EMAIL_PASSWORD", "TAVILY_API_KEY"]
    
    ok = True
    for key in required:
        val = os.getenv(key)
        if val and "your_" not in val:
            print(f"  ✅ {key} is set")
        else:
            print(f"  ❌ {key} is MISSING or still placeholder")
            ok = False
    
    return ok


def test_groq():
    print("\n── 2. Testing Groq API ──")
    import requests
    key = os.getenv("GROQ_API_KEY")
    if not key or "your_" in key:
        print("  ❌ GROQ_API_KEY not set")
        return False
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": "Say: Groq is working!"}],
            "max_tokens": 20
        }
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        print(f"  ✅ Groq responded: {text.strip()[:60]}")
        return True
    except Exception as e:
        print(f"  ❌ Groq failed: {e}")
        return False


def test_tavily():
    print("\n── 3. Testing Tavily job search ──")
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        print("  ❌ TAVILY_API_KEY not set")
        return False
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=key)
        response = client.search(
            query="Software Engineer fresher jobs India 2025",
            search_depth="basic",
            max_results=3
        )
        results = response.get("results", [])
        print(f"  ✅ Tavily returned {len(results)} results")
        if results:
            print(f"     Sample: {results[0].get('title','')[:60]}")
        return True
    except Exception as e:
        print(f"  ❌ Tavily failed: {e}")
        return False


def test_email():
    print("\n── 4. Testing email sending ──")
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    sender   = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    to       = "karthikadiga79@gmail.com"
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "✅ Job Notifier – Test Email"
    msg["From"]    = sender
    msg["To"]      = to
    html = "<h2 style='color:#7c3aed'>Setup working!</h2><p>Your daily job notifier is configured correctly. You will receive job digests at 8:30 PM IST every day.</p>"
    msg.attach(MIMEText(html, "html"))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, to, msg.as_string())
        print(f"  ✅ Test email sent to {to}. Check your inbox!")
        return True
    except Exception as e:
        print(f"  ❌ Email failed: {e}")
        print("     → Make sure you're using a Gmail App Password, not your regular password")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("  Job Notifier – Setup Verification Test")
    print("=" * 50)
    
    env_ok     = check_env()
    if not env_ok:
        print("\n❌ Fix .env file first, then re-run this test.")
        sys.exit(1)
    
    groq_ok    = test_groq()
    tavily_ok  = test_tavily()
    email_ok   = test_email()
    
    print("\n" + "=" * 50)
    if all([env_ok, groq_ok, tavily_ok, email_ok]):
        print("✅ ALL TESTS PASSED — Run: python job_notifier.py")
    else:
        print("⚠️  Some tests failed. Fix issues above, then retry.")
    print("=" * 50)