from abc import ABC
import torch as t
import numpy as np
import json
from .Train import load_FastText
from .Model import ValuePredictionModel
from .TraceReader import NameEntry, CallEntry, AttributeEntry, BinOpEntry
from .TensorFactory import TensorFactory, Embedding
from .Util import dtype, device
from .Hyperparams import Hyperparams as p


class ValuePredictor(ABC):
    def __init__(self):
        p.batch_size = 1

        # load model
        print("Loading value prediction model")
        self.model = ValuePredictionModel()
        self.model.load_state_dict(t.load("data/models/default"))
        print(f"Loaded model: {self.model}")

        # load embedding
        ft = load_FastText(
            "data/embeddings/default/embedding")
        self.token_embedding = Embedding(ft)

        self.tensor_factory = TensorFactory()

        with open("data/tensors/value_map.json") as f:
            value_to_index = json.load(f)
            self.index_to_value = {i: v for v, i in value_to_index.items()}

    def __query_model(self, entry):
        kind, name, args, base, left, right, operator = self.tensor_factory.entry_to_tensors(
            entry, self.token_embedding)
        xs_kind = t.tensor(np.array([kind]), dtype=dtype, device=device)
        xs_name = t.tensor(np.array([name]), dtype=dtype, device=device)
        xs_args = t.tensor(np.array([args]), dtype=dtype, device=device)
        xs_base = t.tensor(np.array([base]), dtype=dtype, device=device)
        xs_left = t.tensor(np.array([left]), dtype=dtype, device=device)
        xs_right = t.tensor(np.array([right]), dtype=dtype, device=device)
        xs_operator = t.tensor(
            np.array([operator]), dtype=dtype, device=device)
        pred_ys = self.model((xs_kind, xs_name, xs_args,
                             xs_base, xs_left, xs_right, xs_operator))
        print(f"Predicted values: {pred_ys}")
        max_index = t.argmax(pred_ys[0]).item()
        predicted_value = self.index_to_value[max_index]
        return predicted_value

    def name(self, iid, name):
        entry = NameEntry(iid, name, None)
        return self.__query_model(entry)

    def call(self, iid, fct, *args, **kwargs):
        entry = CallEntry(iid, fct, args, None)
        pass

    def attribute(self, iid, base, attr_name):
        pass

    def binary_operation(self, iid, left, operator, right):
        pass


if __name__ == "__main__":
    vp = ValuePredictor()
    v = vp.name(23, "first_name")
    print(f"Predicted value: {v} with type {type(v)}")
