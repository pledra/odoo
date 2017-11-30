# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

@odoo.tests.common.at_install(False)
@odoo.tests.common.post_install(True)
class TestUi(odoo.tests.HttpSeleniumCase):

    post_install = True
    at_install = False

    def test_01_admin_rte(self):
        self.selenium_run(
            "/web",
            "odoo.__DEBUG__.services['web_tour.tour'].run('rte')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.rte.ready",
            login='admin',
            max_tries=30)

    def test_02_admin_rte_inline(self):
        self.selenium_run(
            "/web",
            "odoo.__DEBUG__.services['web_tour.tour'].run('rte_inline')",
            ready="odoo.__DEBUG__.services['web_tour.tour'].tours.rte_inline.ready",
            login='admin',
            max_tries=30)
