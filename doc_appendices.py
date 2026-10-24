import os
from fpdf.enums import XPos, YPos

def add_appendices(pdf):
    # ==========================================
    # APPENDIX A: COMPLETE ENVIRONMENT MATRIX
    # ==========================================
    pdf.chapter('App-A', 'Appendix A: Comprehensive Environment Configuration Reference')
    
    pdf.sec('A.1 Complete Environment Variable Dictionary')
    pdf.p(
        "Every environment variable supported by the Revora platform across development, testing, and production "
        "is documented below with type signatures, default fallbacks, and operational significance:"
    )
    
    env_headers = ['Variable Name', 'Type / Default', 'Operational Scope & Security Significance']
    env_rows = [
        ['API_KEY', 'str (demo-key)', 'API gateway security; required in api-key header for all protected endpoints.'],
        ['JWT_SECRET_KEY', 'str (secret)', 'Cryptographic secret key used to sign HS256 JWT access tokens.'],
        ['JWT_EXPIRE_MINUTES', 'int (30)', 'Token expiration TTL; after 30 minutes, client session must be refreshed.'],
        ['ADMIN_USERNAME', 'str (admin)', 'Bootstrap username for accessing /admin/stats and user management.'],
        ['ADMIN_PASSWORD', 'str (admin)', 'Bootstrap password; triggers startup warning if using default value.'],
        ['REDIS_URL', 'str (redis://localhost:6379)', 'Redis connection URI; defaults to localhost for dev, redis:6379 in Docker.'],
        ['MODEL_PATH', 'str (app/models/model.joblib)', 'Filesystem path to serialized HistGradientBoosting production model.'],
        ['MODEL_RANGE_PATH', 'str (app/models/model_range.joblib)', 'Filesystem path to 5th/95th percentile quantile models.'],
        ['MODEL_META_PATH', 'str (app/models/model_meta.json)', 'Metadata JSON storing training timestamp, metrics, and approach.'],
        ['USAGE_DB_PATH', 'str (logs/usage.db)', 'SQLite database tracking every prediction query for auditing and analytics.'],
        ['USERS_DB_PATH', 'str (logs/users.db)', 'SQLite database storing registered user credentials and password hashes.'],
        ['LOGIN_MAX_FAILURES', 'int (5)', 'Threshold of failed login attempts before initiating account lockout.'],
        ['LOGIN_LOCK_MINUTES', 'int (15)', 'Duration in minutes an account remains locked after reaching max failures.'],
        ['RESET_CODE_MINUTES', 'int (30)', 'Validity window for emailed 6-digit password reset verification codes.'],
        ['EMAILS_PER_USER_PER_DAY', 'int (20)', 'Rate-limiting ceiling restricting quotation sharing emails per user.'],
        ['SMTP_HOST', 'str (empty)', 'Outbound SMTP mail server hostname (e.g. smtp.gmail.com).'],
        ['SMTP_PORT', 'int (587)', 'SMTP mail server port; standard submission port with STARTTLS.'],
        ['SMTP_USERNAME', 'str (empty)', 'Authentication username / email for sending quotations.'],
        ['SMTP_PASSWORD', 'str (empty)', 'App-specific password for SMTP authentication.'],
        ['SMTP_FROM', 'str (empty)', 'Sender address displayed on quotation emails.'],
        ['BACKUP_DIR', 'str (logs/backups)', 'Destination directory for daily SQLite database snapshots.'],
        ['BACKUP_KEEP', 'int (14)', 'Retention rotation count; deletes backups older than 14 cycles.'],
        ['BACKUP_INTERVAL_HOURS', 'float (24.0)', 'Cadence interval for automated background database backups.']
    ]
    pdf.table(env_headers, env_rows, [45, 45, 90])

    # ==========================================
    # APPENDIX B: MATHEMATICAL GLOSSARY
    # ==========================================
    pdf.chapter('App-B', 'Appendix B: Mathematical Notation & Statistical Definitions')
    
    pdf.sec('B.1 Standardized Notation Dictionary')
    pdf.p(
        "Below is a reference guide to all mathematical symbols, statistical estimators, and evaluation metrics "
        "utilized throughout the Revora machine learning pipeline:"
    )
    
    math_headers = ['Symbol / Metric', 'Mathematical Definition', 'Interpretation in Revora']
    math_rows = [
        ['y', 'y in R+', 'Actual advertised vehicle listing price in Indian Rupees (INR).'],
        ['z = ln(y)', 'z in R', 'Natural logarithm of listing price; the true regression target.'],
        ['z_hat = g(x)', 'z_hat in R', 'Model raw prediction in logarithmic feature space.'],
        ['y_hat = exp(z_hat)', 'y_hat in R+', 'Exponentiated point estimate price in Indian Rupees (INR).'],
        ['MAE', '1/N sum |y_i - y_hat_i|', 'Mean Absolute Error; average absolute rupee valuation discrepancy.'],
        ['RMSE', 'sqrt(1/N sum (y_i - y_hat_i)^2)', 'Root Mean Squared Error; heavily penalizes extreme outliers.'],
        ['R^2 Score', '1 - SS_res / SS_tot', 'Coefficient of Determination (0.630 on holdout); variance explained.'],
        ['Median % Error', 'median( |y_i - y_hat_i| / y_i )', 'Median relative percentage deviation (12.4% on holdout).'],
        ['Within +/-10%', 'P( |y - y_hat|/y <= 0.10 )', 'Proportion of predictions within 10% of true price (42.3%).'],
        ['Within +/-20%', 'P( |y - y_hat|/y <= 0.20 )', 'Proportion of predictions within 20% of true price (70.5%).'],
        ['L_0.05', 'max(0.05 e, -0.95 e)', '5th percentile pinball loss for price_low lower bound.'],
        ['L_0.95', 'max(0.95 e, -0.05 e)', '95th percentile pinball loss for price_high upper bound.']
    ]
    pdf.table(math_headers, math_rows, [38, 62, 80])

    print("Appendices A and B added.")

if __name__ == '__main__':
    print("Appendices module loaded.")
