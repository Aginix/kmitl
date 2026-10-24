/** @odoo-module **/

// What an Odoo Link keeps of a webclient URL; cids, menu_id and the like are
// session state that would not hold on another database or for another user.
const ODOO_LINK_KEYS = ["action", "model", "id", "view_type", "active_id"];

/**
 * The URL to store for a Link Attachment typed by the user, or null when it
 * is not a web address. A scheme-less address is taken as https; a link to
 * this Odoo is kept host-less (`/web#…`) so it survives a copy of the
 * database to another server.
 */
export function normalizeLinkUrl(value) {
    let text = (value || "").trim();
    if (!text) {
        return null;
    }
    if (!text.startsWith("/") && !/^[a-z][a-z0-9+.-]*:/i.test(text)) {
        text = `https://${text}`;
    }
    let url = null;
    try {
        url = new URL(text, window.location.origin);
    } catch {
        return null;
    }
    if (!["http:", "https:"].includes(url.protocol)) {
        return null;
    }
    if (url.origin !== window.location.origin || url.pathname !== "/web") {
        return url.href;
    }
    const params = new URLSearchParams(url.hash.slice(1));
    const kept = new URLSearchParams();
    for (const key of ODOO_LINK_KEYS) {
        if (params.get(key)) {
            kept.set(key, params.get(key));
        }
    }
    return kept.has("action") || kept.has("model") ? `/web#${kept}` : null;
}

/**
 * The parameters of an Odoo Link ({action, model, id, view_type, …}), or
 * null when `url` is not one.
 */
export function parseOdooLink(url) {
    if (!url || !url.startsWith("/web#")) {
        return null;
    }
    return Object.fromEntries(new URLSearchParams(url.slice("/web#".length)));
}
