/** @odoo-module alias=theme_alan.FrameData **/

import { _t } from '@web/core/l10n/translation';
import { SnippetBox } from 'theme_alan.SnippetBox';
import { useService } from "@web/core/utils/hooks";
import { UserInformDialog } from "theme_alan.UserInformDialog"

const { Component, onMounted } = owl;

class FrameData extends Component {
    setup(){
        this.dialog = useService("dialog");
        this._rpc = useService("rpc");
        onMounted(() => {
            /** Mount the frame */
            if(this.env.SnippetBuilder.PreviewframeTemplate != false){
                $(this.__owl__.bdom.parentEl).find(".as-frame-data").append(this.env.SnippetBuilder.PreviewframeTemplate.html())
            }else{
                $(this.__owl__.bdom.parentEl).find(".as-frame-data").append(this.env.SnippetBuilder.frameCustomTemplate.html())
            }
            this._update_frame();
        });
    }
    _update_frame(){
        /** Update the Frame */
        $.each($(this.__owl__.bdom.parentEl).find(".as-grid"), function (idx, ele) {
            $(ele).removeClass("as-border-none");
            let btn;
            if($(ele).attr("data-snippet-name")){
                btn = "<button class='btn as-e-btn-success as-snippet-btn'><i class='fa fa-edit'></i> Edit </button> \
                    <button class='btn as-e-btn-danger as-snippet-rm-btn m-2'><i class='fa fa-trash'></i> Remove </button>";
            }else{
                btn = "<button class='btn as-e-btn-primary as-data-btn'><i class='fa fa-plus'/> Add </button>";
            }
            $(ele).empty().append(btn);
        });
        $(this.__owl__.bdom.parentEl).find(".as-frame-data").removeClass("d-none");
        $(this.__owl__.bdom.parentEl).find(".as-data-btn").click((ev)=>{
            ev.stopPropagation();
            this._openSnippetBox(ev,"SnippetList");
        });
        $(this.__owl__.bdom.parentEl).find(".as-snippet-btn").click((ev)=>{
            ev.stopPropagation();
            this._openSnippetBox(ev, $(ev.currentTarget).parent().attr("data-snippet-name"));
        });
        $(this.__owl__.bdom.parentEl).find(".as-snippet-rm-btn").click((ev)=>{
            ev.stopPropagation();
            this._removeSnippet(ev);
        });
    }

    _backToFrame(){
        this.dialog.add(UserInformDialog, {
            warning_msg:_t('All configuration will remove. Are you sure you want to go back?'),
            inform_type:"remove_config",
            onConfirm: async () => {
                this.env.SnippetBuilder.state.active_component = "FrameMaker";
            },
        });
    }
    _showPreview(ev){
        /** Go to preview with config data */
        let snippet_count = $(this.__owl__.bdom.parentEl).find("[data-snippet-name]").length;
        if(snippet_count != 0){
            $(this.__owl__.bdom.parentEl).find(".as-frame-data").find(".as-grid").empty();
            this.env.SnippetBuilder.PreviewframeTemplate = $(this.__owl__.bdom.parentEl).find(".as-frame-data");
            this.env.SnippetBuilder.state.active_component = "FramePreview";
            this.env.SnippetBuilder.props.allow_save = true
        }else{
            this.dialog.add(UserInformDialog, {
                warning_msg:_t('Oops, Please configure at least one snippet to see preview.'),
                inform_type:"no_snippet",
                onConfirm: () => {
                    this.env.SnippetBuilder.state.active_component = "FrameMaker";
                },
            });
        }
    }

    _openSnippetBox(ev, snippet){
        /** Use to open the select snippet with init data */
        let static_snippet = ['MegaMenuContent', 'StaticSnippet'];
        let initData;

        if(snippet != "SnippetList"){
            if(static_snippet.includes(snippet)){
                initData = {
                    'selected_templ_id': $(ev.currentTarget).parent().attr("data-selected-templ-id"),
                    'active_id': $(ev.currentTarget).parent().attr("data-active-id"),
                }
            }else{
                initData =  {
                    'record_ids': JSON.parse($(ev.currentTarget).parent().attr("data-records-ids")),
                    'modal': $(ev.currentTarget).parent().attr("data-modal"),
                    'design_edit': JSON.parse($(ev.currentTarget).parent().attr("data-design-edit")),
                }
                if(snippet == "MegaMenuCategory"){
                    if($(ev.currentTarget).parent().attr("data-extra-info")){
                        initData['extra_info'] = JSON.parse($(ev.currentTarget).parent().attr("data-extra-info"))
                    }
                }
            }
        }
        const dialog = this.env.SnippetBuilder.props.snippet_origin.call("dialog", "add", SnippetBox,{
            'title': 'Snippet Box',
            'size': 'as-full-screen',
            'initSnippet':snippet,
            'initData':initData,
            'col_size':$(ev.currentTarget).parent().attr("data-size"),
            'snippet_origin':$(ev.currentTarget).parent(),
            'SnippetBuilder':this.env.SnippetBuilder,
            'SnippetBoxBuilder':SnippetBox,
            'snippet_list':this.env.SnippetBuilder.props.snippet_list.snippets,
        });
        // dialog.mount(this.env.SnippetBuilder.props.snippet_origin.el);
    }

    _removeSnippet(ev){
        /** Use to remove current snippet */
        $(ev.currentTarget).parent().removeAttr("data-modal")
                            .removeAttr("data-snippet-name")
                            .removeAttr("data-records-ids")
                            .removeAttr("data-design-edit")
                            .removeAttr("data-extra-info")
                            .removeAttr("data-selected-templ-id")
                            .removeAttr("data-active-id")
        let btn = '<button class="btn as-e-btn-primary as-data-btn"><i class="fa fa-plus"></i> Add </button>';
        $(ev.currentTarget).parent().empty().append(btn);
        this._update_frame()

    }
}

FrameData.template = 'theme_alan.frame_data';

export default {
    FrameData: FrameData,
}
