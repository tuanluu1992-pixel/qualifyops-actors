# ATS Hiring Signal Finder — Greenhouse, Lever & Ashby

Turn a company's public applicant tracking system (ATS) job board into one structured hiring-signal record.

- **Input:** Greenhouse, Lever, or Ashby company handles or public job-board URLs.
- **Output:** one row per company with open-role count, role titles, locations, a deterministic hiring classification, transparent score reasons, and evidence job URLs.
- **Hosted Actor:** [qualifyops/ats-hiring-signal-finder](https://apify.com/qualifyops/ats-hiring-signal-finder)
- **Pricing:** pay per company record on Apify.

## Example input

```json
{
  "companies": [
    { "platform": "greenhouse", "slug": "stripe" },
    { "platform": "ashby", "slug": "ramp" },
    { "platform": "greenhouse", "slug": "gitlab" }
  ],
  "maxCompanies": 3
}
```

## Output fields

`company`, `platform`, `open_roles`, `roles`, `locations`, `hiring_signal`, `signal_reasons`, `signal_score`, `score_reasons`, `board_url`, `evidence_job_urls`, `status`, and `error`.

## Runtime

- Python 3.11
- Apify Python SDK `>=3.4.0,<4.0.0`
- Official public Greenhouse, Lever, and Ashby job-board endpoints
- No login, browser automation, or paid upstream data source

## Run locally

```bash
pip install -r requirements.txt
python -m src
```

For a local Apify Actor run, provide the input through the Apify CLI or Actor environment.

## Known limitations

- The current `signal_score` is a checklist score and tops out at 55.
- Evidence URLs currently use the first five job rows, so they may not match the dominant hiring category.
- The Actor returns up to 60 role titles and 20 locations, which can consume unnecessary AI-agent context.
- Hiring activity is a prioritization signal, not proof of budget or purchase intent.
