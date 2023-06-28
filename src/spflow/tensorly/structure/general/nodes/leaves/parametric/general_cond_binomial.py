from typing import List, Optional, Callable

import tensorly as tl

from spflow.meta.data import FeatureContext

from spflow.meta.data.scope import Scope


class CondBinomial:  # ToDo: backend über tl.getBackend() abfragen
    def __new__(cls, scope: Scope, n: int, cond_f: Optional[Callable] = None):
        from spflow.tensorly.structure.general.nodes.leaves import CondBinomial as TensorlyCondBinomial
        from spflow.torch.structure.general.nodes.leaves import CondBinomial as TorchCondBinomial
        """TODO"""
        backend = tl.get_backend()
        if backend == "numpy":
            return TensorlyCondBinomial(scope=scope, n=n, cond_f=cond_f)
        elif backend == "pytorch":
            return TorchCondBinomial(scope=scope, n=n, cond_f=cond_f)
        else:
            raise NotImplementedError("GeneralGaussian is not implemented for this backend")

    @classmethod
    def accepts(cls, signatures: List[FeatureContext]) -> bool:
        from spflow.tensorly.structure.general.nodes.leaves import CondBinomial as TensorlyCondBinomial
        from spflow.torch.structure.general.nodes.leaves import CondBinomial as TorchCondBinomial
        backend = tl.get_backend()
        if backend == "numpy":
            return TensorlyCondBinomial.accepts(signatures)
        elif backend == "pytorch":
            return TorchCondBinomial.accepts(signatures)
        else:
            raise NotImplementedError("GeneralGaussian is not implemented for this backend")

    @classmethod
    def from_signatures(cls, signatures: List[FeatureContext]):
        from spflow.tensorly.structure.general.nodes.leaves import CondBinomial as TensorlyCondBinomial
        from spflow.torch.structure.general.nodes.leaves import CondBinomial as TorchCondBinomial
        backend = tl.get_backend()
        if backend == "numpy":
            return TensorlyCondBinomial.from_signatures(signatures)
        elif backend == "pytorch":
            return TorchCondBinomial.from_signatures(signatures)
        else:
            raise NotImplementedError("GeneralGaussian is not implemented for this backend")
