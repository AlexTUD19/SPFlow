# -*- coding: utf-8 -*-
"""Contains conditional Gaussian leaf layer for SPFlow in the 'base' backend.
"""
from typing import List, Union, Optional, Iterable, Tuple, Callable
import numpy as np

from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.contexts.dispatch_context import DispatchContext, init_default_dispatch_context
from spflow.meta.scope.scope import Scope
from spflow.base.structure.module import Module
from spflow.base.structure.nodes.leaves.parametric.cond_gaussian import CondGaussian


class CondGaussianLayer(Module):
    r"""Layer of multiple conditional (univariate) Gaussian distribution leaf nodes in the 'base' backend.

    Represents multiple conditional univariate Gaussian distributions with independent scopes, each with the following probability distribution function (PDF):

    .. math::

        \text{PDF}(x) = \frac{1}{\sqrt{2\pi\sigma^2}}\exp(-\frac{(x-\mu)^2}{2\sigma^2})

    where
        - :math:`x` the observation
        - :math:`\mu` is the mean
        - :math:`\sigma` is the standard deviation

    Attributes:
        cond_f:
            Optional callable or list of callables to retrieve parameters for the leaf nodes.
            If a single callable, its output should be a dictionary contain 'mean','std' as keys, and the values should be
            a floating point, a list of floats or a one-dimensional NumPy array, containing the mean and standard deviation (the latter greater than 0), respectively.
            If the values are single floating point values, the same values are reused for all leaf nodes.
            If a list of callables, each one should return a dictionary containing 'mean','std' as keys, and the values should
            be floating point values (the latter greater than 0.0).
        scopes_out:
            List of scopes representing the output scopes.
        nodes:
            List of ``CondGaussian`` objects for the nodes in this layer.
    """
    def __init__(self, scope: Union[Scope, List[Scope]], cond_f: Optional[Union[Callable, List[Callable]]]=None, n_nodes: int=1, **kwargs) -> None:
        r"""Initializes ``CondGaussianLayer`` object.

        Args:
            scope:
                Scope or list of scopes specifying the scopes of the individual distribution.
                If a single scope is given, it is used for all nodes.
            cond_f:
                Optional callable or list of callables to retrieve parameters for the leaf nodes.
                If a single callable, its output should be a dictionary contain 'mean','std' as keys, and the values should be
                a floating point, a list of floats or a one-dimensional NumPy array, containing the mean and standard deviation (the latter greater than 0), respectively.
                If the values are single floating point values, the same values are reused for all leaf nodes.
                If a list of callables, each one should return a dictionary containing 'mean','std' as keys, and the values should
                be floating point values (the latter greater than 0.0).
            n_nodes:
                Integer specifying the number of nodes the layer should represent. Only relevant if a single scope is given.
                Defaults to 1.
        """
        if isinstance(scope, Scope):
            if n_nodes < 1:
                raise ValueError(f"Number of nodes for 'CondGaussianLayer' must be greater or equal to 1, but was {n_nodes}")

            scope = [scope for _ in range(n_nodes)]
            self._n_out = n_nodes
        else:
            if len(scope) == 0:
                raise ValueError("List of scopes for 'CondGaussianLayer' was empty.")

            self._n_out = len(scope)
        
        super(CondGaussianLayer, self).__init__(children=[], **kwargs)

        # create leaf nodes
        self.nodes = [CondGaussian(s) for s in scope]

        # compute scope
        self.scopes_out = scope

        self.set_cond_f(cond_f)

    @property
    def n_out(self) -> int:
        """Returns the number of outputs for this module. Equal to the number of nodes represented by the layer."""
        return self._n_out
    
    def set_cond_f(self, cond_f: Optional[Union[List[Callable], Callable]]=None) -> None:
        r"""Sets the ``cond_f`` property.

        Args:
            cond_f:
                Optional callable or list of callables to retrieve parameters for the leaf nodes.
                If a single callable, its output should be a dictionary contain 'mean','std' as keys, and the values should be
                a floating point, a list of floats or a one-dimensional NumPy array, containing the mean and standard deviation (the latter greater than 0), respectively.
                If the values are single floating point values, the same values are reused for all leaf nodes.
                If a list of callables, each one should return a dictionary containing 'mean','std' as keys, and the values should
                be floating point values (the latter greater than 0.0).

        Raises:
            ValueError: If list of callables does not match number of nodes represented by the layer.
        """
        if isinstance(cond_f, List) and len(cond_f) != self.n_out:
            raise ValueError("'CondGaussianLayer' received list of 'cond_f' functions, but length does not not match number of conditional nodes.")

        self.cond_f = cond_f
    
    def retrieve_params(self, data: np.ndarray, dispatch_ctx: DispatchContext) -> Tuple[np.ndarray, np.ndarray]:
        r"""Retrieves the conditional parameters of the leaf layer.

        First, checks if conditional parameters (``mean``,``std``) are passed as additional arguments in the dispatch context.
        Secondly, checks if a function or list of functions (``cond_f``) is passed as an additional argument in the dispatch context to retrieve the conditional parameters.
        Lastly, checks if a ``cond_f`` is set as an attributed to retrieve the conditional parameter.

        Args:
            data:
                Two-dimensional NumPy array containing the data to compute the conditional parameters.
                Each row is regarded as a sample.
            dispatch_ctx:
                Dispatch context.

        Returns:
            Two-dimensional NumPy array of non-zero weights summing up to one per row.
        
        Raises:
            ValueError: No way to retrieve conditional parameters or invalid conditional parameters.
        """
        mean, std, cond_f = None, None, None

        # check dispatch cache for required conditional parameters 'mean','std'
        if self in dispatch_ctx.args:
            args = dispatch_ctx.args[self]

            # check if value for 'mean','std' specified (highest priority)
            if "mean" in args:
                mean = args["mean"]
            if "std" in args:
                std = args["std"]
            # check if alternative function to provide 'mean','std' is specified (second to highest priority)
            elif "cond_f" in args:
                cond_f = args["cond_f"]
        elif self.cond_f:
            # check if module has a 'cond_f' to provide 'mean','std' specified (lowest priority)
            cond_f = self.cond_f
        
        # if neither 'mean' and 'std' nor 'cond_f' is specified (via node or arguments)
        if (mean is None or std is None) and cond_f is None:
            raise ValueError("'CondGaussianLayer' requires either 'mean' and 'std' or 'cond_f' to retrieve 'mean','std' to be specified.")

        # if 'mean' or 'std' was not already specified, retrieve it
        if mean is None or std is None:
            # there is a different function for each conditional node
            if isinstance(cond_f, List):
                mean = []
                std = []

                for f in cond_f:
                    args = f(data)
                    mean.append(args['mean'])
                    std.append(args['std'])

                mean = np.array(mean)
                std = np.array(std)
            else:
                args = cond_f(data)
                mean = args['mean']
                std = args['std']

        if isinstance(mean, int) or isinstance(mean, float):
            mean = np.array([mean for _ in range(self.n_out)])
        if isinstance(mean, list):
            mean = np.array(mean)
        if(mean.ndim != 1):
            raise ValueError(f"Numpy array of 'mean' values for 'CondGaussianLayer' is expected to be one-dimensional, but is {mean.ndim}-dimensional.")
        if(mean.shape[0] != self.n_out):
            raise ValueError(f"Length of numpy array of 'mean' values for 'CondGaussianLayer' must match number of output nodes {self.n_out}, but is {mean.shape[0]}")

        if isinstance(std, int) or isinstance(std, float):
            std = np.array([float(std) for _ in range(self.n_out)])
        if isinstance(std, list):
            std = np.array(std)
        if(std.ndim != 1):
            raise ValueError(f"Numpy array of 'std' values for 'CondGaussianLayer' is expected to be one-dimensional, but is {std.ndim}-dimensional.")
        if(std.shape[0] != self.n_out):
            raise ValueError(f"Length of numpy array of 'std' values for 'CondGaussianLayer' must match number of output nodes {self.n_out}, but is {std.shape[0]}")
        return mean, std

    # TODO: dist

    # TODO: check support


@dispatch(memoize=True)  # type: ignore
def marginalize(layer: CondGaussianLayer, marg_rvs: Iterable[int], prune: bool=True, dispatch_ctx: Optional[DispatchContext]=None) -> Union[CondGaussianLayer, CondGaussian, None]:
    r"""Structural marginalization for ``CondGaussianLayer`` objects.

    Structurally marginalizes the specified layer module.
    If the layer's scope contains non of the random variables to marginalize, then the layer is returned unaltered.
    If the layer's scope is fully marginalized over, then None is returned.

    Args:
        layer:
            Layer module to marginalize.
        marg_rvs:
            Iterable of integers representing the indices of the random variables to marginalize.
        prune:
            Boolean indicating whether or not to prune nodes and modules where possible.
            Has no effect here. Defaults to True.
        dispatch_ctx:
            Optional dispatch context.
    
    Returns:
        Unaltered leaf layer or None if it is completely marginalized.
    """
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # marginalize nodes
    marg_scopes = []

    for node in layer.nodes:
        marg_node = marginalize(node, marg_rvs, prune=prune)

        if marg_node is not None:
            marg_scopes.append(marg_node.scope)

    if len(marg_scopes) == 0:
        return None
    elif len(marg_scopes) == 1 and prune:
        new_node = CondGaussian(marg_scopes[0])
        return new_node
    else:
        new_layer = CondGaussianLayer(marg_scopes)
        return new_layer