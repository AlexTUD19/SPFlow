# -*- coding: utf-8 -*-
"""Contains learning methods for ``MultivariateGaussianLayer`` leaves for SPFlow in the ``torch`` backend.
"""
from typing import Optional, Union, Callable
import torch
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.contexts.dispatch_context import DispatchContext, init_default_dispatch_context
from spflow.torch.learning.nodes.leaves.parametric.multivariate_gaussian import maximum_likelihood_estimation
from spflow.torch.structure.layers.leaves.parametric.multivariate_gaussian import MultivariateGaussianLayer


@dispatch(memoize=True)  # type: ignore
def maximum_likelihood_estimation(layer: MultivariateGaussianLayer, data: torch.Tensor, weights: Optional[torch.Tensor]=None, bias_correction: bool=True, nan_strategy: Optional[Union[str, Callable]]=None, check_support: bool=True, dispatch_ctx: Optional[DispatchContext]=None) -> None:
    r"""Maximum (weighted) likelihood estimation (MLE) of ``MultivariateGaussianLayer`` leaves' parameters in the ``torch`` backend.

    Estimates the means and covariance matrices :math:`\mu` and :math:`\Sigma` of each Multivariate Gaussian distribution from data, as follows:

    .. math::

        \mu^{\*}=\frac{1}{n\sum_{i=1}^N w_i}\sum_{i=1}^{N}w_ix_i\\
        \Sigma^{\*}=\frac{1}{\sum_{i=1}^N w_i}\sum_{i=1}^{N}w_i(x_i-\mu^{\*})(x_i-\mu^{\*})^T

    or

    .. math::

        \Sigma^{\*}=\frac{1}{(\sum_{i=1}^N w_i)-1}\sum_{i=1}^{N}w_i(x_i-\mu^{\*})(x_i-\mu^{\*})^T

    if bias correction is used, where
        - :math:`N` is the number of samples in the data set
        - :math:`x_i` is the data of the relevant scope for the `i`-th sample of the data set
        - :math:`w_i` is the weight for the `i`-th sample of the data set
    
    Weights are normalized to sum up to :math:`N` per row.

    Args:
        leaf:
            Leaf node to estimate parameters of.
        data:
            Two-dimensional PyTorch tensor containing the input data.
            Each row corresponds to a sample.
        weights:
            Optional one- or two-dimensional PyTorch tensor containing non-negative weights for all data samples and nodes.
            Must match number of samples in ``data``.
            If a one-dimensional PyTorch tensor is given, the weights are broadcast to all nodes.
            Defaults to None in which case all weights are initialized to ones.
        bias_corrections:
            Boolen indicating whether or not to correct possible biases.
            Defaults to True.
        nan_strategy:
            Optional string or callable specifying how to handle missing data.
            If 'ignore', missing values (i.e., NaN entries) are ignored.
            If a callable, it is called using ``data`` and should return another PyTorch tensor of same size.
            Defaults to None.
        check_support:
            Boolean value indicating whether or not if the data is in the support of the leaf distributions.
            Defaults to True.
        dispatch_ctx:
            Optional dispatch context.

    Raises:
        ValueError: Invalid arguments.
    """
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    if weights is None:
        weights = torch.ones((data.shape[0], layer.n_out))

    if (weights.ndim == 1 and weights.shape[0] != data.shape[0]) or \
       (weights.ndim == 2 and (weights.shape[0] != data.shape[0] or weights.shape[1] != layer.n_out)) or \
       (weights.ndim not in [1, 2]):
            raise ValueError("Number of specified weights for maximum-likelihood estimation does not match number of data points.")

    if weights.ndim == 1:
        # broadcast weights
        weights = torch.unsqueeze(weights, 1).repeat(layer.n_out, 1)

    for node, node_weights in zip(layer.nodes, weights.T):
        maximum_likelihood_estimation(node, data, node_weights, bias_correction=bias_correction, nan_strategy=nan_strategy, check_support=check_support, dispatch_ctx=dispatch_ctx)


@dispatch(memoize=True)  # type: ignore
def em(layer: MultivariateGaussianLayer, data: torch.Tensor, check_support: bool=True, dispatch_ctx: Optional[DispatchContext]=None) -> None:
    """Performs a single expectation maximizaton (EM) step for ``MultivariateGaussianLayer`` in the ``torch`` backend.

    Args:
        layer:
            Leaf layer to perform EM step for.
        data:
            Two-dimensional PyTorch tensor containing the input data.
            Each row corresponds to a sample.
        check_support:
            Boolean value indicating whether or not if the data is in the support of the leaf distributions.
            Defaults to True.
        dispatch_ctx:
            Optional dispatch context.
    """
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # call EM on internal nodes
    for node in layer.nodes:
        em(node, data, check_support=check_support, dispatch_ctx=dispatch_ctx)