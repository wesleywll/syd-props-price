from sklearn.linear_model import LinearRegression
import numpy as np
import pandas as pd


def log_regress(df, n_year_threshold=9):
    # perform linear regression on log price, ignore suburbs with few yearly records
    # model: log(price) ~ year
    # assuming constant rate every year

    # if number of years wtih sales is fewer than threshold, skip regression
    if df.year.nunique() < n_year_threshold:
        return None
    model = LinearRegression()
    model.fit(X=np.array(df.year).reshape(-1, 1), y=np.log(df.price))
    results = pd.Series(
        (model.coef_[0], model.intercept_), index=["slope", "intercept"]
    )
    return results


def dist(lat1, lon1, lat2, lon2):
    # calculate distance between two coordinates
    return np.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) * 60 * 1.852


def million(price):
    # format price into million
    return f"{price/1e6:.1f}M"


def percent(rate):
    # format rate into percentage
    return f"{rate:.1%}"
