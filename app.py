from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone
import smtplib
from email.mime.text import MIMEText
import dateutil.parser
import os

app = Flask(__name__)

# ==============================
# ENV VARIABLES
# ==============================
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TO_EMAIL = os.getenv("TO_EMAIL")  # comma separated
SECRET = os.getenv("SECRET_KEY", "mysecret123")

recipients = [e.strip() for e in TO_EMAIL.split(",")]

URL = "https://www.thehindu.com/latest-news/"

# ==============================
# GLOBAL RATE LIMIT (1 HOUR)
# ==============================
last_run = None


# ==============================
# SCRAPER FUNCTION
# ==============================
def get_last_hour_news():
    news = []

    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, timeout=60000)
        page.wait_for_load_state("networkidle")

        articles = page.locator("div.right-content").all()

        for article in articles:
            try:
                title_el = article.locator("h3.title a")
                title = title_el.inner_text().strip()
                link = title_el.get_attribute("href")

                time_el = article.locator("div.news-time")
                published = time_el.get_attribute("data-published")

                if not published:
                    continue

                published_time = dateutil.parser.parse(published).astimezone(timezone.utc)

                if one_hour_ago <= published_time <= now:
                    news.append((title, link))

            except Exception:
                continue

        browser.close()

    return news


# ==============================
# EMAIL FUNCTION
# ==============================
def send_email(news):
    if not news:
        return "No news found"

    content = ""

    for title, link in news:
        content += f"{title}\n{link}\n\n"

    msg = MIMEText(content)
    msg["Subject"] = "📰 News from Last 1 Hour"
    msg["From"] = EMAIL
    msg["To"] = "Undisclosed Recipients"

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL, PASSWORD)

        server.sendmail(
            EMAIL,
            recipients,
            msg.as_string()
        )

    return f"Sent {len(news)} articles"


# ==============================
# ROUTES
# ==============================
@app.route("/")
def home():
    return "🚀 News Automation Running"


@app.route("/run-news-job")
def run_news():
    global last_run

    # 🔐 security
    key = request.args.get("key")
    if key != SECRET:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    now = datetime.now()

    # ⏱ prevent multiple runs within 1 hour
    if last_run and (now - last_run).seconds < 3600:
        return jsonify({
            "status": "skipped",
            "message": "Already ran within last hour"
        })

    try:
        news = get_last_hour_news()
        result = send_email(news)

        last_run = now

        return jsonify({
            "status": "success",
            "articles": len(news),
            "message": result
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })


# ==============================
# RUN SERVER
# ==============================

port = int(os.environ.get("PORT", 10000))
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)