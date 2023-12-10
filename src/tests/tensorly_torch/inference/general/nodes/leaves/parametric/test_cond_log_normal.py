import random
import unittest

import numpy as np
import torch
import tensorly as tl

from spflow.tensorly.structure.spn import CondLogNormal
from spflow.meta.data import Scope
from spflow.meta.dispatch import DispatchContext
from spflow.tensorly.inference import likelihood, log_likelihood
from spflow.base.structure.general.nodes.leaves.parametric.cond_log_normal import CondLogNormal as BaseCondLogNormal
from spflow.torch.structure.general.nodes.leaves.parametric.cond_log_normal import updateBackend
from spflow.tensorly.utils.helper_functions import tl_toNumpy

tc = unittest.TestCase()

def test_likelihood_module_cond_f(do_for_all_backends):

    cond_f = lambda data: {"mean": 0.0, "std": 1.0}

    log_normal = CondLogNormal(Scope([0], [1]), cond_f=cond_f)

    # create test inputs/outputs
    data = tl.tensor([[0.5], [1.0], [1.5]])
    targets = tl.tensor([[0.627496], [0.398942], [0.244974]])

    probs = likelihood(log_normal, data)
    log_probs = log_likelihood(log_normal, data)

    tc.assertTrue(np.allclose(tl_toNumpy(probs), tl.exp(log_probs)))
    tc.assertTrue(np.allclose(tl_toNumpy(probs), targets))

def test_likelihood_args_p(do_for_all_backends):

    log_normal = CondLogNormal(Scope([0], [1]))

    dispatch_ctx = DispatchContext()
    dispatch_ctx.args[log_normal] = {"mean": 0.0, "std": 1.0}

    # create test inputs/outputs
    data = tl.tensor([[0.5], [1.0], [1.5]])
    targets = tl.tensor([[0.627496], [0.398942], [0.244974]])

    probs = likelihood(log_normal, data, dispatch_ctx=dispatch_ctx)
    log_probs = log_likelihood(log_normal, data, dispatch_ctx=dispatch_ctx)

    tc.assertTrue(np.allclose(tl_toNumpy(probs), tl.exp(log_probs)))
    tc.assertTrue(np.allclose(tl_toNumpy(probs), targets))

def test_likelihood_args_cond_f(do_for_all_backends):

    log_normal = CondLogNormal(Scope([0], [1]))

    cond_f = lambda data: {"mean": 0.0, "std": 1.0}

    dispatch_ctx = DispatchContext()
    dispatch_ctx.args[log_normal] = {"cond_f": cond_f}

    # create test inputs/outputs
    data = tl.tensor([[0.5], [1.0], [1.5]])
    targets = tl.tensor([[0.627496], [0.398942], [0.244974]])

    probs = likelihood(log_normal, data, dispatch_ctx=dispatch_ctx)
    log_probs = log_likelihood(log_normal, data, dispatch_ctx=dispatch_ctx)

    tc.assertTrue(np.allclose(tl_toNumpy(probs), tl.exp(log_probs)))
    tc.assertTrue(np.allclose(tl_toNumpy(probs), targets))

def test_inference(do_for_all_backends):

    mean = random.random()
    std = random.random() + 1e-7  # offset by small number to avoid zero

    torch_log_normal = CondLogNormal(Scope([0], [1]), cond_f=lambda data: {"mean": mean, "std": std})
    node_log_normal = BaseCondLogNormal(Scope([0], [1]), cond_f=lambda data: {"mean": mean, "std": std})

    # create dummy input data (batch size x random variables)
    data = np.random.rand(3, 1)

    log_probs = log_likelihood(node_log_normal, data)
    log_probs_torch = log_likelihood(torch_log_normal, tl.tensor(data))

    # make sure that probabilities match python backend probabilities
    tc.assertTrue(np.allclose(log_probs, tl_toNumpy(log_probs_torch)))

def test_gradient_computation(do_for_all_backends):

    if do_for_all_backends == "numpy":
        return

    mean = tl.tensor(random.random(), requires_grad=True)
    std = tl.tensor(random.random() + 1e-7, requires_grad=True)  # offset by small number to avoid zero

    torch_log_normal = CondLogNormal(Scope([0], [1]), cond_f=lambda data: {"mean": mean, "std": std})

    # create dummy input data (batch size x random variables)
    data = np.random.rand(3, 1)

    log_probs_torch = log_likelihood(torch_log_normal, tl.tensor(data))

    # create dummy targets
    targets_torch = torch.ones(3, 1)

    loss = torch.nn.MSELoss()(log_probs_torch, targets_torch)
    loss.backward()

    tc.assertTrue(mean.grad is not None)
    tc.assertTrue(std.grad is not None)


"""
def test_likelihood_marginalization(do_for_all_backends):

    log_normal = LogNormal(Scope([0], [1]), 0.0, 1.0)
    data = tl.tensor([[float("nan")]])

    # should not raise and error and should return 1
    probs = likelihood(log_normal, data)

    tc.assertTrue(torch.allclose(probs, tl.tensor(1.0)))

def test_support(do_for_all_backends):

    # Support for Log-Normal distribution: floats (0,inf)

    log_normal = LogNormal(Scope([0], [1]), 0.0, 1.0)

    # check infinite values
    tc.assertRaises(ValueError, log_likelihood, log_normal, tl.tensor([[float("inf")]]))
    tc.assertRaises(ValueError, log_likelihood, log_normal, tl.tensor([[-float("inf")]]))

    # invalid float values
    tc.assertRaises(ValueError, log_likelihood, log_normal, tl.tensor([[0]]))

    # valid float values
    log_likelihood(
        log_normal, tl.tensor([[torch.nextafter(tl.tensor(0.0), tl.tensor(1.0))]])
    )
    log_likelihood(log_normal, tl.tensor([[4.3]]))
"""


def test_update_backend(do_for_all_backends):
    backends = ["numpy", "pytorch"]
    mean = random.random()
    std = random.random() + 1e-7  # offset by small number to avoid zero

    log_normal = CondLogNormal(Scope([0], [1]), cond_f=lambda data: {"mean": mean, "std": std})

    # create dummy input data (batch size x random variables)
    data = np.random.rand(3, 1)

    log_probs = log_likelihood(log_normal, tl.tensor(data))

    # make sure that probabilities match python backend probabilities
    for backend in backends:
        with tl.backend_context(backend):
            log_normal_updated = updateBackend(log_normal)
            log_probs_updated = log_likelihood(log_normal_updated, tl.tensor(data))
            # check conversion from torch to python
            tc.assertTrue(np.allclose(tl_toNumpy(log_probs), tl_toNumpy(log_probs_updated)))

def test_change_dtype(do_for_all_backends):
    mean = random.random()
    std = random.random() + 1e-7  # offset by small number to avoid zero

    node = CondLogNormal(Scope([0], [1]), cond_f=lambda data: {"mean": mean, "std": std})
    dummy_data = tl.tensor(np.random.rand(3, 1), dtype=tl.float32)
    layer_ll = log_likelihood(node, dummy_data)
    tc.assertTrue(layer_ll.dtype == tl.float32)
    node.to_dtype(tl.float64)
    dummy_data = tl.tensor(np.random.rand(3, 1), dtype=tl.float64)
    layer_ll_up = log_likelihood(node, dummy_data)
    tc.assertTrue(layer_ll_up.dtype == tl.float64)

def test_change_device(do_for_all_backends):
    torch.set_default_dtype(torch.float32)
    cuda = torch.device("cuda")
    mean = random.random()
    std = random.random() + 1e-7  # offset by small number to avoid zero

    node = CondLogNormal(Scope([0], [1]), cond_f=lambda data: {"mean": mean, "std": std})
    dummy_data = tl.tensor(np.random.rand(3, 1), dtype=tl.float32)
    layer_ll = log_likelihood(node, dummy_data)
    if do_for_all_backends == "numpy":
        tc.assertRaises(ValueError, node.to_device, cuda)
        return
    tc.assertTrue(layer_ll.device.type == "cpu")
    node.to_device(cuda)
    dummy_data = tl.tensor(np.random.rand(3, 1), device=cuda)
    layer_ll = log_likelihood(node, dummy_data)
    tc.assertTrue(layer_ll.device.type == "cuda")

if __name__ == "__main__":
    torch.set_default_dtype(torch.float32)
    unittest.main()
