from mock import Mock

from letz.arrangements import MagicCall, WhenModifier, CallsCountPredicate, ONLY_ONCE_PREDICATE, \
    Verifier, get_mock_verified_calls, InOrder, TypePredicate, NEVER_PREDICATE
from letz.exceptions import NoInteractionWanted, MocksException

magic_call = MagicCall(from_kall=False)


def when(mock_instance):
    # type: (Mock) -> WhenModifier
    return WhenModifier(mock_instance)


def times(count=1):
    if count == 1:
        return ONLY_ONCE_PREDICATE
    return CallsCountPredicate(minimum=count, maximum=count)


def never():
    return NEVER_PREDICATE


def at_most(count=1):
    return CallsCountPredicate(maximum=count)


def at_least(count=1):
    return CallsCountPredicate(minimum=count)


AT_LEAST_ONCE = at_least()


def at_least_once():
    return AT_LEAST_ONCE


def verify(mock_instance, calls_count_verifier=ONLY_ONCE_PREDICATE):
    # type: (Mock, CallsCountPredicate) -> Verifier
    return Verifier(mock_instance, calls_count_verifier)


def verify_zero_interaction(mock_instance):
    all_calls = list(mock_instance.mock_calls)
    if all_calls:
        raise NoInteractionWanted


def verify_no_more_interactions(*mock_instances):
    for mock_instance in mock_instances:
        verified_calls = get_mock_verified_calls(mock_instance)
        all_calls = list(mock_instance.mock_calls)

        for verified_call in verified_calls:
            try:
                all_calls.remove(verified_call)
            except ValueError:
                raise NoInteractionWanted()

        if all_calls:
            raise NoInteractionWanted()


def in_order(*mock_instances):
    if None in mock_instances:
        raise MocksException()
    return InOrder(*mock_instances)


def instance_of(_type):
    return TypePredicate(_type)
