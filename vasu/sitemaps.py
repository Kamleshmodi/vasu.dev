from django.urls import reverse
from django.contrib.sitemaps import Sitemap

from appmens.models import NewProduct as MenProduct
from appwomens.models import NewProduct as WomenProduct


class StaticViewSitemap(Sitemap):
    protocol = 'https'
    changefreq = 'daily'
    priority = 0.7

    def items(self):
        return [
            'home',
            'womens_home',
            'mens_home',
            'womens_new',
            'mens_new',
            'womens_sale',
            'mens_sale',
            'privacy_policy',
            'terms_of_service',
            'cookie_policy',
            'need_help',
        ]

    def location(self, item):
        return reverse(item)


class WomenProductSitemap(Sitemap):
    protocol = 'https'
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return WomenProduct.objects.filter(is_available=True).order_by('-modified_date')

    def lastmod(self, item):
        return item.modified_date

    def location(self, item):
        return reverse('product_detail', args=[item.slug])


class MenProductSitemap(Sitemap):
    protocol = 'https'
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return MenProduct.objects.filter(is_available=True).order_by('-modified_date')

    def lastmod(self, item):
        return item.modified_date

    def location(self, item):
        return reverse('product_detail_men', args=[item.slug])


sitemaps = {
    'static': StaticViewSitemap,
    'women-products': WomenProductSitemap,
    'men-products': MenProductSitemap,
}
