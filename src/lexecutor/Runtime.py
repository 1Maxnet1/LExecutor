import atexit
import sys
from .IIDs import IIDs
from .TraceWriter import TraceWriter
from .ValueAbstraction import restore_value
from .predictors.NaiveValuePredictor import NaiveValuePredictor
from .predictors.FrequencyValuePredictor import FrequencyValuePredictor
from .predictors.feedforward.NeuralValuePredictor import NeuralValuePredictor
from .predictors.codet5.CodeT5ValuePredictor import CodeT5ValuePredictor
from .RuntimeStats import RuntimeStats
from .Util import timestamp
from .predictors.ValuePredictor import ValuePredictor
from .predictors.AsIs import AsIs


# ------- begin: select mode -----
# mode = "RECORD"    # record values and write into a trace file
mode = "PREDICT"   # predict and inject values if missing in exeuction
# mode = "REPLAY"  # replay a previously recorded trace (mostly for testing)
# ------- end: select mode -------

if mode == "RECORD":
    trace = TraceWriter(f"trace_{timestamp()}.h5")
    atexit.register(lambda: trace.write_to_file())
    runtime_stats = None
elif mode == "PREDICT":
    # predictor = AsIs()
    # predictor = NaiveValuePredictor()
    # predictor = FrequencyValuePredictor("/home/beatriz/LExecutor/all_training_traces.txt")
    # predictor = NeuralValuePredictor()
    iids = IIDs('iids_original.json')
    runtime_stats = RuntimeStats(iids)
    atexit.register(runtime_stats.print)
    predictor = CodeT5ValuePredictor(iids, runtime_stats)

    # for running experiments
    file = sys.argv[0]
    atexit.register(runtime_stats.save, file, predictor.__class__.__name__)
elif mode == "REPLAY":
    with open("trace.out", "r") as file:
        trace = file.readlines()
    next_trace_idx = 0
    runtime_stats = None

verbose = True

print(f"### LExecutor running in {mode} mode ###")


def _n_(iid, name, lambada):
    if verbose:
        print(f"\nAt iid={iid}, looking up name '{name}'")

    if runtime_stats is not None:
        runtime_stats.total_uses += 1
        runtime_stats.cover_iid(iid)

    perform_fct = lambada

    def record_fct(v):
        trace.append_name(iid, name, v)

    def predict_fct():
        return predictor.name(iid, name)

    return mode_branch(iid, perform_fct, record_fct, predict_fct)


def _c_(iid, fct, *args, **kwargs):
    if verbose:
        print(f"\nAt iid={iid}, calling function {fct}")

    if runtime_stats is not None:
        runtime_stats.total_uses += 1
        runtime_stats.cover_iid(iid)

    def perform_fct():
        return fct(*args, **kwargs)

    def record_fct(v):
        trace.append_call(iid, fct, args, kwargs, v)

    def predict_fct():
        return predictor.call(iid, fct, args, kwargs)

    return mode_branch(iid, perform_fct, record_fct, predict_fct)


def _a_(iid, base, attr_name):
    if verbose:
        print(f"\nAt iid={iid}, looking up attribute '{attr_name}'")

    if runtime_stats is not None:
        runtime_stats.total_uses += 1
        runtime_stats.cover_iid(iid)

    def perform_fct():
        return getattr(base, attr_name)

    def record_fct(v):
        trace.append_attribute(iid, base, attr_name, v)

    def predict_fct():
        return predictor.attribute(iid, base, attr_name)

    return mode_branch(iid, perform_fct, record_fct, predict_fct)


def _b_(iid, left, operator, right):
    if verbose:
        print(f"\nAt iid={iid}, performing binary {operator} operation")

    if runtime_stats is not None:
        runtime_stats.total_uses += 1
        runtime_stats.cover_iid(iid)

    def perform_fct():
        return perform_binary_op(left, operator, right)

    def record_fct(v):
        trace.append_binary_operation(iid, left, operator, right, v)

    def predict_fct():
        return predictor.binary_operation(iid, left, operator, right)

    return mode_branch(iid, perform_fct, record_fct, predict_fct)


def perform_binary_op(left, operator, right):
    # boolean operators
    if operator == "And":
        v = left and right
    elif operator == "Or":
        v = left or right
    # arithmetic operators
    elif operator == "Add":
        v = left + right
    elif operator == "BitAnd":
        v = left & right
    elif operator == "BitOr":
        v = left | right
    elif operator == "BitXor":
        v = left ^ right
    elif operator == "Divide":
        v = left / right
    elif operator == "FloorDivide":
        v = left // right
    elif operator == "LeftShift":
        v = left << right
    elif operator == "MatrixMultiply":
        v = left @ right
    elif operator == "Modulo":
        v = left % right
    elif operator == "Multiply":
        v = left * right
    elif operator == "Power":
        v = left ^ right
    elif operator == "RightShift":
        v = left >> right
    elif operator == "Subtract":
        v = left - right
    # comparison operators
    elif operator == "Equal":
        v = left == right
    elif operator == "GreaterThan":
        v = left > right
    elif operator == "GreaterThanEqual":
        v = left >= right
    elif operator == "In":
        v = left in right
    elif operator == "Is":
        v = left is right
    elif operator == "LessThan":
        v = left < right
    elif operator == "LessThanEqual":
        v = left <= right
    elif operator == "NotEqual":
        v = left != right
    elif operator == "IsNot":
        v = left is not right
    elif operator == "NotIn":
        v = left not in right
    else:
        raise Exception(f"Unexpected binary operator: {operator}")
    return v


def mode_branch(iid, perform_fct, record_fct, predict_fct):
    if mode in ("RECORD", "PREDICT"):
        try:
            v = perform_fct()
            if mode == "RECORD":
                record_fct(v)
            if verbose:
                print("Found/computed/returned regular value")
            return v
        except Exception as e:
            if verbose:
                print(
                    f"Catching exception {type(e)} and calling predictor instead")
            if mode == "PREDICT":
                v = predict_fct()
                runtime_stats.guided_uses += 1
                return v
            else:
                raise e
    elif mode == "REPLAY":
        # replay mode
        global next_trace_idx
        trace_line = trace[next_trace_idx].rstrip()
        next_trace_idx += 1
        segments = trace_line.split(" ")
        trace_iid = int(segments[0])
        abstract_value = segments[-1]
        if iid != trace_iid:
            raise Exception(
                f"trace_iid={trace_iid} doesn't match execution iid={iid}")
        v = restore_value(abstract_value)
        return v
    else:
        raise Exception(f"Unexpected mode {mode}")


def print_prediction_stats():
    pass
