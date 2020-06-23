from tstcls import TestClassBase
from letz.core import Letz, LetzController


class TestLetz(TestClassBase):
    def setup_test(self, **fixtures):
        self.letz_controller = LetzController()
        self.tester = self.letz_controller.create_letz()
        self.tester_engine = self.letz_controller.get_engine(self.tester)

        self.other_letz = self.letz_controller.create_letz()

    def test_call(self):
        ###
        answer = self.tester()
        ###

        assert self.tester_engine.answer.value == answer
        assert self.tester != answer
        assert self.tester.__engine__ != answer.__engine__
        assert isinstance(answer, Letz)
        assert self.other_letz() != answer

    def test_call_with_signature(self):
        other_letz = self.letz_controller.create_singed_letz(lambda first, second: None)

        ###
        answer = other_letz('s', '4')
        ###

        assert other_letz.__engine__.answer.value == answer
        assert other_letz != answer
        assert other_letz.__engine__ != answer.__engine__
        assert isinstance(answer, Letz)
        assert self.tester() != answer

    def test_set_answer(self):
        self.letz_controller.set_constant_answer(self.tester, 'some_value')

        ###
        answer = self.tester()
        ###

        assert answer == 'some_value'

    def test_get_attr(self):
        ###
        some_attribute = self.tester.some_attribute
        ###

        assert self.tester.some_attribute == some_attribute
        assert isinstance(some_attribute, Letz)
        assert self.other_letz.some_attribute != some_attribute

    def test_set_attr(self):
        ###
        self.tester.some_attribute = None
        ###

        assert 'some_attribute' in self.tester.__engine__.attributes
        assert self.tester.__engine__.attributes['some_attribute'].content is None
        assert self.other_letz.some_attribute is not None

    def test_set_attr__had_value_before(self):
        getattr(self.tester, 'some_attribute')

        ###
        self.tester.some_attribute = None
        ###

        assert 'some_attribute' in self.tester.__engine__.attributes
        assert self.tester.__engine__.attributes['some_attribute'].content is None
        assert self.other_letz.some_attribute is not None
