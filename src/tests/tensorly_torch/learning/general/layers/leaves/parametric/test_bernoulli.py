import random
import unittest

import numpy as np
import pytest
import torch
import tensorly as tl

from spflow.meta.data import Scope
from spflow.meta.dispatch import DispatchContext
from spflow.tensorly.inference import log_likelihood
from spflow.torch.learning import (
    em,
    expectation_maximization,
    maximum_likelihood_estimation,
)
from spflow.tensorly.learning import maximum_likelihood_estimation
from spflow.torch.structure.spn import BernoulliLayer#, ProductNode, SumNode
from spflow.tensorly.structure.spn import ProductNode, SumNode
from spflow.tensorly.utils.helper_functions import tl_toNumpy
from spflow.torch.structure.general.layers.leaves.parametric.bernoulli import updateBackend


class TestNode(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        torch.set_default_dtype(torch.float64)

    @classmethod
    def teardown_class(cls):
        torch.set_default_dtype(torch.float32)

    def test_mle(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        layer = BernoulliLayer(scope=[Scope([0]), Scope([1])])

        # simulate data
        data = np.hstack(
            [
                np.random.binomial(n=1, p=0.3, size=(10000, 1)),
                np.random.binomial(n=1, p=0.7, size=(10000, 1)),
            ]
        )

        # perform MLE
        maximum_likelihood_estimation(layer, torch.tensor(data))

        self.assertTrue(torch.allclose(layer.p, torch.tensor([0.3, 0.7]), atol=1e-2, rtol=1e-3))

    def test_mle_edge_0(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        layer = BernoulliLayer(Scope([0]), n_nodes=1)

        # simulate data
        data = np.random.binomial(n=1, p=0.0, size=(100, 1))

        # perform MLE
        maximum_likelihood_estimation(layer, torch.tensor(data))

        self.assertTrue(torch.all(layer.p > 0.0))

    def test_mle_edge_1(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        layer = BernoulliLayer(Scope([0]), n_nodes=1)

        # simulate data
        data = np.random.binomial(n=1, p=1.0, size=(100, 1))

        # perform MLE
        maximum_likelihood_estimation(layer, torch.tensor(data))

        self.assertTrue(torch.all(layer.p < 1.0))

    def test_mle_only_nans(self):

        layer = BernoulliLayer(scope=[Scope([0]), Scope([1])], n_nodes=1)

        # simulate data
        data = torch.tensor([[float("nan"), float("nan")], [float("nan"), 1.0]])

        # check if exception is raised
        self.assertRaises(
            ValueError,
            maximum_likelihood_estimation,
            layer,
            data,
            nan_strategy="ignore",
            bias_correction=False,
        )

    def test_mle_invalid_support(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        layer = BernoulliLayer(Scope([0]))

        # perform MLE (should raise exceptions)
        self.assertRaises(
            ValueError,
            maximum_likelihood_estimation,
            layer,
            torch.tensor([[float("inf")]]),
            bias_correction=True,
        )
        self.assertRaises(
            ValueError,
            maximum_likelihood_estimation,
            layer,
            torch.tensor([[-0.1]]),
            bias_correction=True,
        )
        self.assertRaises(
            ValueError,
            maximum_likelihood_estimation,
            layer,
            torch.tensor([[2]]),
            bias_correction=True,
        )

    def test_mle_nan_strategy_none(self):

        layer = BernoulliLayer(Scope([0]))
        self.assertRaises(
            ValueError,
            maximum_likelihood_estimation,
            layer,
            torch.tensor([[float("nan")], [1], [0], [1]]),
            nan_strategy=None,
        )

    def test_mle_nan_strategy_ignore(self):

        layer = BernoulliLayer(Scope([0]))
        maximum_likelihood_estimation(
            layer,
            torch.tensor([[float("nan")], [1], [0], [1]]),
            nan_strategy="ignore",
        )
        self.assertTrue(torch.allclose(layer.p, torch.tensor(2.0 / 3.0)))

    def test_mle_nan_strategy_callable(self):

        layer = BernoulliLayer(Scope([0]))
        # should not raise an issue
        maximum_likelihood_estimation(layer, torch.tensor([[1], [0], [1]]), nan_strategy=lambda x: x)

    def test_mle_nan_strategy_invalid(self):

        layer = BernoulliLayer(Scope([0]))
        self.assertRaises(
            ValueError,
            maximum_likelihood_estimation,
            layer,
            torch.tensor([[float("nan")], [1], [0], [1]]),
            nan_strategy="invalid_string",
        )
        self.assertRaises(
            ValueError,
            maximum_likelihood_estimation,
            layer,
            torch.tensor([[float("nan")], [1], [0], [1]]),
            nan_strategy=1,
        )

    def test_weighted_mle(self):

        leaf = BernoulliLayer([Scope([0]), Scope([1])], n_nodes=3)

        data = torch.tensor(
            np.hstack(
                [
                    np.vstack(
                        [
                            np.random.binomial(n=1, p=0.8, size=(10000, 1)),
                            np.random.binomial(n=1, p=0.2, size=(10000, 1)),
                        ]
                    ),
                    np.vstack(
                        [
                            np.random.binomial(n=1, p=0.3, size=(10000, 1)),
                            np.random.binomial(n=1, p=0.7, size=(10000, 1)),
                        ]
                    ),
                ]
            )
        )

        weights = torch.concat([torch.zeros(10000), torch.ones(10000)])

        maximum_likelihood_estimation(leaf, data, weights)

        self.assertTrue(torch.allclose(leaf.p, torch.tensor([0.2, 0.7]), atol=1e-3, rtol=1e-2))

    def test_em_step(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        layer = BernoulliLayer([Scope([0]), Scope([1])])
        data = torch.tensor(
            np.hstack(
                [
                    np.random.binomial(n=1, p=0.2, size=(10000, 1)),
                    np.random.binomial(n=1, p=0.7, size=(10000, 1)),
                ]
            )
        )
        dispatch_ctx = DispatchContext()

        # compute gradients of log-likelihoods w.r.t. module log-likelihoods
        ll = log_likelihood(layer, data, dispatch_ctx=dispatch_ctx)
        ll.retain_grad()
        ll.sum().backward()

        # perform an em step
        em(layer, data, dispatch_ctx=dispatch_ctx)

        self.assertTrue(torch.allclose(layer.p, torch.tensor([0.2, 0.7]), atol=1e-2, rtol=1e-3))

    def test_em_product_of_bernoullis(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        layer = BernoulliLayer([Scope([0]), Scope([1])])
        prod_node = ProductNode([layer])

        data = torch.tensor(
            np.hstack(
                [
                    np.random.binomial(n=1, p=0.8, size=(10000, 1)),
                    np.random.binomial(n=1, p=0.2, size=(10000, 1)),
                ]
            )
        )

        expectation_maximization(prod_node, data, max_steps=10)

        self.assertTrue(torch.allclose(layer.p, torch.tensor([0.8, 0.2]), atol=1e-3, rtol=1e-2))

    def test_em_sum_of_bernoullis(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        leaf = BernoulliLayer(Scope([0]), n_nodes=2, p=[0.4, 0.6])
        sum_node = SumNode([leaf], weights=[0.5, 0.5])

        data = torch.tensor(
            np.vstack(
                [
                    np.random.binomial(n=1, p=0.8, size=(1000, 1)),
                    np.random.binomial(n=1, p=0.3, size=(1000, 1)),
                ]
            )
        )

        expectation_maximization(sum_node, data, max_steps=10)

        # optimal p
        p_opt = data.sum(dim=0) / data.shape[0]
        # total p represented by mixture
        p_em = (sum_node.weights * leaf.p).sum()

        self.assertTrue(torch.allclose(p_opt, p_em))

    def test_update_backend(self):
        backends = ["numpy", "pytorch"]
        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        layer = BernoulliLayer(scope=[Scope([0]), Scope([1])])

        # simulate data
        data = np.hstack(
            [
                np.random.binomial(n=1, p=0.3, size=(10000, 1)),
                np.random.binomial(n=1, p=0.7, size=(10000, 1)),
            ]
        )

        # perform MLE
        maximum_likelihood_estimation(layer, tl.tensor(data))

        params = tl_toNumpy(layer.p)

        layer = BernoulliLayer(scope=[Scope([0]), Scope([1])])
        prod_node = ProductNode([layer])
        expectation_maximization(prod_node, tl.tensor(data), max_steps=10)
        params_em = tl_toNumpy(layer.p)


        # make sure that probabilities match python backend probabilities
        for backend in backends:
            tl.set_backend(backend)
            layer = BernoulliLayer(scope=[Scope([0]), Scope([1])])
            layer_updated = updateBackend(layer)
            maximum_likelihood_estimation(layer_updated, tl.tensor(data))
            # check conversion from torch to python
            self.assertTrue(np.allclose(tl_toNumpy(layer_updated.p), params, atol=1e-2, rtol=1e-3))

            layer = BernoulliLayer(scope=[Scope([0]), Scope([1])])
            layer_updated = updateBackend(layer)
            prod_node = ProductNode([layer_updated])
            if tl.get_backend() != "pytorch":
                with pytest.raises(NotImplementedError):
                    expectation_maximization(prod_node, tl.tensor(data), max_steps=10)
            else:
                expectation_maximization(prod_node, tl.tensor(data), max_steps=10)
                self.assertTrue(np.allclose(tl_toNumpy(layer_updated.p), params_em, atol=1e-3, rtol=1e-2))


if __name__ == "__main__":
    unittest.main()
