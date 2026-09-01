/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { useState, onWillStart, onWillUpdateProps } from "@odoo/owl";

// The stock Many2one dropdown shows a single truncated line per option — for a
// contact that is rarely enough to tell people and companies apart while
// typing. This widget swaps in a rich, multi-line option template (name, type,
// VAT, address, e-mail, phone), enriched by one batched
// res.partner.get_partner_autocomplete_info call per set of options shown, and
// once a contact is picked it keeps a compact muted subtitle under the name so
// the field doesn't fall back to a bare name. Registered for both form and list
// so the same widget="agx_partner_many2one" works on a normal field and inside
// an editable tree.
//
// Which rows/subtitle parts show is configurable per use via widget options,
// e.g. options="{'show_vat': false, 'show_address': false}" — every row and
// subtitle part the server sends is tagged with a key (see
// _partner_autocomplete_rows/_partner_autocomplete_subtitle_parts), and any
// show_<key> option toggles that key off without code changes on either side,
// so a future new row/part is togglable for free.

// Rich list view reused by the "Search More…" dialog so it shows the same
// columns (type, VAT, address…) as the dropdown instead of the bare default
// partner list. Must be a fully-qualified xmlid (tree_view_ref requirement).
const SEARCH_MORE_VIEW = "agx_partner_autocomplete.res_partner_autocomplete_view_tree";

// True unless a key is explicitly turned off via a show_<key> display option.
// The cached payload always carries every key; filtering happens here, per
// widget instance, so the same cache entry serves instances configured
// differently.
function isShown(key, displayOptions) {
    return !displayOptions || displayOptions[key] !== false;
}

function filterByDisplayOptions(items, displayOptions) {
    return items.filter((item) => isShown(item.key, displayOptions));
}

// Module-level micro-batcher + cache for the selected-value subtitle: a tree
// full of partner cells resolves in a single RPC, and re-renders / edit toggles
// never refetch. Staleness is acceptable — the primary name always comes fresh
// from the field value; only the muted subtitle is cached.
const partnerInfoCache = new Map();
let pendingIds = new Set();
let pendingResolvers = [];
let flushScheduled = false;

function loadPartnerInfo(orm, id) {
    if (partnerInfoCache.has(id)) {
        return Promise.resolve(partnerInfoCache.get(id));
    }
    return new Promise((resolve) => {
        pendingIds.add(id);
        pendingResolvers.push({ id, resolve });
        if (flushScheduled) {
            return;
        }
        flushScheduled = true;
        // Flush on the next microtask: every partner cell rendered in the same
        // pass registers its id synchronously first, so they share one call.
        Promise.resolve().then(async () => {
            const ids = [...pendingIds];
            const resolvers = pendingResolvers;
            pendingIds = new Set();
            pendingResolvers = [];
            flushScheduled = false;
            let byId = {};
            try {
                const infos = await orm.call(
                    "res.partner",
                    "get_partner_autocomplete_info",
                    [ids]
                );
                for (const info of infos) {
                    partnerInfoCache.set(info.id, info);
                }
                byId = Object.fromEntries(infos.map((i) => [i.id, i]));
            } catch (e) {
                byId = {};
            }
            for (const r of resolvers) {
                r.resolve(byId[r.id] || null);
            }
        });
    });
}

class PartnerM2XAutocomplete extends Many2XAutocomplete {
    setup() {
        super.setup();
        // "Search More…" is the only caller of selectCreate, so wrapping it here
        // is enough to route that dialog to the rich partner list view.
        if (this.props.resModel === "res.partner") {
            const selectCreate = this.selectCreate;
            this.selectCreate = (params) =>
                selectCreate({
                    ...params,
                    context: {
                        ...params.context,
                        tree_view_ref: SEARCH_MORE_VIEW,
                    },
                });
        }
    }

    get optionsSource() {
        return {
            ...super.optionsSource,
            optionTemplate: "agx_partner_autocomplete.Option",
        };
    }

    async loadOptionsSource(request) {
        const options = await super.loadOptionsSource(request);
        // Only enrich when the field actually points at res.partner; applied to
        // any other comodel the widget degrades to the plain dropdown.
        if (this.props.resModel !== "res.partner") {
            return options;
        }
        // Action rows (Create…, Search More…, Start typing…) have no `value` —
        // leave them to fall back to their plain label.
        const ids = options.filter((o) => o.value).map((o) => o.value);
        if (ids.length) {
            const infos = await this.orm.call(
                "res.partner",
                "get_partner_autocomplete_info",
                [ids]
            );
            const byId = Object.fromEntries(infos.map((i) => [i.id, i]));
            // Pre-warm the subtitle cache so picking an option needs no extra RPC.
            for (const info of infos) {
                partnerInfoCache.set(info.id, info);
            }
            for (const o of options) {
                const info = o.value && byId[o.value];
                if (info) {
                    o.partnerInfo = {
                        ...info,
                        type: isShown("type", this.props.displayOptions) ? info.type : "",
                        rows: filterByDisplayOptions(info.rows, this.props.displayOptions),
                    };
                    // Applied to the <li>; the scss uses it to undo the
                    // single-line clamp the dropdown puts on every item.
                    o.classList = "o_partner_ac_item";
                }
            }
        }
        return options;
    }
}

export class PartnerAutocompleteM2oField extends Many2OneField {
    setup() {
        super.setup();
        this.partnerInfo = useState({ subtitle: "" });
        // Fire-and-forget so the field (and a whole tree of them) paints
        // immediately with the name; the muted subtitle pops in once resolved.
        onWillStart(() => {
            this._loadSubtitle(this.props.value);
        });
        onWillUpdateProps((nextProps) => {
            this._loadSubtitle(nextProps.value);
        });
    }

    async _loadSubtitle(value) {
        if (this.relation !== "res.partner" || !value) {
            this.partnerInfo.subtitle = "";
            return;
        }
        const info = await loadPartnerInfo(this.orm, value[0]);
        const parts = filterByDisplayOptions(
            (info && info.subtitle_parts) || [],
            this.props.displayOptions
        );
        this.partnerInfo.subtitle = parts.map((part) => part.value).join(" · ");
    }

    get extraLines() {
        // Render our compact secondary through the standard extra-lines slot
        // (below the name when read-only, below the input while editing) so no
        // template surgery is needed. Fall back to the stock multiline-name
        // behaviour when we have no subtitle.
        if (this.partnerInfo.subtitle) {
            return [this.partnerInfo.subtitle];
        }
        return super.extraLines;
    }

    get Many2XAutocompleteProps() {
        // The dropdown's row-filtering lives on PartnerM2XAutocomplete, which
        // only gets what this getter hands it — thread displayOptions through.
        return {
            ...super.Many2XAutocompleteProps,
            displayOptions: this.props.displayOptions,
        };
    }
}
PartnerAutocompleteM2oField.components = {
    ...Many2OneField.components,
    Many2XAutocomplete: PartnerM2XAutocomplete,
};
// Guarantee the root gets o_field_partner_autocomplete in every view type so the
// subtitle styling below can scope to this widget only.
PartnerAutocompleteM2oField.additionalClasses = ["o_field_partner_autocomplete"];
// A getter, not a plain spread-copy: other installed modules (e.g.
// web_m2x_options) patch Many2OneField.props in place with their own extra
// keys (searchMore, nodeOptions...) at their own module's load time, which can
// run after this one. A one-time spread here would freeze a stale schema and
// make OWL reject those keys as unknown; re-reading Many2OneField.props on
// every access always picks up whatever it currently is.
Object.defineProperty(PartnerAutocompleteM2oField, "props", {
    configurable: true,
    get() {
        return {
            ...Many2OneField.props,
            displayOptions: { type: Object, optional: true },
        };
    },
});

PartnerAutocompleteM2oField.extractProps = ({ attrs, field }) => {
    const props = Many2OneField.extractProps({ attrs, field });
    // Generic show_<key> -> displayOptions[<key>] mapping: any row/subtitle
    // part key a hook tags on the server becomes toggleable here for free,
    // with no change to this widget, e.g. options="{'show_vat': false}".
    const displayOptions = {};
    for (const optionName in attrs.options) {
        const match = /^show_(.+)$/.exec(optionName);
        if (match) {
            displayOptions[match[1]] = Boolean(attrs.options[optionName]);
        }
    }
    return { ...props, displayOptions };
};

registry.category("fields").add("agx_partner_many2one", PartnerAutocompleteM2oField);
// Register the list variant too so the rich dropdown works in editable trees;
// mirrors how core pins many2one for list to avoid the legacy fallback.
registry
    .category("fields")
    .add("list.agx_partner_many2one", PartnerAutocompleteM2oField);
