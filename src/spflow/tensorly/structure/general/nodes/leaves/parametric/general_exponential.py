from typing import List

import tensorly as tl

from spflow.meta.data import FeatureContext

from spflow.meta.data.scope import Scope


class Exponential:  # ToDo: backend über tl.getBackend() abfragen
    def __new__(cls, scope: Scope, l: float = 1.0):
        from spflow.base.structure.general.nodes.leaves.parametric.exponential import Exponential as TensorlyExponential
        from spflow.torch.structure.general.nodes.leaves.parametric.exponential import Exponential as TorchExponential
        """TODO"""
        backend = tl.get_backend()
        if backend == "numpy":
            return TensorlyExponential(scope=scope, l=l)
        elif backend == "pytorch":
            return TorchExponential(scope=scope, l=l)
        else:
            raise NotImplementedError("Exponential is not implemented for this backend")

    @classmethod
    def accepts(cls, signatures: List[FeatureContext]) -> bool:
        from spflow.base.structure.general.nodes.leaves.parametric.exponential import Exponential as TensorlyExponential
        from spflow.torch.structure.general.nodes.leaves.parametric.exponential import Exponential as TorchExponential
        backend = tl.get_backend()
        if backend == "numpy":
            return TensorlyExponential.accepts(signatures)
        elif backend == "pytorch":
            return TorchExponential.accepts(signatures)
        else:
            raise NotImplementedError("Exponential is not implemented for this backend")

    @classmethod
    def from_signatures(cls, signatures: List[FeatureContext]):
        from spflow.base.structure.general.nodes.leaves.parametric.exponential import Exponential as TensorlyExponential
        from spflow.torch.structure.general.nodes.leaves.parametric.exponential import Exponential as TorchExponential
        backend = tl.get_backend()
        if backend == "numpy":
            return TensorlyExponential.from_signatures(signatures)
        elif backend == "pytorch":
            return TorchExponential.from_signatures(signatures)
        else:
            raise NotImplementedError("Exponential is not implemented for this backend")
