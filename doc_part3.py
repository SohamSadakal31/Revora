import os
from fpdf.enums import XPos, YPos

def add_chapters_11_to_15(pdf):
    # ==========================================
    # CHAPTER 11: DEPRECIATION FORECASTING ENGINE
    # ==========================================
    pdf.chapter('11', 'Multi-Year Value Depreciation Forecasting Algorithm')
    
    pdf.sec('11.1 Dynamic Individual Driving Pace Estimation')
    pdf.p(
        "A static vehicle depreciation schedule (e.g. 'cars lose 10% per year') fails to account for individual driving habits. "
        "A taxi or commercial commuter driving 35,000 km/year depreciates dramatically faster than an urban commuter driving "
        "5,000 km/year. Revora calculates an individualized historical driving velocity for every vehicle:"
    )
    pdf.code(
        "Pace Calculation Logic:\n"
        "    if age >= 1 and km_driven > 0:\n"
        "        km_per_year = km_driven / age\n"
        "    else:\n"
        "        km_per_year = 10_000  # Default Indian national annual average"
    )

    pdf.sec('11.2 Multi-Year Forward Simulation')
    pdf.p(
        "The forecasting engine simulates the vehicle aging into the future across horizons of 1, 2, and 3 years: "
        "years = (1, 2, 3). For each forward step k:"
    )
    pdf.bullet("Simulated Age", "age_future = age_at_listing + k")
    pdf.bullet("Simulated Mileage", "km_future = km_driven + k * km_per_year")
    pdf.bullet("Macroeconomic Market Normalization", "listing_year remains locked at MARKET_YEAR (current year). This is a crucial design choice: it isolates purely mechanical vehicle depreciation from broader macroeconomic inflation, giving buyers and sellers an actionable prediction in today's currency terms.")

    pdf.sec('11.3 Mathematical Monotonicity of the Forecast')
    pdf.p(
        "Because age_future > age and km_future > km_driven, the model's negative monotonic constraints guarantee that: "
        "price_today >= forecast_1yr >= forecast_2yr >= forecast_3yr. The forecast can never produce an irrational future "
        "price increase, providing dependable salvage and trade-in projections for auto financing and loan underwriting."
    )

    # ==========================================
    # CHAPTER 12: FASTAPI REST API ENGINE
    # ==========================================
    pdf.chapter('12', 'FastAPI REST API Engine & Request Lifecycle')
    
    pdf.sec('12.1 ASGI Lifespan & Application Architecture')
    pdf.p(
        "The Revora backend is built with FastAPI 0.110 running on Uvicorn workers. The application root (app/main.py) "
        "initializes middleware, registers structured exception handlers, mounts modular API routers, and exposes "
        "Prometheus performance instrumentation:"
    )
    pdf.code(
        "app = FastAPI(title='Car Price Prediction API')\n"
        "app.add_middleware(LoggingMiddleware)\n"
        "app.include_router(routes_auth.router, tags=['Auth'])\n"
        "app.include_router(routes_predict.router, tags=['Prediction'])\n"
        "app.include_router(routes_health.router, tags=['Health'])\n"
        "app.include_router(routes_admin.router, tags=['Admin'])\n"
        "Instrumentator().instrument(app).expose(app)"
    )

    pdf.sec('12.2 Request Lifecycle & Middleware Processing')
    pdf.p(
        "Every incoming HTTP request undergoes a structured sequence of lifecycle stages:"
    )
    pdf.bullet("1. LoggingMiddleware", "Interprets incoming client IP, request method, path, and records total request processing duration in milliseconds.")
    pdf.bullet("2. Prometheus Instrumentation", "Collects HTTP latency histograms, response status counters (2xx, 4xx, 5xx), and active connection counts.")
    pdf.bullet("3. Dependency Injection", "Executes get_api_key (verifying the X-API-Key or api-key header against settings.API_KEY) and get_account (extracting JWT bearer tokens).")
    pdf.bullet("4. Route Handler & Validation", "Pydantic v2 parses and validates JSON payloads against field-level bounds.")
    pdf.bullet("5. Cache Interception", "Model service checks Redis cache using deterministic SHA-derived keys.")
    pdf.bullet("6. Audit Logging", "usage_log.py records successful searches into SQLite usage.db asynchronously.")

    # ==========================================
    # CHAPTER 13: SCHEMA VALIDATION & INTEGRITY
    # ==========================================
    pdf.chapter('13', 'Schema Validation, Type Systems & Pydantic V2 Integrity')
    
    pdf.sec('13.1 Pydantic V2 CarFeatures Model')
    pdf.p(
        "The core prediction payload is governed by the CarFeatures schema in app/api/routes_predict.py. "
        "Pydantic v2 enforces strict bounds on all inputs, rejecting malicious or physically impossible values:"
    )
    
    schema_headers = ['Field Name', 'Type', 'Validation Constraints', 'Economic / Physical Bounds']
    schema_rows = [
        ['company', 'string', 'Known brands only', 'Case-insensitive; verified against model vocabulary.'],
        ['model', 'string', 'Known models only', 'Case-insensitive; checked against GET /options.'],
        ['edition', 'string', 'Optional string', 'Trim variant (e.g. VXI, ZDI); parsed into sub-tokens.'],
        ['year', 'integer', '1980 <= year <= current', 'Rejects vintage / unverified years prior to 1980.'],
        ['owner', 'string', 'First/Second/Third/Fourth', 'Standard Indian vehicle registration ownership tiers.'],
        ['fuel', 'string', 'Petrol/Diesel/CNG/LPG/Electric', 'Fuel category matching engine combustion characteristics.'],
        ['seller_type', 'string', 'Individual/Dealer/Trustmark', 'Applies appropriate +2.8% dealer margin.'],
        ['transmission', 'string', 'Manual/Automatic', 'Gearbox specification.'],
        ['km_driven', 'float', '0.0 <= km <= 1,000,000', 'Odometer reading capped at 1 million kilometres.'],
        ['mileage_mpg', 'float | None', '0.0 < mpg <= 150.0', 'Optional fuel efficiency; handles missing values.'],
        ['engine_cc', 'float', '500.0 <= cc <= 7,000.0', 'Engine displacement in cubic centimetres.'],
        ['max_power_bhp', 'float', '20.0 <= bhp <= 700.0', 'Engine peak brake horsepower.'],
        ['torque_nm', 'float', '30.0 <= nm <= 2,000.0', 'Engine peak torque in Newton-metres.'],
        ['seats', 'float', '2.0 <= seats <= 14.0', 'Passenger seating capacity (2-seater coupe to 14-seater van).']
    ]
    pdf.table(schema_headers, schema_rows, [28, 24, 46, 82])

    pdf.sec('13.2 Case-Insensitive Normalization & Error Trapping')
    pdf.p(
        "The model service normalizes all string inputs by stripping whitespace and lowercasing strings. "
        "If a user inputs an unknown brand or model (e.g. 'Tesla' or 'Ferrari' which are not present in the training set), "
        "the service raises an UnknownValueError resulting in a clean HTTP 422 Unprocessable Entity error referencing GET /options, "
        "preventing silent extrapolation hallucinations."
    )

    # ==========================================
    # CHAPTER 14: AUTHENTICATION & SECURITY
    # ==========================================
    pdf.chapter('14', 'Authentication, Cryptographic Security & Session Lifecycle')
    
    pdf.sec('14.1 JWT Cryptographic Architecture')
    pdf.p(
        "User authentication is built on stateless JSON Web Tokens (JWT) signed using HMAC-SHA256 (HS256). "
        "The cryptographic token encapsulates user identity and role claims:"
    )
    pdf.code(
        "JWT Claims Payload:\n"
        "{\n"
        "    'sub': 'user_email@example.com',\n"
        "    'email': 'user_email@example.com',\n"
        "    'is_admin': false,\n"
        "    'exp': 1792850400  // Unix timestamp (expires after settings.JWT_EXPIRE_MINUTES = 30m)\n"
        "}"
    )

    pdf.sec('14.2 Password Hashing & Brute-Force Defenses')
    pdf.p(
        "Passwords are cryptographically salted and hashed using PBKDF2 with SHA-256 (100,000 iterations). "
        "To mitigate automated credential-stuffing and brute-force password guessing, app/services/users.py implements "
        "an account lockout mechanism:"
    )
    pdf.bullet("Failed Login Counter", "Tracks failed authentication attempts per email in users.db.")
    pdf.bullet("Account Lockout", "Upon 5 consecutive failed login attempts (settings.LOGIN_MAX_FAILURES), the account is locked for 15 minutes (settings.LOGIN_LOCK_MINUTES).")
    pdf.bullet("Password Reset Codes", "Issues cryptographically secure 6-digit verification codes expiring after 30 minutes, dispatched via TLS-encrypted SMTP.")

    # ==========================================
    # CHAPTER 15: DUAL-DATABASE SQLITE PATTERN
    # ==========================================
    pdf.chapter('15', 'Dual-Database SQLite Architecture & Audit Persistence')
    
    pdf.sec('15.1 The Dual-Database Isolation Strategy')
    pdf.p(
        "Revora segregates transactional user authentication from high-volume analytical search logs by maintaining "
        "two distinct SQLite databases in logs/:"
    )
    pdf.bullet("users.db (Authentication)", "Stores user accounts, password hashes, full names, admin flags, failed login timestamps, and password reset codes.")
    pdf.bullet("usage.db (Audit Trail)", "Stores every pricing query: timestamp, vehicle specifications, predicted price, authenticated user email, full request payload, and resulting JSON response.")

    pdf.sec('15.2 SQLite Concurrency & Automated Backups')
    pdf.p(
        "SQLite provides zero-configuration, ACID-compliant persistence without requiring an external database cluster. "
        "To ensure continuous operations without locking contention:"
    )
    pdf.bullet("WAL Mode & Short Transactions", "Connections are opened on-demand in context managers and committed immediately.")
    pdf.bullet("Dynamic Schema Migration", "Functions inspect PRAGMA table_info on startup and execute ALTER TABLE ADD COLUMN automatically if schema fields evolve.")
    pdf.bullet("Automated Hot-Backups (app.services.backup)", "A dedicated background daemon executes every 24 hours, taking hot snapshots of both databases into logs/backups/ and retaining the last 14 backup rotations.")

    print("Chapters 11 to 15 added.")

if __name__ == '__main__':
    print("Part 3 module loaded.")
