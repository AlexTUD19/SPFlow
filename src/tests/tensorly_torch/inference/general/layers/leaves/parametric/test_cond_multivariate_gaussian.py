import random
import unittest

import torch
import tensorly as tl
import numpy as np

from spflow.meta.data import Scope
from spflow.meta.dispatch import DispatchContext
from spflow.torch.inference import likelihood, log_likelihood
from spflow.tensorly.structure.general.layers.leaves.parametric.general_cond_multivariate_gaussian import CondMultivariateGaussianLayer
from spflow.tensorly.structure.general.nodes.leaves.parametric.general_cond_multivariate_gaussian import CondMultivariateGaussian
from spflow.torch.structure.general.layers.leaves.parametric.cond_multivariate_gaussian import updateBackend
from spflow.tensorly.utils.helper_functions import tl_toNumpy


class TestNode(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        torch.set_default_dtype(torch.float64)

    @classmethod
    def teardown_class(cls):
        torch.set_default_dtype(torch.float32)

    def test_likelihood_no_mean(self):

        multivariate_gaussian = CondMultivariateGaussianLayer(
            Scope([0, 1], [2]),
            cond_f=lambda data: {"cov": [[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]]]},
            n_nodes=2,
        )
        self.assertRaises(
            KeyError,
            log_likelihood,
            multivariate_gaussian,
            torch.tensor([[0], [1]]),
        )

    def test_likelihood_no_cov(self):

        multivariate_gaussian = CondMultivariateGaussianLayer(
            Scope([0, 1], [2]),
            cond_f=lambda data: {"mean": [[0.0, 0.0], [0.0, 0.0]]},
            n_nodes=2,
        )
        self.assertRaises(
            KeyError,
            log_likelihood,
            multivariate_gaussian,
            torch.tensor([[0], [1]]),
        )

    def test_likelihood_no_mean_cov(self):

        multivariate_gaussian = CondMultivariateGaussianLayer(Scope([0], [1]), n_nodes=2)
        self.assertRaises(
            ValueError,
            log_likelihood,
            multivariate_gaussian,
            torch.tensor([[0], [1]]),
        )

    def test_likelihood_module_cond_f(self):

        cond_f = lambda data: {
            "mean": [[0.0, 0.0], [0.0, 0.0]],
            "cov": [[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]]],
        }

        multivariate_gaussian = CondMultivariateGaussianLayer(Scope([0, 1], [2]), n_nodes=2, cond_f=cond_f)

        # create test inputs/outputs
        data = torch.stack([torch.zeros(2), torch.ones(2)], axis=0)
        targets = torch.tensor([[0.1591549, 0.1591549], [0.0585498, 0.0585498]])

        probs = likelihood(multivariate_gaussian, data)
        log_probs = log_likelihood(multivariate_gaussian, data)

        self.assertTrue(torch.allclose(probs, torch.exp(log_probs)))
        self.assertTrue(torch.allclose(probs, targets))

    def test_likelihood_args(self):

        multivariate_gaussian = CondMultivariateGaussianLayer(Scope([0, 1], [2]), n_nodes=2)

        dispatch_ctx = DispatchContext()
        dispatch_ctx.args[multivariate_gaussian] = {
            "mean": [[0.0, 0.0], [0.0, 0.0]],
            "cov": [[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]]],
        }

        # create test inputs/outputs
        data = torch.stack([torch.zeros(2), torch.ones(2)], axis=0)
        targets = torch.tensor([[0.1591549, 0.1591549], [0.0585498, 0.0585498]])

        probs = likelihood(multivariate_gaussian, data, dispatch_ctx=dispatch_ctx)
        log_probs = log_likelihood(multivariate_gaussian, data, dispatch_ctx=dispatch_ctx)

        self.assertTrue(torch.allclose(probs, torch.exp(log_probs)))
        self.assertTrue(torch.allclose(probs, targets))

    def test_likelihood_args_cond_f(self):

        multivariate_gaussian = CondMultivariateGaussianLayer(Scope([0, 1], [2]), n_nodes=2)

        cond_f = lambda data: {
            "mean": [[0.0, 0.0], [0.0, 0.0]],
            "cov": [[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]]],
        }

        dispatch_ctx = DispatchContext()
        dispatch_ctx.args[multivariate_gaussian] = {"cond_f": cond_f}

        # create test inputs/outputs
        data = torch.stack([torch.zeros(2), torch.ones(2)], axis=0)
        targets = torch.tensor([[0.1591549, 0.1591549], [0.0585498, 0.0585498]])

        probs = likelihood(multivariate_gaussian, data, dispatch_ctx=dispatch_ctx)
        log_probs = log_likelihood(multivariate_gaussian, data, dispatch_ctx=dispatch_ctx)

        self.assertTrue(torch.allclose(probs, torch.exp(log_probs)))
        self.assertTrue(torch.allclose(probs, targets))

    def test_layer_likelihood(self):

        mean_values = [
            torch.zeros(2),
            torch.arange(3, dtype=torch.get_default_dtype()),
        ]
        cov_values = [
            torch.eye(2),
            torch.tensor(
                [
                    [2, 2, 1],
                    [2, 3, 2],
                    [1, 2, 3],
                ],
                dtype=torch.get_default_dtype(),
            ),
        ]

        layer = CondMultivariateGaussianLayer(
            scope=[Scope([0, 1], [5]), Scope([2, 3, 4], [5])],
            cond_f=lambda data: {"mean": mean_values, "cov": cov_values},
        )

        nodes = [
            CondMultivariateGaussian(
                Scope([0, 1], [5]),
                cond_f=lambda data: {
                    "mean": mean_values[0],
                    "cov": cov_values[0],
                },
            ),
            CondMultivariateGaussian(
                Scope([2, 3, 4], [5]),
                cond_f=lambda data: {
                    "mean": mean_values[1],
                    "cov": cov_values[1],
                },
            ),
        ]

        dummy_data = torch.vstack([torch.zeros(5), torch.ones(5)])

        layer_ll = log_likelihood(layer, dummy_data)
        nodes_ll = torch.concat([log_likelihood(node, dummy_data) for node in nodes], dim=1)

        self.assertTrue(torch.allclose(layer_ll, nodes_ll))

    def test_gradient_computation(self):

        mean = [
            torch.zeros(2, dtype=torch.get_default_dtype(), requires_grad=True),
            torch.arange(3, dtype=torch.get_default_dtype(), requires_grad=True),
        ]
        cov = [
            torch.eye(2, requires_grad=True),
            torch.tensor(
                [[2, 2, 1], [2, 3, 2], [1, 2, 3]],
                dtype=torch.get_default_dtype(),
                requires_grad=True,
            ),
        ]

        torch_multivariate_gaussian = CondMultivariateGaussianLayer(
            scope=[Scope([0, 1], [5]), Scope([2, 3, 4], [5])],
            cond_f=lambda data: {"mean": mean, "cov": cov},
        )

        # create dummy input data (batch size x random variables)
        data = torch.randn(3, 5)

        log_probs_torch = log_likelihood(torch_multivariate_gaussian, data)

        # create dummy targets
        targets_torch = torch.ones(3, 2)

        loss = torch.nn.MSELoss()(log_probs_torch, targets_torch)
        loss.backward()

        self.assertTrue(all([m.grad is not None for m in mean]))
        self.assertTrue(all([c.grad is not None for c in cov]))

    def test_likelihood_marginalization(self):

        gaussian = CondMultivariateGaussianLayer(
            scope=[Scope([0, 1], [3]), Scope([1, 2], [3])],
            cond_f=lambda data: {
                "mean": torch.zeros(2, 2),
                "cov": torch.stack([torch.eye(2), torch.eye(2)]),
            },
        )
        data = torch.tensor([[float("nan"), float("nan"), float("nan")]])

        # should not raise and error and should return 1
        probs = log_likelihood(gaussian, data).exp()

        self.assertTrue(torch.allclose(probs, torch.tensor([1.0, 1.0])))

    def test_support(self):
        # TODO
        pass

    def test_update_backend(self):
        backends = ["numpy", "pytorch"]
        cond_f = lambda data: {
            "mean": [[0.0, 0.0], [0.0, 0.0]],
            "cov": [[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]]],
        }

        multivariate_gaussian = CondMultivariateGaussianLayer(Scope([0, 1], [2]), n_nodes=2, cond_f=cond_f)

        # create test inputs/outputs
        data = torch.stack([torch.zeros(2), torch.ones(2)], axis=0)
        log_probs = log_likelihood(multivariate_gaussian, data)

        # make sure that probabilities match python backend probabilities
        for backend in backends:
            tl.set_backend(backend)
            layer_updated = updateBackend(multivariate_gaussian)
            log_probs_updated = log_likelihood(layer_updated, tl.tensor(data))
            # check conversion from torch to python
            self.assertTrue(np.allclose(tl_toNumpy(log_probs), tl_toNumpy(log_probs_updated)))


if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
