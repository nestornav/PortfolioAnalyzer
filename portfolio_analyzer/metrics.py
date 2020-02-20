import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import statsmodels.api as sm
from sklearn import linear_model
from statsmodels import regression


class MainMetrics:
    """Compute the main metrics for asset."""

    def __init__(self, benchmark, mkt="NYSE"):
        self.mkt_cal = mcal.get_calendar(mkt)
        self.benchmark = benchmark
        self.benchmark.columns = ["benchmark"]

    def estimate(self, data):
        """Perform the estimation of the metrics for every asset in data."""
        results = {}
        for ticker in data.columns:
            results[ticker] = self.__metrics(data[[ticker]])
        return pd.DataFrame(results)

    def __metrics(self, data):
        main_metrics = {}
        main_metrics["benchmark correlation"] = self.__market_corr(data)
        main_metrics["average return"] = self.__average_return(data)
        main_metrics["alpha"], main_metrics["beta"] = self.__alpha_beta(data)
        main_metrics["sharpe ratio"] = self.__sharpe_ratio(data)
        main_metrics["max draw down"] = self.__max_drawdown(data)
        return main_metrics

    def __market_corr(self, data):
        return (
            pd.concat([data.pct_change(), self.benchmark.pct_change()], axis=1)
            .corr()
            .values[0, 1]
        )

    def __average_return(self, data):
        year_events = self.__event_frequency(data)
        average_return = np.exp(
            np.mean(np.log((1 + data.pct_change()).dropna()))
        ).values[0]
        return average_return ** year_events - 1.0

    def __alpha_beta(self, data):
        pct_change_df = pd.concat(
            [np.log(data).diff(), np.log(self.benchmark).diff()], axis=1
        ).dropna()
        columns = set(pct_change_df.columns)
        asset_name = list(columns.difference(["benchmark"]))[0]
        x = pct_change_df["benchmark"].values
        y = pct_change_df[asset_name].values

        x = sm.add_constant(x)
        model = regression.linear_model.OLS(y, x).fit()
        alpha = model.params[0]
        beta = model.params[1]
        return alpha * self.__event_frequency(data), beta

    def __sharpe_ratio(self, data):
        return_data = data.pct_change().dropna()
        mu = np.mean(return_data).values[0]
        std = np.std(return_data).values[0]
        return mu / std * np.sqrt(self.__event_frequency(data))

    def __event_frequency(self, data):
        end_date = data.index[1]
        start_date = data.index[0]
        data_frequency = len(
            self.mkt_cal.valid_days(start_date=start_date, end_date=end_date)
        )
        return 251 / data_frequency

    @staticmethod
    def __max_drawdown(data):
        prev_high = 0.0
        max_draw = 0.0
        for index, value in data.itertuples():
            prev_high = max(prev_high, value)
            dd = (value - prev_high) / prev_high
            max_draw = min(max_draw, dd)
        return max_draw


def factor_analysis(benchmark_data, factors_data):
    """Perform factor analysis on the benchmark."""
    benchmark_data.columns = ["benchmark"]
    factors_names = factors_data.columns
    data = np.log(pd.concat([factors_data, benchmark_data], axis=1)).diff().dropna()
    y = data[["benchmark"]].values
    X = data[factors_names].values
    reg_model = linear_model.LinearRegression().fit(X, y)
    results = {
        "beta_" + factor_name: [factor_beta]
        for factor_name, factor_beta in zip(factors_names, reg_model.coef_[0])
    }
    results["alpha"] = reg_model.intercept_
    return pd.DataFrame(results)
