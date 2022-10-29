# -*- coding: utf-8 -*-
"""Contains sampling methods for ``CondGamma`` nodes for SPFlow in the ``base`` backend.
"""
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.contexts.dispatch_context import (
    DispatchContext,
    init_default_dispatch_context,
)
from spflow.meta.contexts.sampling_context import (
    SamplingContext,
    init_default_sampling_context,
)
from spflow.base.structure.nodes.leaves.parametric.cond_gamma import CondGamma

import numpy as np
from typing import Optional


@dispatch  # type: ignore
def sample(
    leaf: CondGamma,
    data: np.ndarray,
    check_support: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
    sampling_ctx: Optional[SamplingContext] = None,
) -> np.ndarray:
    r"""Samples from ``CondGamma`` nodes in the ``base`` backend given potential evidence.

    Samples missing values proportionally to its probability distribution function (PDF).

    Args:
        leaf:
            Leaf node to sample from.
        data:
            Two-dimensional NumPy array containing potential evidence.
            Each row corresponds to a sample.
        check_support:
            Boolean value indicating whether or not if the data is in the support of the leaf distributions.
            Defaults to True.
        dispatch_ctx:
            Optional dispatch context.
        sampling_ctx:
            Optional sampling context containing the instances (i.e., rows) of ``data`` to fill with sampled values and the output indices of the node to sample from.

    Returns:
        Two-dimensional NumPy array containing the sampled values together with the specified evidence.
        Each row corresponds to a sample.
    """
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    sampling_ctx = init_default_sampling_context(sampling_ctx, data.shape[0])

    if any([i >= data.shape[0] for i in sampling_ctx.instance_ids]):
        raise ValueError("Some instance ids are out of bounds for data tensor.")

    # retrieve value for 'alpha','beta'
    alpha, beta = leaf.retrieve_params(data, dispatch_ctx)

    marg_ids = (
        np.isnan(data[:, leaf.scope.query]) == len(leaf.scope.query)
    ).squeeze(1)

    instance_ids_mask = np.zeros(data.shape[0])
    instance_ids_mask[sampling_ctx.instance_ids] = 1

    sampling_ids = marg_ids & instance_ids_mask.astype(bool)

    data[sampling_ids, leaf.scope.query] = leaf.dist(
        alpha=alpha, beta=beta
    ).rvs(size=sampling_ids.sum())

    return data
