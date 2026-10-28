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
from discover_kaigo_notices import NOTICE_INDEX, scan_notices, triage, notice_article, reconcile_inventory, coverage_errors

ROOT=Path(__file__).resolve().parent.parent
DEST=ROOT/'kaigo-navi2027-preview'/'data'/'latest.json'
INVENTORY=DEST.with_name('source-inventory.json')
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
 # Every configured source must be parsed. Partial success is not a full check.
 for code,label,url in INDEXES:
  found=scan(code,label,url,get(url))
  print(label,'found',len(found))
  for item in found:
   prior=previous.get(item['id'])
   if prior and prior['source_url'] != item['source_url']:
    raise RuntimeError('Meeting source changed; editorial recheck required: '+item['id'])
   merged[item['id']]=prior or item
 notices=scan_notices(get(NOTICE_INDEX))
 prior_inventory=json.loads(INVENTORY.read_text(encoding='utf-8')) if INVENTORY.exists() else {}
 selected_rows=reconcile_inventory(notices,prior_inventory,[])['documents']
 for row in selected_rows:
  if row['selection']=='include':
   prior=previous.get(row['id'])
   if prior and prior['source_url'] != row['source_url']:
    raise RuntimeError('Notice source changed; editorial recheck required: '+row['id'])
   merged[row['id']]=prior or notice_article(row,classify)
 for item in before['articles']:merged.setdefault(item['id'],item)
 articles=sorted(merged.values(),key=lambda x:(x['date'],x['id']),reverse=True)
 inventory=reconcile_inventory(notices,prior_inventory,articles)
 missing=coverage_errors(inventory,articles)
 if missing:raise RuntimeError('Discovered reform notices not listed: '+', '.join(missing))
 if len(articles)<3:raise RuntimeError('Too few source-linked articles')
 output={**before,'source_type':'厚生労働省・会議資料・通知・Q&A',
         'disclaimer':'検討案・通知・Q&Aを区別します。資料公開だけで改正の決定・施行とは判断しません。',
         'articles':articles}
 if articles!=before['articles']:
  output['verified_on']=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
 for path,data in [(DEST,output),(INVENTORY,inventory)]:
  content=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
  if path.exists() and path.read_text(encoding='utf-8')==content:continue
  tmp=path.with_suffix('.tmp');tmp.write_text(content,encoding='utf-8');os.replace(tmp,path)
 print('NOTICE_COVERAGE',json.dumps({'discovered':len(notices),'included':sum(r['selection']=='include' for r in inventory['documents']),
       'review_pending':[r['id'] for r in inventory['documents'] if r['selection']=='review_pending'],'missing':missing},ensure_ascii=False))
 print('Updated',len(articles),'articles')

if __name__=='__main__':main()

