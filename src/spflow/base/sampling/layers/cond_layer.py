# -*- coding: utf-8 -*-
"""Contains sampling methods for conditional SPN-like layers for SPFlow in the 'base' backend.
"""
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.contexts.dispatch_context import DispatchContext, init_default_dispatch_context
from spflow.meta.contexts.sampling_context import SamplingContext, init_default_sampling_context
from spflow.base.structure.layers.cond_layer import SPNCondSumLayer
from spflow.base.inference.module import log_likelihood
from spflow.base.sampling.nodes.cond_node import sample
from spflow.base.sampling.module import sample

import numpy as np
from typing import Optional


@dispatch  # type: ignore
def sample(sum_layer: SPNCondSumLayer, data: np.ndarray, dispatch_ctx: Optional[DispatchContext]=None, sampling_ctx: Optional[SamplingContext]=None) -> np.ndarray:
    """Samples from conditional SPN-like sum layers in the 'base' backend given potential evidence.

    Can only sample from at most one output at a time, since all scopes are equal and overlap.
    Samples from each input proportionally to its weighted likelihoods given the evidence.
    Missing values (i.e., NaN) are filled with sampled values.

    Args:
        sum_layer:
            Sum layer to sample from.
        data:
            Two-dimensional NumPy array containing potential evidence.
            Each row corresponds to a sample.
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

    # compute log-likelihoods of this module (needed to initialize log-likelihood cache for placeholder)
    log_likelihood(sum_layer, data, dispatch_ctx=dispatch_ctx)

    # retrieve value for 'weights'
    weights = sum_layer.retrieve_params(data, dispatch_ctx)

    for node, w in zip(sum_layer.nodes, weights):
        dispatch_ctx.update_args(node, {'weights': w})

    # sample accoding to sampling_context
    for node_ids in np.unique(sampling_ctx.output_ids, axis=0):
        if len(node_ids) != 1 or (len(node_ids) == 0 and sum_layer.n_out != 1):
            raise ValueError("Too many output ids specified for outputs over same scope.")

        # single node id
        node_id = node_ids[0]
        node_instance_ids = np.array(sampling_ctx.instance_ids)[np.where(sampling_ctx.output_ids == node_ids)[0]].tolist()

        sample(sum_layer.nodes[node_id], data, dispatch_ctx=dispatch_ctx, sampling_ctx=SamplingContext(node_instance_ids, [[] for i in node_instance_ids]))

    return data