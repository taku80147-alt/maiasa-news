"use strict";
const fs = require("node:fs");
const path = require("node:path");
const buildGuides = function buildGuides(feed) {
  const profiles=[
    ["福祉用具","福祉用具・住宅改修","利用者の動作や生活環境で困っている点はありますか？貸与・販売・住宅改修の選択理由をどのように記録していますか？","適合・安全性・本人の希望を確認し、制度上の対象品目や算定は現行資料と自治体情報で再確認する。"],
    ["住宅改修","住宅改修","玄関や浴室、トイレなどで転倒リスクや介助負担が大きい場所はありますか？","現地の動線と本人の使い方を確認し、工事内容・費用・事前申請の要否を自治体へ確認する。"],
    ["認知症対応型共同生活介護","認知症グループホーム","夜間の巡回や見守り、急変時の連絡で負担が大きい場面はありますか？","実際の職員配置・安全手順を聞き、機器導入だけで人員基準が変わると説明しない。"],
    ["看護小規模多機能","看護小規模多機能","通い・訪問・泊まり・看護の切り替えで現場が困っている点はありますか？","連携の流れと負担を聞き、算定ルールの変更については正式通知が出てから判断する。"],
    ["小規模多機能","小規模多機能","利用者の状況が変化したとき、通い・訪問・泊まりの調整は円滑ですか？","提供体制の課題を整理し、見直し案を現在の人員・報酬要件と混同しない。"],
    ["定期巡回","定期巡回・随時対応","夜間の連絡や緊急訪問の調整で負担が大きいところはありますか？","サービスの連携・出動体制を確認し、統合や算定の検討段階を区別する。"],
    ["夜間対応型訪問介護","夜間対応型訪問介護","夜間コールから訪問までの連携や、他サービスとの引き継ぎで困る点はありますか？","経過措置や移行の適用は正式法令・指定権者への確認が必要。"],
    ["認知症対応型通所介護","認知症対応型通所介護","利用者の状態変化に合わせた活動や送迎、家族との連絡で課題はありますか？","利用者・家族の困りごとを整理し、要件変更の推測はしない。"],
    ["地域密着型通所介護","地域密着型通所介護","送迎や入浴、移乗介助の中で職員の負担が大きい場面はありますか？","現場の介助方法と在宅での動作を確認し、基準・加算が決定したと説明しない。"],
    ["療養通所介護","療養通所介護","医療的なケアが必要な利用者の送迎や情報共有で困りごとはありますか？","医療職やケアマネジャーと確認すべき連携課題を整理する。"],
    ["通所リハビリテーション","通所リハビリテーション","リハビリの目標と自宅での移動・トイレ・入浴の困りごとはつながっていますか？","自宅と通所の動作の違いを確認し、福祉用具は評価結果と本人の希望を踏まえて検討する。"],
    ["通所介護","通所介護","送迎・入浴・移乗で職員の負担が大きい動作は何ですか？","利用者の自宅と通所先の動線を確認し、必要なら補助具や介助方法の見直しを相談する。"],
    ["短期入所療養介護","短期入所療養介護","在宅復帰時の移乗や排泄、家族への情報引き継ぎで困ることはありますか？","退所前後の動作・介護環境を確認し、住宅側の準備不足を減らす相談につなげる。"],
    ["短期入所生活介護","短期入所生活介護","ショートステイ利用前後の生活動作や持参用具で困っている点はありますか？","在宅と事業所の介助方法の違いを共有し、用具の適合と安全性を確認する。"],
    ["訪問入浴","訪問入浴","入浴時の移乗や浴室環境、サービス間の調整で難しい場面はありますか？","安全な入浴環境を整理し、報酬上の併算定可否は現行通知を確認する。"],
    ["訪問介護","訪問介護","ご自宅での移乗・排泄介助など、身体的負担が大きい動作は何ですか？","利用者の動線と介助負担を把握し、現行のサービス範囲を踏まえて支援策を相談する。"],
    ["居宅介護支援","居宅介護支援","サービス担当者会議で、福祉用具や住宅改修の課題を共有しにくい場面はありますか？","本人の生活目標に沿って課題を共有し、変更案を既存の給付条件と混同しない。"],
    ["処遇改善","処遇改善・人材確保","職員の定着や業務負担軽減で今一番優先していることは何ですか？","人材課題を聞き、加算率・要件の確定を出典なしに説明しない。"],
    ["介護テクノロジー","介護テクノロジー","記録・見守り・連絡のどの作業に時間が取られていますか？","現状の業務フローを確認し、機器導入が自動的に加算対象になると断定しない。"],
    ["LIFE","LIFE・データ活用","記録や情報共有で二度手間になっている作業はありますか？","業務手順を確認し、提出要件の変更は公式通知で確認する。"],
    ["情報基盤","介護情報基盤","事業所間の情報連携で、紙・電話・二重入力が負担になっていますか？","現行の運用を把握し、施行時期や義務化を決めつけない。"],
    ["介護保険料","介護保険料","保険料とサービス利用時の自己負担を混同される相談はありませんか？","市区町村の通知と本人の状況で案内し、未決定の金額を伝えない。"],
    ["給付と負担","給付と負担","負担割合について利用者・家族からの問い合わせは増えていますか？","現行の負担割合証を基本に説明し、将来の改定案と区別する。"]
  ];
  const fallback={
    "施設運営":["施設運営","日々の介助や安全管理で、特に負担が大きい作業はありますか？","現場の課題を聞き、具体的な制度変更は資料本文・正式通知で確認する。"],
    "介護DX":["介護DX","記録・見守り・情報共有で二重作業になっていることはありますか？","現在の業務負担を把握し、補助金・加算の確定を断定しない。"],
    "福祉用具":["福祉用具","移動・移乗・トイレ・入浴で介助負担が大きい場面はありますか？","本人に合う用具と現在の対象要件を確認する。"],
    "在宅サービス":["在宅サービス","訪問・通い・泊まりの連携で困っている場面はありますか？","提供側と利用者側の困りごとを聞き、現行の運用と改正の議題を区別する。"],
    "介護保険制度":["介護保険制度","制度の変更予定について、利用者やご家族からどんな質問が多いですか？","現行制度に関する回答は正式通知を確認する。"],
    "人員配置":["人材・配置","人手不足や業務負担の中で優先的に改善したい課題は何ですか？","現行配置基準を前提に聞き、検討中の案を確定事項と扱わない。"]
  };
  const valid = feed.articles.filter(a=>a&&/^n-[a-z0-9-]+$/.test(a.id||"")&&/^20\d{2}-\d\d-\d\d$/.test(a.date||"")&& /^https:\/\/www\.mhlw\.go\.jp\//.test(a.source_url||""));
  const guides=valid.map(a=>{
    const agenda=String(a.summary||"").split("議題：").slice(1).join("議題：")||String(a.summary||"");
    // The agenda is the only confirmed source for auto-generated guidance; no PDF reading is claimed.
    const topics=[]; const covered=[];
    for(const [keyword,label,question,next] of profiles){
      const pos=agenda.indexOf(keyword);
      if(pos<0)continue;
      // Avoid repeating a less specific substring when it is contained in a named specialist service.
      if(keyword==="通所介護" && (agenda.includes("地域密着型通所介護")||agenda.includes("認知症対応型通所介護")) && !/(?:^|[、（・\s])通所介護(?:[、）・\s]|$)/.test(agenda))continue;
      if(keyword==="小規模多機能" && agenda.includes("看護小規模多機能")&&!/小規模多機能型居宅介護/.test(agenda))continue;
      topics.push({label,question,next,order:pos});covered.push(keyword);
    }
    topics.sort((x,y)=>x.order-y.order);
    const unique=[];
    for(const t of topics){if(!unique.some(u=>u.label===t.label))unique.push({label:t.label,question:t.question,next:t.next})}
    const selected=unique.slice(0,7);
    if(!selected.length){
      const [label,question,next]=fallback[a.category]||["介護サービスの運営","利用者の生活動作や介助の中で困っているところはありますか？","課題を聞いたうえで、制度の適用は一次資料で確認する。"];
      selected.push({label,question,next});
    }
    return {
      id:a.id,date:a.date,source_url:a.source_url,source_name:a.source_name,
      stage:"会議の議題から自動作成（資料本文の精読・数値検証は未実施）",
      intro:"厚生労働省の会議資料で「"+selected.map(t=>t.label).join("・")+"」が議題になっています。議論があったことと、制度変更が正式決定したことは別です。",
      target:selected.map(t=>t.label).join("／"),
      topics:selected,
      first_phrase:"「"+selected[0].label+"が今回の会議で議題になっています。現場で困っていることや、準備しておきたいことはありますか？」",
      check_first:"新しい単位数・加算・人員基準・施行日は、議題だけからは分かりません。現行制度と検討案を区別し、必要な場合はリンク先の厚労省資料本文と正式通知を確認してください。",
      generated_from:"厚労省・会議資料の議題／資料日付："+a.date
    };
  });
  return {schema_version:1,guide_kind:"議題ベースの営業会話支援（原文精読済み解説とは別）",source_verified_on:feed.verified_on||"",guides};
};
if (require.main === module) {
  const dir = path.resolve(__dirname, "..", "kaigo-navi2027-preview", "data");
  const feed = JSON.parse(fs.readFileSync(path.join(dir, "latest.json"), "utf8"));
  const output = buildGuides(feed);
  const file = path.join(dir, "sales-guides.json");
  const content = JSON.stringify(output, null, 2) + "\n";
  if (!fs.existsSync(file) || fs.readFileSync(file, "utf8") !== content) {
    fs.writeFileSync(file, content, "utf8");
  }
  process.stdout.write("LivNavi sales guides: " + output.guides.length + " agenda-based cards\n");
}
module.exports = { buildGuides };
