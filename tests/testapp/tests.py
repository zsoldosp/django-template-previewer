import json
from django.core.urlresolvers import reverse
from django.test import TransactionTestCase, Client

class Helpers(object):

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
        data = json.loads(response.content.decode('utf-8'))
        self.maxDiff = None
        return data

    def get_stripped_response_content(self, response):
        return response.content.decode('utf-8').strip()


class RegressionTestCase(Helpers, TransactionTestCase):

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
        self.assertEquals('<a href="/_preview/parse/">parse link text</a>', self.get_stripped_response_content(response))

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
        self.assertEqual('foo\nbaz', self.get_stripped_response_content(response))

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
        self.assertEqual('zero', self.get_stripped_response_content(response))

        response = self.render_preview(
            template=template, context=dict(myvar=('1', {}))
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual('nonzero', self.get_stripped_response_content(response))

    def test_coniditionals_can_use_pytohnic_if_object(self):
        template = 'if-unary-condition.html'
        data = self.parse_template(template)
        expected = [
            { u'name': u'somevar', u'children': [] },
        ]
        self.assertEqual(expected, data)

        response = self.render_preview(
            template=template, context=dict(somevar=('sdf', {}))
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual('something', self.get_stripped_response_content(response))

        response = self.render_preview(
            template=template, context=dict(somevar=('', {}))
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual('nothing', self.get_stripped_response_content(response))

    def test_should_ignore_variables_in_comments(self):
        template = 'comments.html'
        data = self.parse_template(template)
        self.assertEqual([], data)

        response = self.render_preview(
            template=template, context=dict()
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual('', self.get_stripped_response_content(response))

    def test_should_only_report_loops_collection_var(self):
        template = 'loops.html'
        data = self.parse_template(template)
        expected = [
            {u'name': u'items', u'children': [
                    { u'name': u'0', u'children': [
                        { u'name': u'sku', u'children': [] }
                    ]}]
            }]
        self.assertEqual(expected, data)

        response = self.render_preview(
            template=template, context=dict(
                items=('', {
                    '0': ('', dict(
                        sku=('1234', {}),
                    )),
                    '1': ('', dict(
                        sku=('5678', {}),
                    )),
                })
            )
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual('SKU: 1234\n\nSKU: 5678', self.get_stripped_response_content(response))

    def test_putting_a_loop_inside_a_block_shouldnt_change_var_collection(self):
        template = 'loop-inside-block.html'
        data = self.parse_template(template)
        expected = [
            {u'name': u'items', u'children': [
                    { u'name': u'0', u'children': [
                        { u'name': u'sku', u'children': [] }
                    ]}]
            }]
        self.assertEqual(expected, data)


    def test_can_parse_single_variable_template(self):
        self.assertEqual(
            [
                    { u'name': u'item', u'children': [
                        { u'name': u'sku', u'children': [] }
                    ] }],
            self.parse_template('includes-repeat.html')
        )

    def test_included_templates_variables_are_parsed_too(self):
        expected = [
            { u'name': u'item', u'children': [
                { u'name': u'sku', u'children': [] }
                ]
            }
        ]
        self.assertEqual(expected, self.parse_template('include-single.html'))

    def test_include_should_not_duplicate_variables_for_include(self):
        template = 'includes-main.html'
        data = self.parse_template(template)
        expected = [
            {u'name': u'items', u'children': [
                    { u'name': u'0', u'children': [
                        { u'name': u'sku', u'children': [] }
                    ]}]
            }]
        self.assertEqual(expected, data)

    def test_tuples_are_parsed_into_correct_variables(self):
        expected = [
            {
                u'name': u'somedict', u'children': [
                    {
                        u'name': u'iteritems', u'children': [
                            {
                                u'name': '0', u'children': [
                                    { u'name': '0', u'children': [] },
                                    { u'name': '1', u'children': [] },
                                ]
                            },
                        ] 
                    }
                ]
            }
        ]
        self.assertEqual(expected, self.parse_template('tuples-in-loops.html'))
