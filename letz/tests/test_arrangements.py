from mock import Mock, call, MagicMock
from pytest import fixture, raises

from letz.aliases import instance_of, when, verify_no_more_interactions, magic_call, \
    verify_zero_interaction, verify, times, never, in_order, at_least_once
from letz.exceptions import NoInteractionWanted, NeverWantedButInvoked, \
    WantedButNotInvoked, TooLittleActualInvocations, TooManyActualInvocations, VerificationInOrderFailure, \
    MocksException, ArgumentsAreDifferent


class TestWhen(object):
    @fixture(autouse=True)
    def init(self):
        self.tester = Mock()

    def test_should_evaluate_latest_stubbing_first(self):
        when(self.tester).has_a_call(call.object_returning_method(instance_of(int))).then_return(100)
        when(self.tester).has_a_call(call.object_returning_method(200)).then_return(200)

        assert 200 == self.tester.object_returning_method(200)
        assert 100 == self.tester.object_returning_method(666)

        assert self.tester.object_returning_method("blah") is None, "default behavior should return null"

    def test_should_stubbing_be_treated_as_interaction(self):
        when(self.tester).has_a_call(call.booleanReturningMethod()).then_return(True)

        self.tester.booleanReturningMethod()

        with raises(NoInteractionWanted):
            verify_no_more_interactions(self.tester)

    def test_should_allow_stubbing_to_string(self):
        other_tester = MagicMock()
        when(other_tester).has_a_call(magic_call.__str__()).then_return("test")

        assert str(self.tester) != 'test'
        assert str(other_tester) == 'test'

    def test_should_stubbing_not_be_treated_as_interaction(self):
        when(self.tester).has_a_call(call.simple_method('one')).then_raise(RuntimeError())
        when(self.tester).has_a_call(call.simple_method('two')).then_raise(RuntimeError())

        verify_zero_interaction(self.tester)


class TestVerify(object):
    @fixture(autouse=True)
    def init(self):
        self.tester = Mock()

    def test_should_verify(self):
        self.tester.clear()
        verify(self.tester).had_called_with(call.clear())

        self.tester.add("test")
        verify(self.tester).had_called_with(call.add("test"))

        verify_no_more_interactions(self.tester)

    def test_should_fail_verification(self):
        with raises(WantedButNotInvoked):
            verify(self.tester).had_called_with(call.clear())

    def test_should_fail_verification_on_method_argument(self):
        self.tester.clear()
        self.tester.add("foo")

        verify(self.tester).had_called_with(call.clear())

        with raises(WantedButNotInvoked):
            verify(self.tester).had_called_with(call.add("bar"))

    def test_should_detect_too_little_actual_invocations(self):
        self.tester.clear()
        self.tester.clear()

        verify(self.tester, times(2)).had_called_with(call.clear())
        with raises(TooLittleActualInvocations):
            verify(self.tester, times(100)).had_called_with(call.clear())

    def test_should_detect_too_many_actual_invocations(self):
        self.tester.clear()
        self.tester.clear()

        verify(self.tester, times(2)).had_called_with(call.clear())
        with raises(TooManyActualInvocations):
            verify(self.tester, times(1)).had_called_with(call.clear())

    def test_should_detect_when_invoked_more_than_once(self):
        self.tester.add("foo")
        self.tester.clear()
        self.tester.clear()

        verify(self.tester).had_called_with(call.add("foo"))
        with raises(TooManyActualInvocations):
            verify(self.tester).had_called_with(call.clear())

    def test_should_detect_actual_invocations_count_is_more_than_zero(self):
        verify(self.tester, times(0)).had_called_with(call.clear())
        with raises(WantedButNotInvoked):
            verify(self.tester, times(15)).had_called_with(call.clear())

    def test_should_detect_actually_called_once(self):
        self.tester.clear()
        with raises(NeverWantedButInvoked):
            verify(self.tester, times(0)).had_called_with(call.clear())

    def test_should_pass_when_methods_actually_not_called(self):
        verify(self.tester, times(0)).had_called_with(call.clear())
        verify(self.tester, times(0)).had_called_with(call.add("yes, I wasn't called"))

    def test_should_not_count_in_stubbed_invocations(self):
        when(self.tester).has_a_call(call.add('test')).then_return(False)
        when(self.tester).has_a_call(call.add('test')).then_return(True)

        self.tester.add('test')
        self.tester.add('test')

        verify(self.tester, times(2)).had_called_with(call.add('test'))

    def test_should_allow_verifying_interaction_never_happened(self):
        self.tester.add('one')

        verify(self.tester, never()).had_called_with(call.add('two'))
        verify(self.tester, never()).had_called_with(call.clear())

        with raises(NeverWantedButInvoked):
            verify(self.tester, never()).had_called_with(call.add('one'))


class TestInOrder(object):
    @fixture(autouse=True)
    def init(self):
        self.mock_a = Mock()
        self.mock_b = Mock()
        self.mock_c = Mock()

        self.tester = in_order(self.mock_a, self.mock_b, self.mock_c)

        self.mock_a.simple_method(1)
        self.mock_b.simple_method(2)
        self.mock_b.simple_method(2)
        self.mock_c.simple_method(3)
        self.mock_b.simple_method(2)
        self.mock_a.simple_method(4)

    def test_should_verify_in_order(self):
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))
        self.tester.verify(self.mock_b, times(2)).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_c).had_called_with(call.simple_method(3))
        self.tester.verify(self.mock_b).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(4))
        verify_no_more_interactions(self.mock_a, self.mock_b, self.mock_c)

    def test_should_verify_in_order_using_at_least_once(self):
        self.tester.verify(self.mock_a, at_least_once()).had_called_with(call.simple_method(1))
        self.tester.verify(self.mock_b, times(2)).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_c).had_called_with(call.simple_method(3))
        self.tester.verify(self.mock_b).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_a, at_least_once()).had_called_with(call.simple_method(4))
        verify_no_more_interactions(self.mock_a, self.mock_b, self.mock_c)

    def test_should_verify_in_order_when_expecting_some_invocations_to_be_called_zero_times(self):
        self.tester.verify(self.mock_a, times(0)).had_called_with(call.one_argument(False))
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))
        self.tester.verify(self.mock_b, times(2)).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_b, times(0)).had_called_with(call.simple_method(22))
        self.tester.verify(self.mock_c).had_called_with(call.simple_method(3))
        self.tester.verify(self.mock_b).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(4))
        self.tester.verify(self.mock_c, times(0)).had_called_with(call.one_arg(False))
        verify_no_more_interactions(self.mock_a, self.mock_b, self.mock_c)

    def test_should_fail_when_first_mock_called_twice(self):
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))

        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))

    def test_should_fail_when_last_mock_called_twice(self):
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))
        self.tester.verify(self.mock_b, times(2)).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_c).had_called_with(call.simple_method(3))
        self.tester.verify(self.mock_b).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(4))
        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_a).had_called_with(call.simple_method(4))

    def test_should_fail_on_first_method_because_one_invocation_wanted(self):
        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_a, times(0)).had_called_with(call.simple_method(1))

    def test_should_fail_on_first_method_because_one_invocation_wanted_again(self):
        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_a, times(2)).had_called_with(call.simple_method(1))

    def test_should_fail_on_second_method_because_four_invocations_wanted(self):
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))
        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_b, times(4)).had_called_with(call.simple_method(2))

    def test_should_fail_on_second_method_because_two_invocations_wanted_again(self):
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))
        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_b, times(0)).had_called_with(call.simple_method(2))

    def test_should_fail_on_last_method_because_one_invocation_wanted(self):
        self.tester.verify(self.mock_a, at_least_once()).had_called_with(call.simple_method(1))
        self.tester.verify(self.mock_b, times(2)).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_c, at_least_once()).had_called_with(call.simple_method(3))
        self.tester.verify(self.mock_b, at_least_once()).had_called_with(call.simple_method(2))
        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_a, times(0)).had_called_with(call.simple_method(4))

    def test_should_fail_on_last_method_because_one_invocation_wanted_again(self):
        self.tester.verify(self.mock_a, at_least_once()).had_called_with(call.simple_method(1))
        self.tester.verify(self.mock_b, times(2)).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_c, at_least_once()).had_called_with(call.simple_method(3))
        self.tester.verify(self.mock_b, at_least_once()).had_called_with(call.simple_method(2))
        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_a, times(2)).had_called_with(call.simple_method(4))

    def test_should_fail_on_first_method_because_different_args_wanted(self):
        with raises(ArgumentsAreDifferent):
            self.tester.verify(self.mock_a).had_called_with(call.simple_method(100))

    def test_should_fail_on_first_method_because_different_method_wanted(self):
        with raises(WantedButNotInvoked):
            self.tester.verify(self.mock_a).had_called_with(call.one_arg(True))

    def test_should_fail_on_second_method_because_different_args_wanted(self):
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))
        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_b, times(2)).had_called_with(call.simple_method(-999))

    def test_should_fail_on_second_method_because_different_method_wanted(self):
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))
        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_b, times(2)).had_called_with(call.one_arg(True))

    def test_should_fail_on_last_method_because_different_args_wanted(self):
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))
        self.tester.verify(self.mock_b, times(2)).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_c).had_called_with(call.simple_method(3))
        self.tester.verify(self.mock_b).had_called_with(call.simple_method(2))
        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_a).had_called_with(call.simple_method(-666))

    def test_should_fail_on_last_method_because_different_method_wanted(self):
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))
        self.tester.verify(self.mock_b, times(2)).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_c).had_called_with(call.simple_method(3))
        self.tester.verify(self.mock_b).had_called_with(call.simple_method(2))
        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_a).had_called_with(call.one_arg(False))

    def test_should_fail_when_last_method_verified_first(self):
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(4))

        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))

    def test_should_fail_when_middle_method_verified_first(self):
        self.tester.verify(self.mock_b, times(2)).had_called_with(call.simple_method(2))

        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))

    def test_should_fail_when_middle_method_verified_first_in_at_least_once_mode(self):
        self.tester.verify(self.mock_b, at_least_once()).had_called_with(call.simple_method(2))

        with raises(VerificationInOrderFailure):
            self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))

    def test_should_fail_on_verify_no_more_interactions(self):
        self.tester.verify(self.mock_a).had_called_with(call.simple_method(1))
        self.tester.verify(self.mock_b, times(2)).had_called_with(call.simple_method(2))
        self.tester.verify(self.mock_c).had_called_with(call.simple_method(3))
        self.tester.verify(self.mock_b).had_called_with(call.simple_method(2))
        with raises(NoInteractionWanted):
            verify_no_more_interactions(self.mock_a, self.mock_b, self.mock_c)

    def test_should_fail_on_verify_zero_interactions(self):
        with raises(NoInteractionWanted):
            verify_zero_interaction(self.mock_a)

    def test_should_scream_when_null_passed(self):
        with raises(MocksException):
            in_order(None)
