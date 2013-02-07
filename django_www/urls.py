from __future__ import absolute_import

from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.flatpages.views import flatpage
from django.contrib.sitemaps import views as sitemap_views
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import RedirectView, TemplateView

from accounts import views as account_views
from aggregator.feeds import CommunityAggregatorFeed, CommunityAggregatorFirehoseFeed
from blog.feeds import WeblogEntryFeed
from django_website.sitemaps import FlatPageSitemap, WeblogSitemap

admin.autodiscover()

sitemaps = {
    'weblog': WeblogSitemap,
    'flatpages': FlatPageSitemap,
}

handler500 = 'django_website.views.server_error'


urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='homepage.html'), name="homepage"),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^community/', include('aggregator.urls')),
    url(r'^contact/', include('contact.urls')),
    url(r'^r/', include('django.conf.urls.shortcut')),

    # There's no school like the old school.
    url(r'^~(?P<username>[\w-]+)/$', account_views.user_profile, name='user_profile'),

    # Feeds
    url(r'^rss/weblog/$', WeblogEntryFeed(), name='weblog-feed'),
    url(r'^rss/community/$', RedirectView.as_view(url='/rss/community/blogs/')),
    url(r'^rss/community/firehose/$', CommunityAggregatorFirehoseFeed(), name='aggregator-firehose-feed'),
    url(r'^rss/community/(?P<slug>[\w-]+)/$', CommunityAggregatorFeed(), name='aggregator-feed'),

    # PayPal insists on POSTing to the "thank you" page which means we can't
    # just use a flatpage for it.
    url(r'^foundation/donate/thanks/$', csrf_exempt(TemplateView.as_view(template_name='donate_thanks.html'))),

    # django-push
    url(r'^subscriber/', include('django_push.subscriber.urls')),

    url(r'^sitemap\.xml$', cache_page(sitemap_views.sitemap, 60 * 60 * 6), {'sitemaps': sitemaps}),
    url(r'^weblog/', include('blog.urls')),
    url(r'^download$', flatpage, {'url': 'download'}, name="download"),
    url(r'^svntogit/', include('svntogit.urls')),
    url(r'', include('legacy.urls')),
)
