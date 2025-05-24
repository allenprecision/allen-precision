/** @odoo-module */
import publicWidget from '@web/legacy/js/public/public_widget';
import { registry } from '@web/core/registry';
import { _t } from "@web/core/l10n/translation";
//import wSaleUtils from "@website_sale/js/website_sale_utils";

publicWidget.registry.WebsiteSale.include({
    _onClickSubmit: function (ev, forceSubmit){
            var data = [];
            if ($('div.p_variant').length > 0){
                $('div.p_variant').each(function(ev) {
                    var dict = {};
                    var $this = $(this);
                    var product_id = parseInt($this.find('input[name="combo_product_id"]').val(), 10);
                    var add_qty = parseInt($this.find('input[name="add_qty"]').val(), 10);

                    if (!isNaN(add_qty) && add_qty != 0) {
                        dict["product_id"] = product_id;
                        dict["add_qty"] = add_qty;
                        data.push(dict);
                    }
                });
                if (data.length > 0) {
                    this.rpc("/shop/cart/update/multi/variant", {
                        'data': data
                    }).then(function(result) {
                        window.location.href = window.location.origin + result['redirect_url'];
                    });
                } else {
                    $("#grpError").show().delay('3000').fadeOut();
                    return false;
                }
            }
            else {
                this._super.apply(this, arguments);
            }
        },

    _onClickAdd: function (ev, forceSubmit){
            var data = [];
            if ($('div.p_variant').length > 0){
                $('div.p_variant').each(function(ev) {
                    var dict = {};
                    var $this = $(this);
                    var product_id = parseInt($this.find('input[name="combo_product_id"]').val(), 10);
                    var add_qty = parseInt($this.find('input[name="add_qty"]').val(), 10);

                    if (!isNaN(add_qty) && add_qty != 0) {
                        dict["product_id"] = product_id;
                        dict["add_qty"] = add_qty;
                        data.push(dict);
                    }
                });
                if (data.length > 0) {
                    this.rpc("/shop/cart/update/multi/variant", {
                        'data': data
                    }).then(function(result) {
                        window.location.href = window.location.origin + result['redirect_url'];
                    });
                } else {
                    $("#grpError").show().delay('3000').fadeOut();
                    return false;
                }
            }
            else {
                this._super.apply(this, arguments);
            }
        },

});
export default publicWidget.registry.WebsiteSale;

$(document).ready(function() {
        if ($("div.hide-product_price").length){
            $("div.hide-product_price").each(function() {
              if($(this).parents('div.cs_group_table').length == 0){
                $(this).children('h3.css_editable_mode_hidden ').hide();
                $(this).find('span[itemprop="price"]').hide();
              }
            });
        }
    });

