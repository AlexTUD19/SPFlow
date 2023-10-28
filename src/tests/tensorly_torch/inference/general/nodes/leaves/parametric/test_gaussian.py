import random
import unittest

import numpy as np
import torch
import tensorly as tl

from spflow.tensorly.structure.spn import Gaussian
from spflow.meta.data import Scope
from spflow.tensorly.inference import likelihood, log_likelihood
from spflow.base.structure.general.nodes.leaves.parametric.gaussian import Gaussian as BaseGaussian
from spflow.torch.structure.general.nodes.leaves.parametric.gaussian import updateBackend
from spflow.tensorly.utils.helper_functions import tl_toNumpy

tc = unittest.TestCase()

def test_inference(do_for_all_backends):

    mean = random.random()
    std = random.random() + 1e-7  # offset by small number to avoid zero

    torch_gaussian = Gaussian(Scope([0]), mean, std)
    node_gaussian = BaseGaussian(Scope([0]), mean, std)

    # create dummy input data (batch size x random variables)
    data = np.random.randn(3, 1)

    log_probs = log_likelihood(node_gaussian, data)
    log_probs_torch = log_likelihood(torch_gaussian, tl.tensor(data))

    # make sure that probabilities match python backend probabilities
    tc.assertTrue(np.allclose(log_probs, tl_toNumpy(log_probs_torch)))

def test_gradient_computation(do_for_all_backends):

    if do_for_all_backends == "numpy":
        return

    mean = random.random()
    std = random.random() + 1e-7  # offset by small number to avoid zero

    torch_gaussian = Gaussian(Scope([0]), mean, std)

    # create dummy input data (batch size x random variables)
    data = np.random.randn(3, 1)

    log_probs_torch = log_likelihood(torch_gaussian, tl.tensor(data))

    # create dummy targets
    targets_torch = torch.ones(3, 1)

    loss = torch.nn.MSELoss()(log_probs_torch, targets_torch)
    loss.backward()

    tc.assertTrue(torch_gaussian.mean.grad is not None)
    tc.assertTrue(torch_gaussian.std_aux.grad is not None)

    mean_orig = torch_gaussian.mean.detach().clone()
    std_aux_orig = torch_gaussian.std_aux.detach().clone()

    optimizer = torch.optim.SGD(torch_gaussian.parameters(), lr=1)
    optimizer.step()

    # make sure that parameters are correctly updated
    tc.assertTrue(torch.allclose(mean_orig - torch_gaussian.mean.grad, torch_gaussian.mean))
    tc.assertTrue(
        torch.allclose(
            std_aux_orig - torch_gaussian.std_aux.grad,
            torch_gaussian.std_aux,
        )
    )

    # verify that distribution parameters match parameters
    tc.assertTrue(torch.allclose(torch_gaussian.mean, torch_gaussian.dist.mean))
    tc.assertTrue(torch.allclose(torch_gaussian.std, torch_gaussian.dist.stddev))

def test_gradient_optimization(do_for_all_backends):
    torch.set_default_dtype(torch.float64)

    if do_for_all_backends == "numpy":
        return

    # initialize distribution
    torch_gaussian = Gaussian(Scope([0]), mean=1.0, std=2.0)

    torch.manual_seed(0)

    # create dummy data (unit variance Gaussian)
    data = torch.randn((100000, 1))
    data = (data - data.mean()) / data.std()

    # initialize gradient optimizer
    optimizer = torch.optim.SGD(torch_gaussian.parameters(), lr=0.5)

    # perform optimization (possibly overfitting)
    for i in range(20):

        # clear gradients
        optimizer.zero_grad()

        # compute negative log-likelihood
        nll = -log_likelihood(torch_gaussian, data).mean()
        nll.backward()

        # update parameters
        optimizer.step()

    tc.assertTrue(torch.allclose(torch_gaussian.mean, tl.tensor(0.0, dtype=tl.float64), atol=1e-3, rtol=1e-3))
    tc.assertTrue(torch.allclose(torch_gaussian.std, tl.tensor(1.0, dtype=tl.float64), atol=1e-3, rtol=1e-3))

def test_likelihood_marginalization(do_for_all_backends):

    gaussian = Gaussian(Scope([0]), 0.0, 1.0)
    data = tl.tensor([[float("nan")]])

    # should not raise and error and should return 1
    probs = likelihood(gaussian, data)

    tc.assertTrue(np.allclose(tl_toNumpy(probs), tl.tensor(1.0)))

def test_support(do_for_all_backends):

    # Support for Gaussian distribution: floats (-inf, inf)

    gaussian = Gaussian(Scope([0]), 0.0, 1.0)

    # check infinite values
    tc.assertRaises(ValueError, log_likelihood, gaussian, tl.tensor([[float("inf")]]))
    tc.assertRaises(
        ValueError,
        log_likelihood,
        gaussian,
        tl.tensor([[-float("inf")]]),
    )

def test_update_backend(do_for_all_backends):
    backends = ["numpy", "pytorch"]
    mean = random.random()
    std = random.random() + 1e-7  # offset by small number to avoid zero

    gaussian = Gaussian(Scope([0]), mean, std)

    # create dummy input data (batch size x random variables)
    data = np.random.randn(3, 1)

    log_probs = log_likelihood(gaussian, tl.tensor(data))

    # make sure that probabilities match python backend probabilities
    for backend in backends:
        with tl.backend_context(backend):
            gaussian_updated = updateBackend(gaussian)
            log_probs_updated = log_likelihood(gaussian_updated, tl.tensor(data))
            # check conversion from torch to python
            tc.assertTrue(np.allclose(tl_toNumpy(log_probs), tl_toNumpy(log_probs_updated)))


if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
