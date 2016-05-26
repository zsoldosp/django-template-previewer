import json
from django.core.urlresolvers import reverse
from django.test import TransactionTestCase, Client


class RegressionTestCase(TransactionTestCase):

    def test_can_load_main_page(self):
        url = reverse('preview')
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

    def test_can_load_parse_page_for_doc_sample_template(self):
        data = self.parse_template('sample.html')
        self.assertEqual([
                {u'name': u'title', u'children': [] },
                {
                    u'name': u'foo', u'children': [
                        {
                            u'name': u'bar', u'children': [
                            {u'name': u'0', u'children': [
                                {u'name': u'last_name', u'children': []},
                                {u'name': u'first_name', u'children': []},
                            ]},
                        ]},
                    ]
                },
            ], data)

    def test_can_parse_url_nodes_in_templates(self):
        data = self.parse_template('url.html')
        self.assertEqual([{u'children': [], u'name': u'parse_link_text'}], data)

    def test_can_parse_translations_with_vars(self):
        # TODO: {% trans "This is the title" as the_title %}<h1>{{ the_title }}</h1>

        data = self.parse_template('translation.html')
        self.assertEqual([{u'children': [], u'name': u'var_to_translate'}, {u'children': [], u'name': u'first_name'}], data)

    def test_can_render_preview_for_a_given_template(self):
        response = self.render_preview(template='url.html', context=dict(parse_link_text=('parse link text', {})))
        self.assertEqual(200, response.status_code)
        self.assertEquals('<a href="/_preview/parse/">parse link text</a>', response.content.strip())

    def test_handling_hidden_context_usage_in_custom_template_tags(self):
        template = 'hidden_context_use_via_template_tags.html'
        data = self.parse_template(template)
        expected = [
            { u'name': u'foo', u'children': [] },
            { u'name': u'bar', u'children': [
                    { u'name': u'baz', u'children': [] }
                ] },
        ]
        self.assertEqual(expected, data)
        response = self.render_preview(
            template=template, context=dict(
                foo=('foo', {}),
                bar=('bar', dict(
                    baz=('baz', {}),
                )),
            )
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual('foo\nbaz', response.content.strip())

    def test_should_only_pick_up_variables_not_constants_from_conditionals(self):
        template = 'conditionals.html'
        data = self.parse_template(template)
        expected = [
            { u'name': u'myvar', u'children': [] },
        ]
        self.assertEqual(expected, data)

        response = self.render_preview(
            template=template, context=dict(myvar=('0', {}))
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual('zero', response.content.strip())

        response = self.render_preview(
            template=template, context=dict(myvar=('1', {}))
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual('nonzero', response.content.strip())

    def test_should_ignore_variables_in_comments(self):
        template = 'comments.html'
        data = self.parse_template(template)
        self.assertEqual([], data)

        response = self.render_preview(
            template=template, context=dict()
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual('', response.content.strip())


    def render_preview(self, template, context):
        """
        context is of form
        {
          'attr_name': (val, <child context>)
        }
        """
        url = reverse('render')
        def context2payload(context):
            data = {}
            for name, (val, child) in context.items():
                data[name] = dict(_str=val)
                for child_name, (child_val, child_context) in child.items():
                    data[name][child_name] = context2payload(child_context)
                    data[name][child_name]['_str'] = child_val
            return data

        payload = dict(
            template=template,
            context=json.dumps(context2payload(context)),
        )
        return self.client.post(url, payload)

    def parse_template(self, template_name):
        url = reverse('parse') + '?template=%s' % template_name
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content)
        self.maxDiff = None
        return data
