import inspect
import keyword

from future.utils import isidentifier
from typing import Any, Dict, NoReturn, Type, Callable, Union


class Call(tuple):
    def __new__(cls, *args, **kwargs):
        # type: (Type[Call], *Any, **Any) -> Call
        return tuple.__new__(cls, (args, kwargs))

    def __init__(self, *args, **kwargs):
        pass

    def __eq__(self, other):
        self_args, self_kwargs = self
        other_args, other_kwargs = other

        return (other_args, other_kwargs) == (self_args, self_kwargs)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __call__(self, *args, **kwargs):
        return Call(*args, **kwargs)

    def __repr__(self):
        return '<{} args={} kwargs={}>'.format(self.__name__, *self)

    @property
    def args(self):
        return self[0]

    @property
    def kwargs(self):
        return self[1]


class CallSignature(object):
    def __init__(self, arguments_names, args=False, kwargs=False):
        self.arguments_names = ['{}'.format(name) for name in arguments_names]
        self.args = args
        self.kwargs = kwargs

        self.validate_arguments()

    def validate_arguments(self):
        for name in self.arguments_names:
            if not isidentifier(name) or keyword.iskeyword(name):
                raise ValueError('{} is not valid argument name!'.format(name))

    @classmethod
    def from_model(cls, model):
        arg_spec = inspect.getargspec(model)
        return cls(arg_spec.args, arg_spec.varargs, arg_spec.keywords)


class CallSignatureCheckerFactory(object):
    SIGNATURE_CHECKER_FORMAT = 'lambda {signature}: None'

    @classmethod
    def format_signature(cls, call_signature):
        return inspect.formatargspec(
            call_signature.arguments_names,
            'args' if call_signature.args else None,
            'kwargs' if call_signature.kwargs else None,
            []
        ).strip('()')

    @classmethod
    def create(cls, signature_model):
        # type: (Callable) -> Callable
        formatted_signature = cls.format_signature(CallSignature.from_model(signature_model))
        formatted_checker = cls.SIGNATURE_CHECKER_FORMAT.format(signature=formatted_signature)
        return eval(formatted_checker, {'LetzCall': Call})


class LetzFactory(object):
    @classmethod
    def create(cls, engine, is_callable=True):
        # type: (LetzEngine, bool) -> Union[Letz, CallableLetz]
        bases = (Letz,)
        if is_callable:
            bases = (CallableLetz,)

        new_class = type(Letz.__name__, tuple(bases), {
            '__slots__': (),
            '__doc__': Letz.__doc__,
            '__engine__': engine,
        })  # type: Union[Letz, CallableLetz]
        return object.__new__(new_class)


class LetzController(object):
    def __init__(self):
        self.letzim = {}  # type: Dict[Letz, LetzEngine]

    def create_letz(self, is_callable=True):
        # type: (bool) -> Union[Letz, CallableLetz]
        engine = LetzEngine(self)

        letz = LetzFactory.create(engine, is_callable)

        self.letzim[letz] = engine
        return letz

    def create_singed_letz(self, signature_model):
        # type: (Callable) -> CallableLetz
        letz = self.create_letz(is_callable=True)
        letz.__engine__.set_signature(signature_model)
        return letz

    def get_engine(self, letz):
        return self.letzim[letz]

    def set_answer(self, letz, answer):
        self.letzim[letz].answer = answer

    def set_constant_answer(self, letz, value):
        self.letzim[letz].answer = ConstantAnswer(value)


class LetzAttribute(object):
    def __init__(self, content):
        self.content = content

        self.deleted = False


class Answer(object):
    def __call__(self, *args, **kwargs):
        raise NotImplementedError()


class SequencedAnswer(object):
    def __init__(self, values=None):
        self.values = values or []

        self.index = 0

    def add_value(self, value):
        self.values.insert(0, value)
        self.index += 1

    def __call__(self, *args, **kwargs):
        if self.index > 0:
            self.index -= 1
        return self.values[self.index]


class ConstantAnswer(Answer):
    def __init__(self, value):
        self.value = value

    def __call__(self, *args, **kwargs):
        return self.value


class SignatureMatchingAnswer(object):
    def __init__(self, default=None):
        self.configured_calls = []
        self.default = default

    def add_configuration(self, call, answer):
        self.configured_calls.insert(0, (call, answer))

    def __call__(self, *args, **kwargs):
        for configured_call, answer in self.configured_calls:
            if Call(*args, **kwargs) == configured_call:
                return answer(*args, **kwargs)
        return self.default


class CallAction(object):
    def act(self, engine, call):
        # type: (LetzEngine, Call) -> NoReturn
        engine.check_call_signature(*call.args, **call.kwargs)


class DefaultAction(CallAction):
    def act(self, engine, call):
        super(DefaultAction, self).act(engine, call)
        engine.log_call(call)


DEFAULT_ACTION = DefaultAction()


class AnswerConfigurationAction(CallAction):
    def __init__(self, call_answer):
        self.call_answer = call_answer

    def act(self, engine, call):
        super(AnswerConfigurationAction, self).act(engine, call)
        engine.check_call_signature(*call.args, **call.kwargs)
        if engine.answer is None:
            engine.answer = SignatureMatchingAnswer()

        engine.answer.add_configuration(call, self.call_answer)
        engine.reset_action()


class VerificationAction(CallAction):
    def __init__(self, verifier):
        self.verifier = verifier

    def act(self, engine, call):
        super(VerificationAction, self).act(engine, call)

        self.verifier.verify(engine.log_call, call)

        engine.reset_action()


class LetzEngine(object):
    def __init__(self, letz_controller, call_signature_checker=None):
        # type: (LetzController, Callable) -> NoReturn
        self.letz_controller = letz_controller
        if call_signature_checker is not None:
            self.check_call_signature = call_signature_checker

        self.attributes = {}
        self.answer = None
        self.calls_log = []

        self._call_action = DEFAULT_ACTION

    @staticmethod
    def check_call_signature(*args, **kwargs):
        pass

    def get_attribute(self, name):
        if name not in self.attributes:
            self.attributes[name] = LetzAttribute(self.letz_controller.create_letz())
        attribute = self.attributes[name]
        if attribute.deleted:
            raise AttributeError()
        return attribute.content

    def set_attribute(self, name, value):
        if name not in self.attributes:
            self.attributes[name] = LetzAttribute(value)
        else:
            self.attributes[name].content = value

    def get_answer(self, *args, **kwargs):
        # type: (...) -> Any
        if self.answer is None:
            self.answer = ConstantAnswer(self.letz_controller.create_letz())
        return self.answer(*args, **kwargs)

    def log_call(self, call):
        self.calls_log.append(call)

    def reset_action(self):
        self._call_action = DEFAULT_ACTION

    def handle_call(self, call):
        self._call_action.act(self, call)

    def set_signature(self, signature_model):
        self.check_call_signature = CallSignatureCheckerFactory.create(signature_model)


class Letz(object):
    __slots__ = ()
    __engine__ = None  # type: LetzEngine

    def __getattr__(self, name):
        return self.__engine__.get_attribute(name)

    def __setattr__(self, name, value):
        self.__engine__.set_attribute(name, value)


class CallableLetz(Letz):
    def __call__(self, *args, **kwargs):
        call = Call(*args, **kwargs)
        self.__engine__.handle_call(call)
        return self.__engine__.get_answer(*args, **kwargs)
