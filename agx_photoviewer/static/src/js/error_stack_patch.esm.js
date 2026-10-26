/** @odoo-module **/

/**
 * pdf.js 2.2 errors inherit from `new Error()` without a stack of their own,
 * which recent Chrome reports as `undefined`: Odoo's error dialog then
 * crashes on `error.stack.split` and hides the real error. Give such errors
 * a stack before Odoo's listeners (registered later, without capture) run.
 *
 * Odoo's `fullTraceback` walks `error.cause` and formats each link in the
 * chain, so a stackless Error anywhere in the chain crashes the dialog —
 * `error_service` sets `uncaughtError.cause = ev.reason` itself, which
 * guarantees at least two links to patch.
 */
function ensureStack(error, seen = new WeakSet()) {
    if (!(error instanceof Error) || seen.has(error)) {
        return;
    }
    seen.add(error);
    if (typeof error.stack !== "string") {
        try {
            Object.defineProperty(error, "stack", {
                value: `${error.name}: ${error.message}`,
                configurable: true,
                writable: true,
            });
        } catch (_e) {
            // A non-configurable stack we cannot overwrite — nothing more to do.
        }
    }
    if (error.cause) {
        ensureStack(error.cause, seen);
    }
}

window.addEventListener("unhandledrejection", (ev) => ensureStack(ev.reason), true);
window.addEventListener("error", (ev) => ensureStack(ev.error), true);
