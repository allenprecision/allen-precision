/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { renderToElement } from "@web/core/utils/render";
import Dialog from '@web/legacy/js/core/dialog';

export const ImgHotSpot = publicWidget.Widget.extend({
    selector:'.hotspot',
    init: function () {
        this._super.apply(this, arguments);
        this.rpc = this.bindService("rpc");
    },

    start:function(ev){
        var self = this;
        if(this.$target.find(".hs_icon").hasClass("dynamic_type")){
            if(this.$target.find(".hs_icon").attr("data-dy_type") == "popover"){
                let prod_tmpl_id = this.$target.find(".hs_icon").attr("data-product_tmpl_id");
                var pop_style = this.$target.find(".hs_icon").attr('data-po_style') == undefined ? '' :this.$target.find(".hs_icon").attr('data-po_style');
                if(prod_tmpl_id && pop_style){
                    this.rpc('/get_hotspot_product',{'product_tmpl_id':prod_tmpl_id, 'style':pop_style}).then((res)=>{
                        self._showPopover(res['template']);
                    })
                }
            }
            else if(this.$target.find(".hs_icon").attr("data-dy_type") == "modal"){
                this.$target.find(".hs_icon").addClass("as_quick_view");
                this.trigger_up('widgets_start_request', {
                    $target: $('.as_quick_view'),
                });
            }
        }else if(this.$target.find(".hs_icon").hasClass("static_type")){
            var title = this.$target.find(".hs_icon").attr('data-po_title') == undefined ? '':this.$target.find(".hs_icon").attr('data-po_title');
            var description = this.$target.find(".hs_icon").attr('data-po_desc') == undefined ? '':this.$target.find(".hs_icon").attr('data-po_desc');
            var btn_txt = this.$target.find(".hs_icon").attr('data-po_btxt') == undefined ? '':this.$target.find(".hs_icon").attr('data-po_btxt');

            var language = document.getElementsByTagName("html")[0].getAttribute("lang");
            var activeLang = language.replace(/-/g, "_");

            var data_lang = 'data-lang-'
            var activeLanguage = data_lang.concat("",activeLang);
            if(this.$target.find(".hs_icon").attr(activeLanguage)){
                title = this.$target.find(".hs_icon").attr(activeLanguage) == undefined ? '':this.$target.find(".hs_icon").attr(activeLanguage);
            }

            var data_descr_lang = 'data-description-lang-'
            var activeLanguageDescription = data_descr_lang.concat("",activeLang);
            if(this.$target.find(".hs_icon").attr(activeLanguageDescription)){
                description = this.$target.find(".hs_icon").attr(activeLanguageDescription) == undefined ? '':this.$target.find(".hs_icon").attr(activeLanguageDescription);
            }

            var data_btn_lang = 'data-btn-lang-'
            var activeLanguageBtn = data_btn_lang.concat("",activeLang);
            if(this.$target.find(".hs_icon").attr(activeLanguageBtn)){
                btn_txt = this.$target.find(".hs_icon").attr(activeLanguageBtn) == undefined ? '':this.$target.find(".hs_icon").attr(activeLanguageBtn);
            }

            var btn_url = this.$target.find(".hs_icon").attr('data-po_bturl') == undefined ? '':this.$target.find(".hs_icon").attr('data-po_bturl');
            var img_url = this.$target.find(".hs_icon").attr('data-po_imgurl') == undefined ? '' :this.$target.find(".hs_icon").attr('data-po_imgurl');
            var pop_thm = this.$target.find(".hs_icon").attr('data-po_theme') == undefined ? '' :this.$target.find(".hs_icon").attr('data-po_theme');
            var pop_style = this.$target.find(".hs_icon").attr('data-po_style') == undefined ? '' :this.$target.find(".hs_icon").attr('data-po_style');
            var context = { 'title':title,'description':description,'btn_txt':btn_txt,
                'btn_url':btn_url,'img_url':img_url,'pop_thm':pop_thm, 'pop_style':pop_style }
            if(this.$target.find(".hs_icon").attr("data-st_type") == "popover"){
                let template = $(renderToElement("theme_alan.s_static_hotspot_popover", {data:context}))
                this._showPopover(template);
            }
            else if(this.$target.find(".hs_icon").attr("data-st_type") == "modal"){
                this.$target.find(".hs_icon").on("click",function(){
                    new Dialog(this, {
                        $content:$(renderToElement("theme_alan.s_static_hotspot_popover", {data:context})),
                        renderHeader: false,
                        renderFooter: false,
                        backdrop: true,
                    }).open();
                })
            }
        }
    },
    _showPopover(template){
        var self = this;
        this.$target.find(".hs_icon").popover({
            html: true,
            container: 'body',
            trigger : 'manual',
            content: $(template),
        }).on("mouseenter", function () {
            $(this).popover("show");
            $(".popover").on("mouseleave", function () {
                self.$target.find(".hs_icon").popover('hide');
            }).addClass("as-popover");
        }).on("mouseleave", function () {
            setTimeout(function () {
                if (!$(".popover:hover").length) {
                    self.$target.find(".hs_icon").popover('hide');
                }
            }, 100);
        });

    }
})
publicWidget.registry.ImgHotSpot = ImgHotSpot;

export default {
    ImgHotSpot: publicWidget.registry.ImgHotSpot,
};
