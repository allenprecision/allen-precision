/** @odoo-module alias=theme_alan.StaticSnippet **/

import { registry } from '@web/core/registry';
import { ContentBuilder } from "theme_alan.ContentBuilder";

const { Component, useSubEnv } = owl;

class StaticSnippet extends Component {
    setup(){
        /** Setup Method  */

        // Required to go back
        useSubEnv({'SnippetPicker':this.env.SnippetPicker})
        this.props.snippet = "StaticSnippet";
        this.props.active_id = "as_slider";
        this.props.snippet_content = registry.category("as_snippet_registry").get("as_static_snippets");

        useSubEnv({"StaticSnippets":this})
    }
}

StaticSnippet.template = 'theme_alan.s_static_snippet_configuration';
StaticSnippet.components = { ContentBuilder };

export default {
    StaticSnippet: StaticSnippet,
}