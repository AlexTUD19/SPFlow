import random
import unittest

import numpy as np
import torch

from spflow.base.inference import log_likelihood
from spflow.base.structure.spn import MultivariateGaussian as BaseMultivariateGaussian
from spflow.meta.data import FeatureContext, FeatureTypes, Scope
from spflow.torch.inference import log_likelihood
from spflow.tensorly.structure.autoleaf import AutoLeaf
from spflow.torch.structure.spn import MultivariateGaussian as TorchMultivariateGaussian
from spflow.tensorly.structure.general.nodes.leaves.parametric.general_multivariate_gaussian import MultivariateGaussian
from spflow.torch.structure import marginalize, toBase, toTorch
from spflow.torch.structure.spn import Gaussian#, MultivariateGaussian


class TestMultivariateGaussian(unittest.TestCase):
    def test_initialization(self):

        # Valid parameters for Multivariate Gaussian distribution: mean vector in R^k, covariance matrix in R^(k x k) symmetric positive semi-definite

        # mean contains inf and mean contains nan
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([0, 1]),
            torch.tensor([0.0, float("inf")]),
            torch.eye(2),
        )
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([0, 1]),
            torch.tensor([-float("inf"), 0.0]),
            torch.eye(2),
        )
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([0, 1]),
            torch.tensor([0.0, float("nan")]),
            torch.eye(2),
        )

        # mean vector of wrong shape
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([0, 1]),
            torch.zeros(3),
            torch.eye(2),
        )
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([0, 1]),
            torch.zeros((1, 1, 2)),
            torch.eye(2),
        )

        # covariance matrix of wrong shape
        M = torch.tensor([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        self.assertRaises(Exception, MultivariateGaussian, Scope([0, 1]), torch.zeros(2), M)
        self.assertRaises(Exception, MultivariateGaussian, Scope([0, 1]), torch.zeros(2), M.T)
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([0, 1]),
            torch.zeros(2),
            np.eye(3),
        )
        # covariance matrix not symmetric positive semi-definite
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([0, 1]),
            torch.zeros(2),
            torch.tensor([[1.0, 0.0], [1.0, 0.0]]),
        )
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([0, 1]),
            torch.zeros(2),
            -torch.eye(2),
        )
        # covariance matrix containing inf or nan
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([0, 1]),
            torch.zeros(2),
            torch.tensor([[float("inf"), 0], [0, float("inf")]]),
        )
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([0, 1]),
            torch.zeros(2),
            torch.tensor([[float("nan"), 0], [0, float("nan")]]),
        )

        # duplicate scope variables
        self.assertRaises(
            Exception, Scope, [0, 0]
        )  # makes sure that MultivariateGaussian can also not be given a scope with duplicate query variables

        # invalid scopes
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([]),
            [0.0, 0.0],
            [[1.0, 0.0], [0.0, 1.0]],
        )
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([0, 1, 2]),
            [0.0, 0.0],
            [[1.0, 0.0], [0.0, 1.0]],
        )
        self.assertRaises(
            Exception,
            MultivariateGaussian,
            Scope([0, 1], [2]),
            [0.0, 0.0],
            [[1.0, 0.0], [0.0, 1.0]],
        )

        # initialize using lists
        MultivariateGaussian(Scope([0, 1]), [0.0, 0.0], [[1.0, 0.0], [0.0, 1.0]])

        # initialize using numpy arrays
        MultivariateGaussian(Scope([0, 1]), np.zeros(2), np.eye(2))

    def test_structural_marginalization(self):

        multivariate_gaussian = MultivariateGaussian(Scope([0, 1]), [0.0, 0.0], [[1.0, 0.0], [0.0, 1.0]])

        self.assertTrue(isinstance(marginalize(multivariate_gaussian, [2]), TorchMultivariateGaussian))
        self.assertTrue(isinstance(marginalize(multivariate_gaussian, [1]), Gaussian))
        self.assertTrue(marginalize(multivariate_gaussian, [0, 1]) is None)

    def test_accept(self):

        # continuous meta types
        self.assertTrue(
            MultivariateGaussian.accepts(
                [
                    FeatureContext(
                        Scope([0, 1]),
                        [FeatureTypes.Continuous, FeatureTypes.Continuous],
                    )
                ]
            )
        )

        # Gaussian feature type class
        self.assertTrue(
            MultivariateGaussian.accepts(
                [
                    FeatureContext(
                        Scope([0, 1]),
                        [FeatureTypes.Gaussian, FeatureTypes.Gaussian],
                    )
                ]
            )
        )

        # Gaussian feature type instance
        self.assertTrue(
            MultivariateGaussian.accepts(
                [
                    FeatureContext(
                        Scope([0, 1]),
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
            MultivariateGaussian.accepts(
                [
                    FeatureContext(
                        Scope([0, 1]),
                        [FeatureTypes.Continuous, FeatureTypes.Gaussian],
                    )
                ]
            )
        )

        # invalid feature type
        self.assertFalse(
            MultivariateGaussian.accepts(
                [
                    FeatureContext(
                        Scope([0, 1]),
                        [FeatureTypes.Discrete, FeatureTypes.Continuous],
                    )
                ]
            )
        )

        # conditional scope
        self.assertFalse(
            MultivariateGaussian.accepts(
                [
                    FeatureContext(
                        Scope([0, 1], [2]),
                        [FeatureTypes.Continuous, FeatureTypes.Continuous],
                    )
                ]
            )
        )

    def test_initialization_from_signatures(self):

        multivariate_gaussian = MultivariateGaussian.from_signatures(
            [
                FeatureContext(
                    Scope([0, 1]),
                    [FeatureTypes.Continuous, FeatureTypes.Continuous],
                )
            ]
        )
        self.assertTrue(torch.allclose(multivariate_gaussian.mean, torch.zeros(2)))
        self.assertTrue(torch.allclose(multivariate_gaussian.cov, torch.eye(2)))

        multivariate_gaussian = MultivariateGaussian.from_signatures(
            [
                FeatureContext(
                    Scope([0, 1]),
                    [FeatureTypes.Gaussian, FeatureTypes.Gaussian],
                )
            ]
        )
        self.assertTrue(torch.allclose(multivariate_gaussian.mean, torch.zeros(2)))
        self.assertTrue(torch.allclose(multivariate_gaussian.cov, torch.eye(2)))

        multivariate_gaussian = MultivariateGaussian.from_signatures(
            [
                FeatureContext(
                    Scope([0, 1]),
                    [
                        FeatureTypes.Gaussian(-1.0, 1.5),
                        FeatureTypes.Gaussian(1.0, 0.5),
                    ],
                )
            ]
        )
        self.assertTrue(torch.allclose(multivariate_gaussian.mean, torch.tensor([-1.0, 1.0])))
        self.assertTrue(
            torch.allclose(
                multivariate_gaussian.cov,
                torch.tensor([[1.5, 0.0], [0.0, 0.5]]),
            )
        )

        # ----- invalid arguments -----

        # invalid feature type
        self.assertRaises(
            ValueError,
            MultivariateGaussian.from_signatures,
            [
                FeatureContext(
                    Scope([0, 1]),
                    [FeatureTypes.Discrete, FeatureTypes.Continuous],
                )
            ],
        )

        # conditional scope
        self.assertRaises(
            ValueError,
            MultivariateGaussian.from_signatures,
            [
                FeatureContext(
                    Scope([0, 1], [2]),
                    [FeatureTypes.Continuous, FeatureTypes.Continuous],
                )
            ],
        )

    def test_autoleaf(self):

        # make sure leaf is registered
        self.assertTrue(AutoLeaf.is_registered(MultivariateGaussian))

        # make sure leaf is correctly inferred
        self.assertEqual(
            MultivariateGaussian,
            AutoLeaf.infer(
                [
                    FeatureContext(
                        Scope([0, 1]),
                        [FeatureTypes.Gaussian, FeatureTypes.Gaussian],
                    )
                ]
            ),
        )

        # make sure AutoLeaf can return correctly instantiated object
        multivariate_gaussian = AutoLeaf(
            [
                FeatureContext(
                    Scope([0, 1]),
                    [
                        FeatureTypes.Gaussian(mean=-1.0, std=1.5),
                        FeatureTypes.Gaussian(mean=1.0, std=0.5),
                    ],
                )
            ]
        )
        self.assertTrue(isinstance(multivariate_gaussian, TorchMultivariateGaussian))
        self.assertTrue(torch.allclose(multivariate_gaussian.mean, torch.tensor([-1.0, 1.0])))
        self.assertTrue(
            torch.allclose(
                multivariate_gaussian.cov,
                torch.tensor([[1.5, 0.0], [0.0, 0.5]]),
            )
        )

    def test_base_backend_conversion(self):

        mean = np.arange(3)
        cov = np.array([[2, 2, 1], [2, 3, 2], [1, 2, 3]])

        torch_multivariate_gaussian = MultivariateGaussian(Scope([0, 1, 2]), mean, cov)
        node_multivariate_gaussian = BaseMultivariateGaussian(Scope([0, 1, 2]), mean.tolist(), cov.tolist())

        node_params = node_multivariate_gaussian.get_params()
        torch_params = torch_multivariate_gaussian.get_params()

        # check conversion from torch to python
        torch_to_node_params = toBase(torch_multivariate_gaussian).get_params()

        self.assertTrue(
            np.allclose(
                np.array([torch_params[0]]),
                np.array([torch_to_node_params[0]]),
            )
        )
        self.assertTrue(
            np.allclose(
                np.array([torch_params[1]]),
                np.array([torch_to_node_params[1]]),
            )
        )
        # check conversion from python to torch#
        node_to_torch_params = toTorch(node_multivariate_gaussian).get_params()

        self.assertTrue(
            np.allclose(
                np.array([node_params[0]]),
                np.array([node_to_torch_params[0]]),
            )
        )
        self.assertTrue(
            np.allclose(
                np.array([node_params[1]]),
                np.array([node_to_torch_params[1]]),
            )
        )


if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
