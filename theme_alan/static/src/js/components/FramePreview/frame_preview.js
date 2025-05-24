/** @odoo-module alias=theme_alan.FramePreview **/

import { useService } from "@web/core/utils/hooks";
import { alanTemplate } from "theme_alan.mixins";

const { Component, onMounted } = owl;

class FramePreview extends Component {
    setup(){
        /** setup method */
        this.rpc = useService("rpc");
        onMounted(async ()=>{
            let $preview_template = await this.env.SnippetBuilder._getPreviewframeTemplate(false)
            $(this.__owl__.bdom.parentEl).find(".as-preview-section").empty().append($preview_template);
            $(this.__owl__.bdom.parentEl).find(".border").addClass("as-border-none");
            this.initializedSnippet();
        })
    }
    _backToDataConfig(){
        /** beck to data config component */
        this.env.SnippetBuilder.state.active_component = "FrameData";
    }
    async _save(){
        /** save the snippet */

        $(this.__owl__.bdom.parentEl).find("[data-default-content]").removeAttr("data-default-content");
        $(this.__owl__.bdom.parentEl).find(".as-preview-section").empty().append(this.env.SnippetBuilder.PreviewframeTemplate);
        this.props.snippet_origin.$target.empty().append($(this.__owl__.bdom.parentEl).find(".as-preview-section").html());

        let configs = await this.rpc('/save_user_custom_frame',{
            'frame':this.env.SnippetBuilder.frameCustomTemplate.html(),
            'is_default_frame':this.env.SnippetBuilder.defaultFrame,
            'default_frame_id':this.env.SnippetBuilder.defaultFrameId,
            'frame_config':$(this.__owl__.bdom.parentEl).find(".as-preview-section").html(),
        })
        this.props.snippet_origin.$target.attr('data-frame-work',configs.frame_config);
        this.props.snippet_origin.$target.attr('data-frame-id',configs.frame);
        this.props.close();
    }

    async initializedSnippet(){
        /** Add the snippet in preview if exist */
        let snippetList = $(this.__owl__.bdom.parentEl).find("[data-snippet-name]");

        let MegaMenuList = ['MegaMenuContent','MegaMenuProduct','MegaMenuBrand', 'MegaMenuCategory']
        let ProductList = ['ProductSlider','BestSellingProduct', 'LatestProduct', 'BrandProduct', 'CategoryProduct', 'ProductBanner','CategorySlider', 'BrandSlider','BlogSlider']

        for (const snippet of snippetList) {
            let static_snippet = ['MegaMenuContent','StaticSnippet'];
            if(static_snippet.includes($(snippet).attr("data-snippet-name"))){
                if($(snippet).attr("data-default-content") == undefined){
                    let pos_id =  "[data-pos-id='"+ $(snippet).data("posId") +"']";
                    let $set_data = this.props.snippet_origin.$target.find(pos_id)
                    $(snippet).empty().append($set_data.html());
                }else{
                    let temp_id = "theme_alan." + $(snippet).attr("data-selected-templ-id");
                    let template = alanTemplate.getStaticTemplate(temp_id, {})
                    $(snippet).empty().append($(template));
                }
            }else{
                let context = {
                    'snippet':$(snippet).attr("data-snippet-name"),
                    'record_ids':JSON.parse($(snippet).attr("data-records-ids")),
                    'modal':$(snippet).attr("data-modal"),
                    'design_editor':JSON.parse($(snippet).attr("data-design-edit")),
                }
                if($(snippet).attr("data-snippet-name") == "MegaMenuCategory"){
                    context['extra_info'] = JSON.parse($(snippet).attr("data-extra-info"))
                }
                let response = false
                if(MegaMenuList.includes($(snippet).attr("data-snippet-name"))){
                    response = await this.rpc("/get_mega_snippet_template",context);
                }else if(ProductList.includes($(snippet).attr("data-snippet-name"))){

                    response = await this.rpc("/get_products_snippet_template",context);
                }
                // Multi tabe
                if($(snippet).attr("data-snippet-name") == "BrandProduct"){
                    $(snippet).empty().append(response['template']);
                    var $template = $(snippet).find('.as_page_swiper');
                    for (let s_templ of $template) {
                        $(s_templ).attr("id",'as_swiper_slider_as');
                        if(Object.keys(response.slider_config).length != 0){
                            new Swiper("#as_swiper_slider_as", response.slider_config);
                        }
                        $(s_templ).removeAttr("id","as_swiper_slider_as")
                    }
                }
                else if($(snippet).attr("data-snippet-name") == "CategoryProduct"){
                    $(snippet).empty().append(response['template']);
                    var $template = $(snippet).find('.as_page_swiper')
                    for (let s_templ of $template) {
                        $(s_templ).attr("id",'as_swiper_slider_as');
                        if(Object.keys(response.slider_config).length != 0){
                            new Swiper("#as_swiper_slider_as", response.slider_config);
                        }
                        $(s_templ).removeAttr("id","as_swiper_slider_as")
                    }
                }
                else{
                    var $template =  $(response['template']).attr("id","as_swiper_slider_as");
                    $(snippet).empty().append($template);
                    if(Object.keys(response.slider_config).length != 0){
                        new Swiper("#as_swiper_slider_as", response.slider_config);
                    }
                    $template.removeAttr("id");
                }
            }
        }
    }
}

FramePreview.template = 'theme_alan.frame_preview';
FramePreview.components = {};

export default {
    FramePreview: FramePreview,
}