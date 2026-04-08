/** @odoo-module **/

import {Many2OneField} from "@web/views/fields/many2one/many2one_field";
import {registry} from "@web/core/registry";

export class HelperText extends Many2OneField {
    setup() {
        super.setup();
    }

    get value() {
        if (!this.props.helperText) {
            return this.props.value[1]
        }
        return this.props.helperText
    }
}

HelperText.template = "web.HelperText";
HelperText.supportedTypes = ["many2one"];
HelperText.props = {
    ...Many2OneField.props,
    helperText: {type: String, optional: true},
    "*": true,
};

HelperText.extractProps = ({attrs, field}) => {
    return {
        ...Many2OneField.extractProps({attrs, field}),
        helperText: attrs.helperText,
    };
};

registry.category("fields").add("helper_text", HelperText);
