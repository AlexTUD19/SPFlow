"""
Created on November 06, 2021

@authors: Kevin Huy Nguyen, Philipp Deibert
"""

from spflow.base.structure.nodes.leaves.parametric import (
    Hypergeometric,
    get_scipy_object,
    get_scipy_object_parameters,
)
from .parametric import MIN_NEG
from multipledispatch import dispatch  # type: ignore

import numpy as np


@dispatch(Hypergeometric, data=np.ndarray)  # type: ignore[no-redef]
def node_likelihood(node: Hypergeometric, data: np.ndarray) -> np.ndarray:

    # initialize probabilities
    probs = np.ones((data.shape[0], 1))

    # select relevant data based on node's scope
    data = data[:, node.scope]

    # create mask based on marginalized instances (NaNs)
    # keeps default value of 1 (0 in log-space)
    marg_ids = np.isnan(data).sum(axis=-1).astype(bool)

    # create masked based on distribution's support
    valid_ids = node.check_support(data[~marg_ids])

    if not all(valid_ids):
        raise ValueError(
            f"Encountered data instances that are not in the support of the Gaussian distribution."
        )

    # compute probabilities for all non-marginalized instances
    probs[~marg_ids] = get_scipy_object(node).pmf(
        k=data[~marg_ids], **get_scipy_object_parameters(node)
    )

    return probs


@dispatch(Hypergeometric, data=np.ndarray)  # type: ignore[no-redef]
def node_log_likelihood(node: Hypergeometric, data: np.ndarray) -> np.ndarray:

    # initialize probabilities
    probs = np.zeros((data.shape[0], 1))

    # select relevant data based on node's scope
    data = data[:, node.scope]

    # create mask based on marginalized instances (NaNs)
    # keeps default value of 1 (0 in log-space)
    marg_ids = np.isnan(data).sum(axis=-1).astype(bool)

    # create masked based on distribution's support
    valid_ids = node.check_support(data[~marg_ids])

    if not all(valid_ids):
        raise ValueError(
            f"Encountered data instances that are not in the support of the Hypergeometric distribution."
        )

    # compute probabilities for all non-marginalized instances
    probs[~marg_ids] = get_scipy_object(node).logpmf(
        k=data[~marg_ids], **get_scipy_object_parameters(node)
    )

    return probs
