/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";
import { MediaDialog } from '@web_editor/components/media_dialog/media_dialog';
import { renderToElement } from "@web/core/utils/render";
import Dialog from '@web/legacy/js/core/dialog';
import { loadLanguages,_t } from "@web/core/l10n/translation";

var popoverShow = false;

options.SnippetOptionWidget.include({
    events: Object.assign({}, options.SnippetOptionWidget.prototype.events, {
        'click .add_img_hotspot':'_addHotSpotIcon',
    }),
    _addHotSpotIcon:function(){
        var $block = '<div class="hotspot" style="position: absolute;top:50%;left: 50%;transform: translate(-50%, -50%);"> \
                        <p class="hs_icon as_img_icon" data-name="Block"> \
                            <a href="#" class="icon"> \
                                icon\
                            </a>\
                        </p> \
                    </div>';
        if(!this.$target.parent().hasClass("hs_container")){
            this.$target.wrap("<div class='hs_container' style='position:relative'></div>");
        }
        this.$target.after($block);
        this.$target.parent().find('.as_img_icon').trigger('click').removeClass('as_img_icon');
    }
});
const AlanWebsiteTranslation = Dialog.extend({
    willStart: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            switch (self.size) {
                case 'extra-large':
                    self.$modal.find('.modal-dialog').addClass('modal-xl');
                    break;
            }
        });
    },
})

options.registry.img_hotspots_slider_actions = options.Class.extend({
    events:{
        'click we-button.add_preview':'_showPreview',
        'change we-range.pos_left':'_setPositionLeft',
        'change we-range.pos_top':'_setPositionRight',
        'click we-select.hs_types':'_setHotspotType',
        'click we-button.add_product':'_setProduct',
        'click .imagebox':'_setImage',
        'click .style_icon':'_setIcon',
        'click .as_hotspot_translation':'_set_hotspot_translation',
    },
    start:function(){
        var leftPanelEl = this.$overlay.data('$optionsSection')[0];
        var titleTextEl = leftPanelEl.querySelector('we-title > span');
        $(titleTextEl).text('Hotspot');
    },
    init: function () {
        this._super.apply(this, arguments);
        this.rpc = this.bindService("rpc");
    },
    _set_hotspot_translation : async function(ev){
        var cr = this;
        var key_data = $(ev.currentTarget).attr("data-key")
        var attributesDictionary = {};
        var attributes = this.$target[0].attributes;
        var attributePrefix = '';
        var defaultDataAttr = '';
        switch (key_data) {
            case "title_translation":
                attributePrefix = 'data-lang-';
                defaultDataAttr = 'data-po_title';
                break;
            case "desc_translation":
                attributePrefix = 'data-description-lang-';
                defaultDataAttr = 'data-po_desc';
                break;
            case "btn_translation":
                attributePrefix = 'data-btn-lang-';
                defaultDataAttr = 'data-po_btxt';
                break;
            default:
                return false;
        }
        for (var i = 0; i < attributes.length; i++) {
            var attributeName = attributes[i].name;
            if (attributeName.startsWith(attributePrefix)) {
                var attributeValue = attributes[i].value;
                attributesDictionary[attributeName] = attributeValue;
            }
        }
        let outputArray = [];
        for (const key in attributesDictionary) {
            outputArray.push([key, attributesDictionary[key]]);
        }
        var DefaultData = this.$target.attr(defaultDataAttr);
        var languages = await loadLanguages(this.orm);
        let lowerCaseLanguages = languages.map(innerArray => innerArray.map(item => item.toLowerCase()));
        const context = {'lang_code_name': lowerCaseLanguages,'defaultTitle' : DefaultData,'defaultAtt' : outputArray,'key_data' : key_data}
        var HotspotTranslation = new AlanWebsiteTranslation(cr, {
            size: 'extra-large',
            title: 'Hotspot Translation',
            $content :$(renderToElement("theme_alan.as_hotspot_tr",{data:context})),
            buttons:[{
                text: _t('Add Translation'),
                classes: 'btn-primary',
                close: true, click: async () => {
                    var languageData = {};
                    $('.o_field_translation_code').each(function(index) {
                        var codeValue = $(this).attr('value');
                        var inputValue = $('.o_field_translation_field').eq(index).val();
                        languageData[codeValue] = inputValue;
                    });
                    var key_data = $(ev.currentTarget).attr("data-key")
                    for (var code in languageData) {
                        if (languageData.hasOwnProperty(code) && languageData[code] !== '') {
                            if (key_data == "title_translation") {
                                this.$target.attr('data-lang-' + code, languageData[code]);
                            }
                            else if (key_data == "desc_translation") {
                                this.$target.attr('data-description-lang-' + code, languageData[code]);
                            }
                            else if (key_data == "btn_translation") {
                                this.$target.attr('data-btn-lang-' + code, languageData[code]);
                            }
                            else{
                                return false
                            }
                        }
                    }
                }
            }]
        })
        HotspotTranslation.open()
    },
    _setPositionLeft:function(ev){
        var posval = $(ev.currentTarget).find("input").val() + "%";
        this.$target.parents(".hotspot").css('left',posval);
    },
    _setPositionRight:function(ev){
        var posval = $(ev.currentTarget).find("input").val() + "%";
        this.$target.parents(".hotspot").css('top',posval);
    },
    _setIcon:function(evt){
        var get_icon_style = $(evt.currentTarget).attr('data-select-data-attribute');
        this.$target.removeClass('st1 st2 st3').addClass(get_icon_style);
    },
    _setImage:function(){
        this.call("dialog", "add", MediaDialog, {
            noImages: false,
            noDocuments: true,
            noVideos: true,
            save: image => {
                let image_url = $(image).attr("src")
                this.$target.attr('data-po_imgurl', image_url);
            },
        });
    },
    _procedureData(rec) {
        rec.forEach(ele => { ele['text'] = ele['name'] });
        return rec;
    },
    _setProduct:function(){
        var self = this;
        let dialog = new Dialog(this, {
            $content:$(renderToElement("theme_alan.s_hotspot_product_selector",{})),
            renderHeader: false,
            renderFooter: false,
            backdrop: true,
        });
        dialog.opened(function(ev){
            let $input = dialog.$el.find("#as_search");
            $input.select2({
                width: "100%",
                placeholder:_t("Search Products..."),
                multiple: true,
                maximumSelectionSize: 1,
                dropdownCssClass: 'as-select2-dropdown',
                initSelection: function (ele, cbf) { },
                ajax: {
                    url: "/select/data/fetch",
                    quietMillis: 100,
                    dataType: 'json',
                    data: function (terms) {
                        return ({ terms:terms, searchIn: JSON.stringify(["product.template"]) });
                    },
                    results: function (rec) {
                        return {
                            results: self._procedureData(rec)
                        };
                    },
                },
                formatResult: function (res) {
                    return $(renderToElement("theme_alan.select2_fetch_info",{data:res}));
                },
                allowClear: true,
            });
             if(self.$target.attr('data-product_tmpl_id') != undefined){
                $input.select2('data', {id:  self.$target.attr('data-product_tmpl_id'), text: self.$target.attr('data-product-name')});
            }
            dialog.$el.find(".as_btn_save").click(function(){
                let select_data = $input.select2('data');
                if(select_data){
                    self.$target.attr('data-product_tmpl_id', $input.val());
                    self.$target.attr('data-product-name', select_data[0].text);
                    dialog.close();
                }
            })
        })
        dialog.open();
    },
    _showPreview:function(){
        var title = this.$target.attr('data-po_title') == undefined ? '':this.$target.attr('data-po_title');
        var description = this.$target.attr('data-po_desc') == undefined ? '':this.$target.attr('data-po_desc');
        var btn_txt = this.$target.attr('data-po_btxt') == undefined ? '':this.$target.attr('data-po_btxt');
        var btn_url = this.$target.attr('data-po_bturl') == undefined ? '':this.$target.attr('data-po_bturl');
        var img_url = this.$target.attr('data-po_imgurl') == undefined ? '' :this.$target.attr('data-po_imgurl');
        var pop_thm = this.$target.attr('data-po_theme') == undefined ? '' :this.$target.attr('data-po_theme');
        var pop_style = this.$target.attr('data-po_style') == undefined ? '' :this.$target.attr('data-po_style');
        var context = { 'title':title,'description':description,'btn_txt':btn_txt,
            'btn_url':btn_url,'img_url':img_url,'pop_thm':pop_thm, 'pop_style':pop_style }

        if(this.$target.attr("data-st_type") == "popover"){
            if(popoverShow === false){
                this.$target.popover({
                    html: true,
                    container: 'body',
                    content:$(renderToElement("theme_alan.s_static_hotspot_popover", {data:context})),
                }).popover('show');
                popoverShow = true;
            }
            else{
                this.$target.popover('dispose');
                popoverShow = false;
            }
        }
        else if(this.$target.attr("data-st_type") == "modal"){
            new Dialog(this, {
                $content:$(renderToElement("theme_alan.s_static_hotspot_popover", {data:context})),
                renderHeader: false,
                renderFooter: false,
                backdrop: true,
            }).open();
        }
    },
    _setHotspotType:function(ev){
        this.$target.popover('dispose');
        if(!this.$target.hasClass('dynamic_type')){
            this.$target.removeClass("as_quick_view");
        }
    },
    cleanForSave:function(){
        this.$target.popover('dispose');
    },
});
