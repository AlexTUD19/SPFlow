"""Contains conditional Negative Binomial leaf layer for SPFlow in the ``base`` backend.
"""
from typing import Callable, Iterable, List, Optional, Tuple, Type, Union

import numpy as np
import tensorly as tl
from scipy.stats.distributions import rv_frozen  # type: ignore

from spflow.base.structure.general.nodes.leaves.parametric.cond_negative_binomial import (
    CondNegativeBinomial,
)
from spflow.base.structure.module import Module
from spflow.meta.data.feature_context import FeatureContext
from spflow.meta.data.feature_types import FeatureType, FeatureTypes
from spflow.meta.data.meta_type import MetaType
from spflow.meta.data.scope import Scope
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.dispatch.dispatch_context import (
    DispatchContext,
    init_default_dispatch_context,
)


class CondNegativeBinomialLayer(Module):
    r"""Layer of multiple conditional (univariate) Negative Binomial distribution leaf nodes in the ``base`` backend.

    Represents multiple conditional univariate Negative Binomial distributions with independent scopes, each with the following probability mass function (PMF):

    .. math::

        \text{PMF}(k) = \binom{k+n-1}{n-1}p^n(1-p)^k

    where
        - :math:`k` is the number of failures
        - :math:`n` is the maximum number of successes
        - :math:`\binom{n}{k}` is the binomial coefficient (n choose k)

    Attributes:
        n:
            One-dimensional NumPy array containing the number of successes (greater or equal to 0) for each independent Negative Binomial distribution.
        cond_f:
            Optional callable or list of callables to retrieve parameters for the leaf nodes.
            If a single callable, its output should be a dictionary containing ``p`` as a key, and the value should be
            a floating point, a list of floats or a one-dimensional NumPy array, containing the success probabilities in the range :math:`(0,1]`.
            If it is a single floating point value, the same value is reused for all leaf nodes.
            If a list of callables, each one should return a dictionary containing ``p`` as a key, and the value should
            be a floating point value in the range :math:`(0,1]`.
        scopes_out:
            List of scopes representing the output scopes.
        nodes:
            List of ``CondNegativeBinomial`` objects for the nodes in this layer.
    """

    def __init__(
        self,
        scope: Union[Scope, List[Scope]],
        n: Union[int, List[int], tl.tensor],
        cond_f: Optional[Union[Callable, List[Callable]]] = None,
        n_nodes: int = 1,
        **kwargs,
    ) -> None:
        r"""Initializes ``CondNegativeBinomialLayer`` object.

        Args:
            scope:
                Scope or list of scopes specifying the scopes of the individual distribution.
                If a single scope is given, it is used for all nodes.
            n:
                Integer, list of integers or one-dimensional NumPy array containing the number of successes (greater or equal to 0) for each independent Negative Binomial distribution.
                If a single integer value is given it is broadcast to all nodes.
            cond_f:
                Optional callable or list of callables to retrieve parameters for the leaf nodes.
                If a single callable, its output should be a dictionary containing ``p`` as a key, and the value should be
                a floating point, a list of floats or a one-dimensional NumPy array, containing the success probabilities in the range :math:`(0,1]`.
                If it is a single floating point value, the same value is reused for all leaf nodes.
                If a list of callables, each one should return a dictionary containing ``p`` as a key, and the value should
                be a floating point value in the range :math:`(0,1]`.
            n_nodes:
                Integer specifying the number of nodes the layer should represent. Only relevant if a single scope is given.
                Defaults to 1.
        """
        if isinstance(scope, Scope):
            if n_nodes < 1:
                raise ValueError(
                    f"Number of nodes for 'CondNegativeBinomialLayer' must be greater or equal to 1, but was {n_nodes}"
                )

            scope = [scope for _ in range(n_nodes)]
            self._n_out = n_nodes
        else:
            if len(scope) == 0:
                raise ValueError("List of scopes for 'ConNegativeBinomialLayer' was empty.")

            self._n_out = len(scope)

        super().__init__(children=[], **kwargs)

        # create leaf nodes
        self.nodes = [CondNegativeBinomial(s, 1) for s in scope]

        # compute scope
        self.scopes_out = scope

        # parse weights
        self.set_params(n)

        self.set_cond_f(cond_f)

    @property
    def n_out(self) -> int:
        """Returns the number of outputs for this module. Equal to the number of nodes represented by the layer."""
        return self._n_out

    @property
    def n(self) -> tl.tensor:
        """Returns the numbers of successes of the represented distributions."""
        return tl.tensor([node.n for node in self.nodes])

    @classmethod
    def accepts(cls, signatures: List[FeatureContext]) -> bool:
        """Checks if a specified signature can be represented by the module.

        ``CondNegativeBinomial`` can represent one or more univariate nodes with ``NegativeBinomialType`` domains.

        Returns:
            Boolean indicating whether the module can represent the specified signature (True) or not (False).
        """
        # leaf has at least one output
        if len(signatures) < 1:
            return False

        for signature in signatures:
            if not CondNegativeBinomial.accepts([signature]):
                return False

        return True

    @classmethod
    def from_signatures(cls, signatures: List[FeatureContext]) -> "CondNegativeBinomialLayer":
        """Creates an instance from a specified signature.

        Returns:
            ``CondNegativeBinomialLayer`` instance.

        Raises:
            Signatures not accepted by the module.
        """
        if not cls.accepts(signatures):
            raise ValueError(
                f"'CondNegativeBinomialLayer' cannot be instantiated from the following signatures: {signatures}."
            )

        n = []
        scopes = []

        for feature_ctx in signatures:

            domain = feature_ctx.get_domains()[0]

            # read or initialize parameters
            if isinstance(domain, FeatureTypes.NegativeBinomial):
                n.append(domain.n)
            else:
                raise ValueError(
                    f"Unknown signature type {domain} for 'CondNegativeBinomialLayer' that was not caught during acception checking."
                )

            scopes.append(feature_ctx.scope)

        return CondNegativeBinomialLayer(scopes, n=n)

    def set_cond_f(self, cond_f: Optional[Union[List[Callable], Callable]] = None) -> None:
        r"""Sets the ``cond_f`` property.

        Args:
            cond_f:
                Optional callable or list of callables to retrieve parameters for the leaf nodes.
                If a single callable, its output should be a dictionary containing ``p`` as a key, and the value should be
                a floating point, a list of floats or a one-dimensional NumPy array, containing the success probabilities in the range :math:`(0,1]`.
                If it is a single floating point value, the same value is reused for all leaf nodes.
                If a list of callables, each one should return a dictionary containing ``p`` as a key, and the value should
                be a floating point value in the range :math:`(0,1]`.

        Raises:
            ValueError: If list of callables does not match number of nodes represented by the layer.
        """
        if isinstance(cond_f, List) and len(cond_f) != self.n_out:
            raise ValueError(
                "'CondNegativeBinomialLayer' received list of 'cond_f' functions, but length does not not match number of conditional nodes."
            )

        self.cond_f = cond_f

    def retrieve_params(self, data: tl.tensor, dispatch_ctx: DispatchContext) -> tl.tensor:
        r"""Retrieves the conditional parameters of the leaf layer.

        First, checks if conditional parameter (``p``) is passed as an additional argument in the dispatch context.
        Secondly, checks if a function or list of functions (``cond_f``) is passed as an additional argument in the dispatch context to retrieve the conditional parameters.
        Lastly, checks if a ``cond_f`` is set as an attributed to retrieve the conditional parameter.

        Args:
            data:
                Two-dimensional NumPy array containing the data to compute the conditional parameters.
                Each row is regarded as a sample.
            dispatch_ctx:
                Dispatch context.

        Returns:
            One-dimensional NumPy array representing the success probabilities.

        Raises:
            ValueError: No way to retrieve conditional parameters or invalid conditional parameters.
        """
        p, cond_f = None, None

        # check dispatch cache for required conditional parameter 'p'
        if self in dispatch_ctx.args:
            args = dispatch_ctx.args[self]

            # check if a value for 'p' is specified (highest priority)
            if "p" in args:
                p = args["p"]
            # check if alternative function to provide 'p' is specified (second to highest priority)
            elif "cond_f" in args:
                cond_f = args["cond_f"]
        elif self.cond_f:
            # check if module has a 'cond_f' to provide 'p' specified (lowest priority)
            cond_f = self.cond_f

        # if neither 'p' nor 'cond_f' is specified (via node or arguments)
        if p is None and cond_f is None:
            raise ValueError(
                "'CondNegativeBinomialLayer' requires either 'p' or 'cond_f' to retrieve 'p' to be specified."
            )

        # if 'p' was not already specified, retrieve it
        if p is None:
            # there is a different function for each conditional node
            if isinstance(cond_f, List):
                p = tl.tensor([f(data)["p"] for f in cond_f])
            else:
                p = cond_f(data)["p"]

        if isinstance(p, int) or isinstance(p, float):
            p = tl.tensor([float(p) for _ in range(self.n_out)])
        if isinstance(p, list):
            p = tl.tensor(p)
        if tl.ndim(p) != 1:
            raise ValueError(
                f"Numpy array of 'p' values for 'CondNegativeBinomialLayer' is expected to be one-dimensional, but is {p.ndim}-dimensional."
            )
        if p.shape[0] != self.n_out:
            raise ValueError(
                f"Length of numpy array of 'p' values for 'CondNegativeBinomialLayer' must match number of output nodes {self.n_out}, but is {p.shape[0]}"
            )

        return p

    def set_params(self, n: Union[int, List[int], tl.tensor]) -> None:
        """Sets the parameters for the represented distributions.

        Args:
            n:
                Integer, list of integers or one-dimensional NumPy array containing the number of successes (greater or equal to 0) for each independent Negative Binomial distribution.
                If a single integer value is given it is broadcast to all nodes.
        """
        if isinstance(n, int):
            n = tl.tensor([n for _ in range(self.n_out)])
        if isinstance(n, list):
            n = tl.tensor(n)
        if tl.ndim(n) != 1:
            raise ValueError(
                f"Numpy array of 'n' values for 'CondNegativeBinomialLayer' is expected to be one-dimensional, but is {n.ndim}-dimensional."
            )
        if n.shape[0] != self.n_out:
            raise ValueError(
                f"Length of numpy array of 'n' values for 'CondNegativeBinomialLayer' must match number of output nodes {self.n_out}, but is {n.shape[0]}"
            )

        node_scopes = tl.tensor([s.query[0] for s in self.scopes_out])

        for node_scope in np.unique(node_scopes):
            # at least one such element exists
            n_values = n[node_scopes == node_scope]
            if not tl.all(n_values == n_values[0]):
                raise ValueError(
                    "All values of 'n' for 'CondNegativeBinomialLayer' over the same scope must be identical."
                )

        for node_n, node in zip(n, self.nodes):
            node.set_params(node_n)

    def get_params(self) -> Tuple[tl.tensor]:
        """Returns the parameters of the represented distribution.

        Returns:
            One-dimensional NumPy array representing the numbers of successes.
        """
        return (self.n,)

    def dist(self, p: tl.tensor, node_ids: Optional[List[int]] = None) -> List[rv_frozen]:
        r"""Returns the SciPy distributions represented by the leaf layer.

        Args:
            p:
                One-dimensional NumPy array representing the success probabilities of all distributions between zero and one (not just the ones specified by ``node_ids``).
            node_ids:
                Optional list of integers specifying the indices (and order) of the nodes' distribution to return.
                Defaults to None, in which case all nodes distributions selected.

        Returns:
            List of ``scipy.stats.distributions.rv_frozen`` distributions.
        """
        if node_ids is None:
            node_ids = list(range(self.n_out))

        return [self.nodes[i].dist(p[i]) for i in node_ids]

    def check_support(self, data: tl.tensor, node_ids: Optional[List[int]] = None) -> tl.tensor:
        r"""Checks if specified data is in support of the represented distributions.

        Determines whether or note instances are part of the supports of the Negative Binomial distributions, which are:

        .. math::

            \text{supp}(\text{NegativeBinomial})=\mathbb{N}\cup\{0\}

        Additionally, NaN values are regarded as being part of the support (they are marginalized over during inference).

        Args:
            data:
                Two-dimensional NumPy array containing sample instances.
                Each row is regarded as a sample.
                Assumes that relevant data is located in the columns corresponding to the scope indices.
            node_ids:
                Optional list of integers specifying the indices (and order) of the nodes' distribution to return.
                Defaults to None, in which case all nodes distributions selected.

        Returns:
            Two dimensional NumPy array indicating for each instance and node, whether they are part of the support (True) or not (False).
            Each row corresponds to an input sample.
        """
        if node_ids is None:
            node_ids = list(range(self.n_out))

        return tl.concatenate([self.nodes[i].check_support(data) for i in node_ids], axis=1)


@dispatch(memoize=True)  # type: ignore
def marginalize(
    layer: CondNegativeBinomialLayer,
    marg_rvs: Iterable[int],
    prune: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
) -> Union[CondNegativeBinomialLayer, CondNegativeBinomial, None]:
    r"""Structural marginalization for ``CondNegativeBinomialLayer`` objects in the ``base`` backend.

    Structurally marginalizes the specified layer module.
    If the layer's scope contains non of the random variables to marginalize, then the layer is returned unaltered.
    If the layer's scope is fully marginalized over, then None is returned.

    Args:
        layer:
            Layer module to marginalize.
        marg_rvs:
            Iterable of integers representing the indices of the random variables to marginalize.
        prune:
            Boolean indicating whether or not to prune nodes and modules where possible.
            Has no effect here. Defaults to True.
        dispatch_ctx:
            Optional dispatch context.

    Returns:
        Unaltered leaf layer or None if it is completely marginalized.
    """
    # initialize dispatch context
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)

    # marginalize nodes
    marg_scopes = []
    marg_params = []

    for node in layer.nodes:
        marg_node = marginalize(node, marg_rvs, prune=prune)

        if marg_node is not None:
            marg_scopes.append(marg_node.scope)
            marg_params.append(marg_node.get_params())

    if len(marg_scopes) == 0:
        return None
    elif len(marg_scopes) == 1 and prune:
        new_node = CondNegativeBinomial(marg_scopes[0], tl.tensor(marg_params[0]))
        return new_node
    else:
        new_layer = CondNegativeBinomialLayer(marg_scopes, tl.tensor(sum(marg_params, tuple())))
        return new_layer
