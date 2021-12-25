"""
Created on November 06, 2021

@authors: Philipp Deibert
"""

import numpy as np
import torch
import torch.distributions as D
from torch.nn.parameter import Parameter
from typing import List, Tuple
from .parametric import TorchParametricLeaf, proj_bounded_to_real, proj_real_to_bounded
from spflow.base.structure.nodes.leaves.parametric.statistical_types import ParametricType
from spflow.base.structure.nodes.leaves.parametric import Geometric

from multipledispatch import dispatch  # type: ignore


class TorchGeometric(TorchParametricLeaf):
    r"""(Univariate) Geometric distribution.

    .. math::

        \text{PMF}(k) =  p(1-p)^{k-1}

    where
        - :math:`k` is the number of trials
        - :math:`p` is the success probability of each trial

    Note, that the Geometric distribution as implemented in PyTorch uses :math:`k-1` as input.

    Args:
        scope:
            List of integers specifying the variable scope.
        p:
            Probability of success in the range :math:`(0,1]`.
    """

    ptype = ParametricType.BINARY

    def __init__(self, scope: List[int], p: float) -> None:

        if len(scope) != 1:
            raise ValueError(f"Scope size for TorchGeometric should be 1, but was: {len(scope)}")

        super(TorchGeometric, self).__init__(scope)

        # register auxiliary torch parameter for the success probability p
        self.p_aux = Parameter()

        # set parameters
        self.set_params(p)

    @property
    def p(self) -> torch.Tensor:
        # project auxiliary parameter onto actual parameter range
        return proj_real_to_bounded(self.p_aux, lb=0.0, ub=1.0)  # type: ignore

    @property
    def dist(self) -> D.Distribution:
        return D.Geometric(probs=self.p)

    def forward(self, data: torch.Tensor) -> torch.Tensor:

        batch_size: int = data.shape[0]

        # get information relevant for the scope
        scope_data = data[:, list(self.scope)]

        # initialize empty tensor (number of output values matches batch_size)
        log_prob: torch.Tensor = torch.empty(batch_size, 1)

        # ----- marginalization -----

        marg_ids = torch.isnan(scope_data).sum(dim=1) == len(self.scope)

        # if the scope variables are fully marginalized over (NaNs) return probability 1 (0 in log-space)
        log_prob[marg_ids] = 0.0

        # ----- log probabilities -----

        # create masked based on distribution's support
        valid_ids = self.check_support(scope_data[~marg_ids])

        if not all(valid_ids):
            raise ValueError(
                f"Encountered data instances that are not in the support of the TorchGeometric distribution."
            )

        # compute probabilities for values inside distribution support
        # data needs to be offset by -1 due to the different definitions between SciPy and PyTorch
        log_prob[~marg_ids] = self.dist.log_prob(
            scope_data[~marg_ids].type(torch.get_default_dtype()) - 1
        )

        return log_prob

    def set_params(self, p: float) -> None:

        if p <= 0.0 or p > 1.0 or not np.isfinite(p):
            raise ValueError(
                f"Value of p for TorchGeometric distribution must to be greater than 0.0 and less or equal to 1.0, but was: {p}"
            )

        self.p_aux.data = proj_bounded_to_real(torch.tensor(float(p)), lb=0.0, ub=1.0)

    def get_params(self) -> Tuple[float]:
        return (self.p.data.cpu().numpy(),)  # type: ignore

    def check_support(self, scope_data: torch.Tensor) -> torch.Tensor:
        # data needs to be offset by -1 due to the different definitions between SciPy and PyTorch
        return self.dist.support.check(scope_data - 1)  # type: ignore


@dispatch(Geometric)  # type: ignore[no-redef]
def toTorch(node: Geometric) -> TorchGeometric:
    return TorchGeometric(node.scope, *node.get_params())


@dispatch(TorchGeometric)  # type: ignore[no-redef]
def toNodes(torch_node: TorchGeometric) -> Geometric:
    return Geometric(torch_node.scope, *torch_node.get_params())
