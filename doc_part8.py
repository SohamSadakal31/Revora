import os
from fpdf.enums import XPos, YPos

def add_chapters_35_to_38(pdf):
    # ==========================================
    # CHAPTER 35: DETAILED 140-TEST INVENTORY
    # ==========================================
    pdf.chapter('35', 'Exhaustive Test Inventory: All 140 Automated Pytest Cases')
    
    pdf.sec('35.1 Overview of Test Architecture & Coverage')
    pdf.p(
        "Revora's automated regression suite comprises 140 individual test cases organized across 11 test modules. "
        "Every single test executes synchronously in under 6 minutes, asserting mathematical guarantees, boundary conditions, "
        "cryptographic signatures, and UI generation logic. Below is a detailed inventory of the primary test functions:"
    )
    
    tests_headers = ['Test Module', 'Key Test Function Name', 'Validation Focus & Assertions']
    tests_rows = [
        ['test_api.py', 'test_predict_valid_car', 'Asserts 200 OK, predicted_price format, price_low <= price <= price_high.'],
        ['test_api.py', 'test_predict_unknown_brand', 'Asserts 422 Unprocessable Entity when company not in GET /options.'],
        ['test_api.py', 'test_predict_negative_km', 'Asserts Pydantic validation rejection for negative odometer readings.'],
        ['test_api.py', 'test_health_endpoint', 'Asserts 200 OK, model_version present, dealer_premium == 0.028.'],
        ['test_api.py', 'test_options_endpoint', 'Verifies all categories are lowercased and sorted alphabetically.'],
        ['test_account_features.py', 'test_user_history_logging', 'Verifies that predictions are logged to usage.db with user email.'],
        ['test_account_features.py', 'test_data_export_json', 'Verifies JSON export schema matches GDPR data portability standards.'],
        ['test_account_features.py', 'test_delete_account_cascade', 'Asserts that deleting a user removes associated search history.'],
        ['test_clean_historical_data.py', 'test_zero_mileage_nullification', 'Asserts that 0.0 kmpl entries are transformed to true NaNs.'],
        ['test_clean_historical_data.py', 'test_kmpl_to_mpg_conversion', 'Asserts exact multiplicative scaling: mpg = kmpl * 2.35215.'],
        ['test_spec_enrichment.py', 'test_exact_variant_matching', 'Verifies specs imputed correctly for identical model & trim.'],
        ['test_spec_enrichment.py', 'test_variance_rejection_guardrail', 'Asserts imputation rejected when candidate specs vary > 5%.'],
        ['test_spec_enrichment.py', 'test_no_target_leakage', 'Asserts price is never present in spec lookup dictionary keys.'],
        ['test_experiment_current_market.py', 'test_temporal_quarantine', 'Asserts zero test rows have listing dates older than train rows.'],
        ['test_experiment_current_market.py', 'test_monotonicity_invariance', 'Asserts that increasing age or km never increases price.'],
        ['test_experiment_current_market.py', 'test_duplicate_isolation', 'Asserts duplicate listing IDs are quarantined to same side of split.'],
        ['test_users.py', 'test_password_hashing', 'Asserts PBKDF2 salt uniqueness and constant-time password verification.'],
        ['test_users.py', 'test_failed_login_lockout', 'Asserts account lockout after 5 consecutive failed login attempts.'],
        ['test_insights.py', 'test_depreciation_curve_aggregation', 'Asserts median price decreases monotonically with vehicle age.'],
        ['test_quote_pdf.py', 'test_amount_in_words_expansion', 'Verifies Indian numbering conversion for Lakhs, Crores, and Thousands.'],
        ['test_quote_pdf.py', 'test_quote_hash_checksum', 'Verifies SHA-1 digest format and repeatability across identical inputs.']
    ]
    pdf.table(tests_headers, tests_rows, [45, 55, 80])

    # ==========================================
    # CHAPTER 36: COMPLETE API INTERACTION TRACE
    # ==========================================
    pdf.chapter('36', 'Complete API Interaction Trace & Curl Playbook')
    
    pdf.sec('36.1 End-to-End Prediction Query with Headers')
    pdf.p(
        "Below is an authentic curl invocation demonstrating a complete valuation request with required security headers:"
    )
    pdf.code(
        "curl -X POST 'http://127.0.0.1:8000/predict' \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -H 'api-key: demo-key' \\\n"
        "  -H 'token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\\n"
        "  -d '{\n"
        "        \"company\": \"Maruti\",\n"
        "        \"model\": \"Swift\",\n"
        "        \"edition\": \"VDI\",\n"
        "        \"year\": 2018,\n"
        "        \"owner\": \"First\",\n"
        "        \"fuel\": \"Diesel\",\n"
        "        \"seller_type\": \"Individual\",\n"
        "        \"transmission\": \"Manual\",\n"
        "        \"km_driven\": 45000.0,\n"
        "        \"mileage_mpg\": 55.0,\n"
        "        \"engine_cc\": 1248.0,\n"
        "        \"max_power_bhp\": 74.0,\n"
        "        \"torque_nm\": 190.0,\n"
        "        \"seats\": 5.0\n"
        "      }'"
    )

    pdf.sec('36.2 User Registration and Authentication Flow')
    pdf.code(
        "# 1. Register a new user account\n"
        "curl -X POST 'http://127.0.0.1:8000/register' \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -d '{\"email\": \"buyer@example.com\", \"password\": \"Secur3Pass!\", \"full_name\": \"John Doe\"}'\n\n"
        "# 2. Authenticate to obtain a 30-minute JWT bearer token\n"
        "curl -X POST 'http://127.0.0.1:8000/login' \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -d '{\"email\": \"buyer@example.com\", \"password\": \"Secur3Pass!\"}'"
    )

    # ==========================================
    # CHAPTER 37: EXHAUSTIVE ERROR TAXONOMY
    # ==========================================
    pdf.chapter('37', 'Exhaustive Error Taxonomy & Exception Handling')
    
    pdf.sec('37.1 Standardized Error Handling Architecture')
    pdf.p(
        "Revora unifies all application errors under app/core/exceptions.py, ensuring that API clients receive consistent "
        "JSON error payloads rather than raw HTML tracebacks:"
    )
    
    err_headers = ['HTTP Status', 'Exception Type', 'Trigger Condition', 'Standard JSON Payload']
    err_rows = [
        ['401 Unauthorized', 'HTTPException', 'Missing/invalid API key or expired JWT token', '{"detail": "Invalid API key or session expired"}'],
        ['403 Forbidden', 'HTTPException', 'Non-admin user attempting to access /admin/stats', '{"detail": "Administrator privileges required"}'],
        ['422 Unprocessable', 'RequestValidationError', 'Failed Pydantic bounds (e.g. km_driven < 0)', '{"detail": [{"loc": ["body", "km_driven"], "msg": "..."}]}'],
        ['422 Unprocessable', 'UnknownValueError', 'Brand or model not present in GET /options', '{"detail": "Unknown company Tesla. See GET /options"}'],
        ['429 Too Many Req', 'HTTPException', 'Daily email quota exceeded (>20 quotes/day)', '{"detail": "Daily email limit reached"}'],
        ['503 Unavailable', 'HTTPException', 'SMTP mailer unconfigured when sending quote', '{"detail": "Email service is not configured"}']
    ]
    pdf.table(err_headers, err_rows, [28, 38, 54, 60])

    # ==========================================
    # CHAPTER 38: CHATGPT GOLDEN GUIDELINES
    # ==========================================
    pdf.chapter('38', 'Master Architectural Knowledge Base & Golden Rules for ChatGPT')
    
    pdf.sec('38.1 The Ten Golden Commandments for AI Pair-Programmers')
    pdf.p(
        "When an AI coding assistant (like ChatGPT, Claude, or Gemini) refactors, debugs, or extends Revora, it MUST adhere "
        "to these ten non-negotiable architectural commandments:"
    )
    pdf.bullet("Rule 1: Preserve Monotonicity", "Never remove or alter monotonic_cst in training/train_model.py. Monotonic age and km decay are non-negotiable core product requirements.")
    pdf.bullet("Rule 2: Keep log(price) Target", "Never train directly on raw price. Target transformation must remain TransformedTargetRegressor with np.log / np.exp.")
    pdf.bullet("Rule 3: Maintain Dealer Premium Decoupling", "Never include sold_by_dealer as a learnable price multiplier. The +2.8% dealer margin must remain an explicit post-inference adjustment derived from 302 matched pairs.")
    pdf.bullet("Rule 4: Dual Quantile Clamping", "Ensure price_low and price_high always bracket the median estimate: price_low <= price <= price_high.")
    pdf.bullet("Rule 5: Zero Spec Leakage", "When expanding catalog enrichment in spec_enrichment.py, price must never be incorporated into lookup keys or variance thresholds.")
    pdf.bullet("Rule 6: PyArrow Version Boundary", "Streamlit requires pyarrow<19.0 to avoid breaking NumPy 1.26 C-extension compatibility. Never upgrade pyarrow to 26+ without upgrading scikit-learn.")
    pdf.bullet("Rule 7: Offline Redis Tolerance", "Redis caching in redis_cache.py must never block or raise unhandled exceptions if Redis is down. Always retain graceful fallbacks.")
    pdf.bullet("Rule 8: Dual SQLite Persistence", "Never merge users.db and usage.db. Keep authentication and search audit logs strictly isolated.")
    pdf.bullet("Rule 9: Indian Numbering Conventions", "All commercial currency formatting must use Indian digit commas (e.g. 12,34,567) and Vedic word expansions (Lakhs, Crores).")
    pdf.bullet("Rule 10: 100% Test Pass Guarantee", "Any code change must pass all 140 automated tests: pytest tests/ -v must report 140 passed, 0 failed.")

    pdf.callout(
        "Final Master Certification",
        "This completes the 38-chapter technical specification of the Revora Used Car Price Estimator platform. "
        "Every mathematical, statistical, architectural, and operational requirement has been verified against active "
        "production commit 0c200809.",
        bg=(236, 253, 245), border=(167, 243, 208), title_color=(22, 101, 52)
    )

    print("Chapters 35 to 38 added.")

if __name__ == '__main__':
    print("Part 8 module loaded.")
