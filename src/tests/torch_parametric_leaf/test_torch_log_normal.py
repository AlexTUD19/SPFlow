from spflow.base.structure.nodes.leaves.parametric import LogNormal
from spflow.base.inference import log_likelihood
from spflow.torch.structure.nodes.leaves.parametric import TorchLogNormal, toNodes, toTorch
from spflow.torch.inference import log_likelihood, likelihood

from spflow.base.structure.network_type import SPN

import torch
import numpy as np

import random
import unittest


class TestTorchLogNormal(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        torch.set_default_dtype(torch.float64)

    @classmethod
    def teardown_class(cls):
        torch.set_default_dtype(torch.float32)

    def test_inference(self):

        mean = random.random()
        stdev = random.random() + 1e-7  # offset by small number to avoid zero

        torch_log_normal = TorchLogNormal([0], mean, stdev)
        node_log_normal = LogNormal([0], mean, stdev)

        # create dummy input data (batch size x random variables)
        data = np.random.rand(3, 1)

        log_probs = log_likelihood(node_log_normal, data, SPN())
        log_probs_torch = log_likelihood(torch_log_normal, torch.tensor(data))

        # make sure that probabilities match python backend probabilities
        self.assertTrue(np.allclose(log_probs, log_probs_torch.detach().cpu().numpy()))

    def test_gradient_computation(self):

        mean = random.random()
        stdev = random.random() + 1e-7  # offset by small number to avoid zero

        torch_log_normal = TorchLogNormal([0], mean, stdev)

        # create dummy input data (batch size x random variables)
        data = np.random.rand(3, 1)

        log_probs_torch = log_likelihood(torch_log_normal, torch.tensor(data))

        # create dummy targets
        targets_torch = torch.ones(3, 1)

        loss = torch.nn.MSELoss()(log_probs_torch, targets_torch)
        loss.backward()

        self.assertTrue(torch_log_normal.mean.grad is not None)
        self.assertTrue(torch_log_normal.stdev_aux.grad is not None)

        mean_orig = torch_log_normal.mean.detach().clone()
        stdev_aux_orig = torch_log_normal.stdev_aux.detach().clone()

        optimizer = torch.optim.SGD(torch_log_normal.parameters(), lr=1)
        optimizer.step()

        # make sure that parameters are correctly updated
        self.assertTrue(
            torch.allclose(mean_orig - torch_log_normal.mean.grad, torch_log_normal.mean)
        )
        self.assertTrue(
            torch.allclose(
                stdev_aux_orig - torch_log_normal.stdev_aux.grad, torch_log_normal.stdev_aux
            )
        )

        # verify that distribution parameters match parameters
        self.assertTrue(torch.allclose(torch_log_normal.mean, torch_log_normal.dist.loc))
        self.assertTrue(torch.allclose(torch_log_normal.stdev, torch_log_normal.dist.scale))

    def test_gradient_optimization(self):

        # initialize distribution
        torch_log_normal = TorchLogNormal([0], mean=1.0, stdev=2.0)

        torch.manual_seed(0)

        # create dummy data
        data = torch.distributions.LogNormal(0.0, 1.0).sample((100000, 1))

        # initialize gradient optimizer
        optimizer = torch.optim.SGD(torch_log_normal.parameters(), lr=0.5, momentum=0.5)

        # perform optimization (possibly overfitting)
        for i in range(20):

            # clear gradients
            optimizer.zero_grad()

            # compute negative log-likelihood
            nll = -log_likelihood(torch_log_normal, data).mean()
            nll.backward()

            # update parameters
            optimizer.step()

        self.assertTrue(
            torch.allclose(torch_log_normal.mean, torch.tensor(0.0), atol=1e-3, rtol=0.3)
        )
        self.assertTrue(
            torch.allclose(torch_log_normal.stdev, torch.tensor(1.0), atol=1e-3, rtol=0.3)
        )

    def test_base_backend_conversion(self):

        mean = random.random()
        stdev = random.random() + 1e-7  # offset by small number to avoid zero

        torch_log_normal = TorchLogNormal([0], mean, stdev)
        node_log_normal = LogNormal([0], mean, stdev)

        # check conversion from torch to python
        self.assertTrue(
            np.allclose(
                np.array([*torch_log_normal.get_params()]),
                np.array([*toNodes(torch_log_normal).get_params()]),
            )
        )
        # check conversion from python to torch
        self.assertTrue(
            np.allclose(
                np.array([*node_log_normal.get_params()]),
                np.array([*toTorch(node_log_normal).get_params()]),
            )
        )

    def test_initialization(self):

        # Valid parameters for Log-Normal distribution: mean in R (TODO: (-inf,inf)?), std>0

        # mean = inf and mean = 0
        self.assertRaises(Exception, TorchLogNormal, [0], np.inf, 1.0)
        self.assertRaises(Exception, TorchLogNormal, [0], np.nan, 1.0)

        mean = random.random()

        # stdev <= 0
        self.assertRaises(Exception, TorchLogNormal, [0], mean, 0.0)
        self.assertRaises(Exception, TorchLogNormal, [0], mean, np.nextafter(0.0, -1.0))
        # stdev = inf and stdev = nan
        self.assertRaises(Exception, TorchLogNormal, [0], mean, np.inf)
        self.assertRaises(Exception, TorchLogNormal, [0], mean, np.nan)

        # invalid scope lengths
        self.assertRaises(Exception, TorchLogNormal, [], 0.0, 1.0)
        self.assertRaises(Exception, TorchLogNormal, [0,1], 0.0, 1.0)

    def test_support(self):

        # Support for Log-Normal distribution: (0,inf) (TODO: 0,inf?)

        # TODO:
        #   outside support -> 0 (or error?)

        log_normal = TorchLogNormal([0], 0.0, 1.0)

        # edge cases (-inf,inf) and 0.0
        data = torch.tensor([[-float("inf")], [0.0], [float("inf")]])
        targets = torch.zeros((3,1))

        probs = likelihood(log_normal, data)
        log_probs = log_likelihood(log_normal, data)

        self.assertTrue(torch.allclose(probs, targets))
        self.assertTrue(torch.allclose(probs, torch.exp(log_probs)))


if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
