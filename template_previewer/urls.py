from django.conf.urls import patterns, url

urlpatterns = patterns('template_previewer.views',
    url(r'^$', 'preview', name='preview'),
    url(r'^parse/$', 'parse', name='parse'),
    url(r'^render/$', 'render', name='render'),
)
