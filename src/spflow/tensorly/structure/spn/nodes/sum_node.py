"""Contains ``SumNode`` for SPFlow in the ``base`` backend.
"""
from copy import deepcopy
from typing import Iterable, List, Optional, Union
from itertools import chain

import numpy as np
import torch
import tensorly as tl

from ....utils.helper_functions import tl_isclose, T

from spflow.tensorly.structure.general.nodes.node import Node
from spflow.meta.structure import MetaModule
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.dispatch.dispatch_context import (
    DispatchContext,
    init_default_dispatch_context,
)
from spflow.tensorly.utils.projections import proj_convex_to_real, proj_real_to_convex


class SumNode(Node):
    """SPN-like sum node in the ``base`` backend.

    Represents a convex combination of its children over the same scope.

    Attributes:
        children:
            Non-empty list of modules that are children to the node in a directed graph.
        weights:
            One-dimensional NumPy array containing non-negative weights for each input, summing up to one.
        n_out:
            Integer indicating the number of outputs. One for nodes.
        scopes_out:
            List of scopes representing the output scopes.
    """

    def __init__(
        self,
        children: List[MetaModule],#List[Module],
        weights: Optional[Union[T, List[float]]] = None,
    ) -> None:
        r"""Initializes ``SumNode`` object.

        Args:
            children:
                Non-empty list of modules that are children to the node.
                The output scopes for all child modules need to be equal.
            weights:
                Optional list of floats, or one-dimensional NumPy array containing non-negative weights for each input, summing up to one.
                Defaults to 'None' in which case weights are initialized to random weights in (0,1) and normalized.

        Raises:
            ValueError: Invalid arguments.
        """
        super().__init__(children=children)

        if not children:
            raise ValueError("'SumNode' requires at least one child to be specified.")

        scope = None

        for child in children:
            for s in child.scopes_out:
                if scope is None:
                    scope = s
                else:
                    if not scope.equal_query(s):
                        raise ValueError(f"'SumNode' requires child scopes to have the same query variables.")

                scope = scope.join(s)

        self.scope = scope
        self.n_in = sum(child.n_out for child in children)

        if weights is None:
            weights = tl.random.random_tensor(self.n_in, dtype=self.dtype, device=self.device) + 1e-08  # avoid zeros
            weights /= tl.sum(weights)

        if self.backend == "pytorch":
            self._weights = torch.nn.Parameter(requires_grad=True)
        else:
            self._weights = None
        self.weights = weights

    @property
    def weights(self) -> T:
        """Returns the weights of the node as a NumPy array."""

        return proj_real_to_convex(self._weights)


    @weights.setter
    def weights(self, values: Union[T, List[float]]) -> None:
        """Sets the weights of the node to specified values.

        Args:
            values:
                One-dimensional NumPy array or list of floats of non-negative values summing up to one.
                Number of values must match number of total inputs to the node.

        Raises:
            ValueError: Invalid values.
        """
        if isinstance(values, list):
            values = tl.tensor(values, dtype=self.dtype, device=self.device)
        if tl.ndim(values) != 1:
            raise ValueError(
                f"Numpy array of weight values for 'SumNode' is expected to be one-dimensional, but is {values.ndim}-dimensional."
            )
        if not tl.all(values > 0):
            raise ValueError("Weights for 'SumNode' must be all positive.")
        if not tl_isclose(tl.sum(values), 1.0):
            raise ValueError("Weights for 'SumNode' must sum up to one.")
        if not (len(values) == self.n_in):
            raise ValueError("Number of weights for 'SumNode' does not match total number of child outputs.")
        if self.backend == "pytorch":
            self._weights.data = proj_convex_to_real(values).type(self.dtype).to(self.device)
        else:
            self._weights = proj_convex_to_real(values).astype(self.dtype)

    def to_dtype(self, dtype):
        self.dtype = dtype
        self.weights = self.weights
        for child in self.children:
            child.to_dtype(dtype)

    def to_device(self, device):
        if self.backend == "numpy":
            raise ValueError("it is not possible to change the device of models that have a numpy backend")
        self.device = device
        self.weights = self.weights
        for child in self.children:
            child.to_device(device)


    def parameters(self):
        print("sumnode")
        params = []
        for child in self.children:
            params.extend(list(child.parameters()))
        params.insert(0,self._weights)
        return params






@dispatch(memoize=True)  # type: ignore
def marginalize(
    sum_node: SumNode,
    marg_rvs: Iterable[int],
    prune: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
) -> Union[SumNode, None]:
    r"""Structural marginalization for ``SumNode`` objects in the ``base`` backend.

    Structurally marginalizes the specified sum node.
    If the sum node's scope contains non of the random variables to marginalize, then the node is returned unaltered.
    If the sum node's scope is fully marginalized over, then None is returned.
    If the sum node's scope is partially marginalized over, then a new sum node over the marginalized child modules is returned.

    Args:
        sum_node:
            Sum node module to marginalize.
        marg_rvs:
            Iterable of integers representing the indices of the random variables to marginalize.
        prune:
            Boolean indicating whether or not to prune nodes and modules where possible.
            Has no effect when marginalizing sum nodes. Defaults to True.
        dispatch_ctx:
            Optional dispatch context.

    Returns:
        (Marginalized) sum node or None if it is completely marginalized.
    """
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # compute node scope (node only has single output)
    node_scope = sum_node.scope

    mutual_rvs = set(node_scope.query).intersection(set(marg_rvs))

    # node scope is being fully marginalized
    if len(mutual_rvs) == len(node_scope.query):
        return None
    # node scope is being partially marginalized
    elif mutual_rvs:
        marg_children = []

        # marginalize child modules
        for child in sum_node.children:
            marg_child = marginalize(child, marg_rvs, prune=prune, dispatch_ctx=dispatch_ctx)

            # if marginalized child is not None
            if marg_child:
                marg_children.append(marg_child)

        return SumNode(children=marg_children, weights=sum_node.weights)
    else:
        return deepcopy(sum_node)

@dispatch(memoize=True)  # type: ignore # ToDo: überprüfen ob sum_layer.weights ein parameter ist
def updateBackend(sum_node: SumNode, dispatch_ctx: Optional[DispatchContext] = None) -> SumNode:
    """Conversion for ``SumNode`` from ``torch`` backend to ``base`` backend.

    Args:
        sum_node:
            Sum node to be converted.
        dispatch_ctx:
            Dispatch context.
    """
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    if isinstance(sum_node.weights, np.ndarray):
        return SumNode(
            children=[updateBackend(child, dispatch_ctx=dispatch_ctx) for child in sum_node.children],
            weights=tl.tensor(sum_node.weights)
        )
    elif torch.is_tensor(sum_node.weights):
        return SumNode(
            children=[updateBackend(child, dispatch_ctx=dispatch_ctx) for child in sum_node.children],
            weights=tl.tensor(sum_node.weights.data)
        )
    else:
        raise NotImplementedError("updateBackend has no implementation for this backend")

@dispatch(memoize=True)  # type: ignore # ToDo: überprüfen ob sum_layer.weights ein parameter ist
def toLayerBased(sum_node: SumNode, dispatch_ctx: Optional[DispatchContext] = None) -> SumNode:
    """Conversion for ``SumNode`` from ``torch`` backend to ``base`` backend.

    Args:
        sum_node:
            Sum node to be converted.
        dispatch_ctx:
            Dispatch context.
    """
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    if isinstance(sum_node.weights, np.ndarray):
        return SumNode(
            children=[toLayerBased(child, dispatch_ctx=dispatch_ctx) for child in sum_node.children],
            weights=tl.tensor(sum_node.weights)
        )
    elif torch.is_tensor(sum_node.weights):
        return SumNode(
            children=[toLayerBased(child, dispatch_ctx=dispatch_ctx) for child in sum_node.children],
            weights=tl.tensor(sum_node.weights.data)
        )
    else:
        raise NotImplementedError("toLayerBased has no implementation for this backend")

@dispatch(memoize=True)  # type: ignore # ToDo: überprüfen ob sum_layer.weights ein parameter ist
def toNodeBased(sum_node: SumNode, dispatch_ctx: Optional[DispatchContext] = None) -> SumNode:
    """Conversion for ``SumNode`` from ``torch`` backend to ``base`` backend.

    Args:
        sum_node:
            Sum node to be converted.
        dispatch_ctx:
            Dispatch context.
    """
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    if isinstance(sum_node.weights, np.ndarray):
        return SumNode(
            children=[toNodeBased(child, dispatch_ctx=dispatch_ctx) for child in sum_node.children],
            weights=tl.tensor(sum_node.weights)
        )
    elif torch.is_tensor(sum_node.weights):
        return SumNode(
            children=[toNodeBased(child, dispatch_ctx=dispatch_ctx) for child in sum_node.children],
            weights=tl.tensor(sum_node.weights.data)
        )
    else:
        raise NotImplementedError("toNodeBased has no implementation for this backend")

