#!/usr/bin/env python3


class LinearOperatorRepresentationTree(object):
    def __init__(self, linear_op):
        self._cls = linear_op.__class__
        self._kwargs = linear_op._kwargs

        counter = 0
        self.children = []
        for arg in linear_op._args:
            if hasattr(arg, "representation") and callable(arg.representation):  # Is it a lazy tensor?
                representation_size = len(arg.representation())
                self.children.append(
                    (
                        slice(counter, counter + representation_size, None),
                        arg.representation_tree(),
                    )
                )
                counter += representation_size
            else:
                self.children.append((counter, None))
                counter += 1

    def __call__(self, *flattened_representation):
        unflattened_representation = []

        for index, subtree in self.children:
            if subtree is None:
                unflattened_representation.append(flattened_representation[index])
            else:
                sub_representation = flattened_representation[index]
                unflattened_representation.append(subtree(*sub_representation))

        return self._cls(*unflattened_representation, **self._kwargs)
