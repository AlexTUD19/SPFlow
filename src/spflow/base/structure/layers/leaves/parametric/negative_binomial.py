"""
Created on August 12, 2022

@authors: Philipp Deibert
"""
from typing import List, Union, Optional, Iterable, Tuple
import numpy as np

from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.contexts.dispatch_context import DispatchContext, init_default_dispatch_context
from spflow.meta.scope.scope import Scope
from spflow.base.structure.module import Module
from spflow.base.structure.nodes.leaves.parametric.negative_binomial import NegativeBinomial


class NegativeBinomialLayer(Module):
    """Layer representing multiple (univariate) negative binomial leaf nodes.

    Args:
        scope: TODO
        n: TODO
        p: TODO
        n_nodes: number of output nodes.
    """
    def __init__(self, scope: Union[Scope, List[Scope]], n: Union[int, List[int], np.ndarray], p: Union[int, float, List[float], np.ndarray]=0.5, n_nodes: int=1, **kwargs) -> None:
        """TODO"""
        
        if isinstance(scope, Scope):
            if n_nodes < 1:
                raise ValueError(f"Number of nodes for 'NegativeBinomialLayer' must be greater or equal to 1, but was {n_nodes}")

            scope = [scope for _ in range(n_nodes)]
            self._n_out = n_nodes
        else:
            self._n_out = len(scope)
        
        super(NegativeBinomialLayer, self).__init__(children=[], **kwargs)

        # create leaf nodes
        self.nodes = [NegativeBinomial(s, 1, 0.5) for s in scope]

        # parse weights
        self.set_params(n, p)

        # compute scope
        self.scopes = scope

    @property
    def n_out(self) -> int:
        """Returns the number of outputs for this module."""
        return self._n_out
    
    @property
    def scopes_out(self) -> List[Scope]:
        """TODO"""
        return self.scopes

    @property
    def n(self) -> np.ndarray:
        return np.array([node.n for node in self.nodes])
    
    @property
    def p(self) -> np.ndarray:
        return np.array([node.p for node in self.nodes])

    def set_params(self, n: Union[int, List[int], np.ndarray], p: Union[int, float, List[float], np.ndarray]=0.5) -> None:

        if isinstance(n, int):
            n = np.array([n for _ in range(self.n_out)])
        if isinstance(n, list):
            n = np.array(n)
        if(n.ndim != 1):
            raise ValueError(f"Numpy array of 'n' values for 'NegativeBinomialLayer' is expected to be one-dimensional, but is {n.ndim}-dimensional.")
        if(n.shape[0] != self.n_out):
            raise ValueError(f"Length of numpy array of 'n' values for 'NegativeBinomialLayer' must match number of output nodes {self.n_out}, but is {n.shape[0]}")

        if isinstance(p, int) or isinstance(p, float):
            p = np.array([float(p) for _ in range(self.n_out)])
        if isinstance(p, list):
            p = np.array(p)
        if(p.ndim != 1):
            raise ValueError(f"Numpy array of 'p' values for 'NegativeBinomialLayer' is expected to be one-dimensional, but is {p.ndim}-dimensional.")
        if(p.shape[0] != self.n_out):
            raise ValueError(f"Length of numpy array of 'p' values for 'NegativeBinomialLayer' must match number of output nodes {self.n_out}, but is {p.shape[0]}")

        for node_n, node_p, node in zip(n, p, self.nodes):
            node.set_params(node_n, node_p)
    
    def get_params(self) -> Tuple[np.ndarray, np.ndarray]:
        return self.n, self.p


@dispatch(memoize=True)
def marginalize(layer: NegativeBinomialLayer, marg_rvs: Iterable[int], prune: bool=True, dispatch_ctx: Optional[DispatchContext]=None) -> Union[NegativeBinomialLayer, NegativeBinomial, None]:
    """TODO"""
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # marginalize nodes
    marg_scopes = []
    marg_params = []

    for node in layer.nodes:
        marg_node = marginalize(node, marg_rvs, prune=prune)

        if marg_node is not None:
            marg_scopes.append(marg_node.scope)
            marg_params.append(marg_node.get_params())

    if len(marg_scopes) == 0:
        return None
    elif len(marg_scopes) == 1 and prune:
        new_node = NegativeBinomial(marg_scopes[0], *marg_params[0])
        return new_node
    else:
        new_layer = NegativeBinomialLayer(marg_scopes, *[np.array(p) for p in zip(*marg_params)])
        return new_layer