# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
  "name"                 :  "Shipping Per Product",
  "summary"              :  """Shipping per product module allows customer to select delivery method for each product separately and delivery amount will be calculated for each product.""",
  "category"             :  "Website",
  "version"              :  "1.1.5",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/Odoo-Shipping-Per-Product.html",
  "description"          :  """Odoo Shipping Per Product
per-item shipping
Odoo Per product shipping
per -product shipping
Odoo Per-item shipping rates
Shipping by item odoo
delivery method for each product
separate delivery
shipping individual product""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=shipping_per_product&custom_url=/shop",
  "depends"              :  ['website_sale_delivery'],
  "data"                 :  [
                             'data/demo_sale_order.xml',
                             'views/inherit_delivery_view.xml',
                             'views/inherit_product_view.xml',
                             'views/inherit_sale_view.xml',
                             'views/inherit_sol_template.xml',
                             'wizard/choose_delivery_carrier_views.xml',
                            ],
  "images"               :  ['static/description/Banner.gif'],
  "application"          :  True,
  "installable"          :  True,
  'assets': {
        'web.assets_frontend': [
            'shipping_per_product/static/src/**/*',
        ],
    },
  "auto_install"         :  False,
  "price"                :  75,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}
