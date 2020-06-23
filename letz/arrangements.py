from mock import call, Mock
from typing import List, Tuple, Any

from letz.consts import DEFAULT
from letz.exceptions import NeverWantedButInvoked, WantedButNotInvoked, \
    TooLittleActualInvocations, TooManyActualInvocations, VerificationInOrderFailure, MocksException, \
    ArgumentsAreDifferent


class CallsCountPredicate(object):
    def __init__(self, minimum=None, maximum=None):
        self.minimum = minimum
        self.maximum = maximum

    def __call__(self, calls_count):
        if self.maximum == 0 and calls_count != 0:
            raise NeverWantedButInvoked()
        if self.maximum > 0:
            if calls_count == 0:
                raise WantedButNotInvoked()
            if self.minimum and calls_count < self.minimum:
                raise TooLittleActualInvocations()
            if self.maximum and calls_count > self.maximum:
                raise TooManyActualInvocations()


ONLY_ONCE_PREDICATE = CallsCountPredicate(minimum=1, maximum=1)

NEVER_PREDICATE = CallsCountPredicate(maximum=0)


class MagicCall(call.__class__):
    def __init__(self, value=(), name=None, parent=None, two=False, from_kall=True):
        super(MagicCall, self).__init__(value, name, parent, two, from_kall)

    def __call__(self, *args, **kwargs):
        if self.name is None:
            return MagicCall(('', args, kwargs), name='()')

        name = self.name + '()'
        return MagicCall((self.name, args, kwargs), name=name, parent=self)

    def __getattr__(self, attr):
        if self.name is None:
            return MagicCall(name=attr, from_kall=False)
        name = '%s.%s' % (self.name, attr)
        return MagicCall(name=name, parent=self, from_kall=False)

    def __str__(self):
        return self.__getattr__('__str__')()


class SideEffect(object):
    def __init__(self, default=DEFAULT):
        self.configured_calls = []  # type: List[Tuple[Any, List]]
        self.default = default

    def __call__(self, *args, **kwargs):
        for configured_call, return_value in self.configured_calls:
            if call(*args, **kwargs) == configured_call:
                if len(return_value) > 1:
                    return return_value.pop(0)(*args, **kwargs)
                return return_value[0](*args, **kwargs)
        return self.default


class SideEffectModifier(object):
    def __init__(self, configurations):
        self.configurations = configurations

    def then_return(self, value):
        self.configurations.append(lambda *args, **kwargs: value)
        return self

    def then_raise(self, exception):
        def answer(*_, **__):
            raise exception

        self.configurations.append(answer)
        return self


class WhenModifier(object):
    def __init__(self, mock):
        self.mock = mock

    def has_a_call(self, modified_call):
        mock_call = self.mock
        call_structure = modified_call.parent.name.split('.')
        for attr in call_structure:
            mock_call = getattr(mock_call, attr)

        side_effect = mock_call.side_effect
        if not isinstance(mock_call.side_effect, SideEffect):
            side_effect = SideEffect(None)
            mock_call.side_effect = side_effect

        configured_calls = []
        current_call = call(*modified_call[1], **modified_call[2])
        side_effect.configured_calls.insert(0, (current_call, configured_calls))

        return SideEffectModifier(configured_calls)


def get_mock_verified_calls(mock):
    if not isinstance(mock.mock_verified_calls, list):
        mock.mock_verified_calls = []
        original_reset_mock = mock.reses_mock

        def new_reset_mock():
            mock.mock_verified_calls = []
            original_reset_mock()

        mock.reset_mock = new_reset_mock
    return mock.mock_verified_calls


class Verifier(object):
    def __init__(self, mock_instance, verification):
        self.mock_instance = mock_instance
        self.verification = verification

    def had_called_with(self, call_to_verify):
        calls_count = self.mock_instance.mock_calls.count(call_to_verify)
        self.verification(calls_count)

        mock_verified_call = get_mock_verified_calls(self.mock_instance)
        mock_verified_call += [call_to_verify] * calls_count


class InOrderVerifier(object):
    def __init__(self, parent_in_order, mock_instance, verification):
        # type: (InOrder, Mock, CallsCountPredicate) -> None
        self.parent_in_order = parent_in_order
        self.mock_instance = mock_instance
        self.mock_name = parent_in_order.instances_names[mock_instance]
        self.verification = verification

    def found_first_invocation(self, call_to_find):
        name, args, kwargs = call_to_find
        manager_call_name = '{}.{}'.format(self.mock_name, name)
        manager_call_to_find = (manager_call_name, args, kwargs)

        calls = self.parent_in_order.mock_manager.mock_calls
        if manager_call_to_find in calls:
            self.parent_in_order.next_index = calls.index(manager_call_to_find)
        else:
            self.parent_in_order.next_index = 0

    def had_called_with(self, call_to_verify):
        if self.parent_in_order.next_index is None:
            self.found_first_invocation(call_to_verify)

        calls_count = 0

        name, args, kwargs = call_to_verify
        manager_call_name = '{}.{}'.format(self.mock_name, name)
        manager_call_to_verify = (manager_call_name, args, kwargs)

        calls = self.parent_in_order.mock_manager.mock_calls
        next_index = self.parent_in_order.next_index
        while next_index < len(calls) and calls[next_index] == manager_call_to_verify:
            next_index += 1
            calls_count += 1

        try:
            self.verification(calls_count)
        except WantedButNotInvoked:
            if next_index == 0:
                if calls_count == 0 and next_index < len(calls) and manager_call_name == calls[next_index][0]:
                    raise ArgumentsAreDifferent()
                elif calls_count == 0:
                    raise
            raise VerificationInOrderFailure()
        except MocksException:
            raise VerificationInOrderFailure()

        mock_manager_verified_call = get_mock_verified_calls(self.parent_in_order.mock_manager)
        mock_manager_verified_call += [call_to_verify] * calls_count
        self.parent_in_order.next_index = next_index

        mock_verified_call = get_mock_verified_calls(self.mock_instance)
        mock_verified_call += [call_to_verify] * calls_count


class InOrder(object):
    def __init__(self, *mock_instances):
        self.mock_manager = Mock()

        self.instances_names = {}

        for index, mock_instance in enumerate(mock_instances):
            mock_name = 'm_{}'.format(index)
            self.instances_names[mock_instance] = mock_name
            self.mock_manager.attach_mock(mock_instance, mock_name)

        self.next_index = None

    def verify(self, mock_instance, verification=ONLY_ONCE_PREDICATE):
        return InOrderVerifier(self, mock_instance, verification)


class TypePredicate(object):
    def __init__(self, type_):
        self.type = type_

    def __eq__(self, other):
        return isinstance(other, self.type)

    def __ne__(self, other):
        return not isinstance(other, self.type)

    def __repr__(self):
        return '<type: {}>'.format(self.type.__name__)

    @classmethod
    def create(cls, _type):
        return TypePredicate(_type)
