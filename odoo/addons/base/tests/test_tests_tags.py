# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest

from odoo.tests.common import set_tags, check_tags, TagsError
from odoo.tools.config import parse_pico_lang


@set_tags('nodatabase')
class TestSetTags(unittest.TestCase):

    def test_set_tags_empty(self):
        """Test the set_tags decorator with an empty set of tags"""

        @set_tags()
        class FakeClass():
            pass

        fc = FakeClass()

        self.assertTrue(hasattr(fc, 'test_tags'))
        self.assertEqual(fc.test_tags, set())

    def test_set_tags_single_tag(self):
        """Test the set_tags decorator with a single tag"""

        @set_tags('slow')
        class FakeClass():
            pass

        fc = FakeClass()

        self.assertEqual(fc.test_tags, {'slow', })

    def test_set_tags_multiple_tags(self):
        """Test the set_tags decorator with multiple tags"""

        @set_tags('slow', 'nightly')
        class FakeClass():
            pass

        fc = FakeClass()

        self.assertEqual(fc.test_tags, {'slow', 'nightly'})

    def test_set_tags_unallowed_chars(self):
        """Test the set_tags decorator with unallowed chars"""

        with self.assertRaises(TagsError):
            @set_tags('+slow')
            class FakeClass:
                pass
            
        with self.assertRaises(TagsError):
            @set_tags('js+slow')
            class FakeClass:
                pass

@set_tags('nodatabase')
class TestPicoLang(unittest.TestCase):
    
    def test_pico_language(self):
        """Test the pico language for selecting deselecting tags"""
        
        self.assertEqual(({'slow',}, set()), parse_pico_lang('+slow'))
        self.assertEqual(({'slow', 'nightly'}, set()), parse_pico_lang('+slow,nightly'))
        self.assertEqual(({'slow'}, {'standard'}), parse_pico_lang('+slow,-standard'))
        self.assertEqual(({'slow'}, {'standard'}), parse_pico_lang('+slow, -standard'))
        self.assertEqual(({'slow'}, {'standard'}), parse_pico_lang('+slow , -standard'))
        self.assertEqual(({'slow', 'js'},{'standard'}), parse_pico_lang('slow,-standard,+js'))
        self.assertEqual(({'slow'},set()), parse_pico_lang('slow, '))
        self.assertEqual(({'slow'}, {'standard'}), parse_pico_lang('+slow,-standard, slow,-standard'))
        self.assertEqual((set(),set()), parse_pico_lang(''))

@set_tags('nodatabase')
class TestCheckTags(unittest.TestCase):

    def test_check_tags(self):
        """Test check_tags use cases"""
        class Test_A():
            pass

        @set_tags('stock')
        class Test_B():
            pass

        @set_tags('stock', 'slow')
        class Test_C():
            pass

        @set_tags('standard', 'slow')
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
        self.assertTrue(check_tags(no_tags_obj, None, None))
        self.assertTrue(check_tags(no_tags_obj, set(), set()))

        # same as "--test-tags '+slow'":
        self.assertFalse(check_tags(no_tags_obj, {'slow'}, set()))
        # same as "--test-tags '+slow,+fake'":
        self.assertFalse(check_tags(no_tags_obj, {'slow', 'fake'}, set()))
        # same as "--test-tags '+slow,+standard'":
        self.assertTrue(check_tags(no_tags_obj, {'slow', 'standard'}, set()))
        # same as "--test-tags '+slow,-standard'":
        self.assertFalse(check_tags(no_tags_obj, {'slow'}, {'standard'}))
        # same as "--test-tags '-slow,-standard'":
        self.assertFalse(check_tags(no_tags_obj, set(), {'slow', 'standard'}))
        # same as "--test-tags '-slow,+standard'":
        self.assertTrue(check_tags(no_tags_obj, {'standard'}, {'slow'}))

        self.assertFalse(check_tags(stock_tag_obj, set(), set()))
        self.assertFalse(check_tags(stock_tag_obj, {'slow'}, set()))
        self.assertFalse(check_tags(stock_tag_obj, {'standard'}, set()))
        self.assertFalse(check_tags(stock_tag_obj, {'slow', 'standard'}, set()))
        self.assertFalse(check_tags(stock_tag_obj, {'slow'}, {'standard'}))
        self.assertTrue(check_tags(stock_tag_obj, {'stock'}, set()))
        self.assertTrue(check_tags(stock_tag_obj, {'stock', 'fake'}, set()))
        self.assertTrue(check_tags(stock_tag_obj, {'stock'}, {'standard'}))
        self.assertFalse(check_tags(stock_tag_obj, set(), {'stock'}))

        self.assertFalse(check_tags(multiple_tags_obj, set(), set()))
        self.assertFalse(check_tags(multiple_tags_obj, set(), {'stock'}))
        self.assertFalse(check_tags(multiple_tags_obj, set(), {'slow'}))
        self.assertTrue(check_tags(multiple_tags_obj, {'slow'}, set()))
        self.assertTrue(check_tags(multiple_tags_obj, {'slow', 'stock'}, set()))
        self.assertFalse(check_tags(multiple_tags_obj, {'stock'}, {'slow'}))
        self.assertFalse(check_tags(multiple_tags_obj, {'stock', 'slow'}, {'slow'}))

        self.assertTrue(check_tags(multiple_tags_standard_obj, set(), set()))
        self.assertTrue(check_tags(multiple_tags_standard_obj, {'standard'}, set()))
        self.assertTrue(check_tags(multiple_tags_standard_obj, {'slow'}, set()))
        self.assertTrue(check_tags(multiple_tags_standard_obj, {'slow', 'fake'}, set()))
        self.assertFalse(check_tags(multiple_tags_standard_obj, set(), {'slow'}))
        self.assertFalse(check_tags(multiple_tags_standard_obj, set(), {'standard'}))
        self.assertFalse(check_tags(multiple_tags_standard_obj, set(), {'standard', 'slow'}))
        self.assertFalse(check_tags(multiple_tags_standard_obj, {'standard'}, {'slow'}))
        self.assertFalse(check_tags(multiple_tags_standard_obj, {'slow'}, {'standard'}))
