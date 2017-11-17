odoo.define('web.action_manager_tests', function (require) {
"use strict";

var ActionManager = require('web.ActionManager');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

var createActionManager = function (params) {
    params = params || {};
    var $target = $('#qunit-fixture');
    if (params.debug) {
        $target = $('body');
    }

    var widget = new Widget();
    testUtils.addMockEnvironment(widget, params);
    widget.appendTo($target);
    widget.$el.addClass('o_web_client');

    var actionManager = new ActionManager(widget);
    var originalDestroy = ActionManager.prototype.destroy;
    actionManager.destroy = function () {
        actionManager.destroy = originalDestroy;
        widget.destroy();
    };
    actionManager.appendTo(widget.$el);

    return actionManager;
};

QUnit.module('ActionManager', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                },
                records: [
                    {id: 1, display_name: "First record", foo: "yop"},
                    {id: 2, display_name: "Second record", foo: "blip"},
                    {id: 3, display_name: "Third record", foo: "gnap"},
                    {id: 4, display_name: "Fourth record", foo: "plop"},
                    {id: 5, display_name: "Fifth record", foo: "zoup"},
                ],
            },
        };

        this.actions = [{
            id: 1,
            display_name: 'Partners',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[1, 'kanban']],
        }, {
            id: 2,
            type: 'ir.actions.server',
        }, {
            id: 3,
            display_name: 'Partners',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'list'], [1, 'kanban'], [false, 'form']],
        }, {
            id: 4,
            display_name: 'Partners',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[1, 'kanban'], [2, 'list'], [false, 'form']],
        }, {
            id: 5,
            display_name: 'Create a Partner',
            res_model: 'partner',
            target: 'new',
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
        }];
        this.archs = {
            // kanban views
            'partner,1,kanban': '<kanban><templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                '</t></templates></kanban>',

            // list views
            'partner,false,list': '<tree><field name="foo"/></tree>',
            'partner,2,list': '<tree limit="3"><field name="foo"/></tree>',

            // form views
            'partner,false,form': '<form>' +
                    '<header>' +
                        '<button name="object" string="Call method" type="object"/>' +
                        '<button name="4" string="Execute action" type="action"/>' +
                    '</header>' +
                    '<group>' +
                        '<field name="display_name"/>' +
                        '<field name="foo"/>' +
                    '</group>' +
                '</form>',

            // search views
            'partner,false,search': '<search><field name="foo" string="Foo"/></search>',
        };
    },
}, function () {

    QUnit.module('Client Actions');

    QUnit.test('can execute client actions from tag name', function (assert) {
        assert.expect(3);

        var ClientAction = Widget.extend({
            className: 'o_client_action_test',
            start: function () {
                this.$el.text('Hello World');
            },
        });
        core.action_registry.add('HelloWorldTest', ClientAction);

        var actionManager = createActionManager({
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            }
        });
        actionManager.do_action('HelloWorldTest');

        assert.strictEqual($('.o_control_panel:visible').length, 0, // AAB: global selector until the ControlPanel is moved from ActionManager to the Views
            "shouldn't have rendered a control panel");
        assert.strictEqual(actionManager.$('.o_client_action_test').text(),
            'Hello World', "should have correctly rendered the client action");
        assert.verifySteps([]);

        actionManager.destroy();
        delete core.action_registry.map.HelloWorldTest;
    });

    QUnit.test('client action with control panel', function (assert) {
        assert.expect(4);

        var ClientAction = Widget.extend(ControlPanelMixin, {
            className: 'o_client_action_test',
            start: function () {
                this.$el.text('Hello World');
                this.set('title', 'Hello'); // AAB: drop this and replace by getTitle()
            },
        });
        core.action_registry.add('HelloWorldTest', ClientAction);

        var actionManager = createActionManager();
        actionManager.do_action('HelloWorldTest');

        assert.strictEqual($('.o_control_panel:visible').length, 1,
            "should have rendered a control panel");
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 1,
            "there should be one controller in the breadcrumbs");
        assert.strictEqual($('.o_control_panel .breadcrumb li').text(), 'Hello',
            "breadcrumbs should still display the title of the controller");
        assert.strictEqual(actionManager.$('.o_client_action_test').text(),
            'Hello World', "should have correctly rendered the client action");

        actionManager.destroy();
        delete core.action_registry.map.HelloWorldTest;
    });

    QUnit.module('Server actions');

    QUnit.test('can execute server actions from db ID', function (assert) {
        assert.expect(9);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === '/web/action/run') {
                    assert.strictEqual(args.action_id, 2,
                        "should call the correct server action");
                    return $.when(1); // execute action 1
                }
                return this._super.apply(this, arguments);
            },
        });
        actionManager.do_action(2);

        assert.strictEqual($('.o_control_panel:visible').length, 1,
            "should have rendered a control panel");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 1,
            "should have rendered a kanban view");
        assert.verifySteps([
            '/web/action/load',
            '/web/action/run',
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read',
        ]);

        actionManager.destroy();
    });

    QUnit.module('Window Actions');

    QUnit.test('can execute act_window actions from db ID', function (assert) {
        assert.expect(6);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        actionManager.do_action(1);

        assert.strictEqual($('.o_control_panel').length, 1,
            "should have rendered a control panel");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 1,
            "should have rendered a kanban view");
        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read',
        ]);

        actionManager.destroy();
    });

    QUnit.test('can switch between views', function (assert) {
        assert.expect(18);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        actionManager.do_action(3);

        assert.strictEqual(actionManager.$('.o_list_view').length, 1,
            "should display the list view");

        // switch to kanban view
        $('.o_control_panel .o_cp_switch_kanban').click();
        assert.strictEqual(actionManager.$('.o_list_view').length, 0,
            "should no longer display the list view");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 1,
            "should display the kanban view");

        // switch back to list view
        $('.o_control_panel .o_cp_switch_list').click();
        assert.strictEqual(actionManager.$('.o_list_view').length, 1,
            "should display the list view");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 0,
            "should no longer display the kanban view");

        // open a record in form view
        actionManager.$('.o_list_view .o_data_row:first').click();
        assert.strictEqual(actionManager.$('.o_list_view').length, 0,
            "should no longer display the list view");
        assert.strictEqual(actionManager.$('.o_form_view').length, 1,
            "should display the form view");
        assert.strictEqual(actionManager.$('.o_field_widget[name=foo]').text(), 'yop',
            "should have opened the correct record");

        // go back to list view using the breadcrumbs
        $('.o_control_panel .breadcrumb a').click();
        assert.strictEqual(actionManager.$('.o_list_view').length, 1,
            "should display the list view");
        assert.strictEqual(actionManager.$('.o_form_view').length, 0,
            "should no longer display the form view");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read', // list
            '/web/dataset/search_read', // kanban
            '/web/dataset/search_read', // list
            'read', // form
            '/web/dataset/search_read', // list
        ]);

        actionManager.destroy();
    });

    QUnit.test('breadcrumbs are updated when switching between views', function (assert) {
        assert.expect(10);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        actionManager.do_action(3);

        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 1,
            "there should be one controller in the breadcrumbs");
        assert.strictEqual($('.o_control_panel .breadcrumb li').text(), 'Partners',
            "breadcrumbs should display the display_name of the action");

        // switch to kanban view
        $('.o_control_panel .o_cp_switch_kanban').click();
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 1,
            "there should still be one controller in the breadcrumbs");
        assert.strictEqual($('.o_control_panel .breadcrumb li').text(), 'Partners',
            "breadcrumbs should still display the display_name of the action");

        // switch back to list view
        $('.o_control_panel .o_cp_switch_list').click();
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 1,
            "there should still be one controller in the breadcrumbs");
        assert.strictEqual($('.o_control_panel .breadcrumb li').text(), 'Partners',
            "breadcrumbs should still display the display_name of the action");

        // open a record in form view
        actionManager.$('.o_list_view .o_data_row:first').click();
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($('.o_control_panel .breadcrumb li:last').text(), 'First record',
            "breadcrumbs should contain the display_name of the opened record");

        // go back to list view using the breadcrumbs
        $('.o_control_panel .breadcrumb a').click();
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 1,
            "there should be one controller in the breadcrumbs");
        assert.strictEqual($('.o_control_panel .breadcrumb li').text(), 'Partners',
            "breadcrumbs should display the display_name of the action");

        actionManager.destroy();
    });

    QUnit.test('switch buttons are updated when switching between views', function (assert) {
        assert.expect(13);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        actionManager.do_action(3);

        assert.strictEqual($('.o_control_panel .o_cp_switch_buttons button').length, 2,
            "should have two switch buttons (list and kanban)");
        assert.strictEqual($('.o_control_panel .o_cp_switch_buttons button.active').length, 1,
            "should have only one active button");
        assert.ok($('.o_control_panel .o_cp_switch_buttons button:first').hasClass('o_cp_switch_list'),
            "list switch button should be the first one");
        assert.ok($('.o_control_panel .o_cp_switch_list').hasClass('active'),
            "list should be the active view");

        // switch to kanban view
        $('.o_control_panel .o_cp_switch_kanban').click();
        assert.strictEqual($('.o_control_panel .o_cp_switch_buttons button').length, 2,
            "should still have two switch buttons (list and kanban)");
        assert.strictEqual($('.o_control_panel .o_cp_switch_buttons button.active').length, 1,
            "should still have only one active button");
        assert.ok($('.o_control_panel .o_cp_switch_buttons button:first').hasClass('o_cp_switch_list'),
            "list switch button should still be the first one");
        assert.ok($('.o_control_panel .o_cp_switch_kanban').hasClass('active'),
            "kanban should now be the active view");

        // switch back to list view
        $('.o_control_panel .o_cp_switch_list').click();
        assert.strictEqual($('.o_control_panel .o_cp_switch_buttons button').length, 2,
            "should still have two switch buttons (list and kanban)");
        assert.ok($('.o_control_panel .o_cp_switch_list').hasClass('active'),
            "list should now be the active view");

        // open a record in form view
        actionManager.$('.o_list_view .o_data_row:first').click();
        assert.strictEqual($('.o_control_panel .o_cp_switch_buttons button').length, 0,
            "should not have any switch buttons");

        // go back to list view using the breadcrumbs
        $('.o_control_panel .breadcrumb a').click();
        assert.strictEqual($('.o_control_panel .o_cp_switch_buttons button').length, 2,
            "should have two switch buttons (list and kanban)");
        assert.ok($('.o_control_panel .o_cp_switch_list').hasClass('active'),
            "list should be the active view");

        actionManager.destroy();
    });

    QUnit.test('pager is updated when switching between views', function (assert) {
        assert.expect(10);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        actionManager.do_action(4);

        assert.strictEqual($('.o_control_panel .o_pager_value').text(), '1-5',
            "value should be correct for kanban");
        assert.strictEqual($('.o_control_panel .o_pager_limit').text(), '5',
            "limit should be correct for kanban");

        // switch to list view
        $('.o_control_panel .o_cp_switch_list').click();
        assert.strictEqual($('.o_control_panel .o_pager_value').text(), '1-3',
            "value should be correct for list");
        assert.strictEqual($('.o_control_panel .o_pager_limit').text(), '5',
            "limit should be correct for list");

        // open a record in form view
        actionManager.$('.o_list_view .o_data_row:first').click();
        assert.strictEqual($('.o_control_panel .o_pager_value').text(), '1',
            "value should be correct for form");
        assert.strictEqual($('.o_control_panel .o_pager_limit').text(), '3',
            "limit should be correct for form");

        // go back to list view using the breadcrumbs
        $('.o_control_panel .breadcrumb a').click();
        assert.strictEqual($('.o_control_panel .o_pager_value').text(), '1-3',
            "value should be correct for list");
        assert.strictEqual($('.o_control_panel .o_pager_limit').text(), '5',
            "limit should be correct for list");

        // switch back to kanban view
        $('.o_control_panel .o_cp_switch_kanban').click();
        assert.strictEqual($('.o_control_panel .o_pager_value').text(), '1-5',
            "value should be correct for kanban");
        assert.strictEqual($('.o_control_panel .o_pager_limit').text(), '5',
            "limit should be correct for kanban");

        actionManager.destroy();
    });

    QUnit.test('there is no flickering when switching between views', function (assert) {
        assert.expect(20);

        var def;
        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function () {
                var result = this._super.apply(this, arguments);
                return $.when(def).then(_.constant(result));
            },
        });
        actionManager.do_action(3);

        // switch to kanban view
        def = $.Deferred();
        $('.o_control_panel .o_cp_switch_kanban').click();
        assert.strictEqual(actionManager.$('.o_list_view').length, 1,
            "should still display the list view");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 0,
            "shouldn't display the kanban view yet");
        def.resolve();
        assert.strictEqual(actionManager.$('.o_list_view').length, 0,
            "shouldn't display the list view anymore");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 1,
            "should now display the kanban view");

        // switch back to list view
        def = $.Deferred();
        $('.o_control_panel .o_cp_switch_list').click();
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 1,
            "should still display the kanban view");
        assert.strictEqual(actionManager.$('.o_list_view').length, 0,
            "shouldn't display the list view yet");
        def.resolve();
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 0,
            "shouldn't display the kanban view anymore");
        assert.strictEqual(actionManager.$('.o_list_view').length, 1,
            "should now display the list view");

        // open a record in form view
        def = $.Deferred();
        actionManager.$('.o_list_view .o_data_row:first').click();
        assert.strictEqual(actionManager.$('.o_list_view').length, 1,
            "should still display the list view");
        assert.strictEqual(actionManager.$('.o_form_view').length, 0,
            "shouldn't display the form view yet");
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 1,
            "there should still be one controller in the breadcrumbs");
        def.resolve();
        assert.strictEqual(actionManager.$('.o_list_view').length, 0,
            "should no longer display the list view");
        assert.strictEqual(actionManager.$('.o_form_view').length, 1,
            "should display the form view");
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 2,
            "there should be two controllers in the breadcrumbs");

        // go back to list view using the breadcrumbs
        def = $.Deferred();
        $('.o_control_panel .breadcrumb a').click();
        assert.strictEqual(actionManager.$('.o_form_view').length, 1,
            "should still display the form view");
        assert.strictEqual(actionManager.$('.o_list_view').length, 0,
            "shouldn't display the list view yet");
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 2,
            "there should still be two controllers in the breadcrumbs");
        def.resolve();
        assert.strictEqual(actionManager.$('.o_form_view').length, 0,
            "should no longer display the form view");
        assert.strictEqual(actionManager.$('.o_list_view').length, 1,
            "should display the list view");
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 1,
            "there should be one controller in the breadcrumbs");

        actionManager.destroy();
    });

    QUnit.test('breadcrumbs are updated when display_name changes', function (assert) {
        assert.expect(4);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        actionManager.do_action(3);

        // open a record in form view
        actionManager.$('.o_list_view .o_data_row:first').click();
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($('.o_control_panel .breadcrumb li:last').text(), 'First record',
            "breadcrumbs should contain the display_name of the opened record");

        // switch to edit mode and change the display_name
        $('.o_control_panel .o_form_button_edit').click();
        actionManager.$('.o_field_widget[name=display_name]').val('New name').trigger('input');
        $('.o_control_panel .o_form_button_save').click();

        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 2,
            "there should still be two controllers in the breadcrumbs");
        assert.strictEqual($('.o_control_panel .breadcrumb li:last').text(), 'New name',
            "breadcrumbs should contain the display_name of the opened record");

        actionManager.destroy();
    });

    QUnit.test('reload previous controller when discarding a new record', function (assert) {
        assert.expect(8);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        actionManager.do_action(3);

        // create a new record
        $('.o_control_panel .o_list_button_add').click();
        assert.strictEqual(actionManager.$('.o_form_view.o_form_editable').length, 1,
            "should have opened the form view in edit mode");

        // discard
        $('.o_control_panel .o_form_button_cancel').click();
        assert.strictEqual(actionManager.$('.o_list_view').length, 1,
            "should have switched back to the list view");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read', // list
            'default_get', // form
            '/web/dataset/search_read', // list
        ]);

        actionManager.destroy();
    });

    QUnit.test('requests for execute_action of type object are handled', function (assert) {
        assert.expect(10);

        var self = this;
        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === '/web/dataset/call_button') {
                    assert.deepEqual(args, {
                        args: [[1], {some_key: 2}],
                        method: 'object',
                        model: 'partner',
                    }, "should call route with correct arguments");
                    var record = _.findWhere(self.data.partner.records, {id: args.args[0][0]});
                    record.foo = 'value changed';
                    return $.when(false);
                }
                return this._super.apply(this, arguments);
            },
            session: {user_context: {
                some_key: 2,
            }},
        });
        actionManager.do_action(3);

        // open a record in form view
        actionManager.$('.o_list_view .o_data_row:first').click();
        assert.strictEqual(actionManager.$('.o_field_widget[name=foo]').text(), 'yop',
            "check initial value of 'yop' field");

        // click on 'Call method' button (should call an Object method)
        actionManager.$('.o_form_view button:contains(Call method)').click();
        assert.strictEqual(actionManager.$('.o_field_widget[name=foo]').text(), 'value changed',
            "'yop' has been changed by the server, and should be updated in the UI");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read', // list for action 3
            'read', // form for action 3
            'object', // click on 'Call method' button
            'read', // re-read form view
        ]);

        actionManager.destroy();
    });

    QUnit.test('requests for execute_action of type action are handled', function (assert) {
        assert.expect(11);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        actionManager.do_action(3);

        // open a record in form view
        actionManager.$('.o_list_view .o_data_row:first').click();

        // click on 'Execute action' button (should execute an action)
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 2,
            "there should be two parts in the breadcrumbs");
        actionManager.$('.o_form_view button:contains(Execute action)').click();
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 3,
            "the returned action should have been stacked over the previous one");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 1,
            "the returned action should have been executed");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read', // list for action 3
            'read', // form for action 3
            '/web/action/load', // click on 'Execute action' button
            'load_views',
            '/web/dataset/search_read', // kanban for action 4
        ]);

        actionManager.destroy();
    });

    QUnit.test('can open different records from a multi record view', function (assert) {
        assert.expect(11);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        actionManager.do_action(3);

        // open the first record in form view
        actionManager.$('.o_list_view .o_data_row:first').click();
        assert.strictEqual($('.o_control_panel .breadcrumb li:last').text(), 'First record',
            "breadcrumbs should contain the display_name of the opened record");
        assert.strictEqual(actionManager.$('.o_field_widget[name=foo]').text(), 'yop',
            "should have opened the correct record");

        // go back to list view using the breadcrumbs
        $('.o_control_panel .breadcrumb a').click();

        // open the second record in form view
        actionManager.$('.o_list_view .o_data_row:nth(1)').click();
        assert.strictEqual($('.o_control_panel .breadcrumb li:last').text(), 'Second record',
            "breadcrumbs should contain the display_name of the opened record");
        assert.strictEqual(actionManager.$('.o_field_widget[name=foo]').text(), 'blip',
            "should have opened the correct record");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read', // list
            'read', // form
            '/web/dataset/search_read', // list
            'read', // form
        ]);

        actionManager.destroy();
    });

    // keep internal state of views when switching back

    QUnit.module('Actions in target="new"');

    QUnit.test('can execute act_window actions in target="new"', function (assert) {
        assert.expect(7);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        actionManager.do_action(5);

        assert.strictEqual($('.o_technical_modal .o_form_view').length, 1,
            "should have rendered a form view in a modal");
        assert.ok($('.o_technical_modal .modal-body').hasClass('o_act_window'),
            "modal-body element should have classname 'o_act_window'");
        assert.ok($('.o_technical_modal .o_form_view').hasClass('o_form_editable'),
            "form view should be in edit mode");

        // AAB: todo: check buttons position (in footer)

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            'default_get',
        ]);

        actionManager.destroy();
    });

    QUnit.module('"ir.actions.act_window_close" actions');

    QUnit.test('close the currently opened dialog', function (assert) {
        assert.expect(2);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        // execute an action in target="new"
        actionManager.do_action(5);
        assert.strictEqual($('.o_technical_modal .o_form_view').length, 1,
            "should have rendered a form view in a modal");

        // execute an 'ir.actions.act_window_close' action
        actionManager.do_action({
            type: 'ir.actions.act_window_close',
        });
        assert.strictEqual($('.o_technical_modal').length, 0,
            "should have closed the modal");

        actionManager.destroy();
    });
});

});
