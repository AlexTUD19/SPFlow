"""
Created on November 06, 2021

@authors: Philipp Deibert
"""
import numpy as np
import torch
import torch.distributions as D
from torch.nn.parameter import Parameter
from typing import List, Tuple, Optional
from .projections import proj_bounded_to_real, proj_real_to_bounded
from spflow.meta.scope.scope import Scope
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.contexts.dispatch_context import DispatchContext, init_default_dispatch_context
from spflow.torch.structure.nodes.node import LeafNode
from spflow.base.structure.nodes.leaves.parametric.log_normal import LogNormal as BaseLogNormal


class LogNormal(LeafNode):
    r"""(Univariate) Log-Normal distribution for Torch backend.

    .. math::

        \text{PDF}(x) = \frac{1}{x\sigma\sqrt{2\pi}}\exp\left(-\frac{(\ln(x)-\mu)^2}{2\sigma^2}\right)

    where
        - :math:`x` is an observation
        - :math:`\mu` is the mean
        - :math:`\sigma` is the standard deviation

    Args:
        scope:
            List of integers specifying the variable scope.
        mean:
            mean (:math:`\mu`) of the distribution (default 0.0).
        std:
            standard deviation (:math:`\sigma`) of the distribution (must be greater than 0; default 1.0).
    """
    def __init__(self, scope: Scope, mean: Optional[float]=0.0, std: Optional[float]=1.0) -> None:

        if len(scope.query) != 1:
            raise ValueError(f"Query scope size for LogNormal should be 1, but was: {len(scope.query)}.")
        if len(scope.evidence):
            raise ValueError(f"Evidence scope for LogNormal should be empty, but was {scope.evidence}.")

        super(LogNormal, self).__init__(scope=scope)

        # register mean as torch parameter
        self.mean = Parameter()
        # register auxiliary torch paramter for standard deviation
        self.std_aux = Parameter()

        # set parameters
        self.set_params(mean, std)

    @property
    def std(self) -> torch.Tensor:
        # project auxiliary parameter onto actual parameter range
        return proj_real_to_bounded(self.std_aux, lb=0.0)  # type: ignore

    @property
    def dist(self) -> D.Distribution:
        return D.LogNormal(loc=self.mean, scale=self.std)

    def set_params(self, mean: float, std: float) -> None:

        if not (np.isfinite(mean) and np.isfinite(std)):
            raise ValueError(
                f"Mean and standard deviation for Gaussian distribution must be finite, but were: {mean}, {std}"
            )
        if std <= 0.0:
            raise ValueError(
                f"Standard deviation for Gaussian distribution must be greater than 0.0, but was: {std}"
            )

        self.mean.data = torch.tensor(float(mean))
        self.std_aux.data = proj_bounded_to_real(torch.tensor(float(std)), lb=0.0)

    def get_params(self) -> Tuple[float, float]:
        return self.mean.data.cpu().numpy(), self.std.data.cpu().numpy()  # type: ignore

    def check_support(self, scope_data: torch.Tensor) -> torch.Tensor:
        r"""Checks if instances are part of the support of the LogNormal distribution.

        .. math::

            \text{supp}(\text{LogNormal})=(0,\infty)

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
        valid[~nan_mask] = self.dist.support.check(scope_data[~nan_mask]).squeeze(-1)  # type: ignore

        # check for infinite values
        valid[~nan_mask & valid] &= ~scope_data[~nan_mask & valid].isinf().squeeze(-1)

        return valid


@dispatch(memoize=True)
def toTorch(node: BaseLogNormal, dispatch_ctx: Optional[DispatchContext]=None) -> LogNormal:
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    return LogNormal(node.scope, *node.get_params())


@dispatch(memoize=True)
def toBase(torch_node: LogNormal, dispatch_ctx: Optional[DispatchContext]=None) -> BaseLogNormal:
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    return BaseLogNormal(torch_node.scope, *torch_node.get_params())