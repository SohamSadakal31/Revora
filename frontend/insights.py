"""Market insights tab: descriptive statistics of the legal listing data (advertised prices, 2019-2023)."""
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
HISTORICAL_LISTING_YEAR = 2020  # the historical file has no listing dates; same assumption as model training
ACCENT = '#3b82f6'
MIN_ROWS = 30  # groups smaller than this are not shown
DISPLAY_BRAND = {'Land': 'Land Rover', 'Ashok': 'Ashok Leyland'}
DISPLAY_MODEL = {'Wagon': 'Wagon R'}


@st.cache_data(show_spinner=False)
def market_data() -> pd.DataFrame:
    """Historical + current listings in one frame with consistent spellings and the car's age when listed."""
    cols = ['company', 'model', 'year', 'km_driven', 'fuel', 'transmission', 'seller_type', 'owner',
            'selling_price', 'listing_year', 'city']
    hist = pd.read_csv(DATA_DIR / 'car-details-cleaned.csv').assign(listing_year=HISTORICAL_LISTING_YEAR)
    frames = [hist.reindex(columns=cols)]
    current_path = DATA_DIR / 'current-listings.csv'
    if current_path.exists():
        cur = pd.read_csv(current_path)
        cur['listing_year'] = pd.to_datetime(cur['listing_date']).dt.year
        frames.append(cur.reindex(columns=cols))
    df = pd.concat(frames, ignore_index=True)

    # one spelling per brand / model: the historical spelling where it exists
    brand = {b.lower(): b for b in hist['company'].unique()}
    model = {m.lower(): m for m in hist['model'].unique()}
    tidy = lambda s, known: s.astype(str).str.strip().map(  # noqa: E731
        lambda x: known.get(x.lower(), x if x != x.lower() else x.title()))
    df['company'] = tidy(df['company'], brand)
    df['model'] = tidy(df['model'], model)
    # display names only: the data splits vehicle names at the first two words ("Land" / "Rover", "Wagon" / "R ...")
    df['company'] = df['company'].replace(DISPLAY_BRAND)
    df['model'] = df['model'].replace(DISPLAY_MODEL)
    df['car'] = np.where(df['company'] == 'Land Rover', 'Land Rover', df['company'] + ' ' + df['model'])
    df['age'] = (df['listing_year'] - df['year']).clip(lower=0)
    return df[df['selling_price'] > 0]


@st.cache_data(show_spinner=False)
def yearly_value_loss(df: pd.DataFrame) -> pd.DataFrame:
    """Average % of value lost per year of age, measured within each model (so brands' model mix doesn't bias it)."""
    rows = []
    for (company, car), g in df.groupby(['company', 'car']):
        if len(g) >= MIN_ROWS and g['age'].nunique() >= 4:
            slope = np.polyfit(g['age'], np.log(g['selling_price']), 1)[0]
            rows.append((company, car, len(g), 1 - np.exp(slope)))
    per_model = pd.DataFrame(rows, columns=['company', 'car', 'listings', 'loss_per_year'])
    return per_model[per_model['loss_per_year'].between(-0.05, 0.5)]  # drop implausible fits


@st.cache_data(show_spinner=False)
def like_for_like_premiums(df: pd.DataFrame) -> pd.DataFrame:
    """Price difference between two versions of the SAME model at the SAME age (so brand / age mix can't bias it)."""
    comparisons = [('Automatic vs manual', 'transmission', 'Automatic', 'Manual'),
                   ('Diesel vs petrol', 'fuel', 'Diesel', 'Petrol'),
                   ('CNG vs petrol', 'fuel', 'CNG', 'Petrol'),
                   ('Dealer vs private seller', 'seller_type', 'Dealer', 'Individual'),
                   ('First vs second owner', 'owner', 'First', 'Second')]
    rows = []
    for label, col, a, b in comparisons:
        med = (df[df[col].isin([a, b])].groupby(['car', 'age', col])['selling_price']
               .agg(['median', 'size']).unstack(col))
        both = med.dropna()
        both = both[(both[('size', a)] >= 3) & (both[('size', b)] >= 3)]
        if len(both) >= 10:
            ratio = np.log(both[('median', a)] / both[('median', b)])
            weights = np.minimum(both[('size', a)], both[('size', b)])
            rows.append((label, float(np.exp(np.average(ratio, weights=weights)) - 1), len(both)))
    return pd.DataFrame(rows, columns=['comparison', 'difference', 'groups'])


@st.cache_data(show_spinner=False)
def _spellings() -> tuple[dict, dict]:
    hist = pd.read_csv(DATA_DIR / 'car-details-cleaned.csv', usecols=['company', 'model'])
    return ({b.lower(): DISPLAY_BRAND.get(b, b) for b in hist['company'].unique()},
            {m.lower(): DISPLAY_MODEL.get(m, m) for m in hist['model'].unique()})


def display_name(company: str, model: str) -> str:
    """'maruti', 'sx4' -> 'Maruti SX4'; 'maruti', 'wagon' -> 'Maruti Wagon R' (as spelled in the data)."""
    brands, models = _spellings()
    brand = brands.get(str(company).lower(), str(company).title())
    return 'Land Rover' if brand == 'Land Rover' else f"{brand} {models.get(str(model).lower(), str(model).title())}"


def _lakh(v: float) -> str:
    return f'₹{v / 1e5:,.2f} L'


def _style(chart, colors: dict, height: int):
    return (chart.properties(height=height, background='transparent')
            .configure_axis(labelColor=colors['text'], titleColor=colors['muted'], gridColor=colors['line'],
                            domainColor=colors['line'], tickColor=colors['line'], labelFontSize=12)
            .configure_legend(labelColor=colors['text'], titleColor=colors['muted'])
            .configure_view(strokeWidth=0))


def render(colors: dict, stats: dict | None):
    df = market_data()
    losses = yearly_value_loss(df)

    # ---- snapshot
    st.markdown('#### Market snapshot')
    k = st.columns(5)
    k[0].metric('Listings analysed', f'{len(df):,}')
    k[1].metric('Brands', df['company'].nunique())
    k[2].metric('Models', df['car'].nunique())
    k[3].metric('Median listed price', _lakh(df['selling_price'].median()))
    k[4].metric('Typical value lost / year', f"{losses['loss_per_year'].median():.1%}",
                help='Median across models: how much a car of the same model is listed for less per extra year of age.')

    # ---- model explorer
    st.markdown('#### Explore a model')
    counts = df.groupby(['company', 'car']).size()
    popular = counts[counts >= MIN_ROWS]
    brands = sorted(popular.index.get_level_values(0).unique())
    c1, c2 = st.columns(2)
    brand = c1.selectbox('Brand', brands, index=brands.index('Maruti') if 'Maruti' in brands else 0, key='ins_brand')
    cars = sorted(popular[brand].index)
    car = c2.selectbox('Model', cars, index=cars.index('Maruti Swift') if 'Maruti Swift' in cars else 0,
                       format_func=lambda x: x.split(' ', 1)[1], key='ins_model')
    g = df[df['car'] == car]
    by_age = (g.groupby('age')['selling_price'].agg(median='median', low=lambda s: s.quantile(.25),
                                                   high=lambda s: s.quantile(.75), n='size')
              .query('n >= 5').reset_index())
    loss = losses.loc[losses['car'] == car, 'loss_per_year']
    km_year = (g['km_driven'] / g['age'].clip(lower=1)).median()

    m = st.columns(4)
    m[0].metric('Listings', f'{len(g):,}')
    m[1].metric('Median listed price', _lakh(g['selling_price'].median()))
    m[2].metric('Value lost per year', f'{loss.iloc[0]:.1%}' if len(loss) else '-',
                help='Measured from this model\'s listings: the typical drop in listed price for each extra year of age.')
    m[3].metric('Typical km per year', f'{km_year:,.0f} km')

    left, right = st.columns([2, 1], gap='large')
    with left:
        st.markdown(f'**How {car} holds its value** - listed price by age (line: median; band: middle 50%)')
        if len(by_age) >= 2:
            base = alt.Chart(by_age.assign(**{c: by_age[c] / 1e5 for c in ('median', 'low', 'high')}))
            band = base.mark_area(opacity=0.25, color=ACCENT).encode(
                x=alt.X('age:Q', title='Age when listed (years)'), y=alt.Y('low:Q', title='₹ Lakh'), y2='high:Q')
            line = base.mark_line(point=True, color=ACCENT, strokeWidth=3).encode(
                x='age:Q', y='median:Q',
                tooltip=[alt.Tooltip('age:Q', title='Age (years)'), alt.Tooltip('median:Q', title='Median ₹ L', format='.2f'),
                         alt.Tooltip('low:Q', title='25th pct ₹ L', format='.2f'),
                         alt.Tooltip('high:Q', title='75th pct ₹ L', format='.2f'), alt.Tooltip('n:Q', title='Listings')])
            st.altair_chart(_style(band + line, colors, 300), use_container_width=True, theme=None)
        else:
            st.caption('Not enough listings at different ages to draw a curve.')
    with right:
        st.markdown('**Fuel and gearbox mix**')
        mix = (g.groupby(['fuel', 'transmission']).size().rename('listings').reset_index())
        chart = alt.Chart(mix).mark_bar(cornerRadiusEnd=4).encode(
            y=alt.Y('fuel:N', title=None), x=alt.X('listings:Q', title='Listings'),
            color=alt.Color('transmission:N', title='Gearbox', scale=alt.Scale(range=[ACCENT, '#f59e0b'])),
            tooltip=['fuel', 'transmission', 'listings'])
        st.altair_chart(_style(chart, colors, 300), use_container_width=True, theme=None)

    # ---- market overview
    st.markdown('#### Market overview')
    o1, o2 = st.columns(2, gap='large')
    with o1:
        st.markdown('**Value retention by brand** - value lost per year (lower is better)')
        by_brand = (losses.groupby('company')
                    .apply(lambda x: pd.Series({'loss': np.average(x['loss_per_year'], weights=x['listings']),
                                                'models': len(x), 'listings': x['listings'].sum()}))
                    .query('listings >= 200').reset_index())
        chart = alt.Chart(by_brand).mark_bar(color=ACCENT, cornerRadiusEnd=4).encode(
            x=alt.X('loss:Q', title='Value lost per year', axis=alt.Axis(format='%')),
            y=alt.Y('company:N', sort='x', title=None),
            tooltip=[alt.Tooltip('company:N', title='Brand'), alt.Tooltip('loss:Q', title='Lost / year', format='.1%'),
                     alt.Tooltip('models:Q', title='Models measured'), alt.Tooltip('listings:Q', title='Listings')])
        st.altair_chart(_style(chart, colors, 360), use_container_width=True, theme=None)
    with o2:
        st.markdown('**What changes the price** - same model, same age, compared like for like')
        prem = like_for_like_premiums(df)
        chart = alt.Chart(prem).mark_bar(cornerRadiusEnd=4).encode(
            x=alt.X('difference:Q', title='Listed price difference', axis=alt.Axis(format='+%')),
            y=alt.Y('comparison:N', sort=None, title=None),
            color=alt.condition('datum.difference >= 0', alt.value(ACCENT), alt.value('#f59e0b')),
            tooltip=[alt.Tooltip('comparison:N', title='Comparison'),
                     alt.Tooltip('difference:Q', title='Difference', format='+.1%'),
                     alt.Tooltip('groups:Q', title='Model-and-age groups compared')])
        st.altair_chart(_style(chart, colors, 360), use_container_width=True, theme=None)

    o3, o4 = st.columns(2, gap='large')
    with o3:
        st.markdown('**Typical listed price by brand** (median)')
        price = (df.groupby('company')['selling_price'].agg(median='median', n='size')
                 .query(f'n >= {MIN_ROWS}').reset_index())
        price['lakh'] = price['median'] / 1e5
        chart = alt.Chart(price).mark_bar(color=ACCENT, cornerRadiusEnd=4).encode(
            x=alt.X('lakh:Q', title='₹ Lakh'), y=alt.Y('company:N', sort='-x', title=None),
            tooltip=[alt.Tooltip('company:N', title='Brand'), alt.Tooltip('lakh:Q', title='Median ₹ L', format='.2f'),
                     alt.Tooltip('n:Q', title='Listings')])
        st.altair_chart(_style(chart, colors, 420), use_container_width=True, theme=None)
    with o4:
        st.markdown('**Most searched on this site**')
        if stats and stats.get('most_searched'):
            top = pd.DataFrame(stats['most_searched'])
            rows = ''.join(f"<tr><td>{display_name(r.company, r.model)}</td><td>{r.searches}</td>"
                           f"<td>{_lakh(r.avg_price)}</td></tr>" for r in top.itertuples())
            st.markdown(f'<table class="table"><tr><th>Car</th><th>Searches</th><th>Avg estimate</th></tr>{rows}</table>',
                        unsafe_allow_html=True)
            st.caption(f"{stats['total_searches']:,} estimates given so far.")
        else:
            st.caption('No searches yet.')

    periods = df['listing_year']
    st.caption(f'About this data: {len(df):,} advertised used-car prices (not final sale prices) from public datasets, '
               f'listed {periods.min()}-{periods.max()}. Groups with fewer than {MIN_ROWS} listings are not shown. '
               'Value lost per year is measured within each model from listings of different ages.')
