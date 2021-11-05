import numpy as np
import torch
import torch.distributions as D
from torch.nn.parameter import Parameter
from typing import List, Tuple
from .parametric import TorchParametricLeaf, proj_bounded_to_real, proj_real_to_bounded
from spflow.base.structure.nodes.leaves.parametric.statistical_types import ParametricType
from spflow.base.structure.nodes.leaves.parametric import Exponential

from multipledispatch import dispatch  # type: ignore


class TorchExponential(TorchParametricLeaf):
    """(Univariate) Exponential distribution.
    PDF(x) =
        l * exp(-l * x) , if x > 0
        0               , if x <= 0
    Attributes:
        l:
            Rate parameter of the Exponential distribution (usually denoted as lambda, must be greater than 0).
    """

    ptype = ParametricType.POSITIVE

    def __init__(self, scope: List[int], l: float) -> None:
        super(TorchExponential, self).__init__(scope)

        # register auxiliary torch parameter for parameter l
        self.l_aux = Parameter()

        # set parameters
        self.set_params(l)

    @property
    def l(self) -> torch.Tensor:
        # project auxiliary parameter onto actual parameter range
        return proj_real_to_bounded(self.l_aux, lb=0.0)  # type: ignore

    @property
    def dist(self) -> D.Distribution:
        return D.Exponential(rate=self.l)

    def forward(self, data: torch.Tensor) -> torch.Tensor:

        batch_size: int = data.shape[0]

        # get information relevant for the scope
        scope_data = data[:, list(self.scope)]

        # initialize empty tensor (number of output values matches batch_size)
        log_prob: torch.Tensor = torch.empty(batch_size, 1)

        # ----- marginalization -----

        # if the scope variables are fully marginalized over (NaNs) return probability 1 (0 in log-space)
        log_prob[torch.isnan(scope_data).sum(dim=1) == len(self.scope)] = 0.0

        # ----- log probabilities -----

        # create Torch distribution with specified parameters
        dist = D.Exponential(rate=self.l)

        # compute probabilities on data samples where we have all values
        prob_mask = torch.isnan(scope_data).sum(dim=1) == 0
        # set probabilities of values outside of distribution support to 0 (-inf in log space)
        support_mask = (scope_data >= 0).sum(dim=1).bool()
        log_prob[prob_mask & (~support_mask)] = -float("Inf")
        # compute probabilities for values inside distribution support
        log_prob[prob_mask & support_mask] = dist.log_prob(scope_data[prob_mask & support_mask])

        return log_prob

    def set_params(self, l: float) -> None:

        if l <= 0.0 or not np.isfinite(l):
            raise ValueError(
                f"Value of l for Exponential distribution must be greater than 0, but was: {l}"
            )

        self.l_aux.data = proj_bounded_to_real(torch.tensor(float(l)), lb=0.0)

    def get_params(self) -> Tuple[float]:
        return (self.l.data.cpu().numpy(),)  # type: ignore


@dispatch(Exponential)  # type: ignore[no-redef]
def toTorch(node: Exponential) -> TorchExponential:
    return TorchExponential(node.scope, *node.get_params())


@dispatch(TorchExponential)  # type: ignore[no-redef]
def toNodes(torch_node: TorchExponential) -> Exponential:
    return Exponential(torch_node.scope, *torch_node.get_params())
