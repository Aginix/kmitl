odoo.define('agx_sarabun.SarabunDocumentPortalSidebar', function (require) {
'use strict';

const dom = require('web.dom');
var publicWidget = require('web.public.widget');
var PortalSidebar = require('portal.PortalSidebar');
var utils = require('web.utils');

publicWidget.registry.SarabunDocumentPortalSidebar = PortalSidebar.extend({
    selector: '.o_portal_sarabun_document_sidebar',
    events: {
        'click .o_portal_sarabun_document_print': '_onPrintPurhaseRequest',
    },

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        var $SarabunDocument = this.$el.find('iframe#sarabun_document_html');
        var updateIframeSize = this._updateIframeSize.bind(this, $SarabunDocument);

        $(window).on('resize', updateIframeSize);

        var iframeDoc = $SarabunDocument[0].contentDocument || $SarabunDocument[0].contentWindow.document;
        if (iframeDoc.readyState === 'complete') {
            updateIframeSize();
        } else {
            $SarabunDocument.on('load', updateIframeSize);
        }

        return def;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the iframe is loaded or the window is resized on customer portal.
     * The goal is to expand the iframe height to display the full report without scrollbar.
     *
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
    _onPrintPurhaseRequest: function (ev) {
        ev.preventDefault();
        var href = $(ev.currentTarget).attr('href');
        this._printIframeContent(href);
    },
});
});
