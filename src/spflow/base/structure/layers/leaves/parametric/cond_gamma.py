# -*- coding: utf-8 -*-
"""Contains conditional Gamma leaf layer for SPFlow in the 'base' backend.
"""
from typing import List, Union, Optional, Iterable, Tuple, Callable
import numpy as np

from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.contexts.dispatch_context import DispatchContext, init_default_dispatch_context
from spflow.meta.scope.scope import Scope
from spflow.base.structure.module import Module
from spflow.base.structure.nodes.leaves.parametric.cond_gamma import CondGamma


class CondGammaLayer(Module):
    r"""Layer of multiple conditional (univariate) Gamma distribution leaf nodes in the 'base' backend.

    Represents multiple conditional univariate Gamma distributions with independent scopes, each with the following probability distribution function (PDF):

    .. math::
    
        \text{PDF}(x) = \begin{cases} \frac{\beta^\alpha}{\Gamma(\alpha)}x^{\alpha-1}e^{-\beta x} & \text{if } x > 0\\
                                      0 & \text{if } x <= 0\end{cases}

    where
        - :math:`x` is the input observation
        - :math:`\Gamma` is the Gamma function
        - :math:`\alpha` is the shape parameter
        - :math:`\beta` is the rate parameter
    
    Attributes:
        cond_f:
            Optional callable or list of callables to retrieve parameters for the leaf nodes.
            If a single callable, its output should be a dictionary contain 'alpha','beta' as keys, and the values should be
            a floating point, a list of floats or a one-dimensional NumPy array, containing the shape and rate parameters (greater than 0), respectively.
            If the values are single floating point values, the same values are reused for all leaf nodes.
            If a list of callables, each one should return a dictionary containing 'alpha','beta' as keys, and the values should
            be floating point values greater than 0.0.
        scopes_out:
            List of scopes representing the output scopes.
        nodes:
            List of ``CondGamma`` objects for the nodes in this layer.
    """
    def __init__(self, scope: Union[Scope, List[Scope]], cond_f: Optional[Union[Callable,List[Callable]]]=None, n_nodes: int=1, **kwargs) -> None:
        r"""Initializes ``CondGammaLayer`` object.

        Args:
            scope:
                Scope or list of scopes specifying the scopes of the individual distribution.
                If a single scope is given, it is used for all nodes.
            cond_f:
                Optional callable or list of callables to retrieve parameters for the leaf nodes.
                If a single callable, its output should be a dictionary contain 'alpha','beta' as keys, and the values should be
                a floating point, a list of floats or a one-dimensional NumPy array, containing the shape and rate parameters (greater than 0), respectively.
                If the values are single floating point values, the same values are reused for all leaf nodes.
                If a list of callables, each one should return a dictionary containing 'alpha','beta' as keys, and the values should
                be floating point values greater than 0.0.
            n_nodes:
                Integer specifying the number of nodes the layer should represent. Only relevant if a single scope is given.
                Defaults to 1.
        """
        if isinstance(scope, Scope):
            if n_nodes < 1:
                raise ValueError(f"Number of nodes for 'CondGammaLayer' must be greater or equal to 1, but was {n_nodes}")

            scope = [scope for _ in range(n_nodes)]
            self._n_out = n_nodes
        else:
            if len(scope) == 0:
                raise ValueError("List of scopes for 'CondGammaLayer' was empty.")

            self._n_out = len(scope)
        
        super(CondGammaLayer, self).__init__(children=[], **kwargs)

        # create leaf nodes
        self.nodes = [CondGamma(s) for s in scope]

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
                If a single callable, its output should be a dictionary contain 'alpha','beta' as keys, and the values should be
                a floating point, a list of floats or a one-dimensional NumPy array, containing the shape and rate parameters (greater than 0), respectively.
                If the values are single floating point values, the same values are reused for all leaf nodes.
                If a list of callables, each one should return a dictionary containing 'alpha','beta' as keys, and the values should
                be floating point values greater than 0.0.

        Raises:
            ValueError: If list of callables does not match number of nodes represented by the layer.
        """
        if isinstance(cond_f, List) and len(cond_f) != self.n_out:
            raise ValueError("'CondGammaLayer' received list of 'cond_f' functions, but length does not not match number of conditional nodes.")

        self.cond_f = cond_f
    
    def retrieve_params(self, data: np.ndarray, dispatch_ctx: DispatchContext) -> Tuple[np.ndarray, np.ndarray]:
        r"""Retrieves the conditional parameters of the leaf layer.

        First, checks if conditional parameters (``alpha``,``beta``) are passed as additional arguments in the dispatch context.
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
        alpha, beta, cond_f = None, None, None

        # check dispatch cache for required conditional parameters 'alpha','beta'
        if self in dispatch_ctx.args:
            args = dispatch_ctx.args[self]

            # check if values 'alpha','beta' are specified (highest priority)
            if "alpha" in args:
                alpha = args["alpha"]
            if "beta" in args:
                beta = args["beta"]
            # check if alternative function to provide 'alpha','beta' is specified (second to highest priority)
            elif "cond_f" in args:
                cond_f = args["cond_f"]
        elif self.cond_f:
            # check if module has a 'cond_f' to provide 'alpha','beta' specified (lowest priority)
            cond_f = self.cond_f
        
        # if neither 'alpha' or 'beta' nor 'cond_f' is specified (via node or arguments)
        if (alpha is None or beta is None) and cond_f is None:
            raise ValueError("'CondBinomialLayer' requires either 'alpha' and 'beta' or 'cond_f' to retrieve 'alpha','beta to be specified.")

        # if 'alpha' or 'beta' was not already specified, retrieve it
        if alpha is None or beta is None:
            # there is a different function for each conditional node
            if isinstance(cond_f, List):
                alpha = []
                beta = []

                for f in cond_f:
                    args = f(data)
                    alpha.append(args['alpha'])
                    beta.append(args['beta'])

                alpha = np.array(alpha)
                beta = np.array(beta)
            else:
                args = cond_f(data)
                alpha = args['alpha']
                beta = args['beta']

        if isinstance(alpha, int) or isinstance(alpha, float):
            alpha = np.array([alpha for _ in range(self.n_out)])
        if isinstance(alpha, list):
            alpha = np.array(alpha)
        if(alpha.ndim != 1):
            raise ValueError(f"Numpy array of 'alpha' values for 'CondGammaLayer' is expected to be one-dimensional, but is {alpha.ndim}-dimensional.")
        if(alpha.shape[0] != self.n_out):
            raise ValueError(f"Length of numpy array of 'alpha' values for 'CondGammaLayer' must match number of output nodes {self.n_out}, but is {alpha.shape[0]}")

        if isinstance(beta, int) or isinstance(beta, float):
            beta = np.array([float(beta) for _ in range(self.n_out)])
        if isinstance(beta, list):
            beta = np.array(beta)
        if(beta.ndim != 1):
            raise ValueError(f"Numpy array of 'beta' values for 'CondGammaLayer' is expected to be one-dimensional, but is {beta.ndim}-dimensional.")
        if(beta.shape[0] != self.n_out):
            raise ValueError(f"Length of numpy array of 'beta' values for 'CondGammaLayer' must match number of output nodes {self.n_out}, but is {beta.shape[0]}")

        return alpha, beta

    # TODO: dist

    # TODO: check support


@dispatch(memoize=True)  # type: ignore
def marginalize(layer: CondGammaLayer, marg_rvs: Iterable[int], prune: bool=True, dispatch_ctx: Optional[DispatchContext]=None) -> Union[CondGammaLayer, CondGamma, None]:
    r"""Structural marginalization for ``CondGammaLayer`` objects.

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
        new_node = CondGamma(marg_scopes[0])
        return new_node
    else:
        new_layer = CondGammaLayer(marg_scopes)
        return new_layer