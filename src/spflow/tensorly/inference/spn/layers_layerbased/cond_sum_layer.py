"""Contains inference methods for SPN-like conditional layers for SPFlow in the ``torch`` backend.
"""
from typing import Optional

import tensorly as tl
from spflow.tensorly.utils.helper_functions import T, tl_unsqueeze, tl_logsumexp, get_device
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.dispatch.dispatch_context import (
    DispatchContext,
    init_default_dispatch_context,
)
from spflow.tensorly.structure.spn.layer_layerbased.cond_sum_layer import CondSumLayer


@dispatch(memoize=True)  # type: ignore
def log_likelihood(
    sum_layer: CondSumLayer,
    data: T,
    check_support: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
) -> T:
    """Computes log-likelihoods for conditional SPN-like sum layers given input data in the ``torch`` backend.

    Log-likelihoods for sum nodes are the logarithm of the sum of weighted exponentials (LogSumExp) of its input likelihoods (weighted sum in linear space).
    Missing values (i.e., NaN) are marginalized over.

    Args:
        sum_layer:
            Sum layer to perform inference for.
        data:
            Two-dimensional PyTorch tensor containing the input data.
            Each row corresponds to a sample.
        check_support:
            Boolean value indicating whether or not if the data is in the support of the leaf distributions.
            Defaults to True.
        dispatch_ctx:
            Optional dispatch context.

    Returns:
        Two-dimensional PyTorch tensor containing the log-likelihoods of the input data for the sum node.
        Each row corresponds to an input sample.
    """
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # retrieve value for 'weights'
    weights = sum_layer.retrieve_params(data, dispatch_ctx)

    # compute child log-likelihoods
    child_lls = tl.concatenate(
        [
            log_likelihood(
                child,
                data,
                check_support=check_support,
                dispatch_ctx=dispatch_ctx,
            )
            for child in sum_layer.children
        ],
        axis=1,
    )

    weighted_lls = tl_unsqueeze(child_lls,1) + tl.log(weights)

    return tl_logsumexp(weighted_lls, axis=-1)
