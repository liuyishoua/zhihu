import tempfile,unittest
from unittest.mock import Mock
from web.platform import Platform

class AdapterTests(unittest.TestCase):
    def test_bounded_collection_retains_parent_relationship(self):
        with tempfile.TemporaryDirectory() as d:
            p=Platform(d);p.cookie=lambda:'offline-placeholder'
            p.api=Mock()
            p.api.get_answer_outer_comment.return_value=(True,'ok',{'data':[{'id':'root001','content':'<p>父评论</p>','author':{'member':{'name':'父作者'}},'child_comment_count':1}],'paging':{'is_end':True}})
            p.api.get_answer_inner_comment.return_value=(True,'ok',{'data':[{'id':'child001','content':'回复','author':{'member':{'name':'子作者'}}}],'paging':{'is_end':True}})
            value=p.tool('collect',{'value':'123456','kind':'answer','pages':1,'children':'yes'})
            self.assertEqual(len(value['items']),2);self.assertEqual(value['items'][1]['parent_id'],'root001')
            self.assertIn('已到末页',value['notice']);self.assertNotIn('<',value['items'][0]['text'])
            self.assertEqual(p.api.get_answer_outer_comment.call_count,1)
    def test_type_is_inferred_and_limits_are_enforced(self):
        self.assertEqual(Platform.resolve('https://zhuanlan.zhihu.com/p/123456','answer'),('123456','article'))
        with self.assertRaises(ValueError):Platform.resolve('https://www.zhihu.com/question/123456','answer')
        with tempfile.TemporaryDirectory() as d:
            p=Platform(d);p.cookie=lambda:'offline'
            with self.assertRaises(ValueError):p.tool('collect',{'value':'123456','pages':11})
