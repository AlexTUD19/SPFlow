import random
import unittest

import numpy as np
import pytest
import torch
import tensorly as tl

from spflow.meta.data import Scope
from spflow.meta.dispatch import DispatchContext
from spflow.modules.module import log_likelihood
from spflow.torch.learning import (
    em,
    expectation_maximization,
    maximum_likelihood_estimation,
)
from spflow.structure.spn import ExponentialLayer  # , ProductNode, SumNode
from spflow.structure.spn import ProductNode, SumNode
from spflow.utils import Tensor
from spflow.tensor import ops as tle
from spflow.torch.structure.general.layer.leaf.exponential import updateBackend

tc = unittest.TestCase()


def test_mle(do_for_all_backends):
    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    layer = ExponentialLayer(scope=[Scope([0]), Scope([1])])

    # simulate data
    data = np.hstack(
        [
            np.random.exponential(scale=1.0 / 0.3, size=(20000, 1)),
            np.random.exponential(scale=1.0 / 2.7, size=(20000, 1)),
        ]
    )

    # perform MLE
    maximum_likelihood_estimation(layer, tl.tensor(data), bias_correction=True)

    tc.assertTrue(np.allclose(tle.toNumpy(layer.l), tl.tensor([0.3, 2.7]), atol=1e-2, rtol=1e-3))


def test_mle_bias_correction(do_for_all_backends):
    layer = ExponentialLayer(Scope([0]))
    data = tl.tensor([[0.3], [2.7]])

    # perform MLE
    maximum_likelihood_estimation(layer, data, bias_correction=False)
    tc.assertTrue(np.isclose(tle.toNumpy(layer.l), tl.tensor(2.0 / 3.0)))

    # perform MLE
    maximum_likelihood_estimation(layer, data, bias_correction=True)
    tc.assertTrue(np.isclose(tle.toNumpy(layer.l), tl.tensor(1.0 / 3.0)))


def test_mle_edge_0(do_for_all_backends):
    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    layer = ExponentialLayer(Scope([0]))

    # simulate data
    data = np.random.exponential(scale=1.0, size=(1, 1))

    # perform MLE (bias correction leads to zero result)
    maximum_likelihood_estimation(layer, tl.tensor(data), bias_correction=True)

    tc.assertFalse(np.isnan(tle.toNumpy(layer.l)))
    tc.assertTrue(tl.all(layer.l > 0.0))


def test_mle_only_nans(do_for_all_backends):
    layer = ExponentialLayer(scope=[Scope([0]), Scope([1])])

    # simulate data
    data = tl.tensor([[float("nan"), float("nan")], [float("nan"), 0.5]])

    # check if exception is raised
    tc.assertRaises(
        ValueError,
        maximum_likelihood_estimation,
        layer,
        data,
        nan_strategy="ignore",
    )


def test_mle_invalid_support(do_for_all_backends):
    layer = ExponentialLayer(Scope([0]))

    # perform MLE (should raise exceptions)
    tc.assertRaises(
        ValueError,
        maximum_likelihood_estimation,
        layer,
        tl.tensor([[float("nan")]]),
        bias_correction=True,
    )
    tc.assertRaises(
        ValueError,
        maximum_likelihood_estimation,
        layer,
        tl.tensor([[-0.1]]),
        bias_correction=True,
    )


def test_mle_nan_strategy_none(do_for_all_backends):
    layer = ExponentialLayer(Scope([0]))
    tc.assertRaises(
        ValueError,
        maximum_likelihood_estimation,
        layer,
        tl.tensor([[float("nan")], [0.1], [1.9], [0.7]]),
        nan_strategy=None,
    )


def test_mle_nan_strategy_ignore(do_for_all_backends):
    layer = ExponentialLayer(Scope([0]))
    maximum_likelihood_estimation(
        layer,
        tl.tensor([[float("nan")], [0.1], [1.9], [0.7]]),
        nan_strategy="ignore",
        bias_correction=False,
    )
    tc.assertTrue(np.isclose(tle.toNumpy(layer.l), tl.tensor(3.0 / 2.7)))


def test_mle_nan_strategy_callable(do_for_all_backends):
    layer = ExponentialLayer(Scope([0]))
    # should not raise an issue
    maximum_likelihood_estimation(layer, tl.tensor([[0.5], [1]]), nan_strategy=lambda x: x)


def test_mle_nan_strategy_invalid(do_for_all_backends):
    layer = ExponentialLayer(Scope([0]))
    tc.assertRaises(
        ValueError,
        maximum_likelihood_estimation,
        layer,
        tl.tensor([[float("nan")], [0.1], [1.9], [0.7]]),
        nan_strategy="invalid_string",
    )
    tc.assertRaises(
        ValueError,
        maximum_likelihood_estimation,
        layer,
        tl.tensor([[float("nan")], [1], [0], [1]]),
        nan_strategy=1,
    )


def test_weighted_mle(do_for_all_backends):
    torch.set_default_dtype(torch.float32)

    leaf = ExponentialLayer([Scope([0]), Scope([1])])

    data = tl.tensor(
        np.hstack(
            [
                np.vstack(
                    [
                        np.random.exponential(scale=1.0 / 1.8, size=(10000, 1)),
                        np.random.exponential(scale=1.0 / 0.2, size=(10000, 1)),
                    ]
                ),
                np.vstack(
                    [
                        np.random.exponential(scale=1.0 / 0.3, size=(10000, 1)),
                        np.random.exponential(scale=1.0 / 1.7, size=(10000, 1)),
                    ]
                ),
            ]
        ),
        dtype=tl.float32,
    )
    weights = tl.concatenate([tl.zeros(10000, dtype=tl.float32), tl.ones(10000, dtype=tl.float32)])

    maximum_likelihood_estimation(leaf, data, weights)

    tc.assertTrue(
        np.allclose(tle.toNumpy(leaf.l), tl.tensor([0.2, 1.7], dtype=tl.float64), atol=1e-2, rtol=1e-2)
    )


def test_em_step(do_for_all_backends):
    if do_for_all_backends == "numpy":
        return

    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    layer = ExponentialLayer([Scope([0]), Scope([1])])
    data = tl.tensor(
        np.hstack(
            [
                np.random.exponential(scale=1.0 / 0.3, size=(10000, 1)),
                np.random.exponential(scale=1.0 / 1.7, size=(10000, 1)),
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

    tc.assertTrue(np.allclose(tle.toNumpy(layer.l), tl.tensor([0.3, 1.7]), atol=1e-2, rtol=1e-2))


def test_em_product_of_exponentials(do_for_all_backends):
    if do_for_all_backends == "numpy":
        return

    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    layer = ExponentialLayer([Scope([0]), Scope([1])])
    prod_node = ProductNode([layer])

    data = tl.tensor(
        np.hstack(
            [
                np.random.exponential(scale=1.0 / 0.8, size=(10000, 1)),
                np.random.exponential(scale=1.0 / 1.4, size=(10000, 1)),
            ]
        )
    )

    expectation_maximization(prod_node, data, max_steps=10)

    tc.assertTrue(np.allclose(tle.toNumpy(layer.l), tl.tensor([0.8, 1.4]), atol=1e-3, rtol=1e-2))


def test_em_sum_of_exponentials(do_for_all_backends):
    if do_for_all_backends == "numpy":
        return

    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    layer = ExponentialLayer([Scope([0]), Scope([0])], l=[0.6, 1.2])
    sum_node = SumNode([layer], weights=[0.5, 0.5])

    data = tl.tensor(
        np.vstack(
            [
                np.random.exponential(scale=1.0 / 0.8, size=(10000, 1)),
                np.random.exponential(scale=1.0 / 1.4, size=(10000, 1)),
            ]
        )
    )

    expectation_maximization(sum_node, data, max_steps=10)

    tc.assertTrue(np.allclose(tle.toNumpy(layer.l), tl.tensor([0.8, 1.4]), atol=1e-2, rtol=1e-2))


def test_update_backend(do_for_all_backends):
    if do_for_all_backends == "numpy":
        return
    backends = ["numpy", "pytorch"]
    # set seed
    torch.manual_seed(0)
    np.random.seed(0)
    random.seed(0)

    layer = ExponentialLayer(scope=[Scope([0]), Scope([1])])

    # simulate data
    data = np.hstack(
        [
            np.random.exponential(scale=1.0 / 0.3, size=(20000, 1)),
            np.random.exponential(scale=1.0 / 2.7, size=(20000, 1)),
        ]
    )

    # perform MLE
    maximum_likelihood_estimation(layer, tl.tensor(data))

    params = tle.toNumpy(layer.l)

    layer = ExponentialLayer(scope=[Scope([0]), Scope([1])])
    prod_node = ProductNode([layer])
    expectation_maximization(prod_node, tl.tensor(data), max_steps=10)
    params_em = tle.toNumpy(layer.l)

    # make sure that probabilities match python backend probabilities
    for backend in backends:
        with tl.backend_context(backend):
            layer = ExponentialLayer(scope=[Scope([0]), Scope([1])])
            layer_updated = updateBackend(layer)
            maximum_likelihood_estimation(layer_updated, tl.tensor(data))
            # check conversion from torch to python
            tc.assertTrue(np.allclose(tle.toNumpy(layer_updated.l), params, atol=1e-2, rtol=1e-3))

            layer = ExponentialLayer(scope=[Scope([0]), Scope([1])])
            layer_updated = updateBackend(layer)
            prod_node = ProductNode([layer_updated])
            if tl.get_backend() != "pytorch":
                with pytest.raises(NotImplementedError):
                    expectation_maximization(prod_node, tl.tensor(data), max_steps=10)
            else:
                expectation_maximization(prod_node, tl.tensor(data), max_steps=10)
                tc.assertTrue(np.allclose(tle.toNumpy(layer_updated.l), params_em, atol=1e-3, rtol=1e-2))


def test_change_dtype(do_for_all_backends):
    np.random.seed(0)
    random.seed(0)

    layer = ExponentialLayer(scope=[Scope([0]), Scope([1])])
    prod_node = ProductNode([layer])

    # simulate data
    data = np.hstack(
        [
            np.random.exponential(scale=1.0 / 0.3, size=(20000, 1)),
            np.random.exponential(scale=1.0 / 2.7, size=(20000, 1)),
        ]
    )

    # perform MLE
    maximum_likelihood_estimation(layer, tl.tensor(data, dtype=tl.float32))
    tc.assertTrue(layer.l.dtype == tl.float32)

    layer.to_dtype(tl.float64)

    dummy_data = tl.tensor(data, dtype=tl.float64)
    maximum_likelihood_estimation(layer, dummy_data)
    tc.assertTrue(layer.l.dtype == tl.float64)

    if do_for_all_backends == "numpy":
        tc.assertRaises(
            NotImplementedError,
            expectation_maximization,
            prod_node,
            tl.tensor(data, dtype=tl.float64),
            max_steps=10,
        )
    else:
        # test if em runs without error after dype change
        expectation_maximization(prod_node, tl.tensor(data, dtype=tl.float64), max_steps=10)


def test_change_device(do_for_all_backends):
    cuda = torch.device("cuda")
    np.random.seed(0)
    random.seed(0)

    layer = ExponentialLayer(scope=[Scope([0]), Scope([1])])
    prod_node = ProductNode([layer])

    # simulate data
    data = np.hstack(
        [
            np.random.exponential(scale=1.0 / 0.3, size=(20000, 1)),
            np.random.exponential(scale=1.0 / 2.7, size=(20000, 1)),
        ]
    )

    if do_for_all_backends == "numpy":
        tc.assertRaises(ValueError, layer.to_device, cuda)
        return

    # perform MLE
    maximum_likelihood_estimation(layer, tl.tensor(data, dtype=tl.float32))

    tc.assertTrue(layer.l.device.type == "cpu")

    layer.to_device(cuda)

    dummy_data = tl.tensor(data, dtype=tl.float32, device=cuda)

    # perform MLE
    maximum_likelihood_estimation(layer, dummy_data)
    tc.assertTrue(layer.l.device.type == "cuda")

    # test if em runs without error after device change
    expectation_maximization(prod_node, tl.tensor(data, dtype=tl.float32, device=cuda), max_steps=10)


if __name__ == "__main__":
    torch.set_default_dtype(torch.float32)
    unittest.main()