/** @odoo-module **/

import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";

// Fetch the annotation count of each attachment for the badge.
Many2ManyBinaryField.fieldsToFetch = {
    ...Many2ManyBinaryField.fieldsToFetch,
    annotation_count: {name: "annotation_count", type: "integer"},
};
