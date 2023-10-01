import random
import unittest
from typing import Callable

import numpy as np
import torch
import tensorly as tl
from spflow.base.structure.general.nodes.leaves.parametric.cond_exponential import CondExponential as CondExponentialBase
from spflow.torch.structure.general.nodes.leaves.parametric.cond_exponential import updateBackend
from spflow.meta.data import Scope
from spflow.meta.data.feature_context import FeatureContext
from spflow.meta.data.feature_types import FeatureTypes
from spflow.meta.dispatch.dispatch_context import DispatchContext
from spflow.tensorly.structure.autoleaf import AutoLeaf
from spflow.torch.structure.general.nodes.leaves.parametric.cond_exponential import CondExponential as CondExponentialTorch
from spflow.tensorly.structure.general.nodes.leaves.parametric.general_cond_exponential import CondExponential
from spflow.torch.structure.spn.nodes.sum_node import marginalize
from spflow.tensorly.utils.helper_functions import tl_nextafter, tl_toNumpy

tc = unittest.TestCase()

def test_initialization(do_for_all_backends):

    exponential = CondExponential(Scope([0], [1]))
    tc.assertTrue(exponential.cond_f is None)
    exponential = CondExponential(Scope([0], [1]), lambda x: {"l": 0.5})
    tc.assertTrue(isinstance(exponential.cond_f, Callable))

    # invalid scopes
    tc.assertRaises(Exception, CondExponential, Scope([]))
    tc.assertRaises(Exception, CondExponential, Scope([0, 1], [2]))
    tc.assertRaises(Exception, CondExponential, Scope([0]))

def test_retrieve_params(do_for_all_backends):

    # Valid parameters for Exponential distribution: l>0

    exponential = CondExponential(Scope([0], [1]))

    # l > t
    exponential.set_cond_f(lambda data: {"l": tl_nextafter(tl.tensor(0.0), tl.tensor(1.0))})
    tc.assertTrue(
        exponential.retrieve_params(np.array([[1.0]]), DispatchContext())
        == tl_nextafter(tl.tensor(0.0), tl.tensor(1.0))
    )

    # l = 0 and l < 0
    exponential.set_cond_f(lambda data: {"l": tl.tensor(0.0)})
    tc.assertRaises(
        Exception,
        exponential.retrieve_params,
        np.array([[1.0]]),
        DispatchContext(),
    )

    exponential.set_cond_f(lambda data: {"l": tl_nextafter(tl.tensor(0.0), tl.tensor(-1.0))})
    tc.assertRaises(
        Exception,
        exponential.retrieve_params,
        np.array([[1.0]]),
        DispatchContext(),
    )

    # l = inf and l = nan
    exponential.set_cond_f(lambda data: {"l": tl.tensor(float("inf"))})
    tc.assertRaises(
        Exception,
        exponential.retrieve_params,
        np.array([[1.0]]),
        DispatchContext(),
    )
    exponential.set_cond_f(lambda data: {"l": tl.tensor(float("nan"))})
    tc.assertRaises(
        Exception,
        exponential.retrieve_params,
        np.array([[1.0]]),
        DispatchContext(),
    )

def test_accept(do_for_all_backends):

    # continuous meta type
    tc.assertTrue(CondExponential.accepts([FeatureContext(Scope([0], [1]), [FeatureTypes.Continuous])]))

    # Exponential feature type class
    tc.assertTrue(CondExponential.accepts([FeatureContext(Scope([0], [1]), [FeatureTypes.Exponential])]))

    # Exponential feature type instance
    tc.assertTrue(CondExponential.accepts([FeatureContext(Scope([0], [1]), [FeatureTypes.Exponential(1.0)])]))

    # invalid feature type
    tc.assertFalse(CondExponential.accepts([FeatureContext(Scope([0], [1]), [FeatureTypes.Discrete])]))

    # non-conditional scope
    tc.assertFalse(CondExponential.accepts([FeatureContext(Scope([0]), [FeatureTypes.Continuous])]))

    # multivariate signature
    tc.assertFalse(
        CondExponential.accepts(
            [
                FeatureContext(
                    Scope([0, 1], [2]),
                    [FeatureTypes.Continuous, FeatureTypes.Continuous],
                )
            ]
        )
    )

def test_initialization_from_signatures(do_for_all_backends):

    CondExponential.from_signatures([FeatureContext(Scope([0], [1]), [FeatureTypes.Continuous])])
    CondExponential.from_signatures([FeatureContext(Scope([0], [1]), [FeatureTypes.Exponential])])
    CondExponential.from_signatures([FeatureContext(Scope([0], [1]), [FeatureTypes.Exponential(l=1.5)])])

    # ----- invalid arguments -----

    # invalid feature type
    tc.assertRaises(
        ValueError,
        CondExponential.from_signatures,
        [FeatureContext(Scope([0], [1]), [FeatureTypes.Discrete])],
    )

    # non-conditional scope
    tc.assertRaises(
        ValueError,
        CondExponential.from_signatures,
        [FeatureContext(Scope([0]), [FeatureTypes.Continuous])],
    )

    # multivariate signature
    tc.assertRaises(
        ValueError,
        CondExponential.from_signatures,
        [
            FeatureContext(
                Scope([0, 1], [2]),
                [FeatureTypes.Continuous, FeatureTypes.Continuous],
            )
        ],
    )

def test_autoleaf(do_for_all_backends):

    if tl.get_backend() == "numpy":
        CondExponentialInst = CondExponentialBase
    elif tl.get_backend() == "pytorch":
        CondExponentialInst = CondExponentialTorch
    else:
        raise NotImplementedError("This test is not implemented for this backend")

    # make sure leaf is registered
    tc.assertTrue(AutoLeaf.is_registered(CondExponential))

    # make sure leaf is correctly inferred
    tc.assertEqual(
        CondExponential,
        AutoLeaf.infer([FeatureContext(Scope([0], [1]), [FeatureTypes.Exponential])]),
    )

    # make sure AutoLeaf can return correctly instantiated object
    exponential = AutoLeaf([FeatureContext(Scope([0], [1]), [FeatureTypes.Exponential])])
    tc.assertTrue(isinstance(exponential, CondExponentialInst))

def test_structural_marginalization(do_for_all_backends):

    exponential = CondExponential(Scope([0], [1]), 1.0)

    tc.assertTrue(marginalize(exponential, [1]) is not None)
    tc.assertTrue(marginalize(exponential, [0]) is None)

def test_update_backend(do_for_all_backends):
    backends = ["numpy", "pytorch"]
    cond_exponential = CondExponential(Scope([0], [1]))
    for backend in backends:
        with tl.backend_context(backend):
            cond_exponential_updated = updateBackend(cond_exponential)

            # check conversion from torch to python
            tc.assertTrue(np.all(cond_exponential.scopes_out == cond_exponential_updated.scopes_out))

if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
