"""
Created on August 29, 2022

@authors: Philipp Deibert
"""
from typing import Optional, Union, Callable
import torch
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.contexts.dispatch_context import DispatchContext
from spflow.torch.structure.nodes.leaves.parametric.log_normal import LogNormal


# TODO: MLE dispatch context?


@dispatch(memoize=True) # TODO: swappable
def maximum_likelihood_estimation(leaf: LogNormal, data: torch.Tensor, weights: Optional[torch.Tensor]=None, bias_correction: bool=True, nan_strategy: Optional[Union[str, Callable]]=None) -> None:
    """TODO."""

    # select relevant data for scope
    scope_data = data[:, leaf.scope.query]

    if weights is None:
        weights = torch.ones(data.shape[0])

    if weights.ndim != 1 or weights.shape[0] != data.shape[0]:
        raise ValueError("Number of specified weights for maximum-likelihood estimation does not match number of data points.")

    # reshape weights
    weights = weights.reshape(-1, 1)

    if torch.any(~leaf.check_support(scope_data)):
        raise ValueError("Encountered values outside of the support for 'LogNormal'.")

    # NaN entries (no information)
    nan_mask = torch.isnan(scope_data)

    if torch.all(nan_mask):
        raise ValueError("Cannot compute maximum-likelihood estimation on nan-only data.")

    if nan_strategy is None and torch.any(nan_mask):
        raise ValueError("Maximum-likelihood estimation cannot be performed on missing data by default. Set a strategy for handling missing values if this is intended.")
    
    if isinstance(nan_strategy, str):
        if nan_strategy == "ignore":
            # simply ignore missing data
            scope_data = scope_data[~nan_mask.squeeze(1)]
            weights = weights[~nan_mask.squeeze(1)]
        else:
            raise ValueError("Unknown strategy for handling missing (NaN) values for 'LogNormal'.")
    elif isinstance(nan_strategy, Callable):
        scope_data = nan_strategy(scope_data)
        # TODO: how to handle weights?
    elif nan_strategy is not None:
        raise ValueError(f"Expected 'nan_strategy' to be of type '{type(str)}, or '{Callable}' or '{None}', but was of type {type(nan_strategy)}.")
    
    # normalize weights to sum to n_samples
    weights /= weights.sum() / scope_data.shape[0]

    # total (weighted) number of instances
    n_total = weights.sum()

    # calculate mean and standard deviation from data
    mean_est = (weights * torch.log(scope_data)).sum() / n_total
    
    if bias_correction:
        std_est = torch.sqrt(torch.pow(weights * (torch.log(scope_data)-mean_est), 2).sum() / (n_total - 1))
    else:
        std_est = torch.sqrt(torch.pow(weights * (torch.log(scope_data)-mean_est), 2).sum() / n_total)

    # edge case (if all values are the same, not enough samples or very close to each other)
    if torch.isclose(std_est, torch.tensor(0.0)) or torch.isnan(std_est):
        std_est = 1e-8

    # set parameters of leaf node
    leaf.set_params(mean=mean_est, std=std_est)


@dispatch
def em(leaf: LogNormal, data: torch.Tensor, dispatch_ctx: Optional[DispatchContext]=None) -> None:

    with torch.no_grad():
        # ----- expectation step -----

        # get cached log-likelihood gradients w.r.t. module log-likelihoods
        expectations = dispatch_ctx.cache['log_likelihood'][leaf].grad
        # normalize expectations for better numerical stability
        expectations /= expectations.sum()

        # ----- maximization step -----

        # update parameters through maximum weighted likelihood estimation
        maximum_likelihood_estimation(leaf, data, weights=expectations.squeeze(1), bias_correction=False)

    # NOTE: since we explicitely override parameters in 'maximum_likelihood_estimation', we do not need to zero/None parameter gradients