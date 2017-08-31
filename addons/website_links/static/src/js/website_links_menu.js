odoo.define('website_links.website_links_menu', function (require) {
'use strict';

var editPages = require('website.editPages');

/* The purpose of this script is to copy the current URL of the website
 * into the URL form of the URL shortener (module website_links) 
 * when the user click the link "Share this page" on top of the page.
*/
$(document).ready(function () {
  $('#o_website_links_share_page').attr('href', '/r?u=' + encodeURIComponent(window.location.href));
});

editPages.ManagePagesMenu.include({
    xmlDependencies: editPages.ManagePagesMenu.prototype.xmlDependencies.concat(
        ['/website_links/static/src/xml/track_page.xml']
    ),
});
});
