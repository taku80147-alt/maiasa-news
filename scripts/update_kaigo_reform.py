#!/usr/bin/env python3
"""Monitor MHLW council indexes for source-linked meeting documents.

Only meeting metadata is published automatically. No law-change decisions or
numeric reimbursement claims are inferred. On error preserve the last good JSON.
"""
import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent.parent
DEST=ROOT/'kaigo-navi2027-preview'/'data'/'latest.json'
INDEXES=[
 ('pay','介護給付費分科会','https://www.mhlw.go.jp/stf/shingi/shingi-hosho_126698_00022.html'),
 ('ins','介護保険部会','https://www.mhlw.go.jp/stf/shingi/shingi-hosho_126734.html')
]

def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; KaigoNavi2027/1.0)','Accept':'text/html'})
 with urllib.request.urlopen(req,timeout=30) as r:
  if r.status!=200: raise ValueError('HTTP '+str(r.status))
  return r.read().decode('utf-8',errors='replace')

def normalize(s):
 return re.sub(r'\s+',' ',s).strip()

def classify(s,section):
 if '福祉用具' in s or '住宅改修' in s: return '福祉用具'
 if '認知症' in s: return '認知症・地域密着'
 if '小規模多機能' in s or '訪問' in s: return '在宅サービス'
 if '情報基盤' in s or 'LIFE' in s: return '介護DX'
 if '処遇' in s or '人材' in s: return '人員配置'
 if '介護老人福祉施設' in s: return '施設運営'
 return '介護保険制度' if section=='ins' else '介護報酬'

def scan(code,label,url,html):
 meetings=[]
 for tr in BeautifulSoup(html,'html.parser').select('tr'):
  td=tr.find_all(['th','td'],recursive=False)
  if len(td)<3: continue
  n=re.search(r'第\s*(\d{2,3})\s*回',normalize(td[0].get_text(' ',strip=True)))
  d=re.search(r'(20\d\d)\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',normalize(td[1].get_text(' ',strip=True)))
  if not n or not d: continue
  try: date=dt.date(*map(int,d.groups())).isoformat()
  except ValueError: continue
  if date<'2026-04-01': continue
  agenda=normalize(td[2].get_text(' ',strip=True))
  if len(agenda)<12: continue
  link=None
  for cell in td[3:]:
   for a in cell.find_all('a',href=True):
    if '資料' in a.get_text(' ',strip=True):
     dest=urllib.parse.urljoin(url,a['href'])
     if dest.startswith('https://www.mhlw.go.jp/'):
      link=dest;break
   if link: break
  if not link: continue
  number=n[1]
  actual_label='介護事業経営調査委員会' if (code=='pay' and '介護事業経営調査委員会' in agenda) else label
  actual_code='econ' if actual_label=='介護事業経営調査委員会' else code
  if actual_code=='econ': agenda=agenda.replace('介護事業経営調査委員会','',1).strip()
  summary=f'第{number}回{actual_label}の議題：{agenda}'
  if len(summary)>110: summary=summary[:107].rstrip(' ・、')+'…'
  meetings.append({
   'id':f'n-{actual_code}-{number}','date':date,
   'title':f'第{number}回{actual_label}の資料が公開',
   'summary':summary,
   'detail':f'{date}の第{number}回{actual_label}の公式資料が公開されています。議題は「{agenda[:160]}」。資料の公表だけで制度改正が正式決定したわけではありません。',
   'sales_tip':'得意先への説明では「審議された内容」と「法令で正式決定された内容」を区別してください。',
   'category':classify(agenda,code),'status':'会議資料',
   'source_url':link,'source_name':f'厚生労働省 第{number}回{actual_label}資料',
   'curated':False})
 if not meetings: raise RuntimeError(f'No parseable recent meetings: {url}')
 return meetings

def main():
 before=json.loads(DEST.read_text(encoding='utf-8'))
 previous={x['id']:x for x in before['articles']}
 merged={}
 successes=0
 for code,label,url in INDEXES:
  try:
   found=scan(code,label,url,get(url))
   print(label,'found',len(found))
   successes+=1
   for item in found:merged[item['id']]=previous.get(item['id'],item)
  except Exception as exc:print('WARNING',label,exc,flush=True)
 if successes==0:raise RuntimeError('Both source pages failed; original JSON remains unchanged')
 for item in before['articles']:merged.setdefault(item['id'],item)
 articles=sorted(merged.values(),key=lambda x:(x['date'],x['id']),reverse=True)[:40]
 if len(articles)<3:raise RuntimeError('Too few source-linked articles')
 if articles==before['articles']:
  print('No new entries, nothing to publish');return
 output={'schema_version':1,
         'verified_on':dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat(),
         'source_type':'厚生労働省・会議資料',
         'disclaimer':'会議の議題・資料公開の情報です。改正の正式決定・施行を意味しません。',
         'articles':articles}
 tmp=DEST.with_suffix('.tmp')
 tmp.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 os.replace(tmp,DEST)
 print('Updated',len(articles),'articles')

if __name__=='__main__':main()
