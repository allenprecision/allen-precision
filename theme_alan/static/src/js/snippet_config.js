/** @odoo-module **/

import { SnippetBuilder } from 'theme_alan.SnippetBuilder';
import snippetsEditor from "@web_editor/js/editor/snippets.editor";
import options from "@web_editor/js/editor/snippets.options";
import Dialog from '@web/legacy/js/core/dialog';
import { _t } from '@web/core/l10n/translation';
import { registry } from "@web/core/registry";

snippetsEditor.SnippetsMenu.include({
    _onSaveRequest: function (ev) {
        let static_snippet_list = ['MegaMenuContent', 'StaticSnippet'];
        let $snippet_list = this.$body.find(".as-grid");
        for (let snippet of $snippet_list) {
           if(!static_snippet_list.includes($(snippet).attr("data-snippet-name"))){
                $(snippet).empty();
           }
        }
        this._super.apply(this, arguments);
    }
})

options.registry.as_snippet_configure = options.Class.extend({
    xmlDependencies: ["/theme_alan/static/src/xml/templates.xml"],
    start:function(){
        /** Call configuration method on first time and on click */
        this._super.apply(this, arguments);
        this._openSnippetConfigure();
        this.$target.click(() => {this._openSnippetConfigure()});
    },
    _openSnippetConfigure: function (ev) {
        /** Fetch snippet detail and open configure dialog */
        if (!this.snippetProcessing) {
            var snippet_type = this.$target.attr("data-as-snippet");
            if (snippet_type == undefined) {
                if (this.$target.hasClass("as_mega_menu")) {
                    snippet_type = "as_mega_menu";
                }
            }
            const snippet_list = registry.category("as_snippet_registry").get(snippet_type);
            const is_static = this.$target.hasClass("as_static_menu");
            if (!is_static) {
                if (snippet_type == "as_mega_menu") {
                    let data = { 'title': 'Megamenu Configuration', 'size': 'as-full-screen', 'snippet_list': snippet_list, 'snippet_origin': this }
                    this.call("dialog", "add", SnippetBuilder, data);
                    // dialog.mount(this.el);
                } else if (snippet_type == "as_dynamic_snippets") {
                    let data = { 'title': 'Alan Snippet Configuration', 'size': 'as-full-screen', 'snippet_list': snippet_list, 'snippet_origin': this }
                    this.call("dialog", "add", SnippetBuilder, data);
                    // dialog.mount(this.el);
                }
            }
        }
    },
});

options.registry.hero_builder = options.Class.extend({
    events:{
        'click .add_slide':'_addSlide',
    },
    _addSlide:function(){
        var $container = this.$target.find(".swiper-wrapper");
        let slider = '<section class="active oe_img_bg o_bg_img_center pt240 pb240 swiper-slide" style="background-image: url('+ '/theme_alan/static/src/img/snippets/1920x800.jpg' + ');" data-name="Slide">\
                <div class="container">\
                    <div class="row content justify-content-center">\
                        <div class="col-lg-10 s_col_no_bgcolor carousel-content">\
                            <div class="text-center">\
                                <div class="display-3 h1 fw-600 mb-3">Spread the holiday sparkle</div>\
                                <div class="display-3 h1 fw-600 mb-3">With 30%off sitewide!</div>\
                                <div class="btn-bar pt-2">\
                                    <a class="btn btn-primary o_default_snippet_text m-2" href="#">Shop Now</a>\
                                </div>\
                            </div>\
                        </div>\
                    </div>\
                </div>\
            </section>'
        $(slider).appendTo($container);
    }
})
