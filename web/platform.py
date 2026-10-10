"""Bounded article/answer comment research over cv-cat/ZhihuApis."""
import json
import os
from pathlib import Path
import re
import time
from html import unescape
from urllib.parse import urlsplit,parse_qs
import requests
from apis import zhihu_apis
from utils.zhihu_utils import get_comment_headers,get_x_zse_96
from .service import PlatformError


class BoundedRequests:
    @staticmethod
    def get(url,**kwargs):
        kwargs.setdefault('timeout',(8,20));response=requests.get(url,**kwargs);response.raise_for_status();return response
zhihu_apis.requests=BoundedRequests


def text(value):return unescape(re.sub('<[^>]+>','',str(value or '')))


def checked(result):
    ok,_,raw=result
    if not ok or not isinstance(raw,dict) or raw.get('error') or not isinstance(raw.get('data'),list):
        raise PlatformError('知乎评论读取失败，请检查 Cookie、文章/回答 ID 或在官网完成验证后重试')
    return raw


def projection(row,source_url,source_label,parent=''):
    author=row.get('author') or {};member=author.get('member') or author
    return {'id':'comment-'+str(row.get('id','')),'comment_id':str(row.get('id','')),
        'title':text(member.get('name') or '知乎用户')+'的评论','text':text(row.get('content')),
        'author':text(member.get('name') or '知乎用户'),'uid':str(member.get('id') or member.get('url_token') or ''),
        'url':source_url,'cover':'','views':row.get('child_comment_count',0),'likes':row.get('like_count',0),
        'comments':row.get('child_comment_count',0),'created':row.get('created_time',''),'parent_id':parent,
        'source':source_label,'tags':source_label,'note':''}


class Platform:
    def __init__(self,directory):self.path=Path(directory)/'account.json';self.api=zhihu_apis.ZhiHu_Apis();self.progress=lambda value:None
    def identity(self):return json.loads(self.path.read_text())['account'] if self.path.exists() else None
    def cookie(self):
        if not self.path.exists():raise PlatformError('请先导入知乎登录 Cookie（含 d_c0 和 z_c0）')
        return json.loads(self.path.read_text())['cookie']
    def persist(self,cookie,account):
        tmp=self.path.with_suffix('.tmp');fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as f:json.dump({'cookie':cookie,'account':account},f,ensure_ascii=False)
        os.replace(tmp,self.path);return account
    def connect(self,cookie):
        cookies=dict(x.strip().split('=',1) for x in cookie.split(';') if '=' in x)
        if not cookies.get('d_c0') or not cookies.get('z_c0'):raise PlatformError('Cookie 需要包含 d_c0 和 z_c0，请在知乎官网登录后复制')
        headers=get_comment_headers();url='https://www.zhihu.com/api/v4/me'
        headers['x-zse-96']=get_x_zse_96(url,{},cookies['d_c0'])
        try:raw=BoundedRequests.get(url,headers=headers,cookies=cookies).json()
        except Exception:raise PlatformError('知乎账号检查未通过，请重新复制登录 Cookie')
        if not raw.get('id') or raw.get('error'):raise PlatformError('知乎 Cookie 已失效或账号需要验证')
        normalized='; '.join(f'{k}={v}' for k,v in cookies.items())
        return self.persist(normalized,{'id':str(raw['id']),'name':text(raw.get('name')),'status':'connected','checked_at':time.time()})
    def check(self):return self.connect(self.cookie())
    def disconnect(self):self.path.unlink(missing_ok=True)
    def search(self,*args):raise PlatformError('请使用专项工具采集文章或回答评论')
    def detail(self,*args):raise PlatformError('请使用专项工具采集文章或回答评论')
    def comments(self,*args):raise PlatformError('请使用评论采集工具查看楼中楼')
    def user(self,*args):raise PlatformError('当前知乎上游提供文章与回答评论接口')
    def publish(self,*args):raise PlatformError('当前知乎工作台只保存本地研究草稿')
    def qr_start(self):raise PlatformError('请使用 Cookie 连接知乎账号')
    def qr_poll(self,token):raise PlatformError('请使用 Cookie 连接知乎账号')

    @staticmethod
    def resolve(value,kind):
        if re.fullmatch(r'\d{3,24}',value):return value,kind
        u=urlsplit(value)
        if u.scheme!='https' or u.hostname not in ('www.zhihu.com','zhihu.com','zhuanlan.zhihu.com') or u.port not in (None,443) or u.username or u.password:
            raise PlatformError('请输入知乎文章/回答数字 ID 或 HTTPS 原文链接')
        match=re.fullmatch(r'/p/(\d{3,24})/?',u.path)
        if match and u.hostname=='zhuanlan.zhihu.com':return match.group(1),'article'
        match=re.fullmatch(r'(?:/question/\d+)?/answer/(\d{3,24})/?',u.path)
        if match and u.hostname in ('www.zhihu.com','zhihu.com'):return match.group(1),'answer'
        raise PlatformError('请提供具体回答或专栏文章链接，问题链接不包含回答 ID')

    def tool(self,name,data):
        cookie=self.cookie()
        if name=='children':
            comment_id=str(data.get('comment_id','')).strip()
            if not re.fullmatch(r'\d{3,30}',comment_id):raise PlatformError('请输入评论数字 ID')
            raw=checked(self.api.get_article_inner_comment(comment_id,'',cookie))
            items=[projection(x,'https://www.zhihu.com/','评论 '+comment_id,comment_id) for x in raw['data']]
            return {'items':items,'notice':'当前页楼中楼；在任务或收藏导出中保留 parent_id'}
        if name!='collect':raise PlatformError('工具不存在')
        kind=str(data.get('kind','answer'))
        if kind not in ('answer','article'):raise PlatformError('请选择回答或文章')
        content_id,kind=self.resolve(str(data.get('value','')).strip(),kind)
        try:pages=int(data.get('pages',1))
        except Exception:raise PlatformError('采集页数需要 1–10')
        if not 1<=pages<=10:raise PlatformError('每次最多采集 10 页，避免长时间批量请求')
        children=data.get('children')=='yes';max_requests=40;calls=0;offset='';items=[];seen=set();offsets=set();is_end=False;child_limited=False
        source_url=f'https://zhuanlan.zhihu.com/p/{content_id}' if kind=='article' else f'https://www.zhihu.com/answer/{content_id}'
        label=('文章 ' if kind=='article' else '回答 ')+content_id
        method=self.api.get_article_outer_comment if kind=='article' else self.api.get_answer_outer_comment
        child_method=self.api.get_article_inner_comment if kind=='article' else self.api.get_answer_inner_comment
        for page in range(pages):
            if calls>=max_requests:break
            self.progress({'stage':'读取第 '+str(page+1)+' 页','count':len(items),'requests':calls})
            raw=checked(method(content_id,offset,cookie));calls+=1
            for row in raw['data']:
                item=projection(row,source_url,label)
                if item['id'] not in seen:items.append(item);seen.add(item['id'])
                if children and int(row.get('child_comment_count') or 0)>0:
                    if calls>=max_requests:child_limited=True;continue
                    child_offset='';child_offsets=set()
                    for _ in range(3):
                        if calls>=max_requests:child_limited=True;break
                        child=checked(child_method(str(row['id']),child_offset,cookie));calls+=1
                        for reply in child['data']:
                            sub=projection(reply,source_url,label,str(row['id']))
                            if sub['id'] not in seen:items.append(sub);seen.add(sub['id'])
                        paging=child.get('paging') or {}
                        if paging.get('is_end',True):break
                        new_offset=parse_qs(urlsplit(paging.get('next','')).query).get('offset',[''])[0]
                        if not new_offset or new_offset in child_offsets:child_limited=True;break
                        child_offsets.add(new_offset);child_offset=new_offset;time.sleep(.3)
                    else:child_limited=True
            paging=raw.get('paging') or {};is_end=bool(paging.get('is_end',True))
            if is_end:break
            next_offset=parse_qs(urlsplit(paging.get('next','')).query).get('offset',[''])[0]
            if not next_offset or next_offset in offsets:break
            offsets.add(next_offset);offset=next_offset;time.sleep(.4)
        notice=f'本次采集 {len(items)} 条评论，共 {calls} 次请求。'+('一级评论已到末页。' if is_end else '已达本次采集上限，结果不代表全量。')
        if child_limited:notice+=' 部分楼中楼已达到每楼 3 页 / 总计 40 次请求上限。'
        return {'items':items,'notice':notice,'source':source_url,'has_more':not is_end,'next_offset':offset}
