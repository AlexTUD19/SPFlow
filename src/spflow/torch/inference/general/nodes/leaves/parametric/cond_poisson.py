"""Contains inference methods for ``CondPoisson`` nodes for SPFlow in the ``torch`` backend.
"""
from typing import Optional

import torch

from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.dispatch.dispatch_context import (
    DispatchContext,
    init_default_dispatch_context,
)
from spflow.torch.structure.general.nodes.leaves.parametric.cond_poisson import (
    CondPoisson,
)


@dispatch(memoize=True)  # type: ignore
def log_likelihood(
    leaf: CondPoisson,
    data: torch.Tensor,
    check_support: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
) -> torch.Tensor:
    r"""Computes log-likelihoods for ``CondPoisson`` node given input data in the ``torch`` backend.

    Log-likelihood for ``CondPoisson`` is given by the logarithm of its probability mass function (PMF):

    .. math::

        \log(\text{PMF}(k) = \lambda^k\frac{e^{-\lambda}}{k!})

    where
        - :math:`k` is the number of occurrences
        - :math:`\lambda` is the rate parameter

    Missing values (i.e., NaN) are marginalized over.

    Args:
        node:
            Leaf node to perform inference for.
        data:
            Two-dimensional PyTorch tensor containing the input data.
            Each row corresponds to a sample.
        check_support:
            Boolean value indicating whether or not if the data is in the support of the distribution.
            Defaults to True.
        dispatch_ctx:
            Optional dispatch context.

    Returns:
        Two-dimensional PyTorch tensor containing the log-likelihoods of the input data for the sum node.
        Each row corresponds to an input sample.
    """
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    batch_size: int = data.shape[0]

    # retrieve value for 'l'
    l = leaf.retrieve_params(data, dispatch_ctx)

    # get information relevant for the scope
    scope_data = data[:, leaf.scope.query]

    # initialize empty tensor (number of output values matches batch_size)
    log_prob: torch.Tensor = torch.empty(batch_size, 1).type(leaf.dtype).to(leaf.device)

    # ----- marginalization -----

    marg_ids = torch.isnan(scope_data).sum(dim=1) == len(leaf.scope.query)

    # if the scope variables are fully marginalized over (NaNs) return probability 1 (0 in log-space)
    log_prob[marg_ids] = 0.0

    # ----- log probabilities -----

    if check_support:
        # create masked based on distribution's support
        valid_ids = leaf.check_support(scope_data[~marg_ids], is_scope_data=True).squeeze(1)

        if not all(valid_ids):
            raise ValueError(f"Encountered data instances that are not in the support of the CondPoisson distribution.")

    # compute probabilities for values inside distribution support
    log_prob[~marg_ids] = leaf.dist(l=l).log_prob(scope_data[~marg_ids])

    return log_prob
