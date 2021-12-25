"""
Created on November 06, 2021

@authors: Philipp Deibert
"""

import numpy as np
import torch
import torch.distributions as D
from typing import List, Tuple
from .parametric import TorchParametricLeaf
from spflow.base.structure.nodes.leaves.parametric.statistical_types import ParametricType
from spflow.base.structure.nodes.leaves.parametric import Uniform

from multipledispatch import dispatch  # type: ignore


class TorchUniform(TorchParametricLeaf):
    r"""(Univariate) continuous Uniform distribution.

    .. math::

        \text{PDF}(x) = \frac{1}{\text{end} - \text{start}}\mathbf{1}_{[\text{start}, \text{end}]}(x)

    where
        - :math:`x` is the input observation
        - :math:`\mathbf{1}_{[\text{start}, \text{end}]}` is the indicator function for the given interval (evaluating to 0 if x is not in the interval)

    Args:
        scope:
            List of integers specifying the variable scope.
        start:
            Start of the interval.
        end:
            End of interval (must be larger than start).
    """

    ptype = ParametricType.CONTINUOUS

    def __init__(
        self, scope: List[int], start: float, end: float, support_outside: bool = True
    ) -> None:

        if len(scope) != 1:
            raise ValueError(f"Scope size for TorchUniform should be 1, but was: {len(scope)}")

        super(TorchUniform, self).__init__(scope)

        # register interval bounds as torch buffers (should not be changed)
        self.register_buffer("start", torch.empty(size=[]))
        self.register_buffer("end", torch.empty(size=[]))

        # set parameters
        self.set_params(start, end, support_outside)

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
                f"Encountered data instances that are not in the support of the TorchUniform distribution."
            )

        if self.support_outside:
            torch_valid_ids = torch.zeros(len(marg_ids), dtype=torch.bool)
            torch_valid_ids[~marg_ids] |= self.dist.support.check(scope_data[~marg_ids]).squeeze(1)
            # TODO: torch_valid_ids does not necessarily have the same dimension as marg_ids
            # try:
            log_prob[~marg_ids & ~torch_valid_ids] = -float("inf")
            # except:
            #    print(marg_ids, torch_valid_ids)
            #    print(err)

            # compute probabilities for values inside distribution support
            log_prob[~marg_ids & torch_valid_ids] = self.dist.log_prob(
                scope_data[~marg_ids & torch_valid_ids].type(torch.get_default_dtype())
            )
        else:
            # compute probabilities for values inside distribution support
            log_prob[~marg_ids] = self.dist.log_prob(
                scope_data[~marg_ids].type(torch.get_default_dtype())
            )

        return log_prob

        return log_prob

    def set_params(self, start: float, end: float, support_outside: bool = True) -> None:

        if not start < end:
            raise ValueError(
                f"Lower bound for TorchUniform distribution must be less than upper bound, but were: {start}, {end}"
            )
        if not (np.isfinite(start) and np.isfinite(end)):
            raise ValueError(f"Lower and upper bound must be finite, but were: {start}, {end}")

        # since torch Uniform distribution excludes the upper bound, compute next largest number
        end_next = torch.nextafter(torch.tensor(end), torch.tensor(float("Inf")))  # type: ignore

        self.start.data = torch.tensor(float(start))  # type: ignore
        self.end.data = torch.tensor(float(end_next))  # type: ignore
        self.support_outside = support_outside

        # create Torch distribution with specified parameters
        self.dist = D.Uniform(low=self.start, high=end_next)

    def get_params(self) -> Tuple[float, float, bool]:
        return self.start.cpu().numpy(), self.end.cpu().numpy(), self.support_outside  # type: ignore

    def check_support(self, scope_data: torch.Tensor) -> torch.Tensor:

        if scope_data.shape[1] != len(self.scope):
            raise ValueError(
                f"Dimension 1 of scope_data is expected to match the scope length {len(self.scope)}, but was {scope_data.shape[1]} instead."
            )

        # torch distribution support is an interval, despite representing a distribution over a half-open interval
        # end is adjusted to the next largest number to make sure that desired end is part of the distribution interval
        # may cause issues with the support check; easier to do a manual check instead
        valid = torch.ones(scope_data.shape, dtype=torch.bool)

        # check for infinite values
        valid &= ~scope_data.isinf().sum(dim=-1, keepdim=True).bool()

        # check if values are within valid range
        if not self.support_outside:

            mask = valid.clone()
            valid[mask] &= (scope_data[mask] >= self.start) & (scope_data[mask] < self.end)

        return valid.squeeze(1)


@dispatch(Uniform)  # type: ignore[no-redef]
def toTorch(node: Uniform) -> TorchUniform:
    return TorchUniform(node.scope, node.start, node.end)


@dispatch(TorchUniform)  # type: ignore[no-redef]
def toNodes(torch_node: TorchUniform) -> Uniform:
    return Uniform(torch_node.scope, torch_node.start.cpu().numpy(), torch_node.end.cpu().numpy())  # type: ignore
