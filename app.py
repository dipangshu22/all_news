from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone
import dateutil.parser  # pip install python-dateutil
import smtplib
from email.mime.text import MIMEText


URL = "https://www.thehindu.com/latest-news/"

def send_email(news):
    if not news:
        print("No news in last 1 hour")
        return
    
    recipients = [
        "newtechdevng@gmail.com",
        "ronku@gmail.com",
        "ddbdev407@gmail.com"
    ]

    content = ""

    for title, link in news:
        content += f"{title}\n{link}\n\n"

    msg = MIMEText(content)
    msg["Subject"] = "📰 News from Last 1 Hour"
    msg["From"] = "dipangshu22@gmail.com"
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login("dipangshu22@gmail.com", "jelk dlfq guut cgjs")
        server.send_message(msg)

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

                # Convert to UTC
                published_time = dateutil.parser.parse(published).astimezone(timezone.utc)

                # ✅ Keep only last 1 hour news
                if one_hour_ago <= published_time <= now:
                    news.append((title, link))

            except Exception:
                continue

        browser.close()

    return news

def main():
    news = get_last_hour_news()
    send_email(news)


if __name__ == "__main__":
    main()
    print("done!")