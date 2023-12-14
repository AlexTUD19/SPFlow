"""Contains the abstract ``Module`` class for SPFlow modules in the ``base`` backend.

All valid SPFlow modules in the ``base`` backend should inherit from this class or a subclass of it.
"""
from abc import ABC
from typing import List, Optional, Tuple, Union

import numpy as np
import tensorly as tl
import torch

from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.dispatch.dispatch_context import (
    DispatchContext,
)
from spflow.tensorly.utils.helper_functions import tl_ravel


class Module(ABC):
    r"""Abstract module class for building graph-based models in the ``base`` backend.

    Attributes:
        children:
            List of modules that are children to the module in a directed graph.
        n_out:
            Integer indicating the number of outputs.
        scopes_out:
            List of scopes representing the output scopes.
    """

    def __init__(self, children: Optional[List["Module"]] = None) -> None:
        r"""Initializes ``Module`` object.

        Initializes module by correctly setting its children.

        Args:
            children:
                List of modules that are children to the module.

        Raises:
            ValueError: children of invalid type.
        """
        if children is None:
            children = []

        self.backend = tl.get_backend()
        if any(child.backend != self.backend for child in children):
            raise ValueError("Children must all have the same backend as the parent")
        self.children = children
        self.dtype = self.get_default_dtype()

        # as soon as there are more possible backend with gpu compatibility, a backend distinction is necessary
        self.device = torch.device("cpu")

    def input_to_output_ids(self, input_ids: Union[List[int], tl.tensor]) -> Tuple[List[int], List[int]]:
        """Translates input indices into corresponding child module indices and child module output indices.

        For a given sequence of input indices (taking the inputs of all child modules into account), computes
        the corresponding child module indices and child module output indices.

        Args:
            input_ids:
                List of integers or one-dimensional NumPy array of integers specifying input indices to the module.

        Returns:
            A tuple of two lists of integers. The first list contains indices of child modules and the
            second list contains the corresponding output indices of the respective child modules.
        """
        if len(input_ids) == 0:
            input_ids = list(range(self.n_out))

        if isinstance(input_ids, list):
            input_ids = tl.tensor(input_ids, dtype=tl.int32)

        # remember original shape
        shape = tl.shape(input_ids)
        # flatten tensor
        input_ids = tl_ravel(input_ids)

        # infer number of inputs from children (and their numbers of outputs)
        child_num_outputs = tl.tensor([child.n_out for child in self.children])
        child_cum_outputs = tl.cumsum(child_num_outputs, -1)

        # get child module for corresponding input
        child_ids = tl.sum(child_cum_outputs <= tl.reshape(input_ids, (-1, 1)), axis=1)
        # get output id of child module for corresponding input
        output_ids = input_ids - (child_cum_outputs[child_ids.tolist()] - child_num_outputs[child_ids.tolist()])

        # restore original shape
        child_ids = tl.reshape(child_ids, shape)
        output_ids = tl.reshape(output_ids, shape)

        return tl.tensor(child_ids, dtype=tl.int32).tolist(), tl.tensor(output_ids, dtype=tl.int32).tolist()

    def modules(self):
        modules = []
        for child in self.children:
            modules.extend(list(child.modules()))
        modules.insert(0, self)
        return modules

    def parameters(self):
        return self.get_trainable_params()

    def get_default_dtype(self):
        if self.backend == "numpy":
            return np.float32
        elif self.backend == "pytorch":
            return torch.get_default_dtype()
        else:
            raise NotImplementedError("get_default_dtype() is not implemented for this backend")

    def to_dtype(self, dtype):
        self.dtype = dtype
        for child in self.children:
            child.to_dtype(dtype)

    def to_device(self, device):
        if self.backend == "numpy":
            raise ValueError("it is not possible to change the device of models that have a numpy backend")
        self.device = device
        for child in self.children:
            child.to_device(device)






@dispatch(memoize=True)  # type: ignore
def toNodeBased(mod: Module, dispatch_ctx: Optional[DispatchContext] = None):
    return mod

@dispatch(memoize=True)  # type: ignore
def toLayerBased(mod: Module, dispatch_ctx: Optional[DispatchContext] = None):
    return mod
