# ☀️ Daily Solar & Renewable Energy News Report — India

Automated daily news tracker for the **Solar & Renewable Energy** sector in India.
Every morning at **9:00 AM IST** a fresh HTML report is generated and published automatically.

---

## 📋 Report Sections

| Section | Coverage |
|---------|----------|
| **Section 1 — IPO & Stock News** | IPOs, share prices, NSE/BSE listings, investor news, quarterly results, analyst ratings for companies like Adani Green, Tata Power, Suzlon, Waaree, etc. |
| **Section 2 — Industry News** | Project tenders, capacity additions (MW/GW), MNRE policy, solar parks, wind farms, green hydrogen, SECI auctions, rooftop solar, battery storage |

---

## 🌐 View Reports

👉 **[Open Latest Report](https://YOUR-USERNAME.github.io/Daily-News-Report/reports/latest.html)**
👉 **[Browse Archive](https://YOUR-USERNAME.github.io/Daily-News-Report/reports/index.html)**

---

## ⚙️ How It Works

```
GitHub Actions (daily 9 AM IST)
        │
        ▼
scripts/generate_report.py
        │  fetches RSS from Google News, Mercom India, PV Magazine India…
        │  categorises → IPO/Stock  or  Industry
        │  generates HTML report
        ▼
reports/report_YYYY-MM-DD.html   ← saved & committed
reports/latest.html              ← always the most recent
reports/index.html               ← archive listing
        │
        ▼
GitHub Pages (public URL)
```

## 🔄 Manual Trigger

Go to **Actions → Generate Daily News Report → Run workflow** to generate a report on demand.

---

*News is sourced from public RSS feeds. This report is for informational purposes only and does not constitute financial advice.*
