# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest

from odoo.tests.common import set_tags, check_tags, TagsError


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
        """Test the set_tags decorator ith multiple tags"""

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

        self.assertTrue(check_tags(no_tags_obj, None))
        self.assertTrue(check_tags(no_tags_obj, ''))

#       if 'standard' in not explicitly removed, tests are without tags are standards
        self.assertTrue(check_tags(no_tags_obj, '+slow'))
        self.assertTrue(check_tags(no_tags_obj, '+slow,fake'))
        self.assertTrue(check_tags(no_tags_obj, 'slow'))
        self.assertTrue(check_tags(no_tags_obj, '+slow,+standard'))
        self.assertTrue(check_tags(no_tags_obj, '+slow,standard'))
        self.assertFalse(check_tags(no_tags_obj, '+slow,-standard'))

        self.assertTrue(check_tags(stock_tag_obj, None))
        self.assertTrue(check_tags(stock_tag_obj, ''))
        self.assertFalse(check_tags(stock_tag_obj, '+slow'))
        self.assertFalse(check_tags(stock_tag_obj, '+standard'))
        self.assertFalse(check_tags(stock_tag_obj, '+slow,+standard'))
        self.assertFalse(check_tags(stock_tag_obj, '+slow,-standard'))
        self.assertTrue(check_tags(stock_tag_obj, '+stock'))
        self.assertTrue(check_tags(stock_tag_obj, '+stock,+fake'))
        self.assertTrue(check_tags(stock_tag_obj, '+stock,-standard'))
        self.assertFalse(check_tags(stock_tag_obj, '-stock'))

        self.assertTrue(check_tags(multiple_tags_obj, None))
        self.assertTrue(check_tags(multiple_tags_obj, ''))
        self.assertFalse(check_tags(multiple_tags_obj, '-stock'))
        self.assertFalse(check_tags(multiple_tags_obj, '-slow'))
        self.assertTrue(check_tags(multiple_tags_obj, 'slow'))
        self.assertTrue(check_tags(multiple_tags_obj, '+slow'))
        self.assertTrue(check_tags(multiple_tags_obj, 'slow,stock'))
        self.assertTrue(check_tags(multiple_tags_obj, '+slow,stock'))
        self.assertTrue(check_tags(multiple_tags_obj, 'slow,+stock'))
        self.assertFalse(check_tags(multiple_tags_obj, '-slow,stock'))
        self.assertFalse(check_tags(multiple_tags_obj, '-slow,+stock'))
        self.assertFalse(check_tags(multiple_tags_obj, '-slow,+stock,+slow'))

        self.assertTrue(check_tags(multiple_tags_standard_obj, None))
        self.assertTrue(check_tags(multiple_tags_standard_obj, ''))
        self.assertTrue(check_tags(multiple_tags_standard_obj, '+standard'))
        self.assertTrue(check_tags(multiple_tags_standard_obj, '+slow'))
        self.assertTrue(check_tags(multiple_tags_standard_obj, 'slow'))
        self.assertTrue(check_tags(multiple_tags_standard_obj, 'slow,-fake'))
        self.assertFalse(check_tags(multiple_tags_standard_obj, '-slow'))
        self.assertFalse(check_tags(multiple_tags_standard_obj, '-standard'))
        self.assertFalse(check_tags(multiple_tags_standard_obj, '-standard,-slow'))
        self.assertFalse(check_tags(multiple_tags_standard_obj, '+standard,-slow'))
        self.assertFalse(check_tags(multiple_tags_standard_obj, '-standard,+slow'))
        self.assertFalse(check_tags(multiple_tags_standard_obj, '-standard,slow'))

#       One could use spaces by accident
        self.assertTrue(check_tags(no_tags_obj, 'fake, slow,fake'))
        self.assertTrue(check_tags(no_tags_obj, 'fake, slow ,fake'))
