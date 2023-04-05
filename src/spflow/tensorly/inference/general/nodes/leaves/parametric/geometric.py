"""Contains inference methods for ``Geometric`` nodes for SPFlow in the ``base`` backend.
"""
from typing import Optional

import tensorly as tl
from spflow.tensorly.utils.helper_functions import tl_isnan, T

from spflow.tensorly.structure.general.nodes.leaves.parametric.geometric import Geometric
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.dispatch.dispatch_context import (
    DispatchContext,
    init_default_dispatch_context,
)


@dispatch(memoize=True)  # type: ignore
def log_likelihood(
    node: Geometric,
    data: T,
    check_support: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
) -> T:
    r"""Computes log-likelihoods for ``Geometric`` node in the ``base`` backend given input data.

    Log-likelihood for ``Geometric`` is given by the logarithm of its probability distribution function (PDF):

    .. math::

        \log(\text{PMF}(k)) =  \log(p(1-p)^{k-1})

    where
        - :math:`k` is the number of trials
        - :math:`p` is the success probability of each trial

    Missing values (i.e., NaN) are marginalized over.

    Args:
        node:
            Leaf node to perform inference for.
        data:
            Two-dimensional NumPy array containing the input data.
            Each row corresponds to a sample.
        check_support:
            Boolean value indicating whether or not if the data is in the support of the distribution.
            Defaults to True.
        dispatch_ctx:
            Optional dispatch context.

    Returns:
        Two-dimensional NumPy array containing the log-likelihoods of the input data for the sum node.
        Each row corresponds to an input sample.

    Raises:
        ValueError: Data outside of support.
    """
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # initialize probabilities
    probs = tl.zeros((tl.shape(data)[0], 1))

    # select relevant data based on node's scope
    data = data[:, node.scope.query]

    # create mask based on marginalized instances (NaNs)
    # keeps default value of 1 (0 in log-space)
    marg_ids = tl.tensor(tl.sum(tl_isnan(data),axis=-1), dtype=bool)

    if check_support:
        # create masked based on distribution's support
        valid_ids = node.check_support(data[~marg_ids], is_scope_data=True).squeeze(1)

        if not all(valid_ids):
            raise ValueError(f"Encountered data instances that are not in the support of the Geometric distribution.")

    # compute probabilities for all non-marginalized instances
    probs[~marg_ids] = node.dist.logpmf(k=data[~marg_ids])

    return probs
