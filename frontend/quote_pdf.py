"""Professional valuation quotation (PDF) for one car estimate.

Business details are optional and come from environment variables - nothing is invented:
    QUOTE_BUSINESS_NAME     (default "Revora")
    QUOTE_BUSINESS_ADDRESS, QUOTE_BUSINESS_PHONE, QUOTE_BUSINESS_EMAIL, QUOTE_BUSINESS_GSTIN
    QUOTE_VALID_DAYS        (default 7)
"""
import hashlib
import json
import os
from datetime import date, timedelta

from fpdf import FPDF
from fpdf.fonts import FontFace

NAVY = (30, 58, 138)
LIGHT = (240, 247, 255)
GREY = (100, 116, 139)
TEXT = (15, 23, 42)
LINE = (203, 213, 225)

BUSINESS = {
    'name': os.getenv('QUOTE_BUSINESS_NAME', 'Revora'),
    'address': os.getenv('QUOTE_BUSINESS_ADDRESS', ''),
    'phone': os.getenv('QUOTE_BUSINESS_PHONE', ''),
    'email': os.getenv('QUOTE_BUSINESS_EMAIL', ''),
    'gstin': os.getenv('QUOTE_BUSINESS_GSTIN', ''),
}
VALID_DAYS = int(os.getenv('QUOTE_VALID_DAYS', '7'))
ATTRIBUTION = ('Valuation data: "Vehicle dataset" by Nehal Birla (kaggle.com/datasets/nehalbirla/vehicle-dataset-'
               'from-cardekho), Open Database License (ODbL) v1.0 / Database Contents License (DbCL) v1.0; and "Used Car '
               'Price Prediction" (Kaggle), CC0.')

_ONES = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve',
         'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
_TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']


def _below_thousand(n: int) -> str:
    words = []
    if n >= 100:
        words += [_ONES[n // 100], 'Hundred']
        n %= 100
    if n >= 20:
        words.append(_TENS[n // 10])
        n %= 10
    if n:
        words.append(_ONES[n])
    return ' '.join(words)


def amount_in_words(amount: float) -> str:
    """368000 -> 'Rupees Three Lakh Sixty Eight Thousand Only' (Indian numbering)."""
    n = int(round(amount))
    if n == 0:
        return 'Rupees Zero Only'
    parts = []
    for size, label in ((10_000_000, 'Crore'), (100_000, 'Lakh'), (1_000, 'Thousand')):
        if n >= size:
            parts.append(f'{_below_thousand(n // size)} {label}')  # fine up to 999 crore
            n %= size
    if n:
        parts.append(_below_thousand(n))
    return 'Rupees ' + ' '.join(parts) + ' Only'


def inr(amount: float) -> str:
    """1234567 -> 'INR 12,34,567' (Indian digit grouping)."""
    s = f'{int(round(abs(amount)))}'
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ('-' if amount < 0 else '') + 'INR ' + (','.join(groups + [tail]) if groups else tail)


def quote_number(payload: dict, today: date) -> str:
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:6].upper()
    return f'QT-{today:%Y%m%d}-{digest}'


class _Quote(FPDF):
    def __init__(self, number: str):
        super().__init__(format='A4')
        self.number = number
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(True, margin=24)
        self.alias_nb_pages()

    def footer(self):
        self.set_y(-20)
        self.set_draw_color(*LINE)
        self.line(15, self.get_y(), 195, self.get_y())
        self.set_font('Helvetica', '', 7)
        self.set_text_color(*GREY)
        self.multi_cell(0, 3.4, ATTRIBUTION, new_x='LMARGIN', new_y='NEXT')
        self.cell(0, 4, f'Quotation {self.number}', align='L')
        self.set_x(15)
        self.cell(0, 4, f'Page {self.page_no()} of {{nb}}', align='R')


def _section(pdf: FPDF, title: str):
    pdf.ln(3)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, title.upper(), new_x='LMARGIN', new_y='NEXT')
    pdf.set_draw_color(*NAVY)
    pdf.set_line_width(0.4)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.ln(2)
    pdf.set_text_color(*TEXT)


def _key_value_table(pdf: FPDF, pairs: list):
    """Two label/value pairs per row."""
    pdf.set_font('Helvetica', '', 9.5)
    label_style = FontFace(emphasis='BOLD', color=GREY, fill_color=LIGHT)
    value_style = FontFace(color=TEXT, fill_color=(255, 255, 255))
    with pdf.table(col_widths=(28, 62, 28, 62), line_height=6.5, borders_layout='HORIZONTAL_LINES',
                   first_row_as_headings=False, text_align=('LEFT', 'LEFT', 'LEFT', 'LEFT')) as table:
        for i in range(0, len(pairs), 2):
            row = table.row()
            for label, value in pairs[i:i + 2]:
                row.cell(label, style=label_style)
                row.cell(str(value), style=value_style)
            if len(pairs[i:i + 2]) == 1:
                row.cell('', style=label_style)
                row.cell('', style=value_style)


def _letterhead(pdf: FPDF, number: str, customer: str, today: date, title: str = 'QUOTATION',
                subtitle: str = 'Used car valuation'):
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 26, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(15, 7)
    pdf.set_font('Helvetica', 'B', 17)
    pdf.cell(110, 8, BUSINESS['name'])
    pdf.set_font('Helvetica', 'B', 20)
    pdf.cell(0, 8, title, align='R', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 8.5)
    contact = '  |  '.join(x for x in (BUSINESS['address'], BUSINESS['phone'], BUSINESS['email']) if x)
    pdf.cell(110, 5, contact)
    pdf.cell(0, 5, subtitle, align='R', new_x='LMARGIN', new_y='NEXT')
    if BUSINESS['gstin']:
        pdf.cell(0, 5, f"GSTIN: {BUSINESS['gstin']}", new_x='LMARGIN', new_y='NEXT')
    pdf.set_y(31)
    pdf.set_text_color(*TEXT)
    _key_value_table(pdf, [
        ('Quotation No.', number), ('Date', f'{today:%d %b %Y}'),
        ('Prepared for', customer.strip() or '-'), ('Valid until', f'{today + timedelta(days=VALID_DAYS):%d %b %Y}'),
    ])


def _terms(pdf: FPDF, number: str = '5', dealer_premium: float | None = None):
    _section(pdf, f'{number}. Terms and conditions')
    pdf.set_font('Helvetica', '', 8)
    terms = [
        'This quotation is an indicative market valuation. It is not an offer to buy or sell the vehicle and not a '
        'certified valuation for insurance, loan or legal purposes.',
        f'The quotation is valid for {VALID_DAYS} days from the date of issue.',
        'The final price is subject to physical inspection, accident and service history, tyre and battery condition, '
        'and verification of the registration certificate (RC), insurance, PUC and loan (hypothecation) status.',
        'Amounts are in Indian Rupees and exclude RTO transfer charges, insurance, taxes and any other fees.',
        'This is a computer-generated quotation and does not require a signature.',
    ]
    if dealer_premium:  # the premium the pricing service applies (from its /health endpoint)
        terms.insert(4, f'Dealer listings include a dealer premium of {dealer_premium:.1%} over a private sale, '
                        'measured from market data.')
    for i, term in enumerate(terms, 1):
        pdf.cell(6, 4.1, f'{i}.')
        pdf.multi_cell(0, 4.1, term, new_x='LMARGIN', new_y='NEXT')


def _period(info: dict) -> str:
    years = info.get('listing_years')
    return f'{years[0]} to {years[1]}' if years else '2019 to 2023'


def _spec(value, unit: str) -> str:
    return f'{value:g} {unit}' if value else 'Not provided'


def build_quote(car: dict, result: dict, asking: float | None = None, customer: str = '',
                model_info: dict | None = None, verdict_text: str | None = None, today: date | None = None) -> bytes:
    today = today or date.today()
    p = car['payload']
    number = quote_number(p, today)
    pdf = _Quote(number)
    pdf.add_page()

    _letterhead(pdf, number, customer, today)

    # ---- vehicle
    _section(pdf, '1. Vehicle details')
    spec = _spec
    _key_value_table(pdf, [
        ('Make', p['company']), ('Model', p['model']),
        ('Variant', p['edition'] or 'Not specified'), ('Year of mfg.', p['year']),
        ('Age', f"{today.year - p['year']} years"), ('Kilometres', f"{int(p['km_driven']):,} km"),
        ('Fuel', p['fuel']), ('Transmission', p['transmission']),
        ('Ownership', f"{p['owner']} owner"), ('Sold by', p['seller_type']),
        ('Engine', spec(p['engine_cc'], 'cc')), ('Max power', spec(p['max_power_bhp'], 'bhp')),
        ('Torque', spec(p['torque_nm'], 'Nm')), ('Seats', int(p['seats']) if p['seats'] else 'Not provided'),
        ('Mileage', spec(p.get('mileage_mpg'), 'mpg')),
    ])

    # ---- valuation
    _section(pdf, '2. Valuation summary')
    top = pdf.get_y()
    pdf.set_fill_color(*LIGHT)
    pdf.set_draw_color(*NAVY)
    pdf.rect(15, top, 180, 30, 'DF')
    pdf.set_xy(20, top + 3)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*GREY)
    pdf.cell(85, 5, 'FAIR MARKET VALUE')
    pdf.cell(0, 5, 'EXPECTED PRICE RANGE', new_x='LMARGIN', new_y='NEXT')
    pdf.set_x(20)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(*NAVY)
    pdf.cell(85, 10, inr(result['price']))
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*TEXT)
    rng = f"{inr(result['price_low'])} - {inr(result['price_high'])}" if 'price_low' in result else '-'
    pdf.cell(0, 10, rng, new_x='LMARGIN', new_y='NEXT')
    pdf.set_x(20)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.cell(0, 6, amount_in_words(result['price']), new_x='LMARGIN', new_y='NEXT')
    pdf.set_y(top + 32)

    if result.get('forecast'):
        pdf.set_font('Helvetica', '', 9.5)
        forecast = result['forecast']
        with pdf.table(col_widths=(45,) + (135 / len(forecast),) * len(forecast), line_height=6.5,
                       first_row_as_headings=False, borders_layout='HORIZONTAL_LINES') as table:
            row = table.row()
            row.cell('Expected value', style=FontFace(emphasis='BOLD', color=GREY, fill_color=LIGHT))
            for f in forecast:
                row.cell(f"In {f['years']} yr: {inr(f['price'])}", style=FontFace(color=TEXT, fill_color=(255, 255, 255)))
    if asking:
        pdf.set_font('Helvetica', '', 9.5)
        with pdf.table(col_widths=(45, 135), line_height=6.5, first_row_as_headings=False,
                       borders_layout='HORIZONTAL_LINES') as table:
            row = table.row()
            row.cell("Seller's asking price", style=FontFace(emphasis='BOLD', color=GREY, fill_color=LIGHT))
            row.cell(f'{inr(asking)}  -  {verdict_text or ""}', style=FontFace(color=TEXT, fill_color=(255, 255, 255)))

    # ---- breakdown
    if result.get('factors'):
        _section(pdf, '3. Price breakdown')
        pdf.set_font('Helvetica', '', 9.5)
        head = FontFace(emphasis='BOLD', color=(255, 255, 255), fill_color=NAVY)
        with pdf.table(col_widths=(45, 95, 40), line_height=6.5, headings_style=head,
                       text_align=('LEFT', 'LEFT', 'RIGHT'), borders_layout='HORIZONTAL_LINES') as table:
            table.row(['Factor', 'Compared with', 'Effect on price'])
            for f in result['factors']:
                sign = '+' if f['effect'] >= 0 else '-'
                row = table.row()
                for text in (f['factor'], f['compared_to'].replace('vs ', '').capitalize(),
                             f"{sign}{inr(abs(f['effect']))}"):
                    row.cell(text, style=FontFace(color=TEXT, fill_color=(255, 255, 255)))

    # ---- basis
    _section(pdf, '4. Basis of valuation')
    pdf.set_font('Helvetica', '', 9)
    info = model_info or {}
    metrics = info.get('holdout_metrics', {})
    rows = info.get('training_rows', {}).get('total')
    basis = (f"Estimated by a machine-learning model trained on the advertised prices of "
             f"{f'{rows:,}' if rows else 'thousands of'} real used-car listings in India ({_period(info)}). "
             "The value reflects the car's age, kilometres, ownership, seller type, variant and specifications.")
    if metrics:
        basis += (f" In testing on listings the model had not seen, {metrics.get('within_20pct', 0):.0%} of estimates "
                  f"were within 20% of the advertised price and {metrics.get('range_coverage', 0):.0%} of advertised "
                  'prices fell inside the expected range.')
    if info.get('model_version'):
        basis += f" Model version {info['model_version']}."
    pdf.multi_cell(0, 4.8, basis, new_x='LMARGIN', new_y='NEXT')

    _terms(pdf, dealer_premium=info.get('dealer_premium'))
    return bytes(pdf.output())


def comparison_number(payloads: list, today: date) -> str:
    digest = hashlib.sha1(json.dumps(payloads, sort_keys=True, default=str).encode()).hexdigest()[:6].upper()
    return f'CMP-{today:%Y%m%d}-{digest}'


def build_comparison(cars: list, results: list, customer: str = '', model_info: dict | None = None,
                     today: date | None = None, asking: list | None = None, verdicts: list | None = None) -> bytes:
    """One-page side-by-side quotation for 2-3 cars; the lowest fair market value is highlighted."""
    today = today or date.today()
    payloads = [c['payload'] for c in cars]
    number = comparison_number(payloads, today)
    pdf = _Quote(number)
    pdf.add_page()
    _letterhead(pdf, number, customer, today, title='COMPARISON', subtitle='Used car valuation - side by side')

    n = len(cars)
    best = min(range(n), key=lambda i: results[i]['price'])
    label_w = 36
    col_w = (180 - label_w) / n
    label_style = FontFace(emphasis='BOLD', color=GREY, fill_color=LIGHT)
    value_style = FontFace(color=TEXT, fill_color=(255, 255, 255))
    best_style = FontFace(emphasis='BOLD', color=NAVY, fill_color=(220, 252, 231))
    head = FontFace(emphasis='BOLD', color=(255, 255, 255), fill_color=NAVY)

    def grid(title: str, rows: list, highlight_best: bool = False):
        _section(pdf, title)
        pdf.set_font('Helvetica', '', 9)
        with pdf.table(col_widths=(label_w,) + (col_w,) * n, line_height=5.8, headings_style=head,
                       borders_layout='HORIZONTAL_LINES', text_align=('LEFT',) + ('CENTER',) * n) as table:
            table.row([''] + [f'Car {i + 1}' + ('  (lowest price)' if i == best else '') for i in range(n)])
            for label, values in rows:
                row = table.row()
                row.cell(label, style=label_style)
                for i, v in enumerate(values):
                    row.cell(str(v), style=best_style if highlight_best and i == best else value_style)

    grid('1. Vehicles compared', [
        ('Make', [p['company'] for p in payloads]),
        ('Model', [p['model'] for p in payloads]),
        ('Variant', [p['edition'] or 'Not specified' for p in payloads]),
        ('Year of mfg.', [p['year'] for p in payloads]),
        ('Age', [f"{today.year - p['year']} years" for p in payloads]),
        ('Kilometres', [f"{int(p['km_driven']):,} km" for p in payloads]),
        ('Fuel', [p['fuel'] for p in payloads]),
        ('Transmission', [p['transmission'] for p in payloads]),
        ('Ownership', [f"{p['owner']} owner" for p in payloads]),
        ('Sold by', [p['seller_type'] for p in payloads]),
        ('Engine', [_spec(p['engine_cc'], 'cc') for p in payloads]),
        ('Max power', [_spec(p['max_power_bhp'], 'bhp') for p in payloads]),
    ])
    lowest = results[best]['price']
    grid('2. Valuation comparison', [
        ('Fair market value', [inr(r['price']) for r in results]),
        ('Expected range', [f"{inr(r['price_low'])} - {inr(r['price_high'])}" if 'price_low' in r else '-'
                            for r in results]),
        ('vs lowest price', ['Lowest' if i == best else
                             ('Same' if r['price'] - lowest < 1000 else f"+{inr(r['price'] - lowest)}")
                             for i, r in enumerate(results)]),
    ] + ([('Asking price', [inr(a) if a else '-' for a in asking]),
          ('Assessment', [v or '-' for v in (verdicts or [None] * n)])] if asking and any(asking) else []),
        highlight_best=True)

    _section(pdf, '3. Basis of valuation')
    pdf.set_font('Helvetica', '', 9)
    info = model_info or {}
    rows = info.get('training_rows', {}).get('total')
    basis = (f"Each car is valued independently by a machine-learning model trained on the advertised prices of "
             f"{f'{rows:,}' if rows else 'thousands of'} real used-car listings in India ({_period(info)}), "
             "using its age, kilometres, ownership, seller type, variant and specifications. The lowest fair market "
             "value is highlighted; it is not a recommendation - condition and history should be checked for each car.")
    if info.get('model_version'):
        basis += f" Model version {info['model_version']}."
    pdf.multi_cell(0, 4.8, basis, new_x='LMARGIN', new_y='NEXT')
    _terms(pdf, '4', dealer_premium=info.get('dealer_premium'))
    return bytes(pdf.output())

