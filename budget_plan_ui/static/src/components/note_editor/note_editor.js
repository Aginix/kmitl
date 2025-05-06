/** @odoo-module **/

import { Component, useState, useEnv } from "@odoo/owl";

export class NoteEditor extends Component {
    setup() {
        this.env = useEnv();
        this.state = useState({
            toggle: false,
            noteValue: this.props.data.plan_line ? 
            this.props.data.plan_line.note ? 
            this.props.data.plan_line.note : "" : "",
        });
    }

    async saveNote() {
        await this.props.updateNote(this.state.noteValue, this.props.data);
        this.toggleNote()
    }

    sendEvent() {
        this.env.bus.trigger("custom_event", { message: "Hello from AnotherComponent" });
    }

    toggleNote() {
        this.state.toggle = !this.state.toggle;
    }

    resetNote() {
        this.state.noteValue = this.props.data.plan_line ?
         this.props.data.plan_line.note ? 
         this.props.data.plan_line.note : "" : "";
        this.state.toggle = false;
    }
}

NoteEditor.template = "budget_plan_ui.NoteEditor";
NoteEditor.props = {
    data:Object,
    updateNote: Function,
}