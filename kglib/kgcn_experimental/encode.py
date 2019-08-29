#
#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.
#

import numpy as np
import sonnet as snt
import tensorflow as tf

from kglib.kgcn_experimental.custom_nx import multidigraph_data_iterator


def augment_data_fields(graph_data_iterator, fields_to_augment, augmented_field):
    """
    Returns a graph with features built from augmenting data fields found in the graph

    Args:
        graph_data_iterator: iterator over the data for elements in a graph
        fields_to_augment: the fields of the data dictionaries to augment together
        augmented_field: the field in which to store the augmented fields

    Returns:
        None, updates the graph in-place

    """

    for data in graph_data_iterator:
        data[augmented_field] = np.hstack([np.array(data[field], dtype=float) for field in fields_to_augment])


def encode_solutions(graph, solution_field="solution", encoded_solution_field="encoded_solution",
                     encodings=np.array([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])):
    """
    Determines the encoding to use for a solution category
    Args:
        graph: Graph to update
        solution_field: The property in the graph that holds the value of the solution
        encoded_solution_field: The property in the graph to use to hold the new solution value
        encodings: An array, a row from which will be picked as the new solution based on using the current solution
            as a row index

    Returns: Graph with updated `encoded_solution_field`

    """

    for data in multidigraph_data_iterator(graph):
        solution = data[solution_field]
        data[encoded_solution_field] = encodings[solution]

    return graph


def encode_type_categorically(graph_data_iterator, all_types, type_field, category_field):
    """
    Encodes the type found in graph data as an integer according to the index it is found in `all_types`
    Args:
        graph_data_iterator: An iterator of data in the graph (node data, edge data or combined node and edge data)
        all_types: The full list of types to be encoded in this order
        type_field: The data field containing the type
        category_field: The data field to use to store the encoding

    Returns:

    """
    for data in graph_data_iterator:
        data[category_field] = all_types.index(data[type_field])


def make_mlp_model(latent_size=16, num_layers=2):
    """Instantiates a new MLP, followed by LayerNorm.

    The parameters of each new MLP are not shared with others generated by
    this function.

    Returns:
      A Sonnet module which contains the MLP and LayerNorm.
    """
    return snt.Sequential([
        snt.nets.MLP([latent_size] * num_layers, activate_final=True),
        snt.LayerNorm()
    ])


class TypeEncoder(snt.AbstractModule):
    def __init__(self, num_types, type_indicator_index, op, name='type_encoder'):
        super(TypeEncoder, self).__init__(name=name)
        self._index_of_type = type_indicator_index
        self._num_types = num_types
        with self._enter_variable_scope():
            self._op = op

    def _build(self, features):
        index = tf.cast(features[:, self._index_of_type], dtype=tf.int64)
        one_hot = tf.one_hot(index, self._num_types, on_value=1.0, off_value=0.0, axis=-1, dtype=tf.float32)
        return self._op(one_hot)


def pass_input_through_op(op):
    return lambda features: tf.concat([tf.expand_dims(tf.cast(features[:, 0], dtype=tf.float32), axis=1), op(features[:, 1:])], axis=1)
