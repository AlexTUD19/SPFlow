import unittest

import tensorly as tl

from spflow.tensorly.structure.spn.rat.region_graph import random_region_graph
from spflow.meta.data import Scope
from spflow.meta.data.feature_context import FeatureContext
from spflow.meta.data.feature_types import FeatureTypes
from spflow.tensorly.structure.spn.rat.rat_spn import updateBackend
from spflow.tensorly.structure.autoleaf import (
    AutoLeaf,
    Bernoulli,
    BernoulliLayer,
    Binomial,
    BinomialLayer,
    CondBernoulli,
    CondBernoulliLayer,
    CondBinomial,
    CondBinomialLayer,
    CondExponential,
    CondExponentialLayer,
    CondGamma,
    CondGammaLayer,
    CondGaussian,
    CondGaussianLayer,
    CondGeometric,
    CondGeometricLayer,
    CondLogNormal,
    CondLogNormalLayer,
    CondMultivariateGaussian,
    CondMultivariateGaussianLayer,
    CondNegativeBinomial,
    CondNegativeBinomialLayer,
    CondPoisson,
    CondPoissonLayer,
    Exponential,
    ExponentialLayer,
    Gamma,
    GammaLayer,
    Gaussian,
    GaussianLayer,
    Geometric,
    GeometricLayer,
    Hypergeometric,
    HypergeometricLayer,
    LogNormal,
    LogNormalLayer,
    MultivariateGaussian,
    MultivariateGaussianLayer,
    NegativeBinomial,
    NegativeBinomialLayer,
    Poisson,
    PoissonLayer,
    Uniform,
    UniformLayer,
)
from spflow.tensorly.structure.spn.layers.cond_sum_layer import CondSumLayer, marginalize
from spflow.tensorly.structure.spn.layers.hadamard_layer import HadamardLayer, marginalize
from spflow.tensorly.structure.spn.layers.partition_layer import (
    PartitionLayer,
    marginalize,
)
from spflow.tensorly.structure.spn.layers.sum_layer import SumLayer, marginalize
from spflow.tensorly.structure.spn.nodes.cond_sum_node import (
    CondSumNode,
    marginalize,
    #toBase,
    #toTorch,
)
from spflow.tensorly.structure.spn.nodes.sum_node import (
    SumNode,
    marginalize,
    #toBase,
    #toTorch,
)
from spflow.tensorly.structure.spn.rat.rat_spn import RatSPN, marginalize#, toBase, toTorch
from spflow.torch.structure.general.nodes.leaves.parametric.gaussian import Gaussian as TorchGaussian
from spflow.torch.structure.general.layers.leaves.parametric.gaussian import GaussianLayer as TorchGaussianLayer
from spflow.base.structure.general.nodes.leaves.parametric.gaussian import Gaussian as Gaussian
from spflow.base.structure.general.layers.leaves.parametric.gaussian import GaussianLayer as GaussianLayer

leaf_node_classes = (
    Bernoulli,
    Binomial,
    Exponential,
    Gamma,
    Gaussian,
    TorchGaussian,
    Geometric,
    Hypergeometric,
    LogNormal,
    MultivariateGaussian,
    NegativeBinomial,
    Poisson,
    Uniform,
    CondBernoulli,
    CondBinomial,
    CondExponential,
    CondGamma,
    CondGaussian,
    CondGeometric,
    CondLogNormal,
    CondMultivariateGaussian,
    CondNegativeBinomial,
    CondPoisson,
)

leaf_layer_classes = (
    BernoulliLayer,
    BinomialLayer,
    ExponentialLayer,
    GammaLayer,
    GaussianLayer,
    TorchGaussianLayer,
    GeometricLayer,
    HypergeometricLayer,
    LogNormalLayer,
    MultivariateGaussianLayer,
    NegativeBinomialLayer,
    PoissonLayer,
    UniformLayer,
    CondBernoulliLayer,
    CondBinomialLayer,
    CondExponentialLayer,
    CondGammaLayer,
    CondGaussianLayer,
    CondGeometricLayer,
    CondLogNormalLayer,
    CondMultivariateGaussianLayer,
    CondNegativeBinomialLayer,
    CondPoissonLayer,
)


def get_rat_spn_properties(rat_spn: RatSPN):

    n_sum_nodes = 1  # root node
    n_product_nodes = 0
    n_leaf_nodes = 0

    layers = [rat_spn.root_region]

    while layers:
        layer = layers.pop()

        # internal region
        if isinstance(layer, (SumLayer, CondSumLayer)):
            n_sum_nodes += layer.n_out
            layers += list(layer.children)
        # partition
        elif isinstance(layer, PartitionLayer):
            n_product_nodes += layer.n_out
            layers += list(layer.children)
        # multivariate leaf region
        elif isinstance(layer, HadamardLayer):
            n_product_nodes += layer.n_out
            layers += list(layer.children)
        # leaf node
        elif isinstance(layer, leaf_node_classes):
            n_leaf_nodes += 1
            layers += list(layer.children)
        # leaf layer
        elif isinstance(layer, leaf_layer_classes):
            n_leaf_nodes += layer.n_out
            layers += list(layer.children)
        else:
            raise TypeError(f"Encountered unknown layer of type {type(layer)}.")

        #layers += list(layer.children)

    return n_sum_nodes, n_product_nodes, n_leaf_nodes

tc = unittest.TestCase()

def test_rat_spn_initialization(do_for_all_backends):

    random_variables = list(range(7))
    scope = Scope(random_variables)
    region_graph = random_region_graph(scope, depth=2, replicas=1)
    feature_ctx = FeatureContext(scope, {rv: FeatureTypes.Gaussian for rv in scope.query})

    tc.assertRaises(
        ValueError,
        RatSPN,
        region_graph,
        feature_ctx,
        n_root_nodes=0,
        n_region_nodes=1,
        n_leaf_nodes=1,
    )
    tc.assertRaises(
        ValueError,
        RatSPN,
        region_graph,
        feature_ctx,
        n_root_nodes=1,
        n_region_nodes=0,
        n_leaf_nodes=1,
    )
    tc.assertRaises(
        ValueError,
        RatSPN,
        region_graph,
        feature_ctx,
        n_root_nodes=1,
        n_region_nodes=1,
        n_leaf_nodes=0,
    )

    RatSPN(
        region_graph,
        feature_ctx,
        n_root_nodes=1,
        n_region_nodes=1,
        n_leaf_nodes=1,
    )

def test_rat_spn_1(do_for_all_backends):

    random_variables = list(range(7))
    scope = Scope(random_variables)
    region_graph = random_region_graph(scope, depth=2, replicas=1)
    feature_ctx = FeatureContext(scope, {rv: FeatureTypes.Gaussian for rv in scope.query})

    rat_spn = RatSPN(
        region_graph,
        feature_ctx,
        n_root_nodes=1,
        n_region_nodes=1,
        n_leaf_nodes=1,
    )

    n_sum_nodes, n_product_nodes, n_leaf_nodes = get_rat_spn_properties(rat_spn)
    tc.assertEqual(n_sum_nodes, 4)
    tc.assertEqual(n_product_nodes, 6)
    tc.assertEqual(n_leaf_nodes, 7)

def test_rat_spn_2(do_for_all_backends):

    random_variables = list(range(7))
    scope = Scope(random_variables)
    region_graph = random_region_graph(scope, depth=3, replicas=1)
    feature_ctx = FeatureContext(scope, {rv: FeatureTypes.Gaussian for rv in scope.query})

    rat_spn = RatSPN(
        region_graph,
        feature_ctx,
        n_root_nodes=1,
        n_region_nodes=1,
        n_leaf_nodes=1,
    )

    n_sum_nodes, n_product_nodes, n_leaf_nodes = get_rat_spn_properties(rat_spn)
    tc.assertEqual(n_sum_nodes, 7)
    tc.assertEqual(n_product_nodes, 6)
    tc.assertEqual(n_leaf_nodes, 7)

def test_rat_spn_3(do_for_all_backends):

    random_variables = list(range(7))
    scope = Scope(random_variables)
    region_graph = random_region_graph(scope, depth=3, replicas=2)
    feature_ctx = FeatureContext(scope, {rv: FeatureTypes.Gaussian for rv in scope.query})

    rat_spn = RatSPN(
        region_graph,
        feature_ctx,
        n_root_nodes=2,
        n_region_nodes=2,
        n_leaf_nodes=2,
    )

    n_sum_nodes, n_product_nodes, n_leaf_nodes = get_rat_spn_properties(rat_spn)
    tc.assertEqual(n_sum_nodes, 23)
    tc.assertEqual(n_product_nodes, 48)
    tc.assertEqual(n_leaf_nodes, 28)

def test_rat_spn_4(do_for_all_backends):

    random_variables = list(range(7))
    scope = Scope(random_variables)
    region_graph = random_region_graph(scope, depth=3, replicas=3)
    feature_ctx = FeatureContext(scope, {rv: FeatureTypes.Gaussian for rv in scope.query})

    rat_spn = RatSPN(
        region_graph,
        feature_ctx,
        n_root_nodes=3,
        n_region_nodes=3,
        n_leaf_nodes=3,
    )

    n_sum_nodes, n_product_nodes, n_leaf_nodes = get_rat_spn_properties(rat_spn)
    tc.assertEqual(n_sum_nodes, 49)
    tc.assertEqual(n_product_nodes, 162)
    tc.assertEqual(n_leaf_nodes, 63)

def test_rat_spn_5(do_for_all_backends):

    random_variables = list(range(7))
    scope = Scope(random_variables)
    region_graph = random_region_graph(scope, depth=2, replicas=1, n_splits=3)
    feature_ctx = FeatureContext(scope, {rv: FeatureTypes.Gaussian for rv in scope.query})

    rat_spn = RatSPN(
        region_graph,
        feature_ctx,
        n_root_nodes=1,
        n_region_nodes=1,
        n_leaf_nodes=1,
    )

    n_sum_nodes, n_product_nodes, n_leaf_nodes = get_rat_spn_properties(rat_spn)
    tc.assertEqual(n_sum_nodes, 3)
    tc.assertEqual(n_product_nodes, 4)
    tc.assertEqual(n_leaf_nodes, 7)

def test_rat_spn_6(do_for_all_backends):

    random_variables = list(range(9))
    scope = Scope(random_variables)
    region_graph = random_region_graph(scope, depth=3, replicas=1, n_splits=3)
    feature_ctx = FeatureContext(scope, {rv: FeatureTypes.Gaussian for rv in scope.query})

    rat_spn = RatSPN(
        region_graph,
        feature_ctx,
        n_root_nodes=1,
        n_region_nodes=1,
        n_leaf_nodes=1,
    )

    n_sum_nodes, n_product_nodes, n_leaf_nodes = get_rat_spn_properties(rat_spn)
    tc.assertEqual(n_sum_nodes, 5)
    tc.assertEqual(n_product_nodes, 4)
    tc.assertEqual(n_leaf_nodes, 9)

def test_rat_spn_7(do_for_all_backends):

    random_variables = list(range(7))
    scope = Scope(random_variables)
    region_graph = random_region_graph(scope, depth=2, replicas=2, n_splits=3)
    feature_ctx = FeatureContext(scope, {rv: FeatureTypes.Gaussian for rv in scope.query})

    rat_spn = RatSPN(
        region_graph,
        feature_ctx,
        n_root_nodes=2,
        n_region_nodes=2,
        n_leaf_nodes=2,
    )

    n_sum_nodes, n_product_nodes, n_leaf_nodes = get_rat_spn_properties(rat_spn)
    tc.assertEqual(n_sum_nodes, 7)
    tc.assertEqual(n_product_nodes, 40)
    tc.assertEqual(n_leaf_nodes, 28)

def test_rat_spn_8(do_for_all_backends):

    random_variables = list(range(20))
    scope = Scope(random_variables)
    region_graph = random_region_graph(scope, depth=3, replicas=3, n_splits=3)
    feature_ctx = FeatureContext(scope, {rv: FeatureTypes.Gaussian for rv in scope.query})

    rat_spn = RatSPN(
        region_graph,
        feature_ctx,
        n_root_nodes=3,
        n_region_nodes=3,
        n_leaf_nodes=2,
    )

    n_sum_nodes, n_product_nodes, n_leaf_nodes = get_rat_spn_properties(rat_spn)
    tc.assertEqual(n_sum_nodes, 49)
    tc.assertEqual(n_product_nodes, 267)
    tc.assertEqual(n_leaf_nodes, 120)

def test_conditional_rat(do_for_all_backends):

    random_variables = list(range(7))
    scope = Scope(random_variables, [7])  # conditional scope
    region_graph = random_region_graph(scope, depth=2, replicas=1)
    feature_ctx = FeatureContext(scope, {rv: FeatureTypes.Gaussian for rv in scope.query})

    rat_spn = RatSPN(
        region_graph,
        feature_ctx,
        n_root_nodes=1,
        n_region_nodes=1,
        n_leaf_nodes=1,
    )

    tc.assertTrue(isinstance(rat_spn.root_node, CondSumNode))
    tc.assertTrue(isinstance(rat_spn.root_region, CondSumLayer))

def test_update_backend(do_for_all_backends):
    backends = ["numpy", "pytorch"]
    random_variables = list(range(7))
    scope = Scope(random_variables)
    region_graph = random_region_graph(scope, depth=2, replicas=1)
    feature_ctx = FeatureContext(scope, {rv: FeatureTypes.Gaussian for rv in scope.query})

    rat_spn = RatSPN(
        region_graph,
        feature_ctx,
        n_root_nodes=1,
        n_region_nodes=1,
        n_leaf_nodes=1,
    )

    n_sum_nodes, n_product_nodes, n_leaf_nodes = get_rat_spn_properties(rat_spn)
    for backend in backends:
        with tl.backend_context(backend):
            rat_spn_updated = updateBackend(rat_spn)
            n_sum_nodes_up, n_product_nodes_up, n_leaf_nodes_up = get_rat_spn_properties(rat_spn_updated)
            tc.assertEqual(n_sum_nodes,n_sum_nodes_up)
            tc.assertEqual(n_product_nodes,n_product_nodes_up)
            tc.assertEqual(n_leaf_nodes, n_leaf_nodes_up)

if __name__ == "__main__":
    unittest.main()
