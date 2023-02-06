odoo.define('atharva_theme_base.s_img_hotspots', function (require) {
"use strict";

var publicWidget = require('web.public.widget');
var Common_dialog = require('theme_alan.common_modal');
const { BaseAlanQweb } = require("theme_alan.core_mixins");
const webUtils = require('web.utils');
var alanLazy = require("atharva_theme_base.lazy_loader");

publicWidget.registry.img_hotspot = alanLazy.extend(BaseAlanQweb,{
    selector:'#wrapwrap',
    disabledInEditableMode: false,
    xmlDependencies: ['/theme_alan/static/src/xml/snippets/hotspot_modal.xml'],
    events:{
        'click a.icon':'_addThemeStyle'
    },
    _addThemeStyle:function(ev){
        if (!this.editableMode){
            var getUserData = $(ev.currentTarget).attr('data-content');
            if(getUserData != ""){
                if($(getUserData).attr('class')  != undefined){
                    var getclass = $(getUserData).attr('class').split(' ');
                    getclass.shift();
                    getclass = getclass.join(" ");
                    var popTemp = '<div class="popover as-hotspot-popover '+ getclass + '" style="position: absolute; transform: translate3d(675px, 153px, 0px); top: 0px; left: 0px; will-change: transform;">\
                        <div class="arrow" style="top: 43px;"></div>\
                        <h3 class="popover-header"></h3>\
                        <div class="popover-body">\
                        </div>\
                        </div>';
                    $(ev.currentTarget).popover({
                            container: '#wrap',
                            template:popTemp
                    });
                    if($(ev.currentTarget).attr('aria-describedby') == undefined){
                        $(ev.currentTarget).trigger('click');
                    };
                }
            } else {
                let cr = $(ev.currentTarget).parent();
                var title = cr.attr('data-po_title') == undefined ? '':cr.attr('data-po_title');
                var description = cr.attr('data-po_desc') == undefined ? '':cr.attr('data-po_desc');
                var btn_txt = cr.attr('data-po_btxt') == undefined ? '':cr.attr('data-po_btxt');
                var btn_url = cr.attr('data-po_bturl') == undefined ? '':cr.attr('data-po_bturl');
                var img_url = cr.attr('data-po_imgurl') == undefined ? '' :cr.attr('data-po_imgurl');
                var pop_thm = cr.attr('data-po_theme') == undefined ? '' :cr.attr('data-po_theme');
                var pop_style = cr.attr('data-po_style') == undefined ? '' :cr.attr('data-po_style');
                var style_cls = pop_thm + " " + pop_style;
                var context = {'title':title,'description':description,'btn_txt':btn_txt,'btn_url':btn_url,'img_url':img_url ,'theme':style_cls}

                var common_dialog = new Common_dialog(cr,{
                    size: 'medium',
                    subTemplate: webUtils.Markup($(this._baseAlanQweb("theme_alan.hotspot_static_modal", context)).html()),
                });
                common_dialog.open();
            }
        }

    },
    start: function (editable_mode) {
        var self = this;
        if (!self.editableMode){
            var getDyanmicHs = self.$target.find('p.dynamic_type');
            $.each(getDyanmicHs, function (index, eachDOM) {
                var gettype = $(eachDOM).attr('data-dy_type');
                var prod_id  = $(eachDOM).attr('data-product-id');
                if(gettype == "popover"){
                    var po_style = $(eachDOM).attr('data-po_style');
                    $(eachDOM).children().removeClass("as-quick-view").removeAttr('data-product-id',prod_id);
                    self._rpc({
                        route: '/get/product_popover',
                        params: {'id':prod_id,
                                 'popstyle':po_style,
                                 'popover':true
                                }
                    }).then(function (result) {
                        $(eachDOM).children().attr('data-toggle','popover').attr('data-html',true).attr('data-content',result);
                    });
                }
                else{
                    $(eachDOM).children().removeAttr('data-toggle').removeAttr('data-html').removeAttr('data-content')
                    .attr('data-product-id',prod_id);
                    $(eachDOM).children().addClass("as-quick-view");
                }
            });
            var getStaticHs = self.$target.find('p.static_type');
            $.each(getStaticHs, function (index, eachDOM) {
                var title = $(eachDOM).attr('data-po_title') == undefined ? 'Title':$(eachDOM).attr('data-po_title');
                var description = $(eachDOM).attr('data-po_desc') == undefined ? 'description':$(eachDOM).attr('data-po_desc');
                var btn_txt = $(eachDOM).attr('data-po_btxt') == undefined ? 'text':$(eachDOM).attr('data-po_btxt');
                var btn_url = $(eachDOM).attr('data-po_bturl') == undefined ? '/':$(eachDOM).attr('data-po_bturl');
                var img_url = $(eachDOM).attr('data-po_imgurl') == undefined ? '/theme_alan/static/src/img/snippets/image.png' :$(eachDOM).attr('data-po_imgurl');
                var pop_thm = $(eachDOM).attr('data-po_theme') == undefined ? '' :$(eachDOM).attr('data-po_theme');
                var pop_style = $(eachDOM).attr('data-po_style') == undefined ? '' :$(eachDOM).attr('data-po_style');
                var style_cls = pop_thm + " " + pop_style;
                var pop_type = $(eachDOM).attr('data-st_type') == undefined ? '' :$(eachDOM).attr('data-st_type');
                if (pop_type == "popover"){
                    var popoverhtm = "<div class='hp-media "+ style_cls +"'>\<div class='hp-img'><img src='"+img_url+"' alt='Image'></div>\<div class='hp-media-body'>\<h5 class='hp-title'>"+ title +"</h5><p>"+description+"</p><a href='"+btn_url+"' class='as-btn as-btn-theme btn-sm'>"+ btn_txt +"</a></div></div>";
                } else {
                    var popoverhtm = ""
                }
                $(eachDOM).children().attr('data-content',popoverhtm);
            });
        }
        else{
            var getDyanmicHs = self.$target.find('p.dynamic_type');
            $.each(getDyanmicHs, function (index, eachDOM) {
                $(eachDOM).children().removeClass("as-quick-view");
            });
        }
    }
});
});
