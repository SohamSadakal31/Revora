import os
from fpdf.enums import XPos, YPos

def add_chapters_39_to_40(pdf):
    # ==========================================
    # CHAPTER 39: COMPARATIVE CASE STUDY
    # ==========================================
    pdf.chapter('39', 'Comparative Case Study: Maruti Swift vs. Hyundai i20 vs. Tata Altroz')
    
    pdf.sec('39.1 Scenario Setup: 3-Way Used Hatchback Showdown')
    pdf.p(
        "To illustrate the multi-car comparison engine in action, consider a prospective buyer evaluating three competing "
        "2019 premium hatchbacks in the secondary market, all configured as Manual Petrol variants driven 40,000 km "
        "under First Ownership, listed by Individual Private Sellers:"
    )
    
    comp_headers = ['Metric / Specification', 'Car 1: Maruti Swift VXI', 'Car 2: Hyundai i20 Magna', 'Car 3: Tata Altroz XT']
    comp_rows = [
        ['Manufacturing Year', '2019', '2019', '2019'],
        ['Odometer Reading', '40,000 km', '40,000 km', '40,000 km'],
        ['Fuel & Transmission', 'Petrol * Manual', 'Petrol * Manual', 'Petrol * Manual'],
        ['Engine Displacement', '1197 cc (4-Cyl K12)', '1197 cc (4-Cyl Kappa)', '1199 cc (3-Cyl Revotron)'],
        ['Power & Torque', '82 bhp / 113 Nm', '82 bhp / 114 Nm', '85 bhp / 113 Nm'],
        ['Claimed Mileage', '50.2 mpg (21.3 km/l)', '43.5 mpg (18.5 km/l)', '44.7 mpg (19.0 km/l)'],
        ['Revora Point Estimate', 'INR 5,12,400.00', 'INR 4,88,200.00', 'INR 4,65,700.00'],
        ['Confidence Bounds', 'INR 4.62L - 5.75L', 'INR 4.38L - 5.42L', 'INR 4.18L - 5.15L'],
        ['5-Year Depreciation Rate', '8.4% per annum', '9.8% per annum', '11.2% per annum'],
        ['Projected 1-Yr Value', 'INR 4,75,000.00', 'INR 4,45,000.00', 'INR 4,18,000.00'],
        ['Projected 3-Yr Value', 'INR 4,05,000.00', 'INR 3,68,000.00', 'INR 3,35,000.00'],
        ['Asking Price Verdict', 'Great Deal at <= 4.90L', 'Fair Deal at <= 5.05L', 'High if >= 4.90L']
    ]
    pdf.table(comp_headers, comp_rows, [44, 46, 46, 44])

    pdf.sec('39.2 Valuation Divergence Analysis')
    pdf.p(
        "Why does the Maruti Swift command a +INR 24,200 premium over the Hyundai i20 and +INR 46,700 over the Tata Altroz "
        "despite identical mechanical horsepower and odometer readings? Revora's gradient boosting model reflects three "
        "empirical macroeconomic market realities:"
    )
    pdf.bullet("Brand Equity Liquidity Premium", "Maruti Suzuki maintains the highest resale velocity in India, with transactions closing in an average of 11 days versus 24 days for Tata hatchbacks.")
    pdf.bullet("Fuel Economy Sensitivity", "The Swift's 50.2 mpg economy creates an ongoing operational savings advantage of ~INR 14,000 annually over 10,000 km, capitalized into the purchase price.")
    pdf.bullet("Long-Term Reliability Perception", "4-cylinder naturally aspirated engines maintain higher 5-year trade-in values than 3-cylinder powerplants in Indian secondary markets.")

    # ==========================================
    # CHAPTER 40: ENTERPRISE PRODUCTION RUNBOOK
    # ==========================================
    pdf.chapter('40', 'Enterprise Production Deployment Runbook & Cloud Scaling')
    
    pdf.sec('40.1 Zero-Downtime Deployment Playbook')
    pdf.p(
        "For enterprise production deployments across cloud virtual machines (AWS EC2, GCP Compute Engine, DigitalOcean), "
        "execute the following zero-downtime operational playbook:"
    )
    pdf.code(
        "# 1. Clone repository and verify environment secrets\n"
        "git clone https://github.com/organization/revora.git\n"
        "cd revora\n"
        "cp .env.example .env\n"
        "# Ensure API_KEY, JWT_SECRET_KEY, and ADMIN_PASSWORD are strong random strings\n\n"
        "# 2. Build multi-service container images\n"
        "docker compose build\n\n"
        "# 3. Launch the container stack with automated HTTPS via Caddy\n"
        "docker compose --profile https up -d\n\n"
        "# 4. Verify system health and metrics exposition\n"
        "curl -f http://127.0.0.1:8000/health\n"
        "curl -f http://127.0.0.1:8000/metrics | grep http_requests_total"
    )

    pdf.sec('40.2 SSL/TLS Hardening via Caddy (Caddyfile)')
    pdf.p(
        "The included Caddyfile provisions automatic TLS certificates via Let's Encrypt or ZeroSSL, terminating SSL "
        "at the edge and routing clean HTTP traffic to the internal frontend container on port 8501:"
    )
    pdf.code(
        "# Caddyfile Configuration\n"
        "{$DOMAIN:localhost} {\n"
        "    reverse_proxy frontend:8501 {\n"
        "        header_up Host {host}\n"
        "        header_up X-Real-IP {remote_host}\n"
        "    }\n"
        "    encode gzip zstd\n"
        "    header {\n"
        "        Strict-Transport-Security \"max-age=31536000; includeSubDomains; preload\"\n"
        "        X-Content-Type-Options nosniff\n"
        "        X-Frame-Options SAMEORIGIN\n"
        "    }\n"
        "}"
    )

    pdf.sec('40.3 Concluding Engineering Summary')
    pdf.p(
        "This concludes the complete 40-chapter architectural, statistical, and operational specification for the "
        "Revora Used Car Price Estimator platform. The system successfully combines institutional-grade statistical rigor, "
        "monotonic economic guardrails, modern microservices architecture, and comprehensive continuous testing."
    )

    pdf.callout(
        "Document Delivery Complete",
        "Total Chapters: 40  *  Total Test Cases: 140  *  Dataset: 15,602 Listings  *  Model Version: 0c200809.\n"
        "This PDF represents an exhaustive, ground-truth technical manual designed specifically for AI pair programmers, "
        "ChatGPT context ingestion, and enterprise software engineering teams.",
        bg=(236, 253, 245), border=(167, 243, 208), title_color=(22, 101, 52)
    )

    print("Chapters 39 and 40 added.")

if __name__ == '__main__':
    print("Part 9 module loaded.")
