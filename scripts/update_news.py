#!/usr/bin/env python3
"""Official-source news collector. No generated claims or inferred summaries."""
from __future__ import annotations
import hashlib, html, json, re, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST=timezone(timedelta(hours=9))
UA="MaiasaNews/1.0 (+GitHub Actions; official-source monitor)"
SOURCES=[
  {"name":"厚生労働省","url":"https://www.mhlw.go.jp/stf/news.html","category":"care","primary":True},
  {"name":"厚生労働省・介護保険","url":"https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/kaigo_koureisha/index.html","category":"care","primary":True},
  {"name":"厚生労働省・福祉用具","url":"https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000212398.html","category":"welfare","primary":True},
  {"name":"PMDA","url":"https://www.pmda.go.jp/","category":"care","primary":True},
  {"name":"宮城県","url":"https://www.pref.miyagi.jp/site/kourei/","category":"local","primary":True},
  {"name":"仙台市","url":"https://www.city.sendai.jp/kurashi/kenkotofukushi/korenokata/index.html","category":"local","primary":True},
  {"name":"内閣府","url":"https://www.cao.go.jp/press/new_wave/","category":"general","primary":True},
  {"name":"総務省統計局","url":"https://www.stat.go.jp/data/index.html","category":"general","primary":True},
  {"name":"日本銀行","url":"https://www.boj.or.jp/announcements/release_2026/index.htm","category":"general","primary":True},
]
KEYWORDS={
 "care":["介護","高齢","医療","診療報酬","介護報酬","在宅","認知症","社会保障","福祉","看護","リハビリ","薬","医療機器"],
 "welfare":["福祉用具","貸与価格","上限価格","車いす","歩行器","介護ベッド","手すり","スロープ","リフト","安全情報","自主回収"],
 "local":["介護","高齢","医療","福祉","地域包括","在宅","補助","支援","施設"],
 "general":["物価","景気","雇用","賃金","金利","災害","地震","経済","企業","人口"],
}
DECISION=["公布","施行","決定","公表","通知","改正しました","開始します","発出"]
DISCUSSION=["検討会","審議会","部会","議論","案","意見募集","取りまとめに向け"]

def get(url:str)->str:
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept-Language":"ja"})
    with urllib.request.urlopen(req,timeout=25) as r:
        raw=r.read(2_000_000)
        enc=r.headers.get_content_charset() or "utf-8"
    try:return raw.decode(enc,"replace")
    except LookupError:return raw.decode("utf-8","replace")

def clean(s:str)->str:
    s=re.sub(r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>"," ",s,flags=re.I|re.S)
    s=re.sub(r"<[^>]+>"," ",s);s=html.unescape(s)
    return re.sub(r"\s+"," ",s).strip()

def status(text:str)->tuple[str,str]:
    if any(k in text for k in DISCUSSION): return "検討・会議資料","確定事項とは限りません。元資料で議論の段階をご確認ください。"
    if any(k in text for k in DECISION): return "公式発表","公表元が示した内容の範囲で掲載しています。"
    return "公式ページ","ページの記載内容だけを掲載しています。"

def extract(source:dict,body:str)->list[dict]:
    out=[]
    # Links are treated as candidate headlines; surrounding text becomes the non-generative summary.
    for m in re.finditer(r"<a\b[^>]*href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>",body,flags=re.I|re.S):
        title=clean(m.group(2))
        if not (12<=len(title)<=130):continue
        url=urllib.parse.urljoin(source["url"],html.unescape(m.group(1)))
        if urllib.parse.urlparse(url).scheme not in ("http","https"):continue
        start=max(0,m.start()-180);end=min(len(body),m.end()+280)
        # Avoid beginning or ending the excerpt inside an HTML tag.
        if start:
            tag_end=body.find(">",start,m.start())
            if tag_end!=-1:start=tag_end+1
        if end<len(body):
            tag_start=body.rfind("<",m.end(),end)
            if tag_start!=-1:end=tag_start
        around=clean(body[start:end])
        keys=KEYWORDS[source["category"]]
        if not any(k in title+around for k in keys):continue
        category=source["category"]
        if any(k in title+around for k in KEYWORDS["welfare"]):category="welfare"
        date_match=re.search(r"(20\d{2})[年./-]\s*(\d{1,2})[月./-]\s*(\d{1,2})日?",around)
        published=f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}" if date_match else ""
        summary=around
        if title in summary: summary=summary.replace(title,"",1).strip(" ｜|・:：")
        if len(summary)<20: summary=f"{source['name']}が公開している新着情報です。"
        summary=summary[:220].rstrip("、。 ")+"。"
        st,note=status(title+summary)
        out.append({"id":hashlib.sha1(url.encode()).hexdigest()[:14],"category":category,"title":title,"summary":summary,"detail":summary,"source":source["name"],"published":published,"status":st,"fact_note":note,"url":url,"primary":True})
    return out

def main()->int:
    items=[];errors=[]
    for src in SOURCES:
        try: items.extend(extract(src,get(src["url"])))
        except Exception as e: errors.append(f"{src['name']}: {type(e).__name__}")
    unique={}
    for x in items:
        score=(1 if x["published"] else 0)+(2 if x["category"] in ("care","welfare") else 0)
        if x["id"] not in unique or score>unique[x["id"]][0]:unique[x["id"]]=(score,x)
    rows=[v[1] for v in unique.values()]
    rows.sort(key=lambda x:(x["published"],x["category"] in ("care","welfare")),reverse=True)
    # Keep the page compact; healthcare/care gets the largest quota.
    quotas={"care":18,"welfare":12,"local":12,"general":8};kept=[]
    for cat,n in quotas.items():kept.extend([x for x in rows if x["category"]==cat][:n])
    important=[]
    for cat in ("care","welfare","local","general"):
        hit=next((x for x in kept if x["category"]==cat),None)
        if hit and len(important)<3:important.append(hit["id"])
    now=datetime.now(JST)
    payload={"updated_at":now.isoformat(),"updated_label":f"{now.month}月{now.day}日 {now:%H:%M}","important_ids":important,"items":kept,"source_errors":errors}
    if len(kept)<3:
        print(f"Collected only {len(kept)} items; preserving previous data.",file=sys.stderr);return 2
    Path("data").mkdir(exist_ok=True);Path("data/news.json").write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print(f"Collected {len(kept)} official-source items; {len(errors)} source errors.")
    return 0
if __name__=="__main__":raise SystemExit(main())
