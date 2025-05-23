import pandas as pd
import numpy as np

def detect_outliers_sigma(series, n_std=3):
    """
    Detects outliers in a Pandas Series using the 3-Sigma rule.
    Assumes data is normally distributed.
    Returns a boolean Series where True indicates an outlier.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("Input must be a Pandas Series.")
    if series.empty or not pd.api.types.is_numeric_dtype(series):
        return pd.Series([False] * len(series), index=series.index) # No outliers if not numeric or empty
        
    mean = series.mean()
    std = series.std()
    
    # Avoid division by zero or issues with zero standard deviation
    if std == 0:
        return pd.Series([False] * len(series), index=series.index) # No outliers if std is zero
        
    lower_bound = mean - n_std * std
    upper_bound = mean + n_std * std
    
    return (series < lower_bound) | (series > upper_bound)

def detect_outliers_quantile(series, lower_quantile=0.01, upper_quantile=0.99):
    """
    Detects outliers in a Pandas Series using quantiles.
    Returns a boolean Series where True indicates an outlier.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("Input must be a Pandas Series.")
    if series.empty or not pd.api.types.is_numeric_dtype(series):
        return pd.Series([False] * len(series), index=series.index)

    q_low = series.quantile(lower_quantile)
    q_high = series.quantile(upper_quantile)
    
    # If quantiles are the same (e.g. constant series or many identical values),
    # then nothing is an outlier by this method.
    if q_low == q_high:
        return pd.Series([False] * len(series), index=series.index)
        
    return (series < q_low) | (series > q_high)

def cap_outliers(series, lower_bound, upper_bound):
    """
    Caps outliers in a Pandas Series to the provided lower and upper bounds.
    Returns the Series with outliers capped.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("Input must be a Pandas Series.")
    if series.empty or not pd.api.types.is_numeric_dtype(series):
        return series.copy() # Return as is if not numeric or empty
        
    return series.clip(lower=lower_bound, upper=upper_bound)
