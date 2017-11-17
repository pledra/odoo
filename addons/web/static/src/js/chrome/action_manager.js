odoo.define('web.ActionManager', function (require) {
"use strict";

/**
 * ActionManager
 *
 * The ActionManager is one of the centrepieces in the WebClient architecture.
 * Its role is to makes sure that Odoo actions are properly started and
 * coordinated.
 */

var Bus = require('web.Bus');
var concurrency = require('web.concurrency');
var Context = require('web.Context');
var ControlPanel = require('web.ControlPanel');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var framework = require('web.framework');
var pyeval = require('web.pyeval');
var session = require('web.session');
var Widget = require('web.Widget');

var ActionManager = Widget.extend({
    className: 'o_content',
    custom_events: {
        breadcrumb_clicked: '_onBreadcrumbClicked',
        push_state: '_onPushState',
    },

    /**
     * @override
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.webClient = options && options.webclient;

        // use a DropPrevious to drop previous actions when multiple actions are
        // run simultaneously
        this.dp = new concurrency.DropPrevious();

        // 'actions' is an Object that registers the actions that are currently
        // handled by the ActionManager (either stacked in the current window,
        // or opened in dialogs)
        this.actions = {};

        // 'controllers' is an Object that registers the alive controllers
        // linked registered actions, a controller being Object with keys
        // (amongst others) 'jsID' (a local identifier) and 'widget' (the
        // instance of the controller's widget)
        this.controllers = {};

        // 'controllerStack' is the stack of ids of the controllers currently
        // displayed in the current window
        this.controllerStack = [];

        // 'currentDialogController' is the current controller opened in a
        // dialog (i.e. coming from an action with target='new')
        this.currentDialogController = null;
    },

    /**
     * @override
     */
    start: function () {
        // AAB: temporarily instantiate a unique main ControlPanel used by
        // controllers in the controllerStack
        this.controlPanel = new ControlPanel(this);
        var def = this.controlPanel.insertBefore(this.$el);
        // this.controlPanel.on("on_breadcrumb_click", this, _.debounce(function (action, index) {
        //     this.select_action(action, index);
        // }, 200, true));

        // AAB: TODO: listen to DOM_updated to restore scroll position?

        return $.when(def, this._super.apply(this, arguments));
    },
    /**
     * Called each time the action manager is attached into the DOM.
     */
    on_attach_callback: function() {
        this.isInDOM = true;
        var currentController = this.getCurrentController();
        if (currentController && currentController.widget.on_attach_callback) {
            currentController.widget.on_attach_callback();
        }
    },
    /**
     * Called each time the action manager is detached from the DOM.
     */
    on_detach_callback: function() {
        this.isInDOM = false;
        var currentController = this.getCurrentController();
        if (currentController && currentController.widget.on_detach_callback) {
            currentController.widget.on_detach_callback();
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This is the entry point to execute Odoo actions, given as an ID in
     * database, an xml ID, a client action tag or an action descriptor.
     *
     * @param {number|string|Object} action the action to execute
     * @param {Object} [options]
     * @param {Object} [options.additional_context] additional context to be
     *   merged with the action's context.
     * @param {boolean} [options.clear_breadcrumbs=false] set to true to clear
     *   the breadcrumbs history list
     * @param {Function} [options.on_close] callback to be executed when the
     *   dialog is closed (only relevant for target='new' actions)
     * @param {Function} [options.on_reverse_breadcrumb] callback to be executed
     *   whenever an anterior breadcrumb item is clicked on
     * @param {boolean} [options.replace_breadcrumb=false] set to true to
     *   replace last part of the breadcrumbs with the action
     * @return {Deferred} resolved when the action is loaded and appended to the
     *   DOM
    */
    do_action: function (action, options) {
        var self = this;
        options = _.defaults({}, options, {
            additional_context: {},
            clear_breadcrumbs: false,
            on_close: function () {},
            on_reverse_breadcrumb: function () {},
            replace_last_action: false,
        });

        // build or load an action descriptor for the given action
        var def;
        if (_.isString(action) && core.action_registry.contains(action)) {
            // action is a tag of a client action
            action = { type: 'ir.actions.client', tag: action };
        } else if (_.isNumber(action) || _.isString(action)) {
            // action is an id or xml id
            def = this._loadAction(action, {
                active_id: options.additional_context.active_id,
                active_ids: options.additional_context.active_ids,
                active_model: options.additional_context.active_model,
            }).then(function (result) {
                action = result;
            });
        }

        return this.dp.add($.when(def)).then(function () {
            action.jsID = _.uniqueId('action_');

            // action.target 'main' is equivalent to 'current' except that it
            // also clears the breadcrumbs
            options.clear_breadcrumbs = action.target === 'main' ||
                                        options.clear_breadcrumbs;

            // ensure that the context and domain are evaluated
            var context = new Context(session.user_context,
                                      options.additional_context, action.context || {});
            action.context = pyeval.eval('context', context);
            if (action.domain) {
                action.domain = pyeval.eval('domain', action.domain, action.context);
            }

            return self._handleAction(action, options);
        });
    },

    do_push_state: function (state) {
        // AAB: TODO
    },
    do_load_state: function (state) {
        return $.when(); // AAB: TODO
    },
    /**
     * Returns the last controller in the controllerStack, i.e. the currently
     * displayed controller in the main window (not in a dialog), and
     * undefined if there is no controller in the stack.
     *
     * @returns {Object|undefined}
     */
    getCurrentController: function () {
        var currentControllerID = _.last(this.controllerStack);
        return currentControllerID ? this.controllers[currentControllerID] : undefined;
    },
    get_inner_action: function () {
        // AAB: TODO
        return null;
    },
    /**
     * AAB: compatibility with existing client actions
     * todo: remove this
     */
    get_breadcrumbs: function () {
        return this._getBreadcrumbs();
    },

    /**
     * Sets the scroll position of the current controller, if there is one.
     *
     * @param {integer} scrollTop
     */
    setScrollTop: function (scrollTop) {
        var currentController = this.getCurrentController();
        if (currentController && currentController.widget.setScrollTop) {
            currentController.widget.setScrollTop(scrollTop);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This function is called when the current controller is about to be
     * removed from the DOM, because a new one will be pushed, or an old one
     * will be restored. It ensures that the current controller can be left (for
     * instance, that it has no unsaved changes).
     *
     * @returns {Deferred} resolved if the current controller can be left,
     *   rejected otherwise.
     */
    _clearUncommittedChanges: function () {
        var currentController = this.getCurrentController();
        // AAB: with AbstractAction, the second part of the condition won't be
        // necessary anymore, as there will be such a function it its API
        if (currentController && currentController.widget.discardChanges) {
            return currentController.widget.discardChanges(undefined, {
                readonlyIfRealDiscard: true, // AAB: there is a whole story about this option
            });
        }
        return $.when();
    },
    /**
     * Closes the current dialog, if any. This destroys the embedded controller.
     * Also removes the reference to the corresponding action.
     *
     * @param {Object} reason AAB: weird arg... could be a boolean
     */
    _closeDialog: function (reason) {
        if (this.currentDialogController) {
            delete this.actions[this.currentDialogController.actionID];
            this.currentDialogController.dialog.destroy(reason);
            this.currentDialogController = null;
        }
    },
    /**
     * Executes actions for which a controller has to be appended to the DOM,
     * either in the main content (target="current", by default), or in a dialog
     * (target="new").
     *
     * @private
     * @param {Object} action
     * @param {widget} action.controller a Widget instance to append to the DOM
     * @param {string} [action.target="current"] set to "new" to render the
     *   controller in a dialog
     * @param {Object} options @see do_action for details
     * @returns {Deferred} resolved when the controller is started and appended
     */
    _executeAction: function (action, options) {
        var self = this;
        this.actions[action.jsID] = action;

        if (action.target === 'new') {
            return this._executeActionInDialog(action, options);
        }

        var widget = action.controller.widget;
        // AAB: this will be moved to the Controller
        if (widget.need_control_panel) {
            // set the ControlPanel bus on the controller to allow it to
            // communicate its status
            widget.set_cp_bus(this.controlPanel.get_bus());
        }

        return this._clearUncommittedChanges()
            .then(function () {
                self._startController(action.controller);
            })
            .then(function () {
                if (self.currentDialogController) {
                    self._closeDialog(action);
                }

                // update the internal state and the DOM
                self._pushController(action.controller, options);

                // notify the environment of the new action
                // AAB: reactivate this later or find another way to do that
                // self.trigger_up('current_action_updated', {action: action});

                return action;
            })
            .fail(function () {
                widget.destroy();
                delete self.actions[action.jsID];
            });
    },
    /**
     * Executes actions with attribute target='new'. Such actions are rendered
     * in a dialog.
     *
     * @private
     * @param {Object} action
     * @param {Object} options @see do_action for details
     * @returns {Deferred} resolved when the controller is rendered inside a
     *   dialog appended to the DOM
     */
    _executeActionInDialog: function (action, options) {
        var self = this;
        var controller = action.controller;
        var widget = action.controller.widget;
        var dialog = new Dialog(widget, _.defaults({}, options, {
            buttons: [],
            dialogClass: controller.className,
            title: action.name,
            size: action.context.dialog_size,
        }));
        dialog.on('closed', widget, function () {
            self.currentDialogController = null;
            delete self.actions[action.jsID];
            if (options.on_close) {
                options.on_close();
            }
        });
        controller.dialog = dialog;

        // AAB: this will be moved to the Controller
        if (widget.need_control_panel) {
            // set the ControlPanel bus on the controller to allow it to
            // communicate its status
            widget.set_cp_bus(new Bus());
        }

        return this._startController(controller).then(function () {
            if (self.currentDialogController) {
                self._closeDialog(action);
            }
            return dialog.open().opened(function () {
                dom.append(dialog.$el, widget.$el, {
                    in_DOM: true,
                    callbacks: [{widget: dialog}],
                });
                self.currentDialogController = controller;

                return action;
            });
        }).fail(function () {
            dialog.destroy();
            delete self.actions[action.jsID];
        });
    },
    /**
     * Executes actions of type 'ir.actions.client'.
     *
     * @private
     * @param {Object} action the description of the action to execute
     * @param {string} action.tag the key of the action in the action_registry
     * @param {Object} options @see do_action for details
     * @returns {Deferred} resolved when the action is appended to the DOM
     */
    _executeClientAction: function (action, options) {
        var ClientAction = core.action_registry.get(action.tag);
        if (!ClientAction) {
            var message = "Could not find client action '" + action.tag + "'.";
            return this.do_warn("Action Error", message);
        }
        // AAB: drop the support of this?
        if (!(ClientAction.prototype instanceof Widget)) {
            // the client action might be a function, which is executed and
            // whose returned value might be another action to execute
            var next = ClientAction(this, action);
            if (next) {
                return this.do_action(next, options);
            }
            return $.when();
        }

        var controllerID = _.uniqueId('controller_');
        this.controllers[controllerID] = {
            actionID: action.jsID,
            jsID: controllerID,
            widget: new ClientAction(this, action, options),
        };
        action.controller = this.controllers[controllerID]; // AAB: give the controllerID instead
        return this._executeAction(action, options);
    },
    /**
     * Executes actions of type 'ir.actions.act_window_close', i.e. closes the
     * last opened dialog.
     *
     * @private
     * @param {Object} action
     * @returns {Deferred} resolved immediately
     */
    _executeCloseAction: function (action) {
        this._closeDialog();

        // display some effect (like rainbowman) on appropriate actions
        if (action.effect) {
            this.trigger_up('show_effect', action.effect);
        }

        return $.when();
    },
    /**
     * Executes actions of type 'ir.actions.server'.
     *
     * @private
     * @param {Object} action the description of the action to execute
     * @param {integer} action.id the db ID of the action to execute
     * @param {Object} [action.context]
     * @param {Object} options @see do_action for details
     * @returns {Deferred} resolved when the action has been executed
     */
    _executeServerAction: function (action, options) {
        var self = this;
        var runDef = this._rpc({
            route: '/web/action/run',
            params: {
                action_id: action.id,
                context: action.context || {},
            },
        });
        return this.dp.add(runDef).then(function (action) {
            return self.do_action(action, options);
        });
    },
    /**
     * Executes actions of type 'ir.actions.act_url', i.e. redirects to the
     * given url.
     *
     * @private
     * @param {Object} action the description of the action to execute
     * @param {string} action.url
     * @param {string} [target] set to 'self' to redirect in the current page,
     *   redirects to a new page by default
     * @returns {Deferred} resolved when the redirection is done (immediately
     *   when redirecting to a new page)
     */
    _executeURLAction: function (action) {
        var url = action.url;
        if (session.debug && url && url.length && url[0] === '/') {
            url = $.param.querystring(url, {debug: session.debug});
        }

        if (action.target === 'self') {
            framework.redirect(url);
            return $.Deferred(); // the action is finished only when the redirection is done
        } else {
            window.open(url, '_blank');
        }
        return $.when();
    },
    /**
     * Returns a description of the current stack of controllers, used to render
     * the breadcrumbs. It is an array of Objects with keys 'title' (what to
     * display in the breadcrumbs) and 'controllerID' (the ID of the
     * corresponding controller, used to restore it when this part of the
     * breadcrumbs is clicked).
     *
     * @private
     * @returns {Object[]}
     */
    _getBreadcrumbs: function () {
        var self = this;
        return _.map(this.controllerStack, function (controllerID) {
            return {
                title: self._getControllerTitle(controllerID),
                controllerID: controllerID,
            };
        });
    },
    /**
     * Returns an object containing information about the given controller, like
     * its title, its action'sid, the active_id and active_ids of the action...
     *
     * @private
     * @param {string} controllerID
     * @returns {Object}
     */
    _getControllerState: function (controllerID) {
        var controller = this.controllers[controllerID];
        var action = this.actions[controller.actionID];
        var state = {};
        state.title = this._getControllerTitle(controllerID);
        if (action.id) {
            state.action = action.id;
        } else if (action.type === 'ir.actions.client') {
            state.action = action.tag;
            var params = {};
            _.each(action.params, function (v, k) {
                if(_.isString(v) || _.isNumber(v)) {
                    params[k] = v;
                }
            });
            state = _.extend(params || {}, state);
        }
        if (action.context) {
            var active_id = action.context.active_id;
            if (active_id) {
                state.active_id = active_id;
            }
            var active_ids = action.context.active_ids;
            // we don't push active_ids if it's a single element array containing the active_id
            // to make the url shorter in most cases
            if (active_ids && !(active_ids.length === 1 && active_ids[0] === active_id)) {
                state.active_ids = action.context.active_ids.join(',');
            }
        }
        return state;
    },
    /**
     * Returns the title of a given controller.
     *
     * @todo  simplify this with AbstractAction (implement a getTitle function
     * that returns action.display_name by default, and that can be overriden
     * in client actions and view controllers)
     * @private
     * @param {string} controllerID
     * @returns {string}
     */
    _getControllerTitle: function (controllerID) {
        var controller = this.controllers[controllerID];
        var title = controller.widget.getTitle && controller.widget.getTitle();
        if (!title) {
            title = controller.widget.get('title');
            if (!title) {
                var action = this.actions[controller.actionID];
                title = action.display_name;
            }
        }
        return title;
    },
    /**
     * Dispatches the given action to the corresponding handler to execute it,
     * according to its type. This function can be overriden to extend the
     * range of supported action types.
     *
     * @private
     * @param {Object} action
     * @param {string} action.type
     * @param {Object} options
     * @returns {Deferred} resolved when the action has been executed
     */
    _handleAction: function (action, options) {
        if (!action.type) {
            console.error("No type for action", action);
            return $.Deferred().reject();
        }
        switch (action.type) {
            case 'ir.actions.act_url':
                return this._executeURLAction(action, options);
            case 'ir.actions.act_window_close':
                return this._executeCloseAction(action, options);
            case 'ir.actions.client':
                return this._executeClientAction(action, options);
            case 'ir.actions.server':
                return this._executeServerAction(action, options);
            default:
                console.error("The ActionManager can't handle actions of type " +
                    action.type, action);
                return $.Deferred().reject();
        }
    },
    /**
     * Updates the internal state and the DOM with the given controller as
     * current controller.
     *
     * @private
     * @param {Object} controller
     * @param {string} controller.jsID
     * @param {Widget} controller.widget
     * @param {Object} [options]
     * @param {Object} [options.clear_breadcrumbs=false] if true, destroys all
     *   controllers from the controller stack before adding the given one
     * @param {Object} [options.replace_last_action=false] if true, replaces the
     *   last controller of the controller stack by the given one
     * @param {integer} [options.index] if given, pushes the controller at that
     *   position in the controller stack, and destroys the controllers with an
     *   higher index
     */
    _pushController: function (controller, options) {
        options = options || {};
        var self = this;

        // detach the current controller from the DOM before emptying the
        // action manager's $el to keep its handlers alive, in case we'd come
        // back to that controller later
        var currentController = this.getCurrentController();
        if (currentController) {
            currentController.widget.$el.detach();
        }
        this.$el.empty();

        // empty the controller stack or replace the last controller as requested,
        // destroy the removed controllers and push the new controller to the stack
        var toDestroy;
        if (options.clear_breadcrumbs) {
            toDestroy = this.controllerStack;
            this.controllerStack = [];
        } else if (options.replace_last_action && this.controllerStack.length > 0) {
            toDestroy = [this.controllerStack.pop()];
        } else if (options.index !== undefined) {
            toDestroy = this.controllerStack.splice(options.index);
            // reject from the list of controllers to destroy the one that we are
            // currently pushing, or those linked to the same action as the one
            // linked to the controller that we are pushing
            toDestroy = _.reject(toDestroy, function (controllerID) {
                return controllerID === controller.jsID ||
                       self.controllers[controllerID].actionID === controller.actionID;
            });
        }
        var actionsToRemove = _.map(toDestroy, function (controllerID) {
            return self.controllers[controllerID].actionID;
        });
        _.each(_.uniq(actionsToRemove), this._removeAction.bind(this));
        this.controllerStack.push(controller.jsID);

        // update the control panel and append the new controller
        if (!controller.widget.need_control_panel) {
            this.controlPanel.do_hide();
        } else {
            this.controlPanel.update({
                breadcrumbs: this._getBreadcrumbs(),
            }, {clear: false});
        }
        dom.append(this.$el, controller.widget.$el, {
            in_DOM: this.isInDOM,
            callback: [{widget: controller.widget}],
        });
    },
    /**
     * Loads an action from the database given its ID.
     *
     * @private
     * @param {integer} actionID
     * @param {Object} context
     * @returns {Deferred<Object>} resolved with the description of the action
     */
    _loadAction: function (actionID, context) {
        var def = $.Deferred();
        this.trigger_up('load_action', {
            actionID: actionID,
            context: context,
            on_success: def.resolve.bind(def),
        });
        return def;
    },
    /**
     * Unlinks the given action and its controller from the internal structures
     * and destroys its controllers.
     *
     * @private
     * @param {string} actionID the id of the action to remove
     */
    _removeAction: function (actionID) {
        var action = this.actions[actionID];
        var controller = action.controller;
        controller.widget.destroy();
        delete this.controllers[controller.jsID];
        delete this.actions[action.jsID];
    },
    /**
     * Restores a controller from the controllerStack and destroys all
     * controllers stacked over the given controller.
     *
     * @private
     * @param {Object} controllerID
     * @param {Deferred} resolved when the controller has been restored
     */
    _restoreController: function (controllerID) {
        var self = this;
        var controller = this.controllers[controllerID];
        // AAB: AbstractAction should define a proper hook to execute code when
        // it is restored (other than do_show), and it should return a deferred
        return $.when(controller.widget.do_show()).then(function () {
            var index = _.indexOf(self.controllerStack, controllerID);
            self._pushController(controller, {index: index});
        });
    },
    /**
     * Starts the controller by appending it in a document fragment, so that it
     * is ready when it will be appended to the DOM. This allows to prevent
     * flickering for widgets doing async stuff in start().
     *
     * @private
     * @param {Object} controller
     * @returns {Deferred} resolved when the controller is ready
     */
    _startController: function (controller) {
        var fragment = document.createDocumentFragment();
        return $.when(controller.widget.appendTo(fragment));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     * @param {OdooEvent} ev.data.controllerID
     */
    _onBreadcrumbClicked: function (ev) {
        ev.stopPropagation();
        this._restoreController(ev.data.controllerID);
    },
    /**
     * Lets the 'push_state' event bubble up, but adds some information to the
     * state, like the action's id and the controller's title.
     *
     * @private
     * @param {OdooEvent} e
     */
    _onPushState: function (ev) {
        var controller = this.controllers[ev.data.controllerID];
        if (controller) {
            var action = this.actions[controller.actionID];
            if (action.target === 'new' || action._push_me === false) {
                // do not push state for actions in target="new" or for actions
                // that have been explicitly marked as not pushable
                ev.stopPropagation();
                return;
            }
            _.extend(ev.data.state, this._getControllerState(controller.jsID));
        }
    },
});

return ActionManager;

});
