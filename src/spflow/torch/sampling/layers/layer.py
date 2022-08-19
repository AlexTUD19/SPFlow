"""
Created on August 08, 2022

@authors: Philipp Deibert
"""
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.contexts.dispatch_context import DispatchContext, init_default_dispatch_context
from spflow.meta.contexts.sampling_context import SamplingContext, init_default_sampling_context
from spflow.torch.structure.layers.layer import SPNSumLayer, SPNProductLayer, SPNPartitionLayer
from spflow.torch.inference.module import log_likelihood
from spflow.torch.sampling.module import sample

import torch
import numpy as np
from typing import Optional
import itertools


@dispatch
def sample(sum_layer: SPNSumLayer, data: torch.Tensor, dispatch_ctx: Optional[DispatchContext]=None, sampling_ctx: Optional[SamplingContext]=None) -> torch.Tensor:
    """TODO"""
    # initialize contexts
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    sampling_ctx = init_default_sampling_context(sampling_ctx, data.shape[0])

    # all nodes in sum layer have same scope
    if any([len(out) != 1 for out in sampling_ctx.output_ids]):
        raise ValueError("'SPNSumLayer only allows single output sampling.")

    # create mask for instane ids
    instance_ids_mask = torch.zeros(data.shape[0]).bool()
    instance_ids_mask[sampling_ctx.instance_ids] = True

    # compute log likelihoods for sum "nodes"
    partition_ll = torch.concat([log_likelihood(child, data, dispatch_ctx=dispatch_ctx) for child in sum_layer.children()], dim=1)

    children = list(sum_layer.children())

    for node_id, instances in sampling_ctx.group_output_ids(sum_layer.n_out):

        # sample branches
        input_ids = torch.multinomial(sum_layer.weights[node_id]*partition_ll[instances].exp(), num_samples=1)

        # get correct child id and corresponding output id
        child_ids, output_ids = sum_layer.input_to_output_ids(input_ids)

        # group by child ids
        for child_id in np.unique(child_ids):

            child_instance_ids = torch.tensor(instances)[torch.tensor(child_ids) == child_id].tolist()
            child_output_ids = np.array(output_ids)[np.array(child_ids) == child_id].tolist()

            # sample from partition node
            sample(children[child_id], data, dispatch_ctx=dispatch_ctx, sampling_ctx=SamplingContext(child_instance_ids, child_output_ids))

    return data


@dispatch
def sample(product_layer: SPNProductLayer, data: torch.Tensor, dispatch_ctx: Optional[DispatchContext]=None, sampling_ctx: Optional[SamplingContext]=None) -> torch.Tensor:
    """TODO"""
    # initialize contexts
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    sampling_ctx = init_default_sampling_context(sampling_ctx, data.shape[0])

    # all nodes in sum layer have same scope
    if any([len(out) != 1 for out in sampling_ctx.output_ids]):
        raise ValueError("'SPNProductLayer only allows single output sampling.")

    # all product nodes are over (all) children
    for child in product_layer.children():
        sample(child, data, dispatch_ctx=dispatch_ctx, sampling_ctx=SamplingContext(sampling_ctx.instance_ids, [list(range(child.n_out)) for _ in sampling_ctx.instance_ids]))

    return data


@dispatch
def sample(partition_layer: SPNPartitionLayer, data: torch.Tensor, dispatch_ctx: Optional[DispatchContext]=None, sampling_ctx: Optional[SamplingContext]=None) -> torch.Tensor:
    """TODO"""
    # initialize contexts
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    sampling_ctx = init_default_sampling_context(sampling_ctx, data.shape[0])

    # all nodes in sum layer have same scope
    if any([len(out) != 1 for out in sampling_ctx.output_ids]):
        raise ValueError("'SPNPartitionLayer only allows single output sampling.")

    partition_indices = torch.tensor_split(torch.arange(0, partition_layer.n_out), torch.cumsum(torch.tensor(partition_layer.partition_sizes), dim=0)[:-1])
    input_ids_per_node = torch.cartesian_prod(*partition_indices)

    children = list(partition_layer.children())

    # sample accoding to sampling_context
    for node_id, instances in sampling_ctx.group_output_ids(partition_layer.n_out):

        # get input ids for this node
        input_ids = input_ids_per_node[node_id]
        child_ids, output_ids = partition_layer.input_to_output_ids(input_ids.tolist())

        # group by child ids
        for child_id in np.unique(child_ids):

            child_output_ids = np.array(output_ids)[np.array(child_ids) == child_id].tolist()

            # sample from partition node
            sample(children[child_id], data, dispatch_ctx=dispatch_ctx, sampling_ctx=SamplingContext(instances, [child_output_ids for _ in instances]))

    return data