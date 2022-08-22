"""
Created on August 09, 2022

@authors: Philipp Deibert
"""
from typing import List, Union, Optional, Iterable
from copy import deepcopy

import numpy as np
import torch

from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.contexts.dispatch_context import DispatchContext, init_default_dispatch_context
from spflow.meta.scope.scope import Scope
from spflow.torch.structure.module import Module
from spflow.base.structure.layers.layer import SPNSumLayer as BaseSPNSumLayer
from spflow.base.structure.layers.layer import SPNProductLayer as BaseSPNProductLayer


class SPNSumLayer(Module):
    """Layer representing multiple SPN-like sum nodes over all children.

    Args:
        n: number of output nodes.
        children: list of child modules.
    """
    def __init__(self, n_nodes: int, children: List[Module], weights: Optional[Union[np.ndarray, torch.Tensor, List[List[float]], List[float]]]=None, **kwargs) -> None:
        """TODO"""

        if(n_nodes < 1):
            raise ValueError("Number of nodes for 'SumLayer' must be greater of equal to 1.")

        if not children:
            raise ValueError("'SPNSumLayer' requires at least one child to be specified.")

        super(SPNSumLayer, self).__init__(children=children, **kwargs)

        self._n_out = n_nodes
        self.n_in = sum(child.n_out for child in self.children())

        # parse weights
        if(weights is None):
            weights = torch.rand(self.n_out, self.n_in) + 1e-08  # avoid zeros
            weights /= weights.sum(dim=-1, keepdims=True)

        self.weights = weights

        # compute scope
        scope = None

        for child in children:
            for s in child.scopes_out:
                if(scope is None):
                    scope = s
                else:
                    if not scope.equal_query(s):
                        raise ValueError(f"'SPNSumLayer' requires child scopes to have the same query variables.")
                
                scope = scope.union(s)
        
        self.scope = scope

    @property
    def n_out(self) -> int:
        """Returns the number of outputs for this module."""
        return self._n_out
    
    @property
    def scopes_out(self) -> List[Scope]:
        """TODO"""
        return [self.scope for _ in range(self.n_out)]

    @property
    def weights(self) -> np.ndarray:
        """TODO"""
        return self._weights

    @weights.setter
    def weights(self, values: Union[np.ndarray, torch.Tensor, List[List[float]], List[float]]) -> None:
        """TODO"""
        if isinstance(values, list) or isinstance(values, np.ndarray):
            values = torch.tensor(values).type(torch.get_default_dtype())
        if(values.ndim != 1 and values.ndim != 2):
            raise ValueError(f"Torch tensor of weight values for 'SPNSumLayer' is expected to be one- or two-dimensional, but is {values.ndim}-dimensional.")
        if not torch.all(values > 0):
            raise ValueError("Weights for 'SPNSumLayer' must be all positive.")
        if not torch.allclose(values.sum(dim=-1), torch.tensor(1.0)):
            raise ValueError("Weights for 'SPNSumLayer' must sum up to one in last dimension.")
        if not (values.shape[-1] == self.n_in):
            raise ValueError("Number of weights for 'SPNSumLayer' in last dimension does not match total number of child outputs.")
        
        # same weights for all sum nodes
        if(values.ndim == 1):
            self._weights = values.repeat((self.n_out, 1)).clone()
        if(values.ndim == 2):
            # same weights for all sum nodes
            if(values.shape[0] == 1):
                self._weights = values.repeat((self.n_out, 1)).clone()
            # different weights for all sum nodes
            elif(values.shape[0] == self.n_out):
                self._weights = values.clone()
            # incorrect number of specified weights
            else:
                raise ValueError(f"Incorrect number of weights for 'SPNSumLayer'. Size of first dimension must be either 1 or {self.n_out}, but is {values.shape[0]}.")


@dispatch(memoize=True)
def marginalize(layer: SPNSumLayer, marg_rvs: Iterable[int], prune: bool=True, dispatch_ctx: Optional[DispatchContext]=None) -> Union[None, SPNSumLayer]:
    """TODO"""
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # compute node scope (node only has single output)
    layer_scope = layer.scope

    mutual_rvs = set(layer_scope.query).intersection(set(marg_rvs))

    # node scope is being fully marginalized
    if(len(mutual_rvs) == len(layer_scope.query)):
        return None
    # node scope is being partially marginalized
    elif mutual_rvs:
        # TODO: pruning
        marg_children = []

        # marginalize child modules
        for child in layer.children():
            marg_child = marginalize(child, marg_rvs, prune=prune, dispatch_ctx=dispatch_ctx)

            # if marginalized child is not None
            if marg_child:
                marg_children.append(marg_child)
        
        return SPNSumLayer(n_nodes=layer.n_out, children=marg_children, weights=layer.weights)
    else:
        return deepcopy(layer)


@dispatch(memoize=True)
def toBase(sum_layer: SPNSumLayer, dispatch_ctx: Optional[DispatchContext]=None) -> BaseSPNSumLayer:
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    return BaseSPNSumLayer(n_nodes=sum_layer.n_out, children=[toBase(child, dispatch_ctx=dispatch_ctx) for child in sum_layer.children()], weights=sum_layer.weights.detach().cpu().numpy())


@dispatch(memoize=True)
def toTorch(sum_layer: BaseSPNSumLayer, dispatch_ctx: Optional[DispatchContext]=None) -> SPNSumLayer:
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    return SPNSumLayer(n_nodes=sum_layer.n_out, children=[toTorch(child, dispatch_ctx=dispatch_ctx) for child in sum_layer.children], weights=sum_layer.weights)


class SPNProductLayer(Module):
    """Layer representing multiple SPN-like product nodes over all children.

    Args:
        n: number of output nodes.
        children: list of child modules.
    """
    def __init__(self, n_nodes: int, children: List[Module], **kwargs) -> None:
        """TODO"""

        if(n_nodes < 1):
            raise ValueError("Number of nodes for 'ProductLayer' must be greater of equal to 1.")

        self._n_out = n_nodes

        if not children:
            raise ValueError("'SPNProductLayer' requires at least one child to be specified.")

        super(SPNProductLayer, self).__init__(children=children, **kwargs)

        # compute scope
        scope = Scope()

        for child in children:
            for s in child.scopes_out:
                if not scope.isdisjoint(s):
                    raise ValueError(f"'SPNProductNode' requires child scopes to be pair-wise disjoint.")

                scope = scope.union(s)

        self.scope = scope

    @property
    def n_out(self) -> int:
        """Returns the number of outputs for this module."""
        return self._n_out
    
    @property
    def scopes_out(self) -> List[Scope]:
        return [self.scope for _ in range(self.n_out)]


@dispatch(memoize=True)
def marginalize(layer: SPNProductLayer, marg_rvs: Iterable[int], prune: bool=True, dispatch_ctx: Optional[DispatchContext]=None) -> Union[None, SPNProductLayer]:
    """TODO"""
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # compute layer scope (same for all outputs)
    layer_scope = layer.scope

    mutual_rvs = set(layer_scope.query).intersection(set(marg_rvs))

    # layer scope is being fully marginalized over
    if(len(mutual_rvs) == len(layer_scope.query)):
        return None
    # node scope is being partially marginalized
    elif mutual_rvs:

        marg_children = []

        # marginalize child modules
        for child in layer.children():
            marg_child = marginalize(child, marg_rvs, prune=prune, dispatch_ctx=dispatch_ctx)

            # if marginalized child is not None
            if marg_child:
                marg_children.append(marg_child)
       
        return SPNProductLayer(n_nodes=layer.n_out, children=marg_children)
    else:
        return deepcopy(layer)


@dispatch(memoize=True)
def toBase(product_layer: SPNProductLayer, dispatch_ctx: Optional[DispatchContext]=None) -> BaseSPNProductLayer:
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    return BaseSPNProductLayer(n_nodes=product_layer.n_out, children=[toBase(child, dispatch_ctx=dispatch_ctx) for child in product_layer.children()])


@dispatch(memoize=True)
def toTorch(product_layer: BaseSPNProductLayer, dispatch_ctx: Optional[DispatchContext]=None) -> SPNProductLayer:
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    return SPNProductLayer(n_nodes=product_layer.n_out, children=[toTorch(child, dispatch_ctx=dispatch_ctx) for child in product_layer.children])


class SPNPartitionLayer(Module):
    """Layer representing multiple SPN-like product nodes partitions.

    Args:
        child_partitions: list of lists of child modules with pair-wise disoint scopes between partitions.
    """
    def __init__(self, child_partitions: List[List[Module]], **kwargs) -> None:
        """TODO"""

        if len(child_partitions) == 0:
            raise ValueError("No partitions for 'SPNPartitionLayer' specified.")

        scope = Scope()
        self.partition_sizes = []
        self.modules_per_partition = []
        self.partition_scopes = []

        # parse partitions
        for partition in child_partitions:
            # check if partition is empty 
            if len(partition) == 0:
                raise ValueError("All partitions for 'SPNPartitionLayer' must be non-empty")
            
            self.modules_per_partition.append(len(partition))
            partition_scope = Scope()
            size = 0

            # iterate over modules in this partition
            for child in partition:
                # increase total number of outputs of this partition
                size += child.n_out

                # for each output scope
                for s in child.scopes_out:
                    # check if query scope is the same
                    if partition_scope.equal_query(s) or partition_scope.isempty():
                        partition_scope = partition_scope.union(s)
                    else:
                        raise ValueError("Scopes of modules inside a partition must have same query scope.")
            
            # add partition size to list
            self.partition_sizes.append(size)
            self.partition_scopes.append(partition_scope)

            # check if partition is pairwise disjoint to the overall scope so far (makes sure all partitions have pair-wise disjoint scopes)
            if partition_scope.isdisjoint(scope):
                scope = scope.union(partition_scope)
            else:
                raise ValueError("Scopes of partitions must be pair-wise disjoint.")

        super(SPNPartitionLayer, self).__init__(children=sum(child_partitions, []), **kwargs)

        self.n_in = sum(self.partition_sizes)
        self._n_out = torch.prod(torch.tensor(self.partition_sizes)).item()
        self.scope = scope

    @property
    def n_out(self) -> int:
        """Returns the number of outputs for this module."""
        return self._n_out
    
    @property
    def scopes_out(self) -> List[Scope]:
        return [self.scope for _ in range(self.n_out)]


@dispatch(memoize=True)
def marginalize(layer: SPNPartitionLayer, marg_rvs: Iterable[int], prune: bool=True, dispatch_ctx: Optional[DispatchContext]=None) -> Union[SPNPartitionLayer, None]:
    """TODO"""

    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # compute layer scope (same for all outputs)
    layer_scope = layer.scope

    mutual_rvs = set(layer_scope.query).intersection(set(marg_rvs))

    # layer scope is being fully marginalized over
    if(len(mutual_rvs) == len(layer_scope.query)):
        return None
    # node scope is being partially marginalized
    elif mutual_rvs:
        marg_partitions = []

        children = list(layer.children())
        partitions = np.split(children, np.cumsum(layer.modules_per_partition[:-1]))

        for partition_scope, partition_children in zip(layer.partition_scopes, partitions):
            partition_children = partition_children.tolist()
            partition_mutual_rvs = set(partition_scope.query).intersection(set(marg_rvs))

            # partition scope is being fully marginalized over
            if(len(partition_mutual_rvs) == len(partition_scope.query)):
                # drop partition entirely
                continue
            # node scope is being partially marginalized
            elif partition_mutual_rvs:
                # marginalize child modules
                marg_partitions.append([marginalize(child, marg_rvs, prune=prune, dispatch_ctx=dispatch_ctx) for child in partition_children])
            else:
                marg_partitions.append(deepcopy(partition_children))

        # if product node has only one child after marginalization and pruning is true, return child directly
        if(len(marg_partitions) == 1 and len(marg_partitions[0]) == 1 and prune):
            return marg_partitions[0][0]
        else:
            return SPNPartitionLayer(child_partitions=marg_partitions)
    else:
        return deepcopy(layer)