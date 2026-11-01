/** @odoo-module **/

/**
 * pdf.js 2.2 errors inherit from `new Error()` without a stack of their own,
 * which recent Chrome reports as `undefined`: Odoo's error dialog then
 * crashes on `error.stack.split` and hides the real error. Give such errors
 * a stack before Odoo's listeners (registered later, without capture) run.
 */
function ensureStack(error) {
    if (error instanceof Error && typeof error.stack !== "string") {
        Object.defineProperty(error, "stack", {
            value: `${error.name}: ${error.message}`,
            configurable: true,
            writable: true,
        });
    }
}

window.addEventListener("unhandledrejection", (ev) => ensureStack(ev.reason), true);
window.addEventListener("error", (ev) => ensureStack(ev.error), true);
