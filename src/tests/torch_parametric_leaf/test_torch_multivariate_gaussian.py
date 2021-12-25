from spflow.base.structure.nodes.leaves.parametric import MultivariateGaussian
from spflow.base.inference import log_likelihood
from spflow.torch.structure.nodes.leaves.parametric import (
    TorchMultivariateGaussian,
    toNodes,
    toTorch,
)
from spflow.torch.inference import log_likelihood, likelihood

from spflow.base.structure.network_type import SPN

import torch
import numpy as np

import unittest


class TestTorchMultivariateGaussian(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        torch.set_default_dtype(torch.float64)

    @classmethod
    def teardown_class(cls):
        torch.set_default_dtype(torch.float32)

    def test_inference(self):

        mean_vector = np.arange(3)
        covariance_matrix = np.array([[2, 2, 1], [2, 3, 2], [1, 2, 3]])

        torch_multivariate_gaussian = TorchMultivariateGaussian(
            [0, 1, 2], mean_vector, covariance_matrix
        )
        node_multivariate_gaussian = MultivariateGaussian(
            [0, 1, 2], mean_vector.tolist(), covariance_matrix.tolist()
        )

        # create dummy input data (batch size x random variables)
        data = np.random.rand(3, 3)

        log_probs = log_likelihood(node_multivariate_gaussian, data, SPN())
        log_probs_torch = log_likelihood(torch_multivariate_gaussian, torch.tensor(data))

        # make sure that probabilities match python backend probabilities
        self.assertTrue(np.allclose(log_probs, log_probs_torch.detach().cpu().numpy()))

    def test_gradient_computation(self):

        mean_vector = np.arange(3)
        covariance_matrix = np.array([[2, 2, 1], [2, 3, 2], [1, 2, 3]])

        torch_multivariate_gaussian = TorchMultivariateGaussian(
            [0, 1, 2], mean_vector, covariance_matrix
        )

        # create dummy input data (batch size x random variables)
        data = np.random.rand(3, 3)

        log_probs_torch = log_likelihood(torch_multivariate_gaussian, torch.tensor(data))

        # create dummy targets
        targets_torch = torch.ones(3, 1)

        loss = torch.nn.MSELoss()(log_probs_torch, targets_torch)
        loss.backward()

        self.assertTrue(torch_multivariate_gaussian.mean_vector.grad is not None)
        self.assertTrue(torch_multivariate_gaussian.tril_diag_aux.grad is not None)
        self.assertTrue(torch_multivariate_gaussian.tril_nondiag.grad is not None)

        mean_vector_orig = torch_multivariate_gaussian.mean_vector.detach().clone()
        tril_diag_aux_orig = torch_multivariate_gaussian.tril_diag_aux.detach().clone()
        tril_nondiag_orig = torch_multivariate_gaussian.tril_nondiag.detach().clone()

        optimizer = torch.optim.SGD(torch_multivariate_gaussian.parameters(), lr=1)
        optimizer.step()

        # make sure that parameters are correctly updated
        self.assertTrue(
            torch.allclose(
                mean_vector_orig - torch_multivariate_gaussian.mean_vector.grad,
                torch_multivariate_gaussian.mean_vector,
            )
        )
        self.assertTrue(
            torch.allclose(
                tril_diag_aux_orig - torch_multivariate_gaussian.tril_diag_aux.grad,
                torch_multivariate_gaussian.tril_diag_aux,
            )
        )
        self.assertTrue(
            torch.allclose(
                tril_nondiag_orig - torch_multivariate_gaussian.tril_nondiag.grad,
                torch_multivariate_gaussian.tril_nondiag,
            )
        )

        # verify that distribution parameters match parameters
        self.assertTrue(
            torch.allclose(
                torch_multivariate_gaussian.mean_vector, torch_multivariate_gaussian.dist.loc
            )
        )
        self.assertTrue(
            torch.allclose(
                torch_multivariate_gaussian.covariance_matrix,
                torch_multivariate_gaussian.dist.covariance_matrix,
            )
        )

    def test_gradient_optimization(self):

        # initialize distribution
        torch_multivariate_gaussian = TorchMultivariateGaussian(
            [0, 1],
            mean_vector=torch.tensor([1.0, -1.0]),
            covariance_matrix=torch.tensor(
                [
                    [2.0, 0.5],
                    [0.5, 1.5],
                ]
            ),
        )

        torch.manual_seed(0)

        # create dummy data (unit variance Gaussian)
        data = torch.distributions.MultivariateNormal(
            loc=torch.zeros(2), covariance_matrix=torch.eye(2)
        ).sample((100000,))

        # initialize gradient optimizer
        optimizer = torch.optim.SGD(torch_multivariate_gaussian.parameters(), lr=0.5)

        # perform optimization (possibly overfitting)
        for i in range(20):

            # clear gradients
            optimizer.zero_grad()

            # compute negative log-likelihood
            nll = -log_likelihood(torch_multivariate_gaussian, data).mean()
            nll.backward()

            # update parameters
            optimizer.step()

        self.assertTrue(
            torch.allclose(
                torch_multivariate_gaussian.mean_vector, torch.zeros(2), atol=1e-2, rtol=0.3
            )
        )
        self.assertTrue(
            torch.allclose(
                torch_multivariate_gaussian.covariance_matrix, torch.eye(2), atol=1e-2, rtol=0.3
            )
        )

    def test_base_backend_conversion(self):

        mean_vector = np.arange(3)
        covariance_matrix = np.array([[2, 2, 1], [2, 3, 2], [1, 2, 3]])

        torch_multivariate_gaussian = TorchMultivariateGaussian(
            [0, 1, 2], mean_vector, covariance_matrix
        )
        node_multivariate_gaussian = MultivariateGaussian(
            [0, 1, 2], mean_vector.tolist(), covariance_matrix.tolist()
        )

        node_params = node_multivariate_gaussian.get_params()
        torch_params = torch_multivariate_gaussian.get_params()

        # check conversion from torch to python
        torch_to_node_params = toNodes(torch_multivariate_gaussian).get_params()

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

    def test_initialization(self):

        # Valid parameters for Multivariate Gaussian distribution: mean vector in R^k, covariance matrix in R^(k x k) symmetric positive semi-definite (TODO: PDF only exists if p.d.?)

        # mean contains inf and mean contains nan (TODO: exception not raised)
        # self.assertRaises(Exception, TorchMultivariateGaussian, [0,1], torch.tensor([0.0, float("inf")]), torch.eye(2))
        # self.assertRaises(Exception, TorchMultivariateGaussian, [0,1], torch.tensor([0.0, float("nan")]), torch.eye(2))

        # mean vector of wrong shape (TODO: test where Exception is raised, second exception not raised),
        self.assertRaises(
            Exception, TorchMultivariateGaussian, [0, 1], torch.zeros(3), torch.eye(2)
        )
        # self.assertRaises(Exception, TorchMultivariateGaussian, [0,1], torch.zeros((1,1,2)), torch.eye(2))

        # covariance matrix of wrong shape (TODO: test where Exception is raised)
        M = torch.tensor([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        self.assertRaises(Exception, TorchMultivariateGaussian, [0, 1], torch.zeros(2), M)
        self.assertRaises(Exception, TorchMultivariateGaussian, [0, 1], torch.zeros(2), M.T)
        self.assertRaises(Exception, TorchMultivariateGaussian, [0, 1], torch.zeros(2), np.eye(3))
        # covariance matrix not symmetric positive semi-definite (TODO: test where Exception is raised)
        self.assertRaises(
            Exception, TorchMultivariateGaussian, [0, 1], torch.tensor([[1.0, 0.0], [1.0, 0.0]])
        )
        self.assertRaises(Exception, TorchMultivariateGaussian, [0, 1], -torch.eye(2))

        # invalid scope lengths
        self.assertRaises(
            Exception, TorchMultivariateGaussian, [], [0.0, 0.0], [[1.0, 0.0], [0.0, 1.0]]
        )
        self.assertRaises(
            Exception, TorchMultivariateGaussian, [0, 1, 2], [0.0, 0.0], [[1.0, 0.0], [0.0, 1.0]]
        )

        # initialize using lists
        TorchMultivariateGaussian([0, 1], [0.0, 0.0], [[1.0, 0.0], [0.0, 1.0]])

        # initialize using numpy arrays
        TorchMultivariateGaussian([0, 1], np.zeros(2), np.eye(2))

    def test_support(self):

        # Support for Multivariate Gaussian distribution: floats R^k

        multivariate_gaussian = TorchMultivariateGaussian([0, 1], np.zeros(2), np.eye(2))

        # check for infinite values
        # TODO

        # check partial marginalization
        self.assertRaises(
            ValueError, log_likelihood, multivariate_gaussian, torch.tensor([[float("nan"), 0.0]])
        )

        # check infinite values (TODO: fixed in newer versions? how to handle?)
        self.assertRaises(
            ValueError, log_likelihood, multivariate_gaussian, torch.tensor([[-float("inf"), 0.0]])
        )
        self.assertRaises(
            ValueError, log_likelihood, multivariate_gaussian, torch.tensor([[0.0, float("inf")]])
        )

    def test_marginalization(self):

        multivariate_gaussian = TorchMultivariateGaussian([0, 1], torch.zeros(2), torch.eye(2))
        data = torch.tensor([[float("nan"), float("nan")]])

        # should not raise and error and should return 1
        probs = likelihood(multivariate_gaussian, data)

        self.assertTrue(torch.allclose(probs, torch.tensor(1.0)))

        # check partial marginalization
        self.assertRaises(
            ValueError, log_likelihood, multivariate_gaussian, torch.tensor([[float("nan"), 0.0]])
        )


if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
