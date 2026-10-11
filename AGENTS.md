# Codex handoff — 介護制度改正ナビ2027 (2026-10-10)

## Project and owner intent
This repository hosts several projects. **The approved care-reform app is only at `kaigo-navi2027-preview/`.** Older `kaigo-navi2027/` is NOT the approved UI. Do not alter unrelated `maiasa-news` app/files unless specifically requested.

Product goal: A **free-to-run**, browser-accessible, mobile-first Japanese nursing-care system reform explainer for Sendai sales reps, not merely a headline collector. It must help reps understand official policies *and* explain them accurately and plainly to care managers, home-care/assistive-equipment shops, nursing-care facilities, users/families. Address ALL relevant 2027 care-law / reimbursement / operational themes, not just welfare equipment. No required login, no password, no Google account. Hosted on GitHub Pages if possible. Avoid fees, paid API dependencies, SaaS trials, and uncertain billing; disclose where fully automatic AI article generation without paid inference is not feasible.

## Immutable approved UI / design change discipline
**User selected the latest `kaigo-navi2027-preview/index.html` UI and explicitly praised its visual balance.** Treat it as design source of truth. NEVER wholesale redesign or replace it with a utilitarian dashboard. Keep the sky-blue illustrated Sendai/cityscape reform banner, vivid rounded topic cards, welcoming cheerful design, visible bottom navigation, horizontal headings, and current typography. Changes must be minimal, scoped to requested area, and visually regression-tested against the unchanged baseline.

User's top usability decisions: horizontal-swipe feeds are unacceptable; news is a vertical list (up to 3 prominent items on home); the page scrolls vertically naturally; no giant banner wasting the first viewport; no '特集をみる' button; no forced compression of all content into one screen; bottom nav stays visible. Ensure title/header and latest information heading never wrap into vertical glyph stacks.

Do not report success without functional + visual validation at mobile viewports 320, 360, 390 and 430 CSS px, including actual screenshot comparison, no horizontal overflow, no clipped cards or navbar, and working taps. If visual browser testing is unavailable, say it is unverified — never misrepresent it.

## Current code
- `kaigo-navi2027-preview/index.html`: approved design + source-linked article detail UX. Large self-contained HTML; prefer surgical changes over replacing all markup.
- `kaigo-navi2027-preview/data/latest.json`: source-linked verified/candidate official meeting summaries. Publication of a meeting agenda is NOT a formal reform decision.
- `scripts/update_kaigo_reform.py`: daily official *meeting listing* scraper only; does not currently read full PDFs, extract exceptions/tables, or generate careful understandable explanations.
- `.github/workflows/update-kaigo-reform.yml`: free GitHub Actions scheduled daily check and Pages deployment; schedule timing is approximate.
- GitHub Pages: `https://taku80147-alt.github.io/maiasa-news/kaigo-navi2027-preview/`

Other news workflows/pages must not be broken.

## Priority: evidence-to-explanation pipeline (next development)
The user wants deeply read official documents, not teaser summaries. Build an auditable staged pipeline:
1. Discover new primary official sources (MHLW care council PDFs, discussion papers, legal ordinances, notices, Q&A). Deduplicate by official source URL and document date. Preserve source original.
2. Retrieve and parse full document text, TABLES, side notes, exception clauses, service-type eligibility. Handle broken PDFs/scan and unavailable files by failing closed — no guessed contents. Use free OSS tools (pymupdf, pypdf, pdfplumber, etc); verify license/security and testing. Avoid expensive OCR unless necessary and justified.
3. Determine epistemic status **現行制度 / 検討中（案） / 決定（公布・通知） / 施行済み** only when evidence supports it. Do not infer "決定" from council meeting documents.
4. Every article must include: exact date of document and date of discussion where known, category/service type, short practical summary in clear Japanese, full easy-to-follow explanation, **current vs proposal** (if grounded), applicability and exceptions, exact numeric units / percentage / thresholds with source + page/table anchors, sales impact, and audience-tailored explanation examples without invented promises or advice.
5. Independent evidence/quality checks: quotes/numerals vs source including unit, denominator, time scope, applicability; dates; contradictions; no undocumented claims; relevant source URLs and page numbers; clear human check requirement where automation cannot verify. If evidence insufficient, label as uncertain or hold from publication. Prefer fewer correct articles to many weak ones.
6. Output structured JSON with version/validation, issue warnings, and artifact links. Add tests and dry-run before publishing. Keep GitHub Actions free quota in view; robust timeouts/retries/fail-safe/preserve last known good data; no secrets in repository.
7. Start by thoroughly processing 2 official articles for acceptance: `第268回介護給付費分科会` 2026-09-30 basic viewpoints (draft), and `第259回` 2026-06-29 welfare equipment / home renovation material. Check every actual PDF; never fabricate details or numeric claims. Make 30-second / 3-minute / sales-ready reading layers, precise citations/page/figures.
8. Add PDF handout customer explanations later, maintaining confirmed legal facts.

## Operating philosophy
The user has suffered repetitive loss of adopted design and having to QA obvious errors. Be proactive, preserve approved choices, do self-review, run tests, and be truthful about what has/hasn't been tested. Do NOT ask the user to hand-check basic design, numbers, or links. Escalate only real trade-offs and irreversible actions. Keep costs basically zero. Respect explicit user agreement before adding paid services.

## Repo collaboration
Use small commits and/or pull requests, separate pipeline code from UI. No unexpected rewrites. When user explicitly asks only for planning/advice, do not change files. For current next task, start by analyzing existing code, proposing testable staged plan, then build safe code with automated tests and source-based exemplar articles.

## 2026-10-10 implementation update (verified)
- `kaigo-navi2027-preview/data/explainers.json` contains two curated, page-cited 30-second/deep-dive/customer-talk articles (第268回基本的な視点案 and 第259回福祉用具・住宅改修). Preserve editorial dates and wording; do not present proposals as decisions.
- `scripts/build_kaigo_explainers.py` reads the **full original PDFs** using free PyMuPDF; rejects unreadable PDFs, verifies declared page anchors and pinned source hashes, and only then writes `kaigo-navi2027-preview/data/explainers-verified.json`. 268 draft-summary PDF = 1 page; 259 source PDF = 48 pages. Do not treat PDF-anchor validation as complete human legal correctness verification.
- `scripts/test_kaigo_explainers.py` checks article status, numbers, current/proposal distinction, release synchronization, and source provenance. `.github/workflows/verify-kaigo-explainers.yml` runs on updates and weekly; failure halts publication of new detailed articles. We fixed two overly literal test failures and confirmed a succeeding release/test run.
- `scripts/collect_kaigo_documents.py` + `.github/workflows/collect-kaigo-documents.yml` download up to 4 **new** MHLW meeting PDFs daily and validate page text coverage; records extracted-document metadata in `data/document-review-queue.json` without auto-publishing speculative summaries. First run read four PDFs from 第269回, 27 + 33 + 30 + 35 pages.
- The approved `index.html` retains original visual design and now shows the three *article detail* tabs ⚡30秒/📖詳しく/💼営業; these only load the verified JSON and show official page anchors. Do not redesign homepage.
- Main unsolved challenge: safe **free automated full-document synthesis with independently verified numeric/legal reasoning**. We currently automate discovery, PDF extraction, page-anchor QA, article distribution; editorial prose for two high-stakes sample articles was prepared and verified in this chat. A model-free scraper alone is not capable of comprehensive reliable interpretations. Do not claim that fully autonomous, correct summaries are done.
- Next steps: strengthen legal cross-references (effective dates, exceptions, current law); test actual hosted mobile rendering, improve extracted tabular evidence coverage, gradually curate/review remaining PDF queue; scale with free GitHub Actions while respecting limits.

## 2026-10-10 additional release: four reviewed articles
- Added `n-pay-269-gh`: 2026-10-09 第269回分科会 資料４「認知症対応型共同生活介護」（35 PDF pages), and `n-pay-269-sm`: 資料２「小規模多機能型居宅介護」（30 pages). Both have all three detailed reading modes and source-page pointers. Approved count is now **4**, not 2.
- `data/latest.json` includes these IDs. Parent meeting item `n-pay-269` links to the two deeper articles. Nested article back navigation fixed, and unreviewed articles are visibly labeled as overview-only.
- PDF build now checks source SHA256, every declared evidence anchor, explicit **scoped numeric literal/page** (`numeric_evidence`), and >=75% readable text coverage for multi-page PDFs. This proves only the checks described; it is NOT a formal guarantee of complete legal accuracy. Human-grade comparison of PDF tables, exceptions, newest notices still required.
- Corrected accidental source category `第44回介護給付費分科会` to **第44回介護事業経営調査委員会** with id `n-econ-44`. Do not merge these committees. Added regression guard to reject duplicate feed ids.
- Keep `scripts/inspect_kaigo_pdf.py` as an optional manual editorial inspection helper, NOT a scheduled article-publishing agent.

## Overnight handoff: validated mobile end-to-end QA (2026-10-10 ~23:20 JST)
- `scripts/test_kaigo_mobile.cjs` and `.github/workflows/test-kaigo-mobile.yml` are a **no-paid-API** Chromium smoke test. On approved `index.html` edits, GitHub Actions now renders 320/360/390/430px pages and tests no horizontal overflow, 3 home news cards, bottom navigation, all four 2026-10-09 curated topic links, quick/deep/sales tabs, and return navigation. 8 screenshots are archived as an Actions artifact for 7 days. Latest result: successful run 38058959943 at commit 33e61d4a (selector fix).
- First run failed **only due to the QA selector grabbing a hidden home card** instead of a visible `#viewbody` card; we corrected the test, reran and it passed. This is not pixel-perfect screenshot comparison; do not claim exact design regression testing from the automated smoke tests alone.
- `kaigo-navi2027-preview/index.html` parent `n-pay-269` article now links to all four developed subtopics (GH/SM/NM/DN), not only GH/SM; visible strings "見本記事" were corrected. No changes to approved home layout.
- Reuse the smoke workflow and archived screenshots after any subsequent index.html edits. Do not alter auto-verified articles based on visual checks alone.


## Work継続更新（2026-10-11）
- 採用画像10点・バナー・丸い特集カード・縦スクロールを維持。特集は実記事へリンク。
- 解説は13記事（うち現行制度の基礎2記事）。給付と負担、1号保険料、DX、公布済み法律・福祉用具販売の算定枠組みを追加。status_kind は proposal/current/mixed/enacted。記事日付は資料の実日付。
- 看多機の費用表は計7件だが金額無回答1件を含む。平均の算出母数は明記されず、「7件すべての平均」と表現しない。
- 原本を保存し、全ページ本文・表候補・注記例外候補を取得する kaigo_evidence.py を共通化。原本改変、空の根拠、読取不能、数値のページ違い、単位違い、途中失敗時の公開保持をテスト。
- JSON schema2。article_sha256 と原本ハッシュ・根拠・数値をクライアントでも照合。未審査資料から解説を自動生成しない。
- お気に入り永続化、詳細本文検索（全角数字・複数語）、学習記事、記事直リンク、営業ネタを実装。「調べる」は記事検索で、有料AI自動回答は使用しない。
- Pages公開は再利用スマホQA＋全オフラインテストが必要。320/360/390/430px、全13記事、検索・保存・失敗時・改変記事除外と、採用画面の静的3領域の比較を検査。原文検証ワークフローは独自デプロイをせず、重複した先行公開を防ぐ。
- 本スナップショットのローカル元はGitHub cfbda0d4dd6d5cf261bfd7e563941519bc64902e。ユーザーの以前のローカル未反映版は見つからず、確認済みGitHubから継続。
- 開発・運用手順は kaigo-navi2027-preview/README.md。完全無料、ログイン・パスワード不要を引き続き遵守。

- 日次会議一覧更新・週次解説検証からの自動公開も `pages.yml` の共通検査へ固定SHAで渡す。ボットのpushが他ワークフローを起動しない場合でも、検査を迂回して公開しない。

## 2026-10-11 新聞版への変更（ユーザー承認済み）
- ポータルのニュースは `/maiasa-news/` のまま、一般的な話題を読む新聞版へ。介護制度の解説はナビへ案内。採用済みの青い朝刊ヘッダー・スマホ8分類2列×4段・縦スクロールを維持。
- 公式発表（仙台市・宮城県・外務省）の最近1週間と、手動で出典を読んだ6件の地域要点。本文ハッシュが変わった要点はリンクのみへ戻す。有料API/自動AIは使用しない。
- 一般報道・楽天は外部入口。媒体記事・RSSの無断転載は行わない。現時点で全国一般報道を自動要約するサービスではない。詳細は NEWS.md。
- 新聞版の320/360/390/430/1280px検査を共通Pagesゲートに追加。日次ニュースも共通検査の固定SHAだけを公開する。
