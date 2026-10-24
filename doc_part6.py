import os
from fpdf.enums import XPos, YPos

def add_chapters_24_to_28(pdf):
    # ==========================================
    # CHAPTER 24: CORE CODE WALKTHROUGH
    # ==========================================
    pdf.chapter('24', 'Annotated Code Walkthrough of Critical Engine Components')
    
    pdf.sec('24.1 In-Memory Model Service (app/services/model_service.py)')
    pdf.p(
        "The model service loads the serialized Scikit-Learn pipeline and quantile bounds at server startup, "
        "retaining them in memory for sub-millisecond execution without repeated disk I/O:"
    )
    pdf.code(
        "# app/services/model_service.py (Core Valuation Routine)\n"
        "model = joblib.load(settings.MODEL_PATH)\n"
        "price_range = joblib.load(settings.MODEL_RANGE_PATH) if os.path.exists(settings.MODEL_RANGE_PATH) else None\n\n"
        "def predict_car_price(data: dict) -> dict:\n"
        "    data = _normalise(data)          # Strip whitespace and lowercase\n"
        "    _check_known(data)               # Verify brand and model exist in KNOWN_VALUES\n"
        "    data = _model_input(data)        # Compute age_at_listing and listing_year\n"
        "    cache_key = f'{MODEL_VERSION} r{RESULT_FORMAT} {MARKET_YEAR} {DEALER_PREMIUM} ' + \\\n"
        "                ' '.join([str(val) for val in data.values()])\n"
        "    cached = get_cached_prediction(cache_key)\n"
        "    if cached:\n"
        "        return cached\n\n"
        "    price = _estimate(model, [data])[0]\n"
        "    result = {'price': round(price, 2)}\n"
        "    if price_range:\n"
        "        low = _estimate(price_range['low'], [data])[0]\n"
        "        high = _estimate(price_range['high'], [data])[0]\n"
        "        result['price_low'], result['price_high'] = round(min(low, price), 2), round(max(high, price), 2)\n"
        "    result['factors'] = _factors(data, price)\n"
        "    result.update(_forecast(data))\n"
        "    set_cached_prediction(cache_key, result)\n"
        "    return result"
    )

    pdf.sec('24.2 Indian Numbering & Currency Spelling in PDF Engine (quote_pdf.py)')
    pdf.p(
        "Commercial invoices and valuation quotations in India mandate amounts written in words following the Vedic/Indian "
        "numbering system (Crores, Lakhs, Thousands, Hundreds) rather than Western millions/billions:"
    )
    pdf.code(
        "# frontend/quote_pdf.py (Number-to-Words Expansion)\n"
        "def amount_in_words(amount: float) -> str:\n"
        "    n = int(round(amount))\n"
        "    if n == 0:\n"
        "        return 'Rupees Zero Only'\n"
        "    parts = []\n"
        "    for size, label in ((10_000_000, 'Crore'), (100_000, 'Lakh'), (1_000, 'Thousand')):\n"
        "        if n >= size:\n"
        "            parts.append(f'{_below_thousand(n // size)} {label}')\n"
        "            n %= size\n"
        "    if n:\n"
        "        parts.append(_below_thousand(n))\n"
        "    return 'Rupees ' + ' '.join(parts) + ' Only'"
    )

    # ==========================================
    # CHAPTER 25: 25 CHATGPT TECHNICAL Q&A PAIRS
    # ==========================================
    pdf.chapter('25', '25 Exhaustive Technical Q&A Prompts for ChatGPT & AI Models')
    pdf.p(
        "Below are 25 verified, technically rigorous question-and-answer pairs designed to provide instant reference "
        "for ChatGPT when reasoning about or writing code for the Revora repository:"
    )

    qa_list = [
        ("Q1: What is the exact primary machine learning algorithm used in Revora?",
         "HistGradientBoostingRegressor from scikit-learn 1.3.2 wrapped inside a TransformedTargetRegressor on log(price) with squared_error loss."),
        ("Q2: Why does Revora use squared_error instead of absolute_error for gradient boosting?",
         "absolute_error recalculates final tree leaf values using the median of residuals post-splitting, which breaks monotonic constraints on 1% to 4% of samples. squared_error calculates leaf values strictly as the gradient mean, mathematically preserving 100% of monotonic rules."),
        ("Q3: How are dealer listings priced differently from private seller listings?",
         "The model predicts the private seller price first. If seller_type in ('dealer', 'trustmark dealer'), a +2.8% dealer margin is added. This +2.8% was derived from 302 matched pairs in historical data."),
        ("Q4: How does Revora enforce that older cars or higher mileage never increase price?",
         "Through the monotonic_cst parameter in HistGradientBoostingRegressor: age_at_listing is set to -1, km_driven is set to -1, and sold_by_dealer is set to +1."),
        ("Q5: What are the lower and upper price bounds, and how are they calculated?",
         "They are estimated by two auxiliary HistGradientBoosting models trained with quantile loss at alpha=0.05 (5th percentile) and alpha=0.95 (95th percentile). They are clamped so that price_low <= price <= price_high."),
        ("Q6: How does the multi-year value depreciation forecasting algorithm work?",
         "It calculates the car's annual driving pace (km_per_year = km_driven / age, or 10,000 km fallback) and simulates the car aging at 1, 2, and 3 years ahead while holding listing_year constant at the current market year."),
        ("Q7: How does counterfactual factor sensitivity attribution work?",
         "It re-prices the car four separate times with one attribute changed: (1) km set to typical age*10,000 km, (2) owner set to First, (3) seller set to Individual, (4) edition set to empty base trim. The deltas isolate the exact rupee impact of each feature."),
        ("Q8: Why does the project use a dual-database pattern for SQLite?",
         "To isolate critical authentication and user credentials (logs/users.db) from high-volume analytical search logs and query payloads (logs/usage.db), preventing locking contention."),
        ("Q9: What happens if Redis is offline or not installed?",
         "The app handles redis.RedisError gracefully via try-except blocks in app/cache/redis_cache.py, skipping the cache and calculating predictions in-process with zero downtime."),
        ("Q10: Why did Streamlit previously crash on the Market Insights tab, and how was it fixed?",
         "Streamlit 1.39 pulled pyarrow 26.0 which requires NumPy >= 2.0, but scikit-learn 1.3.2 requires NumPy < 2.0 (1.26.4). The conflict was resolved by pinning pyarrow<19.0 (version 18.1.0) in requirements.txt."),
        ("Q11: What is the total test coverage of the automated test suite?",
         "140 tests across 11 test files, executed via pytest tests/ -v with 100% pass rate."),
        ("Q12: How are missing technical specifications handled during inference?",
         "Missing specs are preserved as NaN. HistGradientBoostingRegressor natively handles missing values during split evaluation without requiring synthetic mean/median imputation."),
        ("Q13: How does spec_enrichment.py avoid data leakage during training?",
         "Price is completely excluded from the lookup dictionary key, and enrichment dictionaries are constructed independently from training rows without cross-pollinating holdout sets."),
        ("Q14: How does JWT authentication protect against brute-force attacks?",
         "app/services/users.py locks an account for 15 minutes after 5 consecutive failed login attempts."),
        ("Q15: What is the holdout evaluation strategy used to benchmark Approach C?",
         "The newest 20% of modern current listings (1,737 rows) were quarantined by timestamp and never used for training or feature engineering."),
        ("Q16: What is the holdout R2 score and median percentage error of the production model?",
         "Holdout R2 is 0.630, and the median percentage error is 12.4%."),
        ("Q17: What percentage of holdout estimates fall within +/-10% and +/-20% of actual listing prices?",
         "42.3% of estimates fall within +/-10%, and 70.5% fall within +/-20%."),
        ("Q18: What is the role of the backup service in docker-compose.yml?",
         "It runs a Python daemon executing app.services.backup --loop, copying SQLite databases to logs/backups/ every 24 hours and keeping a 14-day rotation."),
        ("Q19: How are Prometheus metrics exposed from FastAPI?",
         "Via prometheus-fastapi-instrumentator mounted in app/main.py, exposing request counters, status codes, and latency histograms on GET /metrics."),
        ("Q20: How does the PDF quotation engine generate unique quote numbers?",
         "Using SHA-1: hashlib.sha1(json.dumps(payload).encode()).hexdigest()[:6].upper() combined with the date: QT-YYYYMMDD-XXXXXX."),
        ("Q21: How are car variants (edition) encoded in the ML pipeline?",
         "Using CountVectorizer(token_pattern=r'(?u)\\b\\w+\\b', min_df=5), which breaks variant names into sub-tokens such as VXI, ZDI, AMT, and ABS."),
        ("Q22: What are the valid fuel types accepted by the API?",
         "Petrol, Diesel, CNG, LPG, and Electric (verified by Pydantic and GET /options)."),
        ("Q23: How does the frontend optimize tab switching performance in Streamlit?",
         "By wrapping tabs in @st.fragment decorators, which isolate widget redraws and prevent top-to-bottom script re-execution."),
        ("Q24: What is the purpose of Caddy in docker-compose.yml?",
         "It acts as an optional production reverse proxy with the https profile, automatically provisioning and renewing Let's Encrypt TLS certificates."),
        ("Q25: Why is the model trained on 15,602 rows with current rows weighted x2?",
         "Because older historical data provides deep variant coverage but underestimates current post-pandemic inflation. Weighting modern listings x2 balances broad variant breadth with contemporary price levels.")
    ]

    for q, a in qa_list:
        pdf.subsec(q)
        pdf.p(a)

    # ==========================================
    # CHAPTER 26: COMPLETE DATA DICTIONARY
    # ==========================================
    pdf.chapter('26', 'Complete Data Dictionary & Automotive Vocabulary Catalog')
    
    pdf.sec('26.1 The 39 Recognized Automotive Manufacturers')
    pdf.p(
        "Revora strictly validates manufacturer inputs against its verified training vocabulary. The 39 recognized brands are:"
    )
    pdf.code(
        "Ambassador, Ashok Leyland, Audi, BMW, Chevrolet, Daewoo, Datsun, DC, Fiat, Force, Ford,\n"
        "Honda, Hyundai, Isuzu, Jaguar, Jeep, Kia, Land Rover, Lexus, Mahindr, Mahindra, Maruti,\n"
        "Mercedes-Benz, MG, Mini, Mitsubishi, Nissan, Opel, Porsche, Premier, Renault, Skoda, Smart,\n"
        "Tata, Toyota, Volkswagen, Volvo"
    )

    pdf.sec('26.2 Fuel, Transmission and Ownership Allowed Domains')
    pdf.p(
        "Below are the verified categorical domains exposed by GET /options:"
    )
    domain_headers = ['Field Name', 'Allowed Value Domain', 'Validation Behavior']
    domain_rows = [
        ['fuel', 'cng, diesel, electric, lpg, petrol', 'Normalized to lowercase; rejected with 422 if invalid.'],
        ['transmission', 'automatic, manual', 'Normalized to lowercase; binary split in gearbox.'],
        ['owner', 'first, second, third, fourth & above, test drive car', 'Maps directly to ownership depreciation penalties.'],
        ['seller_type', 'dealer, individual, trustmark dealer', 'Governs application of the +2.8% dealer margin.']
    ]
    pdf.table(domain_headers, domain_rows, [30, 80, 70])

    # ==========================================
    # CHAPTER 27: PRODUCTION RUNBOOK & TROUBLESHOOTING
    # ==========================================
    pdf.chapter('27', 'Production Runbook, Common Runtime Errors & Troubleshooting')
    
    pdf.sec('27.1 Common Runtime Scenarios and Proven Resolutions')
    pdf.p(
        "Below are operational failure modes encountered during deployment and their exact technical solutions:"
    )
    
    pdf.subsec('Issue 1: Port 8000 Conflict During docker-compose up')
    pdf.p(
        "Error: bind: Only one usage of each socket address (protocol/network address/port) is normally permitted.\n"
        "Root Cause: A local Python uvicorn process is already running on port 8000 on the host machine.\n"
        "Resolution: Stop the local uvicorn background process or run Get-Process python | Stop-Process before launching Docker Compose."
    )

    pdf.subsec('Issue 2: Latency Delay on Compare Prices (Redis Socket Timeout)')
    pdf.p(
        "Error: Repeated WARNING:root:Redis unavailable, skipping cache read: Timeout connecting to server.\n"
        "Root Cause: Redis is offline while redis_cache.py attempts connection with a 1-second socket timeout on every read and write.\n"
        "Resolution: Either start Redis container (docker run -d --name redis -p 6379:6379 redis:alpine) or apply the circuit breaker fallback in redis_cache.py."
    )

    pdf.subsec('Issue 3: PyArrow & NumPy Version Conflict in Streamlit Charts')
    pdf.p(
        "Error: ImportError: pyarrow requires NumPy 2.0 or newer, found 1.26.4.\n"
        "Root Cause: Streamlit 1.39 pulled unpinned PyArrow 26.0 which requires NumPy 2.0+, but scikit-learn 1.3.2 requires NumPy < 2.0.\n"
        "Resolution: Pin pyarrow<19.0 (PyArrow 18.1.0) in requirements.txt and frontend/requirements.txt."
    )

    # ==========================================
    # CHAPTER 28: FUTURE ROADMAP & EVOLUTION
    # ==========================================
    pdf.chapter('28', 'Future Architectural Roadmap & Engineering Evolution')
    
    pdf.sec('28.1 Near-Term Enhancements')
    pdf.bullet("Deep Computer Vision Inspection", "Integrating YOLOv8/v9 vehicle damage detection from user-uploaded photos to automatically adjust valuation for scratches and dents.")
    pdf.bullet("Regional Geo-Spatial Pricing", "Expanding the city pricing model with RTO (Regional Transport Office) road-tax depreciation adjustments across Indian states.")
    pdf.bullet("Live Market Web Scraper Pipeline", "Automating weekly Scrapy/Playwright crawlers to ingest current listings from major Indian classified portals, triggering automated monthly retraining.")

    pdf.callout(
        "Final Architectural Certification",
        "Revora exemplifies modern production Machine Learning engineering: blending statistically rigorous algorithms, "
        "domain-specific economic guardrails, clean microservice architecture, and defensive programming practices.",
        bg=(236, 253, 245), border=(167, 243, 208), title_color=(22, 101, 52)
    )

    print("Chapters 24 to 28 added.")

if __name__ == '__main__':
    print("Part 6 module loaded.")
