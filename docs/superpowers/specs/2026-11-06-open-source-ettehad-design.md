# Design Spec: Open-Sourcing Islam Unity (اوپن سورس کردن اتحاد اسلامی)

**Date**: 2026-11-06
**Author**: Brainstorming session
**Status**: Approved

---

## 1. Overview / خلاصه

Transform the private Ettehad Islamic platform into a world-class open-source project under the name **"Islam Unity"** (اتحاد اسلامی), enabling global contributors to participate in developing an Islamic knowledge and AI platform while maintaining full control over code quality and merge decisions.

پروژه اتحاد اسلامی (Islam Unity) — پلتفرم جامع معارفی و هوش مصنوعی اسلامی — به یک پروژه اوپن سورس جهانی تبدیل می‌شود تا افراد مختلف دنیا بتوانند در توسعه آن مشارکت کنند.

## 2. Goals / اهداف

1. **Community Growth**: Attract global contributors (developers, scholars, translators)
2. **Faster Development**: More hands → more features, faster iteration
3. **Security**: Community code review → higher security confidence
4. **Trust**: Transparent code → trust from all parts of society
5. **Islamic Mission**: Spread Islamic knowledge through collaborative open-source effort

## 3. Architecture / معماری

### 3.1 GitHub Organization

- **Organization name**: `islam-unity-project`
- **Repository name**: `islam-unity`
- **Owner**: @shahryar5sg-prog (sole merge authority on `main`)
- **Teams** (future):
  - `core-maintainers` — full write access
  - `backend-team` — backend issues/PRs
  - `mobile-team` — Flutter issues/PRs
  - `content-team` — Islamic content & translations
  - `ai-team` — AI/RAG features

### 3.2 Repository Structure (Clean)

```
ettehad/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API routes
│   │   ├── core/              # Config, security, response helpers
│   │   ├── db/                # Models, migrations, seeds
│   │   └── admin/             # Admin dashboard (static SPA)
│   ├── tests/                 # Test suite
│   ├── requirements.txt
│   └── Dockerfile
├── flutter_app/               # Flutter mobile application
├── docs/                      # Documentation
│   ├── api/                   # API documentation
│   ├── architecture/          # Architecture diagrams
│   └── contributing/          # Contribution guides
├── .github/                   # GitHub automation
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── content_request.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       ├── ci.yml             # Run tests on PR
│       └── lint.yml           # Code quality checks
├── .env.example               # Environment template (NO real values)
├── .gitignore                 # Comprehensive ignore rules
├── LICENSE                    # GPL-3.0
├── README.md                  # Bilingual (EN + FA)
├── README.fa.md               # Full Persian README
├── CONTRIBUTING.md            # Contribution guidelines (EN + FA)
├── CODE_OF_CONDUCT.md         # Community standards
├── SECURITY.md                # Vulnerability reporting
├── ROADMAP.md                 # Project roadmap
└── CHANGELOG.md               # Version history
```

### 3.3 What Gets Excluded from Open-Source Repo

| Item | Reason |
|------|--------|
| `.env` files with real keys | Security — API keys, SECRET_KEY |
| `ettehad.db` (17MB database) | Contains production user data |
| `*.apk` files (60-68MB) | Binary artifacts, too large |
| `raw_data_books/` | Raw source data, not needed |
| `knowledge_backup/` | Internal backups |
| `error.*.log` files | Runtime logs |
| `benchmark_*.json` | Internal benchmarks |
| `dataset*.jsonl` | Training data |
| `stitch_screens*/` | Internal design screens |
| Agent/tooling files | `.gemini/`, `.agents/`, `teamwork/` |

## 4. License / مجوز

**GPL-3.0-or-later**

Rationale:
- Any derivative work MUST remain open source
- Contributors can't create proprietary forks
- Owner retains control through merge authority (not license restriction)
- Strong copyleft protects the Islamic knowledge mission

## 5. Security Plan / طرح امنیتی

### 5.1 Pre-Launch Checklist

- [ ] Create fresh repository (NO history from unity_V2)
- [ ] Remove ALL hardcoded secrets from codebase
- [ ] Create `.env.example` with placeholder values
- [ ] **ROTATE all existing API keys** (DeepSeek, AvalAI, NVIDIA, TypeSafe)
- [ ] Rotate `SECRET_KEY` in production
- [ ] Verify `.gitignore` covers all sensitive patterns
- [ ] Add `SECURITY.md` with responsible disclosure process
- [ ] Enable GitHub secret scanning on the new repo

### 5.2 Sensitive Items Identified

| File | Contains | Action |
|------|----------|--------|
| `.env` | All API keys, DB URL, SECRET_KEY | Exclude, create `.env.example` |
| `backend/.env` | Same secrets | Exclude |
| `ettehad.db` | User data, content | Exclude |
| `Ketabkhan-Ettehad.apk` | Binary build | Exclude |
| `Ettehad-Islamic-App.apk` | Binary build | Exclude |

## 6. Documentation Plan / مستندات

All documentation is **bilingual** (English primary + Persian).

### 6.1 README.md Structure

```
# اتحاد / Ettehad — Islamic Knowledge & AI Platform

[Persian intro paragraph]
[English intro paragraph]

## ✨ Features / ویژگی‌ها
## 🏗️ Architecture / معماری
## 🚀 Quick Start / شروع سریع
## 📖 Documentation / مستندات
## 🤝 Contributing / مشارکت
## 📋 Roadmap / نقشه راه
## 📜 License / مجوز
## 🌟 Acknowledgments / قدردانی
```

### 6.2 CONTRIBUTING.md Topics

1. How to fork & create a PR
2. Branch naming conventions (`feature/`, `fix/`, `docs/`)
3. Commit message format (Conventional Commits)
4. Code review process (Owner approval required)
5. Areas open for contribution (labels)
6. Setting up local development environment
7. Running tests

### 6.3 Issue Labels

| Label | Color | Description |
|-------|-------|-------------|
| `backend` | blue | FastAPI / Python backend |
| `flutter` | cyan | Flutter mobile app |
| `admin-ui` | purple | Admin dashboard |
| `ai` | orange | AI / RAG features |
| `quran` | green | Quran-related features |
| `hadith` | green | Hadith content |
| `docs` | yellow | Documentation |
| `translation` | yellow | Translation tasks |
| `good-first-issue` | lime | Beginner-friendly |
| `help-wanted` | red | Need help |
| `bug` | red | Bug report |
| `enhancement` | teal | Feature request |
| `security` | black | Security issue |

## 7. Branch Protection / محافظت شاخه

Rules for `main` branch:
- **Require pull request before merging**
- **Require approval from code owner** (Owner only)
- **Require status checks to pass** (CI tests)
- **No direct pushes** (not even Owner — use PRs)
- **Require linear history** (squash merge)

## 8. CI/CD Workflows / خط لوله

### 8.1 `ci.yml` — On every PR

```yaml
- Python lint (ruff/flake8)
- Python tests (pytest)
- Flutter analyze
- Flutter test
```

### 8.2 `lint.yml` — Code quality

```yaml
- Check commit messages (Conventional Commits)
- Check for secrets (git-secrets / trufflehog)
```

## 9. Implementation Steps / مراحل اجرا

### Phase 1: Preparation (This Session)
1. Create all open-source files locally (README, CONTRIBUTING, LICENSE, etc.)
2. Create `.env.example` from `.env` (strip all real values)
3. Create GitHub issue/PR templates
4. Create CI workflow files
5. Review and clean codebase for public consumption

### Phase 2: GitHub Setup (Manual by Owner)
1. Create GitHub Organization `ettehad-project`
2. Create empty public repository `ettehad`
3. Push clean codebase (fresh history)
4. Enable branch protection rules
5. Enable secret scanning
6. Add repository description, topics, and social preview

### Phase 3: Post-Launch
1. Rotate ALL compromised API keys
2. Create initial issues with `good-first-issue` labels
3. Announce on relevant communities
4. Monitor and respond to early contributions

## 10. Files to Create / فایل‌های مورد نیاز

| # | File | Purpose |
|---|------|---------|
| 1 | `LICENSE` | GPL-3.0 full text |
| 2 | `README.md` | Bilingual project intro |
| 3 | `README.fa.md` | Full Persian README |
| 4 | `CONTRIBUTING.md` | Contribution guide |
| 5 | `CODE_OF_CONDUCT.md` | Community standards |
| 6 | `SECURITY.md` | Vulnerability reporting |
| 7 | `ROADMAP.md` | Project roadmap |
| 8 | `CHANGELOG.md` | Version history |
| 9 | `.env.example` | Environment template |
| 10 | `.github/ISSUE_TEMPLATE/bug_report.md` | Bug report template |
| 11 | `.github/ISSUE_TEMPLATE/feature_request.md` | Feature request template |
| 12 | `.github/ISSUE_TEMPLATE/content_request.md` | Content request template |
| 13 | `.github/PULL_REQUEST_TEMPLATE.md` | PR template |
| 14 | `.github/workflows/ci.yml` | CI pipeline |
| 15 | Updated `.gitignore` | Comprehensive exclusions |
