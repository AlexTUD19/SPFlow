from spflow.meta.data import Scope
from spflow.meta.dispatch import DispatchContext
from spflow.torch.structure.spn import SumNode, ProductNode, Gaussian
from spflow.torch.inference import log_likelihood
from spflow.torch.learning import (
    em,
    expectation_maximization,
    maximum_likelihood_estimation,
)

import torch
import numpy as np
import random
import unittest


class TestNode(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        torch.set_default_dtype(torch.float64)

    @classmethod
    def teardown_class(cls):
        torch.set_default_dtype(torch.float32)

    def test_mle_1(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        leaf = Gaussian(Scope([0]))

        # simulate data
        data = np.random.normal(loc=-1.7, scale=0.2, size=(10000, 1))

        # perform MLE
        maximum_likelihood_estimation(
            leaf, torch.tensor(data), bias_correction=True
        )

        self.assertTrue(
            torch.isclose(leaf.mean, torch.tensor(-1.7), atol=1e-2, rtol=1e-2)
        )
        self.assertTrue(
            torch.isclose(leaf.std, torch.tensor(0.2), atol=1e-2, rtol=1e-2)
        )

    def test_mle_2(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        leaf = Gaussian(Scope([0]))

        # simulate data
        data = np.random.normal(loc=0.5, scale=1.3, size=(30000, 1))

        # perform MLE
        maximum_likelihood_estimation(
            leaf, torch.tensor(data), bias_correction=True
        )

        self.assertTrue(
            torch.isclose(leaf.mean, torch.tensor(0.5), atol=1e-2, rtol=1e-2)
        )
        self.assertTrue(
            torch.isclose(leaf.std, torch.tensor(1.3), atol=1e-2, rtol=1e-2)
        )

    def test_mle_bias_correction(self):

        leaf = Gaussian(Scope([0]))
        data = torch.tensor([[-1.0], [1.0]])

        # perform MLE
        maximum_likelihood_estimation(leaf, data, bias_correction=False)
        self.assertTrue(torch.isclose(leaf.std, torch.sqrt(torch.tensor(1.0))))

        # perform MLE
        maximum_likelihood_estimation(leaf, data, bias_correction=True)
        self.assertTrue(torch.isclose(leaf.std, torch.sqrt(torch.tensor(2.0))))

    def test_mle_edge_std_0(self):

        leaf = Gaussian(Scope([0]))

        # simulate data
        data = torch.randn(1, 1)

        # perform MLE
        maximum_likelihood_estimation(leaf, data, bias_correction=False)

        self.assertTrue(torch.isclose(leaf.mean, data[0]))
        self.assertTrue(leaf.std > 0)

    def test_mle_edge_std_nan(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        leaf = Gaussian(Scope([0]))

        # simulate data
        data = torch.randn(1, 1)

        # perform MLE (Torch does not throw a warning here different to NumPy)
        maximum_likelihood_estimation(leaf, data, bias_correction=True)

        self.assertTrue(torch.isclose(leaf.mean, data[0]))
        self.assertFalse(torch.isnan(leaf.std))
        self.assertTrue(leaf.std > 0)

    def test_mle_only_nans(self):

        leaf = Gaussian(Scope([0]))

        # simulate data
        data = torch.tensor([[float("nan")], [float("nan")]])

        # check if exception is raised
        self.assertRaises(
            ValueError,
            maximum_likelihood_estimation,
            leaf,
            data,
            nan_strategy="ignore",
        )

    def test_mle_invalid_support(self):

        leaf = Gaussian(Scope([0]))

        # perform MLE (should raise exceptions)
        self.assertRaises(
            ValueError,
            maximum_likelihood_estimation,
            leaf,
            torch.tensor([[float("inf")]]),
            bias_correction=True,
        )

    def test_mle_nan_strategy_none(self):

        leaf = Gaussian(Scope([0]))
        self.assertRaises(
            ValueError,
            maximum_likelihood_estimation,
            leaf,
            torch.tensor([[float("nan")], [0.1], [-1.8], [0.7]]),
            nan_strategy=None,
        )

    def test_mle_nan_strategy_ignore(self):

        leaf = Gaussian(Scope([0]))
        maximum_likelihood_estimation(
            leaf,
            torch.tensor([[float("nan")], [0.1], [-1.8], [0.7]]),
            nan_strategy="ignore",
            bias_correction=False,
        )
        self.assertTrue(torch.isclose(leaf.mean, torch.tensor(-1.0 / 3.0)))
        self.assertTrue(
            torch.isclose(
                leaf.std,
                torch.sqrt(
                    1
                    / 3
                    * torch.sum(
                        (torch.tensor([[0.1], [-1.8], [0.7]]) + 1.0 / 3.0) ** 2
                    )
                ),
            )
        )

    def test_mle_nan_strategy_callable(self):

        leaf = Gaussian(Scope([0]))
        # should not raise an issue
        maximum_likelihood_estimation(
            leaf, torch.tensor([[0.5], [1]]), nan_strategy=lambda x: x
        )

    def test_mle_nan_strategy_invalid(self):

        leaf = Gaussian(Scope([0]))
        self.assertRaises(
            ValueError,
            maximum_likelihood_estimation,
            leaf,
            torch.tensor([[float("nan")], [0.1], [1.9], [0.7]]),
            nan_strategy="invalid_string",
        )
        self.assertRaises(
            ValueError,
            maximum_likelihood_estimation,
            leaf,
            torch.tensor([[float("nan")], [1], [0], [1]]),
            nan_strategy=1,
        )

    def test_weighted_mle(self):

        leaf = Gaussian(Scope([0]))

        data = torch.tensor(
            np.vstack(
                [
                    np.random.normal(1.7, 0.8, size=(10000, 1)),
                    np.random.normal(0.5, 1.4, size=(10000, 1)),
                ]
            )
        )
        weights = torch.concat([torch.zeros(10000), torch.ones(10000)])

        maximum_likelihood_estimation(leaf, data, weights)

        self.assertTrue(
            torch.isclose(leaf.mean, torch.tensor(0.5), atol=1e-2, rtol=1e-1)
        )
        self.assertTrue(
            torch.isclose(leaf.std, torch.tensor(1.4), atol=1e-2, rtol=1e-2)
        )

    def test_em_step(self):

        # since this is the root module here, all gradients (i.e., expectations) should be 1, and thus result in regular MLE

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        leaf = Gaussian(Scope([0]))
        data = torch.tensor(
            np.random.normal(loc=-1.7, scale=0.2, size=(10000, 1))
        )
        dispatch_ctx = DispatchContext()

        # compute gradients of log-likelihoods w.r.t. module log-likelihoods
        ll = log_likelihood(leaf, data, dispatch_ctx=dispatch_ctx)
        ll.retain_grad()
        ll.sum().backward()

        # perform an em step
        em(leaf, data, dispatch_ctx=dispatch_ctx)

        self.assertTrue(
            torch.isclose(leaf.mean, torch.tensor(-1.7), atol=1e-2, rtol=1e-3)
        )
        self.assertTrue(
            torch.isclose(leaf.std, torch.tensor(0.2), atol=1e-2, rtol=1e-3)
        )

    def test_em_product_of_gaussians(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        l1 = Gaussian(Scope([0]), mean=1.5, std=0.75)
        l2 = Gaussian(Scope([1]), mean=-2.5, std=1.5)
        prod_node = ProductNode([l1, l2])

        data = torch.tensor(
            np.hstack(
                [
                    np.random.normal(2.0, 1.0, size=(20000, 1)),
                    np.random.normal(-2.0, 1.0, size=(20000, 1)),
                ]
            )
        )

        expectation_maximization(prod_node, data, max_steps=10)

        self.assertTrue(
            torch.isclose(l1.mean, torch.tensor(2.0), atol=1e-3, rtol=1e-2)
        )
        self.assertTrue(
            torch.isclose(l1.std, torch.tensor(1.0), atol=1e-2, rtol=1e-2)
        )
        self.assertTrue(
            torch.isclose(l2.mean, torch.tensor(-2.0), atol=1e-3, rtol=1e-2)
        )
        self.assertTrue(
            torch.isclose(l2.std, torch.tensor(1.0), atol=1e-2, rtol=1e-2)
        )

    def test_em_mixture_of_gaussians(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        l1 = Gaussian(Scope([0]), mean=1.5, std=0.75)
        l2 = Gaussian(Scope([0]), mean=-2.5, std=1.5)
        sum_node = SumNode([l1, l2], weights=[0.5, 0.5])

        data = torch.tensor(
            np.vstack(
                [
                    np.random.normal(2.0, 1.0, size=(20000, 1)),
                    np.random.normal(-2.0, 1.0, size=(20000, 1)),
                ]
            )
        )

        expectation_maximization(sum_node, data, max_steps=10)

        self.assertTrue(
            torch.isclose(l1.mean, torch.tensor(2.0), atol=1e-3, rtol=1e-3)
        )
        self.assertTrue(
            torch.isclose(l1.std, torch.tensor(1.0), atol=1e-2, rtol=1e-2)
        )
        self.assertTrue(
            torch.isclose(l2.mean, torch.tensor(-2.0), atol=1e-3, rtol=1e-3)
        )
        self.assertTrue(
            torch.isclose(l2.std, torch.tensor(1.0), atol=1e-2, rtol=1e-2)
        )
        self.assertTrue(
            torch.allclose(
                sum_node.weights, torch.tensor([0.5, 0.5]), atol=1e-3, rtol=1e-2
            )
        )


if __name__ == "__main__":
    unittest.main()