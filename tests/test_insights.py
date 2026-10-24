import sys

import pytest

pytest.importorskip('streamlit')  # frontend dependency - skipped where only the API is installed
sys.path.insert(0, 'frontend')
import insights  # noqa: E402


@pytest.fixture(scope='module')
def df():
    return insights.market_data()


def test_market_data_combines_all_legal_listings(df):
    assert len(df) == 6926 + sum(1 for _ in open('data/current-listings.csv')) - 1
    assert (df['selling_price'] > 0).all() and (df['age'] >= 0).all()
    assert {'Maruti', 'Hyundai', 'Land Rover'} <= set(df['company'])  # one spelling per brand
    assert 'maruti' not in set(df['company'])


def test_value_loss_is_plausible(df):
    loss = insights.yearly_value_loss(df)
    assert len(loss) > 20 and 0.03 < loss['loss_per_year'].median() < 0.2


def test_like_for_like_premiums(df):
    prem = insights.like_for_like_premiums(df).set_index('comparison')['difference']
    assert prem['Automatic vs manual'] > 0 and prem['First vs second owner'] > 0
    assert abs(prem['Dealer vs private seller'] - 0.028) < 0.01  # matches the premium the API applies


@pytest.mark.parametrize('company, model, expected', [
    ('maruti', 'sx4', 'Maruti SX4'), ('maruti', 'wagon', 'Maruti Wagon R'),
    ('hyundai', 'i20', 'Hyundai i20'), ('land', 'rover', 'Land Rover')])
def test_display_names(company, model, expected):
    assert insights.display_name(company, model) == expected
