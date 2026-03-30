#!/usr/bin/env python3
"""
Daily Solar/Renewable Energy News Report Generator for India
Fetches news from Google News RSS and other sources, categorizes them,
and generates a professional HTML report matching the Eastman design.
"""

import feedparser
import re
import html
import os
import time
import json
import requests
from datetime import datetime, timezone, timedelta
try:
    from bs4 import BeautifulSoup
    _BS4_OK = True
except ImportError:
    _BS4_OK = False

# ─── India Standard Time ────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))

# ─── Priority companies for IPO/Stock section ────────────────────────────────
PRIORITY_COMPANIES = [
    'waaree energies', 'waaree',
    'tata power',
    'reliance industries', 'reliance solar', 'reliance renewable', 'reliance green',
    'ntpc green energy', 'ntpc green',
    'jsw energy', 'jsw energies', 'jsw solar',
    'premier energies',
    'borosil renewables', 'borosil',
    'saatvik solar', 'saatvik',
    'utl solar', 'utl',
    'fujiyama solar', 'fujiyama',
    'exide industries', 'exide',
    'amara raja batteries', 'amara raja', 'amaraja',
]

# Other solar/RE companies to track in stock section
OTHER_STOCK_COMPANIES = [
    'adani green', 'suzlon', 'inox wind', 'inox green',
    'sterling wilson', 'orient green', 'renew power', 'azure power',
    'hero future energies', 'greenko', 'torrent power', 'cesc',
    'power grid', 'ireda', 'sjvn', 'nhpc',
]

# ─── RSS Feed Sources ────────────────────────────────────────────────────────
RSS_FEEDS = [
    # General solar/renewable India
    "https://news.google.com/rss/search?q=solar+energy+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=renewable+energy+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=wind+energy+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=green+energy+india&hl=en-IN&gl=IN&ceid=IN:en",
    # General stock/IPO
    "https://news.google.com/rss/search?q=solar+IPO+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=renewable+energy+stock+NSE+BSE+india&hl=en-IN&gl=IN&ceid=IN:en",
    # Industry
    "https://news.google.com/rss/search?q=solar+power+plant+india+MW+GW&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=MNRE+solar+policy+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=green+hydrogen+india&hl=en-IN&gl=IN&ceid=IN:en",
    # ── Residential / Rooftop solar ──
    "https://news.google.com/rss/search?q=PM+Surya+Ghar+Muft+Bijli+Yojana+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=rooftop+solar+residential+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=home+solar+system+india+subsidy&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=solar+rooftop+net+metering+india&hl=en-IN&gl=IN&ceid=IN:en",
    # ── Priority company feeds ──
    "https://news.google.com/rss/search?q=Waaree+Energies+solar&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=TATA+Power+solar+renewable&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Reliance+Industries+solar+renewable+energy&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=NTPC+Green+Energy+solar&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=JSW+Energy+solar+renewable&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Premier+Energies+solar&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Borosil+Renewables+solar&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Saatvik+Solar+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=UTL+Solar+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Fujiyama+Solar+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Exide+Industries+solar+battery+energy+storage&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Amara+Raja+Batteries+solar+energy+storage&hl=en-IN&gl=IN&ceid=IN:en",
    # ── Regulatory & Policy feeds ──
    "https://news.google.com/rss/search?q=CERC+solar+renewable+energy+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=MNRE+policy+order+india+2025+2026&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=solar+renewable+energy+regulation+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=SECI+tender+solar+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=PLI+solar+module+india+policy&hl=en-IN&gl=IN&ceid=IN:en",
    # ── Solar industry company feeds ──
    "https://news.google.com/rss/search?q=Adani+Green+Energy+solar&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Suzlon+Energy+wind+solar+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=INOX+Wind+renewable+energy+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=ReNew+Power+solar+wind+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Sterling+Wilson+solar+EPC+india&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=IREDA+solar+renewable+india&hl=en-IN&gl=IN&ceid=IN:en",
    # Specialist portals
    "https://mercomindia.com/feed/",
    "https://www.pv-magazine-india.com/feed/",
]

# ─── Keyword Sets ────────────────────────────────────────────────────────────
STOCK_KEYWORDS = [
    # Market/finance terms
    'ipo', 'stock', 'share', 'nse', 'bse', 'sensex', 'nifty', 'listing',
    'market cap', 'sebi', 'equity', 'invest', 'fund', 'mutual fund',
    'dividend', 'earnings', 'quarter', 'revenue', 'profit', 'loss',
    'fundraise', 'bond', 'debt', 'valuation', 'investors',
    'shares', 'analyst', 'target price', 'buy rating', 'hold rating',
    'fpo', 'preferential allotment', 'qip', 'rights issue',
    # Priority companies
    'waaree energies', 'waaree',
    'tata power',
    'reliance industries', 'reliance solar', 'reliance renewable',
    'ntpc green energy', 'ntpc green',
    'jsw energy', 'jsw energies', 'jsw solar',
    'premier energies',
    'borosil renewables', 'borosil',
    'saatvik solar', 'saatvik',
    'utl solar',
    'fujiyama solar', 'fujiyama',
    # Other solar companies
    'adani green', 'suzlon', 'inox wind', 'inox green',
    'sterling and wilson', 'sterling wilson',
    'orient green', 'renew power', 'azure power',
    'hero future energies', 'greenko', 'torrent power',
    'ireda', 'sjvn', 'nhpc', 'power grid',
]

INDUSTRY_KEYWORDS = [
    # Capacity / project
    'mw', 'gw', 'megawatt', 'gigawatt', 'solar park', 'wind farm',
    'tender', 'bid', 'auction', 'capacity', 'plant', 'project',
    'power purchase', 'ppa', 'power plant', 'floating solar',
    'solar farm', 'wind turbine', 'solar module', 'solar cell',
    'installation', 'deployment', 'commissioning', 'epc',
    # Regulatory / policy
    'cerc', 'serc', 'mnre', 'ministry', 'policy', 'regulation',
    'regulatory', 'compliance', 'amendment', 'notification',
    'circular', 'directive', 'order by', 'tribunal', 'nclt',
    'tariff', 'grid', 'discom', 'net metering', 'rpo',
    'renewable purchase obligation', 'rec', 'carbon credit',
    'seci', 'rewa', 'ireda', 'irena', 'pli scheme', 'pli solar',
    'solar mission', 'pm kusum', 'pm surya ghar',
    # Rooftop / residential
    'rooftop', 'rooftop solar', 'residential solar', 'home solar',
    'solar subsidy', 'solar water heater', 'solar pump',
    # Technology / storage
    'green hydrogen', 'battery storage', 'bess', 'energy storage',
    'offshore wind', 'hybrid', 'evacuation', 'transmission',
    'electrolyser', 'fuel cell', 'floating solar',
    # Solar industry companies
    'adani green', 'suzlon', 'inox wind', 'inox green',
    'sterling wilson', 'renew power', 'azure power',
    'hero future energies', 'greenko', 'torrent power',
    'ireda', 'sjvn', 'nhpc', 'power grid corporation',
    'ntpc renewable', 'tata power solar', 'avaada', 'amp energy',
    'acme solar', 'eden renewables', 'ayana renewable',
]

RELEVANCE_KEYWORDS = [
    'solar', 'renewable', 'wind energy', 'clean energy', 'green energy',
    'photovoltaic', 'pv ', 'energy storage', 'solar power', 'wind power',
    'rooftop solar', 'solar farm', 'solar park', 'offshore wind',
    'green hydrogen', 'battery storage', 'bess',
    'residential solar', 'pm surya ghar', 'home solar', 'rooftop pv',
    'solar subsidy', 'net metering', 'solar for home', 'solar water heater',
]

# ─── Analyst / noise filter — skip articles that are ONLY analyst opinions ────
ANALYST_FILTER_KEYWORDS = [
    'analyst', 'target price', 'buy rating', 'hold rating', 'sell rating',
    'brokerage', 'broking', 'price target', 'stock rating', 'upgrade to buy',
    'downgrade to sell', 'initiates coverage', 'reiterates buy',
    'reiterates hold', 'reiterates sell', 'overweight', 'underweight',
    'outperform', 'underperform', 'technical analysis', 'rsi level',
    'support level', 'resistance level', 'moving average', 'fibonacci',
    'short term target', 'long term target',
    # Analyst recommendation titles
    'stock to buy', 'stocks to buy', 'buy this stock', 'top pick',
    '% upside', 'upside target', 'upside potential', '% return',
    'multibagger', 'wealth creator', 'stock recommendation',
    'should you buy', 'should i buy', 'is it a buy',
]

# High-importance keywords — allow a 2nd article for the same company if these appear
HIGH_IMPORTANCE_KEYWORDS = [
    'ipo', 'listing', 'fundraise', 'merger', 'acquisition', 'takeover',
    'sebi', 'penalty', 'court', 'settlement', 'bankruptcy', 'insolvency',
    'raises', 'secures', 'wins', 'commissions', 'record', 'milestone',
    'qip', 'fpo', 'rights issue', 'preferential allotment', 'delisting',
]

# ─── Config ──────────────────────────────────────────────────────────────────
NEWS_LOOKBACK_DAYS = 2

# ─── Helpers ─────────────────────────────────────────────────────────────────
def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    return text.strip()

def truncate(text, limit=700):
    text = text.strip()
    if not text:
        return ''
    return text[:limit].rsplit(' ', 1)[0] + '…' if len(text) > limit else text

_ARTICLE_CACHE = {}   # url → list[str]

_FETCH_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-IN,en;q=0.9',
}

_SKIP_TAGS = {'script','style','nav','header','footer','aside',
              'form','noscript','iframe','figure','figcaption'}

_NOISE_PAT = re.compile(
    r'(cookie|subscribe|sign in|log in|newsletter|advertisement|'
    r'click here|read more|all rights reserved|©|follow us|share this)', re.I)

def _fetch_article_sentences(url, timeout=5):
    """Fetch article page → clean sentences. Returns [] on failure."""
    if not _BS4_OK:
        return []
    if url in _ARTICLE_CACHE:
        return _ARTICLE_CACHE[url]
    try:
        r = requests.get(url, timeout=timeout, headers=_FETCH_HEADERS,
                         allow_redirects=True)
        if r.status_code == 200 and 'text/html' in r.headers.get('Content-Type', ''):
            soup = BeautifulSoup(r.text, 'html.parser')
            for tag in soup(_SKIP_TAGS):
                tag.decompose()
            body = (soup.find('article') or soup.find('main') or
                    soup.find(class_=re.compile(r'article[-_]?(body|content|text)', re.I)) or
                    soup.find('body'))
            raw  = re.sub(r'\s+', ' ', body.get_text(' ') if body else '').strip()
            sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', raw)
                     if len(s.strip()) > 35 and not _NOISE_PAT.search(s)]
            result = sents[:5]
            _ARTICLE_CACHE[url] = result
            return result
    except Exception:
        pass
    _ARTICLE_CACHE[url] = []
    return []

# ── Title-analysis helpers ─────────────────────────────────────────────────────
_NUM_PAT = re.compile(
    r'\b(\d[\d,]*\.?\d*)\s*(mw|gw|kw|mwh|gwh|kwh|%|crore|lakh|million|billion|rs\.?|₹)\b', re.I)

_INDIA_LOCATIONS = [
    'rajasthan','gujarat','maharashtra','tamil nadu','andhra pradesh','telangana',
    'karnataka','kerala','madhya pradesh','uttar pradesh','punjab','haryana',
    'odisha','jharkhand','west bengal','himachal','uttarakhand','arunachal',
    'ladakh','jammu','kashmir','rewa','khavda','bhadla','pavagada',
    'nellore','coimbatore','surat','pune','nagpur','jodhpur',
]

_REGULATORS = ['cerc','serc','sebi','mnre','ministry','nclt','nclat','tribunal',
               'high court','supreme court']

def _extract_title_facts(title):
    t_lower = title.lower()
    nums = _NUM_PAT.findall(title)
    co_m = re.match(
        r'^([A-Z][A-Za-z0-9\s&\-\.\']+?)(?=\s+(?:Declares|Wins|Secures|Launches|'
        r'Commissions|Raises|Signs|Awards|Approves|Achieves|Expands|Completes|'
        r'Announces|Acquires|Files|Receives|Targets|Bids|Installs|Deploys|Sets|'
        r'Reports|Posts|Records|Bags|Gets|Joins|Partners|Plans|Seeks|Cuts|Drops|'
        r'Surges|Falls|Slips|Hits|Reaches|Crosses|Enters|Exits|Schedules|Hikes|Plunges))', title)
    if co_m:
        company = co_m.group(1).strip()
    else:
        # Fallback: first sequence of capitalized words at start of title
        fb = re.match(r'^([A-Z][A-Za-z0-9\s&\-\.]+?)(?=\s+[a-z]|$)', title)
        company = fb.group(1).strip() if fb else ''
    location = next((l.title() for l in _INDIA_LOCATIONS if l in t_lower), '')
    regulator = next((r.upper() for r in _REGULATORS if r in t_lower), '')
    return nums, company, location, regulator

def _news_type(t_lower, nums):
    if any(w in t_lower for w in ['declares commercial operation','commissions','commissioned',' cod']):
        return 'commissioning'
    if any(w in t_lower for w in ['ipo','fpo','qip','listing','rights issue','preferential allotment','goes public']):
        return 'ipo'
    if any(w in t_lower for w in ['cerc','serc','high court','supreme court','nclt','relief','penalty','case','lawsuit','legal']):
        return 'legal'
    if any(w in t_lower for w in ['profit','revenue','ebitda','quarterly',' q1 ',' q2 ',' q3 ',' q4 ','results','pbt','pat']):
        return 'results'
    if any(w in t_lower for w in ['rooftop','surya ghar','pm kusum','prosumer','net metering','residential solar']):
        return 'rooftop'
    if any(w in t_lower for w in ['tender','auction','rfp','rfq','floats','invited bids','invites bid']):
        return 'tender'
    if any(w in t_lower for w in ['mnre','ministry','policy','pli','amendment','regulation','tariff','rpo','government scheme']):
        return 'policy'
    if nums and nums[0][1].lower() in ('crore','lakh','million','billion'):
        if any(w in t_lower for w in ['raises','raised','fundraise','secures funding','ncd','bond','debt','investment']):
            return 'financial'
    if any(w in t_lower for w in ['secures','wins','bags','awarded contract','order worth','supply order','order for','bagged','clinches','inks deal','nets order','contract worth','supply agreement']):
        return 'order'
    if any(w in t_lower for w in ['analyst','investor meet','investor day','concall','conference call']):
        return 'analyst_meet'
    if any(w in t_lower for w in ['share price','stock rises','stock falls','surges','plunges',' hits 52','rally']):
        return 'stock_move'
    if any(w in t_lower for w in ['expands','targets','plans to','aims','sets target','eyes','forays']):
        return 'expansion'
    if any(w in t_lower for w in ['hydrogen','electrolyser','green fuel']):
        return 'hydrogen'
    if any(w in t_lower for w in ['storage','bess','battery','mwh','gwh']):
        return 'storage'
    return 'general'

def _title_to_lines(title, source, art_category='industry'):
    """Return 3 lines unique to THIS article — based on its news type and specific facts."""
    t       = title.strip().rstrip('.')
    t_lower = t.lower()
    nums, company, location, regulator = _extract_title_facts(t)
    ntype   = _news_type(t_lower, nums)

    co       = company or source or 'The company'
    qty      = nums[0][0] if nums else ''
    unit_raw = nums[0][1] if nums else ''
    unit     = unit_raw.upper() if unit_raw.lower() in ('mw','gw','kw','mwh','gwh','kwh') else unit_raw
    loc_str  = f" in {location}" if location else " across India"

    if ntype == 'commissioning':
        l1 = (f"{co} has achieved commercial operation of its {qty} {unit} solar project{loc_str}, "
              f"adding fresh renewable capacity and marking a key execution milestone.")
        l2 = (f"The {qty} {unit} plant will supply clean electricity to the grid under a Power Purchase Agreement, "
              f"contributing directly to India's national target of 500 GW renewable capacity by 2030.")
        l3 = (f"Commissioning milestones are closely tracked by investors and analysts "
              f"as they signal the start of revenue generation and validate the company's project delivery capability.")

    elif ntype == 'order':
        order_size = f"{qty} {unit} " if qty and unit_raw.lower() in ('mw','gw','kw') else (f"₹{qty} {unit} " if qty else "")
        l1 = (f"{co} has secured a {order_size}solar order, adding to its revenue backlog "
              f"and reinforcing its position as a key player in India's solar market.")
        l2 = (f"Order wins of this nature strengthen {co}'s manufacturing or EPC pipeline "
              f"and signal rising demand from utilities, PSUs, or commercial & industrial buyers.")
        l3 = (f"A growing order book directly supports revenue visibility and investor confidence — "
              f"it is one of the most-watched metrics for solar manufacturers and EPC companies.")

    elif ntype == 'ipo':
        l1 = (f"{co} is advancing its public market journey, opening up India's solar growth story "
              f"to a broader base of retail and institutional investors on Indian stock exchanges.")
        l2 = (f"IPO proceeds are typically earmarked for capacity expansion, debt reduction, and "
              f"working capital, enabling the company to scale up faster in a competitive market.")
        l3 = (f"Solar sector IPOs in India have attracted strong subscription demand, "
              f"reflecting high investor confidence in long-term renewable energy sector growth.")

    elif ntype == 'legal':
        reg = regulator or 'the regulatory authority'
        l1 = (f"{co} has received a key ruling from {reg}, which could directly affect "
              f"its project economics, tariff recovery, or compliance obligations.")
        l2 = (f"Regulatory and legal decisions involving GST, tariff adjustments, or compliance orders "
              f"can materially impact a solar company's revenue recognition and project margins.")
        l3 = (f"The outcome of this case sets a precedent for similar disputes across the sector, "
              f"making it a development closely watched by developers, financiers, and legal counsel.")

    elif ntype == 'results':
        l1 = (f"{co} has disclosed its latest financial results, offering a window into its revenue "
              f"growth, operational efficiency, and profitability for the reporting period.")
        l2 = (f"Key performance indicators — including revenue from operations, EBITDA margins, and net profit — "
              f"reflect the company's project commissioning pace and order execution progress.")
        l3 = (f"Earnings releases are pivotal events for stock market investors, "
              f"often driving near-term price action and shaping analyst target revisions.")

    elif ntype == 'rooftop':
        l1 = (f"This update relates to India's rooftop solar segment — one of the fastest-growing "
              f"areas of the clean energy market, serving households, businesses, and institutions.")
        l2 = (f"Government schemes like PM Surya Ghar Muft Bijli Yojana and net metering regulations "
              f"are enabling millions of Indians to generate their own clean electricity and reduce bills.")
        l3 = (f"Rooftop solar reduces grid dependency for end-users and promotes distributed generation, "
              f"playing a vital role alongside large-scale solar parks in India's energy transition.")

    elif ntype == 'tender':
        cap_str = f"{qty} {unit} " if qty else ""
        l1 = (f"A {cap_str}solar tender has been issued{loc_str}, creating fresh project opportunities "
              f"for solar developers, EPC firms, and equipment suppliers across India.")
        l2 = (f"Competitive bidding for tenders of this scale attracts leading developers and typically "
              f"results in aggressive tariff discovery, benefiting DISCOMs and end consumers.")
        l3 = (f"India's auction-based solar market has consistently driven tariffs to record lows, "
              f"making solar one of the cheapest sources of new electricity generation.")

    elif ntype == 'policy':
        l1 = (f"A regulatory or policy development has been announced that could reshape "
              f"investment flows, project approval timelines, or equipment sourcing in India's solar sector.")
        l2 = (f"Policy signals from MNRE, state energy departments, or CERC are critical inputs "
              f"for developers planning capacity additions and for financiers structuring project debt.")
        l3 = (f"India's solar market is highly policy-sensitive — clarity and consistency in government "
              f"regulation are essential for sustaining the pace of renewable capacity addition.")

    elif ntype == 'financial':
        l1 = (f"{co} has raised ₹{qty} {unit} in fresh capital, strengthening its financial position "
              f"to fund upcoming capacity additions, project development, or debt reduction.")
        l2 = (f"This fundraise signals institutional confidence in {co}'s growth strategy and "
              f"its ability to scale operations in India's increasingly competitive clean energy market.")
        l3 = (f"Access to capital at competitive rates is a key advantage for solar companies — "
              f"it enables aggressive project bidding, faster manufacturing scale-up, and lower tariff offers.")

    elif ntype == 'analyst_meet':
        l1 = (f"{co} has scheduled an analyst and investor interaction, where management is expected to "
              f"discuss order pipeline, capacity expansion plans, financial guidance, and market outlook.")
        l2 = (f"Investor meets provide direct access to management commentary on near-term order wins, "
              f"margins, working capital, and strategic priorities — key inputs for equity research.")
        l3 = (f"Such events reflect a company's commitment to investor transparency and "
              f"often coincide with or precede major business announcements or quarterly earnings.")

    elif ntype == 'stock_move':
        l1 = (f"{co}'s stock is attracting market attention on Indian exchanges, "
              f"with price movement driven by business developments or broader sector sentiment.")
        l2 = (f"Share price moves in the solar sector are often triggered by order disclosures, "
              f"earnings beats, capacity commissioning news, or policy-related catalysts.")
        l3 = (f"Investors should evaluate whether such price action is backed by fundamental "
              f"changes in business outlook or reflects short-term momentum trading activity.")

    elif ntype == 'expansion':
        l1 = (f"{co} has outlined expansion targets or strategic growth plans{loc_str}, "
              f"reflecting its ambition to scale up in India's fast-growing solar energy market.")
        l2 = (f"Expansion announcements reveal management's confidence in long-term project demand, "
              f"domestic manufacturing opportunities, and the company's ability to execute at scale.")
        l3 = (f"India's solar sector is attracting aggressive capacity expansion from established players "
              f"and new entrants alike, supported by strong government policy tailwinds and rising demand.")

    elif ntype == 'hydrogen':
        l1 = (f"This development relates to green hydrogen — a clean fuel produced using renewable "
              f"electricity — increasingly central to India's industrial decarbonisation strategy.")
        l2 = (f"India's National Green Hydrogen Mission targets 5 MMTPA output by 2030, "
              f"creating significant opportunities for electrolyser manufacturers and RE project developers.")
        l3 = (f"Green hydrogen production requires large volumes of solar and wind power, "
              f"making it a major demand driver for renewable energy in the decade ahead.")

    elif ntype == 'storage':
        l1 = (f"This news covers energy storage — a critical technology that allows solar and "
              f"wind power to be dispatched beyond generation hours, enabling 24x7 clean power supply.")
        l2 = (f"Battery Energy Storage Systems (BESS) are gaining rapid traction in India as "
              f"costs decline and grid operators increasingly mandate storage in new renewable tenders.")
        l3 = (f"India's energy storage market is projected to grow significantly, driven by "
              f"round-the-clock RE obligations and rising corporate demand for firm clean energy.")

    else:  # general
        l1 = (f"{co} is involved in a new development in India's solar and renewable energy sector, "
              f"reflecting the dynamic commercial, regulatory, and investment activity across the industry.")
        l2 = (f"India's clean energy sector is seeing record activity in 2025–26, with new project "
              f"announcements, manufacturing investments, and policy developments emerging regularly.")
        l3 = (f"Stakeholders across the solar value chain — developers, manufacturers, financiers, and "
              f"policymakers — are actively shaping India's next phase of clean energy expansion.")

    return [l1, l2, l3]
def _rss_sentences(summary, title):
    """Extract genuine non-title sentences from RSS summary."""
    # Strip trailing source attribution (Google News: '  SourceName')
    cleaned = re.sub(r'\s{2,}[A-Za-z].*$', '', summary).strip()
    # Remove sentences that are essentially just the title
    title_core = title.lower()[:40]
    sents = []
    for s in re.split(r'(?<=[.!?])\s+', cleaned):
        s = s.strip()
        if len(s) > 30 and s.lower()[:40] != title_core:
            sents.append(s)
    return sents

def get_description_lines(art, art_category='industry'):
    """Return exactly 3 meaningful, non-repetitive description lines."""
    summary = art.get('summary', '').strip()
    title   = art.get('title', '').strip()
    source  = art.get('source', '').strip()
    link    = art.get('link', '')

    # 1. Try fetching article for rich content
    fetched = []
    if link and link != '#':
        fetched = _fetch_article_sentences(link)

    # Filter fetched sentences that just repeat the title
    title_core = title.lower()[:40]
    genuine = [s for s in fetched if s.lower()[:40] != title_core and len(s) > 30]

    # 2. If we have 3+ real sentences from article, use them
    if len(genuine) >= 3:
        lines = [l[:200].rsplit(' ',1)[0]+'…' if len(l)>200 else l for l in genuine[:3]]
        return lines

    # 3. Try RSS non-title sentences to supplement
    rss = _rss_sentences(summary, title)
    pool = genuine + [s for s in rss if s not in genuine]

    # 4. Generate title-derived lines for all 3 slots (the reliable fallback)
    title_lines = _title_to_lines(title, source, art_category)

    # 5. Blend: real pool sentences first, then title-derived to fill gaps
    lines = []
    for s in pool:
        if len(lines) >= 3:
            break
        s_clean = s[:200].rsplit(' ',1)[0]+'…' if len(s)>200 else s
        if s_clean not in lines:
            lines.append(s_clean)
    for tl in title_lines:
        if len(lines) >= 3:
            break
        if tl not in lines:
            lines.append(tl)

    return lines[:3]

def get_description(art):
    """Plain joined string (legacy use)."""
    return ' '.join(get_description_lines(art))

def parse_date(entry):
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
    if dt_utc is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=NEWS_LOOKBACK_DAYS)
    return dt_utc >= cutoff

def source_name(feed_title, entry):
    title = entry.get('title', '')
    if ' - ' in title:
        return title.rsplit(' - ', 1)[-1].strip()
    return feed_title or 'Unknown'

def clean_title(raw_title):
    if ' - ' in raw_title:
        return raw_title.rsplit(' - ', 1)[0].strip()
    return raw_title.strip()


# ─── Fetch ────────────────────────────────────────────────────────────────────
def fetch_all_articles():
    articles = []
    seen = set()

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            feed_title = feed.feed.get('title', '')
            for entry in feed.entries[:20]:
                raw_title = entry.get('title', '')
                title = clean_title(html.unescape(raw_title))
                if not title or title.lower() in seen:
                    continue
                dt_utc, date_display = parse_date(entry)
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
                    'dt_utc': dt_utc,
                })
        except Exception as e:
            print(f"[WARN] Could not fetch {url}: {e}")
        time.sleep(0.4)

    articles.sort(key=lambda a: a['dt_utc'] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return articles


# ─── Categorise ──────────────────────────────────────────────────────────────
def _which_priority_company(blob):
    """Return a canonical company key if blob mentions a priority company."""
    groups = [
        ('waaree',         ['waaree energies', 'waaree']),
        ('tata power',     ['tata power']),
        ('reliance',       ['reliance industries', 'reliance solar', 'reliance renewable', 'reliance green']),
        ('ntpc green',     ['ntpc green energy', 'ntpc green']),
        ('jsw energy',     ['jsw energy', 'jsw energies', 'jsw solar']),
        ('premier',        ['premier energies']),
        ('borosil',        ['borosil renewables', 'borosil']),
        ('saatvik',        ['saatvik solar', 'saatvik']),
        ('utl',            ['utl solar', 'utl']),
        ('fujiyama',       ['fujiyama solar', 'fujiyama']),
        ('exide',          ['exide industries', 'exide']),
        ('amara raja',     ['amara raja batteries', 'amara raja', 'amaraja']),
    ]
    for key, variants in groups:
        if any(v in blob for v in variants):
            return key
    return None

def categorise(articles):
    priority_stock = []   # priority companies — always top of stock section
    other_stock    = []   # other solar companies with stock signals
    industry_news  = []

    for art in articles:
        blob = (art['title'] + ' ' + art['summary']).lower()

        # ── Skip pure analyst/brokerage opinion pieces ──────────────────────
        analyst_hits = sum(1 for kw in ANALYST_FILTER_KEYWORDS if kw in blob)
        # 1 strong hit (upside target, stock to buy, etc.) or 2+ general hits → filter
        strong_analyst = any(kw in blob for kw in [
            'stock to buy', 'stocks to buy', '% upside', 'upside target',
            'multibagger', 'stock recommendation', 'should you buy',
            'price target', 'initiates coverage',
        ])
        if strong_analyst or analyst_hits >= 2:
            real_news = any(kw in blob for kw in HIGH_IMPORTANCE_KEYWORDS)
            if not real_news:
                continue

        # Must be relevant to solar/renewable
        if not any(kw in blob for kw in RELEVANCE_KEYWORDS):
            # Exception: priority company articles are always included
            if not any(kw in blob for kw in PRIORITY_COMPANIES):
                continue

        is_priority    = any(kw in blob for kw in PRIORITY_COMPANIES)
        stock_score    = sum(1 for kw in STOCK_KEYWORDS    if kw in blob)
        industry_score = sum(1 for kw in INDUSTRY_KEYWORDS if kw in blob)

        # Regulatory / policy articles always go to industry regardless of stock score
        is_regulatory = any(kw in blob for kw in [
            'cerc', 'serc', 'mnre', 'ministry', 'policy', 'regulation',
            'regulatory', 'amendment', 'notification', 'circular',
            'directive', 'tribunal', 'pli scheme', 'pli solar',
            'tariff order', 'discom', 'rpo', 'net metering',
        ])

        if is_priority and not is_regulatory:
            priority_stock.append(art)
        elif is_regulatory:
            industry_news.append(art)
        elif stock_score >= industry_score and stock_score > 0:
            other_stock.append(art)
        elif industry_score > 0:
            industry_news.append(art)
        else:
            industry_news.append(art)

    # Deduplicate across buckets (priority takes precedence)
    seen_titles = set()
    def dedup(lst):
        out = []
        for a in lst:
            k = a['title'].lower()
            if k not in seen_titles:
                seen_titles.add(k)
                out.append(a)
        return out

    priority_stock = dedup(priority_stock)
    other_stock    = dedup(other_stock)
    industry_news  = dedup(industry_news)

    # ── 1 article per priority company; allow 2nd only if high-importance ────
    company_count  = {}   # company_key → how many articles included so far
    filtered_priority = []
    for art in priority_stock:
        blob = (art['title'] + ' ' + art['summary']).lower()
        co   = _which_priority_company(blob) or 'other'
        count = company_count.get(co, 0)
        is_important = any(kw in blob for kw in HIGH_IMPORTANCE_KEYWORDS)
        if count == 0:
            filtered_priority.append(art)
            company_count[co] = 1
        elif count == 1 and is_important:
            # Allow one extra article if it's high-importance
            filtered_priority.append(art)
            company_count[co] = 2
        # else: skip — already have enough for this company

    stock_news = filtered_priority[:5]

    return stock_news, industry_news[:10]


# ─── Sentiment & Tag helpers ──────────────────────────────────────────────────
_POS_KW = ['signs','wins','raises','adds','launches','growth','surge','expands',
           'approves','awards','secures','record','milestone','commissions',
           'advances','completes','achieves','boost','strengthens','accelerates']
_NEG_KW = ['falls','declines','risk','curtailment','loss','rejected','cuts',
           'delays','concern','warning','penalty','slumps','drops','weakens']

TAG_MAP = [
    # Priority companies first
    ('waaree',           'Waaree Energies'),
    ('tata power',       'Tata Power'),
    ('reliance',         'Reliance'),
    ('ntpc green',       'NTPC Green Energy'),
    ('jsw energy',       'JSW Energy'),
    ('jsw energies',     'JSW Energy'),
    ('premier energies', 'Premier Energies'),
    ('borosil',          'Borosil Renewables'),
    ('saatvik',          'Saatvik Solar'),
    ('utl solar',        'UTL Solar'),
    ('fujiyama',         'Fujiyama Solar'),
    ('exide industries', 'Exide Industries'),
    ('exide',            'Exide Industries'),
    ('amara raja',       'Amara Raja Batteries'),
    # Other companies
    ('adani green',      'Adani Green'),
    ('suzlon',           'Suzlon'),
    ('inox wind',        'INOX Wind'),
    ('ireda',            'IREDA'),
    # Market terms
    ('ipo',              'IPO'),
    ('nse',              'NSE'),
    ('bse',              'BSE'),
    ('sebi',             'SEBI'),
    # Sector
    ('bess',             'BESS'),
    ('battery',          'Battery Storage'),
    ('energy storage',   'Storage'),
    ('green hydrogen',   'Green Hydrogen'),
    ('mnre',             'MNRE'),
    ('seci',             'SECI'),
    ('cerc',             'CERC'),
    ('transmission',     'Transmission'),
    ('rooftop',          'Rooftop Solar'),
    ('floating',         'Floating Solar'),
    ('rpo',              'RPO'),
    ('rec',              'REC'),
    ('epc',              'EPC'),
    ('ppa',              'PPA'),
    ('rajasthan',        'Rajasthan'),
    ('gujarat',          'Gujarat'),
    ('maharashtra',      'Maharashtra'),
    ('offshore',         'Offshore Wind'),
    ('hydrogen',         'Hydrogen'),
    ('solar',            'Solar'),
    ('wind',             'Wind'),
]

SIGNAL_DEFS = [
    ('chip-green',  '&#9650; Solar EPC &amp; Developer',  ['epc','solar developer','ppa','mskvy','developer']),
    ('chip-green',  '&#9650; BESS / Storage',             ['bess','battery storage','energy storage','mwh']),
    ('chip-green',  '&#9650; RE Financing',               ['raises','fundraise','investment','crore','million','billion']),
    ('chip-blue',   '&#9675; Policy &amp; Regulation',    ['policy','mnre','cerc','regulation','amendment','rpo','ministry']),
    ('chip-blue',   '&#9675; IPO / Stock Market',         ['ipo','listing','nse','bse','sebi','share price']),
    ('chip-orange', '&#9678; Rooftop / PM Surya Ghar',    ['rooftop','pm surya ghar','pm kusum','distributed']),
    ('chip-orange', '&#9678; Green Hydrogen',             ['green hydrogen','electrolyser']),
    ('chip-red',    '&#9660; Transmission / Grid Risk',   ['curtailment','transmission risk','evacuation gap','tgna']),
]

def get_sentiment(art):
    blob = (art['title'] + ' ' + art['summary']).lower()
    pos = sum(1 for k in _POS_KW if k in blob)
    neg = sum(1 for k in _NEG_KW if k in blob)
    if neg > pos:
        return 'neg', '&#10006; Negative'
    return 'pos', '&#10004; Positive'

def get_tags(art):
    blob = (art['title'] + ' ' + art['summary']).lower()
    seen, tags = set(), []
    for kw, label in TAG_MAP:
        if kw in blob and label not in seen:
            seen.add(label)
            tags.append(label)
        if len(tags) == 5:
            break
    return tags

def build_signals(all_articles):
    blob = ' '.join((a['title'] + ' ' + a['summary']).lower() for a in all_articles)
    chips = []
    for cls, label, kws in SIGNAL_DEFS:
        if any(k in blob for k in kws):
            chips.append(f'<span class="chip {cls}">{label}</span>')
    return '\n    '.join(chips) if chips else '<span class="chip chip-blue">&#9675; India RE Market</span>'

def build_exec_summary(stock_news, industry_news):
    picks = (stock_news[:2] + industry_news[:2])[:4]
    items = []
    for art in picks:
        icon  = '📈' if art in stock_news else '🏭'
        title_esc = html.escape(art['title'][:85]) + ('…' if len(art['title']) > 85 else '')
        body_esc  = html.escape(art['summary'][:230]) + ('…' if len(art['summary']) > 230 else '')
        items.append(
            f'      <div class="exec-item"><strong>{icon} {title_esc}</strong>{body_esc}</div>'
        )
    return '\n'.join(items)


# ─── Card builder ─────────────────────────────────────────────────────────────
def _card_html(art, num, art_category='industry'):
    sent_cls, sent_label = get_sentiment(art)
    tags      = get_tags(art)
    tag_html  = ''.join(f'<span class="tag">{html.escape(t)}</span>' for t in tags)
    num_str   = str(num).zfill(2)
    desc_lines = get_description_lines(art, art_category)
    return (
        f'\n    <div class="card">'
        f'\n      <div class="card-top">'
        f'\n        <span class="card-num">{num_str}</span>'
        f'\n        <div class="card-headline">{html.escape(art["title"])}</div>'
        f'\n      </div>'
        f'\n      <div class="card-meta">'
        f'\n        <span class="pill pill-src">{html.escape(art["source"])}</span>'
        f'\n        <span class="pill pill-date">{html.escape(art["date"])}</span>'
        f'\n        <span class="pill pill-{sent_cls}">{sent_label}</span>'
        f'\n      </div>'
        f'\n      <div class="card-body">'
        + ''.join(f'<p>{html.escape(ln)}</p>' for ln in desc_lines)
        + f'</div>'
        f'\n      <a class="orig-link" href="{art["link"]}" target="_blank" rel="noopener noreferrer">&#128279; Read Original Article</a>'
        f'\n      <div class="tags">{tag_html}</div>'
        f'\n    </div>'
    )

def build_cards(articles, section, start_num=1):
    if not articles:
        return '<p class="no-news">No news found for this category today.</p>'
    cat = 'stock' if section == 'stock' else 'industry'
    parts = []
    for i, art in enumerate(articles):
        parts.append(_card_html(art, start_num + i, cat))
        if i < len(articles) - 1:
            parts.append('\n    <hr class="divider">')
    return ''.join(parts)


# ─── HTML Report ──────────────────────────────────────────────────────────────
def generate_html(stock_news, industry_news):
    now_ist          = datetime.now(IST)
    date_display     = now_ist.strftime('%A, %d %B %Y')
    date_upper       = date_display.upper()
    time_display     = now_ist.strftime('%I:%M %p IST')
    lookback_display = f"Last {NEWS_LOOKBACK_DAYS} Days"
    total            = len(stock_news) + len(industry_news)

    stock_cards    = build_cards(stock_news,    'stock',    start_num=1)
    industry_cards = build_cards(industry_news, 'industry', start_num=len(stock_news) + 1)
    exec_summary   = build_exec_summary(stock_news, industry_news)
    signals_html   = build_signals(stock_news + industry_news)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily News Updates — Solar &amp; Renewable Energy India | {date_display}</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
  :root {{
    --em-yellow:    #FFDD00;
    --em-yellow-lt: #FFF9CC;
    --em-yellow-dk: #F5C800;
    --em-blue:      #243B7F;
    --em-blue-mid:  #1A3070;
    --em-blue-dk:   #152560;
    --em-orange:    #EA7437;
    --em-orange-dk: #DA7527;
    --em-white:     #FFFFFF;
    --em-off-white: #FAFAFA;
    --em-light:     #F3F3F3;
    --em-border:    #E2E2E2;
    --em-text-dk:   #1A1A2E;
    --em-text-mid:  #3A4A6B;
    --em-text-lt:   #6B7A9B;
    --em-green:     #1B7A45;
    --em-green-bg:  #E8F5EE;
    --em-red:       #B22222;
    --em-red-bg:    #FAEAEA;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Montserrat', sans-serif;
    font-size: 10pt;
    background: #E8E8E8;
    color: var(--em-text-dk);
    line-height: 1.55;
    padding: 24px 20px;
  }}
  .page {{ max-width: 980px; margin: 0 auto; }}

  /* ── HEADER ── */
  .header {{ border-radius: 10px 10px 0 0; overflow: hidden; }}
  .header-top {{
    background: var(--em-blue);
    padding: 18px 32px;
    display: flex; align-items: center; justify-content: space-between;
  }}
  .brand-name {{ font-size: 24pt; font-weight: 900; font-style: italic; color: var(--em-yellow); letter-spacing: -0.5px; line-height: 1; }}
  .brand-sub  {{ font-size: 8.5pt; font-weight: 600; color: rgba(255,255,255,0.55); letter-spacing: 2px; text-transform: uppercase; margin-top: 3px; }}
  .header-meta   {{ text-align: right; }}
  .meta-date     {{ color: var(--em-yellow); font-size: 9pt; font-weight: 700; letter-spacing: 1px; }}
  .meta-edition  {{ color: rgba(255,255,255,0.45); font-size: 8pt; margin-top: 3px; }}
  .header-yellow {{
    background: var(--em-yellow);
    padding: 12px 32px;
    display: flex; align-items: center; justify-content: space-between;
  }}
  .hy-tagline  {{ font-size: 10.5pt; font-weight: 800; color: var(--em-blue); letter-spacing: 0.2px; }}
  .hy-tagline em {{ color: var(--em-orange-dk); font-style: normal; }}
  .hy-coverage {{ font-size: 8pt; font-weight: 600; color: var(--em-blue-mid); opacity: 0.75; }}

  /* ── EXEC SUMMARY ── */
  .exec-wrap {{
    background: var(--em-blue);
    padding: 20px 32px;
    border-left: 5px solid var(--em-yellow);
    border-right: 5px solid var(--em-yellow);
  }}
  .exec-label {{ font-size: 7.5pt; font-weight: 800; color: var(--em-yellow); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 12px; }}
  .exec-grid  {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .exec-item  {{
    background: rgba(255,221,0,0.07);
    border: 1px solid rgba(255,221,0,0.2);
    border-left: 4px solid var(--em-yellow);
    border-radius: 6px;
    padding: 11px 14px;
    color: rgba(255,255,255,0.88);
    font-size: 9pt; line-height: 1.5;
  }}
  .exec-item strong {{ display: block; color: var(--em-yellow); font-size: 8.5pt; font-weight: 800; text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 4px; }}

  /* ── SIGNALS BAR ── */
  .signals {{
    background: var(--em-yellow);
    padding: 10px 32px;
    display: flex; align-items: center; gap: 9px; flex-wrap: wrap;
    border-left: 5px solid var(--em-yellow);
    border-right: 5px solid var(--em-yellow);
    border-bottom: 3px solid var(--em-blue);
  }}
  .sig-label {{ font-size: 7.5pt; font-weight: 800; color: var(--em-blue); text-transform: uppercase; letter-spacing: 1px; white-space: nowrap; margin-right: 4px; }}
  .chip {{ display: inline-flex; align-items: center; gap: 4px; font-size: 7.5pt; font-weight: 700; padding: 3px 10px; border-radius: 20px; letter-spacing: 0.2px; }}
  .chip-blue   {{ background: var(--em-blue);      color: var(--em-yellow); }}
  .chip-orange {{ background: var(--em-orange-dk); color: #fff; }}
  .chip-green  {{ background: var(--em-green);     color: #fff; }}
  .chip-red    {{ background: var(--em-red);       color: #fff; }}

  /* ── SECTION ── */
  .section {{ margin-top: 18px; }}
  .section-hdr {{
    background: var(--em-blue);
    padding: 11px 32px;
    border-radius: 8px 8px 0 0;
    display: flex; align-items: center; gap: 10px;
  }}
  .section-icon  {{ font-size: 14pt; }}
  .section-title {{ font-size: 12pt; font-weight: 800; color: var(--em-yellow); font-style: italic; }}
  .section-count {{ margin-left: auto; background: var(--em-yellow); color: var(--em-blue); font-size: 7.5pt; font-weight: 800; padding: 2px 9px; border-radius: 12px; letter-spacing: 0.5px; }}

  /* ── CARD ── */
  .card {{
    background: var(--em-white);
    border-left: 5px solid var(--em-yellow);
    border-right: 1px solid var(--em-border);
    border-bottom: 1px solid var(--em-border);
    padding: 16px 28px;
  }}
  .card:nth-child(even) {{ background: var(--em-off-white); }}
  .card:last-child {{ border-radius: 0 0 8px 8px; }}
  .card-top      {{ display: flex; align-items: flex-start; gap: 11px; margin-bottom: 8px; }}
  .card-num      {{ font-size: 7.5pt; font-weight: 800; color: var(--em-white); background: var(--em-blue); border-radius: 4px; padding: 3px 8px; white-space: nowrap; flex-shrink: 0; margin-top: 2px; letter-spacing: 0.5px; }}
  .card-headline {{ font-size: 10.5pt; font-weight: 700; color: var(--em-blue); line-height: 1.4; }}

  .card-meta {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }}
  .pill      {{ display: inline-flex; align-items: center; font-size: 7.5pt; font-weight: 600; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.2px; }}
  .pill-src  {{ background: var(--em-blue);     color: var(--em-yellow); }}
  .pill-date {{ background: var(--em-yellow);   color: var(--em-blue); }}
  .pill-pos  {{ background: var(--em-green-bg); color: var(--em-green); border: 1px solid #8ED4AE; font-weight: 700; }}
  .pill-neg  {{ background: var(--em-red-bg);   color: var(--em-red);   border: 1px solid #ECA9A9; font-weight: 700; }}

  .card-body   {{ font-size: 9.5pt; color: var(--em-text-mid); line-height: 1.65; margin-bottom: 12px; font-weight: 400; }}
  .card-body p + p {{ margin-top: 7px; }}

  .orig-link {{
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 8.5pt; font-weight: 700;
    color: var(--em-blue); text-decoration: none;
    background: var(--em-yellow); border: 2px solid var(--em-blue);
    padding: 5px 13px; border-radius: 4px; margin-bottom: 10px;
  }}
  .orig-link:hover {{ background: var(--em-yellow-lt); }}

  .tags {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 4px; }}
  .tag  {{ font-size: 7pt; font-weight: 700; padding: 2px 8px; border-radius: 3px; background: rgba(36,59,127,0.07); color: var(--em-blue); border: 1px solid rgba(36,59,127,0.18); text-transform: uppercase; letter-spacing: 0.4px; }}

  .divider {{ border: none; border-top: 2px dashed var(--em-yellow); margin: 0; }}
  .no-news {{ padding: 32px; text-align: center; color: var(--em-text-lt); font-style: italic; background: var(--em-white); border-left: 5px solid var(--em-yellow); border-right: 1px solid var(--em-border); border-bottom: 1px solid var(--em-border); border-radius: 0 0 8px 8px; }}

  /* ── FOOTER ── */
  .footer {{
    margin-top: 18px;
    background: var(--em-blue);
    border-radius: 8px;
    padding: 13px 32px;
    display: flex; align-items: center; justify-content: space-between;
  }}
  .footer-l {{ color: var(--em-yellow); font-size: 8.5pt; font-weight: 700; letter-spacing: 0.3px; display: flex; align-items: center; gap: 8px; }}
  .footer-dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--em-yellow); flex-shrink: 0; }}
  .footer-r {{ color: rgba(255,255,255,0.45); font-size: 8pt; }}

  @media print {{ body {{ background: #fff; padding: 0; }} .page {{ max-width: 100%; }} }}
  @media (max-width: 620px) {{
    .exec-grid {{ grid-template-columns: 1fr; }}
    .header-top, .header-yellow {{ flex-direction: column; gap: 8px; text-align: center; }}
    .footer {{ flex-direction: column; gap: 6px; text-align: center; }}
    .card {{ padding: 14px 16px; }}
  }}
</style>
</head>
<body>
<div class="page">

  <!-- HEADER -->
  <div class="header">
    <div class="header-top">
      <div>
        <div class="brand-name">Daily News Updates</div>
        <div class="brand-sub">Solar &amp; Renewable Energy &nbsp;&#183;&nbsp; India</div>
      </div>
      <div class="header-meta">
        <div class="meta-date">{date_upper}</div>
        <div class="meta-edition">Daily News Intelligence &nbsp;&#183;&nbsp; Coverage: {lookback_display}</div>
      </div>
    </div>
    <div class="header-yellow">
      <div class="hy-tagline">Solar &amp; Renewable Energy India &nbsp;|&nbsp; <em>Daily Market Intelligence</em></div>
      <div class="hy-coverage">IPO / Stock Market &nbsp;&#183;&nbsp; Industry &nbsp;&#183;&nbsp; Policy &amp; Regulation &nbsp;&#183;&nbsp; Energy Storage</div>
    </div>
  </div>

  <!-- EXEC SUMMARY -->
  <div class="exec-wrap">
    <div class="exec-label">&#9728; &nbsp;Executive Summary — Top Stories Today &nbsp;({total} articles)</div>
    <div class="exec-grid">
{exec_summary}
    </div>
  </div>

  <!-- SIGNALS BAR -->
  <div class="signals">
    <span class="sig-label">Market Signals</span>
    {signals_html}
  </div>

  <!-- SECTION 1: IPO / STOCK -->
  <div class="section">
    <div class="section-hdr">
      <span class="section-icon">📈</span>
      <span class="section-title">Section 1 — IPO / Stock Market</span>
      <span class="section-count">{len(stock_news)} STORIES</span>
    </div>
    {stock_cards}
  </div>

  <!-- SECTION 2: INDUSTRY -->
  <div class="section">
    <div class="section-hdr">
      <span class="section-icon">🏭</span>
      <span class="section-title">Section 2 — Industry</span>
      <span class="section-count">{len(industry_news)} STORIES</span>
    </div>
    {industry_cards}
  </div>

  <!-- FOOTER -->
  <div class="footer">
    <div class="footer-l">
      <div class="footer-dot"></div>
      Solar &amp; Renewable Energy India &nbsp;&#183;&nbsp; Daily News Intelligence &nbsp;&#183;&nbsp; {date_display}
    </div>
    <div class="footer-r">Generated {time_display} &nbsp;&#183;&nbsp; Sources: Google News, Mercom India, PV Magazine &amp; others</div>
  </div>

</div>
</body>
</html>"""


# ─── Email-safe HTML (inline styles, table layout, no CSS vars) ───────────────
def _email_section_header(icon, title, count):
    return f"""
  <tr>
    <td style="background:#243B7F;padding:11px 24px;border-radius:8px 8px 0 0;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
        <td style="font-family:Arial,sans-serif;font-size:13pt;font-weight:900;color:#FFDD00;font-style:italic;">{icon} {title}</td>
        <td align="right"><span style="background:#FFDD00;color:#243B7F;font-family:Arial,sans-serif;font-size:7.5pt;font-weight:800;padding:2px 9px;border-radius:12px;">{count} STORIES</span></td>
      </tr></table>
    </td>
  </tr>"""

def _email_card(art, num, is_even, art_category='industry'):
    sent_cls, sent_label = get_sentiment(art)
    tags   = get_tags(art)
    bg     = '#FAFAFA' if is_even else '#FFFFFF'
    sent_style = (
        'background:#E8F5EE;color:#1B7A45;border:1px solid #8ED4AE;'
        if sent_cls == 'pos' else
        'background:#FAEAEA;color:#B22222;border:1px solid #ECA9A9;'
    )
    tag_html = ''.join(
        f'<span style="font-family:Arial,sans-serif;font-size:7pt;font-weight:700;'
        f'padding:2px 7px;border-radius:3px;background:rgba(36,59,127,0.07);'
        f'color:#243B7F;border:1px solid rgba(36,59,127,0.18);'
        f'text-transform:uppercase;letter-spacing:0.4px;margin-right:4px;">'
        f'{html.escape(t)}</span>'
        for t in tags
    )
    num_str   = str(num).zfill(2)
    desc_html = ''.join(
        f'<p style="font-family:Arial,sans-serif;font-size:9.5pt;color:#3A4A6B;'
        f'line-height:1.7;margin:0 0 6px 36px;">{html.escape(ln)}</p>'
        for ln in get_description_lines(art, art_category)
    )
    return f"""
  <tr>
    <td style="background:{bg};border-left:5px solid #FFDD00;border-right:1px solid #E2E2E2;border-bottom:1px solid #E2E2E2;padding:16px 24px;">
      <!-- number + headline -->
      <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
        <td valign="top" style="width:36px;">
          <span style="font-family:Arial,sans-serif;font-size:7.5pt;font-weight:800;color:#FFFFFF;background:#243B7F;border-radius:4px;padding:3px 7px;">{num_str}</span>
        </td>
        <td valign="top" style="font-family:Arial,sans-serif;font-size:10.5pt;font-weight:700;color:#243B7F;line-height:1.4;">{html.escape(art['title'])}</td>
      </tr></table>
      <!-- pills -->
      <p style="margin:10px 0 10px 36px;">
        <span style="font-family:Arial,sans-serif;font-size:7.5pt;font-weight:600;padding:2px 8px;border-radius:4px;background:#243B7F;color:#FFDD00;margin-right:5px;">{html.escape(art['source'])}</span>
        <span style="font-family:Arial,sans-serif;font-size:7.5pt;font-weight:600;padding:2px 8px;border-radius:4px;background:#FFDD00;color:#243B7F;margin-right:5px;">{html.escape(art['date'])}</span>
        <span style="font-family:Arial,sans-serif;font-size:7.5pt;font-weight:700;padding:2px 8px;border-radius:4px;{sent_style}">{sent_label}</span>
      </p>
      <!-- 3-line description -->
      {desc_html}
      <!-- link button -->
      <p style="margin:0 0 10px 36px;">
        <a href="{art['link']}" target="_blank" style="font-family:Arial,sans-serif;font-size:8.5pt;font-weight:700;color:#243B7F;text-decoration:none;background:#FFDD00;border:2px solid #243B7F;padding:5px 13px;border-radius:4px;">&#128279; Read Original Article</a>
      </p>
      <!-- tags -->
      <p style="margin:4px 0 0 36px;">{tag_html}</p>
    </td>
  </tr>
  <tr><td style="border-left:5px solid #FFDD00;border-right:1px solid #E2E2E2;padding:0;"><hr style="border:none;border-top:2px dashed #FFDD00;margin:0;"></td></tr>"""

def _email_cards(articles, start_num, art_category='industry'):
    if not articles:
        return f'<tr><td style="padding:24px;text-align:center;font-family:Arial,sans-serif;font-style:italic;color:#6B7A9B;background:#fff;border-left:5px solid #FFDD00;border-right:1px solid #E2E2E2;">No news found for this category today.</td></tr>'
    return ''.join(_email_card(a, start_num + i, i % 2 == 1, art_category) for i, a in enumerate(articles))

def generate_email_html(stock_news, industry_news):
    """Email-safe HTML: inline styles, table layout, web-safe fonts."""
    now_ist      = datetime.now(IST)
    date_display = now_ist.strftime('%A, %d %B %Y')
    date_upper   = date_display.upper()
    time_display = now_ist.strftime('%I:%M %p IST')
    total        = len(stock_news) + len(industry_news)
    web_url      = 'https://kalpeshvjtigawali-sys.github.io/Daily-News-Report/reports/latest.html'

    # Exec summary (top 4)
    picks = (stock_news[:2] + industry_news[:2])[:4]
    exec_cells = ''
    for i, art in enumerate(picks):
        icon = '📈' if art in stock_news else '🏭'
        t    = html.escape(art['title'][:80]) + ('…' if len(art['title']) > 80 else '')
        b    = html.escape(art['summary'][:200]) + ('…' if len(art['summary']) > 200 else '')
        td_style = 'width:50%;vertical-align:top;padding:11px 14px;background:rgba(255,221,0,0.07);border:1px solid rgba(255,221,0,0.2);border-left:4px solid #FFDD00;border-radius:6px;'
        exec_cells += f'<td style="{td_style}"><p style="font-family:Arial,sans-serif;font-size:8.5pt;font-weight:800;color:#FFDD00;text-transform:uppercase;letter-spacing:0.3px;margin:0 0 4px;">{icon} {t}</p><p style="font-family:Arial,sans-serif;font-size:9pt;color:rgba(255,255,255,0.88);line-height:1.5;margin:0;">{b}</p></td>'
        if i == 1:
            exec_cells += '</tr><tr>'

    stock_rows    = _email_cards(stock_news,    start_num=1,                    art_category='stock')
    industry_rows = _email_cards(industry_news, start_num=len(stock_news) + 1, art_category='industry')
    sec1_hdr = _email_section_header('📈', 'Section 1 — IPO / Stock Market', len(stock_news))
    sec2_hdr = _email_section_header('🏭', 'Section 2 — Industry',           len(industry_news))

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Daily News Updates — Solar &amp; Renewable Energy India | {date_display}</title>
</head>
<body style="margin:0;padding:20px;background:#E8E8E8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:680px;margin:0 auto;">

  <!-- HEADER -->
  <tr><td style="background:#243B7F;padding:18px 28px;border-radius:10px 10px 0 0;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td><p style="font-family:Arial,sans-serif;font-size:22pt;font-weight:900;font-style:italic;color:#FFDD00;margin:0;line-height:1;">Daily News Updates</p>
          <p style="font-family:Arial,sans-serif;font-size:8pt;font-weight:600;color:rgba(255,255,255,0.55);letter-spacing:2px;text-transform:uppercase;margin:3px 0 0;">Solar &amp; Renewable Energy &nbsp;·&nbsp; India</p></td>
      <td align="right" valign="middle">
          <p style="font-family:Arial,sans-serif;font-size:8.5pt;font-weight:700;color:#FFDD00;letter-spacing:1px;margin:0;">{date_upper}</p>
          <p style="font-family:Arial,sans-serif;font-size:7.5pt;color:rgba(255,255,255,0.45);margin:3px 0 0;">Last {NEWS_LOOKBACK_DAYS} Days &nbsp;·&nbsp; {total} Articles</p>
      </td>
    </tr></table>
  </td></tr>

  <!-- YELLOW BAR -->
  <tr><td style="background:#FFDD00;padding:11px 28px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="font-family:Arial,sans-serif;font-size:10pt;font-weight:800;color:#243B7F;">Solar &amp; Renewable Energy India &nbsp;|&nbsp; <span style="color:#DA7527;">Daily Market Intelligence</span></td>
      <td align="right" style="font-family:Arial,sans-serif;font-size:7.5pt;font-weight:600;color:#1A3070;opacity:0.75;">IPO &nbsp;·&nbsp; Industry &nbsp;·&nbsp; Policy &nbsp;·&nbsp; Storage</td>
    </tr></table>
  </td></tr>

  <!-- EXEC SUMMARY -->
  <tr><td style="background:#243B7F;padding:18px 28px;border-left:5px solid #FFDD00;border-right:5px solid #FFDD00;">
    <p style="font-family:Arial,sans-serif;font-size:7.5pt;font-weight:800;color:#FFDD00;letter-spacing:2px;text-transform:uppercase;margin:0 0 12px;">&#9728; &nbsp;Executive Summary — Top Stories Today</p>
    <table width="100%" cellpadding="6" cellspacing="6" border="0"><tr>{exec_cells}</tr></table>
  </td></tr>

  <!-- VIEW FULL REPORT BUTTON -->
  <tr><td style="background:#FFDD00;padding:12px 28px;border-left:5px solid #FFDD00;border-right:5px solid #FFDD00;border-bottom:3px solid #243B7F;text-align:center;">
    <a href="{web_url}" target="_blank" style="font-family:Arial,sans-serif;font-size:9pt;font-weight:800;color:#FFFFFF;text-decoration:none;background:#243B7F;border:2px solid #243B7F;padding:8px 22px;border-radius:5px;">&#128279; View Full Formatted Report Online</a>
  </td></tr>

  <!-- SECTION 1 -->
  <tr><td style="padding-top:18px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      {sec1_hdr}
      {stock_rows}
    </table>
  </td></tr>

  <!-- SECTION 2 -->
  <tr><td style="padding-top:18px;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      {sec2_hdr}
      {industry_rows}
    </table>
  </td></tr>

  <!-- FOOTER -->
  <tr><td style="background:#243B7F;padding:12px 28px;border-radius:8px;margin-top:18px;display:block;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="font-family:Arial,sans-serif;font-size:8pt;font-weight:700;color:#FFDD00;">&#9679; Solar &amp; Renewable Energy India &nbsp;·&nbsp; Daily Intelligence &nbsp;·&nbsp; {date_display}</td>
      <td align="right" style="font-family:Arial,sans-serif;font-size:7.5pt;color:rgba(255,255,255,0.45);">Generated {time_display}</td>
    </tr></table>
  </td></tr>

</table>
</body>
</html>"""


# ─── Index Page ───────────────────────────────────────────────────────────────
def update_index(report_files):
    rows = ''
    for f in sorted(report_files, reverse=True):
        slug = os.path.basename(f).replace('report_', '').replace('.html', '')
        try:
            dt = datetime.strptime(slug, '%Y-%m-%d').strftime('%A, %d %B %Y')
        except Exception:
            dt = slug
        rows += f'<tr><td><a href="{os.path.basename(f)}">{dt}</a></td><td><a href="{os.path.basename(f)}">View Report &#8599;</a></td></tr>\n'

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Daily Solar &amp; Renewable Energy Reports</title>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    body{{font-family:'Montserrat',sans-serif;background:#E8E8E8;color:#1A1A2E;margin:0;padding:24px 20px}}
    .page{{max-width:720px;margin:0 auto}}
    header{{background:#243B7F;color:#fff;padding:24px 32px;border-radius:10px 10px 0 0;display:flex;align-items:center;justify-content:space-between}}
    header h1{{font-size:16pt;font-weight:800;font-style:italic;color:#FFDD00}}
    header p{{font-size:8pt;color:rgba(255,255,255,0.5);margin-top:3px;letter-spacing:1px;text-transform:uppercase}}
    table{{width:100%;border-collapse:collapse;background:#fff}}
    th{{background:#243B7F;color:#FFDD00;padding:11px 18px;text-align:left;font-size:8pt;letter-spacing:1px;text-transform:uppercase}}
    td{{padding:13px 18px;border-bottom:1px solid #E2E2E2;font-size:9.5pt;border-left:5px solid #FFDD00}}
    tr:last-child td{{border-bottom:none;border-radius:0 0 8px 8px}}
    tr:hover td{{background:#FFFDE0}}
    a{{color:#243B7F;font-weight:700;text-decoration:none}}
    a:hover{{text-decoration:underline}}
    .empty{{text-align:center;padding:32px;color:#6B7A9B;font-style:italic}}
  </style>
</head>
<body>
<div class="page">
<header>
  <div><div style="font-size:18pt;font-weight:900;font-style:italic;color:#FFDD00">Daily News Updates</div><div style="font-size:8pt;color:rgba(255,255,255,0.5);margin-top:3px;letter-spacing:2px;text-transform:uppercase">Solar &amp; Renewable Energy India</div></div>
  <div style="text-align:right"><div style="color:#FFDD00;font-size:9pt;font-weight:700">REPORT ARCHIVE</div></div>
</header>
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


# ─── Main ─────────────────────────────────────────────────────────────────────
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
    now_ist      = datetime.now(IST)
    date_slug    = now_ist.strftime('%Y-%m-%d')
    report_path  = f'reports/report_{date_slug}.html'

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_html)

    with open('reports/latest.html', 'w', encoding='utf-8') as f:
        f.write(report_html)

    # Email-safe version
    email_html = generate_email_html(stock_news, industry_news)
    with open(f'reports/email_{date_slug}.html', 'w', encoding='utf-8') as f:
        f.write(email_html)
    with open('reports/email_latest.html', 'w', encoding='utf-8') as f:
        f.write(email_html)

    all_reports = sorted(
        [p for p in os.listdir('reports') if p.startswith('report_') and p.endswith('.html')]
    )
    update_index([f'reports/{p}' for p in all_reports])

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
