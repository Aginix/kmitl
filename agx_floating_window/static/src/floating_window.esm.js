/** @odoo-module **/

import {Component, markRaw, reactive, useRef, useState} from "@odoo/owl";
import {ErrorHandler} from "@web/core/utils/components";
import {registry} from "@web/core/registry";

// The window may be resized down to this size.
const MIN_WIDTH = 320;
const MIN_HEIGHT = 200;
// Room kept around a new window, and the shift between windows opened in a row.
const MARGIN = 24;
const CASCADE = 32;
// Part of the header that must stay on screen while dragging.
const HEADER_GRIP = 48;

export class FloatingWindow extends Component {
    setup() {
        this.rootRef = useRef("root");
        this.state = useState({maximized: false});
    }

    get style() {
        const win = this.props.window;
        if (this.state.maximized) {
            return `z-index: ${win.zIndex};`;
        }
        return (
            `z-index: ${win.zIndex}; left: ${win.left}px; top: ${win.top}px;` +
            ` width: ${win.width}px; height: ${win.height}px;`
        );
    }

    /**
     * The native resize handle sets the inline size behind OWL's back: store
     * it before any render rewrites the style attribute.
     */
    syncSize() {
        if (!this.state.maximized) {
            this.props.window.width = this.rootRef.el.offsetWidth;
            this.props.window.height = this.rootRef.el.offsetHeight;
        }
    }

    onPointerDown() {
        this.syncSize();
        this.props.focus(this.props.window.id);
    }

    onHeaderPointerDown(ev) {
        if (this.state.maximized || ev.button !== 0 || ev.target.closest("button")) {
            return;
        }
        ev.preventDefault();
        const win = this.props.window;
        const el = this.rootRef.el;
        const startX = ev.clientX - win.left;
        const startY = ev.clientY - win.top;
        const header = ev.currentTarget;
        // Capture the pointer so the drag always ends, even when the button is
        // released outside the browser window.
        header.setPointerCapture(ev.pointerId);
        el.classList.add("o_agx_floating_window_moving");
        const onMove = (moveEv) => {
            win.left = Math.min(
                Math.max(moveEv.clientX - startX, HEADER_GRIP - win.width),
                window.innerWidth - HEADER_GRIP
            );
            win.top = Math.min(
                Math.max(moveEv.clientY - startY, 0),
                window.innerHeight - HEADER_GRIP
            );
        };
        const onEnd = () => {
            el.classList.remove("o_agx_floating_window_moving");
            header.removeEventListener("pointermove", onMove);
            header.removeEventListener("lostpointercapture", onEnd);
        };
        header.addEventListener("pointermove", onMove);
        header.addEventListener("lostpointercapture", onEnd);
    }

    onKeydown(ev) {
        // Escape inside the content belongs to it (e.g. closing an autocomplete).
        if (
            ev.key !== "Escape" ||
            ev.defaultPrevented ||
            ev.target.closest(".o_agx_floating_window_body")
        ) {
            return;
        }
        // Keep Odoo's hotkeys from also closing a dialog below.
        ev.stopPropagation();
        this.props.close(this.props.window.id);
    }

    toggleMaximize() {
        this.syncSize();
        this.state.maximized = !this.state.maximized;
    }
}
FloatingWindow.template = "agx_floating_window.FloatingWindow";
FloatingWindow.props = {
    window: Object,
    focus: Function,
    close: Function,
};

export class FloatingWindowContainer extends Component {
    handleError(error, win) {
        this.props.close(win.id);
        Promise.resolve().then(() => {
            throw error;
        });
    }
}
FloatingWindowContainer.template = "agx_floating_window.FloatingWindowContainer";
FloatingWindowContainer.components = {ErrorHandler, FloatingWindow};
FloatingWindowContainer.props = {
    windows: Object,
    focus: Function,
    close: Function,
};

export const floatingWindowService = {
    start() {
        const windows = reactive({});
        let nextId = 0;
        // Stacking order inside the container, which itself sits above the
        // page and below Odoo's dialogs and popovers.
        let nextZIndex = 0;

        function focus(id) {
            const win = windows[id];
            if (win && win.zIndex !== nextZIndex) {
                win.zIndex = ++nextZIndex;
            }
        }

        function close(id) {
            delete windows[id];
        }

        /**
         * Open `Component` with `props` in a new floating window.
         *
         * @param {Object} params
         * @returns {Function} closes the window
         */
        function open({title, Component: WindowComponent, props = {}, width, height}) {
            const id = ++nextId;
            const shift = (Object.keys(windows).length % 5) * CASCADE;
            const winWidth = Math.max(
                MIN_WIDTH,
                Math.min(width || 900, window.innerWidth - 2 * MARGIN)
            );
            const winHeight = Math.max(
                MIN_HEIGHT,
                Math.min(height || 600, Math.round(window.innerHeight * 0.6))
            );
            windows[id] = {
                id,
                title: title || "",
                Component: markRaw(WindowComponent),
                props: markRaw(props),
                width: winWidth,
                height: winHeight,
                // Open bottom right so the form fields and the button box at
                // the top stay in view.
                left: Math.max(MARGIN, window.innerWidth - winWidth - MARGIN - shift),
                top: Math.max(MARGIN, window.innerHeight - winHeight - MARGIN - shift),
                zIndex: ++nextZIndex,
            };
            return () => close(id);
        }

        registry.category("main_components").add("FloatingWindowContainer", {
            Component: FloatingWindowContainer,
            props: {windows, focus, close},
        });

        return {open, close};
    },
};

registry.category("services").add("agx_floating_window", floatingWindowService);

/**
 * Client action opening the client action named in `params.tag` in a floating
 * window, with this action's name and context:
 * {type: "ir.actions.client", tag: "agx_floating_window", params: {tag: ...}}
 */
registry.category("actions").add("agx_floating_window", (env, action) => {
    const tag = action.params && action.params.tag;
    const ClientAction = registry.category("actions").get(tag);
    env.services.agx_floating_window.open({
        title: action.name,
        Component: ClientAction,
        props: {action: {...action, tag, target: "new"}},
        width: action.params.width,
        height: action.params.height,
    });
});
