"""Contains inference methods for ``HypergeometricLayer`` leaves for SPFlow in the ``base`` backend.
"""
from typing import Optional

import numpy as np
import tensorly as tl

from spflow.base.structure.general.layers.leaves.parametric.hypergeometric import (
    HypergeometricLayer,
)
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.dispatch.dispatch_context import (
    DispatchContext,
    init_default_dispatch_context,
)


@dispatch(memoize=True)  # type: ignore
def log_likelihood(
    layer: HypergeometricLayer,
    data: tl.tensor,
    check_support: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
) -> tl.tensor:
    r"""Computes log-likelihoods for ``HypergeometricLayer`` leaves in the ``base`` backend given input data.

    Log-likelihood for ``HypergeometricLayer`` is given by the logarithm of its individual probability mass functions (PMFs):

    .. math::

        \log(\text{PMF}(k)) = \log(\frac{\binom{M}{k}\binom{N-M}{n-k}}{\binom{N}{n}})

    where
        - :math:`\binom{n}{k}` is the binomial coefficient (n choose k)
        - :math:`N` is the total number of entities
        - :math:`M` is the number of entities with property of interest
        - :math:`n` is the number of draws
        - :math:`k` s the number of observed entities

    Missing values (i.e., NaN) are marginalized over.

    Args:
        node:
            Leaf node to perform inference for.
        data:
            Two-dimensional NumPy array containing the input data.
            Each row corresponds to a sample.
        check_support:
            Boolean value indicating whether or not if the data is in the support of the leaf distributions.
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

    # weight child log-likelihoods (sum in log-space) and compute log-sum-exp
    return tl.concatenate(
        [
            log_likelihood(
                node,
                data,
                check_support=check_support,
                dispatch_ctx=dispatch_ctx,
            )
            for node in layer.nodes
        ],
        axis=1,
    )
