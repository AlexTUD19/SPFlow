"""
Created on August 29, 2022

@authors: Philipp Deibert
"""
from typing import Optional, Union, Callable
import numpy as np
from spflow.meta.dispatch.dispatch import dispatch
from spflow.base.structure.nodes.leaves.parametric.exponential import Exponential


@dispatch(memoize=True) # TODO: swappable
def maximum_likelihood_estimation(leaf: Exponential, data: np.ndarray, bias_correction: bool=True, nan_strategy: Optional[Union[str, Callable]]=None) -> None:
    """TODO."""

    # select relevant data for scope
    scope_data = data[:, leaf.scope.query]

    if np.any(~leaf.check_support(scope_data)):
        raise ValueError("Encountered values outside of the support for 'Exponential'.")

    # NaN entries (no information)
    nan_mask = np.isnan(scope_data)

    if np.all(nan_mask):
        raise ValueError("Cannot compute maximum-likelihood estimation on nan-only data.")
    
    if nan_strategy is None and np.any(nan_mask):
        raise ValueError("Maximum-likelihood estimation cannot be performed on missing data by default. Set a strategy for handling missing values if this is intended.")
    
    if isinstance(nan_strategy, str):
        if nan_strategy == "ignore":
            # simply ignore missing data
            scope_data = scope_data[~nan_mask]
        else:
            raise ValueError("Unknown strategy for handling missing (NaN) values for 'Exponential'.")
    elif isinstance(nan_strategy, Callable):
        scope_data = nan_strategy(scope_data)
    elif nan_strategy is not None:
        raise ValueError(f"Expected 'nan_strategy' to be of type '{type(str)}, or '{Callable}' or '{None}', but was of type {type(nan_strategy)}.")

    # total number of instances
    n_total = scope_data.shape[0]

    if(bias_correction):
        n_total -= 1

    # cummulative evidence
    cum_rate = scope_data.sum()

    l_est = n_total/cum_rate

    # edge case: if rate 0, set to larger value (should not happen, but just in case)
    if np.isclose(l_est, 0):
        l_est = 1e-8

    # set parameters of leaf node
    leaf.set_params(l=l_est)