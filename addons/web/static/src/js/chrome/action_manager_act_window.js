odoo.define('web.ActWindowActionManager', function (require) {
"use strict";

/**
 * The purpose of this file is to add the support of Odoo actions of type
 * 'ir.actions.act_window' to the ActionManager.
 */

var ActionManager = require('web.ActionManager');
var config = require('web.config');
var Context = require('web.Context');
var core = require('web.core');
var data = require('web.data'); // this will be removed at some point
var pyeval = require('web.pyeval');
var SearchView = require('web.SearchView');
var view_registry = require('web.view_registry');

var _t = core._t;

ActionManager.include({
    custom_events: _.extend({}, ActionManager.prototype.custom_events, {
        env_updated: '_onEnvUpdated',
        execute_action: '_onExecuteAction',
        search: '_onSearch',
        switch_view: '_onSwitchView',
        switch_to_previous_view: '_onSwitchToPreviousView',
    }),

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Overrides to handle the case where an 'ir.actions.act_window' has to be
     * loaded.
     *
     * @override
     * @param {Object} state
     * @param {integer} [state.action] the id of the action to execute
     * @param {integer} [state.active_id]
     * @param {string} [state.active_ids]
     * @param {integer} [state.id]
     * @param {integer} [state.view_id]
     * @param {string} [state.view_type]
     */
    loadState: function (state) {
        var action, options;
        if (state.action && _.isNumber(state.action)) {
            var currentController = this.getCurrentController();
            var currentAction = currentController && this.actions[currentController.actionID];
            if (currentAction && currentAction.id === state.action) {
                // the action to load is already the current one, so update it
                this._closeDialog(); // there may be a currently opened dialog, close it
                currentAction.env.currentId = state.id;
                var viewType = state.view_type || currentController.viewType;
                return this._switchController(currentAction, viewType);
            } else {
                // the action to load isn't the current one, so execute it
                var context = {};
                if (state.active_id) {
                    context.active_id = state.active_id;
                }
                if (state.active_ids) {
                    // jQuery's BBQ plugin does some parsing on values that are valid integers
                    // which means that if there's only one item, it will do parseInt() on it,
                    // otherwise it will keep the comma seperated list as string
                    context.active_ids = state.active_ids.split(',').map(function (id) {
                        return parseInt(id, 10) || id;
                    });
                } else if (state.active_id) {
                    context.active_ids = [state.active_id];
                }
                context.params = state;
                action = state.action;
                options = {
                    additional_context: context,
                    resID: state.id,
                    viewType: state.view_type,
                };
            }
        } else if (state.model && state.id) {
            action = {
                res_model: state.model,
                res_id: state.id,
                type: 'ir.actions.act_window',
                views: [[_.isNumber(state.view_id) ? state.view_id : false, 'form']],
            };
        }
        if (action) {
            return this.do_action(action, options);
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Instantiates a search view for a given action, and starts it so that it
     * is ready to be appended to the DOM.
     *
     * @param {Object} action
     * @returns {Deferred} resolved with the search view when it is ready
     */
    _createSearchView: function (action) {
        // AAB: temporarily create a dataset, until the SearchView is refactored
        // and stops using it
        var dataset = new data.DataSetSearch(this, action.res_model, action.context, action.domain);
        if (action.res_id) {
            dataset.ids.push(action.res_id);
            dataset.index = 0;
        }

        // find 'search_default_*' keys in actions's context
        var searchDefaults = {};
        _.each(action.context, function (value, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                searchDefaults[match[1]] = value;
            }
        });
        var searchView = new SearchView(this, dataset, action.searchFieldsView, {
            $buttons: $('<div>'),
            action: action,
            disable_custom_filters: action.flags.disableCustomFilters,
            search_defaults: searchDefaults,
        });

        return searchView.appendTo(document.createDocumentFragment()).then(function () {
            action.searchView = searchView;
            return searchView;
        });
    },
    /**
     * Instantiates the controller for a given action and view type, and adds it
     * to the list of controllers in the action.
     *
     * @private
     * @param {Object} action
     * @param {AbstractController[]} action.controllers the already created
     *   controllers for this action
     * @param {Object[]} action.views the views available for the action, each
     *   one containing its fieldsView
     * @param {Object} action.env
     * @param {string} viewType
     * @param {Object} options
     * @param {boolean} [lazy=false] set to true to differ the initialization of
     *   the controller's widget
     * @returns {Deferred<AbstractController>} resolved with the created
     *   controller
     */
    _createViewController: function (action, viewType, options, lazy) {
        var self = this;
        var controllerID = _.uniqueId('controller_');
        var controller = {
            actionID: action.jsID,
            className: 'o_act_window', // used to remove the padding in dialogs
            jsID: controllerID,
            title: action.display_name,
            viewType: viewType,
            widget: controller,
        };
        this.controllers[controllerID] = controller;
        options = _.extend({}, options, action.flags, action.env, {
            controllerID: controllerID,
        });
        var viewDescr = _.findWhere(action.views, {type: viewType});
        var view = new viewDescr.Widget(viewDescr.fieldsView, options);
        if (!lazy) {
            action.controllers[viewType] = view.getController(this).then(function (widget) {
                // AAB: change this logic to stop using the properties mixin
                widget.on("change:title", this, function () {
                    if (!action.flags.headless) {
                        var breadcrumbs = self._getBreadcrumbs();
                        self.controlPanel.update({breadcrumbs: breadcrumbs}, {clear: false});
                    }
                });
                controller.widget = widget;

                return controller;
            });
        } else {
            action.controllers[viewType] = $.when(controller);
        }
        return action.controllers[viewType];
    },
    /**
     * Executes actions of type 'ir.actions.act_window'.
     *
     * @private
     * @param {Object} action the description of the action to execute
     * @param {Array} action.views list of tuples [viewID, viewType]
     * @param {Object} options @see do_action for details
     * @param {interger} [options.resID] the current res ID
     * @param {string} [options.viewType] the view to open
     * @returns {Deferred} resolved when the action is appended to the DOM
     */
    _executeWindowAction: function (action, options) {
        var self = this;

        // generate default action's flags
        var popup = action.target === 'new';
        var inline = action.target === 'inline' || action.target === 'inlineview';
        var form = _.str.startsWith(action.view_mode, 'form');
        action.flags = _.defaults(action.flags || {}, {
            disableCustomFilters: action.context && action.context.search_disable_custom_filters,
            hasSearchView: !(popup && form) && !inline,
            hasSidebar: !popup && !inline,
            headless: (popup || inline) && form,
        });

        return this._loadViews(action).then(function (fieldsViews) {
            // generate the description of the views in the action, linked to
            // their fields_view
            var views = [];
            _.each(action.views, function (view) {
                var viewType = view[1];
                var fieldsView = fieldsViews[viewType];
                var View = view_registry.get(fieldsView.arch.attrs.js_class || viewType);
                if (!View) {
                    console.error("View type '" + viewType + "' is not present in the view registry.");
                    return $.Deferred.reject();
                }
                views.push({
                    accessKey: View.prototype.accessKey,
                    fieldsView: fieldsViews[viewType],
                    icon: View.prototype.icon,
                    isMobileFriendly: View.prototype.mobile_friendly,
                    multiRecord: View.prototype.multi_record,
                    type: viewType,
                    viewID: view[0],
                    Widget: View,
                });
            });
            action.views = views;
            if (fieldsViews.search) {
                action.searchFieldsView = fieldsViews.search;
            }
            action.controllers = {};

            // select the first view to display
            var lazyLoad = false;
            var firstView = options.viewType && _.findWhere(views, {type: options.viewType});
            if (firstView) {
                if (!firstView.multiRecord && views[0].multiRecord) {
                    lazyLoad = true;
                }
            } else {
                firstView = views[0];
            }
            if (config.device.isMobile && !firstView.isMobileFriendly) {
                firstView = _.findWhere(action.views, {isMobileFriendly: true}) || firstView;
            }

            // generate the inital environment of the action
            var actionGroupBy = action.context.group_by || [];
            if (typeof actionGroupBy === 'string') {
                actionGroupBy = [actionGroupBy];
            }
            var resID = options.resID || action.res_id;
            action.env = {
                modelName: action.res_model,
                ids: resID ? [resID] : undefined,
                currentId: resID || undefined,
                domain: undefined,
                context: action.context,
                groupBy: actionGroupBy,
            };

            options.action = action;

            var def;
            if (action.flags.hasSearchView) {
                def = self._createSearchView(action).then(function (searchView) {
                    // udpate domain, context and groupby in the env
                    var searchData = searchView.build_search_data();
                    _.extend(action.env, self._processSearchData(action, searchData));
                });
            }
            return $.when(def)
                .then(function () {
                    var defs = [];
                    defs.push(self._createViewController(action, firstView.type, options));
                    if (lazyLoad) {
                        defs.push(self._createViewController(action, views[0].type, options, true));
                    }
                    return $.when.apply($, defs);
                })
                .then(function (controller, lazyLoadedController) {
                    action.controller = controller;
                    return self._executeAction(action, options).done(function () {
                        if (lazyLoadedController) {
                            self.controllerStack.unshift(lazyLoadedController.jsID);
                            self.controlPanel.update({
                                breadcrumbs: self._getBreadcrumbs(),
                            }, {clear: false});
                        }
                    });
                });
        });
    },
    /**
     * Overrides to add specific information for controllers from actions of
     * type 'ir.actions.act_window', like the res_model and the view_type.
     *
     * @override
     * @private
     */
    _getControllerState: function (controllerID) {
        var state = this._super.apply(this, arguments);
        var controller = this.controllers[controllerID];
        var action = this.actions[controller.actionID];
        if (action.type == 'ir.actions.act_window') {
            state.model = action.res_model;
            state.view_type = controller.viewType;
        }
        return state;
    },
    /**
     * Overrides to handle the 'ir.actions.act_window' actions.
     *
     * @override
     * @private
     */
    _handleAction: function (action, options) {
        if (action.type === 'ir.actions.act_window') {
            return this._executeWindowAction(action, options);
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Loads the fields_views and fields for the given action.
     *
     * @private
     * @param {Object} action
     * @returns {Deferred}
     */
    _loadViews: function (action) {
        var options = {
            action_id: action.id,
            toolbar: action.flags.hasSidebar,
        };
        var views = action.views.slice(0);
        if (action.flags.hasSearchView) {
            options.load_filters = true;
            var searchviewID = action.search_view_id && action.search_view_id[0];
            views.push([searchviewID || false, 'search']);
        }
        return this.loadViews(action.res_model, action.context, views, options);
    },
    _processSearchData: function (action, searchData) {
        var contexts = searchData.contexts;
        var domains = searchData.domains;
        var groupbys = searchData.groupbys;
        var action_context = action.context || {};
        var results = pyeval.eval_domains_and_contexts({
            domains: [action.domain || []].concat(domains || []),
            contexts: [action_context].concat(contexts || []),
            group_by_seq: groupbys || [],
            eval_context: this.getSession().user_context,
        });
        if (results.error) {
            throw new Error(_.str.sprintf(_t("Failed to evaluate search criterions")+": \n%s",
                            JSON.stringify(results.error)));
        }
        return {
            context: results.context,
            domain: results.domain,
            groupBy: results.group_by,
        };
    },
    /**
     * Overrides to handle the case of 'ir.actions.act_window' actions, i.e.
     * destroys all controllers associated to the given action, and its search
     * view.
     *
     * @private
     * @override
     */
    _removeAction: function (actionID) {
        var self = this;
        var action = this.actions[actionID];
        if (action.type === 'ir.actions.act_window') {
            _.each(action.controllers, function (controllerDef) {
                controllerDef.then(function (controller) {
                    if (controller.widget) {
                        controller.widget.destroy();
                    }
                    delete self.controllers[controller.jsID];
                });
            });
            if (action.searchView) {
                action.searchView.destroy();
            }
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides to handle the case where the controller to restore is from an
     * 'ir.actions.act_window' action. In this case, only the controllers
     * stacked over the one to restore *that are not from the same action* are
     * destroyed.
     * For instance, when going back to the list controller from a form
     * controller of the same action using the breadcrumbs, the form controller
     * isn't destroyed, as it might be reused in the future.
     *
     * @override
     * @private
     */
    _restoreController: function (controllerID) {
        var self = this;
        var controller = this.controllers[controllerID];
        var action = this.actions[controller.actionID];
        if (action.type === 'ir.actions.act_window') {
            return this._clearUncommittedChanges().then(function () {
                return self._switchController(action, controller.viewType);
            });
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Handles the switch from a controller to another inside the same window
     * action.
     *
     * @private
     * @param {Object} controller the controller to switch to
     * @param {Object} options
     * @return {Deferred} resolved when the new controller is in the DOM
     */
    _switchController: function (action, viewType, options) {
        var self = this;
        options = options || {};
        options.action = action;
        _.extend(options, action.env);

        var newController = function () {
            // AAB: missing options
            return self
                ._createViewController(action, viewType, options)
                .then(function (controller) {
                    // AAB: this will be moved to the Controller
                    var widget = controller.widget;
                    if (widget.need_control_panel) {
                        // set the ControlPanel bus on the controller to allow it to
                        // communicate its status
                        widget.set_cp_bus(self.controlPanel.get_bus());
                    }
                    return self._startController(controller).then(function () {
                        return controller;
                    });
                });
        };

        var controllerDef = action.controllers[viewType];
        if (!controllerDef) {
            controllerDef = newController();
        } else {
            controllerDef = controllerDef.then(function (controller) {
                if (!controller.widget) {
                    // lazy loaded -> load it now
                    return newController().then(function (newController) {
                        delete self.controllers[newController.jsID];
                        newController.jsID = controller.jsID;
                        self.controllers[newController.jsID] = newController;
                        return newController;
                    });
                } else {
                    return controller.widget.reload(options).then(function () {
                        return controller;
                    });
                }
            });
        }

        return this.dp.add(controllerDef).then(function (controller) {
            var view = _.findWhere(action.views, {type: viewType});
            var index;
            if (view.multiRecord) {
                // remove other controllers linked to the same action from the stack
                index = _.findIndex(self.controllerStack, function (controllerID) {
                    return self.controllers[controllerID].actionID === action.jsID;
                });
            } else {
                var currentController = self.getCurrentController();
                if (currentController) {
                    if (currentController.actionID === action.jsID &&
                        !_.findWhere(action.views, {type: currentController.viewType}).multiRecord) {
                        // replace the last controller by the new one if they are from the
                        // same action and if they both are mono record
                        index = self.controllerStack.length - 1;
                    }
                }
            }
            return self._pushController(controller, _.extend(options, {index: index}));
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     * @param {string} ev.data.controllerID
     * @param {Object} ev.data.env
     */
    _onEnvUpdated: function (ev) {
        ev.stopPropagation();
        var controller = this.controllers[ev.data.controllerID];
        var action = this.actions[controller.actionID];
        _.extend(action.env, ev.data.env);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {Object} ev.data.action_data
     * @param {Object} ev.data.env
     * @param {function} [ev.data.on_closed]
     * @param {function} [ev.data.on_fail]
     * @param {function} [ev.data.on_success]
     */
    _onExecuteAction: function (ev) {
        ev.stopPropagation();
        var self = this;
        var action_data = ev.data.action_data;
        var env = ev.data.env;
        var closeHandler = ev.data.on_closed || function () {};
        var context = new Context(env.context, action_data.context || {});
        var recordID = env.currentID || null; // pyeval handles null value, not undefined
        var def;
        var handler = function (action) {
            // show effect if button have effect attribute
            // rainbowman can be displayed from two places: from attribute on a button or from python
            // code below handles the first case i.e 'effect' attribute on button.
            var effect = false;
            if (action_data.effect) {
                effect = pyeval.py_eval(action_data.effect);
            }

            if (action && action.constructor === Object) {
                // filter out context keys that are specific to the current action, because:
                //  - wrong default_* and search_default_* values won't give the expected result
                //  - wrong group_by values will fail and forbid rendering of the destination view
                var ctx = new Context(
                    _.object(_.reject(_.pairs(env.context), function (pair) {
                        return pair[0].match('^(?:(?:default_|search_default_|show_).+|.+_view_ref|group_by|group_by_no_leaf|active_id|active_ids)$') !== null;
                    }))
                );
                ctx.add(action_data.context || {});
                ctx.add({active_model: env.model});
                if (recordID) {
                    ctx.add({
                        active_id: recordID,
                        active_ids: [recordID],
                    });
                }
                ctx.add(action.context || {});
                action.context = ctx;
                // in case an effect is returned from python and there is already an effect
                // attribute on the button, the priority is given to the button attribute
                action.effect = effect || action.effect;
                return self.do_action(action, {on_close: closeHandler});
            } else {
                // if action doesn't return anything, but have effect attribute on button,
                // display rainbowman
                self.do_action({type: 'ir.actions.act_window_close', effect: effect});
                return closeHandler();
            }
        };

        if (action_data.special) {
            def = handler({type: 'ir.actions.act_window_close'});
        } else if (action_data.type === 'object') {
            var args = recordID ? [[recordID]] : [env.resIDs];
            if (action_data.args) {
                try {
                    // warning: quotes and double quotes problem due to json and xml clash
                    // maybe we should force escaping in xml or do a better parse of the args array
                    var additional_args = JSON.parse(action_data.args.replace(/'/g, '"'));
                    args = args.concat(additional_args);
                } catch(e) {
                    console.error("Could not JSON.parse arguments", action_data.args);
                }
            }
            args.push(context.eval());
            def = this._rpc({
                route: '/web/dataset/call_button',
                params: {
                    args: args,
                    method: action_data.name,
                    model: env.model,
                },
            }).then(handler);
        } else if (action_data.type === 'action') {
            def = this._loadAction(action_data.name, _.extend(pyeval.eval('context', context), {
                active_model: env.model,
                active_ids: env.resIDs,
                active_id: recordID,
            })).then(handler);
        }

        def.then(ev.data.on_success).fail(ev.data.on_fail);
    },
    /**
     * Called when there is a change in the search view, so the current action's
     * environment needs to be updated with the new domain, context and groupby.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSearch: function (ev) {
        ev.stopPropagation();
        // AAB: the id of the correct controller should be given in data
        var currentController = this.getCurrentController();
        var action = this.actions[currentController.actionID];
        _.extend(action.env, this._processSearchData(action, ev.data));
        currentController.widget.reload(_.extend({offset: 0}, action.env));
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSwitchView: function (ev) {
        ev.stopPropagation();
        var viewType = ev.data.view_type;
        // retrieve the correct action using the currentController (AAB: is it
        // enough robust?)
        var currentController = this.getCurrentController();
        var action = this.actions[currentController.actionID];
        if ('res_id' in ev.data) {
            action.env.currentId = ev.data.res_id;
        }
        var options = {};
        if (viewType === 'form' && !action.env.currentId) {
            options.mode = 'edit';
        } else if (ev.data.mode) {
            options.mode = ev.data.mode;
        }

        this._switchController(action, viewType, options);
    },
    /**
     * This handler is probably called by a form view when the user clicks on
     * 'Discard' on a new record. The usual result of this is that we switch
     * back to the previous view.
     *
     * @param {OdooEvent} ev
     * @private
     */
    _onSwitchToPreviousView: function (ev) {
        ev.stopPropagation();
        var self = this;
        var currentController = this.getCurrentController();
        var action = this.actions[currentController.actionID];
        var length = this.controllerStack.length;
        if (length > 1) {
            var previousControllerID = this.controllerStack[length - 2];
            var previousController = this.controllers[previousControllerID];
            if (previousController.actionID === action.jsID) {
                // reload previous controller
                previousController.widget.reload(action.env).then(function () {
                    self._pushController(previousController, {index: length - 2});
                });
            } else {
                // AAB: i guess that it should reload the previous action if the
                // previous controller is not of the same action
            }
        }
    },
});

});
