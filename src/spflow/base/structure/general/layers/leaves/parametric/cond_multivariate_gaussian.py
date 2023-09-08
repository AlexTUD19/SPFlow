"""Contains conditional Multivariate Gaussian leaf layer for SPFlow in the ``base`` backend.
"""
from typing import Callable, Iterable, List, Optional, Tuple, Type, Union

import numpy as np
import tensorly as tl
from scipy.stats.distributions import rv_frozen  # type: ignore

from spflow.base.structure.general.nodes.leaves.parametric.cond_gaussian import (
    CondGaussian,
)
from spflow.base.structure.general.nodes.leaves.parametric.cond_multivariate_gaussian import (
    CondMultivariateGaussian,
)
from spflow.tensorly.structure.spn.layers.leaves.parametric import CondMultivariateGaussianLayer as GeneralCondMultivariateGaussianLayer

from spflow.tensorly.structure.module import Module
from spflow.meta.data.feature_context import FeatureContext
from spflow.meta.data.feature_types import FeatureType, FeatureTypes
from spflow.meta.data.meta_type import MetaType
from spflow.meta.data.scope import Scope
from spflow.meta.dispatch.dispatch import dispatch
from spflow.meta.dispatch.dispatch_context import (
    DispatchContext,
    init_default_dispatch_context,
)


class CondMultivariateGaussianLayer(Module):
    r"""Layer of multiple conditional multivariate Gaussian distribution leaf node in the ``base`` backend.

    Represents multiple conditional multivariate Gaussian distributions with independent scopes, each with the following probability distribution function (PDF):

    .. math::

        \text{PDF}(x) = \frac{1}{\sqrt{(2\pi)^d\det\Sigma}}\exp\left(-\frac{1}{2} (x-\mu)^T\Sigma^{-1}(x-\mu)\right)

    where
        - :math:`d` is the dimension of the distribution
        - :math:`x` is the :math:`d`-dim. vector of observations
        - :math:`\mu` is the :math:`d`-dim. mean vector
        - :math:`\Sigma` is the :math:`d\times d` covariance matrix

    Attributes:
        cond_f:
            Optional callable or list of callables to retrieve parameters for the leaf nodes.
            If a single callable, its output should be a dictionary contain ``mean``,``cov`` as keys.
            The value for ``mean`` should be a list of floats, list of lists of floats, a one-dimensional NumPy array or a list of one-dimensional NumPy arrays
            containing the means of the distributions. If a list of floats or a one-dimensional NumPy array is given, it is broadcast to all nodes.
            The value for ``cov`` should be a list of lists of floats, a list of list of list of floats, a two-dimensional NumPy array or a list of two-dimensional NumPy arrays
            containing the symmetric positive semi-definite covariance matrices.  If a list of lists of floats or one-dimensional NumPy array is given, it is broadcast to all nodes.
            If ``cond_f`` is a list of callables, each one should return a dictionary containing ``mean``,``cov`` as keys.
            The value for ``mean`` should be a list of floating point values or one-dimensional NumPy array
            containing the means.
            The value for ``cov`` should be a list of lists of floating points or two-dimensional NumPy array
            containing a symmetric positive semi-definite covariance matrix.
        scopes_out:
            List of scopes representing the output scopes.
        nodes:
            List of ``CondMultivariateGaussian`` objects for the nodes in this layer.
    """

    def __init__(
        self,
        scope: Union[Scope, List[Scope]],
        cond_f: Optional[Union[Callable, List[Callable]]] = None,
        n_nodes: int = 1,
        **kwargs,
    ) -> None:
        r"""Initializes ``CondMultivariateGaussianLayer`` object.

        Args:
            scope:
                Scope or list of scopes specifying the scopes of the individual distribution.
                If a single scope is given, it is used for all nodes.
            cond_f:
                Optional callable or list of callables to retrieve parameters for the leaf nodes.
                If a single callable, its output should be a dictionary contain ``mean``,``cov`` as keys.
                The value for ``mean`` should be a list of floats, list of lists of floats, a one-dimensional NumPy array or a list of one-dimensional NumPy arrays
                containing the means of the distributions. If a list of floats or a one-dimensional NumPy array is given, it is broadcast to all nodes.
                The value for ``cov`` should be a list of lists of floats, a list of list of list of floats, a two-dimensional NumPy array or a list of two-dimensional NumPy arrays
                containing the symmetric positive semi-definite covariance matrices.  If a list of lists of floats or one-dimensional NumPy array is given, it is broadcast to all nodes.
                If ``cond_f`` is a list of callables, each one should return a dictionary containing ``mean``,``cov`` as keys.
                The value for ``mean`` should be a list of floating point values or one-dimensional NumPy array
                containing the means.
                The value for ``cov`` should be a list of lists of floating points or two-dimensional NumPy array
                containing a symmetric positive semi-definite covariance matrix.
            n_nodes:
                Integer specifying the number of nodes the layer should represent. Only relevant if a single scope is given.
                Defaults to 1.
        """
        if isinstance(scope, Scope):
            if n_nodes < 1:
                raise ValueError(
                    f"Number of nodes for 'CondMultivariateGaussianLayer' must be greater or equal to 1, but was {n_nodes}"
                )

            scope = [scope for _ in range(n_nodes)]
            self._n_out = n_nodes
        else:
            if len(scope) == 0:
                raise ValueError("List of scopes for 'CondMultivariateGaussianLayer' was empty.")

            self._n_out = len(scope)

        super().__init__(children=[], **kwargs)

        # create leaf nodes
        self.nodes = [CondMultivariateGaussian(s) for s in scope]

        # compute scope
        self.scopes_out = scope

        self.set_cond_f(cond_f)

    @property
    def n_out(self) -> int:
        """Returns the number of outputs for this module. Equal to the number of nodes represented by the layer."""
        return self._n_out

    @classmethod
    def accepts(cls, signatures: List[FeatureContext]) -> bool:
        """Checks if a specified signature can be represented by the module.

        ``CondMultivariateGaussianLayer`` can represent one or more multivariate nodes with ``MetaType.Continuous`` or ``GammaType`` domains.

        Returns:
            Boolean indicating whether the module can represent the specified signature (True) or not (False).
        """
        # leaf has at least one output
        if len(signatures) < 1:
            return False

        for signature in signatures:
            if not CondMultivariateGaussian.accepts([signature]):
                return False

        return True

    @classmethod
    def from_signatures(cls, signatures: List[FeatureContext]) -> "CondMultivariateGaussianLayer":
        """Creates an instance from a specified signature.

        Returns:
            ``CondMultivariateGaussianLayer`` instance.

        Raises:
            Signatures not accepted by the module.
        """
        if not cls.accepts(signatures):
            raise ValueError(
                f"'CondMultivariateGaussianLayer' cannot be instantiated from the following signatures: {signatures}."
            )

        scopes = []

        for feature_ctx in signatures:

            for domain in feature_ctx.get_domains():
                # read or initialize parameters
                if (
                    domain == MetaType.Continuous
                    or domain == FeatureTypes.Gaussian
                    or isinstance(domain, FeatureTypes.Gaussian)
                ):
                    pass
                else:
                    raise ValueError(
                        f"Unknown signature type {domain} for 'CondMultivariateGaussianLayer' that was not caught during acception checking."
                    )

            scopes.append(feature_ctx.scope)

        return CondMultivariateGaussianLayer(scopes)

    def set_cond_f(self, cond_f: Optional[Union[List[Callable], Callable]] = None) -> None:
        r"""Sets the ``cond_f`` property.

        Args:
            cond_f:
                Optional callable or list of callables to retrieve parameters for the leaf nodes.
                If a single callable, its output should be a dictionary contain ``mean``,``cov`` as keys.
                The value for ``mean`` should be a list of floats, list of lists of floats, a one-dimensional NumPy array or a list of one-dimensional NumPy arrays
                containing the means of the distributions. If a list of floats or a one-dimensional NumPy array is given, it is broadcast to all nodes.
                The value for ``cov`` should be a list of lists of floats, a list of list of list of floats, a two-dimensional NumPy array or a list of two-dimensional NumPy arrays
                containing the symmetric positive semi-definite covariance matrices.  If a list of lists of floats or one-dimensional NumPy array is given, it is broadcast to all nodes.
                If ``cond_f`` is a list of callables, each one should return a dictionary containing ``mean``,``cov`` as keys.
                The value for ``mean`` should be a list of floating point values or one-dimensional NumPy array
                containing the means.
                The value for ``cov`` should be a list of lists of floating points or two-dimensional NumPy array
                containing a symmetric positive semi-definite covariance matrix.

        Raises:
            ValueError: If list of callables does not match number of nodes represented by the layer.
        """
        if isinstance(cond_f, List) and len(cond_f) != self.n_out:
            raise ValueError(
                "'CondMultivariateGaussianLayer' received list of 'cond_f' functions, but length does not not match number of conditional nodes."
            )

        self.cond_f = cond_f

    def retrieve_params(
        self, data: np.ndarray, dispatch_ctx: DispatchContext
    ) -> Tuple[List[np.ndarray], List[np.ndarray]]:
        r"""Retrieves the conditional parameters of the leaf layer.

        First, checks if conditional parameters (``mean``,``cov``) are passed as additional arguments in the dispatch context.
        Secondly, checks if a function or list of functions (``cond_f``) is passed as an additional argument in the dispatch context to retrieve the conditional parameters.
        Lastly, checks if a ``cond_f`` is set as an attributed to retrieve the conditional parameter.

        Args:
            data:
                Two-dimensional NumPy array containing the data to compute the conditional parameters.
                Each row is regarded as a sample.
            dispatch_ctx:
                Dispatch context.

        Returns:
            Tuple of two lists of NumPy arrays.
            The first list contains one-dimensional NumPy arrays representing the means.
            The second list contains two-dimensional NumPy arrays representing the covariance matrices.

        Raises:
            ValueError: No way to retrieve conditional parameters or invalid conditional parameters.
        """
        mean, cov, cond_f = None, None, None

        # check dispatch cache for required conditional parameters 'mean','cov'
        if self in dispatch_ctx.args:
            args = dispatch_ctx.args[self]

            # check if value for 'mean','cov' specified (highest priority)
            if "mean" in args:
                mean = args["mean"]
            if "cov" in args:
                cov = args["cov"]
            # check if alternative function to provide 'mean','cov' is specified (second to highest priority)
            elif "cond_f" in args:
                cond_f = args["cond_f"]
        elif self.cond_f:
            # check if module has a 'cond_f' to provide 'mean','cov' specified (lowest priority)
            cond_f = self.cond_f

        # if neither 'mean' and 'cov' nor 'cond_f' is specified (via node or arguments)
        if (mean is None or cov is None) and cond_f is None:
            raise ValueError(
                "'CondMultivariateGaussianLayer' requires either 'mean' and 'cov' or 'cond_f' to retrieve 'mean','std' to be specified."
            )

        # if 'mean' or 'cov' was not already specified, retrieve it
        if mean is None or cov is None:
            # there is a different function for each conditional node
            if isinstance(cond_f, List):
                mean = []
                cov = []

                for f in cond_f:
                    args = f(data)
                    mean.append(args["mean"])
                    cov.append(args["cov"])

            else:
                args = cond_f(data)
                mean = args["mean"]
                cov = args["cov"]

        if isinstance(mean, list):
            # can be a list of values specifying a single mean (broadcast to all nodes)
            if all([isinstance(m, float) or isinstance(m, int) for m in mean]):
                mean = [np.array(mean) for _ in range(self.n_out)]
            # can also be a list of different means
            else:
                mean = [m if isinstance(m, np.ndarray) else np.array(m) for m in mean]
        elif isinstance(mean, np.ndarray):
            # can be a one-dimensional numpy array specifying single mean (broadcast to all nodes)
            if mean.ndim == 1:
                mean = [mean for _ in range(self.n_out)]
            # can also be an array of different means
            else:
                mean = [m for m in mean]
        else:
            raise ValueError(f"Specified 'mean' for 'CondMultivariateGaussianLayer' is of unknown type {type(mean)}.")

        if isinstance(cov, list):
            # can be a list of lists of values specifying a single cov (broadcast to all nodes)
            if all([all([isinstance(c, float) or isinstance(c, int) for c in l]) for l in cov]):
                cov = [np.array(cov) for _ in range(self.n_out)]
            # can also be a list of different covs
            else:
                cov = [c if isinstance(c, np.ndarray) else np.array(c) for c in cov]
        elif isinstance(cov, np.ndarray):
            # can be a two-dimensional numpy array specifying single cov (broadcast to all nodes)
            if cov.ndim == 2:
                cov = [cov for _ in range(self.n_out)]
            # can also be an array of different covs
            else:
                cov = [c for c in cov]
        else:
            raise ValueError(f"Specified 'cov' for 'CondMultivariateGaussianLayer' is of unknown type {type(cov)}.")

        if len(mean) != self.n_out:
            raise ValueError(
                f"Length of list of 'mean' values for 'CondMultivariateGaussianLayer' must match number of output nodes {self.n_out}, but is {len(mean)}"
            )
        if len(cov) != self.n_out:
            raise ValueError(
                f"Length of list of 'cov' values for 'CondMultivariateGaussianLayer' must match number of output nodes {self.n_out}, but is {len(cov)}"
            )

        for m, c, s in zip(mean, cov, self.scopes_out):
            if m.ndim != 1:
                raise ValueError(
                    f"All numpy arrays of 'mean' values for 'CondMultivariateGaussianLayer' are expected to be one-dimensional, but at least one is {m.ndim}-dimensional."
                )
            if m.shape[0] != len(s.query):
                raise ValueError(
                    f"Dimensions of a mean vector for 'CondMultivariateGaussianLayer' do not match corresponding scope size."
                )

            if c.ndim != 2:
                raise ValueError(
                    f"All numpy arrays of 'cov' values for 'CondMultivariateGaussianLayer' are expected to be two-dimensional, but at least one is {c.ndim}-dimensional."
                )
            if c.shape[0] != len(s.query) or c.shape[1] != len(s.query):
                raise ValueError(
                    f"Dimensions of a covariance matrix for 'CondMultivariateGaussianLayer' do not match corresponding scope size."
                )

        return mean, cov

    def dist(
        self,
        mean: List[np.ndarray],
        cov: List[np.ndarray],
        node_ids: Optional[List[int]] = None,
    ) -> List[rv_frozen]:
        r"""Returns the SciPy distributions represented by the leaf layer.

        Args:
            mean:
                List of one-dimensional NumPy array representing the means of all distributions (not just the ones specified by ``node_ids``).
            std:
                List of two-dimensional NumPy array representing the covariance matrices of all distributions (not just the ones specified by ``node_ids``).
            node_ids:
                Optional list of integers specifying the indices (and order) of the nodes' distribution to return.
                Defaults to None, in which case all nodes distributions selected.

        Returns:
            List of ``scipy.stats.distributions.rv_frozen`` distributions.
        """
        if node_ids is None:
            node_ids = list(range(self.n_out))

        return [self.nodes[i].dist(mean[i], cov[i]) for i in node_ids]

    def check_support(self, data: np.ndarray, node_ids: Optional[List[int]] = None) -> np.ndarray:
        r"""Checks if specified data is in support of the represented distributions.

        Determines whether or note instances are part of the supports of the Multivariate Gaussian distributions, which are:

        .. math::

            \text{supp}(\text{MultivariateGaussian})=(-\infty,+\infty)^k

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

        return np.concatenate([self.nodes[i].check_support(data) for i in node_ids], axis=1)


@dispatch(memoize=True)  # type: ignore
def marginalize(
    layer: CondMultivariateGaussianLayer,
    marg_rvs: Iterable[int],
    prune: bool = True,
    dispatch_ctx: Optional[DispatchContext] = None,
) -> Union[CondMultivariateGaussianLayer, CondMultivariateGaussian, CondGaussian, None]:
    r"""Structural marginalization for ``CondMultivariateGaussianLayer`` objects in the ``base`` backend.

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
    marg_nodes = []
    marg_scopes = []

    for node in layer.nodes:
        marg_node = marginalize(node, marg_rvs, prune=prune)

        if marg_node is not None:
            marg_scopes.append(marg_node.scope)
            marg_nodes.append(marg_node)

    if len(marg_scopes) == 0:
        return None
    elif len(marg_scopes) == 1 and prune:
        return marg_nodes.pop()
    else:
        new_layer = CondMultivariateGaussianLayer(marg_scopes)
        return new_layer

@dispatch(memoize=True)  # type: ignore
def updateBackend(leaf_node: CondMultivariateGaussianLayer, dispatch_ctx: Optional[DispatchContext] = None):
    """Conversion for ``SumNode`` from ``torch`` backend to ``base`` backend.

    Args:
        sum_node:
            Sum node to be converted.
        dispatch_ctx:
            Dispatch context.
    """
    dispatch_ctx = init_default_dispatch_context(dispatch_ctx)
    data = tl.tensor([])
    params = leaf_node.cond_f(data)

    for key in leaf_node.cond_f(params):
        # Update the value for each key
        params[key] = tl.tensor(params[key])
    cond_f = lambda data: params
    return GeneralCondMultivariateGaussianLayer(scope=leaf_node.scopes_out, cond_f=cond_f)
