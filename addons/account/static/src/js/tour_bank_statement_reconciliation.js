odoo.define('account.tour_bank_statement_reconciliation', function(require) {
'use strict';

var core = require('web.core');
var Tour = require('web.Tour');

var _t = core._t;

Tour.register({
    id: 'bank_statement_reconciliation',
    name: _t("Reconcile the demo bank statement"),
    path: '/web#action=account.open_account_journal_dashboard_kanban',
    mode: 'test',
    steps: [
        // Go to the first statement reconciliation
        {
            title:     "go to 'more'",
            element:   '.o_kanban_record:first a.o_kanban_manage_toggle_button',
        },
        {
            title:     "go to bank statements",
            element:   '.o_kanban_record:first .oe_kanban_action_a:contains("Bank Statement")',
        },
        {
            title:     "select first bank statement",
            element:   'tr:contains("BNK/2014/001")',
        },
        {
            title:     "click the reconcile button",
            element:   'button:contains("Reconcile")',
        },


        // Check mutual exclusion of move lines
/*        {
            title:      "set second reconciliation in match mode",
            element:    '.o_bank_statement_reconciliation_line:nth-child(2) .initial_line'
        },
        {
            title:      "deselect SAJ/2014/002 from second reconciliation",
            element:    '.o_bank_statement_reconciliation_line:nth-child(2) .accounting_view .mv_line:contains("SAJ/2014/002")'
        },
        {
            title:      "check it appeared in first reconciliation's matches list and select SAJ/2014/002 in second reconciliation",
            waitNot:    '.o_bank_statement_reconciliation_line:nth-child(2) .accounting_view .mv_line:contains("SAJ/2014/002")',
            waitFor:    '.o_bank_statement_reconciliation_line:first-child .mv_line:contains("SAJ/2014/002")',
            element:    '.o_bank_statement_reconciliation_line:nth-child(2) .mv_line:contains("SAJ/2014/002")'
        },*/


        // Make a partial reconciliation
        {
            title:      "select SAJ/2014/001",
            element:    '.o_bank_statement_reconciliation_line:first-child  .initial_line'
        },
        {
            title:      "click on the partial reconciliation button",
            element:    '.oe_bank_statement_reconciliation_line:first-child button:contains("Validate")'
        },
        {
            title:      "click on the OK button",
            element:    '.oe_bank_statement_reconciliation_line:first-child .button_ok.oe_highlight'
        },


        // Test changing the partner
        {
            title:      "change the partner (1)",
            waitNot:    '.oe_bank_statement_reconciliation_line:nth-child(4)', // wait for the reconciliation to be processed
            element:    '.oe_bank_statement_reconciliation_line:first-child .partner_name'
        },
        {
            title:      "change the partner (2)",
            element:    '.oe_bank_statement_reconciliation_line:first-child .change_partner_container input',
            sampleText: 'Vauxoo',
        },
        {
            title:      "change the partner (3)",
            element:    '.ui-autocomplete .ui-menu-item:contains("Vauxoo")'
        },
        {
            title:      "check the reconciliation is reloaded and has no match",
            element:    '.oe_bank_statement_reconciliation_line:first-child.no_match',
        },
        {
            title:      "change the partner back (1)",
            element:    '.oe_bank_statement_reconciliation_line:first-child .partner_name'
        },
        {
            title:      "change the partner back (2)",
            element:    '.oe_bank_statement_reconciliation_line:first-child .change_partner_container input',
            sampleText: 'Best Designers',
        },
        {
            title:      "change the partner back (3)",
            element:    '.ui-autocomplete .ui-menu-item:contains("Best Designers")'
        },
        {
            title:      "select SAJ/2014/002",
            element:    '.oe_bank_statement_reconciliation_line:first-child .mv_line:contains("SAJ/2014/002")'
        },
        {
            title:      "click on the OK button",
            element:    '.oe_bank_statement_reconciliation_line:first-child .button_ok.oe_highlight'
        },


        // Create a new move line in first reconciliation and validate it
        {
            title:      "check following reconciliation passes in mode create",
            waitNot:    '.oe_bank_statement_reconciliation_line:nth-child(3)', // wait for the reconciliation to be processed
            element:    '.oe_bank_statement_reconciliation_line:first-child[data-mode="create"]'
        },
        {
            title:      "click the Profit/Loss preset",
            element:    '.oe_bank_statement_reconciliation_line:first-child button:contains("Profit / Loss")'
        },
        {
            title:      "click on the OK button",
            element:    '.oe_bank_statement_reconciliation_line:first-child .button_ok.oe_highlight'
        },


        // Leave an open balance
        {
            title:      "select SAJ/2014/003",
            waitNot:    '.oe_bank_statement_reconciliation_line:nth-child(2)', // wait for the reconciliation to be processed
            element:    '.oe_bank_statement_reconciliation_line:first-child .mv_line:contains("SAJ/2014/003")'
        },
        {
            title:      "click on the Keep Open button",
            element:    '.oe_bank_statement_reconciliation_line:first-child .button_ok:not(.oe_highlight)'
        },


        // Be done
        {
            title:      "check 'finish screen' and close the statement",
            waitFor:    '.done_message',
            element:    '.button_close_statement'
        },
        {
            title:      "check the statement is closed",
            element:    '.oe_form_container header .label:contains("Closed")'
        },
    ]
});

});
