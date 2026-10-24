import os
import sys
from datetime import datetime
from pdf_builder_core import RevoraSystemGuide
from fpdf.enums import XPos, YPos

def build_pdf():
    pdf = RevoraSystemGuide()
    pdf.alias_nb_pages()
    
    # ==========================================
    # PAGE 1: COVER PAGE
    # ==========================================
    pdf.add_page()
    pdf.set_fill_color(30, 58, 138) # Navy #1e3a8a
    pdf.rect(15, 16, 180, 55, style='F')
    
    pdf.set_xy(22, 23)
    pdf.set_font('Helvetica', 'B', 26)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, 'REVORA', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_xy(22, 35)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(191, 219, 254)
    pdf.cell(0, 7, 'Used Car Valuation & Market Intelligence Platform', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_xy(22, 45)
    pdf.set_font('Helvetica', '', 9.5)
    pdf.set_text_color(226, 232, 240)
    pdf.cell(0, 6, 'Complete Architectural, Algorithmic, and Systems Engineering Specification', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_xy(22, 53)
    pdf.set_font('Helvetica', 'I', 8.5)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5, f'A Deep-Dive Guide for AI Models, Engineers & Technical Reviewers  *  {datetime.now().strftime("%B %Y")}', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_y(80)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, 'EXECUTIVE SYSTEM ABSTRACT', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)
    
    pdf.p(
        "Revora is an enterprise-grade, end-to-end Machine Learning web platform designed to eliminate information "
        "asymmetry and price opacity in the Indian used car market. Estimating the accurate, fair transaction price of "
        "a pre-owned car involves multiple non-linear and interacting variables: steep initial depreciation curves, "
        "odometer mileage penalties, trim-level spec variations, fuel-type market transitions (Diesel vs. Petrol vs. CNG/EV), "
        "ownership history, seller channel markups (dealerships vs. private sellers), and inflation between listing years."
    )
    pdf.p(
        "This specification documents every architectural layer, statistical formulation, machine learning algorithm, "
        "REST API contract, database schema, frontend rendering engine, and automated validation suite powering Revora. "
        "It serves as a single source of truth for AI agents (such as ChatGPT), software architects, data scientists, "
        "and DevOps engineers seeking an exhaustive, line-by-line understanding of the entire codebase."
    )
    
    pdf.callout(
        "System Highlights at a Glance",
        "- Core Model: Histogram-based Gradient Boosting (HistGradientBoostingRegressor) trained on log(price) with exact monotonic constraints.\n"
        "- Uncertainty Estimation: Dual 5th & 95th percentile quantile gradient-boosted regressors producing calibrated price ranges.\n"
        "- Dataset: 15,602 verified Indian vehicle listings across two distinct temporal eras (historical + current) weighted x2.\n"
        "- Backend & Frontend: Asynchronous FastAPI (Python 3.10) paired with an interactive, responsive Streamlit dashboard.\n"
        "- Enterprise Rigor: 140 passing automated unit & integration tests, 10-check automated data leakage audit, dual SQLite DBs, and Redis caching."
    )
    
    # Metadata table
    meta_headers = ['Document Attribute', 'Specification Detail']
    meta_rows = [
        ['Platform Name', 'Revora — Used Car Price Estimator & Market Intelligence Platform'],
        ['Target Audience', 'ChatGPT, LLM Context Windows, ML Engineers, System Architects'],
        ['Core Frameworks', 'FastAPI 0.110, Streamlit 1.39, Scikit-Learn 1.3.2, Uvicorn, Pydantic v2'],
        ['Storage & Caching', 'SQLite3 (Dual DB Pattern), Redis 8-Alpine (with offline circuit breaker)'],
        ['Infrastructure', 'Docker Compose (7 Services), Prometheus, Grafana, Caddy (Optional HTTPS)'],
        ['Automated Test Suite', '140 Tests (100% Passed across 11 Test Modules)'],
        ['Repository Version', 'Git Head Commit 0c200809 (Production Approach C)']
    ]
    pdf.table(meta_headers, meta_rows, [55, 125])
    
    # ==========================================
    # PAGES 2-3: TABLE OF CONTENTS
    # ==========================================
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 8, 'Table of Contents', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)
    
    toc_items = [
        ("Chapter 1: Automotive Economics, Price Opacity & Mathematical Problem Formulation", 4),
        ("Chapter 2: Full-Stack Microservices Architecture & System Topography", 6),
        ("Chapter 3: Complete Repository Architecture & File Walkthrough", 8),
        ("Chapter 4: Data Engineering, Cleansing & Multi-Source Dataset Provenance", 11),
        ("Chapter 5: Spec Enrichment & Cross-Variant Attribute Matching", 13),
        ("Chapter 6: Machine Learning Pipeline, Target Formulation & Feature Engineering", 15),
        ("Chapter 7: Monotonic Constraints, Leaf Refinement & Economic Guarantees", 18),
        ("Chapter 8: Quantile Regression, Pinball Loss & Price Uncertainty Bounds", 20),
        ("Chapter 9: The Offline Experimentation Matrix & Automated 10-Check Leakage Audit", 22),
        ("Chapter 10: Counterfactual Interpretability & Sensitivity Attribution", 25),
        ("Chapter 11: Multi-Year Value Depreciation Forecasting Algorithm", 27),
        ("Chapter 12: FastAPI REST API Engine & Request Lifecycle", 29),
        ("Chapter 13: Schema Validation, Type Systems & Pydantic V2 Integrity", 32),
        ("Chapter 14: Authentication, Cryptographic Security & Session Lifecycle", 34),
        ("Chapter 15: Dual-Database SQLite Architecture & Audit Persistence", 36),
        ("Chapter 16: Redis High-Throughput Caching & Circuit-Breaker Resilience", 38),
        ("Chapter 17: Streamlit Frontend Architecture, Theming Engine & CSS Injection", 40),
        ("Chapter 18: Vega-Lite Market Analytics, Altair Charts & PyArrow Buffers", 43),
        ("Chapter 19: Quotation Document Generation Engine & Numbering Algorithms", 45),
        ("Chapter 20: DevOps, Multi-Service Containerization & Observability", 47),
        ("Chapter 21: Test Engineering & Pytest Suite Breakdown (140 Test Cases)", 49),
        ("Chapter 22: Complete JSON API Schemas & Database DDL Reference", 51),
        ("Chapter 23: Complete System Prompt & Knowledge Base for ChatGPT", 53),
    ]
    
    for title, pg in toc_items[:12]:
        pdf.set_font('Helvetica', 'B', 8.5)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(165, 5.2, title, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(15, 5.2, str(pg), align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(241, 245, 249)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(0.8)
        
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 8, 'Table of Contents (Continued)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)
    
    for title, pg in toc_items[12:]:
        pdf.set_font('Helvetica', 'B', 8.5)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(165, 5.2, title, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(15, 5.2, str(pg), align='R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(241, 245, 249)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(0.8)
        
    print("Cover and TOC generated.")
    return pdf

if __name__ == '__main__':
    pdf = build_pdf()
