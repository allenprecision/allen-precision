odoo.define('website_grouped_product.product_add_to_bulk_cart', function(require) {
    "use strict";

    var sAnimations = require('website.content.snippets.animation');
    var core = require('web.core');
    var QWeb = core.qweb;
    var ajax = require('web.ajax');
    var utils = require('web.utils');
    var _t = core._t;
    var publicWidget = require('web.public.widget');
    var rpc = require('web.rpc');
    require('website_sale.website_sale');

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
                    ajax.jsonRpc("/shop/cart/update/multi/variant", 'call', {
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

    publicWidget.registry.WebsiteSale.include({
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
                    ajax.jsonRpc("/shop/cart/update/multi/variant", 'call', {
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
});