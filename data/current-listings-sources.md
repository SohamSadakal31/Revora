# Data sources and licences

Only data whose licence allows commercial (production) use is kept in this project. Nothing is scraped: public
datasets are downloaded with Kaggle's official client (`kagglehub`). This is a licence summary, not legal advice.

## Historical data - `data/car-details.csv` (and the derived `data/car-details-cleaned.csv`)

All 6,926 rows come from **"Vehicle dataset" by Nehal Birla** (`Car details v3.csv`):
https://www.kaggle.com/datasets/nehalbirla/vehicle-dataset-from-cardekho

Licence: **Open Database License (ODbL) v1.0** for the database, **Database Contents License (DbCL) v1.0** for its
contents. Commercial use is allowed. Conditions:
- **Attribution**: credit the dataset (see the notice in README.md and the app) when the data or anything produced
  from it (such as price estimates) is used publicly.
- **Share-alike**: if a modified version of the *database itself* (e.g. `car-details-cleaned.csv`) is shared
  publicly, it must be offered under ODbL. Keeping it private / only serving predictions does not require this.

## Current listings - `data/current-listings.csv`

Built by `python -m training.build_current_listings`. Every row carries `data_source` and `licence`.

| Dataset | Licence | Rows used | Listing dates |
|---|---|---|---|
| [Used Car Price Prediction](https://www.kaggle.com/datasets/vrajesh0sharma7/used-car-price-prediction) | CC0 Public Domain | 6,710 of 7,400 | 2019-08 to 2021-05 (per listing) |
| [Vehicle dataset](https://www.kaggle.com/datasets/nehalbirla/vehicle-dataset-from-cardekho) - `car details v4.csv` | ODbL v1.0 / DbCL v1.0 (attribution) | 1,966 of 2,059 | 2023-01-14 (dataset update date; no per-listing dates) |

Running the build also writes `data/current-listings-import-excluded.csv` (excluded rows + reasons) and `data/current-listings-import-report.json` (counts).

## Reviewed and not used

| Dataset | Licence | Reason |
|---|---|---|
| [Used Cars Dataset (CarDekho, 2023)](https://www.kaggle.com/datasets/sukritchatterjee/used-cars-dataset-cardekho) | CC BY-NC 4.0 | **non-commercial only** - removed, together with every model trained on it |
| [Used Cars in Cars24](https://www.kaggle.com/datasets/balajimummidi/used-cars-in-cars24) | Unknown | licence not stated |
| [Used Car Dataset](https://www.kaggle.com/datasets/mohitkumar282/used-car-dataset) (2024) | CC0 | generated values (identical 4,800 / 4,782 split in transmission and owner); no city or seller type |
| [Indian Used Cars Dataset (Enriched)](https://www.kaggle.com/datasets/vanshhala/used-car-dataset) | CC0 | same base plus generated columns; no city or seller type |
| [Indian Car Sell Dataset](https://www.kaggle.com/datasets/milapgohil/car-dataset) | Apache 2.0 | synthetic (impossible cars, e.g. a diesel Maruti Alto 'Z' at Rs 6.79 lakh) |
| [Used Car Price Data from Cars24](https://www.kaggle.com/datasets/amanrajput16/used-car-price-data-from-cars24) | Apache 2.0 | no city and no listing date (required fields) |
