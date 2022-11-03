# -*- coding: utf-8 -*-
"""Contains sampling methods for SPN-like Hadamard layers for SPFlow in the ``base`` backend.
"""
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.dispatch.dispatch_context import (
    DispatchContext,
    init_default_dispatch_context,
)
from spflow.meta.dispatch.sampling_context import (
    SamplingContext,
    init_default_sampling_context,
)
from spflow.base.structure.spn.layers.hadamard_layer import SPNHadamardLayer

from typing import Optional
import numpy as np


@dispatch  # type: ignore
def sample(
    hadamard_layer: SPNHadamardLayer,
    data: np.ndarray,
    check_support: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
    sampling_ctx: Optional[SamplingContext] = None,
) -> np.ndarray:
    """Samples from SPN-like element-wise product layers in the ``base`` backend given potential evidence.

    Can only sample from at most one output at a time, since all scopes are equal and overlap.
    Recursively samples from each input.
    Missing values (i.e., NaN) are filled with sampled values.

    Args:
        hadamard_layer:
            Hadamard layer to sample from.
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

    Raises:
        ValueError: Sampling from invalid number of outputs.
    """
    # initialize contexts
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    sampling_ctx = init_default_sampling_context(sampling_ctx, data.shape[0])

    # sample accoding to sampling_context
    for node_ids in np.unique(sampling_ctx.output_ids, axis=0):
        if len(node_ids) != 1 or (
            len(node_ids) == 0 and hadamard_layer.n_out != 1
        ):
            raise ValueError(
                "Too many output ids specified for outputs over same scope."
            )

        node_id = node_ids[0]
        node_instance_ids = np.array(sampling_ctx.instance_ids)[
            np.where(sampling_ctx.output_ids == node_ids)[0]
        ].tolist()

        sample(
            hadamard_layer.nodes[node_id],
            data,
            check_support=check_support,
            dispatch_ctx=dispatch_ctx,
            sampling_ctx=SamplingContext(
                node_instance_ids, [[] for _ in node_instance_ids]
            ),
        )

    return data