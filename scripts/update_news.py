#!/usr/bin/env python3
"""Official-source news collector. No generated claims or inferred summaries."""
from __future__ import annotations
import hashlib, html, json, re, sys, urllib.parse, urllib.request, urllib.robotparser
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

JST=timezone(timedelta(hours=9))
UA="MaiasaNews/1.0 (+GitHub Actions; official-source monitor)"
SOURCES=[
  {"name":"IPA・情報セキュリティ","url":"https://www.ipa.go.jp/security/security-alert/2026/index.html","category":"business","primary":True},
  {"name":"公正取引委員会","url":"https://www.jftc.go.jp/houdou/pressrelease/2026/index.html","category":"business","primary":True},
  {"name":"厚生労働省","url":"https://www.mhlw.go.jp/stf/news.html","category":"care","primary":True},
  {"name":"厚生労働省・介護保険","url":"https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/kaigo_koureisha/index.html","category":"care","primary":True},
  {"name":"厚生労働省・福祉用具","url":"https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000212398.html","category":"welfare","primary":True},
  {"name":"PMDA","url":"https://www.pmda.go.jp/","category":"medical","primary":True},
  {"name":"宮城県","url":"https://www.pref.miyagi.jp/","category":"local","primary":True,"accept_all":True},
  {"name":"仙台市","url":"https://www.city.sendai.jp/shise/koho/kisha/index.html","category":"local","primary":True,"accept_all":True},
  {"name":"内閣府","url":"https://www.cao.go.jp/press/new_wave/","category":"general","primary":True},
  {"name":"総務省統計局","url":"https://www.stat.go.jp/data/index.html","category":"general","primary":True},
  {"name":"日本銀行","url":"https://www.boj.or.jp/announcements/release_2026/index.htm","category":"general","primary":True},
]
KEYWORDS={
 "business":["取引","契約","支払","価格転嫁","下請","フリーランス","セキュリティ","脆弱性","不正アクセス","フィッシング","Microsoft"],
 "care":["介護","介護保険","介護報酬","高齢者","在宅介護","認知症","地域包括","ケアマネジメント"],
 "welfare":["福祉用具","貸与価格","上限価格","車いす","歩行器","介護ベッド","手すり","スロープ","リフト","安全情報","自主回収"],
 "local":["介護","高齢","医療","福祉","地域包括","在宅","補助","支援","施設"],
 "medical":["医薬品","医療機器","安全","副作用","回収","医療事故","承認","注意"],
 "facility":["施設","事業所","開設","開所","増床","移転"],
 "subsidy":["補助金","助成金","交付金","補助事業","介護テクノロジー","介護DX"],
 "general":["物価","景気","雇用","賃金","金利","災害","地震","経済","企業","人口"],
}
DECISION=["公布","施行","決定","公表","通知","改正しました","開始します","発出"]
DISCUSSION=["検討会","審議会","部会","議論","改正案","法案","意見募集","取りまとめに向け"]
BOILERPLATE=["ページの先頭","サイトマップ","お問い合わせ","メニューを開く","本文へ","著作権","プライバシー","アクセシビリティ","検索","翻訳対象","ホーム >","について紹介しています"]
PRIORITY=["介護保険","介護報酬","福祉用具","貸与","販売種目","上限価格","給付","改正","施行","通知","報酬改定","地域包括","在宅介護","宮城県","仙台市"]
LOW_PRIORITY=["採用","仕事体験","タイアップ","研修会","ラーニングビデオ"]

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

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.blocks=[];self.meta="";self.capture=None;self.buf=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ("script","style","noscript","svg","nav","footer","header","aside"):self.skip+=1
        if tag=="meta" and (attrs.get("name","").lower()=="description" or attrs.get("property","").lower()=="og:description"):
            if not self.meta:self.meta=clean(attrs.get("content",""))
        if not self.skip and tag in ("h1","h2","h3","p","li","dd"):
            self.capture=tag;self.buf=[]
    def handle_data(self,data):
        if self.capture and not self.skip:self.buf.append(data)
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript","svg","nav","footer","header","aside") and self.skip:self.skip-=1
        if self.capture==tag:
            value=clean(" ".join(self.buf))
            if value:self.blocks.append(value)
            self.capture=None;self.buf=[]

def useful_block(text:str,title:str)->bool:
    if not 24<=len(text)<=700:return False
    if any(x in text for x in BOILERPLATE):return False
    if text==title:return False
    return len(re.findall(r"[一-龠ぁ-んァ-ヶ]",text))>=12

def broken_text(text:str)->bool:
    return text.count("�")>0 or sum(text.count(x) for x in ("縺","譁","螟","蜿","繧"))>=3

def focus_block(text:str,title_terms:list[str])->str:
    """Remove neighboring press-release headlines from an official page excerpt."""
    parts=[x.strip() for x in re.split(r"(?<=[。！？])\s*",text) if x.strip()]
    hits=[i for i,x in enumerate(parts) if any(k in x for k in title_terms)]
    if not hits:return text
    start=hits[0]
    if start and len(parts[start-1])<110 and not re.search(r"開始します|開催します|実施します|お知らせします|公表します",parts[start-1]):
        start-=1
    kept=[]
    for i,x in enumerate(parts[start:],start):
        if kept and i not in hits and len(x)<110 and re.search(r"開始します|開催します|実施します|お知らせします|公表します",x):break
        kept.append(x)
        if len(kept)>=3 or sum(map(len,kept))>=480:break
    return " ".join(kept)

def page_detail(url:str,title:str,source_name:str)->tuple[str,str,list[str]]:
    try:
        parser=PageParser();parser.feed(get(url))
        candidates=[]
        generic_terms=("について","における","に関する","令和","年度","仙台市","宮城県","お知らせ","公表します","実施します","開催します","開始します")
        title_terms=[x for x in re.findall(r"[一-龠ァ-ヶ]{3,}",title) if x not in generic_terms]
        if useful_block(parser.meta,title) and any(k in parser.meta for k in title_terms):
            candidates.append(focus_block(parser.meta,title_terms))
        scored=[]
        for i,b in enumerate(parser.blocks):
            if not useful_block(b,title):continue
            title_score=sum(4 for k in title_terms if k in b)
            if not title_score:continue
            score=title_score+sum(2 for k in PRIORITY if k in b)+sum(1 for k in KEYWORDS["care"]+KEYWORDS["welfare"] if k in b)
            score+=2 if re.search(r"20\d{2}年|令和\s*\d+年|対象|開始|施行|改正|公表|通知",b) else 0
            if score>0:scored.append((score,-i,b))
        # Prefer the official page's lead/description, then the most relevant concrete passages.
        for _,__,b in sorted(scored,reverse=True):
            b=focus_block(b,title_terms)
            if all(b not in x and x not in b for x in candidates):candidates.append(b)
            if len(candidates)>=6:break
        if not candidates:return ("","",[])
        points=candidates[:4]
        summary=" ".join(points[:2])
        detail="\n\n".join(points)
        return summary,detail,points
    except Exception:
        return ("","",[])

def tidy_title(value:str)->str:
    value=re.sub(r"^20\d{2}年\s*\d{1,2}月\s*\d{1,2}日(?:掲載)?\s*","",value)
    value=re.sub(r"^(?:(?:安全|審査|救済|採用|その他|国際|医薬品|部外品|全製品|イベント)\s+|New\s+)+","",value)
    value=re.sub(r"\s*(?:NEW|New)\s*$","",value)
    return value.strip()

def status(text:str)->tuple[str,str]:
    if any(k in text for k in DISCUSSION): return "検討・会議資料","確定事項とは限りません。元資料で議論の段階をご確認ください。"
    if any(k in text for k in DECISION): return "公式発表","公表元が示した内容の範囲で掲載しています。"
    return "公式ページ","ページの記載内容だけを掲載しています。"

def classify_title(title:str,default:str)->str:
    care_context=any(k in title for k in ("介護","福祉","高齢","障害","医療","特養","老人ホーム","病院","診療所"))
    if care_context and any(k in title for k in ("補助金","助成金","交付金","補助事業","補助","助成")):
        return "subsidy"
    facility_context=any(k in title for k in ("施設","事業所","老人ホーム","特養","病院","診療所","介護センター"))
    if care_context and facility_context and any(k in title for k in ("新設","開設","開所","増床","移転","整備","設置","指定","廃止","休止")):
        return "facility"
    return default

def extract(source:dict,body:str)->list[dict]:
    out=[]
    # Links are treated as candidate headlines; surrounding text becomes the non-generative summary.
    for m in re.finditer(r"<a\b[^>]*href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>",body,flags=re.I|re.S):
        title=clean(m.group(2))
        if not (12<=len(title)<=130):continue
        if broken_text(title):continue
        if title.count("「")!=title.count("」") or title.count("『")!=title.count("』"):continue
        url=urllib.parse.urljoin(source["url"],html.unescape(m.group(1)))
        if urllib.parse.urlparse(url).scheme not in ("http","https"):continue
        if url.rstrip("/")==source["url"].rstrip("/"):continue
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
        # Navigation text around an unrelated link can contain care keywords.
        # Require the link title itself to show why it belongs in this category.
        if not source.get("accept_all") and not any(k in title for k in keys):continue
        category=classify_title(title,source["category"])
        if category not in ("facility","subsidy") and any(k in title for k in KEYWORDS["welfare"]):category="welfare"
        date_match=re.search(r"(20\d{2})[年./-]\s*(\d{1,2})[月./-]\s*(\d{1,2})日?",around)
        published=f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}" if date_match else ""
        if not published:
            era=re.search(r"令和\s*(\d{1,2})年\s*(\d{1,2})月\s*(\d{1,2})日",title+" "+around)
            if era:
                published=f"{2018+int(era.group(1)):04d}-{int(era.group(2)):02d}-{int(era.group(3)):02d}"
        st,note=status(title)
        out.append({"id":hashlib.sha1(url.encode()).hexdigest()[:14],"category":category,"title":tidy_title(title),"listing_title":title,"summary":"","detail":"","key_points":[],"source":source["name"],"published":published,"status":st,"fact_note":note,"url":url,"primary":True})
    return out


def verified_announcement(url:str,title:str,published:str)->bool:
    """Require a dated individual announcement on an explicitly approved host."""
    host=urllib.parse.urlparse(url).hostname
    allowed={urllib.parse.urlparse(s["url"]).hostname for s in SOURCES}
    if host not in allowed or not published:return False
    try:
        body=get(url)
        parser=PageParser();parser.feed(body)
        heading=re.findall(r"<h1\b[^>]*>(.*?)</h1>",body,re.I|re.S)
        terms=[t for t in re.findall(r"[一-龠ァ-ヶ]{3,}",title) if t not in ("について","に関する","お知らせ")]
        if not terms or not any(any(t in clean(h) for t in terms) for h in heading):return False
        text=clean(body)
        dates=set()
        for y,m,d in re.findall(r"(20\d{2})[年./-]\s*(\d{1,2})[月./-]\s*(\d{1,2})日?",text):
            try:dates.add(datetime(int(y),int(m),int(d)).date().isoformat())
            except ValueError:pass
        for y,m,d in re.findall(r"令和\s*(\d{1,2})年\s*(\d{1,2})月\s*(\d{1,2})日",text):
            try:dates.add(datetime(2018+int(y),int(m),int(d)).date().isoformat())
            except ValueError:pass
        # Reject listing dates absent from the individual announcement.
        return published in dates
    except Exception:return False

JOINT_FEED="https://www.joint-kaigo.com/feed/"
MHLW_TERMS="https://www.mhlw.go.jp/chosakuken/"

def joint_items(body:str)->list[dict]:
    rows=[]
    for item in ET.fromstring(body).findall("./channel/item"):
        title=clean(item.findtext("title", ""));url=item.findtext("link", "").strip()
        if urllib.parse.urlparse(url).hostname!="www.joint-kaigo.com" or not url.startswith("https://www.joint-kaigo.com/articles/"):continue
        try:published=parsedate_to_datetime(item.findtext("pubDate", "")).astimezone(JST).date().isoformat()
        except (ValueError,TypeError):continue
        if not title or broken_text(title):continue
        tags=[clean(t.text or "") for t in item.findall("category")]
        commentary="コラム" in tags or title.startswith("【")
        category=classify_title(title,"care")
        if any(k in title for k in KEYWORDS["welfare"]):category="welfare"
        if any(k in title for k in ("医療","看護","感染","医薬品")) and category=="care":category="medical"
        rows.append({"id":hashlib.sha1(url.encode()).hexdigest()[:14],"category":category,"title":title,
          "summary":"JOINTの"+("コラム・対談" if commentary else "報道記事")+"です。内容はJOINTの元記事でご確認ください。",
          "detail":"","key_points":[],"source":"介護ニュースJOINT","published":published,
          "status":"コラム・見解" if commentary else "JOINT報道","fact_note":"元記事へのリンク紹介です。公式確認済みの制度情報とは区別しています。",
          "url":url,"primary":False,"verified_source":True,"source_type":"media_link","link_only":True,
          "distribution_allowed":False,"distribution_note":"JOINTの記事は配布用PDFの対象外です。"})
    return rows

def collect_joint()->list[dict]:
    robots=urllib.robotparser.RobotFileParser()
    robots.parse(get("https://www.joint-kaigo.com/robots.txt").splitlines())
    if not robots.can_fetch(UA,JOINT_FEED):raise ValueError("RSS access disallowed")
    return joint_items(get(JOINT_FEED))

def distribution_review(x:dict)->tuple[bool,str]:
    # Default deny; only reviewed publisher-owned text under the confirmed policy.
    if urllib.parse.urlparse(x["url"]).hostname!="www.mhlw.go.jp":return False,"配布条件未確認のため、閲覧用です。"
    try:
        body=get(x["url"])
        # Restrict to individual announcements; never automatically approve PDF/third-party attachments.
        path=urllib.parse.urlparse(x["url"]).path
        if not path.startswith("/stf/") or path.endswith(".pdf"):return False,"配布条件未確認のため、閲覧用です。"
        text=clean(body)
        markers=("転載禁止","無断転載","第三者に著作権","第三者の著作権","別の利用条件","資料提供","写真提供","画像提供")
        if any(k in text for k in markers):return False,"個別の権利条件の確認が必要なため、閲覧用です。"
        # Quotations and attributed passages are excluded from automated PDF approval.
        excerpt=x.get("summary", "")+x.get("detail", "")
        if any(k in excerpt for k in ("出典：","出典:","提供：","提供:","©","Copyright","と述べ","と語","との声","引用")):
            return False,"引用元の権利確認が必要なため、閲覧用です。"
        return True,"厚生労働省の利用条件（PDL1.0）を確認。出典を明記して本文の抜粋を編集・整理しています。"
    except Exception:return False,"配布条件を確認できなかったため、閲覧用です。"

def main()->int:
    # Keep a compact history so the dashboard can show only genuinely new/updated items.
    previous={}
    try:
        previous=json.loads(Path("data/news.json").read_text(encoding="utf-8"))
    except Exception:
        previous={}
    history=previous.get("history",{}) if isinstance(previous,dict) else {}
    items=[];errors=[];media=[]
    try:media=collect_joint()
    except Exception as e:errors.append(f"JOINT RSS: {type(e).__name__}")
    for src in SOURCES:
        try: items.extend(extract(src,get(src["url"])))
        except Exception as e: errors.append(f"{src['name']}: {type(e).__name__}")
    unique={}
    for x in items:
        score=(1 if x["published"] else 0)+(2 if x["category"] in ("care","welfare") else 0)
        if x["id"] not in unique or score>unique[x["id"]][0]:unique[x["id"]]=(score,x)
    rows=[v[1] for v in unique.values()]
    now=datetime.now(JST)
    # Dashboard is a daily DIFFERENTIAL feed: only items from the last 3 days
    # are candidates, and already-seen unchanged items are not shown again.
    fresh_cutoff=(now.date()-timedelta(days=3)).isoformat()
    rows=[x for x in rows if x["published"] and fresh_cutoff<=x["published"]<=now.date().isoformat()]
    rows.sort(key=lambda x:(x["published"],x["category"] in ("care","welfare","medical")),reverse=True)

    quotas={"care":18,"welfare":14,"local":14,"medical":12,"general":8,"facility":12,"subsidy":12,"business":12};kept=[]
    for cat,n in quotas.items():kept.extend([x for x in rows if x["category"]==cat][:n])

    # Read each selected announcement page so fingerprints reflect actual content,
    # not just the listing-page title.
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs={pool.submit(page_detail,x["url"],x["title"],x["source"]):x for x in kept}
        for job in as_completed(jobs):
            x=jobs[job];x["summary"],x["detail"],x["key_points"]=job.result();x.pop("listing_title",None)
    for x in kept:
        x["verified_source"]=verified_announcement(x["url"],x["title"],x["published"])
        x["fact_note"]="公式本文からの抜粋です。対象・金額・期限は本文で確認できた範囲のみ掲載しています。"
        x["source_type"]="official"
        x["distribution_allowed"],x["distribution_note"]=distribution_review(x)
        if x["distribution_allowed"]:x["distribution_policy_url"]=MHLW_TERMS
    kept=[x for x in kept if x["verified_source"] and x["key_points"] and x["summary"] and not broken_text(x["title"]+x["summary"]+x["detail"])]

    kept.extend(x for x in media if fresh_cutoff<=x["published"]<=now.date().isoformat())

    def fingerprint(x):
        raw="\n".join([x.get("title",""),x.get("summary",""),x.get("detail","")])
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    fresh=[]
    for x in kept:
        fp=fingerprint(x)
        old=history.get(x["id"],{}) if isinstance(history,dict) else {}
        old_fp=old.get("fingerprint","") if isinstance(old,dict) else ""
        if not old_fp:
            x["change_type"]="新着"
            fresh.append(x)
        elif old_fp!=fp:
            x["change_type"]="更新"
            fresh.append(x)
        else:
            x["change_type"]=""
            fresh.append(x)
        history[x["id"]]={"fingerprint":fp,"last_seen":now.date().isoformat(),"published":x.get("published","")}

    # Keep history bounded while retaining enough memory to prevent repeats.
    if isinstance(history,dict) and len(history)>500:
        ordered=sorted(history.items(),key=lambda kv:kv[1].get("last_seen",""),reverse=True)[:500]
        history=dict(ordered)

    def importance(x):
        text=x["title"]+" "+x["summary"]
        return sum(4 for k in PRIORITY if k in text)-sum(4 for k in LOW_PRIORITY if k in text)+(2 if x["published"] else 0)

    # Important 3 are selected ONLY from today's new/updated stories.
    important=[]
    for cat in ("care","welfare","facility","subsidy","local","medical","general","business"):
        group=[x for x in fresh if x["category"]==cat]
        if group and len(important)<3:important.append(max(group,key=importance)["id"])

    payload={
        "updated_at":now.isoformat(),
        "updated_label":f"{now.month}月{now.day}日 {now:%H:%M}",
        "mode":"recent_verified_and_media_links",
        "new_count":sum(bool(x.get("change_type")) for x in fresh),
        "important_ids":important,
        "items":sorted(fresh,key=lambda x:x["published"],reverse=True),
        "history":history,
        "source_errors":errors
    }
    if not kept and len(errors)>=max(2,len(SOURCES)//2):
        print("Most sources failed; preserving previous data.",file=sys.stderr);return 2
    Path("data").mkdir(exist_ok=True);Path("data/news.json").write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print(f"Collected {len(kept)} recent candidates; publishing {len(fresh)} new/updated items; {len(errors)} source errors.")
    return 0
if __name__=="__main__":raise SystemExit(main())


