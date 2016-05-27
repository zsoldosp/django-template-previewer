from django.conf.urls import url, include


urlpatterns = [
    url(r'^_preview/', include('template_previewer.urls')),
]
