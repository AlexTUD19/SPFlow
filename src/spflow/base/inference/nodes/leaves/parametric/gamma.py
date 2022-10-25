# -*- coding: utf-8 -*-
"""Contains inference methods for ``Gamma`` nodes for SPFlow in the 'base' backend.
"""
from spflow.meta.contexts.dispatch_context import DispatchContext, init_default_dispatch_context
from spflow.meta.dispatch.dispatch import dispatch
from spflow.base.structure.nodes.leaves.parametric.gamma import Gamma

from typing import Optional
import numpy as np


@dispatch(memoize=True)  # type: ignore
def log_likelihood(node: Gamma, data: np.ndarray, dispatch_ctx: Optional[DispatchContext]=None) -> np.ndarray:
    r"""Computes log-likelihoods for ``Gamma`` node given input data.

    Log-likelihood for ``Gamma`` is given by the logarithm of its probability distribution function (PDF):

    .. math::

        \log(\text{PDF}(x) = \begin{cases} \log(\frac{\beta^\alpha}{\Gamma(\alpha)}x^{\alpha-1}e^{-\beta x}) & \text{if } x > 0\\
                                           \log(0) & \text{if } x <= 0\end{cases}

    where
        - :math:`x` is the input observation
        - :math:`\Gamma` is the Gamma function
        - :math:`\alpha` is the shape parameter
        - :math:`\beta` is the rate parameter

    Args:
        node:
            Leaf node to perform inference for.
        data:
            Two-dimensional NumPy array containing the input data.
            Each row corresponds to a sample.
        dispatch_ctx:
            Optional dispatch context.

    Returns:
        Two-dimensional NumPy array containing the log-likelihoods of the input data for the sum node.
        Each row corresponds to an input sample.
    """
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # initialize probabilities
    probs = np.zeros((data.shape[0], 1))

    # select relevant data based on node's scope
    data = data[:, node.scope.query]

    # create mask based on marginalized instances (NaNs)
    # keeps default value of 1 (0 in log-space)
    marg_ids = np.isnan(data).sum(axis=-1).astype(bool)

    # create masked based on distribution's support
    valid_ids = node.check_support(data[~marg_ids]).squeeze(1)

    # TODO: suppress checks
    if not all(valid_ids):
        raise ValueError(
            f"Encountered data instances that are not in the support of the Gamma distribution."
        )

    # compute probabilities for all non-marginalized instances
    probs[~marg_ids] = node.dist.logpdf(x=data[~marg_ids])

    return probs