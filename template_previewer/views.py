import json

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_GET
from django.template.response import TemplateResponse
from django.core.urlresolvers import reverse
from django.template import Template, loader, TemplateDoesNotExist
from django.utils.encoding import force_text

from template_previewer.forms import RenderForm, ParseForm
from template_previewer.template_parser.context import get_context

class ContextItem(object):
    def __init__(self, context_dict):
        self._context_dict = context_dict
        self._str = context_dict.pop("_str", "")
        self._len = 0
        while str(self._len) in context_dict:
            self._len += 1
        self._islist = self._len > 0

    def __str__(self):
        return force_text(s=self._str, encoding='utf-8')

    def __unicode__(self):
        return self._str

    def __bool__(self):
        if self.__nonzero__():
            return True
        return False

    def __nonzero__(self):
        if self._str or self._context_dict:
            return True
        return False

    def __getitem__(self, key):
        if isinstance(key, int):
            key = str(key)
        raw = self._context_dict[key]
        return self._typed_val(raw)

    def _typed_val(self, raw):
        # TODO: this is ugly. But we need this 'coz otherwise conditionals don't work correctly, e.g.: if foo, if foo == 1, etc.
        str_raw = str(raw)
        for conv_fn in (long, float):
            try:
                _typed = conv_fn(str_raw)
            except (TypeError, ValueError):
                continue
            if str(_typed) == str_raw:
                return _typed
        return raw

    def __getattr__(self, name):
        return self[name]

    def __iter__(self):
        if self._islist:
            return (self[str(x)] for x in range(self._len))
        else:
            return iter(self._context_dict)

    def __len__(self):
        return len(self._context_dict)

    def __int__(self):
        return int(self._str)

    def __float__(self):
        return float(self._str)


@require_POST
def render(request):
    """This is the actually preview, rendered on an <iframe>"""
    form = RenderForm(request.POST)
    if form.is_valid():
        template_name = form.cleaned_data['template']
        template = loader.get_template(template_name)
        context = json.loads(s=form.cleaned_data['context'], encoding='utf-8', object_hook=ContextItem)
        return HttpResponse(template.render(context))
    else:
        return HttpResponseBadRequest()

# The following are auxiliar functions to help making the tree out of the 
# parsed context in the template

def _make_node(name):
    return {
        "name": name,
        "children": []
    }

def _lookup(childlist, name):
    for child in childlist:
        if child["name"] == name: return child
    new = _make_node(name)
    childlist.append(new)
    return new

def _extend(childlist, path):
    path_items = path.split('.')
    for p in path_items:
        childlist = _lookup(childlist, p)["children"]

@require_GET
def parse(request):
    """
    This is an AJAX utility to get the needed context variables given a
    template name
    """
    form = ParseForm(request.GET)
    if form.is_valid():
        template_name = form.cleaned_data['template']
        try:
            template = loader.get_template(template_name)
        except TemplateDoesNotExist:
            return HttpResponse(json.dumps({"error": u"Could not load template '%s'" % template_name}), content_type="application/json")
        tree = []
        for path in get_context(template):
            _extend(tree, path)
        return HttpResponse(json.dumps(tree), content_type="application/json")
    else:
        return HttpResponse(json.dumps({"error": unicode(form.errors)}), content_type="application/json")

def preview(request):
    """
    This is the view where the user can select rendering parameters (i.e.
    template+context)
    """
    form = RenderForm()
    ctx = {
        "form": form,
        "parse_url": reverse(parse),
        "render_url": reverse(render),
    }
    return TemplateResponse(
        request,
        "template_previewer/preview.html",
        ctx
    )

