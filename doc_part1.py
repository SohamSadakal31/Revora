import os
from fpdf.enums import XPos, YPos

def add_chapters_1_to_5(pdf):
    # ==========================================
    # CHAPTER 1: AUTOMOTIVE ECONOMICS & PROBLEM FORMULATION
    # ==========================================
    pdf.chapter('1', 'Automotive Economics & Mathematical Problem Formulation')
    
    pdf.sec('1.1 The Indian Pre-Owned Vehicle Market Landscape')
    pdf.p(
        "The pre-owned automobile market in India is one of the fastest-growing vehicle ecosystems globally, "
        "consistently outpacing new car sales in transaction volume by a factor of 1.4x to 1.6x. However, unlike organized "
        "markets in North America or Western Europe (which rely on centralized data clearinghouses such as Kelley Blue Book "
        "or Edmunds), the Indian market is characterized by severe fragmentation, price asymmetry, regional market imbalances, "
        "and opportunistic unorganized brokering."
    )
    pdf.p(
        "Historically, buyers and private sellers have faced the classic 'Market for Lemons' dilemma described by George Akerlof: "
        "because buyers cannot readily verify odometer authenticity, maintenance rigor, or true residual value, they discount "
        "their willingness to pay across the board, driving higher-quality pre-owned vehicles off the market. Revora was "
        "conceived to resolve this market opacity by replacing intuition and arbitrary dealer markups with an objective, "
        "statistically grounded valuation engine."
    )
    
    pdf.sec('1.2 Depreciation Velocity & Non-Linear Price Curves')
    pdf.p(
        "Automotive depreciation does not follow a linear function. A vehicle loses approximately 15% to 20% of its initial "
        "showroom value within the first twelve months due to initial tax capitalization, dealership registration costs, "
        "and instant classification as pre-owned. Beyond year one, depreciation decelerates into an asymptotic power-law decay "
        "where each incremental year and kilometre driven causes a diminishing absolute price penalty."
    )
    pdf.bullet("Year 0 to 1", "Steep initial loss (-15% to -20% of invoice price), driven by registration transfer and showroom exit.")
    pdf.bullet("Year 2 to 5", "Stable compounding depreciation (-8% to -12% per annum), highly sensitive to odometer reading and brand equity.")
    pdf.bullet("Year 6 to 10", "Depreciation plateau; pricing becomes dominated by mechanical condition, remaining fitness certificate validity, and fuel type.")
    pdf.bullet("Beyond Year 10", "Scrap-floor stabilization; prices converge toward residual utility and regional regulatory mandates (e.g., the 10-year diesel / 15-year petrol ban in Delhi-NCR).")
    
    pdf.sec('1.3 Market Channels: Dealership Spreads vs. Private Sellers')
    pdf.p(
        "In India, used cars are sold via three distinct seller archetypes: Individual Private Sellers, Traditional Independent "
        "Dealers, and Certified Trustmark Dealers (e.g., Maruti True Value, Hyundai Promise, Spinny, Cars24). An empirical analysis "
        "conducted on 302 matched pairs of identical model, fuel, and transmission variants in the CarDekho dataset revealed that "
        "dealerships demand a median price premium of +2.8% over private individual sellers for the exact same vehicle."
    )
    pdf.p(
        "This +2.8% dealer margin compensates for dealership overhead, inventory holding capital, cosmetic reconditioning, "
        "and limited warranty guarantees. A naive machine learning model that treats seller type as an unconstrained categorical "
        "variable frequently violates this economic reality due to noisy training records, occasionally predicting that a private "
        "seller's car is worth more than an identical dealer car. Revora solves this by applying an explicit, verified +2.8% dealer "
        "premium on top of the private-seller baseline."
    )
    
    pdf.sec('1.4 Fuel Type Economics & Emission Regulatory Impacts')
    pdf.p(
        "The Indian passenger vehicle fleet spans five distinct powertrain archetypes: Petrol, Diesel, Compressed Natural Gas (CNG), "
        "Liquified Petroleum Gas (LPG), and Electric Vehicles (EV). Each exhibits unique depreciation trajectories:"
    )
    pdf.bullet("Diesel Vehicles", "Historically prized for superior fuel economy and low-end torque; commands a 10% to 15% price premium when new. However, depreciation accelerates sharply after year 7 due to strict emissions regulations (National Green Tribunal 10-year operational cap in northern zones) and higher routine maintenance costs.")
    pdf.bullet("Petrol Vehicles", "Displays linear, predictable depreciation. Enjoys widespread liquidity across both rural and urban markets with 15-year registration validity.")
    pdf.bullet("Factory CNG vs. Aftermarket Kits", "Factory-fitted CNG models (e.g., Maruti S-CNG, Hyundai Hy-CNG) maintain exceptional price retention due to ultra-low running costs, whereas aftermarket kits suffer a 12% to 18% valuation penalty due to perceived engine wear and trunk space compromise.")
    
    pdf.sec('1.5 Brand Equity & Residual Value Retention Across 39 Manufacturers')
    pdf.p(
        "Automotive resale value in India is heavily dominated by brand perception, spare-parts ubiquity, and service network density. "
        "The Revora catalog encompasses 39 distinct manufacturers grouped into three primary economic tiers:"
    )
    
    brand_headers = ['Market Tier', 'Representative Brands', 'Average 5-Year Value Retention', 'Resale Characteristics']
    brand_rows = [
        ['Tier 1: High Liquidity', 'Maruti Suzuki, Hyundai, Toyota', '65% - 72% of Initial Cost', 'Immediate liquidity, ubiquitous parts availability, low depreciation.'],
        ['Tier 2: Mid Liquidity', 'Honda, Tata, Mahindra, Kia, Volkswagen', '52% - 62% of Initial Cost', 'Solid enthusiast demand, moderate maintenance costs, strong SUV retention.'],
        ['Tier 3: Luxury / Low Vol', 'BMW, Mercedes-Benz, Audi, Jaguar, Volvo', '35% - 48% of Initial Cost', 'Steep early depreciation (-50% in 3 years), high routine maintenance costs.']
    ]
    pdf.table(brand_headers, brand_rows, [38, 48, 42, 52])

    pdf.sec('1.6 Mathematical Formulation of the Valuation Task')
    pdf.p(
        "Let x in R^D represent the feature vector of a vehicle, comprising categorical specifications (brand, model, trim, "
        "fuel type, transmission), continuous technical attributes (engine cc, max power bhp, torque Nm, seating capacity), "
        "and physical condition metrics (age at listing, odometer km driven, seller classification). The valuation task is to learn "
        "a function f: R^D -> R+ that estimates the advertised fair transaction price y in INR."
    )
    pdf.p(
        "Because automotive prices span two orders of magnitude (from INR 40,000 for aging hatchbacks to INR 2,75,00,000 for "
        "luxury sports sedans), minimizing standard Mean Squared Error (MSE) on raw prices causes the model to prioritize high-value "
        "luxury vehicles while generating huge percentage errors on mass-market family vehicles. Revora formulates the regression "
        "target in logarithmic space:"
    )
    pdf.code("Target Transformation:\n    z = ln(y)\n    f_hat(x) = exp( g(x) )\nLoss Function:\n    L(z, g(x)) = ( z - g(x) )^2")
    pdf.p(
        "Optimizing squared error on log(price) corresponds directly to minimizing relative Mean Absolute Percentage Error (MAPE), "
        "ensuring uniform precision across both budget hatchbacks (Maruti Alto) and premium executive sedans (BMW 5 Series)."
    )
    
    # ==========================================
    # CHAPTER 2: FULL-STACK MICROSERVICES ARCHITECTURE
    # ==========================================
    pdf.chapter('2', 'Full-Stack Microservices Architecture & System Topography')
    
    pdf.sec('2.1 Decoupled Microservice Topography')
    pdf.p(
        "Revora is architected as a distributed, decoupled multi-service application containerized with Docker Compose. "
        "The system explicitly isolates client presentation, REST API orchestration, in-memory machine learning inference, "
        "transient caching, persistent relation storage, and metrics telemetry into independent operating boundaries."
    )
    
    pdf.code(
        "                       +-------------------------------------------------------+\n"
        "                       |                 End User Web Browser                  |\n"
        "                       +-------------------------------------------------------+\n"
        "                                                  | (HTTP Port 8501)\n"
        "                                                  v\n"
        "                       +-------------------------------------------------------+\n"
        "                       |       Frontend Service: Streamlit 1.39 + Altair       |\n"
        "                       |       - Dynamic Form Widgets (car_form)               |\n"
        "                       |       - Altair Vega-Lite Visualizations               |\n"
        "                       |       - Client-Side Session State & Theme Engine      |\n"
        "                       +-------------------------------------------------------+\n"
        "                                                  | Internal HTTP (token + api-key)\n"
        "                                                  v\n"
        "                       +-------------------------------------------------------+\n"
        "                       |         Backend Service: FastAPI 0.110 (Uvicorn)       |\n"
        "                       |       - Pydantic v2 Input Validation & Normalization  |\n"
        "                       |       - JWT Authentication & RBAC (routes_auth)       |\n"
        "                       |       - Counterfactual Pricing Engine (routes_predict)|\n"
        "                       |       - Prometheus Instrumentator (/metrics)          |\n"
        "                       +-------------------------------------------------------+\n"
        "                           /                      |                         \\\n"
        "                          v                       v                          v\n"
        "              +-------------------+     +-------------------+      +-------------------+\n"
        "              |  ML Model Engine  |     |   Redis Cache     |      |  SQLite Databases |\n"
        "              |  HistGradBoost    |     |   Port 6379       |      |  users.db (Auth)  |\n"
        "              |  Quantile Bounds  |     |   7-Day TTL Keys  |      |  usage.db (Audit) |\n"
        "              |  In-Process Mem   |     |   Circuit Breaker |      |  Daily Auto-Backup|\n"
        "              +-------------------+     +-------------------+      +-------------------+\n"
        "                                                  ^\n"
        "                                                  | (Scrapes :8000/metrics every 10s)\n"
        "                       +-------------------------------------------------------+\n"
        "                       |      Telemetry: Prometheus v3.15 + Grafana 13.2       |\n"
        "                       +-------------------------------------------------------+"
    )
    
    pdf.sec('2.2 Service Breakdown & Container Specifications')
    pdf.p(
        "The platform consists of seven distinct services defined in docker-compose.yml:"
    )
    
    services_headers = ['Service Name', 'Base Image / Build', 'Port Binding', 'Role & Health Dependency']
    services_rows = [
        ['api', 'Dockerfile (Python 3.10)', '127.0.0.1:8000', 'FastAPI REST backend; serves predictions, auth & metrics.'],
        ['frontend', 'Dockerfile.frontend (Slim)', '127.0.0.1:8501', 'Streamlit UI; communicates over private bridge to api:8000.'],
        ['redis', 'redis:8.10.2-alpine', 'Internal Only (6379)', 'Sub-millisecond prediction key-value cache with LRU eviction.'],
        ['backup', 'Dockerfile (Python 3.10)', 'No Port (Daemon)', 'Scheduled worker copying logs/*.db to logs/backups/ every 24h.'],
        ['prometheus', 'prom/prometheus:v3.15.0', '127.0.0.1:9090', 'Time-series database scraping API metrics every 10 seconds.'],
        ['grafana', 'grafana/grafana:13.2.3', '127.0.0.1:3000', 'Pre-provisioned dashboard displaying latency and throughput.'],
        ['https', 'caddy:2 (Profile: https)', '80, 443', 'Optional reverse proxy providing automatic TLS certificate issuance.']
    ]
    pdf.table(services_headers, services_rows, [28, 42, 38, 72])
    
    pdf.sec('2.3 Network Isolation & Security Perimeter')
    pdf.p(
        "By design, the Redis caching service and database backup worker do not publish ports to the host interface. "
        "They communicate strictly across the private Docker bridge network backend. Furthermore, development ports "
        "(8000, 8501, 9090, 3000) are explicitly bound to the loopback interface 127.0.0.1 rather than 0.0.0.0, "
        "preventing unauthorized external access during development and internal testing."
    )

    pdf.sec('2.4 Hardware Resource Utilization & Latency Budgets')
    pdf.p(
        "The microservice architecture is optimized to run smoothly on modest virtual private servers (1 vCPU, 2GB RAM):"
    )
    pdf.bullet("FastAPI In-Memory Footprint", "~180MB RAM with loaded Scikit-Learn models and Joblib artifacts.")
    pdf.bullet("Streamlit Frontend Footprint", "~120MB RAM including cached catalog DataFrames and Altair specs.")
    pdf.bullet("Redis Cache Footprint", "< 25MB RAM under typical query caching volume.")
    pdf.bullet("Inference Latency Budget", "Raw ML inference: ~12ms per car. With Redis cache hit: < 1.5ms. Factor counterfactuals (4 runs): ~48ms.")
    
    # ==========================================
    # CHAPTER 3: COMPLETE REPOSITORY ARCHITECTURE
    # ==========================================
    pdf.chapter('3', 'Complete Repository Architecture & File Walkthrough')
    pdf.sec('3.1 File Hierarchy & Responsibilities')
    pdf.p(
        "The Revora codebase is organized into strict functional modules separating machine learning training pipelines, "
        "backend API routing, web presentation, persistence, and continuous integration testing. Below is an exhaustive "
        "audit of every critical file in the repository:"
    )
    
    repo_headers = ['Directory / Path', 'File Name', 'Lines', 'Technical Role']
    repo_rows = [
        ['app/', 'main.py', '26', 'ASGI root; initializes FastAPI, Prometheus instrumentator, middleware & routers.'],
        ['app/api/', 'routes_predict.py', '98', 'Defines /predict, /options, /stats, /history, and /share/quotation.'],
        ['app/api/', 'routes_auth.py', '82', 'JWT issuance, user registration, login, and password reset endpoints.'],
        ['app/api/', 'routes_health.py', '16', 'Liveness probe returning model version, dealer premium, and Redis status.'],
        ['app/api/', 'routes_admin.py', '54', 'Administrator dashboard metrics: user counts, popular brands, and fuel breakdown.'],
        ['app/core/', 'config.py', '48', 'Settings class loading .env with security thresholds and dev defaults.'],
        ['app/core/', 'dependencies.py', '42', 'FastAPI Depends hooks: API key validation and JWT bearer token extraction.'],
        ['app/core/', 'exceptions.py', '24', 'Standardized exception handlers formatting HTTP errors into unified JSON.'],
        ['app/services/', 'model_service.py', '123', 'In-memory ML model loader, prediction executor, counterfactuals & forecasting.'],
        ['app/services/', 'users.py', '140', 'User auth logic: PBKDF2 hashing, failed login lockouts, SQLite queries.'],
        ['app/services/', 'usage_log.py', '72', 'Audit trail logger writing search queries and pricing results to usage.db.'],
        ['app/services/', 'mailer.py', '64', 'SMTP email dispatcher for password reset codes and attached quote PDFs.'],
        ['app/services/', 'backup.py', '58', 'Automated SQLite hot-backup daemon managing snapshot rotation.'],
        ['app/cache/', 'redis_cache.py', '26', 'StrictRedis wrapper with 1s timeout and offline fallback.'],
        ['frontend/', 'app.py', '707', 'Streamlit UI root: layout, theme switcher, tab orchestration & forms.'],
        ['frontend/', 'insights.py', '224', 'Altair charts: depreciation curves, fuel mix, brand comparisons.'],
        ['frontend/', 'account.py', '175', 'Account management UI: history table, JSON data export, password updates.'],
        ['frontend/', 'quote_pdf.py', '365', 'FPDF2 engine generating formal A4 quotation and comparison PDFs.'],
        ['training/', 'experiment_current_market.py', '474', 'A/B/C experiment framework, 10-check leakage audit, holdout evaluation.'],
        ['training/', 'train_model.py', '85', 'Production retraining pipeline exporting model.joblib & metadata.'],
        ['training/', 'spec_enrichment.py', '168', 'Imputation engine filling engine_cc, bhp, torque from verified catalog variants.'],
        ['training/', 'clean_historical_data.py', '92', 'Sanitization pipeline cleaning raw CarDekho mileage and units.']
    ]
    pdf.table(repo_headers, repo_rows, [28, 42, 18, 92])

    pdf.sec('3.2 Configuration Engine: app/core/config.py')
    pdf.p(
        "Settings are managed through a centralized Settings class in app/core/config.py using python-dotenv. "
        "The class specifies fallback development defaults while warning administrators if default secrets remain active in production:"
    )
    pdf.code(
        "DEV_DEFAULTS = {'API_KEY': 'demo-key', 'JWT_SECRET_KEY': 'secret', 'ADMIN_PASSWORD': 'admin'}\n\n"
        "class Settings:\n"
        "    PROJECT_NAME = 'Car Price API'\n"
        "    API_KEY = os.getenv('API_KEY', DEV_DEFAULTS['API_KEY'])\n"
        "    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', DEV_DEFAULTS['JWT_SECRET_KEY'])\n"
        "    JWT_ALGORITHM = 'HS256'\n"
        "    JWT_EXPIRE_MINUTES = int(os.getenv('JWT_EXPIRE_MINUTES', '30'))\n"
        "    LOGIN_MAX_FAILURES = int(os.getenv('LOGIN_MAX_FAILURES', '5'))\n"
        "    LOGIN_LOCK_MINUTES = int(os.getenv('LOGIN_LOCK_MINUTES', '15'))\n"
        "    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')\n"
        "    USAGE_DB_PATH = os.getenv('USAGE_DB_PATH', 'logs/usage.db')\n"
        "    USERS_DB_PATH = os.getenv('USERS_DB_PATH', 'logs/users.db')"
    )
    
    # ==========================================
    # CHAPTER 4: DATA ENGINEERING & PROVENANCE
    # ==========================================
    pdf.chapter('4', 'Data Engineering, Cleansing & Multi-Source Dataset Provenance')
    pdf.sec('4.1 Multi-Source Dataset Composition')
    pdf.p(
        "Revora combines multiple verified automotive listing datasets to bridge historical price records with contemporary "
        "market valuations. The aggregated training dataset comprises 15,602 verified records across three distinct collections:"
    )
    
    data_headers = ['Dataset Source', 'Records', 'Date Range', 'Licence Type', 'Role in Pipeline']
    data_rows = [
        ['CarDekho (Nehal Birla)', '6,926', 'Up to ~2020', 'ODbL v1.0 / DbCL v1.0', 'Historical baseline; 302 matched pairs for dealer premium.'],
        ['Used Car Price (Vrajesh Sharma)', '6,710', '2019 - 2021', 'CC0 Public Domain', 'Current market transition dataset; weighted x2 in training.'],
        ['Car Details v4 (CarDekho Updated)', '1,966', 'Jan 2023', 'ODbL v1.0 / DbCL v1.0', 'Modern inflation benchmark; holds the newest market listings.'],
        ['Aggregated Total', '15,602', '1983 - 2023', 'Attribution Verified', 'Comprehensive multi-era training and holdout corpus.']
    ]
    pdf.table(data_headers, data_rows, [44, 20, 26, 38, 52])
    
    pdf.sec('4.2 Data Cleansing & Unit Normalization (clean_historical_data.py)')
    pdf.p(
        "Raw automotive listings contain rampant formatting discrepancies, non-numeric strings, and corrupt zero-values. "
        "The cleansing script clean_historical_data.py enforces strict normalization rules:"
    )
    pdf.bullet("Corrupt Mileage Nullification", "102 listings in the raw historical dataset recorded mileage as '0.0 kmpl'. These were verified as data-entry errors and converted to true NaN values rather than being left as zero (which would distort tree splits).")
    pdf.bullet("Fuel Economy Unit Conversion", "Indian listings report fuel economy in either km/l (for liquid fuels: Petrol, Diesel) or km/kg (for compressed gases: CNG, LPG). Mileage is standardized to miles-per-gallon (mpg) via the exact conversion factor: mileage_mpg = km_per_litre * 2.35215.")
    pdf.bullet("Text Feature Extraction via Regex", "Engine displacements recorded as '1248 CC', power outputs recorded as '74 bhp', and torque ratings recorded as '190Nm@ 2000rpm' are parsed via compiled regular expressions into clean floating-point numerics.")

    pdf.sec('4.3 Data Dictionary for Canonical Model Features')
    pdf.p(
        "Following cleansing and enrichment, all listings adhere to a canonical 15-feature schema:"
    )
    
    feat_headers = ['Feature Name', 'Data Type', 'Value Domain / Units', 'Description']
    feat_rows = [
        ['company', 'Categorical (str)', '39 distinct brands', 'Manufacturer name (e.g. Maruti, Hyundai, Honda).'],
        ['model', 'Categorical (str)', '284 distinct models', 'Vehicle model name (e.g. Swift, City, Creta).'],
        ['edition', 'Text (str)', 'Variant strings', 'Sub-trim level (e.g. VXI, ZDI, Asta, Sport).'],
        ['owner', 'Categorical (str)', 'First, Second, Third, etc.', 'Number of previous registered owners.'],
        ['fuel', 'Categorical (str)', 'Petrol, Diesel, CNG, LPG', 'Primary combustion engine fuel type.'],
        ['seller_type', 'Categorical (str)', 'Individual, Dealer, Trustmark', 'Sales channel classification.'],
        ['transmission', 'Categorical (str)', 'Manual, Automatic', 'Transmission gearbox mechanism.'],
        ['age_at_listing', 'Continuous (int)', '0 to 40 years', 'Listing year minus year of manufacture.'],
        ['listing_year', 'Continuous (int)', '2019 to 2023', 'Year the vehicle was advertised.'],
        ['km_driven', 'Continuous (float)', '0 to 1,000,000 km', 'Odometer distance reading in kilometres.'],
        ['sold_by_dealer', 'Binary (0.0 / 1.0)', '0=Individual, 1=Dealer', 'Indicator flag for dealer margin enforcement.'],
        ['mileage_mpg', 'Continuous (float)', '10.0 to 120.0 mpg', 'Standardized fuel economy.'],
        ['engine_cc', 'Continuous (float)', '500 to 6,600 cc', 'Total cylinder engine displacement.'],
        ['max_power_bhp', 'Continuous (float)', '25 to 650 bhp', 'Peak engine brake horsepower output.'],
        ['torque_nm', 'Continuous (float)', '35 to 1,900 Nm', 'Peak engine rotational torque in Newton-metres.']
    ]
    pdf.table(feat_headers, feat_rows, [35, 34, 45, 66])
    
    # ==========================================
    # CHAPTER 5: SPEC ENRICHMENT ALGORITHM
    # ==========================================
    pdf.chapter('5', 'Spec Enrichment & Cross-Variant Attribute Matching')
    pdf.sec('5.1 The Missing Specification Challenge')
    pdf.p(
        "While historical records often contain detailed mechanical specifications (engine CC, max power BHP, torque Nm, "
        "and seating capacity), modern web-scraped listings frequently omit these technical parameters, providing only "
        "the Brand, Model, Year, Fuel, Transmission, and Trim Variant (e.g., 'Maruti Swift VDI'). Discarding rows with missing "
        "specs would eliminate 40% of modern listings, while training without specs severely degrades accuracy."
    )
    pdf.sec('5.2 The Non-Leaking Enrichment Engine (spec_enrichment.py)')
    pdf.p(
        "Revora implements a multi-tier catalog lookup algorithm that imputes missing mechanical specifications strictly "
        "from verified reference vehicles possessing the exact same engineering identity:"
    )
    pdf.code(
        "Matching Hierarchy:\n"
        "1. Exact Variant Match: (company, model, edition, fuel, transmission)\n"
        "2. Year-Relaxed Variant Match: (company, model, edition, fuel, transmission) across all historical years\n"
        "3. Imputation Guardrail: If candidate reference rows exhibit > 5% variance in engine CC or power, imputation\n"
        "   is rejected to prevent contaminating distinct sub-trims.\n"
        "4. Anti-Leakage Guarantee: Price is strictly omitted from the lookup key. Enrichment is performed independently\n"
        "   on training and holdout partitions."
    )
    pdf.sec('5.3 Enrichment Verification Across 15 Pytest Cases')
    pdf.p(
        "In test_spec_enrichment.py (15 passing tests), the enrichment engine is verified across edge cases: handling Roman "
        "numeral trims (VXI vs. ZXI), lowercase variant tokens, automatic dual-clutch transmissions, and ensuring that no "
        "target label information is ever leaked into feature matrices."
    )
    
    print("Expanded Chapters 1 to 5 added.")

if __name__ == '__main__':
    print("Part 1 module loaded.")
