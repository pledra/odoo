odoo.define('web_editor.web_editor_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var core = require('web.core');
var concurrency = require('web.concurrency');

var _t = core._t;

QUnit.module('web_editor', {
    beforeEach: function() {
        this.data = {
            'mass.mailing': {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    body: {string: "Message Body", type: "html"},
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    body: "<div class='field_body'>yep</div>",
                }],
                onchanges: {},
            },
            'mail.template': {
                fields: {
                    partner_name: { string: "record.name", type: "char" },
                    body_html: { string: "body", type: "html" }
                },
                records: [{
                    id: 1,
                    partner_name: "record.partner_id.name",
                    body_html: "<span t-field='record.partner_id.name'/>",
                }],
            },
        };
    }
});

QUnit.test('field html widget', function (assert) {
    var done = assert.async();
    assert.expect(3);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<field name="body" widget="html" style="height: 100px"/>' +
            '</form>',
        res_id: 1,
    });

    assert.strictEqual(form.$('.field_body').text(), 'yep',
        "should have rendered a div with correct content in readonly");
    assert.strictEqual(form.$('div[name=body]').attr('style'), 'height: 100px',
        "should have applied the style correctly");

    form.$buttons.find('.o_form_button_edit').click();

    assert.strictEqual(form.$('.note-editable').html(), '<div class="field_body">yep</div>',
            "should have rendered the field correctly in edit");

    // summernote invokes handlers after a setTimeout, so we must wait as well
    // before destroying the widget (otherwise we'll have a crash later on)
    setTimeout(function () {
        form.destroy();
        done();
    }, 0);
});

QUnit.test('field html widget (with options inline-style)', function (assert) {
    var done = assert.async();
    assert.expect(3);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<field name="body" widget="html" style="height: 100px" options="{\'style-inline\': true}"/>' +
            '</form>',
        res_id: 1,
    });

    assert.strictEqual(form.$('iframe').length, 1,
        "should have rendered an iframe without crashing in readonly");
    assert.strictEqual(form.$('div[name=body]').attr('style'), 'height: 100px',
        "should have applied the style correctly");

    form.$buttons.find('.o_form_button_edit').click();

    assert.strictEqual(form.$('.note-editable').html(), '<div class="field_body">yep</div>',
            "should have rendered the field correctly in edit");

    // summernote invokes handlers after a setTimeout, so we must wait as well
    // before destroying the widget (otherwise we'll have a crash later on)
    setTimeout(function () {
        form.destroy();
        done();
    }, 0);
});

QUnit.test('field html translatable', function (assert) {
    assert.expect(3);

    var multiLang = _t.database.multi_lang;
    _t.database.multi_lang = true;

    this.data['mass.mailing'].fields.body.translate = true;

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<field name="body" widget="html"/>' +
            '</form>',
        res_id: 1,
        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_button' && args.method === 'translate_fields') {
                assert.deepEqual(args.args, ['mass.mailing',1,'body',{}], "should call 'call_button' route");
                return $.when();
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.strictEqual(form.$('.oe_form_field_html_text .o_field_translate').length, 0,
        "should not have a translate button in readonly mode");

    form.$buttons.find('.o_form_button_edit').click();
    var $button = form.$('.oe_form_field_html_text .o_field_translate');
    assert.strictEqual($button.length, 1, "should have a translate button");
    $button.click();

    form.destroy();
    _t.database.multi_lang = multiLang;
});

QUnit.test('field html_frame widget', function (assert) {
    assert.expect(6);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<field name="body" widget="html_frame" options="{\'editor_url\': \'/test\'}"/>' +
            '</form>',
        res_id: 1,
        session: {user_context: {lang: "en_us"}},
        mockRPC: function (route) {
            if (_.str.startsWith(route, '/test')) {
                // those tests will be executed twice, once in readonly and once in edit
                assert.ok(route.search('model=mass.mailing') > 0,
                    "the route should specify the correct model");
                assert.ok(route.search('res_id=1') > 0,
                    "the route should specify the correct id");
                return $.when();
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.strictEqual(form.$('iframe').length, 1, "should have rendered an iframe without crashing");

    form.$buttons.find('.o_form_button_edit').click();

    assert.strictEqual(form.$('iframe').length, 1, "should have rendered an iframe without crashing");

    form.destroy();
});

QUnit.test('field htmlsimple does not crash when commitChanges is called in mode=readonly', function (assert) {
    assert.expect(1);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<header>' +
                    '<button name="some_method" class="s" string="Do it" type="object"/>' +
                '</header>' +
                '<sheet>' +
                    '<field name="body"/>' +
                '</sheet>' +
            '</form>',
        res_id: 1,
        intercepts: {
            execute_action: function () {
                assert.step('execute_action');
            }
        },
    });

    form.$('button:contains(Do it)').click();
    form.destroy();
});

QUnit.test('html_frame does not crash when saving in readonly', function (assert) {
    // The 'Save' action may be triggered even in readonly (e.g. when clicking
    // on a button in the form view)
    assert.expect(0);

    var form = testUtils.createView({
        View: FormView,
        model: 'mass.mailing',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="body" widget="html_frame" options="{\'editor_url\': \'/test\'}"/>' +
                '</sheet>' +
            '</form>',
        res_id: 1,
        mockRPC: function (route) {
            if (_.str.startsWith(route, '/test')) {
                // manually call the callback to simulate that the iframe has
                // been correctly loaded
                window.odoo[$.deparam(route).callback + '_content'].call();
                return $.when();
            }
            return this._super.apply(this, arguments);
        },
    });

    form.saveRecord(); // before the fix done in this commit, it crashed here
    form.destroy();
});

QUnit.test('Qweb Expression editor test for template', function (assert) {
    var done = assert.async();
    assert.expect(5);

    var form = testUtils.createView({
        View: FormView,
        model: 'mail.template',
        data: this.data,
        arch: '<form string="Partners">' +
                '<field name="body_html" widget="html" />' +
            '</form>',
        res_id: 1,
    });

    form.$buttons.find('.o_form_button_edit').click();

    assert.ok($('.modal').length, 'a modal should be opened');

    // checking tag value in form before edit
    assert.strictEqual(form.$('.o_t_expression').text(), 'record.partner_id.name',
            "value of t-tag in form before edit should be record.partner_id.name");

    form.$('.o_t_expression').click();

    // edit tag value
    $('.modal-dialog .t-tag').val('<span t-field="record.partner_id.firstname"></span>');

    $('.modal button.btn-primary').click();

    // checking tag value in form after click on ok
    assert.strictEqual(form.$('.o_t_expression').text(), 'record.partner_id.firstname',
            "value of t-tag in form should be record.partner_id.firstname after click on ok");

    // checking for discard after edit tag value
    form.$buttons.find('.o_form_button_edit').click();
    form.$('.o_t_expression').click();

    $('.modal-dialog .t-tag').val('<span t-field="record.partner_id.firstname"></span>');
    $('.modal button.btn-default').click();

    // checking tag value in form after click on discard
    assert.strictEqual(form.$('.o_t_expression').text(), 'record.partner_id.name',
            "value of t-tag in form should be record.partner_id.name after click on discard");

    form.$buttons.find('.o_form_button_cancel').click()

    // checking tag value after click on cancel button of form
    assert.strictEqual(form.$('.o_t_expression').text(), 'record.partner_id.name',
            "value of t-tag should be record.partner_id.name when click on discard button of form after edit");

    return concurrency.delay(0).then(function () {
        form.destroy();
        done();
    });
});
});
