#!/usr/bin/env python3
"""
Daily Solar/Renewable Energy News Report Generator for India
Fetches news from Google News RSS and other sources, categorizes them,
and generates a professional HTML report.
"""

import feedparser
import re
import html
import os
import time
import json
from datetime import datetime, timezone, timedelta

# ─── India Standard Time ────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))

# ─── RSS Feed Sources ────────────────────────────────────────────────────────
RSS_FEEDS = [
    # Google News – broad solar/renewable India
    "https://news.google.com/rss/search?q=solar+energy+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=renewable+energy+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=wind+energy+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=green+energy+india&hl=en-IN&gl=IN&ceid=IN:en",
    # IPO / stock angle
    "https://news.google.com/rss/search?q=solar+IPO+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=renewable+energy+stock+NSE+BSE+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=adani+green+tata+power+suzlon+inox+wind+stock&hl=en-IN&gl=IN&ceid=IN:en",
    # Sector-specific
    "https://news.google.com/rss/search?q=solar+power+plant+india+MW+GW&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=MNRE+solar+policy+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=green+hydrogen+india&hl=en-IN&gl=IN&ceid=IN:en",
    # Specialised portals (RSS)
    "https://mercomindia.com/feed/",
    "https://www.pv-magazine-india.com/feed/",
]

# ─── Keyword Sets ────────────────────────────────────────────────────────────
STOCK_KEYWORDS = [
    'ipo', 'stock', 'share', 'nse', 'bse', 'sensex', 'nifty', 'listing',
    'market cap', 'sebi', 'equity', 'invest', 'fund', 'mutual fund',
    'dividend', 'earnings', 'quarter', 'revenue', 'profit', 'loss',
    'fundraise', 'bond', 'debt', 'valuation', 'investors',
    'adani green', 'tata power', 'suzlon', 'inox wind', 'jsw energy',
    'ntpc', 'power grid', 'cesc', 'sterling wilson', 'waaree',
    'premier energies', 'orient green', 'renew power', 'azure power',
    'hero future energies', 'greenko', 'torrent power',
    'shares', 'analyst', 'target price', 'buy rating', 'hold rating',
    'fpo', 'preferential allotment', 'qip',
]

INDUSTRY_KEYWORDS = [
    'mw', 'gw', 'megawatt', 'gigawatt', 'solar park', 'wind farm',
    'tender', 'bid', 'auction', 'capacity', 'plant', 'project',
    'ministry', 'mnre', 'policy', 'tariff', 'grid', 'rooftop',
    'solar panel', 'module', 'cell', 'installation', 'deployment',
    'pm kusum', 'solar mission', 'net metering', 'discom',
    'power purchase', 'ppa', 'power plant', 'green hydrogen',
    'battery storage', 'bess', 'energy storage', 'offshore wind',
    'floating solar', 'hybrid', 'evacuation', 'transmission',
    'seci', 'rewa', 'ntpc renewable', 'ireda', 'irena',
]

RELEVANCE_KEYWORDS = [
    'solar', 'renewable', 'wind energy', 'clean energy', 'green energy',
    'photovoltaic', 'pv ', 'energy storage', 'solar power', 'wind power',
    'rooftop solar', 'solar farm', 'solar park', 'offshore wind',
]


# ─── Helpers ────────────────────────────────────────────────────────────────
def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    return text.strip()

def truncate(text, limit=280):
    text = text.strip()
    return text[:limit].rsplit(' ', 1)[0] + '…' if len(text) > limit else text

def parse_date(entry):
    """Return a formatted date string from feed entry."""
    try:
        t = entry.get('published_parsed') or entry.get('updated_parsed')
        if t:
            dt = datetime(*t[:6], tzinfo=timezone.utc).astimezone(IST)
            return dt.strftime('%d %b %Y, %I:%M %p IST')
    except Exception:
        pass
    return ''

def source_name(feed_title, entry):
    """Best-effort source label."""
    # Google News wraps source in title like: 'Headline - Source Name'
    title = entry.get('title', '')
    if ' - ' in title:
        return title.rsplit(' - ', 1)[-1].strip()
    return feed_title or 'Unknown'

def clean_title(raw_title):
    """Remove trailing '- Source' appended by Google News."""
    if ' - ' in raw_title:
        return raw_title.rsplit(' - ', 1)[0].strip()
    return raw_title.strip()


# ─── Fetch ───────────────────────────────────────────────────────────────────
def fetch_all_articles():
    articles = []
    seen = set()

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            feed_title = feed.feed.get('title', '')
            for entry in feed.entries[:12]:
                raw_title = entry.get('title', '')
                title = clean_title(html.unescape(raw_title))
                if not title or title.lower() in seen:
                    continue
                seen.add(title.lower())

                summary_raw = entry.get('summary', entry.get('description', ''))
                summary = truncate(clean_html(summary_raw))

                articles.append({
                    'title': title,
                    'link': entry.get('link', '#'),
                    'summary': summary,
                    'source': source_name(feed_title, entry),
                    'date': parse_date(entry),
                })
        except Exception as e:
            print(f"[WARN] Could not fetch {url}: {e}")
        time.sleep(0.4)

    return articles


# ─── Categorise ──────────────────────────────────────────────────────────────
def categorise(articles):
    stock_news, industry_news = [], []

    for art in articles:
        blob = (art['title'] + ' ' + art['summary']).lower()

        # Must be relevant to solar/renewable
        if not any(kw in blob for kw in RELEVANCE_KEYWORDS):
            continue

        stock_score = sum(1 for kw in STOCK_KEYWORDS if kw in blob)
        industry_score = sum(1 for kw in INDUSTRY_KEYWORDS if kw in blob)

        if stock_score >= industry_score and stock_score > 0:
            stock_news.append(art)
        elif industry_score > 0:
            industry_news.append(art)
        else:
            # Falls into industry by default if relevant
            industry_news.append(art)

    return stock_news[:20], industry_news[:25]


# ─── HTML Report ─────────────────────────────────────────────────────────────
CARD_TEMPLATE = """
        <div class="card">
          <div class="card-meta">
            <span class="source">{source}</span>
            <span class="date">{date}</span>
          </div>
          <a class="headline" href="{link}" target="_blank" rel="noopener noreferrer">{title}</a>
          <p class="summary">{summary}</p>
          <a class="read-more" href="{link}" target="_blank" rel="noopener noreferrer">Read Full Article ↗</a>
        </div>"""

def build_cards(articles):
    if not articles:
        return '<p class="no-news">No news found for this category today.</p>'
    return '\n'.join(
        CARD_TEMPLATE.format(
            source=html.escape(art['source']),
            date=html.escape(art['date']),
            link=art['link'],
            title=html.escape(art['title']),
            summary=html.escape(art['summary']),
        )
        for art in articles
    )

def generate_html(stock_news, industry_news):
    now_ist = datetime.now(IST)
    date_display = now_ist.strftime('%A, %d %B %Y')
    time_display = now_ist.strftime('%I:%M %p IST')
    date_slug    = now_ist.strftime('%Y-%m-%d')

    stock_cards    = build_cards(stock_news)
    industry_cards = build_cards(industry_news)

    total = len(stock_news) + len(industry_news)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Solar & Renewable Energy India — Daily Report | {date_display}</title>
  <style>
    :root {{
      --bg: #f4f6f9;
      --surface: #ffffff;
      --primary: #1a6b3c;
      --primary-light: #e8f5ee;
      --accent: #f5a623;
      --stock-color: #1558b0;
      --stock-light: #eaf0fb;
      --text: #1e2a38;
      --muted: #6b7a8d;
      --border: #dde3ec;
      --radius: 10px;
      --shadow: 0 2px 12px rgba(0,0,0,0.08);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); }}

    /* ── Header ── */
    header {{
      background: linear-gradient(135deg, #0d3d20 0%, #1a6b3c 60%, #228b22 100%);
      color: #fff;
      padding: 36px 24px 28px;
      text-align: center;
    }}
    header .logo {{ font-size: 2rem; margin-bottom: 6px; }}
    header h1 {{ font-size: 1.65rem; font-weight: 700; letter-spacing: .5px; }}
    header .sub {{ font-size: .95rem; opacity: .85; margin-top: 6px; }}
    .badge-row {{ display: flex; justify-content: center; gap: 12px; margin-top: 16px; flex-wrap: wrap; }}
    .badge {{
      background: rgba(255,255,255,.15);
      border: 1px solid rgba(255,255,255,.3);
      border-radius: 20px;
      padding: 4px 14px;
      font-size: .8rem;
      backdrop-filter: blur(4px);
    }}

    /* ── Summary bar ── */
    .summary-bar {{
      background: var(--accent);
      color: #fff;
      display: flex;
      justify-content: center;
      gap: 40px;
      padding: 12px 24px;
      font-size: .9rem;
      flex-wrap: wrap;
    }}
    .summary-bar span {{ font-weight: 600; }}

    /* ── Layout ── */
    .container {{ max-width: 1100px; margin: 0 auto; padding: 32px 16px 60px; }}

    /* ── Section ── */
    .section {{ margin-bottom: 40px; }}
    .section-header {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 20px;
      border-radius: var(--radius) var(--radius) 0 0;
      color: #fff;
    }}
    .section-header.stock  {{ background: var(--stock-color); }}
    .section-header.industry {{ background: var(--primary); }}
    .section-header .icon {{ font-size: 1.4rem; }}
    .section-header h2 {{ font-size: 1.15rem; font-weight: 700; }}
    .section-header .count {{
      margin-left: auto;
      background: rgba(255,255,255,.25);
      border-radius: 12px;
      padding: 2px 10px;
      font-size: .8rem;
    }}

    /* ── Cards grid ── */
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 16px;
      background: var(--border);
      border: 1px solid var(--border);
      border-top: none;
      border-radius: 0 0 var(--radius) var(--radius);
      padding: 16px;
    }}
    .card {{
      background: var(--surface);
      border-radius: var(--radius);
      padding: 18px;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      gap: 10px;
      border-left: 4px solid var(--border);
      transition: transform .15s, box-shadow .15s;
    }}
    .card:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.12); }}
    .section.stock .card  {{ border-left-color: var(--stock-color); }}
    .section.industry .card {{ border-left-color: var(--primary); }}

    .card-meta {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }}
    .source {{
      font-size: .72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .5px;
      color: var(--muted);
      background: var(--bg);
      padding: 2px 8px;
      border-radius: 4px;
    }}
    .date {{ font-size: .72rem; color: var(--muted); }}

    .headline {{
      font-size: .97rem;
      font-weight: 700;
      color: var(--text);
      text-decoration: none;
      line-height: 1.4;
    }}
    .headline:hover {{ color: var(--primary); text-decoration: underline; }}
    .section.stock .headline:hover {{ color: var(--stock-color); }}

    .summary {{ font-size: .84rem; color: #4a5568; line-height: 1.55; }}

    .read-more {{
      font-size: .8rem;
      font-weight: 600;
      color: var(--primary);
      text-decoration: none;
      margin-top: auto;
    }}
    .section.stock .read-more {{ color: var(--stock-color); }}
    .read-more:hover {{ text-decoration: underline; }}

    .no-news {{ padding: 24px; text-align: center; color: var(--muted); font-style: italic; }}

    /* ── Footer ── */
    footer {{
      text-align: center;
      font-size: .78rem;
      color: var(--muted);
      border-top: 1px solid var(--border);
      padding: 20px 16px;
    }}
    footer a {{ color: var(--primary); text-decoration: none; }}

    @media (max-width: 600px) {{
      header h1 {{ font-size: 1.3rem; }}
      .summary-bar {{ gap: 20px; }}
    }}
  </style>
</head>
<body>

<header>
  <div class="logo">☀️ 🌬️</div>
  <h1>Solar & Renewable Energy India</h1>
  <p class="sub">Daily Market Intelligence Report</p>
  <div class="badge-row">
    <span class="badge">📅 {date_display}</span>
    <span class="badge">🕐 Generated at {time_display}</span>
    <span class="badge">🇮🇳 India Focus</span>
  </div>
</header>

<div class="summary-bar">
  <div>📰 Total Articles &nbsp;<span>{total}</span></div>
  <div>📈 IPO / Stock &nbsp;<span>{len(stock_news)}</span></div>
  <div>🏭 Industry &nbsp;<span>{len(industry_news)}</span></div>
</div>

<div class="container">

  <!-- ── Section 1: IPO / Stock ── -->
  <div class="section stock">
    <div class="section-header stock">
      <span class="icon">📈</span>
      <h2>Section 1 — IPO &amp; Stock Related News</h2>
      <span class="count">{len(stock_news)} articles</span>
    </div>
    <div class="cards">
      {stock_cards}
    </div>
  </div>

  <!-- ── Section 2: Industry ── -->
  <div class="section industry">
    <div class="section-header industry">
      <span class="icon">🏭</span>
      <h2>Section 2 — Industry Related News</h2>
      <span class="count">{len(industry_news)} articles</span>
    </div>
    <div class="cards">
      {industry_cards}
    </div>
  </div>

</div>

<footer>
  <p>Auto-generated by <strong>Daily-News-Report</strong> &nbsp;|&nbsp; Sources: Google News, Mercom India, PV Magazine India &amp; others</p>
  <p style="margin-top:6px;">News links open the original publisher's website. This report is for informational purposes only — not financial advice.</p>
</footer>

</body>
</html>
"""


# ─── Index Page ──────────────────────────────────────────────────────────────
def update_index(report_files):
    """Rebuild reports/index.html listing all past reports."""
    rows = ''
    for f in sorted(report_files, reverse=True):
        slug = os.path.basename(f).replace('report_', '').replace('.html', '')
        try:
            dt = datetime.strptime(slug, '%Y-%m-%d').strftime('%A, %d %B %Y')
        except Exception:
            dt = slug
        rows += f'<tr><td><a href="{os.path.basename(f)}">{dt}</a></td><td><a href="{os.path.basename(f)}">View Report ↗</a></td></tr>\n'

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Daily Solar & Renewable Energy Reports</title>
  <style>
    body{{font-family:'Segoe UI',system-ui,sans-serif;background:#f4f6f9;color:#1e2a38;margin:0}}
    header{{background:linear-gradient(135deg,#0d3d20,#1a6b3c);color:#fff;padding:32px 24px;text-align:center}}
    header h1{{font-size:1.6rem;margin-bottom:6px}}
    header p{{opacity:.85;font-size:.95rem}}
    .container{{max-width:720px;margin:40px auto;padding:0 16px}}
    table{{width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)}}
    th{{background:#1a6b3c;color:#fff;padding:14px 18px;text-align:left;font-size:.9rem}}
    td{{padding:14px 18px;border-bottom:1px solid #dde3ec;font-size:.9rem}}
    tr:last-child td{{border-bottom:none}}
    tr:hover td{{background:#f0f7f4}}
    a{{color:#1a6b3c;font-weight:600;text-decoration:none}}
    a:hover{{text-decoration:underline}}
    .empty{{text-align:center;padding:40px;color:#6b7a8d;font-style:italic}}
  </style>
</head>
<body>
<header>
  <h1>☀️ Solar & Renewable Energy India</h1>
  <p>Daily News Report Archive</p>
</header>
<div class="container">
  <table>
    <thead><tr><th>Report Date</th><th>Link</th></tr></thead>
    <tbody>
      {'<tr><td colspan="2" class="empty">No reports yet. Run the workflow to generate the first report.</td></tr>' if not rows else rows}
    </tbody>
  </table>
</div>
</body>
</html>"""

    with open('reports/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    print("⏳ Fetching news articles…")
    articles = fetch_all_articles()
    print(f"   → {len(articles)} unique articles fetched")

    print("🗂  Categorising…")
    stock_news, industry_news = categorise(articles)
    print(f"   → {len(stock_news)} IPO/Stock  |  {len(industry_news)} Industry")

    print("🖊  Generating HTML report…")
    report_html = generate_html(stock_news, industry_news)

    os.makedirs('reports', exist_ok=True)
    now_ist  = datetime.now(IST)
    date_slug = now_ist.strftime('%Y-%m-%d')
    report_path  = f'reports/report_{date_slug}.html'

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_html)

    # Also write as latest.html at root for GitHub Pages default
    with open('reports/latest.html', 'w', encoding='utf-8') as f:
        f.write(report_html)

    # Rebuild archive index
    all_reports = sorted(
        [p for p in os.listdir('reports') if p.startswith('report_') and p.endswith('.html')]
    )
    update_index([f'reports/{p}' for p in all_reports])

    # Save JSON summary for future use
    summary = {
        'date': date_slug,
        'generated_at': now_ist.isoformat(),
        'total': len(stock_news) + len(industry_news),
        'stock_count': len(stock_news),
        'industry_count': len(industry_news),
    }
    with open('reports/summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"✅ Report saved → {report_path}")
    print(f"✅ Archive index updated → reports/index.html")

if __name__ == '__main__':
    main()
