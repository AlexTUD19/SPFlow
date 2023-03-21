import unittest
from typing import Callable

import tensorly as tl

from spflow.tensorly.structure.autoleaf import AutoLeaf
from spflow.tensorly.structure.general.nodes.leaves.parametric.cond_gaussian import (
    CondGaussian,
)
from spflow.tensorly.structure.general.nodes.leaves.parametric.cond_multivariate_gaussian import (
    CondMultivariateGaussian,
)
from spflow.tensorly.structure.spn.nodes.product_node import marginalize
from spflow.meta.data import Scope
from spflow.meta.data.feature_context import FeatureContext
from spflow.meta.data.feature_types import FeatureTypes
from spflow.meta.dispatch.dispatch_context import DispatchContext


class TestMultivariateGaussian(unittest.TestCase):
    def test_initialization(self):

        multivariate_gaussian = CondMultivariateGaussian(Scope([0, 1], [2]))
        self.assertTrue(multivariate_gaussian.cond_f is None)
        multivariate_gaussian = CondMultivariateGaussian(
            Scope([0], [1]),
            cond_f=lambda x: {"mean": tl.tensor([0.0, 0.0]), "cov": tl.eye(2)},
        )
        self.assertTrue(isinstance(multivariate_gaussian.cond_f, Callable))

        # invalid scopes
        self.assertRaises(Exception, CondMultivariateGaussian, Scope([]))
        self.assertRaises(Exception, CondMultivariateGaussian, Scope([0, 1]))

    def test_retrieve_params(self):

        # Valid parameters for Multivariate Gaussian distribution: mean vector in R^k, covariance matrix in R^(k x k) symmetric positive semi-definite

        multivariate_gaussian = CondMultivariateGaussian(Scope([0, 1], [2]))

        # mean contains inf and mean contains nan
        multivariate_gaussian.set_cond_f(lambda data: {"mean": tl.tensor([0.0, tl.inf]), "cov": tl.eye(2)})
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )
        multivariate_gaussian.set_cond_f(lambda data: {"mean": tl.tensor([-tl.inf, 0.0]), "cov": tl.eye(2)})
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )
        multivariate_gaussian.set_cond_f(lambda data: {"mean": tl.tensor([0.0, tl.nan]), "cov": tl.eye(2)})
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )

        # mean vector of wrong shape
        multivariate_gaussian.set_cond_f(lambda data: {"mean": tl.zeros(3), "cov": tl.eye(2)})
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )
        multivariate_gaussian.set_cond_f(lambda data: {"mean": tl.zeros((1, 1, 2)), "cov": tl.eye(2)})
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )
        multivariate_gaussian.set_cond_f(lambda data: {"mean": tl.tensor([0.0, tl.nan]), "cov": tl.eye(2)})
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )
        # covariance matrix of wrong shape
        M = tl.tensor([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        multivariate_gaussian.set_cond_f(lambda data: {"mean": tl.zeros(2), "cov": M})
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )
        multivariate_gaussian.set_cond_f(lambda data: {"mean": tl.zeros(2), "cov": tl.transpose(M)})
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )
        multivariate_gaussian.set_cond_f(lambda data: {"mean": tl.zeros(2), "cov": tl.eye(3)})
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )
        # covariance matrix not symmetric positive semi-definite
        multivariate_gaussian.set_cond_f(lambda data: {"mean": tl.zeros(2), "cov": -tl.eye(2)})
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )
        multivariate_gaussian.set_cond_f(
            lambda data: {
                "mean": tl.zeros(2),
                "cov": tl.tensor([[1.0, 0.0], [1.0, 0.0]]),
            }
        )
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )
        # covariance matrix containing inf or nan
        multivariate_gaussian.set_cond_f(
            lambda data: {
                "mean": tl.zeros(2),
                "cov": tl.tensor([[tl.inf, 0], [0, tl.inf]]),
            }
        )
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )
        multivariate_gaussian.set_cond_f(
            lambda data: {
                "mean": tl.zeros(2),
                "cov": tl.tensor([[tl.nan, 0], [0, tl.nan]]),
            }
        )
        self.assertRaises(
            ValueError,
            multivariate_gaussian.retrieve_params,
            tl.tensor([[1.0, 1.0]]),
            DispatchContext(),
        )

    def test_accept(self):

        # continuous meta types
        self.assertTrue(
            CondMultivariateGaussian.accepts(
                [
                    FeatureContext(
                        Scope([0, 1], [2]),
                        [FeatureTypes.Continuous, FeatureTypes.Continuous],
                    )
                ]
            )
        )

        # Gaussian feature type class
        self.assertTrue(
            CondMultivariateGaussian.accepts(
                [
                    FeatureContext(
                        Scope([0, 1], [2]),
                        [FeatureTypes.Gaussian, FeatureTypes.Gaussian],
                    )
                ]
            )
        )

        # Gaussian feature type instance
        self.assertTrue(
            CondMultivariateGaussian.accepts(
                [
                    FeatureContext(
                        Scope([0, 1], [2]),
                        [
                            FeatureTypes.Gaussian(0.0, 1.0),
                            FeatureTypes.Gaussian(0.0, 1.0),
                        ],
                    )
                ]
            )
        )

        # continuous meta and Gaussian feature types
        self.assertTrue(
            CondMultivariateGaussian.accepts(
                [
                    FeatureContext(
                        Scope([0, 1], [2]),
                        [FeatureTypes.Continuous, FeatureTypes.Gaussian],
                    )
                ]
            )
        )

        # invalid feature type
        self.assertFalse(
            CondMultivariateGaussian.accepts(
                [
                    FeatureContext(
                        Scope([0, 1], [2]),
                        [FeatureTypes.Discrete, FeatureTypes.Continuous],
                    )
                ]
            )
        )

        # non-conditional scope
        self.assertFalse(
            CondMultivariateGaussian.accepts(
                [
                    FeatureContext(
                        Scope([0, 1]),
                        [FeatureTypes.Continuous, FeatureTypes.Continuous],
                    )
                ]
            )
        )

    def test_initialization_from_signatures(self):

        CondMultivariateGaussian.from_signatures(
            [
                FeatureContext(
                    Scope([0, 1], [2]),
                    [FeatureTypes.Continuous, FeatureTypes.Continuous],
                )
            ]
        )
        CondMultivariateGaussian.from_signatures(
            [
                FeatureContext(
                    Scope([0, 1], [2]),
                    [FeatureTypes.Gaussian, FeatureTypes.Gaussian],
                )
            ]
        )
        CondMultivariateGaussian.from_signatures(
            [
                FeatureContext(
                    Scope([0, 1], [2]),
                    [
                        FeatureTypes.Gaussian(-1.0, 1.5),
                        FeatureTypes.Gaussian(1.0, 0.5),
                    ],
                )
            ]
        )

        # ----- invalid arguments -----

        # invalid feature type
        self.assertRaises(
            ValueError,
            CondMultivariateGaussian.from_signatures,
            [
                FeatureContext(
                    Scope([0, 1], [2]),
                    [FeatureTypes.Discrete, FeatureTypes.Continuous],
                )
            ],
        )

        # non-conditional scope
        self.assertRaises(
            ValueError,
            CondMultivariateGaussian.from_signatures,
            [
                FeatureContext(
                    Scope([0, 1]),
                    [FeatureTypes.Continuous, FeatureTypes.Continuous],
                )
            ],
        )

    def test_autoleaf(self):

        # make sure leaf is registered
        self.assertTrue(AutoLeaf.is_registered(CondMultivariateGaussian))

        # make sure leaf is correctly inferred
        self.assertEqual(
            CondMultivariateGaussian,
            AutoLeaf.infer(
                [
                    FeatureContext(
                        Scope([0, 1], [2]),
                        [FeatureTypes.Gaussian, FeatureTypes.Gaussian],
                    )
                ]
            ),
        )

        # make sure AutoLeaf can return correctly instantiated object
        multivariate_gaussian = AutoLeaf(
            [
                FeatureContext(
                    Scope([0, 1], [2]),
                    [
                        FeatureTypes.Gaussian(mean=-1.0, std=1.5),
                        FeatureTypes.Gaussian(mean=1.0, std=0.5),
                    ],
                )
            ]
        )
        self.assertTrue(isinstance(multivariate_gaussian, CondMultivariateGaussian))

    def test_structural_marginalization(self):

        multivariate_gaussian = CondMultivariateGaussian(Scope([0, 1], [3]))

        self.assertTrue(
            isinstance(
                marginalize(multivariate_gaussian, [2]),
                CondMultivariateGaussian,
            )
        )
        self.assertTrue(isinstance(marginalize(multivariate_gaussian, [1]), CondGaussian))
        self.assertTrue(marginalize(multivariate_gaussian, [0, 1]) is None)


if __name__ == "__main__":
    unittest.main()
