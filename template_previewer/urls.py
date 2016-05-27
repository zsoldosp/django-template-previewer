from django.conf.urls import url
from template_previewer.views import preview, parse, render

urlpatterns = [
    url(r'^$', preview, name='preview'),
    url(r'^parse/$', parse, name='parse'),
    url(r'^render/$', render, name='render'),
]
