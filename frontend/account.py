"""Account screens and result add-ons: forgot password, my account (history, data export, password, deletion),
admin dashboard, value forecast, EMI calculator and emailing a quotation."""
import base64
import json
from datetime import datetime

import altair as alt
import pandas as pd
import requests
import streamlit as st

from insights import display_name


def _detail(error: requests.HTTPError) -> str:
    try:
        detail = error.response.json().get('detail')
    except ValueError:
        detail = None
    if isinstance(detail, list):
        detail = '; '.join(d.get('msg', '') for d in detail)
    return detail or 'Something went wrong. Please try again.'


def _lakh(v: float) -> str:
    return f'₹{v / 1e5:,.2f} Lakh'


# ---------------- login page: forgot password ----------------

def forgot_password_form(api_url: str, gen: int):
    st.caption('Enter your account email. We will email you a 6-digit code to set a new password.')
    with st.form(f'forgot_form_{gen}'):
        email = st.text_input('Email', autocomplete='email', key=f'fp_email_{gen}')
        if st.form_submit_button('Email me a code', type='primary', use_container_width=True):
            if not email:
                st.error('Enter your email.')
            else:
                try:
                    r = requests.post(f'{api_url}/password/forgot', json={'email': email}, timeout=20)
                    if r.status_code == 202:
                        st.session_state[f'fp_sent_{gen}'] = email
                        st.success(r.json()['detail'])
                    else:
                        st.error(r.json().get('detail', 'Please try again later.'))
                except requests.RequestException:
                    st.error('The service is unavailable right now. Please try again in a few minutes.')
    if st.session_state.get(f'fp_sent_{gen}'):
        with st.form(f'reset_form_{gen}'):
            code = st.text_input('6-digit code from the email', max_chars=6, key=f'fp_code_{gen}')
            new = st.text_input('New password', type='password', autocomplete='new-password', key=f'fp_new_{gen}',
                                help='At least 8 characters, with a letter and a number.')
            confirm = st.text_input('Confirm new password', type='password', autocomplete='new-password',
                                    key=f'fp_confirm_{gen}')
            if st.form_submit_button('Set new password', type='primary', use_container_width=True):
                if new != confirm:
                    st.error('The two passwords do not match.')
                else:
                    try:
                        r = requests.post(f'{api_url}/password/reset', timeout=20, json={
                            'email': st.session_state[f'fp_sent_{gen}'], 'code': code, 'new_password': new})
                        (st.success if r.ok else st.error)(r.json().get('detail', 'Please try again.'))
                    except requests.RequestException:
                        st.error('The service is unavailable right now. Please try again in a few minutes.')


# ---------------- estimate result add-ons ----------------

def forecast_block(result: dict):
    forecast = result.get('forecast')
    if not forecast:
        return
    st.markdown('##### Expected value if you keep it')
    cols = st.columns(len(forecast))
    for col, f in zip(cols, forecast):
        change = f['price'] / result['price'] - 1
        col.metric(f"In {f['years']} year{'s' if f['years'] > 1 else ''}", _lakh(f['price']), f'{change:.0%}',
                   delta_color='inverse' if change < 0 else 'normal')
    st.caption(f"Assumes about {result.get('forecast_km_per_year', 10000):,} km per year (this car's average so far) "
               'and today\'s market prices.')


def emi_calculator(price: float, key: str):
    # a remembered on/off switch (a collapsible section would close every time a value changes)
    if not st.toggle('🧮 Show loan / EMI calculator', key=f'{key}_emi_on'):
        return
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        down = c1.number_input('Down payment (₹)', 0, int(price), int(round(price * 0.2, -3)), 5_000, key=f'{key}_down')
        rate = c2.number_input('Interest rate (% per year)', 0.0, 30.0, 10.5, 0.25, key=f'{key}_rate',
                               help='Check the rate your bank or lender offers.')
        months = c3.selectbox('Tenure', [12, 24, 36, 48, 60, 72, 84], index=4, key=f'{key}_months',
                              format_func=lambda m: f'{m} months ({m // 12} yr)')
        loan = max(price - down, 0)
        r = rate / 12 / 100
        emi = loan / months if r == 0 else loan * r * (1 + r) ** months / ((1 + r) ** months - 1)
        m1, m2, m3 = st.columns(3)
        m1.metric('Monthly EMI', f'₹{emi:,.0f}')
        m2.metric('Loan amount', f'₹{loan:,.0f}')
        m3.metric('Total interest', f'₹{emi * months - loan:,.0f}')
        st.caption("An estimate for planning only - the lender's offer decides the actual EMI.")


def share_quote_block(api_call, pdf: bytes, filename: str, key: str):
    with st.expander('✉️ Email this quotation'):
        # a form, so typing does not re-draw the page (which would close this section)
        with st.form(f'{key}_share_form', clear_on_submit=False):
            to = st.text_input('Send to (email)', key=f'{key}_to')
            note = st.text_area('Message (optional)', max_chars=1000, key=f'{key}_note', height=80)
            send = st.form_submit_button('Send quotation')
        if send:
            if not to:
                st.error('Enter the email address to send it to.')
                return
            try:
                r = api_call('POST', '/share/quotation', json={
                    'to': to, 'filename': filename, 'pdf_base64': base64.b64encode(pdf).decode(), 'message': note})
                st.success(r['detail'])
            except requests.HTTPError as e:
                st.error(_detail(e))
            except requests.RequestException:
                st.error('The service is unavailable right now. Please try again in a few minutes.')


# ---------------- my account ----------------

def my_account_tab(api_call, auth: dict, build_quote_pdf, quote_file_name, log_out):
    st.markdown('#### My estimates')
    try:
        history = api_call('GET', '/history')
    except requests.RequestException:
        history = None
        st.error('Your estimates could not be loaded right now.')
    if history == []:
        st.caption('No estimates yet - they appear here after you use "Estimate a price".')
    elif history:
        rows = []
        for h in history:
            c = h['car']
            rows.append({'When': datetime.fromisoformat(h['ts']).strftime('%d %b %Y, %H:%M'),
                         'Car': f"{c['year']} {c['company']} {c['model']} {c.get('edition') or ''}".strip(),
                         'Km': f"{int(c['km_driven']):,}", 'Owner': c['owner'], 'Sold by': c['seller_type'],
                         'Estimate': _lakh(h['result']['price'])})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        pick = st.selectbox('Download a quotation for', range(len(history)),
                            format_func=lambda i: f"{rows[i]['When']} - {rows[i]['Car']} - {rows[i]['Estimate']}")
        chosen = history[pick]
        car = {'name': rows[pick]['Car'], 'payload': chosen['car']}
        st.download_button('📄 Download this quotation (PDF)', data=build_quote_pdf(car, chosen['result']),
                           file_name=quote_file_name(chosen['car']), mime='application/pdf', key='hist_pdf')

    st.markdown('#### My data')
    export = {'account': {'email': auth['email'], 'full_name': auth['full_name']}, 'estimates': history or []}
    st.download_button('⬇️ Download my data (JSON)', data=json.dumps(export, indent=2),
                       file_name='my-car-price-data.json', mime='application/json',
                       help='Everything this website stores about you: your account and your estimates.')

    if auth.get('is_admin'):
        st.info('The admin account is managed in the .env file - its password cannot be changed or deleted here.')
        return

    st.markdown('#### Change password')
    with st.form('change_password'):
        current = st.text_input('Current password', type='password', autocomplete='current-password')
        new = st.text_input('New password', type='password', autocomplete='new-password',
                            help='At least 8 characters, with a letter and a number.')
        confirm = st.text_input('Confirm new password', type='password', autocomplete='new-password')
        if st.form_submit_button('Change password'):
            if new != confirm:
                st.error('The two new passwords do not match.')
            else:
                try:
                    st.success(api_call('POST', '/account/password',
                                        json={'current_password': current, 'new_password': new})['detail'])
                except requests.HTTPError as e:
                    st.error(_detail(e))

    st.markdown('#### Delete my account')
    st.caption('Permanently deletes your account and all your estimates. This cannot be undone.')
    with st.form('delete_account'):
        password = st.text_input('Enter your password to confirm', type='password', autocomplete='current-password')
        sure = st.checkbox('I understand my account and data will be permanently deleted')
        if st.form_submit_button('Delete my account'):
            if not sure:
                st.error('Tick the box to confirm.')
            else:
                try:
                    api_call('POST', '/account/delete', json={'password': password})
                    log_out('Your account and your data have been deleted.')
                    st.rerun()
                except requests.HTTPError as e:
                    st.error(_detail(e))


# ---------------- admin ----------------

def admin_tab(api_call, style_chart):
    try:
        s = api_call('GET', '/admin/stats')
    except requests.RequestException:
        st.error('Admin statistics could not be loaded.')
        return
    m = st.columns(4)
    m[0].metric('Registered users', f"{s['registered_users']:,}")
    m[1].metric('Active users (30 days)', f"{s['active_users']:,}")
    m[2].metric('Estimates (all time)', f"{s['total_estimates']:,}")
    m[3].metric('Estimates (30 days)', f"{sum(d['estimates'] for d in s['estimates_per_day']):,}")

    c1, c2 = st.columns(2, gap='large')
    with c1:
        st.markdown('**Estimates per day** (last 30 days)')
        if s['estimates_per_day']:
            chart = alt.Chart(pd.DataFrame(s['estimates_per_day'])).mark_bar(color='#3b82f6', cornerRadiusEnd=3).encode(
                x=alt.X('day:O', title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y('estimates:Q', title='Estimates'), tooltip=['day', 'estimates'])
            st.altair_chart(style_chart(chart, 260), use_container_width=True, theme=None)
        else:
            st.caption('No estimates yet.')
    with c2:
        st.markdown('**New sign-ups per day** (last 30 days)')
        if s['signups_per_day']:
            chart = alt.Chart(pd.DataFrame(s['signups_per_day'])).mark_bar(color='#f59e0b', cornerRadiusEnd=3).encode(
                x=alt.X('day:O', title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y('signups:Q', title='Sign-ups'), tooltip=['day', 'signups'])
            st.altair_chart(style_chart(chart, 260), use_container_width=True, theme=None)
        else:
            st.caption('No sign-ups yet.')

    c3, c4 = st.columns(2, gap='large')
    with c3:
        st.markdown('**Most searched cars**')
        if s['most_searched']:
            top = pd.DataFrame(s['most_searched'])
            top['car'] = [display_name(c, m) for c, m in zip(top['company'], top['model'])]
            top['avg estimate'] = top['avg_price'].map(_lakh)
            st.dataframe(top[['car', 'searches', 'avg estimate']], hide_index=True, use_container_width=True)
    with c4:
        st.markdown('**Estimates by fuel**')
        if s['estimates_by_fuel']:
            st.dataframe(pd.DataFrame(s['estimates_by_fuel']), hide_index=True, use_container_width=True)
