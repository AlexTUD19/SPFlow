import random
import unittest

import numpy as np
import torch
import tensorly as tl

from spflow.torch.structure.general.nodes.leaves.parametric.log_normal import updateBackend
from spflow.base.structure.general.nodes.leaves.parametric.log_normal import LogNormal as LogNormalBase
from spflow.meta.data import FeatureContext, FeatureTypes, Scope
from spflow.tensorly.structure.autoleaf import AutoLeaf
from spflow.torch.structure.general.nodes.leaves.parametric.log_normal import LogNormal as LogNormalTorch
from spflow.tensorly.structure.general.nodes.leaves.parametric.general_log_normal import LogNormal
from spflow.torch.structure import marginalize, toBase, toTorch
from spflow.tensorly.utils.helper_functions import tl_nextafter, tl_toNumpy

tc = unittest.TestCase()

def test_initialization(do_for_all_backends):

    # Valid parameters for Log-Normal distribution: mean in (-inf,inf), std in (0,inf)

    # mean = +-inf and mean = 0
    tc.assertRaises(Exception, LogNormal, Scope([0]), np.inf, 1.0)
    tc.assertRaises(Exception, LogNormal, Scope([0]), -np.inf, 1.0)
    tc.assertRaises(Exception, LogNormal, Scope([0]), np.nan, 1.0)

    mean = random.random()

    # std <= 0
    tc.assertRaises(Exception, LogNormal, Scope([0]), mean, 0.0)
    tc.assertRaises(Exception, LogNormal, Scope([0]), mean, np.nextafter(0.0, -1.0))
    # std = +-inf and std = nan
    tc.assertRaises(Exception, LogNormal, Scope([0]), mean, np.inf)
    tc.assertRaises(Exception, LogNormal, Scope([0]), mean, -np.inf)
    tc.assertRaises(Exception, LogNormal, Scope([0]), mean, np.nan)

    # invalid scopes
    tc.assertRaises(Exception, LogNormal, Scope([]), 0.0, 1.0)
    tc.assertRaises(Exception, LogNormal, Scope([0, 1]), 0.0, 1.0)
    tc.assertRaises(Exception, LogNormal, Scope([0], [1]), 0.0, 1.0)

def test_structural_marginalization(do_for_all_backends):

    log_normal = LogNormal(Scope([0]), 0.0, 1.0)

    tc.assertTrue(marginalize(log_normal, [1]) is not None)
    tc.assertTrue(marginalize(log_normal, [0]) is None)

def test_accept(do_for_all_backends):

    # continuous meta type
    tc.assertTrue(LogNormal.accepts([FeatureContext(Scope([0]), [FeatureTypes.Continuous])]))

    # LogNormal feature type class
    tc.assertTrue(LogNormal.accepts([FeatureContext(Scope([0]), [FeatureTypes.LogNormal])]))

    # LogNormal feature type instance
    tc.assertTrue(LogNormal.accepts([FeatureContext(Scope([0]), [FeatureTypes.LogNormal(0.0, 1.0)])]))

    # invalid feature type
    tc.assertFalse(LogNormal.accepts([FeatureContext(Scope([0]), [FeatureTypes.Discrete])]))

    # conditional scope
    tc.assertFalse(LogNormal.accepts([FeatureContext(Scope([0], [1]), [FeatureTypes.Continuous])]))

    # multivariate signature
    tc.assertFalse(
        LogNormal.accepts(
            [
                FeatureContext(
                    Scope([0, 1]),
                    [FeatureTypes.Continuous, FeatureTypes.Continuous],
                )
            ]
        )
    )

def test_initialization_from_signatures(do_for_all_backends):

    log_normal = LogNormal.from_signatures([FeatureContext(Scope([0]), [FeatureTypes.Continuous])])
    tc.assertTrue(np.isclose(tl_toNumpy(log_normal.mean), tl.tensor(0.0)))
    tc.assertTrue(np.isclose(tl_toNumpy(log_normal.std), tl.tensor(1.0)))

    log_normal = LogNormal.from_signatures([FeatureContext(Scope([0]), [FeatureTypes.LogNormal])])
    tc.assertTrue(np.isclose(tl_toNumpy(log_normal.mean), tl.tensor(0.0)))
    tc.assertTrue(np.isclose(tl_toNumpy(log_normal.std), tl.tensor(1.0)))

    log_normal = LogNormal.from_signatures([FeatureContext(Scope([0]), [FeatureTypes.LogNormal(-1.0, 1.5)])])
    tc.assertTrue(np.isclose(tl_toNumpy(log_normal.mean), tl.tensor(-1.0)))
    tc.assertTrue(np.isclose(tl_toNumpy(log_normal.std), tl.tensor(1.5)))

    # ----- invalid arguments -----

    # invalid feature type
    tc.assertRaises(
        ValueError,
        LogNormal.from_signatures,
        [FeatureContext(Scope([0]), [FeatureTypes.Discrete])],
    )

    # conditional scope
    tc.assertRaises(
        ValueError,
        LogNormal.from_signatures,
        [FeatureContext(Scope([0], [1]), [FeatureTypes.Continuous])],
    )

    # multivariate signature
    tc.assertRaises(
        ValueError,
        LogNormal.from_signatures,
        [
            FeatureContext(
                Scope([0, 1]),
                [FeatureTypes.Continuous, FeatureTypes.Continuous],
            )
        ],
    )

def test_autoleaf(do_for_all_backends):

    if tl.get_backend() == "numpy":
        LogNormalInst = LogNormalBase
    elif tl.get_backend() == "pytorch":
        LogNormalInst = LogNormalTorch
    else:
        raise NotImplementedError("This test is not implemented for this backend")

    # make sure leaf is registered
    tc.assertTrue(AutoLeaf.is_registered(LogNormal))

    # make sure leaf is correctly inferred
    tc.assertEqual(
        LogNormal,
        AutoLeaf.infer([FeatureContext(Scope([0]), [FeatureTypes.LogNormal])]),
    )

    # make sure AutoLeaf can return correctly instantiated object
    log_normal = AutoLeaf([FeatureContext(Scope([0]), [FeatureTypes.LogNormal(mean=-1.0, std=0.5)])])
    tc.assertTrue(isinstance(log_normal, LogNormalInst))
    tc.assertTrue(np.isclose(tl_toNumpy(log_normal.mean), tl.tensor(-1.0)))
    tc.assertTrue(np.isclose(tl_toNumpy(log_normal.std), tl.tensor(0.5)))

def test_update_backend(do_for_all_backends):
    backends = ["numpy", "pytorch"]
    mean = random.random()
    std = random.random() + 1e-7  # offset by small number to avoid zero
    log_normal = LogNormal(Scope([0]), mean, std)
    for backend in backends:
        with tl.backend_context(backend):
            log_normal_updated = updateBackend(log_normal)

            # check conversion from torch to python
            tc.assertTrue(
                np.allclose(
                    np.array([*log_normal.get_params()]),
                    np.array([*log_normal_updated.get_params()]),
                )
            )


if __name__ == "__main__":
    torch.set_default_dtype(torch.float64)
    unittest.main()
