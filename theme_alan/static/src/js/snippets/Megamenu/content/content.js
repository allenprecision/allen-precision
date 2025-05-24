/** @odoo-module alias=theme_alan.MegaMenuContent **/

import { registry } from '@web/core/registry';
import { ContentBuilder } from "theme_alan.ContentBuilder";

const { Component, useSubEnv } = owl;

class MegaMenuContent extends Component {
    setup(){
        /** Setup Method  */

        // Required to go back
        useSubEnv({'SnippetPicker':this.env.SnippetPicker})
        this.props.snippet = "MegaMenuContent";
        this.props.active_id = "as_slider";
        this.props.snippet_content =this.props.snippet_content = registry.category("as_snippet_registry").get("as_static_snippets");

        useSubEnv({"MegaMenuContent":this})
    }
}

MegaMenuContent.template = 'theme_alan.m_content_configuration';
MegaMenuContent.components = { ContentBuilder };

export default {
    MegaMenuContent: MegaMenuContent,
}