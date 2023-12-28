from typing import List, Optional, Callable

import tensorly as tl

from spflow.meta.data import FeatureContext

from spflow.meta.data.scope import Scope


class CondNegativeBinomial:  # ToDo: backend über T.getBackend() abfragen
    def __new__(cls, scope: Scope, n: int, cond_f: Optional[Callable] = None):
        from spflow.base.structure.general.node.leaf.cond_negative_binomial import (
            CondNegativeBinomial as TensorlyCondNegativeBinomial,
        )
        from spflow.torch.structure.general.node.leaf.cond_negative_binomial import (
            CondNegativeBinomial as TorchCondNegativeBinomial,
        )

        """TODO"""
        backend = T.get_backend()
        if backend == "numpy":
            return TensorlyCondNegativeBinomial(scope=scope, n=n, cond_f=cond_f)
        elif backend == "pytorch":
            return TorchCondNegativeBinomial(scope=scope, n=n, cond_f=cond_f)
        else:
            raise NotImplementedError("CondNegativeBinomial is not implemented for this backend")

    @classmethod
    def accepts(cls, signatures: list[FeatureContext]) -> bool:
        from spflow.base.structure.general.node.leaf.cond_negative_binomial import (
            CondNegativeBinomial as TensorlyCondNegativeBinomial,
        )
        from spflow.torch.structure.general.node.leaf.cond_negative_binomial import (
            CondNegativeBinomial as TorchCondNegativeBinomial,
        )

        backend = T.get_backend()
        if backend == "numpy":
            return TensorlyCondNegativeBinomial.accepts(signatures)
        elif backend == "pytorch":
            return TorchCondNegativeBinomial.accepts(signatures)
        else:
            raise NotImplementedError("CondNegativeBinomial is not implemented for this backend")

    @classmethod
    def from_signatures(cls, signatures: list[FeatureContext]):
        from spflow.base.structure.general.node.leaf.cond_negative_binomial import (
            CondNegativeBinomial as TensorlyCondNegativeBinomial,
        )
        from spflow.torch.structure.general.node.leaf.cond_negative_binomial import (
            CondNegativeBinomial as TorchCondNegativeBinomial,
        )

        backend = T.get_backend()
        if backend == "numpy":
            return TensorlyCondNegativeBinomial.from_signatures(signatures)
        elif backend == "pytorch":
            return TorchCondNegativeBinomial.from_signatures(signatures)
        else:
            raise NotImplementedError("CondNegativeBinomial is not implemented for this backend")
