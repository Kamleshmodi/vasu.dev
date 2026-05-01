from django.conf import settings


def seo_context(request):
    return {
        'seo_site_name': getattr(settings, 'SEO_SITE_NAME', 'VASU Store'),
        'seo_default_description': getattr(
            settings,
            'SEO_DEFAULT_DESCRIPTION',
            'VASU is a luxury fashion store for women and men featuring designer collections, secure checkout, and premium support.',
        ),
        'seo_default_og_image': getattr(
            settings,
            'SEO_DEFAULT_OG_IMAGE',
            '/static/image/logo/logo-transparent.png',
        ),
        'google_site_verification': getattr(settings, 'GOOGLE_SITE_VERIFICATION', '').strip(),
        'bing_site_verification': getattr(settings, 'BING_SITE_VERIFICATION', '').strip(),
        'analytics_tracking_enabled': getattr(settings, 'ANALYTICS_TRACKING_ENABLED', True),
    }
