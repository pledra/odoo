# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from email.utils import formataddr
from unittest.mock import patch

from odoo.addons.mail.tests.common import BaseFunctionalTest, MockEmails
from odoo.addons.mail.tests.data.test_mail_data import MAIL_TEMPLATE_PLAINTEXT
from odoo.exceptions import AccessError
from odoo.tools import mute_logger


class TestMessagePost(BaseFunctionalTest, MockEmails):

    def setUp(self):
        super(TestMessagePost, self).setUp()

        # additional recipients
        self.partner_1 = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'Sylvie Lelitre',
            'email': 'sylvie.lelitre@agrolait.com',
        })
        self.partner_2 = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'Raoulette Lelitre',
            'email': 'raoulette.lelitre@agrolait.com',
        })

        # configure mailing
        self.alias_domain = 'schlouby.fr'
        self.alias_catchall = 'test+catchall'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', self.alias_domain)
        self.env['ir.config_parameter'].set_param('mail.catchall.alias', self.alias_catchall)

        # admin should not receive emails
        self.user_admin.write({'notification_type': 'email'})

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_post_notifications(self):
        _body, _body_alt, _subject = '<p>Test Body</p>', 'Test Body', 'Test Subject'

        # subscribe second employee to the group to test notifications
        self.test_record.message_subscribe_users(user_ids=[self.user_admin.id])

        msg = self.test_record.sudo(self.user_employee).message_post(
            body=_body, subject=_subject,
            message_type='comment', subtype='mt_comment',
            partner_ids=[self.partner_1.id, self.partner_2.id]
        )

        # message content
        self.assertEqual(msg.subject, _subject)
        self.assertEqual(msg.body, _body)
        self.assertEqual(msg.partner_ids, self.partner_1 | self.partner_2)
        self.assertEqual(msg.needaction_partner_ids, self.user_admin.partner_id | self.partner_1 | self.partner_2)
        self.assertEqual(msg.channel_ids, self.env['mail.channel'])

        # notifications emails should have been deleted
        self.assertFalse(self.env['mail.mail'].search([('mail_message_id', '=', msg.message_id)]),
                         'message_post: mail.mail notifications should have been auto-deleted')

        # notification emails
        self.assertEqual(len(self._mails), 3, '3 notification emails: partner_1, partner_2 and admin that works using emails')
        self.assertEqual(set(m['email_from'] for m in self._mails),
                         set([formataddr((self.user_employee.name, self.user_employee.email))]))
        self.assertEqual(set(email for m in self._mails for email in m['email_to']),
                         set([formataddr((self.partner_1.name, self.partner_1.email)),
                              formataddr((self.partner_2.name, self.partner_2.email)),
                              formataddr((self.user_admin.name, self.user_admin.email))]))
        self.assertFalse(any(len(m['email_to']) != 1 for m in self._mails),
                         'message_post: notification email should be sent to one partner at a time')
        self.assertEqual(set(m['reply_to'] for m in self._mails), set([msg.reply_to]),
                         'message_post: notification email should use group aliases and data for reply to')
        self.assertTrue(all(_subject == m['subject'] for m in self._mails))
        self.assertTrue(all(_body in m['body'] for m in self._mails))
        self.assertTrue(all(_body_alt in m['body_alternative'] for m in self._mails))
        self.assertFalse(any(m['references'] for m in self._mails))

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_post_attachments(self):
        _attachments = [
            ('List1', b'My first attachment'),
            ('List2', b'My second attachment')
        ]
        _attach_1 = self.env['ir.attachment'].sudo(self.user_employee).create({
            'name': 'Attach1', 'datas_fname': 'Attach1',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'mail.compose.message', 'res_id': 0})
        _attach_2 = self.env['ir.attachment'].sudo(self.user_employee).create({
            'name': 'Attach2', 'datas_fname': 'Attach2',
            'datas': 'bWlncmF0aW9uIHRlc3Q=',
            'res_model': 'mail.compose.message', 'res_id': 0})

        msg = self.test_record.sudo(self.user_employee).message_post(
            body='Test', subject='Test',
            message_type='comment', subtype='mt_comment',
            attachment_ids=[_attach_1.id, _attach_2.id],
            partner_ids=[self.partner_1.id],
            attachments=_attachments,
        )

        # message attachments
        self.assertEqual(len(msg.attachment_ids), 4)
        self.assertEqual(set(msg.attachment_ids.mapped('res_model')), set([self.test_record._name]))
        self.assertEqual(set(msg.attachment_ids.mapped('res_id')), set([self.test_record.id]))
        self.assertEqual(set([base64.b64decode(x) for x in msg.attachment_ids.mapped('datas')]),
                         set([b'migration test', _attachments[0][1], _attachments[1][1]]))
        self.assertTrue(set([_attach_1.id, _attach_2.id]).issubset(msg.attachment_ids.ids),
                        'message_post: mail.message attachments duplicated')

        # notification email attachments
        self.assertEqual(len(self._mails), 1)
        self.assertEqual(len(self._mails[0]['attachments']), 4)
        self.assertIn(('List1', b'My first attachment', 'application/octet-stream'), self._mails[0]['attachments'])
        self.assertIn(('List2', b'My second attachment', 'application/octet-stream'), self._mails[0]['attachments'])
        self.assertIn(('Attach1', b'migration test', 'application/octet-stream'),  self._mails[0]['attachments'])
        self.assertIn(('Attach2', b'migration test', 'application/octet-stream'), self._mails[0]['attachments'])

    # @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_answer(self):
        parent_msg = self.test_record.sudo(self.user_employee).message_post(
            body='<p>Test</p>', subject='Test Subject',
            message_type='comment', subtype='mt_comment')

        self.assertEqual(parent_msg.partner_ids, self.env['res.partner'])

        msg = self.test_record.sudo(self.user_employee).message_post(
            body='<p>Test Answer</p>',
            message_type='comment', subtype='mt_comment',
            partner_ids=[self.partner_1.id],
            parent_id=parent_msg.id)

        self.assertEqual(msg.parent_id.id, parent_msg.id)
        self.assertEqual(msg.partner_ids, self.partner_1)
        self.assertEqual(parent_msg.partner_ids, self.env['res.partner'])

        # check notification emails: references
        self.assertTrue(all('openerp-%d-mail.test.simple' % self.test_record.id in m['references'] for m in self._mails))

        new_msg = self.test_record.sudo(self.user_employee).message_post(
            body='<p>Test Answer Bis</p>',
            message_type='comment', subtype='mt_comment',
            parent_id=msg.id)

        self.assertEqual(new_msg.parent_id.id, parent_msg.id, 'message_post: flatten error')
        self.assertEqual(new_msg.partner_ids, self.env['res.partner'])

    # @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_portal_ok(self):
        from odoo.addons.mail.tests.models.test_mail_models import MailTestSimple

        portal_user = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })

        with patch.object(MailTestSimple, 'check_access_rights', return_value=True):
            self.test_record.message_subscribe((self.partner_1 | self.user_employee.partner_id).ids)
            new_msg = self.test_record.sudo(portal_user).message_post(
                body='<p>Test</p>', subject='Subject',
                message_type='comment', subtype='mt_comment')

        self.assertEqual(new_msg.sudo().needaction_partner_ids, (self.partner_1 | self.user_employee.partner_id))
        self.assertEqual(
            set(m['email_to'][0] for m in self._mails),
            set(['%s' % formataddr((self.partner_1.name, self.partner_1.email)),
                 '%s' % formataddr((self.user_employee.name, self.user_employee.email))
                 ]))

    def test_post_portal_crash(self):
        portal_user = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })

        with self.assertRaises(AccessError):
            self.test_record.sudo(portal_user).message_post(
                body='<p>Test</p>', subject='Subject',
                message_type='comment', subtype='mt_comment')

    # @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_post_internal(self):
        self.test_record.message_subscribe([self.user_admin.partner_id.id])
        msg = self.test_record.sudo(self.user_employee).message_post(
            body='My Body', subject='My Subject',
            message_type='comment', subtype='mt_note')
        self.assertEqual(msg.partner_ids, self.env['res.partner'])
        self.assertEqual(msg.needaction_partner_ids, self.env['res.partner'])

        self.format_and_process(
            MAIL_TEMPLATE_PLAINTEXT,
            email_from=self.user_admin.email,
            msg_id='<1198923581.41972151344608186800.JavaMail.diff1@agrolait.com>',
            to='not_my_businesss@example.com',
            extra='In-Reply-To:\r\n\t%s\n' % msg.message_id)
        reply = self.test_record.message_ids - msg
        self.assertTrue(reply)
        self.assertEqual(reply.subtype_id, self.env.ref('mail.mt_note'))
        self.assertEqual(reply.needaction_partner_ids, self.user_employee.partner_id)
        self.assertEqual(reply.parent_id, msg)


class TestComposer(BaseFunctionalTest, MockEmails):

    def setUp(self):
        super(TestComposer, self).setUp()

        # additional recipients
        self.partner_1 = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'Sylvie Lelitre',
            'email': 'sylvie.lelitre@agrolait.com',
        })
        self.partner_2 = self.env['res.partner'].with_context(self._quick_create_ctx).create({
            'name': 'Raoulette Lelitre',
            'email': 'raoulette.lelitre@agrolait.com',
        })

        # configure mailing
        self.alias_domain = 'schlouby.fr'
        self.alias_catchall = 'test+catchall'
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', self.alias_domain)
        self.env['ir.config_parameter'].set_param('mail.catchall.alias', self.alias_catchall)

        # admin should not receive emails
        self.user_admin.write({'notification_type': 'email'})

    # @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_comment(self):
        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_model': self.test_record._name,
            'default_res_id': self.test_record.id,
        }).sudo(self.user_employee).create({
            'body': '<p>Test Body</p>',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        self.assertEqual(composer.composition_mode,  'comment')
        self.assertEqual(composer.model, self.test_record._name)
        self.assertEqual(composer.subject, 'Re: %s' % self.test_record.name)
        self.assertEqual(composer.record_name, self.test_record.name)

        composer.send_mail()
        message = self.test_record.message_ids[0]

        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'comment',
            'default_res_id': self.test_record.id,
            'default_parent_id': message.id
        }).sudo(self.user_employee).create({})

        composer.send_mail()

        message = self.test_record.message_ids[0]

    # @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_mass_mail(self):
        test_record_2 = self.env['mail.test.simple'].with_context(self._quick_create_ctx).create({'name': 'Test2'})

        composer = self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': self.test_record._name,
            'default_res_id': False,
            'active_ids': [self.test_record.id, test_record_2.id]
        }).sudo(self.user_employee).create({
            'subject': 'Testing ${object.name}',
            'body': '<p>${object.name}</p>',
            'partner_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]
        })
        composer.with_context({
            'default_res_id': -1,
            'active_ids': [self.test_record.id, test_record_2.id]
        }).send_mail()

        # check mail_mail
        mails = self.env['mail.mail'].search([('subject', 'ilike', 'Testing')])
        for mail in mails:
            self.assertEqual(mail.recipient_ids, self.partner_1 | self.partner_2,
                             'compose wizard: mail_mail mass mailing: mail.mail in mass mail incorrect recipients')

        # check message on test_record
        message1 = self.test_record.message_ids[0]
        self.assertEqual(message1.subject, 'Testing %s' % self.test_record.name)
        self.assertEqual(message1.body, '<p>%s</p>' % self.test_record.name)

        # check message on test_record_2
        message1 = test_record_2.message_ids[0]
        self.assertEqual(message1.subject, 'Testing %s' % test_record_2.name)
        self.assertEqual(message1.body, '<p>%s</p>' % test_record_2.name)

    # @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_composer_mass_mail_active_domain(self):
        test_record_2 = self.env['mail.test.simple'].with_context(self._quick_create_ctx).create({'name': 'Test2'})

        self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': self.test_record._name,
            'default_use_active_domain': True,
            'active_ids': [self.test_record.id],
            'active_domain': [('name', 'in', ['%s' % self.test_record.name, '%s' % test_record_2.name])],
        }).sudo(self.user_employee).create({
            'subject': 'From Composer Test',
            'body': '${object.name}',
        }).send_mail()

        self.assertEqual(self.test_record.message_ids[0].subject, 'From Composer Test')
        self.assertEqual(test_record_2.message_ids[0].subject, 'From Composer Test')

    # @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_message_compose_mass_mail_no_active_domain(self):
        test_record_2 = self.env['mail.test.simple'].with_context(self._quick_create_ctx).create({'name': 'Test2'})

        self.env['mail.compose.message'].with_context({
            'default_composition_mode': 'mass_mail',
            'default_model': self.test_record._name,
            'default_use_active_domain': False,
            'active_ids': [self.test_record.id],
            'active_domain': [('name', 'in', ['%s' % self.test_record.name, '%s' % test_record_2.name])],
        }).sudo(self.user_employee).create({
            'subject': 'From Composer Test',
            'body': '${object.name}',
        }).send_mail()

        self.assertEqual(self.test_record.message_ids[0].subject, 'From Composer Test')
        self.assertFalse(test_record_2.message_ids.ids)

    def test_message_compose_portal_ok(self):
        from odoo.addons.mail.tests.models.test_mail_models import MailTestSimple

        portal_user = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'Chell Gladys',
            'login': 'chell',
            'email': 'chell@gladys.portal',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })

        with patch.object(MailTestSimple, 'check_access_rights', return_value=True):
            ComposerPortal = self.env['mail.compose.message'].sudo(portal_user)

            compose = ComposerPortal.with_context({
                'default_composition_mode': 'comment',
                'default_model': self.test_record._name,
                'default_res_id': self.test_record.id,
            }).create({
                'subject': 'Subject',
                'body': 'Body text',
                'partner_ids': []})
            compose.send_mail()

            # Do: Chell replies to a Pigs message using the composer
            compose = ComposerPortal.with_context({
                'default_composition_mode': 'comment',
                'default_parent_id': self.test_record.message_ids.ids[0],
            }).create({
                'subject': 'Subject',
                'body': 'Body text'})
            compose.send_mail()
