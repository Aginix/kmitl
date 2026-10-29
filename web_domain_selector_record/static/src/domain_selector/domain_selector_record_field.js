/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { DomainSelectorFieldInput } from "@web/core/domain_selector/fields/domain_selector_field_input";
import { DomainSelectorLeafNode } from "@web/core/domain_selector/domain_selector_leaf_node";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";

const dso = registry.category("domain_selector/operator");
const RECORD_OPERATORS = ["=", "!=", "in", "not in", "child_of", "parent_of"];
const SEARCH_LIMIT = 8;

function toIds(value) {
    return (Array.isArray(value) ? value : [value]).filter((id) => Number.isInteger(id) && id > 0);
}

/**
 * Display names of records, cached per model. Archived records are included;
 * ids that are deleted or not readable are simply missing.
 */
function useDisplayNames() {
    const orm = useService("orm");
    const cache = {};
    return {
        get(resModel, id) {
            return (cache[resModel] || {})[id];
        },
        set(resModel, id, name) {
            cache[resModel] = Object.assign(cache[resModel] || {}, { [id]: name });
        },
        async load(resModel, ids) {
            const names = (cache[resModel] = cache[resModel] || {});
            const missing = ids.filter((id) => !(id in names));
            if (!missing.length) {
                return;
            }
            try {
                const records = await orm.searchRead(
                    resModel,
                    [["id", "in", missing]],
                    ["display_name"],
                    { context: { active_test: false } }
                );
                for (const record of records) {
                    names[record.id] = record.display_name;
                }
            } catch (_e) {
                // no read access: fall back to showing the ids
            }
        },
    };
}

/**
 * Value editor of a relational field: a name autocomplete instead of the raw
 * id text box. Text operators (ilike, ...) keep the standard text box.
 */
export class DomainSelectorRecordField extends Component {
    setup() {
        this.orm = useService("orm");
        this.names = useDisplayNames();
        onWillStart(() => this.loadNames(this.props));
        onWillUpdateProps((nextProps) => this.loadNames(nextProps));
    }

    loadNames(props) {
        if (this.isRecordValue(props)) {
            return this.names.load(props.field.relation, toIds(props.value));
        }
    }

    isRecordValue(props) {
        const { value } = props;
        return (
            RECORD_OPERATORS.includes(props.operator.value) &&
            (Number.isInteger(value) ||
                (Array.isArray(value) && value.every((id) => Number.isInteger(id))))
        );
    }

    get isMulti() {
        return Array.isArray(this.props.value);
    }
    get ids() {
        return toIds(this.props.value);
    }
    displayName(id) {
        return this.names.get(this.props.field.relation, id) || String(id);
    }
    get inputValue() {
        return this.isMulti || !this.ids.length ? "" : this.displayName(this.ids[0]);
    }
    get sources() {
        return [{ placeholder: _t("Loading..."), options: this.loadOptions.bind(this) }];
    }

    async loadOptions(request) {
        const records = await this.orm.call(this.props.field.relation, "name_search", [], {
            name: request,
            args: this.isMulti ? [["id", "not in", this.ids]] : [],
            limit: SEARCH_LIMIT,
        });
        if (!records.length) {
            return [{ label: _t("No records"), classList: "o_m2o_no_result", unselectable: true }];
        }
        return records.map(([id, name]) => ({ value: id, label: name }));
    }

    onSelect(option) {
        this.names.set(this.props.field.relation, option.value, option.label);
        const value = this.isMulti ? [...this.ids, option.value] : option.value;
        this.props.update({ value });
    }
    removeId(id) {
        this.props.update({ value: this.ids.filter((i) => i !== id) });
    }
}
Object.assign(DomainSelectorRecordField, {
    template: "web_domain_selector_record.DomainSelectorRecordField",
    components: { AutoComplete, DomainSelectorFieldInput },

    onDidTypeChange() {
        return { value: 0 };
    },
    getOperators() {
        return ["=", "!=", "in", "not in", "child_of", "ilike", "not ilike", "set", "not set"].map(
            (key) => dso.get(key)
        );
    },
});

registry
    .category("domain_selector/fields")
    .add("one2many", DomainSelectorRecordField, { force: true })
    .add("many2one", DomainSelectorRecordField, { force: true })
    .add("many2many", DomainSelectorRecordField, { force: true });

/**
 * Read-only display of a relational value: record names instead of ids.
 */
export class DomainSelectorRecordValue extends Component {
    setup() {
        this.names = useDisplayNames();
        onWillStart(() => this.names.load(this.props.resModel, toIds(this.props.value)));
        onWillUpdateProps((nextProps) =>
            this.names.load(nextProps.resModel, toIds(nextProps.value))
        );
    }

    get values() {
        return Array.isArray(this.props.value) ? this.props.value : [this.props.value];
    }
    displayName(value) {
        return this.names.get(this.props.resModel, value) || value;
    }
}
DomainSelectorRecordValue.template = "web_domain_selector_record.DomainSelectorRecordValue";

DomainSelectorLeafNode.components = {
    ...DomainSelectorLeafNode.components,
    DomainSelectorRecordValue,
};
