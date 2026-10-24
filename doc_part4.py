import os
from fpdf.enums import XPos, YPos

def add_chapters_16_to_20(pdf):
    # ==========================================
    # CHAPTER 16: REDIS CACHING & CIRCUIT BREAKER
    # ==========================================
    pdf.chapter('16', 'Redis High-Throughput Caching & Circuit-Breaker Resilience')
    
    pdf.sec('16.1 Deterministic Prediction Cache Keys')
    pdf.p(
        "To achieve sub-millisecond response times for frequent vehicle valuations, Revora implements an intelligent "
        "caching layer backed by Redis 8-Alpine. A major challenge in ML caching is preventing stale predictions from being "
        "served after a model is retrained or updated. Revora solves this by incorporating the model version hash directly "
        "into the deterministic cache key:"
    )
    pdf.code(
        "Cache Key Composition (app/services/model_service.py):\n"
        "    MODEL_VERSION = hashlib.md5(open(settings.MODEL_PATH, 'rb').read()).hexdigest()[:8]\n"
        "    RESULT_FORMAT = 2  # Incremented when response schema expands (e.g. forecast)\n"
        "    cache_key = f'{MODEL_VERSION} r{RESULT_FORMAT} {MARKET_YEAR} {DEALER_PREMIUM} ' + \\\n"
        "                ' '.join([str(val) for val in data.values()])"
    )
    pdf.p(
        "Predictions are cached with a 7-day Time-To-Live (TTL): redis_client.set(key, json.dumps(result), ex=7*24*3600). "
        "If a new model artifact is placed into production, MODEL_VERSION changes instantly, invalidating the entire cache "
        "without requiring manual key flushing."
    )

    pdf.sec('16.2 Graceful Degradation & Circuit-Breaker Design')
    pdf.p(
        "Redis is treated as a non-blocking performance optimization rather than a hard operational dependency. "
        "If Redis crashes or is not deployed locally, try-except blocks trap redis.RedisError, log a warning, and allow "
        "predictions to proceed directly to in-process ML inference. This guarantees 100% uptime even in resource-constrained "
        "or standalone environments."
    )

    # ==========================================
    # CHAPTER 17: STREAMLIT FRONTEND ARCHITECTURE
    # ==========================================
    pdf.chapter('17', 'Streamlit Frontend Architecture, Theming Engine & CSS Injection')
    
    pdf.sec('17.1 Reactive Execution Model & @st.fragment Isolation')
    pdf.p(
        "Streamlit scripts typically re-execute from top to bottom on any user interaction. In an application with complex "
        "forms, side-by-side car comparisons, and extensive charts, full-page reruns introduce UI stutter and latency. "
        "Revora optimizes execution using Streamlit's @st.fragment decorator:"
    )
    pdf.bullet("Fragmented Tab Reruns", "estimate_tab(), compare_tab(), and insights_tab() are encapsulated in independent @st.fragment scopes, isolating widget state changes to that specific tab.")
    pdf.bullet("Session State Management", "st.session_state maintains authentication tokens (auth), active estimates (last), multi-car comparison selections (compare), and theme selections across reruns.")
    
    pdf.sec('17.2 The Custom Design System & CSS Variable Injection')
    pdf.p(
        "Revora overrides standard Streamlit widget styling using a comprehensive vanilla CSS design system injected "
        "via st.markdown. The styling defines responsive cards, metric callouts, custom pills, and an animated slider toggle:"
    )
    pdf.code(
        "Theme Palette (CSS Variables):\n"
        "  Light Mode: --bg: #ffffff; --text: #0f172a; --field: #f1f5f9; --surface: #f0f7ff; --accent: #1e3a8a\n"
        "  Dark Mode:  --bg: #0b1220; --text: #e2e8f0; --field: #131c2e; --surface: #111b2f; --accent: #93c5fd"
    )

    # ==========================================
    # CHAPTER 18: MARKET INSIGHTS & ALTAIR ENGINE
    # ==========================================
    pdf.chapter('18', 'Vega-Lite Market Analytics, Altair Charts & PyArrow Buffers')
    
    pdf.sec('18.1 Interactive Visual Grammar with Altair')
    pdf.p(
        "The Market Insights dashboard (frontend/insights.py) transforms 15,602 listings into declarative Vega-Lite "
        "visualizations using Altair 5. Key analytical charts include:"
    )
    pdf.bullet("Model Depreciation Curves", "Plots listing price against vehicle age, rendering a central median trend line accompanied by an interquartile (25th-75th percentile) shaded confidence ribbon.")
    pdf.bullet("Fuel & Gearbox Distribution", "Horizontal bar chart visualizing the market proportion of Petrol, Diesel, CNG, and Automatic vs. Manual transmissions for any selected model.")
    pdf.bullet("Macroeconomic Price Disparity Spreads", "Bar chart displaying like-for-like percentage spreads across fuel types, transmissions, and seller tiers.")

    pdf.sec('18.2 PyArrow Buffer Optimization & Compatibility Resolution')
    pdf.p(
        "Streamlit renders Altair charts by serializing pandas DataFrames into Apache Arrow IPC record batches. "
        "When Streamlit 1.39 pulls pyarrow, version mismatches with NumPy 1.26 can cause severe C-extension import crashes. "
        "Revora explicitly locks pyarrow<19.0 (installing PyArrow 18.1.0), guaranteeing seamless memory-efficient Arrow "
        "buffer serialization without crashing NumPy 1.x or scikit-learn 1.3.2 C-bindings."
    )

    # ==========================================
    # CHAPTER 19: QUOTATION PDF ENGINE
    # ==========================================
    pdf.chapter('19', 'Quotation Document Generation Engine & Numbering Algorithms')
    
    pdf.sec('19.1 Institutional Valuation PDF Design (quote_pdf.py)')
    pdf.p(
        "Revora provides dealership-ready, printable valuation documents generated dynamically using FPDF2. "
        "The document structure adheres to formal commercial invoice standards:"
    )
    pdf.bullet("Business Headers", "Customizable company name, GSTIN number, phone, email, and physical address.")
    pdf.bullet("Unique Quotation Hashing", "Deterministic quote identifier generated via SHA-1: QT-YYYYMMDD-XXXXXX.")
    pdf.bullet("Indian Currency Digit Grouping", "Formats large numbers using standard Indian digit commas: INR 12,34,567.")
    pdf.bullet("Currency Word Expansion", "Custom algorithm amount_in_words converting numerical amounts into formal legal text: 'Rupees Four Lakh Fifty Two Thousand Five Hundred Only' (handling Crores, Lakhs, and Thousands).")

    # ==========================================
    # CHAPTER 20: DEVOPS, DOCKER & OBSERVABILITY
    # ==========================================
    pdf.chapter('20', 'DevOps, Multi-Service Containerization & Observability')
    
    pdf.sec('20.1 Multi-Stage Containerization')
    pdf.p(
        "The application is containerized with two distinct Dockerfiles:"
    )
    pdf.bullet("Dockerfile (FastAPI Backend & ML)", "Builds on python:3.10; installs joblib, scikit-learn, numpy, pandas, and uvicorn. Pre-loads model binaries into /app/models.")
    pdf.bullet("Dockerfile.frontend (Streamlit)", "Builds on lightweight python:3.10-slim; installs streamlit, requests, altair, and fpdf2.")

    pdf.sec('20.2 Telemetry with Prometheus & Grafana')
    pdf.p(
        "Production observability is achieved via Prometheus v3.15 scraping the /metrics endpoint exposed by "
        "prometheus-fastapi-instrumentator every 10 seconds. Metrics tracked include:"
    )
    pdf.bullet("http_requests_total", "Monitors incoming query volume broken down by handler, HTTP method, and status code.")
    pdf.bullet("http_request_duration_seconds", "Histogram buckets measuring 50th, 90th, and 99th percentile API latency.")
    pdf.bullet("Pre-Provisioned Grafana Dashboard", "Grafana loads datasources and dashboards automatically from grafana/provisioning, displaying real-time traffic graphs without manual configuration.")

    print("Chapters 16 to 20 added.")

if __name__ == '__main__':
    print("Part 4 module loaded.")
