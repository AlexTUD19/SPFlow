"""
Created on August 29, 2022

@authors: Philipp Deibert
"""
from typing import Optional, Union, Callable
import numpy as np
from spflow.meta.dispatch.dispatch import dispatch
from spflow.base.structure.nodes.leaves.parametric.poisson import Poisson


# TODO: MLE dispatch context?


@dispatch(memoize=True)
def maximum_likelihood_estimation(leaf: Poisson, data: np.ndarray, weights: Optional[np.ndarray]=None, bias_correction: bool=True, nan_strategy: Optional[Union[str, Callable]]=None) -> None:
    """TODO."""

    # select relevant data for scope
    scope_data = data[:, leaf.scope.query]

    if weights is None:
        weights = np.ones(data.shape[0])

    if weights.ndim != 1 or weights.shape[0] != data.shape[0]:
        raise ValueError("Number of specified weights for maximum-likelihood estimation does not match number of data points.")

    # reshape weights
    weights = weights.reshape(-1, 1)

    if np.any(~leaf.check_support(scope_data)):
        raise ValueError("Encountered values outside of the support for 'Poisson'.")

    # NaN entries (no information)
    nan_mask = np.isnan(scope_data)

    if np.all(nan_mask):
        raise ValueError("Cannot compute maximum-likelihood estimation on nan-only data.")

    if nan_strategy is None and np.any(nan_mask):
        raise ValueError("Maximum-likelihood estimation cannot be performed on missing data by default. Set a strategy for handling missing values if this is intended.")
    
    if isinstance(nan_strategy, str):
        if nan_strategy == "ignore":
            # simply ignore missing data
            scope_data = scope_data[~nan_mask.squeeze(1)]
            weights = weights[~nan_mask.squeeze(1)]
        else:
            raise ValueError("Unknown strategy for handling missing (NaN) values for 'Poisson'.")
    elif isinstance(nan_strategy, Callable):
        scope_data = nan_strategy(scope_data)
        # TODO: how to handle missing data?
    elif nan_strategy is not None:
        raise ValueError(f"Expected 'nan_strategy' to be of type '{type(str)}, or '{Callable}' or '{None}', but was of type {type(nan_strategy)}.")

    # normalize weights to sum to n_samples
    weights /= weights.sum() / data.shape[0]

    # total number of instances
    n_total = weights.sum()

    # estimate rate parameter from data
    l_est = (weights * scope_data).sum() / n_total

    # edge case: if rate 0, set to larger value (should not happen, but just in case)
    if np.isclose(l_est, 0):
        l_est = 1e-8

    # set parameters of leaf node
    leaf.set_params(l=l_est)