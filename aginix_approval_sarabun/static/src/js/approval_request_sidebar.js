odoo.define('aginix_approval_sarabun.ApprovalRequestPortalSidebar', function (require) {
'use strict';

const dom = require('web.dom');
var publicWidget = require('web.public.widget');
var PortalSidebar = require('portal.PortalSidebar');
var utils = require('web.utils');

publicWidget.registry.ApprovalRequestPortalSidebar = PortalSidebar.extend({
    selector: '.o_portal_approval_request_sidebar',
    events: {
        'click .o_portal_approval_request_print': '_onPrintApprovalRequest',
    },

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        var $approvalRequestHtml = this.$el.find('iframe#approval_request_html');
        var updateIframeSize = this._updateIframeSize.bind(this, $approvalRequestHtml);

        $(window).on('resize', updateIframeSize);

        var iframeDoc = $approvalRequestHtml[0].contentDocument || $approvalRequestHtml[0].contentWindow.document;
        if (iframeDoc.readyState === 'complete') {
            updateIframeSize();
        } else {
            $approvalRequestHtml.on('load', updateIframeSize);
        }

        return def;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {object} $el: the iframe
     */
    _updateIframeSize: function ($el) {
        var $wrapwrap = $el.contents().find('div#wrapwrap');
        // Set it to 0 first to handle the case where scrollHeight is too big for its content.
        $el.height(0);
        $el.height($wrapwrap[0].scrollHeight);

        // scroll to the right place after iframe resize
        if (!utils.isValidAnchor(window.location.hash)) {
            return;
        }
        var $target = $(window.location.hash);
        if (!$target.length) {
            return;
        }
        dom.scrollTo($target[0], {duration: 0});
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onPrintApprovalRequest: function (ev) {
        ev.preventDefault();
        var href = $(ev.currentTarget).attr('href');
        this._printIframeContent(href);
    },
});
});
