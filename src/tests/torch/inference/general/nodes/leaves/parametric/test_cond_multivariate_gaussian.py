import math
import unittest

import numpy as np
import torch

from spflow.base.inference import log_likelihood
from spflow.base.structure.spn import (
    CondMultivariateGaussian as BaseCondMultivariateGaussian,
)
from spflow.meta.data import Scope
from spflow.meta.dispatch import DispatchContext
from spflow.torch.inference import likelihood, log_likelihood
from spflow.torch.structure.spn import (
    CondGaussian,
    CondMultivariateGaussian,
    ProductNode,
)


class TestMultivariateGaussian(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        torch.set_default_dtype(torch.float64)

    @classmethod
    def teardown_class(cls):
        torch.set_default_dtype(torch.float32)

    def test_likelihood_module_cond_f(self):

        cond_f = lambda data: {"mean": torch.zeros(2), "cov": torch.eye(2)}

        multivariate_gaussian = CondMultivariateGaussian(
            Scope([0, 1], [2]), cond_f=cond_f
        )

        # create test inputs/outputs
        data = torch.tensor(np.stack([np.zeros(2), np.ones(2)], axis=0))
        targets = torch.tensor([[0.1591549], [0.0585498]])

        probs = likelihood(multivariate_gaussian, data)
        log_probs = log_likelihood(multivariate_gaussian, data)

        self.assertTrue(torch.allclose(probs, torch.exp(log_probs)))
        self.assertTrue(torch.allclose(probs, targets))

    def test_likelihood_args_p(self):

        multivariate_gaussian = CondMultivariateGaussian(Scope([0, 1], [2]))

        dispatch_ctx = DispatchContext()
        dispatch_ctx.args[multivariate_gaussian] = {
            "mean": torch.zeros(2),
            "cov": torch.eye(2),
        }

        # create test inputs/outputs
        data = torch.tensor(np.stack([np.zeros(2), np.ones(2)], axis=0))
        targets = torch.tensor([[0.1591549], [0.0585498]])

        probs = likelihood(
            multivariate_gaussian, data, dispatch_ctx=dispatch_ctx
        )
        log_probs = log_likelihood(
            multivariate_gaussian, data, dispatch_ctx=dispatch_ctx
        )

        self.assertTrue(torch.allclose(probs, torch.exp(log_probs)))
        self.assertTrue(torch.allclose(probs, targets))

    def test_likelihood_args_cond_f(self):

        multivariate_gaussian = CondMultivariateGaussian(Scope([0, 1], [2]))

        cond_f = lambda data: {"mean": torch.zeros(2), "cov": torch.eye(2)}

        dispatch_ctx = DispatchContext()
        dispatch_ctx.args[multivariate_gaussian] = {"cond_f": cond_f}

        # create test inputs/outputs
        data = torch.tensor(np.stack([np.zeros(2), np.ones(2)], axis=0))
        targets = torch.tensor([[0.1591549], [0.0585498]])

        probs = likelihood(
            multivariate_gaussian, data, dispatch_ctx=dispatch_ctx
        )
        log_probs = log_likelihood(
            multivariate_gaussian, data, dispatch_ctx=dispatch_ctx
        )

        self.assertTrue(torch.allclose(probs, torch.exp(log_probs)))
        self.assertTrue(torch.allclose(probs, targets))

    def test_inference(self):

        mean = np.arange(3)
        cov = np.array([[2, 2, 1], [2, 3, 2], [1, 2, 3]])

        torch_multivariate_gaussian = CondMultivariateGaussian(
            Scope([0, 1, 2], [3]),
            cond_f=lambda data: {"mean": mean, "cov": cov},
        )
        node_multivariate_gaussian = BaseCondMultivariateGaussian(
            Scope([0, 1, 2], [3]),
            cond_f=lambda data: {"mean": mean, "cov": cov},
        )

        # create dummy input data (batch size x random variables)
        data = np.random.rand(3, 3)

        log_probs = log_likelihood(node_multivariate_gaussian, data)
        log_probs_torch = log_likelihood(
            torch_multivariate_gaussian, torch.tensor(data)
        )

        # make sure that probabilities match python backend probabilities
        self.assertTrue(
            np.allclose(log_probs, log_probs_torch.detach().cpu().numpy())
        )

    def test_gradient_computation(self):

        mean = torch.tensor(
            np.arange(3), dtype=torch.get_default_dtype(), requires_grad=True
        )
        cov = torch.tensor(
            [[2.0, 2.0, 1.0], [2.0, 3.0, 2.0], [1.0, 2.0, 3.0]],
            requires_grad=True,
        )

        torch_multivariate_gaussian = CondMultivariateGaussian(
            Scope([0, 1, 2], [3]),
            cond_f=lambda data: {"mean": mean, "cov": cov},
        )

        # create dummy input data (batch size x random variables)
        data = np.random.rand(3, 3)

        log_probs_torch = log_likelihood(
            torch_multivariate_gaussian, torch.tensor(data)
        )

        # create dummy targets
        targets_torch = torch.ones(3, 1)

        loss = torch.nn.MSELoss()(log_probs_torch, targets_torch)
        loss.backward()

        self.assertTrue(mean.grad is not None)
        self.assertTrue(cov.grad is not None)

    def test_likelihood_marginalization(self):

        # ----- full marginalization -----

        multivariate_gaussian = CondMultivariateGaussian(
            Scope([0, 1], [2]),
            cond_f=lambda data: {
                "mean": torch.zeros(2),
                "cov": torch.tensor([[2.0, 0.0], [0.0, 1.0]]),
            },
        )
        data = torch.tensor([[float("nan"), float("nan")]])

        # should not raise an error and should return 1
        probs = likelihood(multivariate_gaussian, data)

        self.assertTrue(torch.allclose(probs, torch.tensor(1.0)))

        # ----- partial marginalization -----

        data = torch.tensor([[0.0, float("nan")], [float("nan"), 0.0]])
        targets = torch.tensor([[0.282095], [0.398942]])

        # inference using multivariate gaussian and partial marginalization
        mv_probs = likelihood(multivariate_gaussian, data)

        self.assertTrue(torch.allclose(mv_probs, targets))

        # inference using univariate gaussians for each random variable (combined via product node for convenience)
        univariate_gaussians = ProductNode(
            children=[
                CondGaussian(
                    Scope([0], [2]),
                    cond_f=lambda data: {"mean": 0.0, "std": math.sqrt(2.0)},
                ),  # requires standard deviation instead of variance
                CondGaussian(
                    Scope([1], [2]),
                    cond_f=lambda data: {"mean": 0.0, "std": 1.0},
                ),
            ],
        )

        uv_probs = likelihood(univariate_gaussians, data)

        # compare
        self.assertTrue(torch.allclose(mv_probs, uv_probs))

        # higher-dimensional example
        multivariate_gaussian = CondMultivariateGaussian(
            Scope([0, 1, 2, 3], [4]),
            cond_f=lambda data: {
                "mean": torch.zeros(4),
                "cov": torch.tensor(
                    [
                        [2.0, 0.5, 0.5, 0.25],
                        [0.5, 1.0, 0.75, 0.5],
                        [0.5, 0.75, 1.5, 0.5],
                        [0.25, 0.5, 0.5, 1.25],
                    ]
                ),
            },
        )

        data = torch.tensor(
            [
                [0.0] * 4,
                [0.0, float("nan"), float("nan"), 0.0],
                [float("nan"), 0.0, 0.0, 0.0],
                [float("nan")] * 4,
            ]
        )
        targets = torch.tensor(
            [[0.02004004], [0.10194075], [0.06612934], [1.0]]
        )

        # inference using multivariate gaussian and partial marginalization
        mv_probs = likelihood(multivariate_gaussian, data)

        self.assertTrue(torch.allclose(mv_probs, targets, atol=1e-6))

    def test_support(self):

        # Support for Multivariate Gaussian distribution: floats (inf,+inf)^k

        multivariate_gaussian = CondMultivariateGaussian(
            Scope([0, 1], [2]),
            cond_f=lambda data: {"mean": np.zeros(2), "cov": np.eye(2)},
        )

        # check infinite values
        self.assertRaises(
            ValueError,
            log_likelihood,
            multivariate_gaussian,
            torch.tensor([[-float("inf"), 0.0]]),
        )
        self.assertRaises(
            ValueError,
            log_likelihood,
            multivariate_gaussian,
            torch.tensor([[0.0, float("inf")]]),
        )


if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
