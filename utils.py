import numpy as np
from datetime import datetime, timedelta

def get_first_and_last_day(year_month_str):
    """
    Get the first and last day of the month based on the given year and month string.

    Args:
        year_month_str (str): The year and month in the format 'YYYY-MM'.

    Returns:
        tuple: A tuple containing the first day and last day of the month as datetime.date objects.
    """
    # Parse the year and month from the string
    year, month = map(int, year_month_str.split('-'))
    # Get the first day of the month
    first_day = datetime(year, month, 1)
    # Get the last day of the month
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    return first_day.date(), last_day.date()

def calculate_total_return(dataframe, starting_portfolio_value):
    """
    Calculate the total percentage return of a portfolio given a dataframe with daily returns.

    Parameters:
    dataframe (pd.DataFrame): A DataFrame containing two columns: 'current_date' and 'daily_return'.
    starting_portfolio_value (float): The initial value of the portfolio in dollars.

    Returns:
    float: The total percentage return of the portfolio over the given period.
    """
    # Calculate the total return
    total_return = dataframe['daily_return'].sum()
    # Calculate the total return percentage
    total_return_percentage = (total_return / starting_portfolio_value) * 100
    return total_return_percentage, total_return
    
def calculate_max_drawdown(dataframe, starting_portfolio_value):
    """
    Calculate the maximum drawdown of a portfolio given a dataframe with daily returns.

    Parameters:
    dataframe (pd.DataFrame): A DataFrame containing two columns: 'current_date' and 'daily_return'.
    starting_portfolio_value (float): The initial value of the portfolio in dollars.

    Returns:
    float: The maximum drawdown of the portfolio over the given period.
    """
    # Calculate cumulative returns
    dataframe['cumulative_return'] = dataframe['daily_return'].cumsum()

    # Calculate the running maximum of the cumulative returns to this point
    dataframe['running_max'] = dataframe['cumulative_return'].cummax()

    # Calculate the drawdown, which is the difference between the running max and the cumulative return
    dataframe['drawdown'] = dataframe['running_max'] - dataframe['cumulative_return']

    # Find the maximum drawdown
    max_drawdown = dataframe['drawdown'].max()

    # Convert the maximum drawdown to a percentage of the initial portfolio value
    max_drawdown_percentage = (max_drawdown / starting_portfolio_value) * 100
    return max_drawdown_percentage, max_drawdown

def calculate_portfolio_std(dataframe):
    """
    Calculate the standard deviation of a portfolio's daily percentage returns.

    Parameters:
    dataframe (pd.DataFrame): A DataFrame containing two columns: 'current_date' and 'portfolio_value'.
                              'current_date' should be in 'YYYY-MM-DD' format and 'portfolio_value' should be the total value of the portfolio on that date.

    Returns:
    float: The standard deviation of the portfolio's daily percentage returns.
    """
    # Calculate the standard deviation of these daily returns
    std_deviation = dataframe['daily_return_percent'].std()
    return std_deviation

def calculate_downside_deviation(dataframe, mar=0.0):
    """
    Calculate the downside deviation of a portfolio's daily returns.

    Parameters:
    dataframe (pd.DataFrame): A DataFrame containing at least one column 'portfolio_value' for the total value of the portfolio.
    mar (float, optional): Minimum Acceptable Return (MAR) as a percentage. Default is 0.0.

    Returns:
    float: The downside deviation of the portfolio's daily returns.
    """
    # Calculate the differences from MAR for returns below the MAR
    dataframe['downside'] = np.where(dataframe['daily_return_percent'] < mar, 
                                     (mar - dataframe['daily_return_percent']) ** 2, 
                                     0)

    # Calculate the mean of these squared differences
    mean_squared_downside = dataframe['downside'].mean()

    # Calculate the downside deviation (square root of the mean squared downside)
    downside_deviation = np.sqrt(mean_squared_downside)

    return downside_deviation