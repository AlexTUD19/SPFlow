from spflow.meta.data.scope import Scope
from spflow.meta.dispatch.dispatch_context import DispatchContext
from spflow.torch.structure.spn.nodes.sum_node import SPNSumNode
from spflow.torch.structure.spn.nodes.product_node import SPNProductNode
from spflow.torch.inference.spn.nodes.sum_node import log_likelihood
from spflow.torch.inference.spn.nodes.product_node import log_likelihood
from spflow.torch.learning.spn.nodes.sum_node import em
from spflow.torch.learning.spn.nodes.product_node import em
from spflow.torch.structure.layers.leaves.parametric.uniform import UniformLayer
from spflow.torch.learning.layers.leaves.parametric.uniform import (
    maximum_likelihood_estimation,
    em,
)
from spflow.torch.inference.layers.leaves.parametric.uniform import (
    log_likelihood,
)
from spflow.torch.learning.expectation_maximization.expectation_maximization import (
    expectation_maximization,
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

    def test_mle(self):

        layer = UniformLayer(
            scope=[Scope([0]), Scope([1])], start=[0.0, -5.0], end=[1.0, -2.0]
        )

        # simulate data
        data = torch.tensor([[0.5, -3.0]])

        # perform MLE (should not raise an exception)
        maximum_likelihood_estimation(layer, data, bias_correction=True)

        self.assertTrue(torch.all(layer.start == torch.tensor([0.0, -5.0])))
        self.assertTrue(torch.all(layer.end == torch.tensor([1.0, -2.0])))

    def test_mle_invalid_support(self):

        layer = UniformLayer(
            Scope([0]), start=1.0, end=3.0, support_outside=False
        )

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
            torch.tensor([[0.0]]),
            bias_correction=True,
        )

    def test_em_step(self):

        # set seed
        torch.manual_seed(0)

        leaf = UniformLayer(
            [Scope([0]), Scope([1])], start=[-1.0, 2.0], end=[3.0, 5.0]
        )
        data = torch.tensor(
            np.hstack(
                [
                    np.random.rand(15000, 1) * 4.0 - 1.0,
                    np.random.rand(15000, 1) * 3.0 + 2.0,
                ]
            )
        )
        dispatch_ctx = DispatchContext()

        # compute gradients of log-likelihoods w.r.t. module log-likelihoods
        ll = log_likelihood(leaf, data, dispatch_ctx=dispatch_ctx)
        ll.requires_grad = True
        ll.retain_grad()
        ll.sum().backward()

        # perform an em step
        em(leaf, data, dispatch_ctx=dispatch_ctx)

        self.assertTrue(torch.all(leaf.start == torch.tensor([-1.0, 2.0])))
        self.assertTrue(torch.all(leaf.end == torch.tensor([3.0, 5.0])))

    def test_em_product_of_uniforms(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        layer = UniformLayer(
            [Scope([0]), Scope([1])], start=[-1.0, 2.0], end=[3.0, 5.0]
        )
        prod_node = SPNProductNode([layer])

        data = torch.tensor(
            np.hstack(
                [
                    np.random.rand(15000, 1) * 4.0 - 1.0,
                    np.random.rand(15000, 1) * 3.0 + 2.0,
                ]
            )
        )

        expectation_maximization(prod_node, data, max_steps=10)

        self.assertTrue(torch.all(layer.start == torch.tensor([-1.0, 2.0])))
        self.assertTrue(torch.all(layer.end == torch.tensor([3.0, 5.0])))

    def test_em_sum_of_uniforms(self):

        # set seed
        torch.manual_seed(0)
        np.random.seed(0)
        random.seed(0)

        layer = UniformLayer(Scope([0]), n_nodes=2, start=-1.0, end=3.0)
        sum_node = SPNSumNode([layer], weights=[0.5, 0.5])

        data = torch.tensor(np.random.rand(15000, 1) * 3.0 + 2.0)

        expectation_maximization(sum_node, data, max_steps=10)

        self.assertTrue(torch.all(layer.start == torch.tensor([-1.0, -1.0])))
        self.assertTrue(torch.all(layer.end == torch.tensor([3.0, 3.0])))


if __name__ == "__main__":
    unittest.main()
