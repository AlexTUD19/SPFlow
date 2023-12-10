import random
import unittest

import numpy as np
import torch
import tensorly as tl
import pytest

from spflow.meta.data import Scope
from spflow.meta.dispatch import DispatchContext
from spflow.tensorly.inference import log_likelihood
from spflow.torch.learning import (
    em,
    expectation_maximization,
    maximum_likelihood_estimation,
)
from spflow.tensorly.structure.spn import LogNormal
from spflow.tensorly.structure.spn import ProductNode, SumNode
from spflow.torch.structure.general.nodes.leaves.parametric.log_normal import updateBackend
from spflow.tensorly.utils.helper_functions import tl_toNumpy

tc = unittest.TestCase()

def test_mle_1(do_for_all_backends):

    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    leaf = LogNormal(Scope([0]))

    # simulate data
    data = np.random.lognormal(mean=-1.7, sigma=0.2, size=(10000, 1))

    # perform MLE
    maximum_likelihood_estimation(leaf, tl.tensor(data), bias_correction=True)

    tc.assertTrue(np.isclose(tl_toNumpy(leaf.mean), tl.tensor(-1.7), atol=1e-2, rtol=1e-2))
    tc.assertTrue(np.isclose(tl_toNumpy(leaf.std), tl.tensor(0.2), atol=1e-2, rtol=1e-2))

def test_mle_2(do_for_all_backends):

    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    leaf = LogNormal(Scope([0]))

    # simulate data
    data = np.random.lognormal(mean=0.5, sigma=1.3, size=(30000, 1))

    # perform MLE
    maximum_likelihood_estimation(leaf, tl.tensor(data), bias_correction=True)

    tc.assertTrue(np.isclose(tl_toNumpy(leaf.mean), tl.tensor(0.5), atol=1e-2, rtol=1e-2))
    tc.assertTrue(np.isclose(tl_toNumpy(leaf.std), tl.tensor(1.3), atol=1e-2, rtol=1e-2))

def test_mle_bias_correction(do_for_all_backends):

    leaf = LogNormal(Scope([0]))
    data = tl.exp(tl.tensor([[-1.0], [1.0]]))

    # perform MLE
    maximum_likelihood_estimation(leaf, data, bias_correction=False)
    tc.assertTrue(np.isclose(tl_toNumpy(leaf.std), tl.sqrt(tl.tensor(1.0))))

    # perform MLE
    maximum_likelihood_estimation(leaf, data, bias_correction=True)
    tc.assertTrue(np.isclose(tl_toNumpy(leaf.std), tl.sqrt(tl.tensor(2.0))))

def test_mle_edge_std_0(do_for_all_backends):

    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    leaf = LogNormal(Scope([0]))

    # simulate data
    data = tl.exp(tl.randn((1, 1)))

    # perform MLE
    maximum_likelihood_estimation(leaf, data, bias_correction=False)

    tc.assertTrue(np.isclose(tl_toNumpy(leaf.mean), tl.log(data[0])))
    tc.assertTrue(tl_toNumpy(leaf.std) > 0)

def test_mle_edge_std_nan(do_for_all_backends):

    # set seed
    np.random.seed(0)
    random.seed(0)

    leaf = LogNormal(Scope([0]))

    # simulate data
    data = tl.exp(tl.randn((1, 1)))

    # perform MLE (Torch does not throw a warning different to NumPy)
    maximum_likelihood_estimation(leaf, data, bias_correction=True)

    tc.assertTrue(np.isclose(tl_toNumpy(leaf.mean), tl.log(data[0])))
    tc.assertFalse(np.isnan(tl_toNumpy(leaf.std)))
    tc.assertTrue(tl_toNumpy(leaf.std) > 0)

def test_mle_only_nans(do_for_all_backends):

    leaf = LogNormal(Scope([0]))

    # simulate data
    data = tl.tensor([[float("nan")], [float("nan")]])

    # check if exception is raised
    tc.assertRaises(
        ValueError,
        maximum_likelihood_estimation,
        leaf,
        data,
        nan_strategy="ignore",
    )

def test_mle_invalid_support(do_for_all_backends):

    leaf = LogNormal(Scope([0]))

    # perform MLE (should raise exceptions)
    tc.assertRaises(
        ValueError,
        maximum_likelihood_estimation,
        leaf,
        tl.tensor([[float("inf")]]),
        bias_correction=True,
    )

def test_mle_nan_strategy_none(do_for_all_backends):

    leaf = LogNormal(Scope([0]))
    tc.assertRaises(
        ValueError,
        maximum_likelihood_estimation,
        leaf,
        tl.tensor([[float("nan")], [0.1], [-1.8], [0.7]]),
        nan_strategy=None,
    )

def test_mle_nan_strategy_ignore(do_for_all_backends):

    leaf = LogNormal(Scope([0]))
    maximum_likelihood_estimation(
        leaf,
        tl.exp(tl.tensor([[float("nan")], [0.1], [-1.8], [0.7]])),
        nan_strategy="ignore",
        bias_correction=False,
    )
    tc.assertTrue(np.isclose(tl_toNumpy(leaf.mean), tl.tensor(-1.0 / 3.0)))
    tc.assertTrue(
        np.isclose(
            tl_toNumpy(leaf.std),
            tl.sqrt(1 / 3 * tl.sum((tl.tensor([[0.1], [-1.8], [0.7]]) + 1.0 / 3.0) ** 2)),
        )
    )

def test_mle_nan_strategy_callable(do_for_all_backends):

    leaf = LogNormal(Scope([0]))
    # should not raise an issue
    maximum_likelihood_estimation(leaf, tl.tensor([[0.5], [1]]), nan_strategy=lambda x: x)

def test_mle_nan_strategy_invalid(do_for_all_backends):

    leaf = LogNormal(Scope([0]))
    tc.assertRaises(
        ValueError,
        maximum_likelihood_estimation,
        leaf,
        tl.tensor([[float("nan")], [0.1], [1.9], [0.7]]),
        nan_strategy="invalid_string",
    )
    tc.assertRaises(
        ValueError,
        maximum_likelihood_estimation,
        leaf,
        tl.tensor([[float("nan")], [1], [0], [1]]),
        nan_strategy=1,
    )

def test_weighted_mle(do_for_all_backends):

    leaf = LogNormal(Scope([0]))

    data = tl.tensor(
        np.vstack(
            [
                np.random.lognormal(1.7, 0.8, size=(10000, 1)),
                np.random.lognormal(0.5, 1.4, size=(10000, 1)),
            ]
        )
    )
    weights = tl.concatenate([tl.zeros(10000), tl.ones(10000)])

    maximum_likelihood_estimation(leaf, data, weights)

    tc.assertTrue(np.isclose(tl_toNumpy(leaf.mean), tl.tensor(0.5), atol=1e-2, rtol=1e-1))
    tc.assertTrue(np.isclose(tl_toNumpy(leaf.std), tl.tensor(1.4), atol=1e-2, rtol=1e-2))

def test_em_step(do_for_all_backends):
    # em is only implemented for pytorch backend
    if do_for_all_backends == "numpy":
        return

    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    leaf = LogNormal(Scope([0]))
    data = tl.tensor(np.random.lognormal(mean=-1.7, sigma=0.2, size=(10000, 1)))
    dispatch_ctx = DispatchContext()

    # compute gradients of log-likelihoods w.r.t. module log-likelihoods
    ll = log_likelihood(leaf, data, dispatch_ctx=dispatch_ctx)
    ll.retain_grad()
    ll.sum().backward()

    # perform an em step
    em(leaf, data, dispatch_ctx=dispatch_ctx)

    tc.assertTrue(np.isclose(tl_toNumpy(leaf.mean), tl.tensor(-1.7), atol=1e-2, rtol=1e-3))
    tc.assertTrue(np.isclose(tl_toNumpy(leaf.std), tl.tensor(0.2), atol=1e-2, rtol=1e-3))

def test_em_product_of_log_normals(do_for_all_backends):
    # em is only implemented for pytorch backend
    if do_for_all_backends == "numpy":
        return

    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    l1 = LogNormal(Scope([0]), mean=1.5, std=0.75)
    l2 = LogNormal(Scope([1]), mean=-2.5, std=1.5)
    prod_node = ProductNode([l1, l2])

    data = tl.tensor(
        np.hstack(
            [
                np.random.lognormal(2.0, 1.0, size=(20000, 1)),
                np.random.lognormal(-2.0, 1.0, size=(20000, 1)),
            ]
        )
    )

    expectation_maximization(prod_node, data, max_steps=10)

    tc.assertTrue(np.isclose(tl_toNumpy(l1.mean), tl.tensor(2.0), atol=1e-3, rtol=1e-2))
    tc.assertTrue(np.isclose(tl_toNumpy(l1.std), tl.tensor(1.0), atol=1e-2, rtol=1e-2))
    tc.assertTrue(np.isclose(tl_toNumpy(l2.mean), tl.tensor(-2.0), atol=1e-3, rtol=1e-2))
    tc.assertTrue(np.isclose(tl_toNumpy(l2.std), tl.tensor(1.0), atol=1e-2, rtol=1e-2))

def test_em_mixture_of_log_normals(do_for_all_backends):
    # em is only implemented for pytorch backend
    if do_for_all_backends == "numpy":
        return

    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    l1 = LogNormal(Scope([0]), mean=1.5, std=0.75)
    l2 = LogNormal(Scope([0]), mean=-2.5, std=1.5)
    sum_node = SumNode([l1, l2], weights=[0.5, 0.5])

    data = tl.tensor(
        np.vstack(
            [
                np.random.lognormal(2.0, 1.0, size=(30000, 1)),
                np.random.lognormal(-2.0, 1.0, size=(30000, 1)),
            ]
        )
    )

    expectation_maximization(sum_node, data, max_steps=10)

    tc.assertTrue(np.isclose(tl_toNumpy(l1.mean), tl.tensor(2.0), atol=1e-2, rtol=1e-1))
    tc.assertTrue(np.isclose(tl_toNumpy(l1.std), tl.tensor(1.0), atol=1e-2, rtol=1e-1))
    tc.assertTrue(np.isclose(tl_toNumpy(l2.mean), tl.tensor(-2.0), atol=1e-2, rtol=1e-1))
    tc.assertTrue(np.isclose(tl_toNumpy(l2.std), tl.tensor(1.0), atol=1e-2, rtol=1e-1))
    tc.assertTrue(np.allclose(tl_toNumpy(sum_node.weights), tl.tensor([0.5, 0.5]), atol=1e-3, rtol=1e-2))

def test_update_backend(do_for_all_backends):
    # em is only implemented for pytorch backend
    if do_for_all_backends == "numpy":
        return
    backends = ["numpy", "pytorch"]
    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    leaf = LogNormal(Scope([0]))

    # simulate data
    data = np.random.lognormal(mean=-1.7, sigma=0.2, size=(10000, 1))

    # perform MLE
    maximum_likelihood_estimation(leaf, tl.tensor(data))

    params = leaf.get_params()[0]
    params2 = leaf.get_params()[1]

    leaf = LogNormal(Scope([0]))
    prod_node = ProductNode([leaf])
    expectation_maximization(prod_node, tl.tensor(data), max_steps=10)
    params_em = leaf.get_params()[0]
    params_em2 = leaf.get_params()[1]


    # make sure that probabilities match python backend probabilities
    for backend in backends:
        with tl.backend_context(backend):
            leaf = LogNormal(Scope([0]))
            leaf_updated = updateBackend(leaf)
            maximum_likelihood_estimation(leaf_updated, tl.tensor(data))
            # check conversion from torch to python
            tc.assertTrue(np.isclose(leaf_updated.get_params()[0], params, atol=1e-2, rtol=1e-3))
            tc.assertTrue(np.isclose(leaf_updated.get_params()[1], params2, atol=1e-2, rtol=1e-3))

            leaf = LogNormal(Scope([0]))
            leaf_updated = updateBackend(leaf)
            prod_node = ProductNode([leaf_updated])
            if tl.get_backend() != "pytorch":
                with pytest.raises(NotImplementedError):
                    expectation_maximization(prod_node, tl.tensor(data), max_steps=10)
            else:
                expectation_maximization(prod_node, tl.tensor(data), max_steps=10)
                tc.assertTrue(np.isclose(leaf_updated.get_params()[0], params_em, atol=1e-3, rtol=1e-2))
                tc.assertTrue(np.isclose(leaf_updated.get_params()[1], params_em2, atol=1e-3, rtol=1e-2))

def test_change_dtype(do_for_all_backends):
    np.random.seed(0)
    random.seed(0)

    node = LogNormal(Scope([0]))
    prod_node = ProductNode([node])

    # simulate data
    data = np.random.lognormal(mean=-1.7, sigma=0.2, size=(10000, 1))

    # perform MLE
    maximum_likelihood_estimation(node, tl.tensor(data, dtype=tl.float32))
    if do_for_all_backends == "numpy":
        tc.assertTrue(isinstance(node.mean, float))
        tc.assertTrue(isinstance(node.std, float))
    else:
        tc.assertTrue(node.mean.dtype == tl.float32)
        tc.assertTrue(node.std.dtype == tl.float32)

    node.to_dtype(tl.float64)

    dummy_data = tl.tensor(data, dtype=tl.float64)
    maximum_likelihood_estimation(node, dummy_data)
    if do_for_all_backends == "numpy":
        tc.assertTrue(isinstance(node.mean, float))
        tc.assertTrue(isinstance(node.std, float))
    else:
        tc.assertTrue(node.mean.dtype == tl.float64)
        tc.assertTrue(node.std.dtype == tl.float64)

    if do_for_all_backends == "numpy":
        tc.assertRaises(NotImplementedError, expectation_maximization, prod_node, tl.tensor(data, dtype=tl.float64),
                        max_steps=10)
    else:
        # test if em runs without error after dype change
        expectation_maximization(prod_node, tl.tensor(data, dtype=tl.float64), max_steps=10)


def test_change_device(do_for_all_backends):
    torch.set_default_dtype(torch.float32)
    cuda = torch.device("cuda")
    np.random.seed(0)
    random.seed(0)

    node = LogNormal(Scope([0]))
    prod_node = ProductNode([node])

    # simulate data
    data = np.random.lognormal(mean=-1.7, sigma=0.2, size=(10000, 1))

    if do_for_all_backends == "numpy":
        tc.assertRaises(ValueError, node.to_device, cuda)
        return

    # perform MLE
    maximum_likelihood_estimation(node, tl.tensor(data, dtype=tl.float32))

    tc.assertTrue(node.mean.device.type == "cpu")
    tc.assertTrue(node.std.device.type == "cpu")

    node.to_device(cuda)

    dummy_data = tl.tensor(data, dtype=tl.float32, device=cuda)

    # perform MLE
    maximum_likelihood_estimation(node, dummy_data)
    tc.assertTrue(node.mean.device.type == "cuda")
    tc.assertTrue(node.std.device.type == "cuda")

    # test if em runs without error after device change
    expectation_maximization(prod_node, tl.tensor(data, dtype=tl.float32, device=cuda), max_steps=10)


if __name__ == "__main__":
    torch.set_default_dtype(torch.float32)
    unittest.main()
