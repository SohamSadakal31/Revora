import sys
from datetime import date

import pytest

pytest.importorskip('fpdf')  # frontend dependency - skipped where only the API is installed
sys.path.insert(0, 'frontend')
from quote_pdf import amount_in_words, build_quote, inr, quote_number  # noqa: E402

CAR = {'name': '2019 Maruti Wagon R LXI CNG', 'payload': {
    'company': 'Maruti', 'model': 'Wagon', 'edition': 'R LXI CNG', 'year': 2019, 'owner': 'First', 'fuel': 'CNG',
    'seller_type': 'Dealer', 'transmission': 'Manual', 'km_driven': 80214.0, 'mileage_mpg': None, 'engine_cc': 998.0,
    'max_power_bhp': 58.2, 'torque_nm': 77.0, 'seats': 5.0}}
RESULT = {'price': 390463.0, 'price_low': 300274.0, 'price_high': 452546.0,
          'factors': [{'factor': 'Sold by', 'effect': 10635.0, 'compared_to': 'vs a private seller'}]}


@pytest.mark.parametrize('amount, words', [
    (368000, 'Rupees Three Lakh Sixty Eight Thousand Only'),
    (10000000, 'Rupees One Crore Only'),
    (25500005, 'Rupees Two Crore Fifty Five Lakh Five Only'),
    (999, 'Rupees Nine Hundred Ninety Nine Only'),
])
def test_amount_in_words_indian_numbering(amount, words):
    assert amount_in_words(amount) == words


def test_inr_indian_digit_grouping():
    assert inr(1234567) == 'INR 12,34,567' and inr(999) == 'INR 999' and inr(-4698) == '-INR 4,698'


def test_quote_number_is_stable_per_car_and_day():
    a = quote_number(CAR['payload'], date(2026, 9, 30))
    assert a == quote_number(dict(CAR['payload']), date(2026, 9, 30)) and a.startswith('QT-20260930-')
    assert a != quote_number(dict(CAR['payload'], km_driven=1.0), date(2026, 9, 30))


def test_quote_is_one_page_with_all_sections():
    pdf = build_quote(CAR, RESULT, asking=350000, customer='Test Customer', verdict_text='Fair price',
                      model_info={'model_version': 'abc123', 'training_rows': {'total': 15602}}, today=date(2026, 9, 30))
    assert pdf.startswith(b'%PDF') and pdf.count(b'/Type /Page\n') + pdf.count(b'/Type /Page ') <= 2


def test_comparison_pdf_two_and_three_cars():
    from quote_pdf import build_comparison, comparison_number
    other = {'name': '2012 Maruti SX4 Vxi', 'payload': dict(CAR['payload'], model='SX4', edition='Vxi', year=2012,
                                                            fuel='Petrol', seller_type='Individual', mileage_mpg=35.25)}
    cheap = dict(RESULT, price=137271.0, price_low=110000.0, price_high=180000.0)
    for cars, results in (([CAR, other], [RESULT, cheap]), ([CAR, other, CAR], [RESULT, cheap, RESULT])):
        pdf = build_comparison(cars, results, customer='Test', model_info={'model_version': 'abc'}, today=date(2026, 9, 30))
        assert pdf.startswith(b'%PDF')
    assert comparison_number([CAR['payload'], other['payload']], date(2026, 9, 30)).startswith('CMP-20260930-')
