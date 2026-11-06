/**
 * View 6: AI Interactive Testing Lab, Chats, Pricing & Section Configs
 * Comprehensive AI testing suite with multi-turn conversation memory,
 * dynamic scholar routing, specific book constraining, and real-time memory inspection.
 */

import { ApiClient } from '../api.js';
import { renderTable, formatDateTime, formatNum } from '../components/table.js';
import { Drawer } from '../components/drawer.js';
import { Toast } from '../components/toast.js';

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export function renderAI(container) {
  let activeTab = 'playground'; // 'playground' | 'conversations' | 'logs' | 'pricing' | 'sections'

  let playgroundState = {
    conversationId: null,
    targetBookId: '',
    targetScholarId: '',
    forceScholarEscalation: false,
    department: 'فقه مقارن و تقریب',
    model: '',
    targetLanguage: 'fa',
    options: {
      books: [],
      scholars: [],
      models: [],
      departments: []
    },
    messages: [],
    memoryState: null,
    isLoading: false
  };

  let convState = { page: 1, pageSize: 10, search: '', data: [], meta: null };
  let logsState = { page: 1, pageSize: 10, modelName: '', data: [], meta: null };
  let pricingState = { data: [] };
  let sectionsState = { data: [] };

  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div class="card-title">🤖 سرویس‌های هوش مصنوعی، آزمایشگاه جامع تست و تعرفه‌ها</div>
      </div>
      <div class="card-body">
        <!-- Sub-tabs -->
        <div class="subtabs">
          <button id="tab-ai-playground" class="subtab-btn active">🎮 آزمایشگاه تست هوش مصنوعی (حافظه و هدایت)</button>
          <button id="tab-ai-convs" class="subtab-btn">سشن‌های گفتگوی معارفی</button>
          <button id="tab-ai-logs" class="subtab-btn">لاگ مصرف توکن و هزینه‌ها</button>
          <button id="tab-ai-pricing" class="subtab-btn">تعرفه مدل‌ها (AIModelPricing)</button>
          <button id="tab-ai-sections" class="subtab-btn">پیکربندی دپارتمان‌های هوش مصنوعی</button>
        </div>

        <!-- Tab 1: Interactive Testing Playground -->
        <div id="section-ai-playground">
          <!-- Control Panel -->
          <div class="card" style="margin-bottom: 1rem; background: #ffffff; border: 1px solid var(--border-color);">
            <div style="padding: 1rem; display: flex; flex-direction: column; gap: 0.85rem;">
              <!-- Session Header & Reset -->
              <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; border-bottom: 1px dashed var(--border-color); padding-bottom: 0.75rem;">
                <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
                  <span style="font-weight: 800; font-size: 0.95rem; color: var(--primary);">🧪 شبیه‌ساز مکالمه چندمرحله‌ای با حافظه هوشمند</span>
                  <span id="playground-session-badge" class="badge badge-purple" style="font-family: monospace;">سشن: جدید</span>
                  <span id="playground-turn-badge" class="badge badge-success">حافظه: نوبت ۰ (آماده)</span>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                  <button id="btn-playground-reset" class="btn btn-secondary btn-sm" title="پاکسازی حافظه جلسه و شروع مکالمه جدید">
                    🔄 جلسه جدید (ریست حافظه)
                  </button>
                </div>
              </div>

              <!-- Direct Routing Selectors (Book & Scholar Direction) -->
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 0.75rem;">
                <!-- Target Book -->
                <div>
                  <label style="display: block; font-size: 0.78rem; font-weight: 700; margin-bottom: 0.3rem; color: var(--text-main);">
                    📚 هدایت به کتاب مخصوص (Target Book):
                  </label>
                  <select id="playground-book-select" class="search-input" style="width: 100%; font-size: 0.82rem;">
                    <option value="">🌐 تمام کتب کتابخانه (تشخیص خودکار)</option>
                  </select>
                </div>

                <!-- Target Scholar -->
                <div>
                  <label style="display: block; font-size: 0.78rem; font-weight: 700; margin-bottom: 0.3rem; color: var(--text-main);">
                    🎓 هدایت به عالم و استاد (Target Scholar):
                  </label>
                  <select id="playground-scholar-select" class="search-input" style="width: 100%; font-size: 0.82rem;">
                    <option value="">🤖 تشخیص خودکار بر اساس تخصص سوال</option>
                  </select>
                </div>

                <!-- Department -->
                <div>
                  <label style="display: block; font-size: 0.78rem; font-weight: 700; margin-bottom: 0.3rem; color: var(--text-main);">
                    🏢 دپارتمان معارفی:
                  </label>
                  <select id="playground-dep-select" class="search-input" style="width: 100%; font-size: 0.82rem;">
                    <option value="فقه مقارن و تقریب">فقه مقارن و تقریب مذاهب</option>
                    <option value="تفسیر و تدبر قرآن">تفسیر و تدبر قرآن کریم</option>
                    <option value="کلام و عقاید اسلامی">کلام و عقاید اسلامی</option>
                    <option value="اخلاق و سیره نبوی">اخلاق، تربیت و سیره نبوی</option>
                    <option value="کتاب‌پژوهی هوشمند">کتاب‌پژوهی و ارجاعات متون</option>
                  </select>
                </div>

                <!-- Model Override -->
                <div>
                  <label style="display: block; font-size: 0.78rem; font-weight: 700; margin-bottom: 0.3rem; color: var(--text-main);">
                    ⚙️ مدل پردازشگر (Model):
                  </label>
                  <select id="playground-model-select" class="search-input" style="width: 100%; font-size: 0.82rem;">
                    <option value="">پیش‌فرض سیستم (Gemini 1.5 Pro)</option>
                  </select>
                </div>
              </div>

              <!-- Escalation Toggle Strip -->
              <div style="display: flex; align-items: center; justify-content: space-between; background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 0.5rem 0.85rem; font-size: 0.8rem; flex-wrap: wrap; gap: 0.5rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                  <input type="checkbox" id="playground-force-escalation" style="width: 16px; height: 16px; cursor: pointer;">
                  <label for="playground-force-escalation" style="font-weight: 600; cursor: pointer; color: #92400e;">
                    🚨 شبیه‌سازی شرایط نیاز به ارجاع به عالم (Force Scholar Escalation Test)
                  </label>
                </div>
                <span style="font-size: 0.74rem; color: #b45309;">تست فعال‌سازی خودکار هشدار فقهی و کارت معرفی استاد متخصص</span>
              </div>
            </div>
          </div>

          <!-- Split Workspace: Chat Stream (Left) + Memory & Audit Inspector (Right) -->
          <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1.25rem; align-items: start;">
            <!-- Left: Chat Stream & Message Input -->
            <div class="card" style="margin-bottom: 0;">
              <!-- Quick prompts -->
              <div style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-color); background: #f8fafc;">
                <span style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-bottom: 0.35rem;">
                  💡 سناریوهای آماده جهت آزمون سریع حافظه و هدایت:
                </span>
                <div style="display: flex; flex-wrap: wrap; gap: 0.4rem;">
                  <button type="button" class="btn btn-outline btn-sm quick-test-chip" data-q="آیا با آب قلیلی که با نجاست ملاقات کرده می‌توان تطهیر نمود؟">💧 آب قلیل و کثیر</button>
                  <button type="button" class="btn btn-outline btn-sm quick-test-chip" data-q="حکم سرمایه‌گذاری در بورس و خرید و فروش سهام و ارز دیجیتال چیست؟">📈 بورس و رمزارز (دکتر عابدی)</button>
                  <button type="button" class="btn btn-outline btn-sm quick-test-chip" data-q="دیدگاه فقه شافعی پیرامون مهریه و حقوق زوجه در نکاح">👨‍👩‍👧 فقه شافعی (ماموستا محمدی)</button>
                  <button type="button" class="btn btn-outline btn-sm quick-test-chip" data-q="براهین عقلی اثبات وجود خداوند و توحید ذاتی">🧠 براهین توحید (کشف المراد)</button>
                  <button type="button" class="btn btn-outline btn-sm quick-test-chip" data-q="آداب اخوت اسلامی و پرهیز از تفرقه در نهج‌البلاغه">📖 نهج‌البلاغه و اخوت</button>
                </div>
              </div>

              <!-- Message Stream -->
              <div id="playground-messages" class="chat-container" style="min-height: 480px; max-height: 600px; overflow-y: auto; padding: 1rem; background: #fafafa;">
                <div class="empty-state" id="playground-empty-hint">
                  <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">🤖💬</div>
                  <div class="empty-state-title">آماده تست هوش مصنوعی با حافظه و هدایت به عالم و کتاب</div>
                  <div class="empty-state-subtitle" style="max-width: 480px; margin: 0 auto; line-height: 1.6;">
                    پرسش خود را بنویسید یا روی یکی از سناریوهای بالا کلیک کنید. سیستم مکالمه چندمرحله‌ای را در حافظه سشن نگه داشته و پاسخ‌ها را دقیقاً به کتاب مرجع یا عالم متخصص منتخب هدایت می‌نماید.
                  </div>
                </div>
              </div>

              <!-- Input Area -->
              <div style="padding: 0.85rem 1rem; border-top: 1px solid var(--border-color); background: #ffffff;">
                <div style="display: flex; gap: 0.5rem;">
                  <textarea id="playground-input" class="search-input" style="flex: 1; height: 54px; font-size: 0.88rem; line-height: 1.5; resize: none;" placeholder="پرسش معارفی یا فقهی خود را بنویسید (Enter برای ارسال)..."></textarea>
                  <button id="btn-playground-send" class="btn btn-primary" style="padding: 0 1.25rem; font-weight: 700;">
                    ارسال ↵
                  </button>
                </div>
              </div>
            </div>

            <!-- Right: Memory Inspector & System Audit -->
            <div style="display: flex; flex-direction: column; gap: 1rem;">
              <!-- Short-term Conversation Memory Inspector -->
              <div class="card" style="margin-bottom: 0;">
                <div class="card-header" style="padding: 0.75rem 1rem; background: #f8fafc;">
                  <div class="card-title" style="font-size: 0.88rem; display: flex; align-items: center; gap: 0.4rem;">
                    <span>🧠</span> حافظه کوتاه‌مدت جلسه (Session Memory)
                  </div>
                </div>
                <div class="card-body" style="padding: 0.85rem;">
                  <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem;">
                    نوبت‌های گفتگوی ذخیره شده در سشن که مدل در پاسخ‌های بعدی به خاطر دارد:
                  </div>
                  <div id="inspector-short-memory" style="display: flex; flex-direction: column; gap: 0.5rem; max-height: 250px; overflow-y: auto;">
                    <div style="font-size: 0.78rem; color: var(--text-muted); text-align: center; padding: 1rem;">
                      هنوز نوبتی ثبت نشده است.
                    </div>
                  </div>
                </div>
              </div>

              <!-- Long-term User Memory Profile Inspector -->
              <div class="card" style="margin-bottom: 0;">
                <div class="card-header" style="padding: 0.75rem 1rem; background: #f8fafc;">
                  <div class="card-title" style="font-size: 0.88rem; display: flex; align-items: center; gap: 0.4rem;">
                    <span>👤</span> حافظه بلندمدت و ترجیحات فقهی کاربر
                  </div>
                </div>
                <div class="card-body" style="padding: 0.85rem;">
                  <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem;">
                    اطلاعات به خاطر سپرده شده کاربر (مذهب، زبان، سطح علمی):
                  </div>
                  <div id="inspector-long-memory" style="display: flex; flex-direction: column; gap: 0.4rem;">
                    <span class="badge badge-purple" style="font-size: 0.75rem;">مذهب: پیش‌فرض تقریب فریقین</span>
                    <span class="badge badge-info" style="font-size: 0.75rem;">زبان: فارسی (fa)</span>
                    <span class="badge badge-success" style="font-size: 0.75rem;">سطح تفصیل: استاندارد با استناد</span>
                  </div>
                </div>
              </div>

              <!-- Deduplication / Cited Sources Inspector -->
              <div class="card" style="margin-bottom: 0;">
                <div class="card-header" style="padding: 0.75rem 1rem; background: #f8fafc;">
                  <div class="card-title" style="font-size: 0.88rem; display: flex; align-items: center; gap: 0.4rem;">
                    <span>🛡️</span> پیشگیری از تکرار منابع (Source Deduplication)
                  </div>
                </div>
                <div class="card-body" style="padding: 0.85rem;">
                  <div id="inspector-sources-dedup" style="font-size: 0.75rem; color: var(--text-muted);">
                    هیچ منبعی هنوز استخراج نشده است.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab 2: Conversations Section -->
        <div id="section-ai-convs" style="display: none;">
          <div class="toolbar">
            <div class="toolbar-group">
              <div class="search-input-wrap">
                <span class="search-icon">🔍</span>
                <input id="convs-search" type="text" class="search-input" placeholder="جستجو در عنوان مکالمات هوش مصنوعی...">
              </div>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-convs" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="convs-table-container"></div>
        </div>

        <!-- Tab 3: Usage Logs Section -->
        <div id="section-ai-logs" style="display: none;">
          <div class="toolbar">
            <div class="toolbar-group">
              <div class="search-input-wrap">
                <span class="search-icon">🔍</span>
                <input id="logs-model-filter" type="text" class="search-input" placeholder="فیلتر بر اساس نام مدل (gemini-1.5-pro و ...)">
              </div>
            </div>
            <div class="toolbar-group">
              <button id="btn-refresh-logs" class="btn btn-secondary btn-sm">⟳ تازه‌سازی</button>
            </div>
          </div>
          <div id="logs-table-container"></div>
        </div>

        <!-- Tab 4: Pricing Section -->
        <div id="section-ai-pricing" style="display: none;">
          <div id="pricing-table-container"></div>
        </div>

        <!-- Tab 5: Sections Config Section -->
        <div id="section-ai-sections" style="display: none;">
          <div id="sections-container"></div>
        </div>
      </div>
    </div>
  `;

  // Tab switching
  const tabs = [
    { btn: '#tab-ai-playground', sec: '#section-ai-playground', name: 'playground', load: initPlayground },
    { btn: '#tab-ai-convs', sec: '#section-ai-convs', name: 'conversations', load: fetchConversations },
    { btn: '#tab-ai-logs', sec: '#section-ai-logs', name: 'logs', load: fetchLogs },
    { btn: '#tab-ai-pricing', sec: '#section-ai-pricing', name: 'pricing', load: fetchPricing },
    { btn: '#tab-ai-sections', sec: '#section-ai-sections', name: 'sections', load: fetchSections }
  ];

  tabs.forEach(t => {
    container.querySelector(t.btn).addEventListener('click', () => {
      activeTab = t.name;
      tabs.forEach(o => {
        container.querySelector(o.btn).classList.toggle('active', o.name === activeTab);
        container.querySelector(o.sec).style.display = o.name === activeTab ? 'block' : 'none';
      });
      t.load();
    });
  });

  // =========================================================================
  // Playground Implementation
  // =========================================================================

  async function initPlayground() {
    await fetchPlaygroundOptions();
    bindPlaygroundEvents();
  }

  async function fetchPlaygroundOptions() {
    try {
      const res = await ApiClient.get('/ai/playground/options');
      playgroundState.options = res.data || {};

      // 1. Populate Books
      const bookSelect = container.querySelector('#playground-book-select');
      if (bookSelect) {
        bookSelect.innerHTML = '<option value="">🌐 تمام کتب کتابخانه (تشخیص خودکار)</option>';
        (playgroundState.options.books || []).forEach(b => {
          const opt = document.createElement('option');
          opt.value = b.id;
          opt.textContent = `📖 ${b.title} (${b.author || 'علمای اسلام'})`;
          bookSelect.appendChild(opt);
        });
      }

      // 2. Populate Scholars
      const scholarSelect = container.querySelector('#playground-scholar-select');
      if (scholarSelect) {
        scholarSelect.innerHTML = '<option value="">🤖 تشخیص خودکار بر اساس تخصص سوال</option>';
        (playgroundState.options.scholars || []).forEach(s => {
          const opt = document.createElement('option');
          opt.value = s.id;
          const specs = (s.specialties || []).join('، ');
          opt.textContent = `🎓 ${s.name} (${specs || s.title || ''})`;
          scholarSelect.appendChild(opt);
        });
      }

      // 3. Populate Models
      const modelSelect = container.querySelector('#playground-model-select');
      if (modelSelect) {
        modelSelect.innerHTML = '<option value="">پیش‌فرض سیستم (Gemini 1.5 Pro)</option>';
        (playgroundState.options.models || []).forEach(m => {
          const opt = document.createElement('option');
          opt.value = m;
          opt.textContent = `⚡ ${m}`;
          modelSelect.appendChild(opt);
        });
      }
    } catch (err) {
      console.warn('Failed to load playground options:', err);
    }
  }

  function bindPlaygroundEvents() {
    const bookSelect = container.querySelector('#playground-book-select');
    const scholarSelect = container.querySelector('#playground-scholar-select');
    const depSelect = container.querySelector('#playground-dep-select');
    const modelSelect = container.querySelector('#playground-model-select');
    const forceEscCheck = container.querySelector('#playground-force-escalation');

    bookSelect?.addEventListener('change', (e) => playgroundState.targetBookId = e.target.value);
    scholarSelect?.addEventListener('change', (e) => playgroundState.targetScholarId = e.target.value);
    depSelect?.addEventListener('change', (e) => playgroundState.department = e.target.value);
    modelSelect?.addEventListener('change', (e) => playgroundState.model = e.target.value);
    forceEscCheck?.addEventListener('change', (e) => playgroundState.forceScholarEscalation = e.target.checked);

    // Quick test prompts
    container.querySelectorAll('.quick-test-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        const q = btn.getAttribute('data-q');
        const input = container.querySelector('#playground-input');
        if (input) {
          input.value = q;
          input.focus();
        }
      });
    });

    // Reset Session
    container.querySelector('#btn-playground-reset')?.addEventListener('click', resetPlaygroundSession);

    // Send Button & Enter Key
    container.querySelector('#btn-playground-send')?.addEventListener('click', sendPlaygroundMessage);
    container.querySelector('#playground-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendPlaygroundMessage();
      }
    });
  }

  async function resetPlaygroundSession() {
    try {
      const res = await ApiClient.post('/ai/playground/reset', { title: 'سشن جدید تست هوش مصنوعی' });
      playgroundState.conversationId = res.data?.conversationId || null;
      playgroundState.messages = [];
      playgroundState.memoryState = null;

      container.querySelector('#playground-messages').innerHTML = `
        <div class="empty-state" id="playground-empty-hint">
          <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">🔄</div>
          <div class="empty-state-title">جلسه جدید تست آغاز شد (حافظه ریست گردید)</div>
          <div class="empty-state-subtitle">شناسه سشن فعال: ${playgroundState.conversationId || 'جدید'}</div>
        </div>
      `;

      updateMemoryInspector({
        conversationId: playgroundState.conversationId,
        turnCount: 0,
        shortTermHistory: [],
        longTermMemories: [],
        previousSourceIds: []
      });

      Toast.success('سشن جدید ایجاد شد و حافظه گفتگو ریست گردید.');
    } catch (err) {
      Toast.error(`خطا در ریست سشن: ${err.message}`);
    }
  }

  async function sendPlaygroundMessage() {
    const input = container.querySelector('#playground-input');
    const text = input ? input.value.trim() : '';
    if (!text || playgroundState.isLoading) return;

    playgroundState.isLoading = true;
    input.value = '';
    const sendBtn = container.querySelector('#btn-playground-send');
    if (sendBtn) {
      sendBtn.disabled = true;
      sendBtn.textContent = 'در حال پردازش...';
    }

    // Remove empty hint if present
    const emptyHint = container.querySelector('#playground-empty-hint');
    if (emptyHint) emptyHint.remove();

    const messagesBox = container.querySelector('#playground-messages');

    // Append User Bubble
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble user';
    userBubble.style.cssText = 'max-width: 80%; align-self: flex-start; margin-bottom: 1rem; box-shadow: var(--shadow-sm);';
    userBubble.innerHTML = `
      <div style="font-weight: 700; font-size: 0.78rem; margin-bottom: 0.35rem; color: #1e40af;">👤 پرسش آزمایشی ادمین:</div>
      <div style="line-height: 1.6; font-size: 0.88rem;">${escapeHtml(text)}</div>
      <div class="chat-meta" style="font-size: 0.68rem; color: #60a5fa; margin-top: 0.3rem;">${new Date().toLocaleTimeString('fa-IR')}</div>
    `;
    messagesBox.appendChild(userBubble);

    // Append Typing indicator
    const typingBubble = document.createElement('div');
    typingBubble.className = 'chat-bubble assistant';
    typingBubble.id = 'playground-typing-indicator';
    typingBubble.style.cssText = 'max-width: 60%; align-self: flex-end; margin-bottom: 1rem;';
    typingBubble.innerHTML = `
      <div style="display: flex; align-items: center; gap: 0.5rem;">
        <div class="spinner" style="width: 16px; height: 16px;"></div>
        <span style="font-size: 0.82rem; color: var(--primary);">اتحادیار در حال واکاوی حافظه، استناد و تطبیق...</span>
      </div>
    `;
    messagesBox.appendChild(typingBubble);
    messagesBox.scrollTop = messagesBox.scrollHeight;

    try {
      const payload = {
        conversationId: playgroundState.conversationId,
        message: text,
        targetBookId: playgroundState.targetBookId || null,
        targetScholarId: playgroundState.targetScholarId || null,
        forceScholarEscalation: playgroundState.forceScholarEscalation,
        department: playgroundState.department,
        model: playgroundState.model || null,
        targetLanguage: 'fa'
      };

      const res = await ApiClient.post('/ai/playground/chat', payload);
      const data = res.data;

      playgroundState.conversationId = data.conversationId;
      playgroundState.messages.push({ role: 'user', content: text });
      playgroundState.messages.push(data);

      typingBubble.remove();

      // Render Assistant Bubble
      const aiBubble = document.createElement('div');
      aiBubble.innerHTML = renderPlaygroundAiMessage(data);
      messagesBox.appendChild(aiBubble.firstElementChild);
      messagesBox.scrollTop = messagesBox.scrollHeight;

      // Update Memory Inspector
      if (data.memoryState) {
        updateMemoryInspector(data.memoryState);
      }

      // Bind interactive buttons inside the newly added AI message
      bindAiMessageActions(messagesBox);

    } catch (err) {
      typingBubble.remove();
      const errBubble = document.createElement('div');
      errBubble.className = 'chat-bubble';
      errBubble.style.cssText = 'align-self: flex-end; background: #fee2e2; border: 1px solid #f87171; color: #991b1b;';
      errBubble.innerHTML = `❌ خطا در دریافت پاسخ هوش مصنوعی: ${escapeHtml(err.message)}`;
      messagesBox.appendChild(errBubble);
    } finally {
      playgroundState.isLoading = false;
      if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.textContent = 'ارسال ↵';
      }
    }
  }

  function renderPlaygroundAiMessage(m) {
    const sources = m.sources || [];
    const scholar = m.recommendedScholar;
    const book = m.recommendedBook;
    const escalation = m.suggestScholarEscalation;
    const usage = m.tokenUsage || {};
    const lat = m.latencyBreakdown || {};
    const status = m.aiCapabilityStatus || (scholar ? (book ? 'COMPREHENSIVE' : 'SCHOLAR_ESCALATED') : (book ? 'BOOK_RECOMMENDED' : 'SELF_SUFFICIENT'));
    const routing = m.routingAssessment || {};

    let capabilityBadge = '';
    if (status === 'SELF_SUFFICIENT') {
      capabilityBadge = `<span class="badge badge-success" style="font-size: 0.7rem; font-weight: 700;">⚡ پاسخ مستقل AI</span>`;
    } else if (status === 'SCHOLAR_ESCALATED') {
      capabilityBadge = `<span class="badge badge-warning" style="font-size: 0.7rem; font-weight: 700;">🎓 ارجاع به استاد</span>`;
    } else if (status === 'BOOK_RECOMMENDED') {
      capabilityBadge = `<span class="badge badge-info" style="font-size: 0.7rem; font-weight: 700;">📖 معرفی کتاب</span>`;
    } else if (status === 'COMPREHENSIVE') {
      capabilityBadge = `<span class="badge badge-purple" style="font-size: 0.7rem; font-weight: 700;">📚 استاد + کتاب</span>`;
    }

    return `
      <div class="chat-bubble assistant" style="max-width: 92%; align-self: flex-end; margin-bottom: 1.25rem; box-shadow: var(--shadow-sm); border: 1px solid var(--border-color); background: #ffffff;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.4rem; margin-bottom: 0.6rem; flex-wrap: wrap; gap: 0.4rem;">
          <div style="font-weight: 800; font-size: 0.85rem; color: var(--primary); display: flex; align-items: center; gap: 0.4rem;">
            <span>🤖</span>
            <span>اتحادیار هوشمند</span>
            <span style="font-size: 0.72rem; color: var(--text-muted); font-weight: normal;">(${playgroundState.department})</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.4rem;">
            ${capabilityBadge}
            <span class="badge badge-purple" style="font-size: 0.72rem;">${usage.model_name || usage.modelName || 'Gemini'}</span>
          </div>
        </div>

        <!-- Main Answer Content -->
        <div style="line-height: 1.8; font-size: 0.88rem; color: var(--text-main); white-space: pre-wrap; margin-bottom: 0.75rem;">${escapeHtml(m.reply || m.content || '')}</div>

        <!-- Self-Sufficient AI Banner (If no scholar & no book needed) -->
        ${status === 'SELF_SUFFICIENT' ? `
          <div style="margin-top: 0.5rem; background: #f0fdf4; border: 1px dashed #86efac; border-radius: 8px; padding: 0.45rem 0.75rem; font-size: 0.76rem; color: #166534; display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;">
            <div style="display: flex; align-items: center; gap: 0.4rem;">
              <span>⚡</span>
              <strong>تشخیص هوشمند:</strong>
              <span>${escapeHtml(routing.reasoning || 'هوش مصنوعی در توانایی پاسخگویی مستقل بوده و نیازی به ارجاع به عالم یا تحمیل کتاب وجود نداشت.')}</span>
            </div>
            <span class="badge badge-success" style="font-size: 0.68rem;">خودبسنده ✓</span>
          </div>
        ` : ''}

        <!-- Scholar Recommendation Card -->
        ${scholar ? `
          <div class="scholar-recommendation-card" style="margin-top: 0.75rem; background: linear-gradient(135deg, #fffbeb, #fef3c7); border: 1px solid #f59e0b; border-radius: 10px; padding: 0.75rem; display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <div style="font-size: 1.8rem; background: #ffffff; border-radius: 50%; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 4px rgba(0,0,0,0.06);">🎓</div>
              <div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                  <span style="font-weight: 800; font-size: 0.88rem; color: #78350f;">هدایت به استاد متخصص: ${escapeHtml(scholar.name)}</span>
                  ${scholar.rating ? `<span class="badge badge-warning" style="font-size: 0.7rem;">⭐ ${scholar.rating}</span>` : ''}
                </div>
                <div style="font-size: 0.76rem; color: #92400e; margin-top: 0.15rem;">${escapeHtml(scholar.title || '')}</div>
                <div style="font-size: 0.74rem; color: #b45309; margin-top: 0.25rem; font-style: italic;">💡 ${escapeHtml(scholar.matchReason || scholar.match_reason || 'متناسب با زمینه سوال')}</div>
              </div>
            </div>
            <button class="btn btn-sm btn-primary btn-test-scholar-chat" data-scholar-id="${scholar.id}" data-scholar-name="${escapeHtml(scholar.name)}" data-scholar-title="${escapeHtml(scholar.title || '')}" data-scholar-specs="${escapeHtml((scholar.specialties || []).join('، '))}" style="font-size: 0.75rem; padding: 0.35rem 0.75rem;">
              💬 تست شبیه‌سازی مشاوره
            </button>
          </div>
        ` : ''}

        <!-- Book Recommendation Card -->
        ${book ? `
          <div class="book-recommendation-card" style="margin-top: 0.75rem; background: linear-gradient(135deg, #f0fdf4, #dcfce7); border: 1px solid #10b981; border-radius: 10px; padding: 0.75rem; display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <div style="font-size: 1.8rem; background: #ffffff; border-radius: 50%; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 4px rgba(0,0,0,0.06);">📖</div>
              <div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                  <span style="font-weight: 800; font-size: 0.88rem; color: #064e3b;">هدایت به کتاب مرجع: «${escapeHtml(book.title)}»</span>
                  <span class="badge badge-success" style="font-size: 0.7rem;">${escapeHtml(book.categoryTitle || 'کتابخانه')}</span>
                </div>
                <div style="font-size: 0.76rem; color: #047857; margin-top: 0.15rem;">مؤلف: ${escapeHtml(book.author || 'علمای اسلام')}</div>
                <div style="font-size: 0.74rem; color: #065f46; margin-top: 0.25rem; font-style: italic;">📌 ${escapeHtml(book.matchReason || book.match_reason || 'منبع اصلی استناد')}</div>
              </div>
            </div>
            <button class="btn btn-sm btn-outline btn-test-open-book" data-book-id="${book.id}" data-book-title="${escapeHtml(book.title)}" data-book-author="${escapeHtml(book.author || '')}" style="font-size: 0.75rem; padding: 0.35rem 0.75rem; border-color: #059669; color: #059669;">
              🔍 بررسی کتاب در کتابخوان
            </button>
          </div>
        ` : ''}

        <!-- Escalation Warning Alert -->
        ${escalation ? `
          <div style="margin-top: 0.65rem; background: #fef2f2; border: 1px solid #f87171; color: #991b1b; padding: 0.5rem 0.75rem; border-radius: 8px; font-size: 0.78rem; display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.1rem;">🚨</span>
            <div>
              <strong>نیاز به ارجاع به عالم و استاد فقهی (${escapeHtml(m.escalationCategory || 'احکام شرعی')}):</strong>
              <span>این موضوع به دلیل پیچیدگی اجتهادی یا مستحدثه بودن، به بخش مشاوره معارفی ارجاع گردید.</span>
            </div>
          </div>
        ` : ''}

        <!-- RAG Sources Accordion -->
        ${sources.length ? `
          <div style="margin-top: 0.75rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.6rem 0.85rem;">
            <div style="font-weight: 700; font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 0.4rem; display: flex; justify-content: space-between;">
              <span>📚 منابع RAG استخراج‌شده (${sources.length} منبع):</span>
              <span style="font-weight: normal; font-size: 0.72rem; color: var(--primary);">استناد داده شده ✓</span>
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.35rem;">
              ${sources.map((s, idx) => `
                <div style="font-size: 0.76rem; background: #ffffff; padding: 0.4rem 0.6rem; border-radius: 6px; border: 1px solid #f1f5f9;">
                  <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: var(--primary);">[${idx + 1}] ${escapeHtml(s.title || '')}</strong>
                    ${s.score ? `<span style="font-size: 0.7rem; color: var(--text-muted);">شباهت: ${(s.score * 100).toFixed(1)}%</span>` : ''}
                  </div>
                  ${s.excerpt ? `<div style="font-size: 0.73rem; color: var(--text-secondary); margin-top: 0.2rem; line-height: 1.5;">${escapeHtml(s.excerpt.slice(0, 160))}...</div>` : ''}
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- Performance Audit Footer -->
        <div class="chat-meta" style="margin-top: 0.75rem; padding-top: 0.4rem; border-top: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.4rem;">
          <div style="display: flex; gap: 0.75rem;">
            ${usage.total_tokens || usage.totalTokens ? `<span>🔢 <strong>${formatNum(usage.total_tokens || usage.totalTokens)}</strong> توکن</span>` : ''}
            ${usage.cost_usd || usage.costUsd ? `<span>💵 $${(usage.cost_usd || usage.costUsd).toFixed(5)}</span>` : ''}
            ${usage.cost_irr || usage.costIrr ? `<span>(${formatNum(Math.round(usage.cost_irr || usage.costIrr))} ریال)</span>` : ''}
          </div>
          <div>
            ${lat.total_latency_ms ? `<span>⏱️ زمان کل: <strong>${lat.total_latency_ms}ms</strong></span>` : ''}
            ${lat.search_retrieval_ms ? `<span style="color: var(--text-muted); font-size: 0.68rem;">(بازیابی: ${lat.search_retrieval_ms}ms | مدل: ${lat.llm_generation_ms || 0}ms)</span>` : ''}
          </div>
        </div>
      </div>
    `;
  }

  function bindAiMessageActions(containerEl) {
    // Scholar Consultation Simulation Modal
    containerEl.querySelectorAll('.btn-test-scholar-chat').forEach(btn => {
      btn.onclick = () => {
        const id = btn.getAttribute('data-scholar-id');
        const name = btn.getAttribute('data-scholar-name');
        const title = btn.getAttribute('data-scholar-title');
        const specs = btn.getAttribute('data-scholar-specs');

        Drawer.open({
          title: `شبیه‌ساز هدایت به عالم: ${name}`,
          subtitle: `تخصص: ${specs}`,
          contentHtml: `
            <div class="detail-section">
              <div class="detail-section-title">🎓 مشخصات استاد و ارجاع مشاوره</div>
              <div style="line-height: 1.8; font-size: 0.85rem; margin-bottom: 1rem;">
                <div><strong>نام استاد:</strong> ${name}</div>
                <div><strong>مرتبه علمی:</strong> ${title}</div>
                <div><strong>حوزه‌های تخصصی:</strong> ${specs}</div>
                <div style="margin-top: 0.5rem; background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; padding: 0.5rem; border-radius: 6px;">
                  ℹ️ هوش مصنوعی به درستی تشخیص داد که پاسخ قطعی این پرسش نیازمند ارجاع به استاد <strong>${name}</strong> است. کاربر در اپلیکیشن موبایل با یک کلیک به کارتابل پیام این استاد متصل می‌شود.
                </div>
              </div>
            </div>
          `,
          footerHtml: `<button class="btn btn-secondary" onclick="document.getElementById('drawer-close-btn').click()">بستن</button>`
        });
      };
    });

    // Book Viewer Modal
    containerEl.querySelectorAll('.btn-test-open-book').forEach(btn => {
      btn.onclick = () => {
        const id = btn.getAttribute('data-book-id');
        const title = btn.getAttribute('data-book-title');
        const author = btn.getAttribute('data-book-author');

        Drawer.open({
          title: `هدایت به کتاب مرجع: ${title}`,
          subtitle: `مؤلف: ${author}`,
          contentHtml: `
            <div class="detail-section">
              <div class="detail-section-title">📖 مشخصات منبع در کتابخانه</div>
              <div style="line-height: 1.8; font-size: 0.85rem; margin-bottom: 1rem;">
                <div><strong>عنوان کتاب:</strong> ${title}</div>
                <div><strong>مؤلف:</strong> ${author}</div>
                <div><strong>شناسه سیستمی:</strong> <code>${id}</code></div>
                <div style="margin-top: 0.5rem; background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; padding: 0.5rem; border-radius: 6px;">
                  ✅ پیوند معارفی فعال: سیستم هوش مصنوعی چانک‌های این کتاب را استخراج و کاربر را به مطالعه متن کامل در بخش کتابخوان هدایت کرد.
                </div>
              </div>
            </div>
          `,
          footerHtml: `<button class="btn btn-secondary" onclick="document.getElementById('drawer-close-btn').click()">بستن</button>`
        });
      };
    });
  }

  function updateMemoryInspector(mem) {
    if (!mem) return;

    // Badges update
    const sessionBadge = container.querySelector('#playground-session-badge');
    if (sessionBadge) {
      sessionBadge.textContent = `سشن: ${mem.conversationId ? mem.conversationId.slice(0, 12) + '...' : 'جدید'}`;
    }
    const turnBadge = container.querySelector('#playground-turn-badge');
    if (turnBadge) {
      turnBadge.textContent = `حافظه: نوبت ${mem.turnCount || 0} (فعال ✓)`;
    }

    // Short-term History list
    const shortBox = container.querySelector('#inspector-short-memory');
    if (shortBox) {
      const history = mem.shortTermHistory || [];
      if (history.length === 0) {
        shortBox.innerHTML = '<div style="font-size: 0.78rem; color: var(--text-muted); text-align: center; padding: 0.75rem;">هنوز پیامی در حافظه سشن نیست.</div>';
      } else {
        shortBox.innerHTML = history.map((h, idx) => `
          <div style="background: ${h.role === 'user' ? '#eff6ff' : '#f0fdf4'}; border: 1px solid ${h.role === 'user' ? '#bfdbfe' : '#bbf7d0'}; border-radius: 6px; padding: 0.4rem 0.6rem; font-size: 0.76rem;">
            <div style="font-weight: 700; color: ${h.role === 'user' ? '#1e40af' : '#166534'}; margin-bottom: 0.15rem;">
              ${h.role === 'user' ? '👤 پرسش کاربر' : '🤖 پاسخ دستیار'} [ردیف ${idx + 1}]
            </div>
            <div style="color: var(--text-secondary); line-height: 1.4;">${escapeHtml((h.content || '').slice(0, 90))}...</div>
          </div>
        `).join('');
      }
    }

    // Long-term Memories
    const longBox = container.querySelector('#inspector-long-memory');
    if (longBox) {
      const longMems = mem.longTermMemories || [];
      if (longMems.length === 0) {
        longBox.innerHTML = `
          <span class="badge badge-purple" style="font-size: 0.75rem;">مذهب: فقه مقارن و تقریب</span>
          <span class="badge badge-info" style="font-size: 0.75rem;">زبان: فارسی (fa)</span>
          <span class="badge badge-success" style="font-size: 0.75rem;">سطح: استاندارد</span>
        `;
      } else {
        longBox.innerHTML = longMems.map(m => `
          <div style="background: #fdf4ff; border: 1px solid #f5d0fe; color: #86198f; padding: 0.35rem 0.5rem; border-radius: 6px; font-size: 0.75rem; display: flex; justify-content: space-between;">
            <strong>${escapeHtml(m.key)}:</strong>
            <span>${escapeHtml(m.value)}</span>
          </div>
        `).join('');
      }
    }

    // Deduplication sources
    const dedupBox = container.querySelector('#inspector-sources-dedup');
    if (dedupBox) {
      const srcIds = mem.previousSourceIds || [];
      if (srcIds.length === 0) {
        dedupBox.innerHTML = '<div style="font-size: 0.75rem; color: var(--text-muted);">هیچ منبعی در نوبت‌های قبلی قفل نشده است.</div>';
      } else {
        dedupBox.innerHTML = `
          <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.3rem;">
            تعداد منابع در حافظه ضدتکرار: <strong>${srcIds.length}</strong>
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 0.25rem;">
            ${srcIds.map(sid => `<span class="badge badge-gray" style="font-family: monospace; font-size: 0.68rem;">${escapeHtml(sid.slice(0, 16))}</span>`).join('')}
          </div>
        `;
      }
    }
  }

  // =========================================================================
  // Existing Tabs: Conversations, Logs, Pricing, Sections
  // =========================================================================

  // Conversations Search
  let convSearchTimeout = null;
  container.querySelector('#convs-search')?.addEventListener('input', (e) => {
    clearTimeout(convSearchTimeout);
    convSearchTimeout = setTimeout(() => {
      convState.search = e.target.value.trim();
      convState.page = 1;
      fetchConversations();
    }, 300);
  });
  container.querySelector('#btn-refresh-convs')?.addEventListener('click', fetchConversations);

  // Logs Search
  let logsSearchTimeout = null;
  container.querySelector('#logs-model-filter')?.addEventListener('input', (e) => {
    clearTimeout(logsSearchTimeout);
    logsSearchTimeout = setTimeout(() => {
      logsState.modelName = e.target.value.trim();
      logsState.page = 1;
      fetchLogs();
    }, 300);
  });
  container.querySelector('#btn-refresh-logs')?.addEventListener('click', fetchLogs);

  // Conversations Columns
  const convColumns = [
    {
      header: 'عنوان سشن گفتگو',
      render: (c) => `
        <div>
          <div style="font-weight: 700;">${c.title || 'مکالمه بدون عنوان'}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace;">شناسه: ${c.id}</div>
        </div>
      `
    },
    {
      header: 'شناسه کاربر',
      render: (c) => `<span style="font-family: monospace;">${c.userId || c.user_id}</span>`
    },
    {
      header: 'آخرین به‌روزرسانی',
      render: (c) => formatDateTime(c.updatedAt || c.updated_at || c.createdAt || c.created_at)
    },
    {
      header: 'عملیات',
      style: 'text-align: left;',
      render: (c) => `
        <button class="btn btn-primary btn-sm btn-view-conv" data-conv-id="${c.id}" data-conv-title="${c.title || ''}">
          💬 مشاهده چت
        </button>
      `
    }
  ];

  async function fetchConversations() {
    renderTable({
      container: container.querySelector('#convs-table-container'),
      columns: convColumns,
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/ai/conversations', {
        page: convState.page,
        pageSize: convState.pageSize,
        search: convState.search
      });
      convState.data = res.data || [];
      convState.meta = res.meta;

      renderTable({
        container: container.querySelector('#convs-table-container'),
        columns: convColumns,
        data: convState.data,
        meta: convState.meta,
        currentPage: convState.page,
        pageSize: convState.pageSize,
        emptyMessage: 'سشن گفتگویی یافت نشد.',
        onPageChange: (p) => { convState.page = p; fetchConversations(); },
        onPageSizeChange: (s) => { convState.pageSize = s; convState.page = 1; fetchConversations(); }
      });

      // View Conversation Drawer
      container.querySelectorAll('.btn-view-conv').forEach(btn => {
        btn.addEventListener('click', () => {
          const id = btn.getAttribute('data-conv-id');
          const title = btn.getAttribute('data-conv-title');
          openConversationDrawer(id, title);
        });
      });
    } catch (err) {
      container.querySelector('#convs-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا: ${err.message}</div></div>
      `;
    }
  }

  async function openConversationDrawer(convId, convTitle) {
    Drawer.open({
      title: `تاریخچه سشن: ${convTitle}`,
      subtitle: `در حال دریافت پیام‌های گفتگو...`,
      contentHtml: '<div class="loading-container"><div class="spinner"></div></div>'
    });

    try {
      const [msgRes, traceRes] = await Promise.allSettled([
        ApiClient.get(`/ai/conversations/${convId}/messages`),
        ApiClient.get(`/ai/conversations/${convId}/traces`)
      ]);

      const messages = (msgRes.status === 'fulfilled' && msgRes.value.data) ? msgRes.value.data : [];
      const traces = (traceRes.status === 'fulfilled' && traceRes.value.data) ? traceRes.value.data : [];

      let contentHtml = messages.length === 0
        ? '<div class="empty-state"><div class="empty-state-title">پیامی در این سشن یافت نشد.</div></div>'
        : `
          <div class="chat-container" style="max-height: 550px;">
            ${messages.map(m => {
              const isUser = m.role === 'user' || m.role === 'USER';
              const sources = m.sources || [];
              const usage = m.tokenUsage || m.token_usage || {};
              const escalation = m.suggestScholarEscalation ?? m.suggest_scholar_escalation;

              return `
                <div class="chat-bubble ${isUser ? 'user' : 'assistant'}">
                  <div style="font-weight: 700; font-size: 0.75rem; margin-bottom: 0.35rem;">
                    ${isUser ? '👤 پرسش کاربر' : '🤖 دستیار هوشمند اتحاد'}
                  </div>
                  <div style="line-height: 1.7;">${escapeHtml(m.content || '')}</div>

                  ${escalation ? `
                    <div style="margin-top: 0.5rem; background: #fee2e2; border: 1px solid #f87171; color: #991b1b; padding: 0.4rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600;">
                      🚨 نیاز به ارجاع به عالم فقهی (${escapeHtml(m.escalationCategory || m.escalation_category || 'عمومی')})
                    </div>
                  ` : ''}

                  ${sources.length ? `
                    <div style="margin-top: 0.5rem; background: rgba(0,0,0,0.04); padding: 0.4rem; border-radius: 6px; font-size: 0.75rem;">
                      <strong>منابع RAG استخراج‌شده:</strong>
                      <ul style="padding-right: 1rem; margin-top: 0.2rem;">
                        ${sources.map(s => `<li>${typeof s === 'string' ? escapeHtml(s) : escapeHtml(s.title || JSON.stringify(s))}</li>`).join('')}
                      </ul>
                    </div>
                  ` : ''}

                  <div class="chat-meta" style="display: flex; justify-content: space-between;">
                    <span>${formatDateTime(m.createdAt || m.created_at)}</span>
                    ${usage.total_tokens ? `<span>${formatNum(usage.total_tokens)} توکن</span>` : ''}
                  </div>
                </div>
              `;
            }).join('')}
          </div>

          ${traces && traces.length > 0 ? `
            <div class="detail-section" style="margin-top: 1.25rem;">
              <div class="detail-section-title">🔍 ردگیری‌های ایجنت هوشمند (${formatNum(traces.length)} ران)</div>
              <div style="display: flex; flex-direction: column; gap: 0.65rem;">
                ${traces.map((t, idx) => `
                  <div style="background: var(--bg-body); border: 1px solid var(--border-color); border-radius: 6px; padding: 0.65rem; font-size: 0.8rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; font-weight: 700; margin-bottom: 0.25rem;">
                      <span>[${idx + 1}] پرسش: "${escapeHtml(t.userQuery || '—')}"</span>
                      <span class="badge badge-info">⏱ ${formatNum(t.totalLatencyMs || 0)}ms</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.35rem;">
                      حالت: ${t.mode || 'RAG'} | توکن‌ها: ${formatNum(t.totalTokens || 0)} | هزینه تخمینی: $${t.estimatedCostUsd || '0.00'}
                    </div>
                    ${t.plan ? `
                      <div style="background: #ffffff; border: 1px solid var(--border-color); border-radius: 4px; padding: 0.4rem; font-size: 0.75rem; color: var(--text-secondary); line-height: 1.5;">
                        <strong>برنامه ایجنت:</strong> ${typeof t.plan === 'object' ? escapeHtml(JSON.stringify(t.plan)) : escapeHtml(t.plan)}
                      </div>
                    ` : ''}
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        `;

      Drawer.open({
        title: `گفتگو: ${convTitle || 'سشن ' + convId}`,
        subtitle: `تعداد کل پیام‌ها: ${formatNum(messages.length)}`,
        contentHtml,
        footerHtml: `<button class="btn btn-secondary" onclick="document.getElementById('drawer-close-btn').click()">بستن</button>`
      });
    } catch (err) {
      Drawer.setContent(`<div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت پیام‌ها: ${err.message}</div></div>`);
    }
  }

  // Logs Columns
  const logColumns = [
    {
      header: 'مدل پردازشگر',
      render: (l) => `<span class="badge badge-purple">${l.modelName || l.model_name || 'Gemini'}</span>`
    },
    {
      header: 'توکن پرامپت',
      render: (l) => formatNum(l.promptTokens ?? l.prompt_tokens ?? 0)
    },
    {
      header: 'توکن خروجی',
      render: (l) => formatNum(l.outputTokens ?? l.output_tokens ?? 0)
    },
    {
      header: 'مجموع توکن',
      render: (l) => `<span style="font-weight: 700;">${formatNum(l.totalTokens ?? l.total_tokens ?? 0)}</span>`
    },
    {
      header: 'هزینه (USD / IRR)',
      render: (l) => {
        const usd = (l.costUsd ?? l.cost_usd ?? 0).toFixed(6);
        const irr = formatNum(Math.round(l.costIrr ?? l.cost_irr ?? 0));
        return `<div><div>$${usd}</div><div style="font-size: 0.75rem; color: var(--text-muted);">${irr} ریال</div></div>`;
      }
    },
    {
      header: 'زمان ثبت',
      render: (l) => `<span style="font-size: 0.78rem;">${formatDateTime(l.createdAt || l.created_at)}</span>`
    }
  ];

  async function fetchLogs() {
    renderTable({
      container: container.querySelector('#logs-table-container'),
      columns: logColumns,
      data: [],
      isLoading: true
    });

    try {
      const params = {
        page: logsState.page,
        pageSize: logsState.pageSize
      };
      if (logsState.modelName) params.model_name = logsState.modelName;

      const res = await ApiClient.get('/ai/usage-logs', params);
      logsState.data = res.data || [];
      logsState.meta = res.meta;

      renderTable({
        container: container.querySelector('#logs-table-container'),
        columns: logColumns,
        data: logsState.data,
        meta: logsState.meta,
        currentPage: logsState.page,
        pageSize: logsState.pageSize,
        emptyMessage: 'لاگ مصرف توکنی یافت نشد.',
        onPageChange: (p) => { logsState.page = p; fetchLogs(); },
        onPageSizeChange: (s) => { logsState.pageSize = s; logsState.page = 1; fetchLogs(); }
      });
    } catch (err) {
      container.querySelector('#logs-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت لاگ‌ها: ${err.message}</div></div>
      `;
    }
  }

  // Model Pricing Columns
  const pricingColumns = [
    {
      header: 'نام مدل',
      render: (p) => `<span style="font-weight: 700; font-family: monospace;">${p.modelName || p.model_name}</span>`
    },
    {
      header: 'هزینه ورودی (هر ۱M توکن)',
      render: (p) => `$${Number(p.inputCostPerMillionUsd ?? p.input_cost_per_million_usd ?? 0).toFixed(3)}`
    },
    {
      header: 'هزینه خروجی (هر ۱M توکن)',
      render: (p) => `$${Number(p.outputCostPerMillionUsd ?? p.output_cost_per_million_usd ?? 0).toFixed(3)}`
    },
    {
      header: 'هزینه کش‌شده (هر ۱M توکن)',
      render: (p) => `$${Number(p.cachedCostPerMillionUsd ?? p.cached_cost_per_million_usd ?? 0).toFixed(3)}`
    },
    {
      header: 'وضعیت مدل',
      render: (p) => (p.isActive ?? p.is_active)
        ? `<span class="badge badge-success">فعال ✓</span>`
        : `<span class="badge badge-danger">غیرفعال</span>`
    },
    {
      header: 'عملیات',
      style: 'text-align: left;',
      render: (p, idx) => `
        <button class="btn btn-outline btn-sm btn-edit-pricing" data-pricing-idx="${idx}">
          ✏️ ویرایش تعرفه
        </button>
      `
    }
  ];

  async function fetchPricing() {
    renderTable({
      container: container.querySelector('#pricing-table-container'),
      columns: pricingColumns,
      data: [],
      isLoading: true
    });

    try {
      const res = await ApiClient.get('/ai/model-pricing');
      pricingState.data = res.data || [];

      renderTable({
        container: container.querySelector('#pricing-table-container'),
        columns: pricingColumns,
        data: pricingState.data,
        emptyMessage: 'تعرفه‌ای ثبت نشده است.'
      });

      // Edit Pricing Drawer
      container.querySelectorAll('.btn-edit-pricing').forEach(btn => {
        btn.addEventListener('click', () => {
          const idx = Number(btn.getAttribute('data-pricing-idx'));
          const p = pricingState.data[idx];
          if (!p) return;

          Drawer.open({
            title: `ویرایش تعرفه: ${p.modelName || p.model_name}`,
            subtitle: `شناسه تعرفه: ${p.id}`,
            contentHtml: `
              <div class="detail-section">
                <div class="detail-section-title">💲 نرخ مصرف توکن بر حسب دلار (USD)</div>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                  <div>
                    <label class="detail-label" style="display: block; margin-bottom: 0.25rem;">هزینه ورودی هر ۱ میلیون توکن ($):</label>
                    <input id="edit-pricing-input" type="number" step="0.001" class="search-input" value="${p.inputCostPerMillionUsd ?? p.input_cost_per_million_usd ?? 0}">
                  </div>
                  <div>
                    <label class="detail-label" style="display: block; margin-bottom: 0.25rem;">هزینه خروجی هر ۱ میلیون توکن ($):</label>
                    <input id="edit-pricing-output" type="number" step="0.001" class="search-input" value="${p.outputCostPerMillionUsd ?? p.output_cost_per_million_usd ?? 0}">
                  </div>
                  <div>
                    <label class="detail-label" style="display: block; margin-bottom: 0.25rem;">هزینه کش‌شده هر ۱ میلیون توکن ($):</label>
                    <input id="edit-pricing-cached" type="number" step="0.001" class="search-input" value="${p.cachedCostPerMillionUsd ?? p.cached_cost_per_million_usd ?? 0}">
                  </div>
                  <div style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.5rem;">
                    <input id="edit-pricing-active" type="checkbox" ${(p.isActive ?? p.is_active) ? 'checked' : ''} style="width: 18px; height: 18px;">
                    <label for="edit-pricing-active" style="font-weight: 600;">مدل فعال و در دسترس باشد</label>
                  </div>
                </div>
              </div>
            `,
            footerHtml: `
              <button class="btn btn-secondary" onclick="document.getElementById('drawer-close-btn').click()">انصراف</button>
              <button id="btn-save-pricing" class="btn btn-primary">ذخیره تعرفه</button>
            `
          });

          document.getElementById('btn-save-pricing').addEventListener('click', async () => {
            const saveBtn = document.getElementById('btn-save-pricing');
            saveBtn.classList.add('loading');
            saveBtn.disabled = true;

            try {
              const body = {
                input_cost_per_million_usd: parseFloat(document.getElementById('edit-pricing-input').value),
                output_cost_per_million_usd: parseFloat(document.getElementById('edit-pricing-output').value),
                cached_cost_per_million_usd: parseFloat(document.getElementById('edit-pricing-cached').value),
                is_active: document.getElementById('edit-pricing-active').checked
              };

              await ApiClient.put(`/ai/model-pricing/${p.id}`, body);
              Toast.success('تعرفه مدل هوش مصنوعی با موفقیت ذخیره شد.');
              Drawer.close();
              fetchPricing();
            } finally {
              saveBtn.classList.remove('loading');
              saveBtn.disabled = false;
            }
          });
        });
      });
    } catch (err) {
      container.querySelector('#pricing-table-container').innerHTML = `
        <div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت تعرفه‌ها: ${err.message}</div></div>
      `;
    }
  }

  // Sections Config
  async function fetchSections() {
    const secContainer = container.querySelector('#sections-container');
    secContainer.innerHTML = '<div class="loading-container"><div class="spinner"></div></div>';

    try {
      const res = await ApiClient.get('/ai/sections');
      sectionsState.data = res.data || [];

      secContainer.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.25rem;">
          ${sectionsState.data.map(sec => `
            <div class="card" style="margin-bottom: 0;">
              <div class="card-header" style="background: #f8fafc;">
                <div>
                  <div class="card-title" style="font-size: 0.95rem;">${sec.sectionNameFa || sec.section_name_fa || sec.sectionKey}</div>
                  <div style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace;">کلید: ${sec.sectionKey || sec.section_key}</div>
                </div>
                <span class="badge ${(sec.isActive ?? sec.is_active) ? 'badge-success' : 'badge-danger'}">
                  ${(sec.isActive ?? sec.is_active) ? 'فعال' : 'غیرفعال'}
                </span>
              </div>
              <div class="card-body">
                <div style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 0.75rem; min-height: 38px;">
                  ${sec.descriptionFa || sec.description_fa || 'بدون توضیح'}
                </div>
                <div class="detail-section" style="padding: 0.65rem; margin-bottom: 0.75rem;">
                  <div class="detail-row">
                    <span class="detail-label">مدل فعال:</span>
                    <span class="detail-value" style="font-family: monospace;">${sec.modelName || sec.model_name || '—'}</span>
                  </div>
                  <div class="detail-row">
                    <span class="detail-label">سرویس‌دهنده:</span>
                    <span class="detail-value">${sec.provider || 'Gemini'}</span>
                  </div>
                </div>
                <button class="btn btn-outline btn-sm btn-edit-section" data-section-key="${sec.sectionKey || sec.section_key}" style="width: 100%;">
                  ⚙️ ویرایش پیکربندی بخش
                </button>
              </div>
            </div>
          `).join('')}
        </div>
      `;

      // Edit section handler
      secContainer.querySelectorAll('.btn-edit-section').forEach(btn => {
        btn.addEventListener('click', () => {
          const key = btn.getAttribute('data-section-key');
          const sec = sectionsState.data.find(x => (x.sectionKey || x.section_key) === key);
          if (!sec) return;

          Drawer.open({
            title: `پیکربندی بخش: ${sec.sectionNameFa || sec.section_name_fa}`,
            subtitle: `کلید سیستمی: ${key}`,
            contentHtml: `
              <div class="detail-section">
                <div class="detail-section-title">⚙️ مشخصات مدل و کلید ارتباطی</div>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                  <div>
                    <label class="detail-label" style="display: block; margin-bottom: 0.25rem;">نام مدل پردازشگر:</label>
                    <input id="edit-sec-model" type="text" class="search-input" value="${sec.modelName || sec.model_name || ''}">
                  </div>
                  <div>
                    <label class="detail-label" style="display: block; margin-bottom: 0.25rem;">سرویس‌دهنده (Provider):</label>
                    <input id="edit-sec-provider" type="text" class="search-input" value="${sec.provider || 'gemini'}">
                  </div>
                  <div>
                    <label class="detail-label" style="display: block; margin-bottom: 0.25rem;">Base URL:</label>
                    <input id="edit-sec-base-url" type="text" class="search-input" value="${sec.baseUrl || sec.base_url || ''}">
                  </div>
                  <div>
                    <label class="detail-label" style="display: block; margin-bottom: 0.25rem;">API Key:</label>
                    <input id="edit-sec-api-key" type="password" class="search-input" placeholder="کلید محرمانه (بدون تغییر باقی می‌ماند)">
                  </div>
                  <div style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.5rem;">
                    <input id="edit-sec-active" type="checkbox" ${(sec.isActive ?? sec.is_active) ? 'checked' : ''} style="width: 18px; height: 18px;">
                    <label for="edit-sec-active" style="font-weight: 600;">این بخش در سامانه فعال باشد</label>
                  </div>
                </div>
              </div>
            `,
            footerHtml: `
              <button class="btn btn-secondary" onclick="document.getElementById('drawer-close-btn').click()">انصراف</button>
              <button id="btn-save-section" class="btn btn-primary">ذخیره تنظیمات بخش</button>
            `
          });

          document.getElementById('btn-save-section').addEventListener('click', async () => {
            const saveBtn = document.getElementById('btn-save-section');
            saveBtn.classList.add('loading');
            saveBtn.disabled = true;

            try {
              const body = {
                model_name: document.getElementById('edit-sec-model').value.trim(),
                provider: document.getElementById('edit-sec-provider').value.trim(),
                base_url: document.getElementById('edit-sec-base-url').value.trim() || null,
                is_active: document.getElementById('edit-sec-active').checked
              };
              const apiKeyVal = document.getElementById('edit-sec-api-key').value.trim();
              if (apiKeyVal) body.api_key = apiKeyVal;

              await ApiClient.put(`/ai/sections/${key}`, body);
              Toast.success(`پیکربندی بخش ${sec.sectionNameFa || key} با موفقیت به‌روزرسانی شد.`);
              Drawer.close();
              fetchSections();
            } finally {
              saveBtn.classList.remove('loading');
              saveBtn.disabled = false;
            }
          });
        });
      });
    } catch (err) {
      secContainer.innerHTML = `<div class="empty-state"><div class="empty-state-title" style="color: var(--danger);">خطا در دریافت دپارتمان‌ها: ${err.message}</div></div>`;
    }
  }

  // Initial load
  initPlayground();
}
