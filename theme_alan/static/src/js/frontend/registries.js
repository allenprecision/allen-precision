/** @odoo-module **/

import { registry } from '@web/core/registry';

const as_snippet_registry = registry.category("as_snippet_registry");

let m_product = {
          'component': 'MegaMenuProduct',
          'name': 'Product Menu',
          'description': 'Create the Product Menu with grid and slider view with different styles.',
          'icon':'/theme_alan/static/src/img/icons/product-menu.svg'
        }
let m_category = {
          'component': 'MegaMenuCategory',
          'name': 'Category Menu',
          'description': 'Create the Category menu with grid and slider view with different styles.',
          'icon':'/theme_alan/static/src/img/icons/category-menu.svg'
        }
let m_brand = {
            'component': 'MegaMenuBrand',
            'name': 'Brand Menu',
            'description': 'Create the Brand menu with grid and slider view with different styles.',
            'icon':'/theme_alan/static/src/img/icons/brand-menu.svg'
        }
let m_static = {
            'component': 'MegaMenuContent',
            'name': 'Static Menu',
            'description': 'Add the static content and edit it with odoo editor.',
            'icon':'/theme_alan/static/src/img/icons/static-menu.svg'
        }

as_snippet_registry.add("as_mega_menu", { snippets : [ m_product , m_category, m_brand, m_static ] });

let static_snippet = {
        'component': 'StaticSnippet',
        'name': 'Static Snippet',
        'description': 'Add the static content and edit it with odoo editor.',
        'icon':'/theme_alan/static/src/img/icons/static-menu.svg'
    }

let product_slider = {
        'component': 'ProductSlider',
        'name': 'Product Selector',
        'description': 'Amazing product selector snippet comes with awesome design',
        'icon':'/theme_alan/static/src/img/icons/product-menu.svg'
}

let best_selling_product = {
        'component': 'BestSellingProduct',
        'name': 'Best Selling Products',
        'description': 'Best snippet to show best selling product with awesome design',
        'icon':'/theme_alan/static/src/img/icons/best-selling.svg'
}

let latest_product = {
        'component': 'LatestProduct',
        'name': 'Latest Products',
        'description': 'Latest product snippet helps to display latest product with awesome design',
        'icon':'/theme_alan/static/src/img/icons/latest-product.svg'
}

let brand_droduct = {
        'component': 'BrandProduct',
        'name': 'Brand Products',
        'description': 'Shows brand wise product with awesome design.',
        'icon':'/theme_alan/static/src/img/icons/brand-product.svg'
}
let category_product = {
        'component': 'CategoryProduct',
        'name': 'Category Products',
        'description': 'Shows category wise product with awesome design.',
        'icon':'/theme_alan/static/src/img/icons/category-product.svg'
}

let product_banner = {
        'component': 'ProductBanner',
        'name': 'Product Banner',
        'description': 'Create amazing product banners with our banner snippet.',
        'icon':'/theme_alan/static/src/img/icons/product-banner.svg'
}

let category_slider = {
        'component': 'CategorySlider',
        'name': 'Category',
        'description': 'Category snippet helps you to display categories with amazing styles',
        'icon':'/theme_alan/static/src/img/icons/category-menu.svg'
}

let brand_slider = {
        'component': 'BrandSlider',
        'name': 'Brands',
        'description': 'Brand snippet helps you to display brand with amazing styles',
        'icon':'/theme_alan/static/src/img/icons/brand-menu.svg'
}

let blog_slider = {
        'component': 'BlogSlider',
        'name': 'Blogs',
        'description': 'Blog snippet helps you to display blog with amazing styles',
        'icon':'/theme_alan/static/src/img/icons/blogs.svg'
}

as_snippet_registry.add("as_dynamic_snippets", { snippets : [
        product_slider, category_product, best_selling_product, brand_slider, latest_product, brand_droduct,
        category_slider, blog_slider, product_banner, static_snippet
] });


let as_static_snippets = [
        {
            'list':[
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-1.png',
                    'name':'Snippet 1',
                    'temp_id':'slider_temp_1'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-2.png',
                    'name':'Snippet 2',
                    'temp_id':'slider_temp_2'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-3.png',
                    'name':'Snippet 3',
                    'temp_id':'slider_temp_3'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-4.png',
                    'name':'Snippet 4',
                    'temp_id':'slider_temp_4'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-5.jpg',
                    'name':'Snippet 5',
                    'temp_id':'slider_temp_5'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-6.png',
                    'name':'Snippet 6',
                    'temp_id':'slider_temp_6'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-7.jpg',
                    'name':'Snippet 7',
                    'temp_id':'slider_temp_7'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-8.png',
                    'name':'Snippet 8',
                    'temp_id':'slider_temp_8'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-9.png',
                    'name':'Snippet 9',
                    'temp_id':'slider_temp_9'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-10.png',
                    'name':'Snippet 10',
                    'temp_id':'slider_temp_10'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-11.png',
                    'name':'Snippet 11',
                    'temp_id':'slider_temp_11'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-12.png',
                    'name':'Snippet 12',
                    'temp_id':'slider_temp_12'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-13.png',
                    'name':'Snippet 13',
                    'temp_id':'slider_temp_13'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-14.png',
                    'name':'Snippet 14',
                    'temp_id':'slider_temp_14'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-15.jpg',
                    'name':'Snippet 15',
                    'temp_id':'slider_temp_15'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-16.png',
                    'name':'Snippet 16',
                    'temp_id':'slider_temp_16'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-17.jpg',
                    'name':'Snippet 17',
                    'temp_id':'slider_temp_17'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-18.png',
                    'name':'Snippet 18',
                    'temp_id':'slider_temp_18'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-19.png',
                    'name':'Snippet 19',
                    'temp_id':'slider_temp_19'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-20.png',
                    'name':'Snippet 20',
                    'temp_id':'slider_temp_20'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-21.png',
                    'name':'Snippet 21',
                    'temp_id':'slider_temp_21'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-22.jpg',
                    'name':'Snippet 22',
                    'temp_id':'slider_temp_22'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-23.png',
                    'name':'Snippet 23',
                    'temp_id':'slider_temp_23'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-24.png',
                    'name':'Snippet 24',
                    'temp_id':'slider_temp_24'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-25.png',
                    'name':'Snippet 25',
                    'temp_id':'slider_temp_25'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-26.png',
                    'name':'Snippet 26',
                    'temp_id':'slider_temp_26'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-27.png',
                    'name':'Snippet 27',
                    'temp_id':'slider_temp_27'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-28.png',
                    'name':'Snippet 28',
                    'temp_id':'slider_temp_28'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-29.png',
                    'name':'Snippet 29',
                    'temp_id':'slider_temp_29'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-30.png',
                    'name':'Snippet 30',
                    'temp_id':'slider_temp_30'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-31.png',
                    'name':'Snippet 31',
                    'temp_id':'slider_temp_31'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-32.png',
                    'name':'Snippet 32',
                    'temp_id':'slider_temp_32'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-33.png',
                    'name':'Snippet 33',
                    'temp_id':'slider_temp_33'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-34.png',
                    'name':'Snippet 34',
                    'temp_id':'slider_temp_34'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-35.png',
                    'name':'Snippet 35',
                    'temp_id':'slider_temp_35'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-36.png',
                    'name':'Snippet 36',
                    'temp_id':'slider_temp_36'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-37.png',
                    'name':'Snippet 37',
                    'temp_id':'slider_temp_37'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-38.png',
                    'name':'Snippet 38',
                    'temp_id':'slider_temp_38'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-39.png',
                    'name':'Snippet 39',
                    'temp_id':'slider_temp_39'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-40.png',
                    'name':'Snippet 40',
                    'temp_id':'slider_temp_40'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-41.png',
                    'name':'Snippet 41',
                    'temp_id':'slider_temp_41'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-42.png',
                    'name':'Snippet 42',
                    'temp_id':'slider_temp_42'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-43.png',
                    'name':'Snippet 43',
                    'temp_id':'slider_temp_43'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-44.png',
                    'name':'Snippet 44',
                    'temp_id':'slider_temp_44'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-45.png',
                    'name':'Snippet 45',
                    'temp_id':'slider_temp_45'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-46.png',
                    'name':'Snippet 46',
                    'temp_id':'slider_temp_46'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-47.png',
                    'name':'Snippet 47',
                    'temp_id':'slider_temp_47'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-48.png',
                    'name':'Snippet 48',
                    'temp_id':'slider_temp_48'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-49.png',
                    'name':'Snippet 49',
                    'temp_id':'slider_temp_49'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-50.png',
                    'name':'Snippet 50',
                    'temp_id':'slider_temp_50'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-51.png',
                    'name':'Snippet 51',
                    'temp_id':'slider_temp_51'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-52.png',
                    'name':'Snippet 52',
                    'temp_id':'slider_temp_52'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-53.png',
                    'name':'Snippet 53',
                    'temp_id':'slider_temp_53'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-54.png',
                    'name':'Snippet 54',
                    'temp_id':'slider_temp_54'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-55.png',
                    'name':'Title Style 1',
                    'temp_id':'banner_temp_1'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-56.png',
                    'name':'Title Style 2',
                    'temp_id':'banner_temp_2'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-57.png',
                    'name':'Title Style 3',
                    'temp_id':'banner_temp_3'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-58.png',
                    'name':'Title Style 4',
                    'temp_id':'banner_temp_4'
                },
                {
                    'img_url':'/theme_alan/static/src/img/snippets/dynamic_snippets/dy_snippet-59.png',
                    'name':'Title Style 5',
                    'temp_id':'banner_temp_5'
                },
            ]
        },

    ]

as_snippet_registry.add("as_static_snippets", as_static_snippets);