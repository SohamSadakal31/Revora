# Current-market experiment

Created 2026-09-30T09:53:28+00:00. Offline only - production model unchanged.

## Data
- Historical rows: 6,926 (listing year 2020 - UNCONFIRMED ASSUMPTION)
- Historical dataset: `data/car-details-cleaned.csv`
- Current rows: 8,676 valid / 8,676 (2019-08-21 to 2023-01-14)
- Current training: 6,939 (up to 2023-01-14)
- Current holdout: 1,737 (2023-01-14 to 2023-01-14)

## Results on the current holdout

| Experiment | Training rows | MAE | RMSE | R² | Median abs error | Median % error | ±10% | ±20% |
|---|---|---|---|---|---|---|---|---|
| A_historical | 6,926 | ₹500,159 | ₹1,489,226 | 0.5505 | ₹160,417 | 22.9% | 16.2% | 41.5% |
| B_historical_current | 13,865 | ₹388,064 | ₹1,340,260 | 0.6359 | ₹89,964 | 11.8% | 42.0% | 71.0% |
| C_weighted | 13,865 | ₹398,762 | ₹1,352,059 | 0.6295 | ₹89,161 | 12.4% | 42.3% | 70.5% |

EXPLORATORY_* rows are a separate experiment, not part of the A/B/C comparison.

## Leakage audit
- PASS: current holdout never entered training
- PASS: current holdout never entered spec lookup
- PASS: current holdout never influenced preprocessing
- PASS: current holdout never influenced hyperparameters
- PASS: current holdout never influenced sample weights
- PASS: target price was not used for spec enrichment
- PASS: no future listing information leaked into training
- PASS: duplicate listings did not cross train/holdout
- PASS: test metrics calculated only after predictions were generated
- PASS: historical data contains no target leakage

## Breakdown - A_historical
**price_bucket**: <2L (n=49): median 23.4%, ±20% 41%; 2-5L (n=449): median 23.7%, ±20% 40%; 5-10L (n=517): median 21.0%, ±20% 45%; 10-20L (n=337): median 22.7%, ±20% 42%; >20L (n=385): median 27.2%, ±20% 38%
**company**: audi (n=96): median 23.8%, ±20% 40%; bmw (n=104): median 19.0%, ±20% 51%; ford (n=41): median 15.1%, ±20% 71%; honda (n=133): median 20.9%, ±20% 46%; hyundai (n=313): median 21.2%, ±20% 44%; kia (n=21): median 30.4%, ±20% 29%; land (n=29): median 46.2%, ±20% 3%; mahindra (n=106): median 17.7%, ±20% 59%; maruti (n=374): median 23.8%, ±20% 38%; mercedes-benz (n=140): median 36.0%, ±20% 23%; renault (n=36): median 22.8%, ±20% 44%; skoda (n=34): median 33.4%, ±20% 29%; tata (n=39): median 22.7%, ±20% 38%; toyota (n=110): median 17.1%, ±20% 58%; volkswagen (n=43): median 26.6%, ±20% 33%
**age_bucket**: 0-3y (n=286): median 19.5%, ±20% 51%; 4-6y (n=626): median 19.8%, ±20% 50%; 7-10y (n=598): median 25.6%, ±20% 35%; 11-15y (n=217): median 31.9%, ±20% 22%
**fuel**: cng (n=45): median 28.8%, ±20% 13%; diesel (n=896): median 20.5%, ±20% 47%; petrol (n=790): median 24.3%, ±20% 37%

## Breakdown - B_historical_current
**price_bucket**: <2L (n=49): median 32.8%, ±20% 24%; 2-5L (n=449): median 10.4%, ±20% 76%; 5-10L (n=517): median 10.2%, ±20% 83%; 10-20L (n=337): median 11.8%, ±20% 72%; >20L (n=385): median 17.5%, ±20% 55%
**company**: audi (n=96): median 11.4%, ±20% 70%; bmw (n=104): median 16.8%, ±20% 57%; ford (n=41): median 14.5%, ±20% 68%; honda (n=133): median 9.0%, ±20% 83%; hyundai (n=313): median 8.7%, ±20% 84%; kia (n=21): median 20.9%, ±20% 48%; land (n=29): median 25.6%, ±20% 21%; mahindra (n=106): median 11.1%, ±20% 68%; maruti (n=374): median 10.9%, ±20% 80%; mercedes-benz (n=140): median 15.4%, ±20% 60%; renault (n=36): median 14.4%, ±20% 58%; skoda (n=34): median 15.0%, ±20% 68%; tata (n=39): median 11.4%, ±20% 77%; toyota (n=110): median 12.6%, ±20% 71%; volkswagen (n=43): median 14.7%, ±20% 65%
**age_bucket**: 0-3y (n=286): median 12.4%, ±20% 67%; 4-6y (n=626): median 11.1%, ±20% 76%; 7-10y (n=598): median 11.0%, ±20% 73%; 11-15y (n=217): median 17.0%, ±20% 60%
**fuel**: cng (n=45): median 10.3%, ±20% 82%; diesel (n=896): median 12.8%, ±20% 68%; petrol (n=790): median 10.9%, ±20% 74%

## Breakdown - C_weighted
**price_bucket**: <2L (n=49): median 31.7%, ±20% 22%; 2-5L (n=449): median 10.6%, ±20% 76%; 5-10L (n=517): median 10.5%, ±20% 81%; 10-20L (n=337): median 11.1%, ±20% 72%; >20L (n=385): median 18.4%, ±20% 54%
**company**: audi (n=96): median 12.9%, ±20% 70%; bmw (n=104): median 17.2%, ±20% 55%; ford (n=41): median 14.7%, ±20% 61%; honda (n=133): median 10.2%, ±20% 83%; hyundai (n=313): median 8.2%, ±20% 83%; kia (n=21): median 18.4%, ±20% 57%; land (n=29): median 33.5%, ±20% 28%; mahindra (n=106): median 11.4%, ±20% 74%; maruti (n=374): median 11.4%, ±20% 78%; mercedes-benz (n=140): median 16.2%, ±20% 62%; renault (n=36): median 13.4%, ±20% 61%; skoda (n=34): median 16.5%, ±20% 59%; tata (n=39): median 13.3%, ±20% 72%; toyota (n=110): median 13.7%, ±20% 68%; volkswagen (n=43): median 17.4%, ±20% 63%
**age_bucket**: 0-3y (n=286): median 13.2%, ±20% 68%; 4-6y (n=626): median 10.7%, ±20% 75%; 7-10y (n=598): median 11.6%, ±20% 73%; 11-15y (n=217): median 17.5%, ±20% 56%
**fuel**: cng (n=45): median 13.4%, ±20% 78%; diesel (n=896): median 13.1%, ±20% 68%; petrol (n=790): median 11.7%, ±20% 73%
