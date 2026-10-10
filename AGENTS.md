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
