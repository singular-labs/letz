class MocksException(Exception):
    pass


class NoInteractionWanted(MocksException):
    pass


class WantedButNotInvoked(MocksException):
    pass


class TooLittleActualInvocations(MocksException):
    pass


class TooManyActualInvocations(MocksException):
    pass


class NeverWantedButInvoked(MocksException):
    pass


class VerificationInOrderFailure(Exception):
    pass


class ArgumentsAreDifferent(Exception):
    pass
