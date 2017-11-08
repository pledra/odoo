# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import BaseFunctionalTest
from odoo.tools import mute_logger


class TestChatterTweaks(BaseFunctionalTest):

    def setUp(self):
        super(TestChatterTweaks, self).setUp()
        self.partner_1 = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com'})
        self.partner_2 = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'Valid Poilvache',
            'email': 'valid.other@gmail.com'})

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_no_subscribe_author(self):
        original = self.test_record.message_follower_ids
        self.test_record.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment')
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))
        self.assertEqual(self.test_record.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_no_subscribe_recipients(self):
        original = self.test_record.message_follower_ids
        self.test_record.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id'))
        self.assertEqual(self.test_record.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_subscribe_recipients(self):
        original = self.test_record.message_follower_ids
        self.test_record.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id') | self.partner_1 | self.partner_2)
        self.assertEqual(self.test_record.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_subscribe_recipients_partial(self):
        original = self.test_record.message_follower_ids
        self.test_record.sudo(self.user_employee).with_context({'mail_create_nosubscribe': True, 'mail_post_autofollow': True, 'mail_post_autofollow_partner_ids': [self.partner_2.id]}).message_post(
            body='Test Body', message_type='comment', subtype='mt_comment', partner_ids=[(4, self.partner_1.id), (4, self.partner_2.id)])
        self.assertEqual(self.test_record.message_follower_ids.mapped('partner_id'), original.mapped('partner_id') | self.partner_2)
        self.assertEqual(self.test_record.message_follower_ids.mapped('channel_id'), original.mapped('channel_id'))


class TestNotifications(BaseFunctionalTest):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_needaction(self):
        # needaction use Inbox notification
        (self.user_employee | self.user_admin).write({'notification_type': 'inbox'})

        na_emp1_base = self.test_record.sudo(self.user_employee).message_needaction_counter
        na_emp2_base = self.test_record.sudo().message_needaction_counter

        self.test_record.message_post(body='Test', message_type='comment', subtype='mail.mt_comment', partner_ids=[self.user_employee.partner_id.id])

        na_emp1_new = self.test_record.sudo(self.user_employee).message_needaction_counter
        na_emp2_new = self.test_record.sudo().message_needaction_counter
        self.assertEqual(na_emp1_new, na_emp1_base + 1)
        self.assertEqual(na_emp2_new, na_emp2_base)

    def test_set_star(self):
        msg = self.test_record.message_post(body='My Body', subject='1')
        msg_emp = self.env['mail.message'].sudo(self.user_employee).browse(msg.id)

        # Admin set as starred
        msg.toggle_message_starred()
        self.assertTrue(msg.starred)

        # Employee set as starred
        msg_emp.toggle_message_starred()
        self.assertTrue(msg_emp.starred)

        # Do: Admin unstars msg
        msg.toggle_message_starred()
        self.assertFalse(msg.starred)
        self.assertTrue(msg_emp.starred)


class TestChatterMisc(BaseFunctionalTest):

    def test_alias_setup(self):
        alias = self.env['mail.alias'].with_context(alias_model_name='mail.test').create({'alias_name': 'b4r+_#_R3wl$$'})
        self.assertEqual(alias.alias_name, 'b4r+_-_r3wl-', 'Disallowed chars should be replaced by hyphens')

    def test_cache_invalidation(self):
        """ Test that creating a mail-thread record does not invalidate the whole cache. """
        # make a new record in cache
        record = self.env['res.partner'].new({'name': 'Brave New Partner'})
        self.assertTrue(record.name)

        # creating a mail-thread record should not invalidate the whole cache
        self.env['res.partner'].create({'name': 'Actual Partner'})
        self.assertTrue(record.name)
