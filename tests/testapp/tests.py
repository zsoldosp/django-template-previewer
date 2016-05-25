import json
from django.core.urlresolvers import reverse
from django.test import TransactionTestCase, Client


class RegressionTestCase(TransactionTestCase):

    def test_can_load_main_page(self):
        url = reverse('preview')
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

    def test_can_load_parse_page_for_doc_sample_template(self):
        url = reverse('parse') + '?template=sample.html'
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content)
        self.maxDiff = None
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
