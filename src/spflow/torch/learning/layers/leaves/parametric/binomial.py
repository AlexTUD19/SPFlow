"""
Created on September 25, 2022

@authors: Philipp Deibert
"""
from typing import Optional, Union, Callable
import torch
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.contexts.dispatch_context import DispatchContext
from spflow.torch.structure.layers.leaves.parametric.binomial import BinomialLayer


# TODO: MLE dispatch context?


@dispatch(memoize=True)
def maximum_likelihood_estimation(layer: BinomialLayer, data: torch.Tensor, weights: Optional[torch.Tensor]=None, bias_correction: bool=True, nan_strategy: Optional[Union[str, Callable]]=None) -> None:
    """TODO."""

    # select relevant data for scope
    scope_data = torch.hstack([data[:, scope.query] for scope in layer.scopes_out])

    if weights is None:
        weights = torch.ones(data.shape[0], layer.n_out)

    if (weights.ndim == 1 and weights.shape[0] != data.shape[0]) or \
       (weights.ndim == 2 and (weights.shape[0] != data.shape[0] or weights.shape[1] != layer.n_out)) or \
       (weights.ndim not in [1, 2]):
            raise ValueError("Number of specified weights for maximum-likelihood estimation does not match number of data points.")

    if weights.ndim == 1:
        # broadcast weights
        weights = weights.repeat(layer.n_out, 1).T

    if torch.any(~layer.check_support(scope_data)):
        raise ValueError("Encountered values outside of the support for 'BinomialLayer'.")

    # NaN entries (no information)
    nan_mask = torch.isnan(scope_data)

    # check if any columns (i.e., data for a output scope) contain only NaN values
    if torch.any(nan_mask.sum(dim=0) == scope_data.shape[0]):
        raise ValueError("Cannot compute maximum-likelihood estimation on nan-only data for a specified scope.")

    if nan_strategy is None and torch.any(nan_mask):
        raise ValueError("Maximum-likelihood estimation cannot be performed on missing data by default. Set a strategy for handling missing values if this is intended.")
    
    if isinstance(nan_strategy, str):
        # simply ignore missing data
        if nan_strategy == "ignore":

            # set weights for NaN entries to zero
            weights = weights * ~nan_mask
            
            # normalize weights to sum to n_samples
            weights /= weights.sum(dim=0) / scope_data.shape[0]

            # total (weighted) number of instances
            n_total = weights.sum(dim=0) * layer.n # never zero since we checked that earlier

            # count number of total successes
            n_success = (weights * torch.nan_to_num(scope_data, nan=0.0)).sum(dim=0, dtype=torch.get_default_dtype())

            # estimate (weighted) success probability
            p_est = n_success/n_total
        else:
            raise ValueError("Unknown strategy for handling missing (NaN) values for 'BinomialLayer'.")
    elif isinstance(nan_strategy, Callable) or nan_strategy is None:
        if isinstance(nan_strategy, Callable):
            scope_data = nan_strategy(scope_data)
            # TODO: how to handle weights?
        
        # normalize weights to sum to n_samples
        weights /= weights.sum(dim=0) / scope_data.shape[0]

        # total (weighted) number of instances times number of trials per instance
        n_total = (weights.sum(dim=0) * layer.n).type(dtype=torch.get_default_dtype())

        # count (weighted) number of total successes
        n_success = (weights * scope_data).sum(dim=0, dtype=torch.get_default_dtype())

        # estimate (weighted) success probability
        p_est = n_success/n_total
    else:
        raise ValueError(f"Expected 'nan_strategy' to be of type '{type(str)}, or '{Callable}' or '{None}', but was of type {type(nan_strategy)}.")

    # edge case: if prob. 1 (or 0), set to smaller (or larger) value
    p_est[torch.allclose(p_est, torch.tensor(0.0))] = 1e-8
    p_est[torch.allclose(p_est, torch.tensor(1.0))] = 1-1e-8

    # set parameters of leaf node
    layer.set_params(n=layer.n, p=p_est)