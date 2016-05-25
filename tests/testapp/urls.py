from django.conf.urls import patterns, url, include


urlpatterns = patterns('',
    url(r'^_preview/', include('template_previewer.urls')),
)
