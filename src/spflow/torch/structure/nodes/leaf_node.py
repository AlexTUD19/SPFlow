"""Contains the basic abstract ``LeafNode`` module that all leaf nodes for SPFlow in the ``torch`` backend.

All leaf nodes in the ``torch`` backend should inherit from ``LeafNode`` or a subclass of it.
"""
from spflow.meta.data.scope import Scope
from spflow.torch.structure.nodes.node import Node

from abc import ABC


class LeafNode(Node, ABC):
    """Abstract base class for leaf nodes in the ``torch`` backend.

    All valid SPFlow leaf nodes in the 'base' backend should inherit from this class or a subclass of it.

    Attributes:
        n_out:
            Integer indicating the number of outputs. One for nodes.
        scopes_out:
            List of scopes representing the output scopes.
    """

    def __init__(self, scope: Scope, **kwargs) -> None:
        """Initializes 'LeafNode' object.

        Args:
            scope:
                Scope object representing the scope of the leaf node,
        """
        super(LeafNode, self).__init__(children=[], **kwargs)

        self.scope = scope