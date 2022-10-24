"""
Created on October 20, 2022

@authors: Philipp Deibert
"""
import numpy as np
import torch
import torch.distributions as D
from torch.nn.parameter import Parameter
from typing import List, Tuple, Optional, Callable
from .projections import proj_bounded_to_real, proj_real_to_bounded
from spflow.meta.scope.scope import Scope
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.contexts.dispatch_context import DispatchContext, init_default_dispatch_context
from spflow.torch.structure.nodes.node import LeafNode
from spflow.base.structure.nodes.leaves.parametric.cond_bernoulli import CondBernoulli as BaseCondBernoulli


class CondBernoulli(LeafNode):
    r"""Conditional (univariate) Bernoulli distribution for Torch backend.

    .. math::

        \text{PMF}(k)=\begin{cases} p   & \text{if } k=1\\
                                    1-p & \text{if } k=0\end{cases}
        
    where
        - :math:`p` is the success probability
        - :math:`k` is the outcome of the trial (0 or 1)

    Args:
        scope:
            List of integers specifying the variable scope.
        cond_f: TODO
    """
    def __init__(self, scope: Scope, cond_f: Optional[Callable]=None) -> None:

        if len(scope.query) != 1:
            raise ValueError(f"Scope size for CondBernoulli should be 1, but was: {len(scope.query)}")
        if len(scope.evidence):
            raise ValueError(f"Evidence scope for CondBernoulli should be empty, but was {scope.evidence}.")

        super(CondBernoulli, self).__init__(scope=scope)

        self.set_cond_f(cond_f)

    def set_cond_f(self, cond_f: Optional[Callable]=None) -> None:
        self.cond_f = cond_f

    def retrieve_params(self, data: torch.Tensor, dispatch_ctx: DispatchContext) -> Tuple[torch.Tensor]:
        
        p, cond_f = None, None

        # check dispatch cache for required conditional parameter 'p'
        if self in dispatch_ctx.args:
            args = dispatch_ctx.args[self]

            # check if a value for 'p' is specified (highest priority)
            if "p" in args:
                p = args["p"]
            # check if alternative function to provide 'p' is specified (second to highest priority)
            elif "cond_f" in args:
                cond_f = args["cond_f"]
        elif self.cond_f:
            # check if module has a 'cond_f' to provide 'p' specified (lowest priority)
            cond_f = self.cond_f

        # if neither 'p' nor 'cond_f' is specified (via node or arguments)
        if p is None and cond_f is None:
            raise ValueError("'CondBernoulli' requires either 'p' or 'cond_f' to retrieve 'p' to be specified.")

        # if 'p' was not already specified, retrieve it
        if p is None:
            p = cond_f(data)['p']

        if isinstance(p, float):
            p = torch.tensor(p)

        # check if value for 'p' is valid
        if p < 0.0 or p > 1.0 or not torch.isfinite(p):
            raise ValueError(
                f"Value of p for CondBernoulli distribution must to be between 0.0 and 1.0, but was: {p}"
            )
        
        return p

    def get_params(self) -> Tuple:
        return tuple([])

    def dist(self, p: torch.Tensor) -> D.Distribution:
        return D.Bernoulli(probs=p)

    def check_support(self, scope_data: torch.Tensor) -> torch.Tensor:
        r"""Checks if instances are part of the support of the Bernoulli distribution.

        .. math::

            \text{supp}(\text{Bernoulli})=\{0,1\}
        
        Additionally, NaN values are regarded as being part of the support (they are marginalized over during inference).

        Args:
            scope_data:
                Torch tensor containing possible distribution instances.
        Returns:
            Torch tensor indicating for each possible distribution instance, whether they are part of the support (True) or not (False).
        """

        if scope_data.ndim != 2 or scope_data.shape[1] != len(self.scope.query):
            raise ValueError(
                f"Expected scope_data to be of shape (n,{len(self.scope.query)}), but was: {scope_data.shape}"
            )

        # nan entries (regarded as valid)
        nan_mask = torch.isnan(scope_data)

        valid = torch.ones(scope_data.shape[0], 1, dtype=torch.bool)
        valid[~nan_mask] = self.dist(p=torch.tensor(0.0)).support.check(scope_data[~nan_mask]).squeeze(-1)  # type: ignore

        # check for infinite values
        valid[~nan_mask & valid] &= ~scope_data[~nan_mask & valid].isinf().squeeze(-1)

        return valid


@dispatch(memoize=True)
def toTorch(node: BaseCondBernoulli, dispatch_ctx: Optional[DispatchContext]=None) -> CondBernoulli:
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    return CondBernoulli(node.scope)


@dispatch(memoize=True)
def toBase(torch_node: CondBernoulli, dispatch_ctx: Optional[DispatchContext]=None) -> BaseCondBernoulli:
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    return BaseCondBernoulli(torch_node.scope)