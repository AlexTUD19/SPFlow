from spflow.base.structure.nodes.leaves.parametric import NegativeBinomial
from spflow.base.inference import log_likelihood
from spflow.torch.structure.nodes.leaves.parametric import TorchNegativeBinomial, toNodes, toTorch
from spflow.torch.inference import log_likelihood, likelihood

from spflow.base.structure.network_type import SPN

import torch
import numpy as np

import random
import unittest


class TestTorchNegativeBinomial(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        torch.set_default_dtype(torch.float64)

    @classmethod
    def teardown_class(cls):
        torch.set_default_dtype(torch.float32)

    def test_inference(self):

        n = random.randint(2, 10)
        p = random.random()

        torch_negative_binomial = TorchNegativeBinomial([0], n, p)
        node_negative_binomial = NegativeBinomial([0], n, p)

        # create dummy input data (batch size x random variables)
        data = np.random.randint(1, n, (3, 1))

        log_probs = log_likelihood(node_negative_binomial, data, SPN())
        log_probs_torch = log_likelihood(torch_negative_binomial, torch.tensor(data))

        # make sure that probabilities match python backend probabilities
        self.assertTrue(np.allclose(log_probs, log_probs_torch.detach().cpu().numpy()))

    def test_gradient_computation(self):

        n = random.randint(2, 10)
        p = random.random()

        torch_negative_binomial = TorchNegativeBinomial([0], n, p)

        # create dummy input data (batch size x random variables)
        data = np.random.randint(1, n, (3, 1))

        log_probs_torch = log_likelihood(torch_negative_binomial, torch.tensor(data))

        # create dummy targets
        targets_torch = torch.ones(3, 1)

        loss = torch.nn.MSELoss()(log_probs_torch, targets_torch)
        loss.backward()

        self.assertTrue(torch_negative_binomial.n.grad is None)
        self.assertTrue(torch_negative_binomial.p_aux.grad is not None)

        n_orig = torch_negative_binomial.n.detach().clone()
        p_aux_orig = torch_negative_binomial.p_aux.detach().clone()

        optimizer = torch.optim.SGD(torch_negative_binomial.parameters(), lr=1)
        optimizer.step()

        # make sure that parameters are correctly updated
        self.assertTrue(torch.allclose(n_orig, torch_negative_binomial.n))
        self.assertTrue(
            torch.allclose(
                p_aux_orig - torch_negative_binomial.p_aux.grad, torch_negative_binomial.p_aux
            )
        )

    def test_gradient_optimization(self):

        torch.manual_seed(0)

        # initialize distribution
        torch_negative_binomial = TorchNegativeBinomial([0], 5, 0.3)

        # create dummy data
        p_target = 0.8
        data = torch.distributions.NegativeBinomial(5, 1 - p_target).sample((100000, 1))

        # initialize gradient optimizer
        optimizer = torch.optim.SGD(torch_negative_binomial.parameters(), lr=0.5)

        # perform optimization (possibly overfitting)
        for i in range(40):

            # clear gradients
            optimizer.zero_grad()

            # compute negative log-likelihood
            nll = -log_likelihood(torch_negative_binomial, data).mean()
            nll.backward()

            # update parameters
            optimizer.step()

        self.assertTrue(
            torch.allclose(torch_negative_binomial.p, torch.tensor(p_target), atol=1e-3, rtol=1e-3)
        )

    def test_base_backend_conversion(self):

        n = random.randint(2, 10)
        p = random.random()

        torch_negative_binomial = TorchNegativeBinomial([0], n, p)
        node_negative_binomial = NegativeBinomial([0], n, p)

        # check conversion from torch to python
        self.assertTrue(
            np.allclose(
                np.array([*torch_negative_binomial.get_params()]),
                np.array([*toNodes(torch_negative_binomial).get_params()]),
            )
        )
        # check conversion from python to torch
        self.assertTrue(
            np.allclose(
                np.array([*node_negative_binomial.get_params()]),
                np.array([*toTorch(node_negative_binomial).get_params()]),
            )
        )

    def test_initialization(self):

        # Valid parameters for Negative Binomial distribution: p in [0,1], n > 0

        # p = 1
        negative_binomial = TorchNegativeBinomial([0], 1, 1.0)

        data = torch.tensor([[0.0], [1.0]])
        targets = torch.tensor([[1.0], [0.0]])

        probs = likelihood(negative_binomial, data)
        log_probs = log_likelihood(negative_binomial, data)

        self.assertTrue(torch.allclose(probs, torch.exp(log_probs)))
        self.assertTrue(torch.allclose(probs, targets))

        # p = 0
        TorchNegativeBinomial([0], 1, 0.0)

        data = torch.tensor([[0.0], [1.0]])
        targets = torch.tensor([[1.0], [0.0]])

        probs = likelihood(negative_binomial, data)
        log_probs = log_likelihood(negative_binomial, data)

        self.assertTrue(torch.allclose(probs, torch.exp(log_probs)))
        self.assertTrue(torch.allclose(probs, targets))

        # p < 0 and p > 1
        self.assertRaises(
            Exception,
            TorchNegativeBinomial,
            [0],
            1,
            torch.nextafter(torch.tensor(1.0), torch.tensor(2.0)),
        )
        self.assertRaises(
            Exception,
            TorchNegativeBinomial,
            [0],
            1,
            torch.nextafter(torch.tensor(0.0), torch.tensor(-1.0)),
        )

        # p = +-inf and p = nan
        self.assertRaises(Exception, TorchNegativeBinomial, [0], 1, np.inf)
        self.assertRaises(Exception, TorchNegativeBinomial, [0], 1, -np.inf)
        self.assertRaises(Exception, TorchNegativeBinomial, [0], 1, np.nan)

        # n = 0
        TorchNegativeBinomial([0], 0.0, 1.0)

        # n < 0
        self.assertRaises(
            Exception,
            TorchNegativeBinomial,
            [0],
            torch.nextafter(torch.tensor(0.0), torch.tensor(-1.0)),
            1.0,
        )

        # n = inf and n = nan
        self.assertRaises(Exception, TorchNegativeBinomial, [0], np.inf, 1.0)
        self.assertRaises(Exception, TorchNegativeBinomial, [0], np.nan, 1.0)

        # TODO: n float
        self.assertRaises(Exception, likelihood, negative_binomial, 0.5, SPN())

        # invalid scope lengths
        self.assertRaises(Exception, TorchNegativeBinomial, [], 1, 1.0)
        self.assertRaises(Exception, TorchNegativeBinomial, [0, 1], 1, 1.0)

    def test_support(self):

        # Support for Negative Binomial distribution: integers N U {0}

        n = 20
        p = 0.3

        negative_binomial = TorchNegativeBinomial([0], n, p)

        # check infinite values
        self.assertRaises(
            ValueError, log_likelihood, negative_binomial, torch.tensor([[-float("inf")]])
        )
        self.assertRaises(
            ValueError, log_likelihood, negative_binomial, torch.tensor([[float("inf")]])
        )

        # check valid integers, but outside of valid range
        self.assertRaises(ValueError, log_likelihood, negative_binomial, torch.tensor([[-1]]))

        # check valid integers within valid range
        log_likelihood(negative_binomial, torch.tensor([[0]]))
        log_likelihood(negative_binomial, torch.tensor([[100]]))

        # check invalid float values
        self.assertRaises(
            ValueError,
            log_likelihood,
            negative_binomial,
            torch.tensor([[torch.nextafter(torch.tensor(0.0), torch.tensor(-1.0))]]),
        )
        self.assertRaises(
            ValueError,
            log_likelihood,
            negative_binomial,
            torch.tensor([[torch.nextafter(torch.tensor(0.0), torch.tensor(1.0))]]),
        )
        self.assertRaises(ValueError, log_likelihood, negative_binomial, torch.tensor([[10.1]]))

    def test_marginalization(self):

        negative_binomial = TorchNegativeBinomial([0], 20, 0.3)
        data = torch.tensor([[float("nan")]])

        # should not raise and error and should return 1
        probs = likelihood(negative_binomial, data)

        self.assertTrue(torch.allclose(probs, torch.tensor(1.0)))


if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
