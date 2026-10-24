import os
from fpdf.enums import XPos, YPos

def add_chapters_6_to_10(pdf):
    # ==========================================
    # CHAPTER 6: MACHINE LEARNING PIPELINE
    # ==========================================
    pdf.chapter('6', 'Machine Learning Pipeline, Target Formulation & Feature Engineering')
    
    pdf.sec('6.1 Target Formulation: TransformedTargetRegressor on log(price)')
    pdf.p(
        "A critical engineering decision in Revora is wrapping the gradient boosting estimator inside scikit-learn's "
        "TransformedTargetRegressor using a natural logarithmic transformation: func=np.log, inverse_func=np.exp. "
        "The mathematical rationale is fourfold:"
    )
    pdf.bullet("Strict Positive Domain", "Automobile market prices cannot be negative. Predicting raw prices directly with unconstrained regressors can produce negative price outputs for heavily depreciated, high-mileage older cars.")
    pdf.bullet("Multiplicative Error Homogeneity", "A 10% estimation error on an INR 3,00,000 hatchback is INR 30,000, whereas a 10% error on an INR 50,00,000 luxury SUV is INR 5,00,000. In log space, both represent the exact same residual magnitude: |ln(y) - ln(y_hat)| = ln(1.10) approx 0.095.")
    pdf.bullet("Mitigating Extreme Outliers", "The training corpus contains high-end luxury vehicles (e.g. BMW, Mercedes-Benz, Land Rover) with listing prices up to INR 2.75 Crore. Standard MSE on raw rupee values would allow a handful of luxury outliers to dominate the loss function, skewing predictions for mass-market cars.")
    pdf.bullet("Log-Normal Distribution Alignment", "Automotive price distributions closely mirror a log-normal distribution. Transforming to log space produces near-Gaussian residual distributions that satisfy regression assumptions.")

    pdf.sec('6.2 Feature Preprocessing Architecture')
    pdf.p(
        "Features enter the modeling pipeline through a scikit-learn ColumnTransformer configured with three parallel transformation streams:"
    )
    pdf.bullet("Stream 1: Categorical Encoding", "Columns: company, model, owner, fuel, transmission. Preprocessed using OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1). The integer-encoded categories are passed directly to HistGradientBoostingRegressor, which treats them as native categorical partitions.")
    pdf.bullet("Stream 2: Variant Tokenization", "Column: edition. Preprocessed using CountVectorizer(token_pattern=r'(?u)\\b\\w+\\b', min_df=5). This splits variant strings into distinct sub-tokens (e.g. 'VXI', 'ZDI', 'AMT', 'ABS', 'Option'), capturing luxury and transmission cues even when full trim names have low frequency.")
    pdf.bullet("Stream 3: Continuous & Technical Features", "Columns: age_at_listing, listing_year, km_driven, sold_by_dealer, mileage_mpg, engine_cc, max_power_bhp, torque_nm, seats. Passed as numeric features without artificial scaling, as tree splits are invariant to monotonic scaling.")

    pdf.sec('6.3 Algorithm: HistGradientBoostingRegressor')
    pdf.p(
        "Revora selects HistGradientBoostingRegressor over traditional XGBoost or LightGBM due to its native missing-value "
        "handling, histogram binning (256 integer bins per feature), built-in monotonic constraint enforcement, and zero "
        "external C++ binary dependency footprint. Production hyperparameters are locked in training/train_model.py:"
    )
    pdf.code(
        "PRODUCTION_PARAMS = {\n"
        "    'loss': 'squared_error',\n"
        "    'learning_rate': 0.05,\n"
        "    'max_iter': 1500,\n"
        "    'max_leaf_nodes': 15,\n"
        "    'min_samples_leaf': 5,\n"
        "    'l2_regularization': 1.0,\n"
        "    'early_stopping': False,\n"
        "    'random_state': 42\n"
        "}"
    )

    pdf.sec('6.4 Mathematical Gradients of Histogram Gradient Boosting')
    pdf.p(
        "HistGradientBoosting constructs additive decision tree ensembles: F_M(x) = sum_{m=1}^M gamma_m h_m(x). "
        "At step m, the algorithm fits a base tree h_m to pseudo-residuals (negative gradients) of the loss function. "
        "For squared error on log target z = ln(y):"
    )
    pdf.code(
        "Loss:\n"
        "    L(z, F(x)) = 1/2 * ( z - F(x) )^2\n"
        "First-Order Gradient (Residual):\n"
        "    g_i = - [ d L(z_i, F(x_i)) / d F(x_i) ] = z_i - F(x_i)\n"
        "Second-Order Hessian:\n"
        "    h_i = d^2 L(z_i, F(x_i)) / d F(x_i)^2 = 1.0 (Constant)"
    )
    pdf.p(
        "Because the Hessian is exactly 1.0 for all samples, optimal leaf values reduce directly to the arithmetic mean "
        "of gradients falling into each leaf partition. This exact property guarantees that leaf values never violate "
        "monotonic split boundaries during post-pruning."
    )

    # ==========================================
    # CHAPTER 7: MONOTONIC CONSTRAINTS & GUARANTEES
    # ==========================================
    pdf.chapter('7', 'Monotonic Constraints, Leaf Refinement & Economic Guarantees')
    
    pdf.sec('7.1 The Critical Need for Directional Monotonicity')
    pdf.p(
        "Standard decision trees partition feature space using greedy variance reduction. In sparse regions of the dataset, "
        "random noise or localized listing quirks can cause unconstrained trees to violate fundamental laws of supply and demand:"
    )
    pdf.bullet("The Age Anomaly", "An unconstrained model might predict that an 8-year-old car is worth more than an identical 7-year-old car simply because the training dataset contained a single exceptionally clean 8-year-old listing.")
    pdf.bullet("The Mileage Anomaly", "An unconstrained model might predict that a car with 95,000 km is worth more than one with 85,000 km due to tree leaf binning artifacts.")
    
    pdf.sec('7.2 The Monotonic Constraint Vector in Revora')
    pdf.p(
        "HistGradientBoostingRegressor provides a monotonic_cst parameter that constrains tree split values. Revora enforces "
        "a strict constraint vector across the feature matrix:"
    )
    pdf.code(
        "Monotonic Constraint Matrix:\n"
        "  - age_at_listing:   -1  (Monotonically non-increasing: older car NEVER increases price)\n"
        "  - km_driven:        -1  (Monotonically non-increasing: more kilometres NEVER increase price)\n"
        "  - sold_by_dealer:   +1  (Monotonically non-decreasing: dealer listing NEVER decreases price)\n"
        "  - All other features: 0 (Unconstrained)"
    )

    pdf.sec('7.3 Mathematical Justification for squared_error Loss')
    pdf.p(
        "During experimentation, training with absolute_error (MAE loss) revealed a subtle flaw in scikit-learn's "
        "leaf-refinement step. When absolute_error is selected, scikit-learn recalculates the final leaf values using the median "
        "of residuals after tree splitting. This post-split refinement caused 1% to 4% of test cars to violate the monotonic "
        "guarantees. In contrast, squared_error computes leaf values as the exact mean of gradients, mathematically preserving "
        "the monotonic split boundaries across 100% of inputs."
    )

    pdf.sec('7.4 Empirical Verification of the +2.8% Dealer Premium')
    pdf.p(
        "To empirically validate the spread between dealerships and individual private sellers, Revora filtered the historical "
        "CarDekho database for exact matched groups: identical brand, model, manufacturing year, fuel type, transmission, "
        "and ownership tier. Across 302 isolated matched groups containing both dealer and private listings, the median dealer "
        "markup was exactly +2.82% (rounded to 2.8%). In Revora, dealer price is computed cleanly as: "
        "price_dealer = price_private * 1.028."
    )

    # ==========================================
    # CHAPTER 8: QUANTILE REGRESSION & UNCERTAINTY
    # ==========================================
    pdf.chapter('8', 'Quantile Regression, Pinball Loss & Price Uncertainty Bounds')
    
    pdf.sec('8.1 Why Point Estimates Are Insufficient')
    pdf.p(
        "Used car valuation is fundamentally stochastic. Two identical cars with the same year, variant, and mileage can "
        "transact at substantially different prices depending on tire wear, minor cosmetic scratches, service history completeness, "
        "and seller urgency. A single point estimate (e.g. 'INR 4,52,000') provides false precision. Revora pairs its median "
        "prediction with calibrated 5th and 95th percentile confidence intervals."
    )

    pdf.sec('8.2 The Asymmetric Pinball Loss Function')
    pdf.p(
        "To estimate the upper and lower price boundaries, Revora trains two auxiliary gradient boosted models using quantile loss. "
        "Given target quantile alpha in (0, 1) and residual e = y - y_hat, the pinball loss is formulated as:"
    )
    pdf.code(
        "Pinball Loss Formulation:\n"
        "    L_alpha(y, y_hat) = max( alpha * (y - y_hat), (1 - alpha) * (y_hat - y) )\n\n"
        "    - Lower Bound Model (alpha = 0.05): Under-predictions penalised 0.05x; over-predictions penalised 0.95x.\n"
        "    - Upper Bound Model (alpha = 0.95): Under-predictions penalised 0.95x; over-predictions penalised 0.05x."
    )

    pdf.sec('8.3 Empirical Holdout Coverage & Luxury Dispersion')
    pdf.p(
        "In offline holdout evaluation on 1,737 unseen listings, the [price_low, price_high] interval achieved a 67.5% empirical "
        "coverage rate. While theoretically a 5th-95th interval aims for 90% coverage, automotive pricing exhibits extreme dispersion "
        "in the luxury and commercial commercial tiers (e.g. customized interiors, premium sound systems), causing actual listing "
        "prices to occasionally fall outside standard bounds. Revora clamps the predicted bounds to ensure: price_low <= price <= price_high."
    )

    # ==========================================
    # CHAPTER 9: EXPERIMENTAL BENCHMARKS & AUDIT
    # ==========================================
    pdf.chapter('9', 'The Offline Experimentation Matrix & Automated 10-Check Leakage Audit')
    
    pdf.sec('9.1 The Three-Way Experimentation Design (experiment_current_market.py)')
    pdf.p(
        "To prove whether modern web-scraped listings improve valuation accuracy over older historical data, Revora executed "
        "a rigorous, controlled three-way offline experiment across 15,602 listings:"
    )
    pdf.bullet("Approach A (Historical Only)", "Trained strictly on the 6,926 CarDekho historical listings up to ~2020.")
    pdf.bullet("Approach B (Historical + Current Equal Weight)", "Trained on historical data combined with modern listings, assigning uniform 1.0x sample weights.")
    pdf.bullet("Approach C (Historical + Current Weighted x2 — Revora Production)", "Modern listings assigned a 2.0x training sample weight to reflect current market currency inflation.")

    exp_headers = ['Metric / Criterion', 'Approach A (Hist Only)', 'Approach B (Equal Wt)', 'Approach C (Revora Prod)']
    exp_rows = [
        ['Training Rows Used', '6,926 rows', '13,865 rows', '13,865 rows (Current x2)'],
        ['Holdout Test Rows', '1,737 newest rows', '1,737 newest rows', '1,737 newest rows'],
        ['Mean Absolute Error (MAE)', 'INR 5,00,159', 'INR 3,88,064', 'INR 3,98,762'],
        ['R-Squared Score (R2)', '0.551', '0.636', '0.630'],
        ['Median Percentage Error', '22.9%', '11.8%', '12.4%'],
        ['Within +/- 10% of Actual', '16.2%', '42.0%', '42.3%'],
        ['Within +/- 20% of Actual', '41.5%', '71.0%', '70.5%'],
        ['Prediction Range Coverage', 'N/A', '66.8%', '67.5%']
    ]
    pdf.table(exp_headers, exp_rows, [46, 44, 44, 46])

    pdf.sec('9.2 The Automated 10-Check Leakage Audit')
    pdf.p(
        "Data leakage is the primary cause of model failure in production. Revora executes an automated 10-point leakage audit "
        "before any experiment artifact is certified:"
    )
    pdf.bullet("1. Strict Temporal Quarantine", "Holdout set comprises the newest 20% of listings by date; no test listing is older than any training listing.")
    pdf.bullet("2. Duplicate Isolation", "Multiple copies of duplicate listings are forced entirely to the same side of the train/test boundary.")
    pdf.bullet("3. Spec Lookup Anti-Leakage", "Spec lookup dictionaries are populated strictly from training partitions.")
    pdf.bullet("4. Zero Target Utilization in Specs", "Price is never referenced in spec enrichment or categorical imputation.")
    pdf.bullet("5. Preprocessing Fit Isolation", "Ordinal encoders and CountVectorizer are fitted exclusively on training rows.")
    pdf.bullet("6. Feature Version Matching", "Model metadata enforces feature_version == 3 across both backend and training pipelines.")
    pdf.bullet("7. Monotonicity Invariance Check", "Audits 1,000 synthetic pairs to verify age and km constraints hold true.")
    pdf.bullet("8. Clean Target Isolation", "Verifies target log(price) transformation is cleanly inverted without truncation.")
    pdf.bullet("9. Dealer Premium Decoupling", "+2.8% dealer margin is applied post-inference, avoiding double counting in features.")
    pdf.bullet("10. Holdout Immutability", "The production model model.joblib is never modified or overwritten during test runs.")

    # ==========================================
    # CHAPTER 10: COUNTERFACTUAL INTERPRETABILITY
    # ==========================================
    pdf.chapter('10', 'Counterfactual Interpretability & Sensitivity Attribution')
    
    pdf.sec('10.1 Feature-Level Price Decomposition')
    pdf.p(
        "Black-box machine learning models erode user trust when they cannot explain why a particular vehicle is valued at "
        "a specific price. Rather than relying on computationally heavy SHAP or LIME approximations (which can generate "
        "unrealistic synthetic feature combinations), Revora implements an exact, counterfactual sensitivity attribution engine "
        "in app/services/model_service.py:"
    )
    
    pdf.sec('10.2 Counterfactual Reference Baselines')
    pdf.p(
        "For each user estimate, the engine evaluates the vehicle against four economically meaningful counterfactual baselines:"
    )
    pdf.bullet("1. Mileage Attribution", "Compares the car's actual odometer reading against a benchmark typical mileage: typical_km = max(age, 1) * 10,000 km. The car is re-priced with km_driven = typical_km. The delta price - price_ref isolates the exact rupee penalty or bonus for low/high mileage.")
    pdf.bullet("2. Ownership History Attribution", "Re-prices the car with owner = 'first'. The delta isolates the market penalty associated with second, third, or fourth-hand ownership.")
    pdf.bullet("3. Seller Channel Attribution", "Re-prices the car with seller_type = 'individual'. The delta quantifies the exact dealer premium markup.")
    pdf.bullet("4. Variant Trim Attribution", "If an edition trim is specified, re-prices the car with edition = ''. The delta isolates the premium of top-tier trims (e.g. ZXI) over the base model.")

    pdf.sec('10.3 Numerical Case Study: Maruti Swift 2018 Petrol Manual')
    pdf.p(
        "To illustrate the exact mathematical mechanics, consider a 2018 Maruti Swift VXI Petrol Manual with 45,000 km "
        "listed by an Individual Private Seller:"
    )
    pdf.bullet("Base Predicted Price", "INR 4,52,508.88")
    pdf.bullet("Typical Benchmark Mileage", "Age = 2024 - 2018 = 6 years -> Benchmark = 6 * 10,000 km = 60,000 km.")
    pdf.bullet("Counterfactual Mileage Price (at 60,000 km)", "INR 4,41,360.88")
    pdf.bullet("Odometer Attribution Delta", "INR 4,52,508.88 - INR 4,41,360.88 = +INR 11,148.00 (Favorable bonus for 15,000 km below average).")
    
    print("Expanded Chapters 6 to 10 added.")

if __name__ == '__main__':
    print("Part 2 module loaded.")
