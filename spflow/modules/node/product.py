"""Contains ``ProductNode`` for SPFlow in the ``base`` backend.
"""
from copy import deepcopy
from typing import List, Optional, Union
from collections.abc import Iterable

import torch

from spflow.meta.dispatch import SamplingContext, init_default_sampling_context
from spflow.utils import Tensor
from spflow import tensor as T

from spflow.modules.node.node import Node
from spflow.modules.module import Module
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.dispatch.dispatch_context import (
    DispatchContext,
    init_default_dispatch_context,
)
from spflow.meta.data import Scope


class ProductNode(Node):
    r"""SPN-like product node in the ``base`` backend.

    Represents a product of its children over pair-wise disjoint scopes.

    Attributes:
        children:
            Non-empty list of modules that are children to the node in a directed graph.
        n_out:
            Integer indicating the number of outputs. One for nodes.
        scopes_out:
            List of scopes representing the output scopes.
    """

    def __init__(self, children: list[Module]) -> None:
        r"""Initializes ``ProductNode`` object.

        Args:
            children:
                Non-empty list of modules that are children to the node.
                The output scopes for all child modules need to be pair-wise disjoint.
        Raises:
            ValueError: Invalid arguments.
        """
        super().__init__(children=children)

        if not children:
            raise ValueError("'ProductNode' requires at least one child to be specified.")

        scope = Scope()

        for child in children:
            for s in child.scopes_out:
                if not scope.isdisjoint(s):
                    raise ValueError(f"'ProductNode' requires child scopes to be pair-wise disjoint.")

                scope = scope.join(s)

        self.scope = scope

    def parameters(self):
        params = []
        for child in self.children:
            params.extend(list(child.parameters()))
        return params


@dispatch(memoize=True)  # type: ignore
def marginalize(
    product_node: ProductNode,
    marg_rvs: Iterable[int],
    prune: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
) -> Union[ProductNode, Node, None, Module]:
    r"""Structural marginalization for ``ProductNode`` objects in the ``base`` backend.

    Structurally marginalizes the specified product node.
    If the product node's scope contains non of the random variables to marginalize, then the node is returned unaltered.
    If the product node's scope is fully marginalized over, then None is returned.
    If the product node's scope is partially marginalized over, then a new prodcut node over the marginalized child modules is returned.
    If the marginalized product node has only one input and 'prune' is set, then the product node is pruned and the input is returned directly.

    Args:
        product_node:
            Sum node module to marginalize.
        marg_rvs:
            Iterable of integers representing the indices of the random variables to marginalize.
        prune:
            Boolean indicating whether or not to prune nodes and modules where possible.
            If set to True and the marginalized node has a single input, the input is returned directly.
            Defaults to True.
        dispatch_ctx:
            Optional dispatch context.

    Returns:
        (Marginalized) product node or None if it is completely marginalized.
    """
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # compute node scope (node only has single output)
    node_scope = product_node.scope

    mutual_rvs = set(node_scope.query).intersection(set(marg_rvs))

    # node scope is being fully marginalized
    if len(mutual_rvs) == len(node_scope.query):
        return None
    # node scope is being partially marginalized
    elif mutual_rvs:
        marg_children = []

        # marginalize child modules
        for child in product_node.children:
            marg_child = marginalize(child, marg_rvs, prune=prune, dispatch_ctx=dispatch_ctx)

            # if marginalized child is not None
            if marg_child:
                marg_children.append(marg_child)

        # if product node has only one child with a single output after marginalization and pruning is true, return child directly
        if len(marg_children) == 1 and marg_children[0].n_out == 1 and prune:
            return marg_children[0]
        else:
            return ProductNode(marg_children)
    else:
        return deepcopy(product_node)


@dispatch(memoize=True)  # type: ignore
def updateBackend(product_node: ProductNode, dispatch_ctx: Optional[DispatchContext] = None) -> ProductNode:
    """Conversion for ``SumNode`` from ``torch`` backend to ``base`` backend.

    Args:
        product_node:
            Product node to be converted.
        dispatch_ctx:
            Dispatch context.
    """
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    return ProductNode(
        children=[updateBackend(child, dispatch_ctx=dispatch_ctx) for child in product_node.children]
    )


@dispatch(memoize=True)  # type: ignore
def toLayerBased(product_node: ProductNode, dispatch_ctx: Optional[DispatchContext] = None) -> ProductNode:
    """Conversion for ``SumNode`` from ``torch`` backend to ``base`` backend.

    Args:
        product_node:
            Product node to be converted.
        dispatch_ctx:
            Dispatch context.
    """
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    return ProductNode(
        children=[toLayerBased(child, dispatch_ctx=dispatch_ctx) for child in product_node.children]
    )


@dispatch(memoize=True)  # type: ignore
def toNodeBased(product_node: ProductNode, dispatch_ctx: Optional[DispatchContext] = None) -> ProductNode:
    """Conversion for ``SumNode`` from ``torch`` backend to ``base`` backend.

    Args:
        product_node:
            Product node to be converted.
        dispatch_ctx:
            Dispatch context.
    """
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    return ProductNode(
        children=[toNodeBased(child, dispatch_ctx=dispatch_ctx) for child in product_node.children]
    )


@dispatch  # type: ignore
def sample(
    node: ProductNode,
    data: Tensor,
    check_support: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
    sampling_ctx: Optional[SamplingContext] = None,
) -> Tensor:
    """Samples from SPN-like product nodes in the ``base`` backend given potential evidence.

    Recursively samples from each input.
    Missing values (i.e., NaN) are filled with sampled values.

    Args:
        node:
            Product node to sample from.
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
    # initialize contexts
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    sampling_ctx = init_default_sampling_context(sampling_ctx, T.shape(data)[0])

    # sample from all child outputs
    for child in node.children:
        data = sample(
            child,
            data,
            check_support=check_support,
            dispatch_ctx=dispatch_ctx,
            sampling_ctx=SamplingContext(
                sampling_ctx.instance_ids,
                [list(range(child.n_out)) for _ in sampling_ctx.instance_ids],
            ),
        )

    return data


@dispatch(memoize=True)  # type: ignore
def em(
    node: ProductNode,
    data: Tensor,
    check_support: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
) -> None:
    """Performs a single expectation maximizaton (EM) step for ``ProductNode`` in the ``torch`` backend.

    Args:
        node:
            Node to perform EM step for.
        data:
            Two-dimensional PyTorch tensor containing the input data.
            Each row corresponds to a sample.
        check_support:
            Boolean value indicating whether or not if the data is in the support of the leaf distributions.
            Defaults to True.
        dispatch_ctx:
            Optional dispatch context.
    """
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # recursively call EM on children
    for child in node.children:
        em(child, data, check_support=check_support, dispatch_ctx=dispatch_ctx)


@dispatch(memoize=True)  # type: ignore
def log_likelihood(
    product_node: ProductNode,
    data: Tensor,
    check_support: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
) -> Tensor:
    """Computes log-likelihoods for SPN-like product nodes in the ``base`` backend given input data.

    Log-likelihood for product node is the sum of its input likelihoods (product in linear space).
    Missing values (i.e., NaN) are marginalized over.

    Args:
        product_node:
            Product node to perform inference for.
        data:
            Two-dimensional NumPy array containing the input data.
            Each row corresponds to a sample.
        dispatch_ctx:
            Optional dispatch context.

    Returns:
        Two-dimensional NumPy array containing the log-likelihoods of the input data for the sum node.
        Each row corresponds to an input sample.
    """
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # compute child log-likelihoods
    child_lls = T.concatenate(
        [
            log_likelihood(
                child,
                data,
                check_support=check_support,
                dispatch_ctx=dispatch_ctx,
            )
            for child in product_node.children
        ],
        axis=1,
    )

    # multiply child log-likelihoods together (sum in log-space)
    return T.sum(child_lls, axis=1, keepdims=True)


if __name__ == "__main__":
    from spflow.modules.node.leaf.binomial import Binomial
    from spflow.modules.node.sum import SumNode
    from spflow.meta.data.scope import Scope
    from rich.traceback import install

    install()
    P = ProductNode(
        children=[
            SumNode(
                children=[Binomial(scope=Scope([0]), n=256), Binomial(scope=Scope([0]), n=256)],
                weights=[0.1, 0.9],
            ),
            SumNode(
                children=[Binomial(scope=Scope([1]), n=256), Binomial(scope=Scope([1]), n=256)],
                weights=[0.2, 0.8],
            ),
        ],
    )
    print(P)

    data = T.tensor([[1.0, 2.0], [2.0, 3.0], [3.0, 4.0]])  # .to("cuda")
    # print(g.log_prob(data))
    print(log_likelihood(P, data))
    print(sample(P, num_samples=3))
    # maximum_likelihood_estimation(g, data)
    # print(g.mean, g.std)
