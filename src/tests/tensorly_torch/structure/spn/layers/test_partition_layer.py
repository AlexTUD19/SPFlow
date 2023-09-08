import itertools
import unittest

import numpy as np
import torch
import tensorly as tl

from spflow.base.structure.spn import Gaussian as BaseGaussian
from spflow.base.structure.spn import PartitionLayer as BasePartitionLayer
from spflow.meta.data import Scope
#from spflow.torch.structure import marginalize, toBase, toTorch
from spflow.tensorly.structure import marginalize
from spflow.tensorly.structure.general.nodes.leaves.parametric.general_gaussian import Gaussian
from spflow.tensorly.structure.spn import PartitionLayer
from spflow.tensorly.structure.spn.layers.partition_layer import toLayerBased, toNodeBased
from spflow.tensorly.structure.spn.layers_layerbased.partition_layer import toLayerBased, toNodeBased, updateBackend

from ...general.nodes.dummy_node import DummyNode


class TestNode(unittest.TestCase):
    def test_partition_layer_initialization(self):

        # dummy partitios over pair-wise disjont scopes
        input_partitions = [
            [DummyNode(Scope([0])), DummyNode(Scope([0]))],
            [
                DummyNode(Scope([1, 3])),
                DummyNode(Scope([1, 3])),
                DummyNode(Scope([1, 3])),
            ],
            [DummyNode(Scope([2]))],
        ]

        # ----- check attributes after correct initialization -----

        l = PartitionLayer(child_partitions=input_partitions)
        # make sure number of creates nodes is correct
        self.assertEqual(l.n_out, np.prod([len(partition) for partition in input_partitions]))
        # make sure scopes are correct
        self.assertTrue(np.all(l.scopes_out == [Scope([0, 1, 2, 3]) for _ in range(l.n_out)]))
        # make sure order of nodes is correct (important)
        for indices, indices_torch in zip(
            itertools.product([0, 1], [2, 3, 4], [5]),
            torch.cartesian_prod(torch.tensor([0, 1]), torch.tensor([2, 3, 4]), torch.tensor([5])),
        ):
            self.assertTrue(torch.all(torch.tensor(indices) == indices_torch))

        # ----- no child partitions -----
        self.assertRaises(ValueError, PartitionLayer, [])

        # ----- empty partition -----
        self.assertRaises(ValueError, PartitionLayer, [[]])

        # ----- scopes inside partition differ -----
        self.assertRaises(
            ValueError,
            PartitionLayer,
            [
                [DummyNode(Scope([0]))],
                [DummyNode(Scope([1])), DummyNode(Scope([2]))],
            ],
        )

        # ----- partitions of non-pair-wise disjoint scopes -----
        self.assertRaises(
            ValueError,
            PartitionLayer,
            [
                [DummyNode(Scope([0]))],
                [DummyNode(Scope([0])), DummyNode(Scope([0]))],
            ],
        )

    def test_partition_layer_structural_marginalization(self):

        # dummy partitios over pair-wise disjont scopes
        input_partitions = [
            [DummyNode(Scope([0])), DummyNode(Scope([0]))],
            [
                DummyNode(Scope([1, 3])),
                DummyNode(Scope([1, 3])),
                DummyNode(Scope([1, 3])),
            ],
            [DummyNode(Scope([2]))],
        ]

        l = PartitionLayer(child_partitions=input_partitions)
        # should marginalize entire module
        l_marg = marginalize(l, [0, 1, 2, 3])
        self.assertTrue(l_marg is None)
        # should marginalize entire partition
        l_marg = marginalize(l, [2])
        self.assertTrue(l_marg.scope == Scope([0, 1, 3]))
        # should partially marginalize one partition
        l_marg = marginalize(l, [3])
        self.assertTrue(l_marg.scope == Scope([0, 1, 2]))

        # ----- pruning -----
        l = PartitionLayer(child_partitions=input_partitions[1:])

        l_marg = marginalize(l, [1, 3], prune=True)
        self.assertTrue(isinstance(l_marg, DummyNode))
    """
    def test_partition_layer_backend_conversion_1(self):

        torch_partition_layer = PartitionLayer(
            child_partitions=[
                [Gaussian(Scope([0])), Gaussian(Scope([0]))],
                [Gaussian(Scope([1]))],
                [
                    Gaussian(Scope([2])),
                    Gaussian(Scope([2])),
                    Gaussian(Scope([2])),
                ],
            ]
        )

        base_partition_layer = toBase(torch_partition_layer)
        self.assertEqual(base_partition_layer.n_out, torch_partition_layer.n_out)
    
    def test_partition_layer_backend_conversion_2(self):

        base_partition_layer = BasePartitionLayer(
            child_partitions=[
                [BaseGaussian(Scope([0])), BaseGaussian(Scope([0]))],
                [BaseGaussian(Scope([1]))],
                [
                    BaseGaussian(Scope([2])),
                    BaseGaussian(Scope([2])),
                    BaseGaussian(Scope([2])),
                ],
            ]
        )

        torch_partition_layer = toTorch(base_partition_layer)
        self.assertEqual(base_partition_layer.n_out, torch_partition_layer.n_out)
    """
    def test_sum_layer_layerbased_conversion(self):

        partition_layer = PartitionLayer(
            child_partitions=[
                [Gaussian(Scope([0])), Gaussian(Scope([0]))],
                [Gaussian(Scope([1]))],
                [
                    Gaussian(Scope([2])),
                    Gaussian(Scope([2])),
                    Gaussian(Scope([2])),
                ],
            ]
        )

        layer_based_partition_layer = toLayerBased(partition_layer)
        self.assertEqual(layer_based_partition_layer.n_out, partition_layer.n_out)
        node_based_partition_layer = toNodeBased(layer_based_partition_layer)
        self.assertEqual(node_based_partition_layer.n_out, partition_layer.n_out)

        node_based_partition_layer2 = toNodeBased(partition_layer)
        self.assertEqual(node_based_partition_layer2.n_out, partition_layer.n_out)
        layer_based_partition_layer2 = toLayerBased(layer_based_partition_layer)
        self.assertEqual(layer_based_partition_layer2.n_out, partition_layer.n_out)

    def test_update_backend(self):
        backends = ["numpy", "pytorch"]
        partition_layer = PartitionLayer(
            child_partitions=[
                [Gaussian(Scope([0])), Gaussian(Scope([0]))],
                [Gaussian(Scope([1]))],
                [
                    Gaussian(Scope([2])),
                    Gaussian(Scope([2])),
                    Gaussian(Scope([2])),
                ],
            ]
        )
        n_out = partition_layer.n_out
        for backend in backends:
            tl.set_backend(backend)
            partition_layer_updated = updateBackend(partition_layer)
            self.assertTrue(n_out == partition_layer_updated.n_out)


if __name__ == "__main__":
    unittest.main()
