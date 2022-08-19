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
from spflow.base.structure.nodes.leaves.parametric.uniform import Uniform


class UniformLayer(Module):
    """Layer representing multiple (univariate) uniform leaf nodes.

    Args:
        scope: TODO
        start: TODO
        end: TODO
        support_outside: TODO
        n_nodes: number of output nodes.
    """
    def __init__(self, scope: Union[Scope, List[Scope]], start: Union[int, float, List[float], np.ndarray], end: Union[int, float, List[float], np.ndarray], support_outside: Union[bool, List[bool], np.ndarray]=True, n_nodes: int=1, **kwargs) -> None:
        """TODO"""
        
        if isinstance(scope, Scope):
            if n_nodes < 1:
                raise ValueError(f"Number of nodes for 'UniformLayer' must be greater or equal to 1, but was {n_nodes}")

            scope = [scope for _ in range(n_nodes)]
            self._n_out = n_nodes
        else:
            if len(scope) == 0:
                raise ValueError("List of scopes for 'UniformLayer' was empty.")

            self._n_out = len(scope)

        super(UniformLayer, self).__init__(children=[], **kwargs)

        # create leaf nodes
        self.nodes = [Uniform(s, 0.0, 1.0) for s in scope]

        # compute scope
        self.scopes_out = scope

        # parse weights
        self.set_params(start, end, support_outside)

    @property
    def n_out(self) -> int:
        """Returns the number of outputs for this module."""
        return self._n_out

    @property
    def start(self) -> np.ndarray:
        return np.array([node.start for node in self.nodes])
    
    @property
    def end(self) -> np.ndarray:
        return np.array([node.end for node in self.nodes])
    
    @property
    def support_outside(self) -> np.ndarray:
        return np.array([node.support_outside for node in self.nodes])

    def set_params(self, start: Union[int, float, List[float], np.ndarray], end: Union[int, float, List[float], np.ndarray], support_outside: Union[bool, List[bool], np.ndarray]=True) -> None:

        if isinstance(start, int) or isinstance(start, float):
            start = np.array([float(start) for _ in range(self.n_out)])
        if isinstance(start, list):
            start = np.array(start)
        if(start.ndim != 1):
            raise ValueError(f"Numpy array of start values for 'UniformLayer' is expected to be one-dimensional, but is {start.ndim}-dimensional.")
        if(start.shape[0] != self.n_out):
            raise ValueError(f"Length of numpy array of start values for 'UniformLayer' must match number of output nodes {self.n_out}, but is {start.shape[0]}")

        if isinstance(end, int) or isinstance(end, float):
            end = np.array([float(end) for _ in range(self.n_out)])
        if isinstance(end, list):
            end = np.array(end)
        if(end.ndim != 1):
            raise ValueError(f"Numpy array of end values for 'UniformLayer' is expected to be one-dimensional, but is {end.ndim}-dimensional.")
        if(end.shape[0] != self.n_out):
            raise ValueError(f"Length of numpy array of end values for 'UniformLayer' must match number of output nodes {self.n_out}, but is {end.shape[0]}")

        if isinstance(support_outside, bool):
            support_outside = np.array([support_outside for _ in range(self.n_out)])
        if isinstance(support_outside, list):
            support_outside = np.array(support_outside)
        if(support_outside.ndim != 1):
            raise ValueError(f"Numpy array of 'support_outside' values for 'UniformLayer' is expected to be one-dimensional, but is {support_outside.ndim}-dimensional.")
        if(support_outside.shape[0] != self.n_out):
            raise ValueError(f"Length of numpy array of 'support_outside' values for 'UniformLayer' must match number of output nodes {self.n_out}, but is {support_outside.shape[0]}")

        for node_start, node_end, node_support_outside, node in zip(start, end, support_outside, self.nodes):
            node.set_params(node_start, node_end, node_support_outside)
    
    def get_params(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.start, self.end, self.support_outside


@dispatch(memoize=True)
def marginalize(layer: UniformLayer, marg_rvs: Iterable[int], prune: bool=True, dispatch_ctx: Optional[DispatchContext]=None) -> Union[UniformLayer, Uniform, None]:
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
        new_node = Uniform(marg_scopes[0], *marg_params[0])
        return new_node
    else:
        new_layer = UniformLayer(marg_scopes, *[np.array(p) for p in zip(*marg_params)])
        return new_layer