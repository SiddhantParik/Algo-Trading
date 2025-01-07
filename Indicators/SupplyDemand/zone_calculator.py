import pandas as pd

def calculate_supply_demand_zones(candlestick_df, threshold_percent=10, div=8):
    """
    Calculates supply and demand zones based on candlestick data (ignoring volume).
    
    Args:
        candlestick_df (pd.DataFrame): Candlestick data with columns - 'datetime', 'open', 'high', 'low', 'close'.
        threshold_percent (float): The threshold percentage for supply/demand zone detection.
        div (int): The resolution or number of intervals to divide the price range for zone calculation.
    
    Returns:
        dict: A dictionary containing the calculated supply and demand zones with start and end prices, and their average levels.
    """
    candlestick_df['datetime'] = pd.to_datetime(candlestick_df['datetime'])

    supply_zones = []
    demand_zones = []
    high_prices = candlestick_df['high']
    low_prices = candlestick_df['low']

    max_price = high_prices.max()
    min_price = low_prices.min()
    price_step = (max_price - min_price) / div

    supply_zone = {'level': max_price, 'is_reached': False, 'start': None, 'end': None, 'avg': None}
    demand_zone = {'level': min_price, 'is_reached': False, 'start': None, 'end': None, 'avg': None}

    for i in range(div):
        supply_zone['level'] -= price_step
        demand_zone['level'] += price_step

        if not supply_zone['is_reached']:
            supply_zone['start'] = supply_zone['level']
            supply_zone['end'] = supply_zone['level'] + price_step
            supply_zone['avg'] = (supply_zone['start'] + supply_zone['end']) / 2
            supply_zones.append((candlestick_df['datetime'].iloc[0], supply_zone['start'], supply_zone['end'], supply_zone['avg']))
            supply_zone['is_reached'] = True

        if not demand_zone['is_reached']:
            demand_zone['start'] = demand_zone['level']
            demand_zone['end'] = demand_zone['level'] - price_step
            demand_zone['avg'] = (demand_zone['start'] + demand_zone['end']) / 2
            demand_zones.append((candlestick_df['datetime'].iloc[0], demand_zone['start'], demand_zone['end'], demand_zone['avg']))
            demand_zone['is_reached'] = True

    return {'supply': supply_zones, 'demand': demand_zones}
