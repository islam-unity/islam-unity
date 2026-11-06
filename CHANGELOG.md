# Changelog | تاریخچه تغییرات

All notable changes to the **Islam Unity** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2024-12-01

### 🎉 Initial Release

The first public release of **Islam Unity** — an open-source Islamic Knowledge & Unity Platform.

### Added

#### 🔧 Backend (FastAPI)
- Async FastAPI backend with **46+ RESTful API endpoints**
- SQLite database with async SQLAlchemy ORM
- JWT-based authentication and authorization system
- Role-based access control (Admin, User, Consultant roles)
- Comprehensive Quran API (surahs, ayahs, search, bookmarks)
- Hadith API with multi-collection support
- Tafsir (Quran interpretation) API with multiple scholarly sources
- Fiqh (Islamic jurisprudence) knowledge base API
- Library management API (books, categories, favorites)
- AI-powered chat API with conversation history
- Consultation system API (request, schedule, manage sessions)
- User profile management and settings API
- Content management and admin APIs
- Prayer times and Qibla direction API
- Notification system API
- CORS configuration for cross-origin requests
- Rate limiting and request validation
- Structured logging and error handling

#### 🖥️ Admin Dashboard
- **Zero-build Vanilla JavaScript** Single Page Application (SPA)
- Full **RTL (Right-to-Left) Persian** interface
- Dashboard with real-time statistics and analytics charts
- User management panel (list, search, edit, activate/deactivate)
- Content management for Quran, Hadith, Tafsir, and Fiqh entries
- Library and book management interface
- Consultation request management and assignment
- AI chat monitoring and configuration panel
- System settings and configuration management
- Responsive design for desktop and tablet
- Chart.js integration for data visualization
- No build tools required — runs directly in the browser

#### 📱 Mobile Application (Flutter)
- Cross-platform Flutter mobile application (Android & iOS)
- **Quran Reader** with surah listing, ayah display, and search
- **Islamic Library** with categorized books and reading progress
- **AI Chat** interface with real-time conversation
- **Consultation System** for scheduling sessions with scholars
- User authentication (login, register, profile management)
- Bookmarks and favorites system
- Offline content caching
- Beautiful RTL Persian UI with Material Design 3
- Dark mode support
- Push notification integration
- Smooth navigation with bottom navigation bar

#### 🤖 AI Integration
- **Multi-provider LLM architecture** supporting:
  - DeepSeek API integration
  - NVIDIA NIM API integration
  - AvalAI API integration
- Intelligent provider fallback mechanism
- Islamic knowledge-focused system prompts
- Conversation context management
- Token usage tracking and optimization
- Configurable model parameters per provider
- Admin-configurable AI settings

#### 📚 Content & Knowledge Base
- **Quran:** Complete Quran text with Persian translation
- **Hadith:** Multi-collection hadith database (Bukhari, Muslim, and more)
- **Tafsir:** Multiple tafsir (interpretation) sources
- **Fiqh:** Islamic jurisprudence knowledge organized by topic
- **Library:** Curated collection of Islamic books and resources
- Content search across all knowledge domains
- Categorization and tagging system

#### 🔐 Security
- JWT token-based authentication
- Password hashing with bcrypt
- Input validation and sanitization
- SQL injection prevention via ORM
- CORS policy enforcement
- Environment-based secrets management

#### 📄 Documentation & Project
- Comprehensive `README.md` with bilingual documentation (English & Persian)
- `CONTRIBUTING.md` guide for new contributors
- `LICENSE` — GNU General Public License v3.0
- `CODE_OF_CONDUCT.md` — Bilingual community guidelines
- `SECURITY.md` — Vulnerability reporting policy
- `.gitignore` configured for Python, Flutter, and IDE files
- Project structure documentation

---

> **بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِیمِ**
>
> This project is dedicated to promoting Islamic knowledge, unity among Muslims,
> and making authentic Islamic resources accessible to everyone.
