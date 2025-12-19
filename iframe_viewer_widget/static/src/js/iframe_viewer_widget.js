/** @odoo-module **/

import {Component, onMounted, useRef, useState} from "@odoo/owl";

import {CharField} from "@web/views/fields/char/char_field";
import { isValidAnchor } from "web.utils";
import {registry} from "@web/core/registry";

class IFrameViewerWidget extends CharField {
    setup() {
        super.setup();
        this.iframeRef = useRef("iframe");
        this.state = useState({
            url: this.props.value || "",
            loading: true,
            error: false,
        });
    }

    get displayName() {
        return this.props.value || "";
    }

    onIframeLoad() {
        this.state.loading = false;
        this.state.error = false;
    }

    onIframeError() {
        this.state.loading = false;
        this.state.error = true;
    }

    get iframeUrl() {
        const url = this.props.value;
        if (!url) return "";

        return url;
    }

    get name() {
        return this.props.name;
    }
}

IFrameViewerWidget.template = "iframe_widget.IFrameViewerWidget";
IFrameViewerWidget.components = {};

registry.category("fields").add("iframe_viewer", IFrameViewerWidget);

// Template definition
const {xml} = owl;
IFrameViewerWidget.template = xml`
<div class="o_iframe_viewer_widget">
    <style>
        .o_field_iframe_viewer {
            width: 100%;
        }
    </style>
    <div t-if="iframeUrl" class="o_iframe_container mt-2" style="position: relative; width: 100%; height: 400px;">
        <div t-if="state.loading" class="o_iframe_loading" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 2;">
            <i class="fa fa-spinner fa-spin fa-2x"></i>
            <div class="mt-2">Loading...</div>
        </div>
        <div t-if="state.error" class="o_iframe_error alert alert-warning" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 2; text-align: center;">
            <i class="fa fa-exclamation-triangle fa-2x"></i>
            <div class="mt-2">Unable to load URL</div>
            <small t-esc="iframeUrl"></small>
        </div>
        <iframe
            t-ref="iframe"
            t-att-id="name"
            t-att-name="name"
            t-att-src="iframeUrl"
            t-on-load="onIframeLoad"
            t-on-error="onIframeError"
            width="100%"
            height="100%"
            frameborder="0"
            scrolling="no"
            sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
        ></iframe>
    </div>
    <div t-if="!iframeUrl" class="text-muted">
        No URL specified
    </div>
</div>
`;
