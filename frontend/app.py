import os
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import altair as alt
import streamlit as st
import account
import insights
from quote_pdf import build_comparison, build_quote, comparison_number, quote_number

API_URL = os.getenv('API_URL', 'http://localhost:8000')
API_KEY = os.getenv('API_KEY', 'demo-key')
# cleaned copy: unusable mileage values (CNG/LPG, zeros) are missing instead of wrong
DATA_PATH = Path(__file__).resolve().parent.parent / 'data' / 'car-details-cleaned.csv'
CURRENT_PATH = DATA_PATH.parent / 'current-listings.csv'

st.set_page_config(page_title='Revora — Used Car Price Estimator', page_icon='🚗', layout='wide')

THEMES = {
    'light': {'bg': '#ffffff', 'text': '#0f172a', 'field': '#f1f5f9', 'field-hover': '#e2e8f0',
              'line': '#e2e8f0', 'surface': '#f0f7ff', 'border': '#bfdbfe', 'label': '#475569',
              'accent': '#1e3a8a', 'body': '#334155', 'muted': '#64748b', 'hero-from': '#1e3a8a',
              'hero-to': '#2563eb', 'hero-sub': '#dbeafe', 'good-bg': '#dcfce7', 'good-fg': '#166534',
              'fair-bg': '#e0f2fe', 'fair-fg': '#075985', 'high-bg': '#fee2e2', 'high-fg': '#991b1b',
              'info-bg': '#e8f1fd', 'info-fg': '#1e40af', 'shadow': 'rgba(15,23,42,.06)',
              # light values = what Streamlit's light base already renders, so light mode is unchanged
              'faint': 'rgba(15,23,42,.6)', 'control': 'rgba(15,23,42,.4)', 'link': '#0068c9',
              'tip-bg': '#ffffff', 'disabled': '#d5dae5'},
    'dark': {'bg': '#0b1220', 'text': '#e2e8f0', 'field': '#131c2e', 'field-hover': '#1b2740',
             'line': '#24324b', 'surface': '#111b2f', 'border': '#1f3a64', 'label': '#94a3b8',
             'accent': '#93c5fd', 'body': '#cbd5e1', 'muted': '#94a3b8', 'hero-from': '#172554',
             'hero-to': '#1d4ed8', 'hero-sub': '#bfdbfe', 'good-bg': '#052e1a', 'good-fg': '#86efac',
             'fair-bg': '#082f49', 'fair-fg': '#7dd3fc', 'high-bg': '#3b0d0d', 'high-fg': '#fca5a5',
             'info-bg': '#0c2544', 'info-fg': '#bfdbfe', 'shadow': 'rgba(0,0,0,.35)',
             'faint': 'rgba(226,232,240,.6)', 'control': 'rgba(226,232,240,.45)', 'link': '#60a5fa',
             'tip-bg': '#1b2740', 'disabled': '#475569'},
}

# sun / moon icons for the theme switch (inline SVG, no external files)
SUN = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
       "stroke='%23f59e0b' stroke-width='2' stroke-linecap='round'><circle cx='12' cy='12' r='4.5'/>"
       "<path d='M12 1.5v2.5M12 20v2.5M1.5 12H4M20 12h2.5M4.6 4.6l1.8 1.8M17.6 17.6l1.8 1.8M4.6 19.4l1.8-1.8"
       "M17.6 6.4l1.8-1.8'/></svg>")
MOON = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
        "stroke='COLOR' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
        "<path d='M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z'/>"
        "<path d='M17 3.5v2M16 4.5h2M20.5 8v1.5M19.75 8.75h1.5' stroke-width='1.5'/></svg>")

# theme lives in this visitor's session only; also kept in the URL (?theme=dark) so refresh / shared links keep it
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark' if st.query_params.get('theme') == 'dark' else 'light'
is_dark = st.session_state.theme == 'dark'
css_vars = '\n'.join(f'    --{name}: {value};' for name, value in THEMES[st.session_state.theme].items())

# switch: white knob with a sun on the left (light) / navy knob with a moon on the right (dark)
knob_left = '46px' if is_dark else '4px'
knob_bg = '#1e293b' if is_dark else '#ffffff'
knob_icon = MOON.replace('COLOR', '%23fcd34d') if is_dark else SUN
ghost_icon = SUN if is_dark else MOON.replace('COLOR', '%2394a3b8')
ghost_side = 'left: 16px' if is_dark else 'right: 16px'
track_bg = 'linear-gradient(145deg, #0f172a, #1e293b)' if is_dark else 'linear-gradient(145deg, #e2e8f0, #f1f5f9)'

st.markdown(f"""
<style>
:root {{
{css_vars}
}}
    .block-container {{padding-top: 1.25rem; max-width: 1250px;}}
    [data-testid="stHeader"] {{display: none;}}

    /* ---- page + Streamlit widgets follow the theme ---- */
    .stApp, [data-testid="stHeader"] {{background: var(--bg) !important;}}
    .stApp, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
    [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] strong, [data-testid="stWidgetLabel"] p,
    [data-testid="stCaptionContainer"], [data-testid="stHeader"] * {{color: var(--text);}}
    [data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="input"] > div,
    [data-baseweb="base-input"], [data-testid="stNumberInputContainer"] {{
        background: var(--field) !important; border-color: var(--field) !important;}}
    [data-baseweb="select"] *, .stApp input, .stApp textarea {{color: var(--text) !important;
        -webkit-text-fill-color: var(--text); caret-color: var(--text);}}
    [data-baseweb="select"] svg {{fill: var(--muted); color: var(--muted);}}
    [data-testid="stTooltipIcon"] svg {{color: var(--muted); stroke: var(--muted); fill: none;}}
    /* Streamlit strokes the icon shapes themselves, so the svg colour above does not reach them */
    [data-testid="stTooltipIcon"] svg *, [data-testid="stHeaderActionElements"] svg,
    [data-testid="stHeaderActionElements"] svg * {{stroke: var(--faint);}}
    [data-testid="stTextInputRootElement"] button, [data-testid="stTextInputRootElement"] button svg {{
        color: var(--text); fill: var(--text);}}
    [data-testid="InputInstructions"] {{color: var(--faint);}}
    [data-baseweb="tooltip"] > div, [data-baseweb="tooltip"] [data-testid="stTooltipContent"] {{
        background: var(--tip-bg) !important;}}
    [data-testid="stMarkdownContainer"] a {{color: var(--link);}}
    [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:not(:checked)) > div:first-child {{
        background: var(--control);}}
    [data-testid="stNumberInputStepDown"]:disabled svg, [data-testid="stNumberInputStepUp"]:disabled svg {{
        color: var(--disabled); fill: var(--disabled);}}
    .stButton button[kind="primary"] {{color: #ffffff !important; background-color: #2563eb; border-color: #2563eb;}}
    .stButton button[kind="primary"] p {{color: #ffffff !important; background: transparent !important;}}
    .stFormSubmitButton button[kind="primaryFormSubmit"] {{color: #ffffff !important; background-color: #2563eb !important;
        border-color: #2563eb !important; height: 2.75rem; font-weight: 600;}}
    .stFormSubmitButton button[kind="primaryFormSubmit"]:hover {{background-color: #1d4ed8 !important;}}
    .stFormSubmitButton button[kind="primaryFormSubmit"] p {{color: #ffffff !important; font-weight: 600;}}
    .st-key-logout button {{height: 2.25rem !important; font-size: .9rem !important; font-weight: 500 !important;}}
    .stButton button[kind="primary"]:hover {{background-color: #1d4ed8 !important; border-color: #1d4ed8 !important;}}
    [data-stale="true"] {{opacity: 1 !important; transition: none !important;}}
    [data-testid="stDecoration"] {{display: none;}}
    [data-testid="stNumberInputStepDown"], [data-testid="stNumberInputStepUp"] {{
        background: var(--field) !important; color: var(--text) !important;}}
    [data-testid="stNumberInputStepDown"]:hover, [data-testid="stNumberInputStepUp"]:hover {{
        background: var(--field-hover) !important;}}
    [data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="menu"] {{
        background: var(--field) !important; color: var(--text) !important;}}
    [data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] {{
        background: var(--field-hover) !important;}}
    [data-testid="stExpander"] details {{border-color: var(--line) !important; background: transparent;}}
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {{color: var(--text) !important;}}
    [data-baseweb="tab-list"] button p {{color: var(--text);}}
    [data-baseweb="tab-list"] button[aria-selected="true"] p {{color: #3b82f6;}}
    [data-baseweb="tab-border"] {{background: var(--line) !important;}}
    [data-testid="stVerticalBlockBorderWrapper"] {{border-color: var(--line) !important;}}
    [data-testid="stAlert"] > div {{background: var(--info-bg) !important;}}
    [data-testid="stAlert"] p {{color: var(--info-fg) !important;}}
    [data-testid="stMetricLabel"] p, [data-testid="stMetricValue"] {{color: var(--text) !important;}}
    .stApp hr {{border-color: var(--line);}}
    [data-testid="stDownloadButton"] button, .stButton button[kind="secondary"],
    .stFormSubmitButton button[kind="secondaryFormSubmit"] {{
        background: var(--field) !important; color: var(--text) !important; border-color: var(--line) !important;}}
    .stFormSubmitButton button[kind="secondaryFormSubmit"]:hover {{border-color: #3b82f6 !important;}}
    [data-testid="stRadio"] label p {{color: var(--text);}}

    /* ---- custom cards ---- */
    .stApp .hero {{background: linear-gradient(135deg, var(--hero-from) 0%, var(--hero-to) 100%); color: white;
           padding: 1.8rem 2rem; border-radius: 14px; margin-bottom: 1.2rem; box-shadow: 0 4px 18px var(--shadow);}}
    .stApp .hero h1 {{color: white; margin: 0; font-size: 2rem;}}
    .stApp .hero p {{color: var(--hero-sub); margin: .4rem 0 0 0; font-size: 1.05rem;}}
    .stApp .price-card {{background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
                 padding: 1.5rem; text-align: center; box-shadow: 0 2px 10px var(--shadow);}}
    .stApp .price-card hr {{border: none; border-top: 1px solid var(--border); margin: 1rem 0;}}
    .stApp .price-label {{color: var(--label); font-size: .9rem; text-transform: uppercase; letter-spacing: .05em;}}
    .stApp .price-value {{color: var(--accent); font-size: 2.5rem; font-weight: 700; margin: .3rem 0;}}
    .stApp .price-range, .stApp .price-range b {{color: var(--body); font-size: 1.05rem;}}
    .stApp .muted, .stApp .muted b {{color: var(--muted); font-size: .9rem;}}
    .stApp .up, .stApp .up b {{color: var(--good-fg);}} .stApp .down, .stApp .down b {{color: var(--high-fg);}}
    .stApp .verdict {{border-radius: 10px; padding: .9rem 1.1rem; margin-top: .8rem; font-weight: 600;}}
    .stApp .good {{background: var(--good-bg); color: var(--good-fg);}}
    .stApp .fair {{background: var(--fair-bg); color: var(--fair-fg);}}
    .stApp .high {{background: var(--high-bg); color: var(--high-fg);}}
    .stApp .table {{width: 100%; border-collapse: collapse; font-size: .95rem;}}
    .stApp .table th {{text-align: left; color: var(--label); font-weight: 600; padding: .5rem .6rem;
                      border-bottom: 1px solid var(--line); text-transform: uppercase; font-size: .8rem;}}
    .stApp .table td {{color: var(--text); padding: .55rem .6rem; border-bottom: 1px solid var(--line);}}
    div.stButton > button {{width: 100%; height: 3rem; font-size: 1.05rem; font-weight: 600;}}

    /* ---- theme switch (pill with sliding sun / moon knob) ---- */
    .st-key-theme_switch {{display: flex; justify-content: flex-end; position: relative; z-index: 5;
                          top: 1.1rem; right: 1.25rem; margin-bottom: -46px;}}
    [data-testid="stHorizontalBlock"]:has(.st-key-theme_switch) {{height: 0; min-height: 0; margin-bottom: -1rem;}}
    .st-key-theme_switch .stButton {{margin-left: auto; width: auto !important;}}
    .st-key-theme_switch button p {{position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0);}}
    .st-key-theme_switch button {{
        width: 88px !important; height: 46px !important; min-height: 0; padding: 0; position: relative;
        border-radius: 999px; border: 1px solid var(--line) !important; background: {track_bg} !important;
        box-shadow: inset 0 2px 6px rgba(0,0,0,.18); color: transparent !important; overflow: hidden;}}
    .st-key-theme_switch button::before {{
        content: ''; position: absolute; top: 3px; left: {knob_left}; width: 38px; height: 38px;
        border-radius: 50%; background: {knob_bg} url("{knob_icon}") center / 22px no-repeat;
        box-shadow: 0 3px 8px rgba(0,0,0,.28);}}
    .st-key-theme_switch button::after {{
        content: ''; position: absolute; top: 13px; {ghost_side}; width: 18px; height: 18px;
        background: url("{ghost_icon}") center / 18px no-repeat; opacity: .55;}}
    .st-key-theme_switch button:hover {{border-color: #3b82f6 !important;}}
    .st-key-theme_switch button:focus-visible {{outline: 2px solid #3b82f6; outline-offset: 2px;}}
</style>
""", unsafe_allow_html=True)


# ---------- helpers ----------

@st.cache_data(ttl=300, show_spinner=False)
def api_options() -> dict:
    """Every brand / model / owner / seller value the pricing service accepts (lowercase)."""
    try:
        return requests.get(f'{API_URL}/options', timeout=5).json()
    except requests.RequestException:
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def load_catalog():
    """Cars for the dropdowns: historical + current listings, one spelling each, only what the API can price."""
    hist = pd.read_csv(DATA_PATH)
    frames = [hist]
    if CURRENT_PATH.exists():
        frames.append(pd.read_csv(CURRENT_PATH))
    df = pd.concat(frames, ignore_index=True, sort=False)
    brand = {b.lower(): b for b in hist['company'].unique()}
    model = {m.lower(): m for m in hist['model'].unique()}

    def spelled(values, known):
        return values.astype(str).str.strip().map(lambda x: known.get(x.lower(), x if x != x.lower() else x.title()))

    df['company'] = spelled(df['company'], brand)
    df['model'] = spelled(df['model'], model)
    df['edition'] = df['edition'].fillna('').astype(str).str.strip()
    # one spelling per variant ("LXi" and "lxi" are the same) - prefer the one that is not all lowercase
    key = df['company'].str.lower() + '|' + df['model'].str.lower() + '|' + df['edition'].str.lower()
    preferred = (df.assign(key=key, lower=df['edition'] == df['edition'].str.lower())
                 .sort_values('lower').groupby('key')['edition'].first())
    df['edition'] = key.map(preferred)
    options = api_options()
    if options:
        df = df[df['company'].str.lower().isin(options['company']) & df['model'].str.lower().isin(options['model'])]
    return df


OWNER_LABELS = {'first': 'First', 'second': 'Second', 'third': 'Third', 'fourth & above': 'Fourth & Above',
                'test drive car': 'Test Drive Car'}


def owner_choices() -> list:
    accepted = api_options().get('owner') or list(OWNER_LABELS)
    return [label for value, label in OWNER_LABELS.items() if value in accepted]


def indian_format(amount: float) -> str:
    """1234567 -> '12,34,567'"""
    s = f'{int(round(amount))}'
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ','.join(groups) + ',' + tail


def in_lakh(amount: float, symbol='₹') -> str:
    return f'{symbol}{amount / 1e5:,.2f} Lakh'


# ---------- accounts (JWT from the API's /login and /register) ----------

def signed_in() -> dict | None:
    return st.session_state.get('auth')


def _start_session(body: dict):
    st.session_state.auth = {'token': body['access_token'], 'email': body['email'],
                             'full_name': body.get('full_name') or body['email'], 'is_admin': body.get('is_admin', False)}
    st.session_state.pop('auth_message', None)


def log_out(message: str | None = None):
    for key in ('auth', 'last', 'compare'):
        st.session_state.pop(key, None)
    # brand-new login / sign-up forms: nothing the previous person typed survives (shared computers)
    st.session_state.form_generation = st.session_state.get('form_generation', 0) + 1
    if message:
        st.session_state.auth_message = message


def _error_detail(r: requests.Response) -> str:
    try:
        detail = r.json().get('detail')
    except ValueError:
        detail = None
    if isinstance(detail, list):  # FastAPI validation errors
        detail = '; '.join(d.get('msg', '') for d in detail)
    return detail or f'Error {r.status_code}'


def log_in(email: str, password: str) -> str | None:
    """None on success, otherwise a message for the user."""
    try:
        r = requests.post(f'{API_URL}/login', json={'email': email, 'password': password}, timeout=15)
    except requests.RequestException:
        return 'The service is unavailable right now. Please try again in a few minutes.'
    if r.status_code == 401:
        return 'Wrong email or password.'
    if r.status_code != 200:
        return _error_detail(r)
    _start_session(r.json())
    return None


def sign_up(full_name: str, email: str, password: str, confirm: str) -> str | None:
    if password != confirm:
        return 'The two passwords do not match.'
    try:
        r = requests.post(f'{API_URL}/register', timeout=15,
                          json={'email': email, 'password': password, 'full_name': full_name})
    except requests.RequestException:
        return 'The service is unavailable right now. Please try again in a few minutes.'
    if r.status_code != 201:
        return _error_detail(r)
    _start_session(r.json())
    return None


def api_call(method: str, path: str, **kwargs):
    auth = signed_in() or {}
    headers = {'token': auth.get('token', ''), 'api-key': API_KEY}
    r = requests.request(method, f'{API_URL}{path}', headers=headers, timeout=20, **kwargs)
    if r.status_code == 401:  # token expired or revoked
        log_out('Your session has expired - please log in again.')
        st.rerun(scope='app')
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=30, show_spinner=False)
def cached_stats(token: str):
    try:
        r = requests.get(f'{API_URL}/stats', headers={'token': token, 'api-key': API_KEY}, timeout=10)
        return r.json() if r.ok else None
    except requests.RequestException:
        return None


def auth_page():
    """Log in / create account - shown until the visitor is signed in."""
    gen = st.session_state.get('form_generation', 0)
    _, middle, _ = st.columns([1, 1.4, 1])
    with middle:
        with st.container(border=True):
            st.markdown('### Welcome')
            st.caption('Log in or create a free account to get used-car price estimates and quotations.')
            if st.session_state.get('auth_message'):
                st.info(st.session_state.auth_message)
            tab_in, tab_up, tab_forgot = st.tabs(['Log in', 'Create account', 'Forgot password'])
            with tab_forgot:
                account.forgot_password_form(API_URL, gen)
            with tab_in:
                with st.form(f'login_form_{gen}'):
                    email = st.text_input('Email', autocomplete='email', key=f'login_email_{gen}')
                    password = st.text_input('Password', type='password', autocomplete='current-password',
                                             key=f'login_pass_{gen}')
                    if st.form_submit_button('Log in', type='primary', use_container_width=True):
                        error = log_in(email, password) if email and password else 'Enter your email and password.'
                        if error:
                            st.error(error)
                        else:
                            st.rerun()
            with tab_up:
                with st.form(f'signup_form_{gen}'):
                    full_name = st.text_input('Full name', max_chars=60, autocomplete='name', key=f'su_name_{gen}')
                    new_email = st.text_input('Email', max_chars=254, autocomplete='email', key=f'su_email_{gen}')
                    new_pass = st.text_input('Password', type='password', autocomplete='new-password', key=f'su_pass_{gen}',
                                             help='At least 8 characters, with a letter and a number.')
                    confirm = st.text_input('Confirm password', type='password', autocomplete='new-password',
                                            key=f'su_confirm_{gen}')
                    st.caption('We use your email only to identify your account and to contact you about it. '
                               'It is never shared or sold. Your password is stored encrypted (hashed).')
                    if st.form_submit_button('Create account', type='primary', use_container_width=True):
                        error = (sign_up(full_name, new_email, new_pass, confirm) if new_email and new_pass
                                 else 'Enter your email and a password.')
                        if error:
                            st.error(error)
                        else:
                            st.rerun()


def get_estimate(car: dict):
    """Returns the API result, or None after showing a friendly error."""
    try:
        return api_call('POST', '/predict', json=car['payload'])
    except requests.ConnectionError:
        st.error(f'Cannot reach the pricing service at {API_URL}. Please make sure it is running.')
    except requests.HTTPError as e:
        detail = e.response.json().get('detail', e.response.text) if e.response.content else str(e)
        st.error(f'Could not price this car: {detail}')
    return None


def spec_default(rows: pd.DataFrame, col: str, fallback: float) -> float:
    val = rows[col].median()
    return float(fallback if pd.isna(val) else round(val, 1))


def car_form(key: str, compact=False) -> dict:
    """Input widgets for one car. Returns the API payload plus a display name."""
    def k(name):
        return f'{key}_{name}'

    catalog = load_catalog()
    c1, c2 = st.columns(2)
    companies = sorted(catalog.company.unique())
    company = c1.selectbox('Brand', companies, index=companies.index('Maruti'), key=k('company'))
    by_company = catalog[catalog.company == company]
    models = sorted(by_company.model.unique())
    model = c2.selectbox('Model', models, index=models.index('Swift') if 'Swift' in models else 0, key=k('model'))
    by_model = by_company[by_company.model == model]

    c3, c4 = st.columns(2)
    fuels = ['Petrol', 'Diesel', 'CNG', 'LPG']
    common_fuel = by_model.fuel.mode().iloc[0]
    fuel = c3.selectbox('Fuel', fuels, index=fuels.index(common_fuel), key=k('fuel'))
    transmissions = ['Manual', 'Automatic']
    same_fuel = by_model[by_model.fuel == fuel]
    common_gear = (same_fuel if len(same_fuel) else by_model).transmission.mode().iloc[0]
    transmission = c4.selectbox('Transmission', transmissions, index=transmissions.index(common_gear),
                                key=k('transmission'))
    matching = by_model[(by_model.fuel == fuel) & (by_model.transmission == transmission)]
    if matching.empty:  # e.g. a CNG version not in our data - borrow specs from the same model
        matching = same_fuel if len(same_fuel) else by_model
    exact = by_model[(by_model.fuel == fuel) & (by_model.transmission == transmission)]
    variant = st.selectbox('Variant', ['Not sure'] + sorted(exact.edition.unique(), key=str.lower),
                           key=k('variant'),
                           help='The trim level written on the car or its papers, e.g. VXI, ZDI, Asta. '
                                'Choosing it makes the price more accurate.')

    if not compact:
        st.subheader('2. Its condition')
    c5, c6 = st.columns(2)
    year = c5.number_input('Year of manufacture', min_value=1990, max_value=date.today().year,
                           value=int(by_model.year.median()), step=1, key=k('year'))
    km_driven = c6.number_input('Kilometres driven', min_value=0, max_value=1_000_000,
                                value=50_000, step=5_000, key=k('km'))
    c7, c8 = st.columns(2)
    owner = c7.selectbox('Previous owners', owner_choices(), key=k('owner'),
                         help='"Test Drive Car" = a dealer demo car with no previous private owner.')
    seller_type = c8.selectbox('Sold by', ['Individual', 'Dealer', 'Trustmark Dealer'], key=k('seller'))

    spec_rows = exact[exact.edition == variant] if variant != 'Not sure' else matching
    with st.expander('Technical specifications (filled in automatically)'):
        s1, s2, s3 = st.columns(3)
        engine_cc = s1.number_input('Engine (cc)', 500.0, 7000.0, spec_default(spec_rows, 'engine_cc', 1200),
                                    key=k('cc'))
        max_power = s2.number_input('Max power (bhp)', 20.0, 700.0, spec_default(spec_rows, 'max_power_bhp', 80),
                                    key=k('bhp'))
        torque = s3.number_input('Torque (Nm)', 30.0, 2000.0, spec_default(spec_rows, 'torque_nm', 150), key=k('nm'))
        s4, s5 = st.columns(2)
        known_mileage = spec_rows['mileage_mpg'].median()
        mileage = s4.number_input('Mileage (mpg) - leave empty if unknown', 0.0, 150.0,
                                  None if pd.isna(known_mileage) else round(float(known_mileage), 1),
                                  key=k('mpg'))
        seats = s5.number_input('Seats', 2, 14, int(spec_default(spec_rows, 'seats', 5)), key=k('seats'))

    edition = '' if variant == 'Not sure' else variant
    return {
        'name': f'{year} {company} {model}{" " + edition if edition else ""}',
        'details': f'{fuel} · {transmission} · {indian_format(km_driven)} km · {owner} owner · {seller_type} seller',
        'variant_known': bool(edition),
        'payload': {
            'company': company, 'model': model, 'edition': edition, 'year': int(year), 'owner': owner,
            'fuel': fuel, 'seller_type': seller_type, 'transmission': transmission,
            'km_driven': float(km_driven), 'mileage_mpg': mileage or None, 'engine_cc': engine_cc,
            'max_power_bhp': max_power, 'torque_nm': torque, 'seats': float(seats),
        },
    }


def verdict(asking: float, result: dict):
    low, price, high = result.get('price_low', result['price'] * .9), result['price'], result.get(
        'price_high', result['price'] * 1.1)
    diff = (asking - price) / price
    if asking <= low:
        return 'good', f'Great deal - {abs(diff):.0%} below the estimated price.'
    if asking <= price * 1.05:
        return 'fair', f'Fair price - within {abs(diff):.0%} of the estimate.'
    if asking <= high:
        return 'fair', f'A little high ({diff:.0%} above the estimate) - there is room to negotiate.'
    return 'high', f'Overpriced - {diff:.0%} above the estimate and outside the usual range.'


@st.cache_data(ttl=30, show_spinner=False)
def service_health() -> dict | None:
    try:
        return requests.get(f'{API_URL}/health', timeout=5).json()
    except requests.RequestException:
        return None


def model_info() -> dict:
    """Live model version, data period, test accuracy and dealer premium from the API."""
    health = service_health() or {}
    return dict(health.get('model', {}), model_version=health.get('model_version'),
                dealer_premium=health.get('dealer_premium'))


def show_service_status():
    """Shown only when something is wrong - clients don't need technical details when all is well."""
    health = service_health()
    if not health:
        st.error('The pricing service is unavailable right now, so estimates cannot be calculated. '
                 'Please try again in a few minutes.')
    elif health.get('redis') != 'ok':
        st.caption('Estimates may take a little longer than usual right now.')


def accuracy_note() -> str:
    """Accuracy statement built from the live model's own test results, so it never goes out of date."""
    info = model_info()
    years, m, rows = info.get('listing_years'), info.get('holdout_metrics', {}), info.get('training_rows', {})
    text = (f"Estimates are based on the advertised prices of {rows.get('total', 0):,} real used-car listings"
            if rows.get('total') else 'Estimates are based on the advertised prices of thousands of real used-car listings')
    text += f' ({years[0]}-{years[1]})' if years else ''
    text += ' and are a guide only.'
    if m:
        text += (f" In testing on listings the model had not seen, {m['within_10pct']:.0%} of estimates were within 10% "
                 f"of the advertised price, {m['within_20pct']:.0%} within 20%, and {m['range_coverage']:.0%} of "
                 'advertised prices fell inside the expected range.')
    return text


def quote_pdf(car: dict, result: dict, asking: float | None, customer: str = '') -> bytes:
    return build_quote(car, result, asking, customer=customer, model_info=model_info(),
                       verdict_text=verdict(asking, result)[1] if asking else None)


def show_result(car: dict, result: dict, asking: float | None, customer: str = ''):
    low, high = result.get('price_low'), result.get('price_high')
    range_html = (f'<hr><div class="price-label">Expected range</div>'
                  f'<div class="price-range"><b>{in_lakh(low)}</b> &nbsp;to&nbsp; <b>{in_lakh(high)}</b></div>'
                  if low else '')
    st.markdown(f"""
    <div class="price-card">
        <div class="price-label">Fair market price</div>
        <div class="price-value">{in_lakh(result['price'])}</div>
        <div class="muted">₹{indian_format(result['price'])}</div>
        {range_html}
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"**{car['name']}** · {car['details']}")

    if asking:
        css, text = verdict(asking, result)
        st.markdown(f'<div class="verdict {css}">Asking {in_lakh(asking)}: {text}</div>', unsafe_allow_html=True)

    if result.get('factors'):
        st.markdown('##### What affects this price')
        for f in result['factors']:
            arrow, css = ('▲', 'up') if f['effect'] >= 0 else ('▼', 'down')
            sign = '+' if f['effect'] >= 0 else '−'
            st.markdown(f"<span class='{css}'>{arrow} <b>{sign}₹{indian_format(abs(f['effect']))}</b></span>"
                        f" &nbsp;{f['factor']} <span class='muted'>({f['compared_to']})</span>",
                        unsafe_allow_html=True)

    account.forecast_block(result)
    if not car['variant_known']:
        st.info('Tip: choose the variant for a more precise price - top variants can be worth 10-20% more.')
    pdf, filename = quote_pdf(car, result, asking, customer), f"{quote_number(car['payload'], date.today())}.pdf"
    st.download_button('📄 Download quotation (PDF)', data=pdf, file_name=filename,
                       mime='application/pdf', use_container_width=True)
    account.emi_calculator(asking or result['price'], key='est')
    account.share_quote_block(api_call, pdf, filename, key='est')


# ---------- page ----------

def switch_theme():
    st.session_state.theme = 'light' if st.session_state.theme == 'dark' else 'dark'
    st.query_params['theme'] = st.session_state.theme


_, toggle_col = st.columns([6, 1])
with toggle_col:
    st.button('Switch theme', key='theme_switch', on_click=switch_theme,
              help='Switch to light mode' if is_dark else 'Switch to dark mode')

st.markdown("""
<div class="hero">
    <h1>🚗 Revora</h1>
    <p>Used Car Price Estimator</p>
    <p>Get a fair market price for a used car in seconds - pick the car, tell us its condition, and we do the rest.</p>
</div>
""", unsafe_allow_html=True)

show_service_status()

if not signed_in():
    auth_page()
    st.stop()

user_col, logout_col = st.columns([6, 1])
user_col.markdown(f"<span class='muted'>Signed in as <b>{signed_in()['full_name']}</b> "
                  f"({signed_in()['email']})</span>", unsafe_allow_html=True)
logout_col.button('Log out', key='logout', on_click=log_out, use_container_width=True)

tab_names = ['💰 Estimate a price', '⚖️ Compare cars', '📊 Market insights', '👤 My account']
if signed_in().get('is_admin'):
    tab_names.append('🛠️ Admin')
tab_estimate, tab_compare, tab_insights, tab_account, *tab_admin = st.tabs(tab_names)

@st.fragment
def estimate_tab():
    left, right = st.columns([1.35, 1], gap='large')
    with left:
        st.subheader('1. Which car?')
        car = car_form('main')
        asking = st.number_input('Seller\'s asking price in ₹ (optional - we\'ll tell you if it\'s a good deal)',
                                 min_value=0, max_value=50_000_000, value=0, step=10_000)
        customer = st.text_input('Customer name (optional, printed on the quotation)', max_chars=60,
                                 value=signed_in()['full_name'])
        clicked = st.button('Estimate price', type='primary')
    with right:
        st.subheader('Estimated price')
        if clicked:
            with st.spinner('Calculating...'):
                st.session_state.last = (car, get_estimate(car))
            if st.session_state.last[1]:
                st.rerun(scope='app')  # redraw everything so "My account" lists this estimate too
        last = st.session_state.get('last')
        if last and last[1] and last[0]['payload'] == car['payload']:
            show_result(last[0], last[1], asking or None, customer)
        else:
            st.markdown("""
            <div class="price-card">
                <div class="price-label">Your estimate will appear here</div>
                <p class="muted" style="margin-top:.8rem">Fill in the car details on the left and press
                <b>Estimate price</b>.</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('---')
        st.markdown(f'<span class="muted">{accuracy_note()}</span>', unsafe_allow_html=True)


@st.fragment
def compare_tab():
    st.markdown('Compare up to three cars side by side - useful when choosing between options.')
    count = st.radio('Number of cars', [2, 3], horizontal=True)
    cols = st.columns(count, gap='large')
    cars = []
    for i, col in enumerate(cols):
        with col:
            with st.container(border=True):
                st.markdown(f'**Car {i + 1}**')
                cars.append(car_form(f'cmp{i}', compact=True))
                cars[-1]['asking'] = st.number_input('Asking price in ₹ (optional)', min_value=0,
                                                     max_value=50_000_000, value=0, step=10_000,
                                                     key=f'cmp{i}_asking') or None
    customer = st.text_input('Customer name (optional, printed on the comparison)', max_chars=60, key='cmp_customer')
    if st.button('Compare prices', type='primary'):
        st.session_state.compare = (cars, [get_estimate(c) for c in cars])
        if all(st.session_state.compare[1]):
            st.rerun(scope='app')  # redraw everything so "My account" lists these estimates too
    saved = st.session_state.get('compare')
    # show the last comparison while the same cars are selected (it survives the download click)
    if saved and [c['payload'] for c in saved[0]] == [c['payload'] for c in cars] and all(saved[1]) \
            and len(saved[1]) == count:
        results = saved[1]
        best = min(range(count), key=lambda i: results[i]['price'])
        for i, col in enumerate(cols):
            with col:
                st.metric(cars[i]['name'], in_lakh(results[i]['price']),
                          delta='Lowest price' if i == best else
                          'Same price' if results[i]['price'] - results[best]['price'] < 1000 else
                          f"+{in_lakh(results[i]['price'] - results[best]['price'])}",
                          delta_color='normal' if i == best else 'inverse')
                if 'price_low' in results[i]:
                    st.caption(f"Range {in_lakh(results[i]['price_low'])} - {in_lakh(results[i]['price_high'])}")
                if cars[i]['asking']:
                    css, text = verdict(cars[i]['asking'], results[i])
                    st.markdown(f'<div class="verdict {css}">Asking {in_lakh(cars[i]["asking"])}: {text}</div>',
                                unsafe_allow_html=True)
                if results[i].get('factors'):
                    with st.expander('What affects this price'):
                        for f in results[i]['factors']:
                            arrow, css = ('▲', 'up') if f['effect'] >= 0 else ('▼', 'down')
                            sign = '+' if f['effect'] >= 0 else '−'
                            st.markdown(f"<span class='{css}'>{arrow} <b>{sign}₹{indian_format(abs(f['effect']))}</b>"
                                        f"</span> &nbsp;{f['factor']} <span class='muted'>({f['compared_to']})</span>",
                                        unsafe_allow_html=True)
        asking = [c['asking'] for c in cars]
        verdicts = [verdict(a, r)[1] if a else None for a, r in zip(asking, results)]
        st.download_button('📄 Download comparison (PDF)',
                           data=build_comparison(cars, results, customer=customer, model_info=model_info(),
                                                 asking=asking, verdicts=verdicts),
                           file_name=f"{comparison_number([c['payload'] for c in cars], date.today())}.pdf",
                           mime='application/pdf', use_container_width=True)


@st.fragment
def insights_tab():
    insights.render(THEMES[st.session_state.theme], cached_stats(signed_in()['token']))


with tab_estimate:
    estimate_tab()
with tab_compare:
    compare_tab()
with tab_insights:
    insights_tab()
with tab_account:
    account.my_account_tab(
        api_call, signed_in(),
        build_quote_pdf=lambda car, result: build_quote(car, result, customer=signed_in()['full_name'],
                                                        model_info=model_info()),
        quote_file_name=lambda payload: f'{quote_number(payload, date.today())}.pdf',
        log_out=log_out)
if tab_admin:
    with tab_admin[0]:
        account.admin_tab(api_call, lambda chart, height: insights._style(chart, THEMES[st.session_state.theme], height))

# data attribution required by the ODbL / DbCL licence of the training data
st.markdown('---')
st.markdown('<span class="muted">Price estimates use the <a href="https://www.kaggle.com/datasets/nehalbirla/'
            'vehicle-dataset-from-cardekho" target="_blank">Vehicle dataset</a> by Nehal Birla, made available under '
            'the <a href="https://opendatacommons.org/licenses/odbl/1-0/" target="_blank">Open Database License</a>; '
            'its contents are under the <a href="https://opendatacommons.org/licenses/dbcl/1-0/" target="_blank">'
            'Database Contents License</a>.</span>', unsafe_allow_html=True)
