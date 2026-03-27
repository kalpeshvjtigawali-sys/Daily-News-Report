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


# ─── Config ─────────────────────────────────────────────────────────────────
NEWS_LOOKBACK_DAYS = 2   # include articles published within last N days

# ─── Helpers ────────────────────────────────────────────────────────────────
def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    return text.strip()

def truncate(text, limit=600):
    text = text.strip()
    return text[:limit].rsplit(' ', 1)[0] + '…' if len(text) > limit else text

def parse_date(entry):
    """Return (datetime_utc, display_string) from feed entry."""
    try:
        t = entry.get('published_parsed') or entry.get('updated_parsed')
        if t:
            dt_utc = datetime(*t[:6], tzinfo=timezone.utc)
            dt_ist = dt_utc.astimezone(IST)
            return dt_utc, dt_ist.strftime('%d %b %Y, %I:%M %p IST')
    except Exception:
        pass
    return None, ''

def is_recent(dt_utc):
    """Return True if article is within the lookback window."""
    if dt_utc is None:
        return True   # no date info → include it
    cutoff = datetime.now(timezone.utc) - timedelta(days=NEWS_LOOKBACK_DAYS)
    return dt_utc >= cutoff

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
            for entry in feed.entries[:20]:   # check more entries to cover 2 days
                raw_title = entry.get('title', '')
                title = clean_title(html.unescape(raw_title))
                if not title or title.lower() in seen:
                    continue

                dt_utc, date_display = parse_date(entry)

                # Skip articles older than lookback window
                if not is_recent(dt_utc):
                    continue

                seen.add(title.lower())

                summary_raw = entry.get('summary', entry.get('description', ''))
                summary = truncate(clean_html(summary_raw))

                articles.append({
                    'title': title,
                    'link': entry.get('link', '#'),
                    'summary': summary,
                    'source': source_name(feed_title, entry),
                    'date': date_display,
                    'dt_utc': dt_utc,   # used for sorting
                })
        except Exception as e:
            print(f"[WARN] Could not fetch {url}: {e}")
        time.sleep(0.4)

    # Sort newest first
    articles.sort(key=lambda a: a['dt_utc'] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
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

    return stock_news[:30], industry_news[:35]


# ─── HTML Report ─────────────────────────────────────────────────────────────
CARD_TEMPLATE = """
        <div class="card">
          <div class="card-top">
            <div class="card-num">{num}</div>
            <div class="card-meta">
              <span class="source">{source}</span>
              <span class="date">{date}</span>
            </div>
          </div>
          <a class="headline" href="{link}" target="_blank" rel="noopener noreferrer">{title}</a>
          <div class="divider"></div>
          <p class="summary">{summary}</p>
          <a class="read-more" href="{link}" target="_blank" rel="noopener noreferrer">
            Read Full Article &nbsp;↗
          </a>
        </div>"""

def build_cards(articles, section):
    if not articles:
        return '<p class="no-news">No news found for this category today.</p>'
    return '\n'.join(
        CARD_TEMPLATE.format(
            num=i + 1,
            source=html.escape(art['source']),
            date=html.escape(art['date']),
            link=art['link'],
            title=html.escape(art['title']),
            summary=html.escape(art['summary']),
        )
        for i, art in enumerate(articles)
    )

def generate_html(stock_news, industry_news):
    now_ist = datetime.now(IST)
    date_display = now_ist.strftime('%A, %d %B %Y')
    time_display = now_ist.strftime('%I:%M %p IST')
    lookback_display = f"Last {NEWS_LOOKBACK_DAYS} Days"
    date_slug    = now_ist.strftime('%Y-%m-%d')

    stock_cards    = build_cards(stock_news, 'stock')
    industry_cards = build_cards(industry_news, 'industry')

    total = len(stock_news) + len(industry_news)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Solar & Renewable Energy India — Daily Report | {date_display}</title>
  <style>
    :root {{
      --bg:           #eef1f6;
      --surface:      #ffffff;
      --primary:      #1a6b3c;
      --primary-dark: #0d3d20;
      --stock-color:  #1558b0;
      --stock-dark:   #0b3d7a;
      --accent:       #e07b00;
      --text:         #1a2333;
      --muted:        #5a6a7e;
      --border:       #d4dbe6;
      --radius:       12px;
      --shadow:       0 2px 16px rgba(0,0,0,0.07);
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      font-size: 15px;
      line-height: 1.6;
    }}

    /* ── HEADER ── */
    header {{
      background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 55%, #2e8b57 100%);
      color: #fff;
      padding: 44px 32px 36px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }}
    header::before {{
      content: '';
      position: absolute; inset: 0;
      background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.04'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    }}
    header .logo {{ font-size: 2.4rem; margin-bottom: 10px; }}
    header h1 {{
      font-size: 1.9rem;
      font-weight: 800;
      letter-spacing: .4px;
      text-shadow: 0 1px 4px rgba(0,0,0,.2);
    }}
    header .sub {{
      font-size: 1rem;
      opacity: .88;
      margin-top: 6px;
      letter-spacing: .3px;
    }}
    .badge-row {{
      display: flex;
      justify-content: center;
      gap: 10px;
      margin-top: 20px;
      flex-wrap: wrap;
    }}
    .badge {{
      background: rgba(255,255,255,.18);
      border: 1px solid rgba(255,255,255,.35);
      border-radius: 20px;
      padding: 5px 16px;
      font-size: .82rem;
      font-weight: 500;
      backdrop-filter: blur(6px);
    }}

    /* ── STATS BAR ── */
    .stats-bar {{
      display: flex;
      justify-content: center;
      gap: 0;
      background: #fff;
      border-bottom: 3px solid var(--accent);
      flex-wrap: wrap;
    }}
    .stat-item {{
      padding: 14px 36px;
      text-align: center;
      border-right: 1px solid var(--border);
      flex: 1;
      min-width: 160px;
    }}
    .stat-item:last-child {{ border-right: none; }}
    .stat-num {{ font-size: 1.7rem; font-weight: 800; color: var(--accent); line-height: 1; }}
    .stat-label {{ font-size: .75rem; color: var(--muted); text-transform: uppercase; letter-spacing: .6px; margin-top: 3px; }}

    /* ── LAYOUT ── */
    .container {{ max-width: 900px; margin: 0 auto; padding: 36px 16px 64px; }}

    /* ── SECTION ── */
    .section {{ margin-bottom: 48px; }}
    .section-header {{
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 16px 24px;
      border-radius: var(--radius) var(--radius) 0 0;
      color: #fff;
    }}
    .section-header.stock    {{ background: linear-gradient(90deg, var(--stock-dark), var(--stock-color)); }}
    .section-header.industry {{ background: linear-gradient(90deg, var(--primary-dark), var(--primary)); }}
    .section-icon {{ font-size: 1.5rem; }}
    .section-title {{
      font-size: 1.1rem;
      font-weight: 700;
      letter-spacing: .3px;
    }}
    .section-subtitle {{
      font-size: .8rem;
      opacity: .8;
      margin-top: 2px;
    }}
    .section-count {{
      margin-left: auto;
      background: rgba(255,255,255,.22);
      border-radius: 14px;
      padding: 3px 14px;
      font-size: .82rem;
      font-weight: 600;
      white-space: nowrap;
    }}

    /* ── ARTICLE LIST ── */
    .articles {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-top: none;
      border-radius: 0 0 var(--radius) var(--radius);
      overflow: hidden;
    }}

    /* ── ARTICLE CARD ── */
    .card {{
      padding: 24px 28px;
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 0;
      transition: background .15s;
    }}
    .card:last-child {{ border-bottom: none; }}
    .card:hover {{ background: #f8fafd; }}

    .card-top {{
      display: flex;
      align-items: flex-start;
      gap: 14px;
      margin-bottom: 10px;
    }}
    .card-num {{
      flex-shrink: 0;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: .75rem;
      font-weight: 800;
      color: #fff;
      margin-top: 2px;
    }}
    .section.stock    .card-num {{ background: var(--stock-color); }}
    .section.industry .card-num {{ background: var(--primary); }}

    .card-meta {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      flex: 1;
    }}
    .source {{
      font-size: .72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .6px;
      color: #fff;
      padding: 2px 10px;
      border-radius: 4px;
    }}
    .section.stock    .source {{ background: var(--stock-color); }}
    .section.industry .source {{ background: var(--primary); }}

    .date {{
      font-size: .76rem;
      color: var(--muted);
    }}

    .headline {{
      display: block;
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text);
      text-decoration: none;
      line-height: 1.45;
      margin-bottom: 12px;
    }}
    .headline:hover {{ color: var(--primary); text-decoration: underline; }}
    .section.stock .headline:hover {{ color: var(--stock-color); }}

    .divider {{
      height: 2px;
      border-radius: 2px;
      margin-bottom: 14px;
      width: 48px;
    }}
    .section.stock    .divider {{ background: var(--stock-color); }}
    .section.industry .divider {{ background: var(--primary); }}

    .summary {{
      font-size: .92rem;
      color: #3d4f63;
      line-height: 1.75;
      margin-bottom: 16px;
    }}

    .read-more {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: .82rem;
      font-weight: 700;
      text-decoration: none;
      padding: 6px 16px;
      border-radius: 6px;
      border: 1.5px solid;
      align-self: flex-start;
      transition: background .15s, color .15s;
    }}
    .section.stock .read-more {{
      color: var(--stock-color);
      border-color: var(--stock-color);
    }}
    .section.stock .read-more:hover {{
      background: var(--stock-color);
      color: #fff;
    }}
    .section.industry .read-more {{
      color: var(--primary);
      border-color: var(--primary);
    }}
    .section.industry .read-more:hover {{
      background: var(--primary);
      color: #fff;
    }}

    .no-news {{
      padding: 40px;
      text-align: center;
      color: var(--muted);
      font-style: italic;
      font-size: .95rem;
    }}

    /* ── FOOTER ── */
    footer {{
      text-align: center;
      font-size: .8rem;
      color: var(--muted);
      border-top: 1px solid var(--border);
      padding: 24px 16px;
      background: var(--surface);
    }}
    footer strong {{ color: var(--text); }}

    @media (max-width: 600px) {{
      header h1 {{ font-size: 1.4rem; }}
      .card {{ padding: 18px 16px; }}
      .stat-item {{ padding: 12px 20px; }}
    }}
  </style>
</head>
<body>

<header>
  <div class="logo">☀️ 🌬️</div>
  <h1>Solar &amp; Renewable Energy India</h1>
  <p class="sub">Daily Market Intelligence Report</p>
  <div class="badge-row">
    <span class="badge">📅 {date_display}</span>
    <span class="badge">🕐 Generated {time_display}</span>
    <span class="badge">📆 Coverage: {lookback_display}</span>
    <span class="badge">🇮🇳 India Focus</span>
  </div>
</header>

<div class="stats-bar">
  <div class="stat-item">
    <div class="stat-num">{total}</div>
    <div class="stat-label">Total Articles</div>
  </div>
  <div class="stat-item">
    <div class="stat-num">{len(stock_news)}</div>
    <div class="stat-label">IPO &amp; Stock</div>
  </div>
  <div class="stat-item">
    <div class="stat-num">{len(industry_news)}</div>
    <div class="stat-label">Industry News</div>
  </div>
</div>

<div class="container">

  <!-- ── Section 1: IPO / Stock ── -->
  <div class="section stock">
    <div class="section-header stock">
      <span class="section-icon">📈</span>
      <div>
        <div class="section-title">Section 1 — IPO &amp; Stock Related News</div>
        <div class="section-subtitle">Market movements · Listings · Investor activity · Analyst ratings</div>
      </div>
      <span class="section-count">{len(stock_news)} articles</span>
    </div>
    <div class="articles">
      {stock_cards}
    </div>
  </div>

  <!-- ── Section 2: Industry ── -->
  <div class="section industry">
    <div class="section-header industry">
      <span class="section-icon">🏭</span>
      <div>
        <div class="section-title">Section 2 — Industry Related News</div>
        <div class="section-subtitle">Projects · Tenders · Policy · Capacity additions · Technology</div>
      </div>
      <span class="section-count">{len(industry_news)} articles</span>
    </div>
    <div class="articles">
      {industry_cards}
    </div>
  </div>

</div>

<footer>
  <p>Auto-generated by <strong>Daily-News-Report</strong> &nbsp;·&nbsp; Sources: Google News, Mercom India, PV Magazine India &amp; others</p>
  <p style="margin-top:6px; color:#8a9ab0;">News links open the original publisher's website. This report is for informational purposes only — not financial advice.</p>
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
