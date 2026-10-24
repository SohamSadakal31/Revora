import numpy as np
import pandas as pd

from training import import_used_car_price_prediction as uccp
from training.build_current_listings import HEADER


def test_uccp_convert_mapping_and_exclusions():
    raw = pd.DataFrame({
        'make': ['mercedes benz', 'maruti', 'maruti'], 'model': ['c class', 'swift', 'alto'],
        'variant': ['c220 cdi', 'lxi', 'lxi'], 'yr_mfr': [2015, 2016, 2014], 'total_owners': [4, 1, 2],
        'fuel_type': ['diesel', 'petrol & cng', 'petrol'], 'source': ['online', 'customer_to_customer', 'online'],
        'transmission': ['automatic', 'manual', np.nan], 'kms_run': [50000, 20000, 30000],
        'sale_price': [2000000, 400000, 250000], 'city': ['pune', 'noida', 'noida'],
        'ad_created_on': ['2021-03-01T10:00:00', '2021-03-02T10:00:00', '2021-03-03T10:00:00']})
    kept, excluded = uccp.convert(raw)
    assert kept['company'].tolist() == ['Mercedes-Benz', 'maruti']
    assert kept['owner'].tolist() == ['Fourth & Above', 'First']
    assert kept['fuel'].tolist() == ['Diesel', 'CNG'] and kept['seller_type'].tolist() == ['Dealer', 'Individual']
    assert kept[['mileage_mpg', 'engine_cc']].isna().all(axis=None)  # no specs invented
    assert excluded['reason'].tolist() == ['transmission missing in source']


def test_combined_header_extends_the_template():
    with open('data/current-listings.template.csv', encoding='utf-8') as f:
        template = f.read().strip().split(',')
    assert HEADER[:len(template)] == template and HEADER[len(template):] == ['data_source', 'licence']


def test_only_commercially_usable_licences_are_built():
    from training.build_current_listings import SOURCES
    assert {m.LICENCE for m in SOURCES} <= {'CC0: Public Domain', 'ODbL v1.0 / DbCL v1.0'}


def test_v4_convert_never_guesses():
    from training import import_cardekho_vehicle_v4 as v4
    raw = pd.DataFrame({
        'Make': ['Maruti Suzuki', 'Land Rover', 'Tata', 'Honda'], 'Model': ['Swift DZire VDI', 'Evoque SE', 'Nexon EV', 'City V'],
        'Price': [450000, 3450000, 1200000, 500000], 'Year': [2014, 2016, 2021, 2015], 'Kilometer': [75000, 29000, 9000, 60000],
        'Fuel Type': ['Diesel', 'Diesel', 'Electric', 'Petrol + CNG'], 'Transmission': ['Manual', 'Automatic', 'Automatic', 'Manual'],
        'Location': ['Ludhiana', 'Delhi', 'Pune', 'Pune'], 'Owner': ['Second', 'First', 'First', 'First'],
        'Seller Type': ['Individual', 'Individual', 'Individual', 'Corporate'],
        'Engine': ['1248 cc', '2179 cc', None, '1497 cc'], 'Max Power': ['74 bhp @ 4000 rpm', '88@4000', None, None],
        'Max Torque': ['190 Nm @ 2000 rpm', None, None, None], 'Seating Capacity': [5.0, 5.0, 5.0, 5.0]})
    kept, excluded = v4.convert(raw)
    assert kept[['company', 'model', 'edition']].values.tolist() == [['Maruti', 'Swift', 'DZire VDI'], ['Land', 'Rover', 'Evoque SE']]
    assert kept['max_power_bhp'].iloc[0] == 74 and np.isnan(kept['max_power_bhp'].iloc[1])  # unit-less value not guessed
    assert kept['mileage_mpg'].isna().all() and kept['seller_type'].eq('Individual').all()
    assert sorted(excluded['reason']) == ['electric / hybrid fuel is not an accepted value',
                                          'seller type has no equivalent (Corporate / Commercial Registration)']
