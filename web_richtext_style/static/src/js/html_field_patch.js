/** @odoo-module **/

import { HtmlField } from '@web_editor/js/backend/html_field';

const _originalExtractProps = HtmlField.extractProps;

HtmlField.extractProps = (args) => {
    const props = _originalExtractProps(args);
    const { attrs } = args;
    if ('allowCommandJustify' in attrs.options) {
        props.wysiwygOptions.allowCommandJustify = Boolean(attrs.options.allowCommandJustify);
    }
    return props;
};
