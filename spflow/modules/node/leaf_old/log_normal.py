from typing import List

import tensorly as tl

from spflow.meta.data import FeatureContext

from spflow.meta.data.scope import Scope


class LogNormal:  # ToDo: backend über T.getBackend() abfragen
    def __new__(cls, scope: Scope, mean: float = 0.0, std: float = 1.0):
        from spflow.base.structure.general.node.leaf.log_normal import LogNormal as TensorlyLogNormal
        from spflow.torch.structure.general.node.leaf.log_normal import LogNormal as TorchLogNormal

        """TODO"""
        backend = T.get_backend()
        if backend == "numpy":
            return TensorlyLogNormal(scope=scope, mean=mean, std=std)
        elif backend == "pytorch":
            return TorchLogNormal(scope=scope, mean=mean, std=std)
        else:
            raise NotImplementedError("LogNormal is not implemented for this backend")

    @classmethod
    def accepts(cls, signatures: list[FeatureContext]) -> bool:
        from spflow.base.structure.general.node.leaf.log_normal import LogNormal as TensorlyLogNormal
        from spflow.torch.structure.general.node.leaf.log_normal import LogNormal as TorchLogNormal

        backend = T.get_backend()
        if backend == "numpy":
            return TensorlyLogNormal.accepts(signatures)
        elif backend == "pytorch":
            return TorchLogNormal.accepts(signatures)
        else:
            raise NotImplementedError("LogNormal is not implemented for this backend")

    @classmethod
    def from_signatures(cls, signatures: list[FeatureContext]):
        from spflow.base.structure.general.node.leaf.log_normal import LogNormal as TensorlyLogNormal
        from spflow.torch.structure.general.node.leaf.log_normal import LogNormal as TorchLogNormal

        backend = T.get_backend()
        if backend == "numpy":
            return TensorlyLogNormal.from_signatures(signatures)
        elif backend == "pytorch":
            return TorchLogNormal.from_signatures(signatures)
        else:
            raise NotImplementedError("LogNormal is not implemented for this backend")
