# 🚗 Revora — Used Car Price Estimator

Revora estimates the fair market price of a used car in India. Pick the car, describe its condition, and it returns
a price, an expected price range, what moves the price, and how the value is likely to change over the next three
years — with a downloadable PDF quotation.

It is a full-stack ML project: a gradient-boosted model behind a **FastAPI** service, a **Streamlit** web app,
**Redis** caching, **SQLite** accounts and history, **Prometheus/Grafana** monitoring, all run with **Docker Compose**.

> Estimates are a guide based on *advertised* listing prices (not final sale prices) up to January 2023.
> See **Limitations** below.

---

## ✨ Features

**Pricing**
- **Price estimate** with an **expected range** (separate 5th / 95th-percentile models)
- **What affects this price** — the effect of the variant, kilometres (vs a typical 10,000 km/year), number of owners
  and seller type, each computed by re-pricing the car with that one input changed
- **Value forecast** — the same car 1, 2 and 3 years older, at its own km-per-year rate
- **Asking-price verdict** — great deal / fair price / a little high / overpriced, against the estimate and range
- **Compare cars** — 2 or 3 cars side by side, with a comparison PDF
- **PDF quotation** — download it, or email it to a customer (needs SMTP)
- **Loan / EMI calculator** on each estimate

**Market insights** — market snapshot, a per-model "price by age" chart with fuel / gearbox mix, value retention and
typical price by brand, like-for-like price differences (automatic vs manual, diesel vs petrol, dealer vs private
seller, …) and the most searched cars on the site.

**Accounts**
- Sign up / log in with email and password; JWT sessions
- **My account** — past estimates (re-download their quotations), download all your data as JSON, change password,
  delete account (also deletes your estimates)
- Forgot password with an emailed 6-digit code (needs SMTP)
- **Admin dashboard** for the admin account configured in `.env` — users, sign-ups, estimates per day, most searched
  cars, estimates by fuel

**Platform** — light / dark theme, Redis prediction cache (the app keeps working without Redis), Prometheus metrics
with a provisioned Grafana dashboard, automatic SQLite backups, optional HTTPS through Caddy.

---

## 🏗️ Architecture

```
Browser ──► Streamlit frontend (:8501) ──HTTP, headers: token + api-key──► FastAPI backend (:8000)
                                                                             ├── ML models (joblib, loaded at start-up)
                                                                             ├── SQLite: logs/users.db, logs/usage.db
                                                                             ├── Redis: prediction cache (internal only)
                                                                             └── SMTP: reset codes, quotation emails (optional)

Prometheus (:9090) ──scrapes /metrics every 10 s──► FastAPI         Grafana (:3000) ──queries──► Prometheus
backup service ──► copies logs/*.db to logs/backups/ every 24 h
Caddy (profile "https", :80/:443) ──► Streamlit frontend            (optional, for a public server)
```

The Streamlit server calls the API from its own process (the browser never calls the API directly).

### Docker Compose services

| Service | Image | Published port | Purpose |
|---|---|---|---|
| `api` | built from `Dockerfile` (Python 3.10) | `127.0.0.1:8000` | FastAPI backend + model |
| `frontend` | built from `Dockerfile.frontend` (Python 3.10 slim) | `127.0.0.1:8501` | Streamlit web app |
| `redis` | `redis:8.10.2-alpine` | none — internal network only | Prediction cache |
| `prometheus` | `prom/prometheus:v3.15.0` | `127.0.0.1:9090` | Metrics |
| `grafana` | `grafana/grafana:13.2.3` | `127.0.0.1:3000` | Dashboards |
| `backup` | built from `Dockerfile` | none | SQLite backups |
| `https` (profile `https`) | `caddy:2` | `80`, `443` | Optional public HTTPS for the website |

Development ports are bound to `127.0.0.1`, so they are reachable only from the machine running Docker.

---

## 🧠 ML approach

**Inputs** (validated by the API; text is case-insensitive):

| Field | Example | Notes |
|---|---|---|
| `company`, `model` | `Maruti`, `Swift` | Unknown values are rejected with `422` (see `GET /options`) — never guessed |
| `edition` | `VDI` | Variant / trim; optional, improves accuracy |
| `year` | `2015` | 1980 – current year |
| `owner`, `fuel`, `seller_type`, `transmission` | `First`, `Diesel`, `Individual`, `Manual` | |
| `km_driven` | `60000` | 0 – 1,000,000 |
| `mileage_mpg` | `55` | Optional (km/l × 2.352); leave empty for CNG / LPG |
| `engine_cc`, `max_power_bhp`, `torque_nm`, `seats` | `1248`, `74`, `190`, `5` | Range-checked |

**Model** (`training/experiment_current_market.py`, trained by `training/train_model.py`):
- `HistGradientBoostingRegressor` inside a scikit-learn pipeline, trained on **log(price)**
  (`TransformedTargetRegressor`), squared-error loss.
- **Features:** car age at listing and listing year (instead of manufacture year), km driven, seller type as a 0/1
  dealer flag, technical specs, and brand / model / owner / fuel / transmission as native categorical features
  (`OrdinalEncoder`). The variant text is split into words (`CountVectorizer`), so e.g. "VXI" or "AMT" can carry signal.
- **Monotonic constraints:** an older car or more kilometres never raises the price; a dealer listing is never priced
  below the same car from a private seller. Squared-error loss is used because it keeps these rules exact.
- **Price range:** two extra models with quantile loss at the 5th and 95th percentiles.
- **Dealer premium:** the price is estimated as a private-seller price, then dealer listings get **+2.8%** — the
  median dealer-vs-private gap measured across **302 same model + year groups** in the historical data.
- **Missing specs stay missing** (the model handles them). Specs for current listings are filled only from identical
  variants (same company, model, edition, fuel, transmission) when those reference rows agree; price is never used.

**Training data strategy** — historical listings plus more recent "current" listings, with current rows weighted ×2.

**Leakage prevention and evaluation**
- **Time-based holdout:** the newest 20% of current listings (all copies of a listing kept on the same side) are held
  out and never used for training, spec lookup, preprocessing, weights or hyperparameters.
- An automated **10-check leakage audit** runs with every experiment (all pass — `experiments/current_market/experiment_report.md`).
- After evaluation, the production model is retrained on **all** rows, so the reported scores are conservative.

---

## 📊 Dataset and evaluation

| Data | Listings | Source / licence | Listing dates |
|---|---|---|---|
| Historical | 6,926 | CarDekho "Vehicle dataset" (Nehal Birla) — ODbL / DbCL | No dates in the data; assumed 2020 (unconfirmed) |
| Current | 6,710 | "Used Car Price Prediction" — CC0 | 2019 – 2021 |
| Current | 1,966 | `car details v4.csv` from the same Vehicle dataset — ODbL / DbCL | January 2023 |
| **Total** | **15,602** | | newest data: **January 2023** |

The historical data is used in its cleaned form (`data/car-details-cleaned.csv`: 102 unusable mileage values set to
missing; every other value identical to the original, which is verified before training).

**Holdout:** the newest 1,737 current listings. Results of the offline experiment:

| Approach | MAE | R² | Median % error | Within ±10% | Within ±20% |
|---|---|---|---|---|---|
| A — historical data only | ₹500,159 | 0.551 | 22.9% | 16.2% | 41.5% |
| B — historical + current (equal weight) | ₹388,064 | 0.636 | 11.8% | 42.0% | 71.0% |
| **C — historical + current ×2 (production)** | **₹398,762** | **0.630** | **12.4%** | **42.3%** | **70.5%** |

**Production result (approach C):** median error **12.4%**, **42.3%** of estimates within ±10% and **70.5%** within
±20% of the advertised price; **67.5%** of real prices fall inside the predicted range. Approach C was declared as the
production approach before the run; B and C are within about one percentage point of each other. The live model's own
figures are served by `GET /health` and shown in the app.

---

## 🧰 Tech stack

| Area | Tools |
|---|---|
| Language | Python 3.10 |
| Backend | FastAPI 0.110, Uvicorn, Pydantic v2, python-jose (JWT) |
| ML / data | scikit-learn 1.3.2, pandas 2.3.3, NumPy 1.26.4, joblib |
| Frontend | Streamlit 1.39, Altair charts, fpdf2 (PDF quotations) |
| Storage | SQLite (accounts, history), Redis (cache) |
| Monitoring | prometheus-fastapi-instrumentator, Prometheus, Grafana |
| Infrastructure | Docker, Docker Compose, Caddy (optional HTTPS) |
| Quality | pytest, GitHub Actions |

---

## 📁 Project structure

```
.
├── app/                          FastAPI backend
│   ├── main.py                   app, routers, middleware, /metrics
│   ├── api/                      routes: auth, predict, health, admin
│   ├── core/                     settings, JWT security, auth dependencies, error handler
│   ├── cache/redis_cache.py      Redis cache (skipped if Redis is unavailable)
│   ├── middleware/               request logging
│   ├── services/                 model, users, usage log, mailer, backups
│   └── models/                   model.joblib, model_range.joblib, model_meta.json
├── frontend/                     Streamlit app: app.py, account.py, insights.py, quote_pdf.py, .streamlit/
├── training/                     data loading and validation, cleaning, spec enrichment, experiment, train_model
├── data/                         historical + current listings, template, licence and source notes
├── experiments/current_market/   experiment config, results and report
├── tests/                        pytest suite
├── grafana/                      provisioned datasource and dashboard
├── .github/workflows/ci.yml      GitHub Actions
├── Dockerfile, Dockerfile.frontend, docker-compose.yml, Caddyfile, prometheus.yml, render.yaml
├── requirements.txt, requirements-dev.txt, frontend/requirements.txt
└── .env.example
```

`logs/` (SQLite databases and backups) and `.env` are created locally and are not committed.

---

## 🚀 Getting started

**Prerequisites:** Docker with Docker Compose, or Python 3.10 for running without Docker.

### 1. Configure

```bash
cp .env.example .env
```

Edit `.env` and set **your own values** — see **Configuration** below. `.env` holds secrets and is
git-ignored: never commit it.

### 2a. Run with Docker Compose (recommended)

```bash
docker compose up -d --build
docker compose ps
```

| Open | URL |
|---|---|
| Web app | http://localhost:8501 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health / model info | http://localhost:8000/health |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |

Stop with `docker compose down`.

### 2b. Run without Docker

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt -r frontend/requirements.txt
```

The three requirement files are consistent (all use pandas 2.3.3), so they install into one environment.

```bash
uvicorn app.main:app --reload            # API on http://localhost:8000 (reads .env)
```

In a second terminal (the frontend does not read `.env`, so pass the same API key):

```bash
cd frontend
API_URL=http://localhost:8000 API_KEY=<the API_KEY from your .env> streamlit run app.py
```

Without a Redis server at `REDIS_URL`, the API simply runs without its cache.

---

## ⚙️ Configuration

All settings come from environment variables; `.env.example` lists them.

| Variable | Purpose |
|---|---|
| `API_KEY` | Shared key the frontend sends in the `api-key` header |
| `JWT_SECRET_KEY`, `JWT_EXPIRE_MINUTES` | Signing secret and lifetime (default 30 min) of login tokens |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | The admin account (it lives only in `.env`) |
| `REDIS_URL` | For running without Docker; Compose sets `redis://redis:6379` for the API |
| `LOGIN_MAX_FAILURES`, `LOGIN_LOCK_MINUTES` | Lock-out after repeated wrong passwords (defaults 5 / 15 min) |
| `RESET_CODE_MINUTES`, `EMAILS_PER_USER_PER_DAY` | Reset-code lifetime (30 min) and daily quotation-email limit (20) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS` | Outgoing email. Leave `SMTP_HOST` empty to switch password reset and emailed quotations off |
| `QUOTE_BUSINESS_NAME` (+ `_ADDRESS`, `_PHONE`, `_EMAIL`, `_GSTIN`), `QUOTE_VALID_DAYS` | Business details printed on quotations; the name is also used in emails (default `Revora`) |
| `BACKUP_INTERVAL_HOURS`, `BACKUP_KEEP` | Backup frequency (24 h) and copies kept (14) |
| `DOMAIN` | Public domain for the optional HTTPS service |

If `API_KEY`, `JWT_SECRET_KEY` or `ADMIN_PASSWORD` is not set, the API falls back to **development defaults** and logs a
warning. Always set long random values before anyone else can reach the app.

---

## 🔌 API endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /register` | – | Create an account (`email`, `password`, `full_name`); returns a JWT. Passwords need 8+ characters with a letter and a number |
| `POST /login` | – | Get a JWT with `email` + `password` (the admin account uses `username`) |
| `GET /me` | `token` | The signed-in user |
| `POST /account/password` | `token` | Change password (`current_password`, `new_password`) |
| `POST /account/delete` | `token` | Delete the account and its estimates (`password`) |
| `POST /password/forgot` | – | Email a 6-digit reset code (needs SMTP); same answer whether or not the email exists |
| `POST /password/reset` | – | Set a new password with the code (`email`, `code`, `new_password`) |
| `POST /predict` | `token` + `api-key` | Price, range, price factors and 1–3 year forecast |
| `GET /history` | `token` + `api-key` | The user's own estimates (last 50) |
| `GET /stats` | `token` + `api-key` | Most searched cars |
| `POST /share/quotation` | `token` + `api-key` | Email a quotation PDF (needs SMTP; daily limit per user) |
| `GET /admin/stats` | admin `token` + `api-key` | Users, sign-ups, estimates per day, most searched cars |
| `GET /options` | – | Accepted brands, models, fuels, … |
| `GET /health` | – | Status, Redis, model version and the model's test metrics |
| `GET /metrics` | – | Prometheus metrics |

`token` and `api-key` are request headers. Interactive docs: http://localhost:8000/docs.

---

## 🧪 Testing

```bash
pytest -q
```

With all three requirement files installed, the full suite runs: **140 tests, all passing**. The tests use temporary
SQLite databases and need no Redis, SMTP or Docker. If only `requirements.txt` and `requirements-dev.txt` are installed,
the frontend tests (`tests/test_insights.py`, `tests/test_quote_pdf.py`) are skipped automatically.

**CI** — GitHub Actions (`.github/workflows/ci.yml`) runs on every push and pull request: it installs
`requirements.txt` + `requirements-dev.txt` on Python 3.10, runs `python -m pytest -q tests`, then builds both Docker
images.

---

## 📈 Monitoring

- The API exposes request counts and latency histograms at `/metrics` (prometheus-fastapi-instrumentator).
- Prometheus scrapes `api:8000` every 10 seconds (`prometheus.yml`).
- Grafana is provisioned with the Prometheus data source and a dashboard (`grafana/dashboards/car-price-api.json`):
  estimates in the last 24 h, error rate, `/predict` p95 latency, rejected inputs, requests per minute and p95 latency
  by endpoint, and responses by status.
- The repository does not configure Grafana credentials, so Grafana's own default admin login applies until you
  change it.

---

## 🔒 Security

Practical measures in place — this is a portfolio project, not a security-audited product:

- **Secrets from the environment** (`.env`, git-ignored); the API warns when development defaults are in use.
- **JWT authentication** (HS256, 30-minute tokens) plus an API key for the pricing endpoints. A deleted account's
  tokens stop working immediately.
- **Passwords** stored as salted PBKDF2-SHA256 hashes (310,000 iterations) with constant-time comparison.
- **Lock-out** after repeated failed logins; reset codes are hashed, expire, allow 5 guesses and are limited to
  3 requests per hour; quotation emails are limited per user per day.
- **Internal errors** are logged server-side and never returned to clients.
- **Network exposure:** Redis has no published port, and the development ports listen on `127.0.0.1` only.

---

## 🛠️ Retraining and data

Run the training tools in the API image so library versions match production (from the project root):

```bash
# check data/current-listings.csv without training anything (exit code 0 = all rows valid)
docker compose run --rm --no-deps -v "$(pwd)":/app api python -m training.validate_current_listings

# offline A/B/C experiment on the held-out newest listings (writes to experiments/current_market/)
docker compose run --rm --no-deps -v "$(pwd)":/app api python -m training.experiment_current_market --historical-path data/car-details-cleaned.csv

# train the production model (overwrites app/models/), then rebuild the API image
docker compose run --rm --no-deps -v "$(pwd)":/app api python -m training.train_model
docker compose up -d --build api
```

- `data/current-listings.csv` is built from the public datasets with `python -m training.build_current_listings --force`
  (needs `pip install kagglehub`; sources and licences in `data/current-listings-sources.md`).
- To add listings by hand, start from `data/current-listings.template.csv` (header must stay unchanged). Use only real
  listing values: leave unknown specs empty rather than estimating them, and leave mileage empty for CNG / LPG.
- `python -m training.clean_historical_data` regenerates `data/car-details-cleaned.csv`; the original
  `data/car-details.csv` is never modified.

**Backups** — the `backup` service copies `logs/users.db` and `logs/usage.db` to `logs/backups/` every 24 hours and
keeps the newest 14. One-off backup: `docker compose exec backup python -m app.services.backup`.

**Public HTTPS** — on a server whose domain points at it, set `DOMAIN` (and strong secrets) in `.env`, then
`docker compose --profile https up -d --build`. Caddy obtains the certificate and serves the web app on 443; only
ports 80 and 443 need to be reachable from the internet.

**Render** — `render.yaml` deploys the API service only (no frontend or Redis, and no persistent disk for the
SQLite files).

---

## ⚠️ Limitations

- **Data age:** the newest listings are from January 2023, so estimates reflect that market level, and they are
  based on advertised prices, not final sale prices.
- **Assumed historical listing year:** the historical data has no listing dates; 2020 is assumed and not confirmed.
- **Holdout scope:** the held-out listings are all dated January 2023 and come from one source, so the evaluation
  measures generalisation to that data rather than a long period of time.
- **Price range is too narrow:** only 67.5% of real prices fall inside the 5th–95th-percentile range (nominal 90%).
- **Price extremes:** median error is about 10–11% between ₹2 and ₹20 lakh, but 18.4% above ₹20 lakh and 31.7%
  below ₹2 lakh (only 49 holdout listings), with very expensive cars under-predicted.
- **Exact names only:** brands and models must match the training data's naming (no fuzzy matching); unknown cars
  are rejected rather than guessed.
- **Single-node storage:** accounts and history live in SQLite files on one machine.

---

## 📜 Data licences

- Historical data and `car details v4.csv`: [Vehicle dataset](https://www.kaggle.com/datasets/nehalbirla/vehicle-dataset-from-cardekho)
  by Nehal Birla — **ODbL v1.0** (database) / **DbCL v1.0** (contents). Attribution is shown in the app footer; a
  publicly shared modified copy of the database (such as `car-details-cleaned.csv`) must stay under ODbL.
- Current listings: [Used Car Price Prediction](https://www.kaggle.com/datasets/vrajesh0sharma7/used-car-price-prediction) — **CC0**.
- Only datasets whose licence allows commercial use are included. Details: `data/DATA-LICENSE.md` and
  `data/current-listings-sources.md`.

The repository does not currently include a licence for the source code.
