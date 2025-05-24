/** @odoo-module alias=theme_alan.ContentBuilder **/

import { useService } from "@web/core/utils/hooks";
import { UserInformDialog } from 'theme_alan.UserInformDialog';

const { Component, useSubEnv, useState } = owl;

class ContentBuilder extends Component {
    setup(){
        /** Setup Method  */
        this.dialog = useService("dialog");
        let init_data = this.env.SnippetBox.props.initData
        let init_state = false;
        if(init_data != undefined){
            if(init_data.active_id != undefined && init_data.selected_templ_id != undefined){
                this.state = useState({ 'active_id':init_data.active_id,
                'selected_templ_id':init_data.selected_templ_id })
                init_state = true;
            }
        }
        if(!init_state){
            this.state = useState({
                'active_id':this.props.active_id,
                'selected_templ_id':false
            })
        }
        useSubEnv({"ContentBuilder":this});
    }
    change_tab(ev){
        let id = $(ev.target).attr("data-tag")
        this.state.active_id = id
    }
    selete_template(ev){
        let templ_id = $(ev.target).attr("data-temp");
        this.state.selected_templ_id = templ_id;
    }
    save(){
        if(this.state.selected_templ_id != false){
            let snippet_origin = this.env.SnippetBox.props.snippet_origin;
            snippet_origin.attr("data-snippet-name", this.props.snippet);
            snippet_origin.attr("data-active-id",this.state.active_id);
            snippet_origin.attr("data-selected-templ-id", this.state.selected_templ_id);
            snippet_origin.attr("data-default-content", true);

            let btn = "<button class='btn as-e-btn-success as-snippet-btn m-2'><i class='fa fa-edit'></i> Edit </button> \
                    <button class='btn as-e-btn-danger as-snippet-rm-btn m-2'> <i class='fa fa-trash'></i> Remove </button>";

            $(snippet_origin).empty().append(btn);
            $(snippet_origin).find(".as-snippet-btn").click((ev)=>{
                ev.stopPropagation();
                this._openSnippet(ev, this.props.snippet);
            });
            $(snippet_origin).find(".as-snippet-rm-btn").click((ev)=>{
                ev.stopPropagation();
                this._removeSnippet(ev);
            });
            this.env.SnippetBox.props.close()

        }else{
            this.dialog.add(UserInformDialog, {
                warning_msg:'Oops, Please select snippet.',
                inform_type:"no_snippet_config",
                onConfirm: async () => {
                    this.env.SnippetBuilder.state.active_component = "FrameMaker";
                },
            });
        }
    }
    close(){
        this.env.SnippetBox.props.close();
    }

    _openSnippet(ev, Snippet){
        var initData = {
            'selected_templ_id': $(ev.currentTarget).parent().attr("data-selected-templ-id"),
            'active_id': $(ev.currentTarget).parent().attr("data-active-id"),
        }
        const dialog = this.env.SnippetBox.props.SnippetBuilder.props.snippet_origin.call("dialog", "add", this.env.SnippetBox.props.SnippetBoxBuilder,{
            'title': 'Snippet Box',
            'initSnippet':Snippet,
            'initData':initData,
            'snippet_origin':$(ev.currentTarget).parent(),
            'SnippetBuilder':this.env.SnippetBox.props.SnippetBuilder,
            'SnippetBoxBuilder':this.env.SnippetBox.props.SnippetBoxBuilder,
        });
        dialog.mount(this.env.SnippetBox.props.SnippetBuilder.props.snippet_origin.el);
    }
    _removeSnippet(ev){
        var self = this;
        $(ev.currentTarget).parent().removeAttr("data-selected-templ-id")
                            .removeAttr("data-active-id")
                            .removeAttr("data-default-content")
                            .removeAttr("data-snippet-name")

        let btn = '<button class="btn as-e-btn-primary as-data-btn"><i class="fa fa-plus"></i> Add </button>';
        $(this.env.SnippetBox.props.snippet_origin).empty().append(btn)
        $(this.env.SnippetBox.props.snippet_origin).find(".as-data-btn").click((ev)=>{
            ev.stopPropagation();
            self._openSnippet(ev,'SnippetList');
        });
    }
}

ContentBuilder.template = 'theme_alan.content_builder';
ContentBuilder.components = {  };

export default {
    ContentBuilder: ContentBuilder,
}
