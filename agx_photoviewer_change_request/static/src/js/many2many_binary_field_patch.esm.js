/** @odoo-module **/

import {Many2ManyBinaryField} from "@web/views/fields/many2many_binary/many2many_binary_field";

// Fetch the outstanding Change requests count of each attachment for the badge.
Many2ManyBinaryField.fieldsToFetch = {
    ...Many2ManyBinaryField.fieldsToFetch,
    outstanding_request_count: {name: "outstanding_request_count", type: "integer"},
};
