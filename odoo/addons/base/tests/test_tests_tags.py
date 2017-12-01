# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest

from odoo.tests.common import tagged, TagsTestSelector, TagsError


@tagged('nodatabase')
class TestSetTags(unittest.TestCase):

    def test_set_tags_empty(self):
        """Test the set_tags decorator with an empty set of tags"""

        @tagged()
        class FakeClass():
            pass

        fc = FakeClass()

        self.assertTrue(hasattr(fc, 'test_tags'))
        self.assertEqual(fc.test_tags, set())

    def test_set_tags_single_tag(self):
        """Test the set_tags decorator with a single tag"""

        @tagged('slow')
        class FakeClass():
            pass

        fc = FakeClass()

        self.assertEqual(fc.test_tags, {'slow', })

    def test_set_tags_multiple_tags(self):
        """Test the set_tags decorator with multiple tags"""

        @tagged('slow', 'nightly')
        class FakeClass():
            pass

        fc = FakeClass()

        self.assertEqual(fc.test_tags, {'slow', 'nightly'})

    def test_set_tags_unallowed_chars(self):
        """Test the set_tags decorator with unallowed chars"""

        with self.assertRaises(TagsError):
            @tagged('+slow')
            class FakeClass:
                pass
            
        with self.assertRaises(TagsError):
            @tagged('js+slow')
            class FakeClass:
                pass

@tagged('nodatabase')
class TestSelector(unittest.TestCase):

    def test_selector_parser(self):
        """Test the parser part of the TagsTestSelector class"""

        selector = TagsTestSelector('+slow')
        self.assertEqual({'slow', }, selector.include)
        self.assertEqual(set(), selector.exclude)

        selector = TagsTestSelector('+slow,nightly')
        self.assertEqual({'slow', 'nightly'}, selector.include)
        self.assertEqual(set(), selector.exclude)

        selector = TagsTestSelector('+slow,-standard')
        self.assertEqual({'slow', }, selector.include)
        self.assertEqual({'standard', }, selector.exclude)

        # same with space after the comma
        selector = TagsTestSelector('+slow, -standard')
        self.assertEqual({'slow', }, selector.include)
        self.assertEqual({'standard', }, selector.exclude)

        # same with space befaore and after the comma
        selector = TagsTestSelector('+slow , -standard')
        self.assertEqual({'slow', }, selector.include)
        self.assertEqual({'standard', }, selector.exclude)

        selector = TagsTestSelector('+slow ,-standard,+js')
        self.assertEqual({'slow', 'js', }, selector.include)
        self.assertEqual({'standard', }, selector.exclude)

        selector = TagsTestSelector('slow, ')
        self.assertEqual({'slow', }, selector.include)
        self.assertEqual(set(), selector.exclude)

        selector = TagsTestSelector('+slow,-standard, slow,-standard ')
        self.assertEqual({'slow', }, selector.include)
        self.assertEqual({'standard', }, selector.exclude)

        selector = TagsTestSelector('')
        self.assertEqual({'standard', }, selector.include)
        self.assertEqual(set(), selector.exclude)

@tagged('nodatabase')
class TestSelectorSelection(unittest.TestCase):

    def test_selector_selection(self):
        """Test check_tags use cases"""
        class Test_A():
            pass

        @tagged('stock')
        class Test_B():
            pass

        @tagged('stock', 'slow')
        class Test_C():
            pass

        @tagged('standard', 'slow')
        class Test_D():
            pass

        no_tags_obj = Test_A()
        stock_tag_obj = Test_B()
        multiple_tags_obj = Test_C()
        multiple_tags_standard_obj = Test_D()

        # if 'standard' in not explicitly removed, tests without tags are
        # considered tagged standards and they are run by default if
        # not explicitly deselected with '-standards' or if 'standards' is not
        # selectected along with another test tag

        # same as no "--test-tags" parameters:
        selector = TagsTestSelector('')
        self.assertTrue(selector(no_tags_obj))

        # same as "--test-tags '+slow'":
        selector = TagsTestSelector('+slow')
        self.assertFalse(selector(no_tags_obj))

        # same as "--test-tags '+slow,+fake'":
        selector = TagsTestSelector('+slow,fake')
        self.assertFalse(selector(no_tags_obj))

        # same as "--test-tags '+slow,+standard'":
        selector = TagsTestSelector('slow,standard')
        self.assertTrue(no_tags_obj)

        # same as "--test-tags '+slow,-standard'":
        selector = TagsTestSelector('slow,-standard')
        self.assertFalse(selector(no_tags_obj))

        # same as "--test-tags '-slow,-standard'":
        selector = TagsTestSelector('-slow,-standard')
        self.assertFalse(selector(no_tags_obj))

        # same as "--test-tags '-slow,+standard'":
        selector = TagsTestSelector('-slow,+standard')
        self.assertTrue(selector(no_tags_obj))

        selector = TagsTestSelector('')
        self.assertFalse(selector(stock_tag_obj))

        selector = TagsTestSelector('slow')
        self.assertFalse(selector(stock_tag_obj))

        selector = TagsTestSelector('standard')
        self.assertFalse(selector(stock_tag_obj))

        selector = TagsTestSelector('slow,standard')
        self.assertFalse(selector(stock_tag_obj))

        selector = TagsTestSelector('slow,-standard')
        self.assertFalse(selector(stock_tag_obj))

        selector = TagsTestSelector('+stock')
        self.assertTrue(selector(stock_tag_obj))

        selector = TagsTestSelector('stock,fake')
        self.assertTrue(selector(stock_tag_obj))

        selector = TagsTestSelector('stock,standard')
        self.assertTrue(selector(stock_tag_obj))

        selector = TagsTestSelector('-stock')
        self.assertFalse(selector(stock_tag_obj))

        selector = TagsTestSelector('')
        self.assertFalse(selector(multiple_tags_obj))

        selector = TagsTestSelector('-stock')
        self.assertFalse(selector(multiple_tags_obj))

        selector = TagsTestSelector('-slow')
        self.assertFalse(selector(multiple_tags_obj))

        selector = TagsTestSelector('slow')
        self.assertTrue(selector(multiple_tags_obj))

        selector = TagsTestSelector('slow,stock')
        self.assertTrue(selector(multiple_tags_obj))

        selector = TagsTestSelector('-slow,stock')
        self.assertFalse(selector(multiple_tags_obj))

        selector = TagsTestSelector('slow,stock,-slow')
        self.assertFalse(selector(multiple_tags_obj))

        selector = TagsTestSelector('')
        self.assertTrue(selector(multiple_tags_standard_obj))

        selector = TagsTestSelector('standard')
        self.assertTrue(selector(multiple_tags_standard_obj))

        selector = TagsTestSelector('slow')
        self.assertTrue(selector(multiple_tags_standard_obj))

        selector = TagsTestSelector('slow,fake')
        self.assertTrue(selector(multiple_tags_standard_obj))

        selector = TagsTestSelector('-slow')
        self.assertFalse(selector(multiple_tags_standard_obj))

        selector = TagsTestSelector('-standard')
        self.assertFalse(selector(multiple_tags_standard_obj))

        selector = TagsTestSelector('-slow,-standard')
        self.assertFalse(selector(multiple_tags_standard_obj))

        selector = TagsTestSelector('stantard,-slow')
        self.assertFalse(selector(multiple_tags_standard_obj))

        selector = TagsTestSelector('slow,-standard')
        self.assertFalse(selector(multiple_tags_standard_obj))
