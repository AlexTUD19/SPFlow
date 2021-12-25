"""
Created on November 6, 2021

@authors: Bennet Wittelsbach, Philipp Deibert
"""

from .parametric import ParametricLeaf
from .statistical_types import ParametricType
from .exceptions import InvalidParametersError
from typing import Tuple, Dict, List
import numpy as np
from scipy.stats import norm  # type: ignore
from scipy.stats._distn_infrastructure import rv_continuous  # type: ignore
from multipledispatch import dispatch  # type: ignore


class Gaussian(ParametricLeaf):
    """(Univariate) Normal distribution.

    PDF(x) =
        1/sqrt(2*pi*sigma^2) * exp(-(x-mu)^2/(2*sigma^2)), where
            - x is an observation
            - mu is the mean
            - sigma is the standard deviation

    Attributes:
        mean:
            mean (mu) of the distribution.
        stdev:
            standard deviation (sigma) of the distribution.
    """

    type = ParametricType.CONTINUOUS

    def __init__(
        self,
        scope: List[int],
        mean: float = None,
        stdev: float = None,
    ) -> None:
        if len(scope) != 1:
            raise ValueError(f"Scope size for Gaussian should be 1, but was: {len(scope)}")
        super().__init__(scope)
        self.mean = mean if mean is not None else np.random.uniform(-1, 1)
        self.stdev = stdev if stdev is not None else np.random.uniform(0, 1)
        self.set_params(self.mean, self.stdev)

    def set_params(self, mean: float, stdev: float) -> None:

        if not (np.isfinite(mean) and np.isfinite(stdev)):
            raise ValueError(
                f"Mean and standard deviation for Gaussian distribution must be finite, but were: {mean}, {stdev}"
            )
        if stdev <= 0.0:
            raise ValueError(
                f"Standard deviation for Gaussian distribution must be greater than 0.0, but was: {stdev}"
            )

        self.mean = mean
        self.stdev = stdev

    def get_params(self) -> Tuple[float, float]:
        return self.mean, self.stdev

    def check_support(self, scope_data: np.ndarray) -> np.ndarray:

        valid = np.ones(scope_data.shape, dtype=bool)

        return valid


@dispatch(Gaussian)  # type: ignore[no-redef]
def get_scipy_object(node: Gaussian) -> rv_continuous:
    return norm


@dispatch(Gaussian)  # type: ignore[no-redef]
def get_scipy_object_parameters(node: Gaussian) -> Dict[str, float]:
    if node.mean is None:
        raise InvalidParametersError(f"Parameter 'mean' of {node} must not be None")
    if node.stdev is None:
        raise InvalidParametersError(f"Parameter 'stdev' of {node} must not be None")
    parameters = {"loc": node.mean, "scale": node.stdev}
    return parameters
