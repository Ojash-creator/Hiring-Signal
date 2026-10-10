# Hiring Signal

**See which companies are quietly ramping up hiring for a role or skill, and what changed since you last checked.**

Job boards show you a snapshot. Hiring Signal turns repeated snapshots into a trend: new postings, postings that
disappeared (filled or pulled), and posting volume over time. It runs as a small web app on your own machine.

Built for the **SerpApi India Hackathon 2026**.

## How it uses SerpApi

SerpApi's [Google Jobs API](https://serpapi.com/google-jobs-api) is the data source. Without live search results there
is nothing to compare, so the app cannot work without it.

1. You enter a role or skill (and optionally a company watchlist).
2. The app pulls current postings from SerpApi's Google Jobs engine.
3. Each posting is normalized (company, level, location, remote, posted time, a short note).
4. Every run is saved to a local SQLite database.
5. From the second run on, the app diffs against the previous run and charts posting volume over time.

**No AI key needed.** The default extraction is rules-based and uses only fields SerpApi returns. If you add an optional
Anthropic API key, Claude writes the cleaned-up fields and signal notes instead. Same app, same results shape.

## Setup

You need Python 3.10+ and a free SerpApi key (250 searches/month) from <https://serpapi.com/users/sign_up>.

```bash
git clone https://github.com/<your-username>/hiring-signal.git
cd hiring-signal

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # Windows: copy .env.example .env
# open .env and set SERPAPI_API_KEY=your_key   (ANTHROPIC_API_KEY is optional)
```

## Run

```bash
python app.py
```

Open **http://localhost:5000**.

1. Enter a role (for example `LLM infra engineer`), a location, and optionally a company watchlist.
2. Click **Track now**. The first run saves a baseline.
3. Click **Track now** again later (a day or a week). The page shows new and disappeared postings and the trend chart.

**Load simulated demo data** fills in clearly labelled fictional history so you can preview the diff and chart
without waiting for real changes. It is not real market data.

### Command line (optional)

```bash
python main.py track --query "LLM infra engineer" --location "India"
python main.py trend --query "LLM infra engineer"
python main.py chart --query "LLM infra engineer" --out trend.png
python main.py demo
```

## Project layout

```
app.py              Flask web app (localhost)
templates/          Web UI
serpapi_client.py   SerpApi Google Jobs calls
extractor.py        Rules-based extraction (+ optional Claude)
storage.py          SQLite storage and run-to-run diff
demo.py             Simulated demo data (labelled)
main.py, digest.py  Command-line interface
chart.py            PNG trend export
tests/              Unit tests (no API keys needed)
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Notes and limits

- Google Jobs results vary by location and query, and not every employer posts there. Treat trends as a signal, not a
  census.
- A "disappeared" posting may be filled, pulled, or just not returned that time.
- Keys live in `.env` (gitignored). Never commit real keys.
