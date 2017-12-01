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
    testUtils.intercept(widget, 'call_service', function (event) {
        if (event.data.service === 'report') {
            var state = widget._rpc({route: '/report/check_wkhtmltopdf'});
            event.data.callback(state);
        }
    }, true);
    widget.appendTo($target);
    widget.$el.addClass('o_web_client');

    // make sure images and iframes do not trigger a GET on the server
    // AAB; this should be done in addMockEnvironment
    $target.on('DOMNodeInserted.removeSRC', function () {
        testUtils.removeSrcAttribute($(this), widget);
    });

    var actionManager = new ActionManager(widget);
    var originalDestroy = ActionManager.prototype.destroy;
    actionManager.destroy = function () {
        actionManager.destroy = originalDestroy;
        $target.off('DOMNodeInserted.removeSRC');
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
                    bar: {string: "Bar", type: "many2one", relation: 'partner'},
                },
                records: [
                    {id: 1, display_name: "First record", foo: "yop"},
                    {id: 2, display_name: "Second record", foo: "blip"},
                    {id: 3, display_name: "Third record", foo: "gnap"},
                    {id: 4, display_name: "Fourth record", foo: "plop"},
                    {id: 5, display_name: "Fifth record", foo: "zoup"},
                ],
            },
            pony: {
                fields: {
                    name: {string: 'Name', type: 'char'},
                },
                records: [
                    {id: 4, name: 'Twilight Sparkle'},
                    {id: 6, name: 'Applejack'},
                    {id: 9, name: 'Fluttershy'}
                ],
            },
        };

        this.actions = [{
            id: 1,
            display_name: 'Partners Action 1',
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
            display_name: 'Partners Action 4',
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
        }, {
            id: 6,
            name: "Some Report",
            report_name: 'some_report',
            report_type: 'qweb-pdf',
            type: 'ir.actions.report',
        }, {
            id: 7,
            display_name: 'Favorite Ponies',
            res_model: 'pony',
            type: 'ir.actions.act_window',
            views: [[false, 'list'], [false, 'form']],
        }];

        this.archs = {
            // kanban views
            'partner,1,kanban': '<kanban><templates><t t-name="kanban-box">' +
                    '<div class="oe_kanban_global_click"><field name="foo"/></div>' +
                '</t></templates></kanban>',

            // list views
            'partner,false,list': '<tree><field name="foo"/></tree>',
            'partner,2,list': '<tree limit="3"><field name="foo"/></tree>',
            'pony,false,list': '<tree><field name="name"/></tree>',

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
            'pony,false,form': '<form>' +
                    '<field name="name"/>' +
                '</form>',

            // search views
            'partner,false,search': '<search><field name="foo" string="Foo"/></search>',
            'pony,false,search': '<search></search>',
        };
    },
}, function () {

    QUnit.test('breadcrumbs and actions with target inline', function (assert) {
        assert.expect(3);

        this.actions[3].views = [[false, 'form']];
        this.actions[3].target = 'inline';
        this.actions[3].view_mode = 'form';

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.do_action(4);
        assert.ok(!$('.o_control_panel').is(':visible'),
            "control panel should not be visible");

        actionManager.do_action(1, {clear_breadcrumbs: true});
        assert.ok($('.o_control_panel').is(':visible'),
            "control panel should now be visible");
        assert.strictEqual($('.o_control_panel .breadcrumb').text(), "Partners Action 1",
            "should have only one current action visible in breadcrumbs");

        actionManager.destroy();
    });

    QUnit.test('no widget memory leaks when doing some action stuff', function (assert) {
        assert.expect(1);

        var delta = 0;
        var oldInit = Widget.prototype.init;
        var oldDestroy = Widget.prototype.destroy;
        Widget.prototype.init = function () {
            delta++;
            oldInit.apply(this, arguments);
        };
        Widget.prototype.destroy = function () {
            delta--;
            oldDestroy.apply(this, arguments);
        };

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        actionManager.do_action(7);

        var n = delta;
        actionManager.do_action(4);
        // kanban view is loaded, switch to list view
        $('.o_control_panel .o_cp_switch_list').click();
        // open a record in form view
        actionManager.$('.o_list_view .o_data_row:first').click();
        // go back to action 7 in breadcrumbs
        $('.o_control_panel .breadcrumb a:first').click();

        assert.strictEqual(delta, n,
            "should have properly destroyed all other widgets");
        actionManager.destroy();
        Widget.prototype.init = oldInit;
        Widget.prototype.destroy = oldDestroy;
    });

    QUnit.module('Push State');

    QUnit.test('properly push state', function (assert) {
        assert.expect(3);

        var stateDescriptions = [
            {action: 4, model: "partner", title: "Partners Action 4", view_type: "kanban"},
            {action: 7, model: "pony", title: "Favorite Ponies", view_type: "list"},
            {action: 7, id: 4, model: "pony", title: "Twilight Sparkle", view_type: "form"},
        ];

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            intercepts: {
                push_state: function (event) {
                    var descr = stateDescriptions.shift();
                    assert.deepEqual(_.extend({}, event.data.state), descr,
                        "should notify the environment of new state");
                },
            },
        });
        actionManager.do_action(4);
        actionManager.do_action(7);
        actionManager.$('tr.o_data_row:first').click();

        actionManager.destroy();
    });

    QUnit.test('push state after action is loaded, not before', function (assert) {
        assert.expect(5);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            intercepts: {
                push_state: function () {
                    assert.step('push_state');
                },
            },
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });
        actionManager.do_action(4);
        assert.verifySteps([
            '/web/action/load',
            '/web/dataset/call_kw/partner',
            '/web/dataset/search_read',
            'push_state'
        ]);

        actionManager.destroy();
    });

    QUnit.test('do not push state for actions in target=new', function (assert) {
        assert.expect(3);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            intercepts: {
                push_state: function () {
                    assert.step('push_state');
                },
            },
        });
        actionManager.do_action(4);
        assert.verifySteps(['push_state']);
        actionManager.do_action(5);
        assert.verifySteps(['push_state']);

        actionManager.destroy();
    });

    QUnit.test('do not push state when action fails', function (assert) {
        assert.expect(4);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            intercepts: {
                push_state: function () {
                    assert.step('push_state');
                },
            },
            mockRPC: function (route, args) {
                if (args.method === 'read') {
                    // this is the rpc to load form view
                    return $.Deferred().reject();
                }
                return this._super.apply(this, arguments);
            },
        });
        actionManager.do_action(7);
        assert.verifySteps(['push_state']);
        actionManager.$('tr.o_data_row:first').click();
        assert.verifySteps(['push_state']);
        // we make sure here that the list view is still in the dom
        assert.strictEqual(actionManager.$('.o_list_view').length, 1,
            "there should still be a list view in dom");

        actionManager.destroy();
    });

    QUnit.module('Load State');

    QUnit.test('should not crash on invalid state', function (assert) {
        assert.expect(2);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        actionManager.loadState({
            res_model: 'partner', // the valid key for the model is 'model', not 'res_model'
        });

        assert.strictEqual(actionManager.$el.text(), '', "should display nothing");
        assert.verifySteps([]);

        actionManager.destroy();
    });

    QUnit.test('properly load client actions', function (assert) {
        assert.expect(2);

        var ClientAction = Widget.extend({
            className: 'o_client_action_test',
            start: function () {
                this.$el.text('Hello World');
            },
        });
        core.action_registry.add('HelloWorldTest', ClientAction);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        actionManager.loadState({
            action: 'HelloWorldTest',
        });

        assert.strictEqual(actionManager.$('.o_client_action_test').text(),
            'Hello World', "should have correctly rendered the client action");

        assert.verifySteps([]);

        actionManager.destroy();
        delete core.action_registry.map.HelloWorldTest;
    });

    QUnit.test('properly load act window actions', function (assert) {
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
        actionManager.loadState({
            action: 1,
        });

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

    QUnit.test('properly load records', function (assert) {
        assert.expect(5);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });
        actionManager.loadState({
            id: 2,
            model: 'partner',
        });

        assert.strictEqual(actionManager.$('.o_form_view').length, 1,
            "should have rendered a form view");
        assert.strictEqual($('.o_control_panel .breadcrumb li').text(), 'Second record',
            "should have opened the second record");

        assert.verifySteps([
            'load_views',
            'read',
        ]);

        actionManager.destroy();
    });

    QUnit.test('load requested view for act window actions', function (assert) {
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
        actionManager.loadState({
            action: 3,
            viewType: 'kanban',
        });

        assert.strictEqual(actionManager.$('.o_list_view').length, 0,
            "should not have rendered a list view");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 1,
            "should have rendered a kanban view");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            '/web/dataset/search_read',
        ]);

        actionManager.destroy();
    });

    QUnit.test('lazy load multi record view if mono record one is requested', function (assert) {
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
        actionManager.loadState({
            action: 3,
            id: 2,
            viewType: 'form',
        });

        assert.strictEqual(actionManager.$('.o_list_view').length, 0,
            "should not have rendered a list view");
        assert.strictEqual(actionManager.$('.o_form_view').length, 1,
            "should have rendered a form view");
        assert.strictEqual($('.o_control_panel .breadcrumb li').length, 2,
            "there should be two controllers in the breadcrumbs");
        assert.strictEqual($('.o_control_panel .breadcrumb li:last').text(), 'Second record',
            "breadcrumbs should contain the display_name of the opened record");

        // go back to Lst
        $('.o_control_panel .breadcrumb a').click();
        assert.strictEqual(actionManager.$('.o_list_view').length, 1,
            "should now display the list view");
        assert.strictEqual(actionManager.$('.o_form_view').length, 0,
            "should not display the form view anymore");

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            'read', // read the opened record
            '/web/dataset/search_read', // search read when coming back to List
        ]);

        actionManager.destroy();
    });

    QUnit.module('Concurrency management');

    QUnit.test('drop previous actions if possible', function (assert) {
        assert.expect(6);

        var def = $.Deferred();
        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route) {
                var result = this._super.apply(this, arguments);
                assert.step(route);
                if (route === '/web/action/load') {
                    return def.then(_.constant(result));
                }
                return result;
            },
        });
        actionManager.do_action(4);
        actionManager.do_action(7);

        def.resolve();

        // action 4 loads a kanban view first, 6 loads a list view. We want a list
        assert.strictEqual(actionManager.$('.o_list_view').length, 1,
            'there should be a list view in DOM');

        assert.verifySteps([
            '/web/action/load',  // load action 4
            '/web/action/load', // load action 6
            '/web/dataset/call_kw/pony', // load views for action 6
            '/web/dataset/search_read', // search read for list view action 6
        ]);

        actionManager.destroy();
    });

    QUnit.test('handle switching view and switching back on slow network', function (assert) {
        assert.expect(8);

        var def = $.Deferred();
        var defs = [$.when(), def, $.when()];

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route) {
                assert.step(route);
                var result = this._super.apply(this, arguments);
                if (route === '/web/dataset/search_read') {
                    var def = defs.shift();
                    return def.then(_.constant(result));
                }
                return result;
            },
        });
        actionManager.do_action(4);

        // kanban view is loaded, switch to list view
        $('.o_control_panel .o_cp_switch_list').click();

        // here, list view is not ready yet, because def is not resolved
        // switch back to kanban view
        $('.o_control_panel .o_cp_switch_kanban').click();

        // here, we want the kanban view to reload itself, regardless of list view
        assert.verifySteps([
            "/web/action/load",             // initial load action
            "/web/dataset/call_kw/partner", // load views
            "/web/dataset/search_read",     // search_read for kanban view
            "/web/dataset/search_read",     // search_read for list view (not resolved yet)
            "/web/dataset/search_read"      // search_read for kanban view reload (not resolved yet)
        ]);

        // we resolve def => list view is now ready (but we want to ignore it)
        def.resolve();

        assert.strictEqual(actionManager.$('.o_kanban_view').length, 1,
            "there should be a kanban view in dom");
        assert.strictEqual(actionManager.$('.o_list_view').length, 0,
            "there should not be a list view in dom");

        actionManager.destroy();
    });

    QUnit.test('when an server action takes too much time...', function (assert) {
        assert.expect(1);

        var def = $.Deferred();

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route) {
                if (route === '/web/action/run') {
                    return def.then(_.constant(1));
                }
                return this._super.apply(this, arguments);
            },
        });

        actionManager.do_action(2);
        actionManager.do_action(4);

        def.resolve();

        assert.strictEqual($('.o_control_panel .breadcrumb li.active').text(), 'Partners Action 4',
            'action 4 should be loaded');

        actionManager.destroy();
    });

    QUnit.test('clicking quickly on breadcrumbs...', function (assert) {
        assert.expect(1);

        var def = $.when();

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'read') {
                    return def.then(_.constant(result));
                }
                return result;
            },
        });

        // create a situation with 3 breadcrumbs: kanban/form/list
        actionManager.do_action(4);
        actionManager.$('.o_kanban_record:first').click();
        actionManager.do_action(7);

        // now, the next read operations will be deferred (this is the read
        // operation for the form view reload)
        def = $.Deferred();

        // click on the breadcrumbs for the form view, then on the kanban view
        // before the form view is fully reloaded
        $('.o_control_panel .breadcrumb li:eq(1)').click();
        $('.o_control_panel .breadcrumb li:eq(0)').click();

        // resolve the form view read
        def.resolve();

        assert.strictEqual($('.o_control_panel .breadcrumb li.active').text(), 'Partners Action 4',
            'action 4 should be loaded and visible');

        actionManager.destroy();
    });

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

    QUnit.module('Report actions');

    QUnit.test('can execute report actions from db ID', function (assert) {
        assert.expect(4);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === '/report/check_wkhtmltopdf') {
                    return $.when('ok');
                }
                return this._super.apply(this, arguments);
            },
            session: {
                get_file: function (params) {
                    assert.step(params.url);
                    params.complete();
                },
            },
        });
        actionManager.do_action(6);

        assert.verifySteps([
            '/web/action/load',
            '/report/check_wkhtmltopdf',
            '/report/download',
        ]);

        actionManager.destroy();
    });

    QUnit.test('should trigger a notification if wkhtmltopdf is to upgrade', function (assert) {
        assert.expect(5);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === '/report/check_wkhtmltopdf') {
                    return $.when('upgrade');
                }
                return this._super.apply(this, arguments);
            },
            session: {
                get_file: function (params) {
                    assert.step(params.url);
                    params.complete();
                },
            },
            intercepts: {
                notification: function () {
                    assert.step('notification');
                },
            },
        });
        actionManager.do_action(6);

        assert.verifySteps([
            '/web/action/load',
            '/report/check_wkhtmltopdf',
            'notification',
            '/report/download',
        ]);

        actionManager.destroy();
    });

    QUnit.test('should open the report client action if wkhtmltopdf is broken', function (assert) {
        assert.expect(6);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (route === '/report/check_wkhtmltopdf') {
                    return $.when('broken');
                }
                if (route === '/report/html/some_report') {
                    return $.when();
                }
                return this._super.apply(this, arguments);
            },
            session: {
                get_file: function (params) {
                    assert.step(params.url); // should not be called
                },
            },
            intercepts: {
                notification: function () {
                    assert.step('notification');
                },
            },
        });
        actionManager.do_action(6);

        assert.strictEqual(actionManager.$('.o_report_iframe').length, 1,
            "should have opened the report client action");

        assert.verifySteps([
            '/web/action/load',
            '/report/check_wkhtmltopdf',
            'notification',
            '/report/html/some_report', // report client action's iframe
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

    QUnit.test('restore previous view state when switching back', function (assert) {
        assert.expect(5);

        this.actions[2].views.unshift([false, 'graph']);
        this.archs['partner,false,graph'] = '<graph></graph>';

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        actionManager.do_action(3);

        assert.ok($('.o_control_panel  .fa-bar-chart-o').hasClass('active'),
            "bar chart button is active");
        assert.ok(!$('.o_control_panel  .fa-line-chart').hasClass('active'),
            "line chart button is not active");

        // display line chart
        $('.o_control_panel  .fa-line-chart').click();
        assert.ok($('.o_control_panel  .fa-line-chart').hasClass('active'),
            "line chart button is now active");

        // switch to kanban and back to graph view
        $('.o_control_panel .o_cp_switch_kanban').click();
        assert.strictEqual($('.o_control_panel  .fa-line-chart').length, 0,
            "graph buttons are no longer in control panel");

        $('.o_control_panel .o_cp_switch_graph').click();
        assert.ok($('.o_control_panel  .fa-line-chart').hasClass('active'),
            "line chart button is still active");
        actionManager.destroy();
    });

    QUnit.test('view switcher is properly highlighted in graph view', function (assert) {
        assert.expect(4);

        // note: this test should be moved to graph tests ?

        this.actions[2].views.splice(1, 1, [false, 'graph']);
        this.archs['partner,false,graph'] = '<graph></graph>';

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        actionManager.do_action(3);

        assert.ok($('.o_control_panel .o_cp_switch_list').hasClass('active'),
            "list button in control panel is active");
        assert.ok(!$('.o_control_panel .o_cp_switch_graph').hasClass('active'),
            "graph button in control panel is not active");

        // switch to graph view
        $('.o_control_panel .o_cp_switch_graph').click();
        assert.ok(!$('.o_control_panel .o_cp_switch_list').hasClass('active'),
            "list button in control panel is not active");
        assert.ok($('.o_control_panel .o_cp_switch_graph').hasClass('active'),
            "graph button in control panel is active");
        actionManager.destroy();
    });

    QUnit.test('can interact with search view', function (assert) {
        assert.expect(2);

        this.archs['partner,false,search'] = '<search>'+
                '<group>'+
                    '<filter name="foo" string="foo" context="{\'group_by\': \'foo\'}"/>' +
                '</group>'+
            '</search>';
        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        actionManager.do_action(3);

        assert.ok(!actionManager.$('.o_list_view').hasClass('o_list_view_grouped'),
            "list view is not grouped");
        // open search view sub menus
        $('.o_control_panel .o_searchview_more').click();

        // open group by dropdown
        $('.o_control_panel .o_cp_right button:contains(Group By)').click();

        // click on first link
        $('.o_control_panel .o_group_by_menu a:first').click();

        assert.ok(actionManager.$('.o_list_view').hasClass('o_list_view_grouped'),
            'list view is now grouped');

        actionManager.destroy();
    });

    QUnit.test('can open a many2one external window', function (assert) {
        // AAB: this test could be merged with 'many2ones in form views' in relational_fields_tests.js
        assert.expect(8);

        this.data.partner.records[0].bar = 2;
        this.archs['partner,false,search'] = '<search>'+
                '<group>'+
                    '<filter name="foo" string="foo" context="{\'group_by\': \'foo\'}"/>' +
                '</group>'+
            '</search>';
        this.archs['partner,false,form'] = '<form>' +
            '<group>' +
                '<field name="foo"/>' +
                '<field name="bar"/>' +
            '</group>' +
        '</form>';

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(route);
                if (args.method === "get_formview_id") {
                    return $.when(false);
                }
                return this._super.apply(this, arguments);
            },
        });
        actionManager.do_action(3);

        // open first record in form view
        actionManager.$('.o_data_row:first').click();
        // click on edit
        $('.o_control_panel .o_form_button_edit').click();

        // click on external button for m2o
        actionManager.$('.o_external_button').click();
        assert.verifySteps([
            '/web/action/load',             // initial load action
            '/web/dataset/call_kw/partner', // load views
            '/web/dataset/search_read',     // read list view data
            '/web/dataset/call_kw/partner/read', // read form view data
            '/web/dataset/call_kw/partner/get_formview_id', // get form view id
            '/web/dataset/call_kw/partner', // load form view for modal
            '/web/dataset/call_kw/partner/read' // read data for m2o record
        ]);
        actionManager.destroy();
    });

    QUnit.test('ask for confirmation when leaving a "dirty" view', function (assert) {
        assert.expect(4);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        actionManager.do_action(4);

        // open record in form view
        actionManager.$('.o_kanban_record:first').click();

        // edit record
        $('.o_control_panel button.o_form_button_edit').click();
        actionManager.$('input[name="foo"]').val('pinkypie').trigger('input');

        // go back to kanban view
        $('.o_control_panel .breadcrumb li:first a').click();

        assert.strictEqual($('.modal .modal-body').text(),
            "The record has been modified, your changes will be discarded. Do you want to proceed?",
            "should display a modal dialog to confirm discard action");

        // cancel
        $('.modal .modal-footer button.btn-default').click();

        assert.strictEqual(actionManager.$('.o_form_view').length, 1,
            "should still be in form view");

        // go back again to kanban view
        $('.o_control_panel .breadcrumb li:first a').click();

        // confirm discard
        $('.modal .modal-footer button.btn-primary').click();

        assert.strictEqual(actionManager.$('.o_form_view').length, 0,
            "should no longer be in form view");
        assert.strictEqual(actionManager.$('.o_kanban_view').length, 1,
            "should be in kanban view");

        actionManager.destroy();
    });

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
