from typing import List, Optional, Callable

import tensorly as tl

from spflow.meta.data import FeatureContext

from spflow.meta.data.scope import Scope


class CondGaussian:  # ToDo: backend über T.getBackend() abfragen
    def __new__(cls, scope: Scope, cond_f: Optional[Callable] = None):
        from spflow.base.structure.general.node.leaf.cond_gaussian import CondGaussian as TensorlyCondGaussian
        from spflow.torch.structure.general.node.leaf.cond_gaussian import CondGaussian as TorchCondGaussian

        """TODO"""
        backend = T.get_backend()
        if backend == "numpy":
            return TensorlyCondGaussian(scope=scope, cond_f=cond_f)
        elif backend == "pytorch":
            return TorchCondGaussian(scope=scope, cond_f=cond_f)
        else:
            raise NotImplementedError("GeneralGaussian is not implemented for this backend")

    @classmethod
    def accepts(cls, signatures: list[FeatureContext]) -> bool:
        from spflow.base.structure.general.node.leaf.cond_gaussian import CondGaussian as TensorlyCondGaussian
        from spflow.torch.structure.general.node.leaf.cond_gaussian import CondGaussian as TorchCondGaussian

        backend = T.get_backend()
        if backend == "numpy":
            return TensorlyCondGaussian.accepts(signatures)
        elif backend == "pytorch":
            return TorchCondGaussian.accepts(signatures)
        else:
            raise NotImplementedError("GeneralGaussian is not implemented for this backend")

    @classmethod
    def from_signatures(cls, signatures: list[FeatureContext]):
        from spflow.base.structure.general.node.leaf.cond_gaussian import CondGaussian as TensorlyCondGaussian
        from spflow.torch.structure.general.node.leaf.cond_gaussian import CondGaussian as TorchCondGaussian

        backend = T.get_backend()
        if backend == "numpy":
            return TensorlyCondGaussian.from_signatures(signatures)
        elif backend == "pytorch":
            return TorchCondGaussian.from_signatures(signatures)
        else:
            raise NotImplementedError("GeneralGaussian is not implemented for this backend")
