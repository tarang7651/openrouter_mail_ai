# 🤖 OpenRouter AI Mail Assistant — Odoo 19 Module

> Generate AI-powered email templates & subject lines directly inside Odoo's Mail Composer and Email Marketing — powered by **300+ models** via [OpenRouter](https://openrouter.ai).

![Odoo 17](https://img.shields.io/badge/Odoo-19.0-875A7B?logo=odoo)
![License](https://img.shields.io/badge/License-Proprietary-red)
![OpenRouter](https://img.shields.io/badge/Powered%20by-OpenRouter-orange)

---

## ✨ Features

| Feature | Where |
|---|---|
| **AI Email Body Generator** | Mail Composer (Chatter) |
| **AI Email Body Generator** | Email Marketing (`mailing.mailing`) |
| **AI Subject Line Generator** (5 variants, pick best) | Email Marketing |
| **Multi-model selector** — GPT-4o, Claude, Gemini, Llama, Mistral, DeepSeek | All wizards |
| **Tone selector** — Professional, Casual, Formal, Persuasive, Empathetic, Urgent | All wizards |
| **Centralized config** — API key + default model in Settings | Settings |
| **Token usage display** — see how many tokens each generation cost | Result screen |
| **Free model support** — Llama 3.3, Mistral 7B, DeepSeek Chat are free on OpenRouter | All wizards |

---

## 📸 Screenshots

> *(Add your own screenshots here after installing)*

```
Mail Composer → "✨ Generate with AI" button → Wizard → Generated body auto-fills
Email Marketing → "✨ AI Subject Ideas" + "✨ AI Write Email" buttons
Settings → OpenRouter AI section
```

---

## 🚀 Installation

### Requirements
- Odoo **19.0**
- Python `requests` library (pre-installed in most Odoo environments)
- A free [OpenRouter API key](https://openrouter.ai/keys)

### Steps

```bash
# 1. Clone into your Odoo addons path
cd /path/to/odoo/addons
git clone https://github.com/yourname/openrouter_mail_ai.git

# 2. Restart Odoo
sudo systemctl restart odoo

# 3. Update module list
# Settings → Activate Developer Mode → Apps → Update Apps List

# 4. Install the module
# Search for "OpenRouter AI Mail Assistant" → Install
```

---

## ⚙️ Configuration

1. Go to **Settings → OpenRouter AI**
2. Paste your **API Key** from [openrouter.ai/keys](https://openrouter.ai/keys)
3. Choose a **Default AI Model** (Llama 3.3 70B is free and excellent)
4. Set your **App Name** for OpenRouter dashboard tracking
5. Click **Save**

---

## 💡 How to Use

### In Mail Composer (Chatter)
1. Open any record → click **Send message**
2. Click **✨ Generate with AI**
3. Describe the email, pick model & tone → **Generate Email**
4. Review → **✅ Use This Template**

### In Email Marketing
1. Open **Email Marketing → Campaigns → New**
2. Click **✨ AI Subject Ideas** to get 5 subject line options → click **Use** on your favourite
3. Click **✨ AI Write Email** to generate the full body

---

## 🆓 Free Models on OpenRouter

These models are **completely free** to use (no credits needed):

| Model | Best For |
|---|---|
| `meta-llama/llama-3.3-70b-instruct` | Best quality free model — great for emails |
| `meta-llama/llama-3.1-8b-instruct:free` | Fast, lightweight |
| `deepseek/deepseek-chat` | Strong reasoning, free tier |
| `mistralai/mistral-7b-instruct:free` | Reliable, fast |
| `nousresearch/nous-hermes-2-mixtral-8x7b-dpo` | Creative writing |

---

## 🗺️ Roadmap — More AI Features for Email Marketing

Below are **6 additional ideas** you can build on top of this module — all free with OpenRouter:

---

### 1. 🔍 AI Pre-Send Spam Checker
**What:** Before sending a campaign, AI scans the subject + body and flags potential spam triggers (words like "FREE!!!", excessive caps, suspicious link patterns).
**Why it's unique:** No native spam checker exists in Odoo email marketing.
**How to build:** Add a "Check Spam Score" button on `mailing.mailing`. Call OpenRouter with the email content and ask it to rate spam risk 1–10 with specific reasons.

---

### 2. 📊 AI Campaign Performance Narrator
**What:** After a campaign is sent, instead of raw numbers, a button generates a natural-language summary:
> *"Your April newsletter reached 1,240 people. With a 28% open rate (above your 21% average), this was your best campaign this quarter. The subject line 'Don't miss this...' outperformed all previous ones."*
**Why it's unique:** Odoo shows stats but never explains them conversationally.
**How to build:** Extend `mailing.mailing` with a "📝 AI Summary" button. Pass `sent`, `opened`, `clicked`, `bounced` stats + subject to OpenRouter.

---

### 3. 🔁 AI Smart Resend for Non-Openers
**What:** For contacts who didn't open the campaign, AI generates a slightly different version with a new subject line and tweaked opening line — auto-populates a new mailing targeting non-openers.
**Why it's unique:** Odoo has "resend to non-openers" but zero AI rewriting.
**How to build:** Button on sent mailing → pass original email to OpenRouter → ask for a variation → create new `mailing.mailing` record pre-filled.

---

### 4. 🧠 AI Unsubscribe Reason Analyzer
**What:** When contacts unsubscribe with optional feedback, AI clusters and summarizes the feedback monthly into a short report:
> *"This month: 34% said 'too many emails', 28% said 'not relevant', 18% said 'content quality'..."*
**Why it's unique:** Odoo collects unsubscribe reasons but never analyzes them.
**How to build:** Scheduled action that reads `mailing.trace` unsubscribe reasons monthly, sends them to OpenRouter for clustering and summary, stores result in a custom `mailing.unsubscribe.report` model.

---

### 5. 🎉 AI Milestone Email Generator
**What:** Detects customer milestones from Odoo data (1st order, 1-year anniversary, 10th purchase, ₹1L spent) and auto-drafts a warm, personalized celebration email.
**Why it's unique:** Relationship-building at scale — feels human, fully automated.
**How to build:** Scheduled action on `sale.order` → detect milestones → call OpenRouter with customer name + milestone details → create draft mailing or send directly.

---

### 6. 🧪 AI A/B Test Advisor
**What:** After an A/B tested campaign, AI analyzes which variant won and *explains why* with actionable advice for the next campaign.
> *"Variant B's subject was shorter and created curiosity without revealing the offer — this typically increases open rates. For next time, try leading with a question."*
**Why it's unique:** Odoo supports A/B testing but gives zero learning insights.
**How to build:** Hook into `mailing.mailing` after A/B results are in → pass both variants' stats + content to OpenRouter → display insight in a chatter message.

---

## 🤝 Contributing

PRs welcome! Please follow Odoo's module development guidelines.

```bash
git checkout -b feature/your-feature-name
# make your changes
git commit -m "feat: describe your feature"
git push origin feature/your-feature-name
```

---

## 📄 License

Proprietary license. No distribution, resale, sublicensing, or public redistribution is permitted without explicit written permission from the copyright owner.

## © Copyright

Copyright (c) Tarang Kushwaha. All rights reserved.

---

## 🙏 Credits

Built with ❤️ using [OpenRouter](https://openrouter.ai) — the unified API for 300+ AI models.
# openrouter_mail_ai
