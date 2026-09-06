const I18N = {
_langCache: null,
get lang() {
if (this._langCache === null) {
this._langCache = localStorage.getItem('stellio-lang') ||
document.cookie.replace(/(?:(?:^|.*;\s*)stellio-lang\s*=\s*([^;]*).*$)|^.*$/, "$1") || 'fr';
}
return this._langCache;
},
set lang(value) {
this._langCache = value;
localStorage.setItem('stellio-lang', value);
document.cookie = `stellio-lang=${value}; path=/; max-age=31536000; SameSite=Lax`;
},
fallback: 'fr',
translations: {},
isReady: false,
_config: { folder: '/languages' },
_supportedLangs: {
zh: { code: 'zh', name: 'Chinese', native: '中文', dir: 'ltr' },
en: { code: 'en', name: 'English', native: 'English', dir: 'ltr' },
es: { code: 'es', name: 'Español', native: 'Español', dir: 'ltr' },
fr: { code: 'fr', name: 'Français', native: 'Français', dir: 'ltr' },
de: { code: 'de', name: 'German', native: 'Deutsch', dir: 'ltr' },
it: { code: 'it', name: 'Italian', native: 'Italiano', dir: 'ltr' },
ja: { code: 'ja', name: 'Japanese', native: '日本語', dir: 'ltr' },
pt: { code: 'pt', name: 'Portuguese', native: 'Português', dir: 'ltr' }


},
async init(options = {}) {
const { folder, autoApply = true, onReady = null } = options;
if (folder) this._config.folder = folder.startsWith('/') ? folder : `/${folder}`;
try {
let serverLang = null;
const baseUrl = window.location.origin;
try {
const res = await fetch(`${baseUrl}/api/settings`);
if (res.ok) {
const settings = await res.json();
if (settings?.lang && this._supportedLangs[settings.lang]) {
serverLang = settings.lang;
}
}
} catch (e) {
console.debug('[I18N] Backend indisponible, fallback localStorage');
}
this.lang = serverLang || localStorage.getItem('stellio-lang') || document.cookie.replace(/(?:(?:^|.*;\s*)stellio-lang\s*=\s*([^;]*).*$)|^.*$/, "$1") || 'fr';
await this._loadLang(this.lang);
if (this.lang !== this.fallback) {
await this._loadLang(this.fallback);
}
document.documentElement.lang = this.lang;
document.documentElement.dir = this.translations[this.lang]?.__dir || 'ltr';
if (autoApply) this.apply();
this.isReady = true;
if (typeof onReady === 'function') onReady(this.lang);
document.dispatchEvent(new CustomEvent('i18n:ready', { detail: { lang: this.lang } }));
} catch (err) {
console.error('[I18N] Erreur init:', err);
this._handleError();
}
},
async _loadLang(langCode) {
const folder = this._config.folder.startsWith('/') ? this._config.folder : `/${this._config.folder}`;
const res = await fetch(`${folder}/${langCode}.json`);
if (!res.ok) throw new Error(`Fichier ${langCode}.json introuvable`);
this.translations[langCode] = await res.json();
},
_handleError() {
const minimal = { 'app.title': 'Stellio', 'app.loading': 'Loading...', 'app.error': 'Erreur' };
this.translations[this.fallback] = { ...(this.translations[this.fallback] || {}), ...minimal };
this.lang = this.fallback;
document.documentElement.lang = this.fallback;
document.documentElement.dir = 'ltr';
this.apply();
this.isReady = true;
},
t(key, params = {}) {
if (!key) return '';
const raw = this.translations[this.lang]?.[key] || this.translations[this.fallback]?.[key] || key;
return this._interpolate(raw, params);
},
_interpolate(str, params) {
if (!params || !Object.keys(params).length) return str;
return str.replace(/\{\{\s*(\w+)\s*\}\}/g, (_, v) => params[v] !== undefined ? params[v] : `{{${v}}}`);
},
tp(key, count, params = {}) {
const trans = this.translations[this.lang] || this.translations[this.fallback] || {};
const plural = trans[`${key}_plural`];
if (!plural) return this.t(key, { ...params, count });
const forms = plural.split('|').map(s => s.trim());
let idx = forms.length === 3 ? 2 : (count === 0 && forms[0]?.includes('zero') ? 0 : (count === 1 ? (forms[0]?.includes('zero') ? 1 : 0) : 1));
return this._interpolate(forms[idx] || forms[forms.length - 1], { ...params, count });
},
apply(scope = document) {
const targetProp = { 'i18n': 'textContent', 'i18n-placeholder': 'placeholder', 'i18n-title': 'title', 'i18n-aria': 'ariaLabel', 'i18n-html': 'innerHTML', 'i18n-alt': 'alt' };
const applyAttr = (selector, attr, paramsAttr) => {
scope.querySelectorAll(selector).forEach(el => {
const key = el.getAttribute(`data-${attr}`);
const params = this._parseParams(el.getAttribute(`data-${paramsAttr}`));
if (key) el[targetProp[attr] || attr.replace('i18n-', '').toLowerCase()] = this.t(key, params);
});
};
applyAttr('[data-i18n]', 'i18n', 'i18nParams');
applyAttr('[data-i18n-placeholder]', 'i18n-placeholder', 'i18n-placeholderParams');
applyAttr('[data-i18n-title]', 'i18n-title', 'i18n-titleParams');
applyAttr('[data-i18n-aria]', 'i18n-aria', 'i18n-ariaParams');
applyAttr('[data-i18n-html]', 'i18n-html', 'i18n-htmlParams');
applyAttr('[data-i18n-alt]', 'i18n-alt', 'i18n-altParams');
['language-selector', 'language-selector-auth'].forEach(id => {
const sel = document.getElementById(id);
if (sel && sel.value !== this.lang) sel.value = this.lang;
});
},
_parseParams(jsonStr) {
if (!jsonStr) return {};
try { return typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr; }
catch { return {}; }
},
async setLanguage(newLang) {
if (newLang === this.lang) return;
if (!this.isReady) {
document.addEventListener('i18n:ready', () => this.setLanguage(newLang), { once: true });
return;
}
if (!this._supportedLangs[newLang]) return console.warn(`[I18N] Langue "${newLang}" non supportée`);
try {
await this._loadLang(newLang);
this.lang = newLang;
localStorage.setItem('stellio-lang', newLang);
document.documentElement.lang = newLang;
document.documentElement.dir = this.translations[newLang]?.__dir || 'ltr';
this.apply();
const baseUrl = window.location.origin;
fetch(`${baseUrl}/api/settings`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ lang: newLang })
}).catch(e => console.debug('[I18N] Échec sauvegarde serveur:', e));
document.dispatchEvent(new CustomEvent('i18n:changed', { detail: { lang: newLang } }));
if (typeof loadFiles === 'function') loadFiles();
this.showRestartPopup();
} catch (err) {
console.error('[I18N] ❌ Changement échoué:', err);
}
},
showRestartPopup() {
const title = this.t('settings.restart_required') || 'Redémarrage requis';
const message = this.t('settings.restart_message') || 'Un redémarrage de l\'application est requis pour appliquer la nouvelle langue.';
const btnText = this.t('actions.ok') || 'OK';
const overlay = document.createElement('div');
overlay.style.cssText = `position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); display: flex; align-items: center; justify-content: center; z-index: 100000; backdrop-filter: blur(5px);`;
const popup = document.createElement('div');
popup.style.cssText = `background: var(--bg-secondary, #1e2129); color: var(--text-primary, #e6e6e6); padding: 28px; border-radius: 14px; max-width: 380px; width: 90%; box-shadow: 0 12px 35px rgba(0,0,0,0.6); text-align: center; border: 1px solid var(--border, #2a2f3a); animation: popIn 0.25s ease;`;
popup.innerHTML = `<h3 style="margin: 0 0 10px 0; font-size: 19px; font-weight: 600;">${title}</h3><p style="color: var(--text-muted, #9ca3af); margin: 0 0 24px 0; line-height: 1.5; font-size: 14px;">${message}</p><button id="restart-lang-btn" style="padding: 11px 28px; border: none; border-radius: 8px; background: var(--accent, #4ea1d3); color: #fff; font-weight: 600; cursor: pointer; transition: all 0.2s; font-size: 15px;">${btnText}</button>`;
overlay.appendChild(popup);
document.body.appendChild(overlay);
if (!document.getElementById('restart-popup-style')) {
const style = document.createElement('style');
style.id = 'restart-popup-style';
style.textContent = `@keyframes popIn { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }`;
document.head.appendChild(style);
}
document.getElementById('restart-lang-btn').addEventListener('click', () => {
overlay.remove();
location.reload();
});
},
getAvailableLanguages() {
return Object.values(this._supportedLangs).map(l => ({ code: l.code, name: l.name, native: l.native, dir: l.dir }));
},
has(key, lang = null) {
const target = lang || this.lang;
return !!(this.translations[target]?.[key] || this.translations[this.fallback]?.[key]);
},
async reload() {
this.isReady = false;
this._langCache = null;
try {
await this._loadLang(this.lang);
this.isReady = true;
this.apply();
} catch (err) { console.error('[I18N] Reload échoué', err); this.isReady = true; }
}
};
window.I18N = I18N;


const API = window.location.origin;

function _getCsrfCookie() {
    const match = document.cookie.match(/(?:^|;\s*)stellio_csrf=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : null;
}
const _nativeFetch = window.fetch.bind(window);
window.fetch = function (input, init = {}) {
    const url = typeof input === 'string' ? input : (input?.url || '');
    const isSameOrigin = url.startsWith(API) || url.startsWith('/');
    const method = (init.method || (typeof input !== 'string' && input?.method) || 'GET').toUpperCase();
    if (isSameOrigin && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
        const token = _getCsrfCookie();
        if (token) {
            init = { ...init };
            init.headers = new Headers(init.headers || {});
            init.headers.set('X-CSRF-Token', token);
        }
    }
    return _nativeFetch(input, init);
};

let allFiles = [];
let filteredFiles = [];
let currentSlicerFile = null;
let currentView = 'gallery';
let currentSort = 'name-asc';
let allTags = [];
let currentTagFile = null;
let activeTagFilters = new Set();
let activeTypeFilters = [];
let currentSizeFilter = null;
let currentWeightFilter = null;
let printStatusFilter = '';
let noThumbFilterOnly = false;
let failedThumbFilterOnly = false;
let favoriteFiles = new Set();
let seenFilesSet = new Set();
let showFavoritesOnly = false;
let autoScanInterval = null;
let lastKnownTimestamp = Date.now() / 1000;
let thumbRefreshInterval = null;
const analysisCache = {};
const pendingThumbRequests = new Set();
const pendingMetadataRequests = new Set();
const generatingThumbs = new Set();
let isSelectionMode = false;
let selectedFiles = new Set();
const hoverThrottle = new Map();
const HOVER_THROTTLE_MS = 2000;
const HOVER_THROTTLE_MAX_ENTRIES = 1000;
function _hoverThrottleSet(path, timestamp) {
    hoverThrottle.set(path, timestamp);
    if (hoverThrottle.size > HOVER_THROTTLE_MAX_ENTRIES) {
        hoverThrottle.delete(hoverThrottle.keys().next().value);
    }
}

function translateSortOptions() {
const sortSelect = document.getElementById('sort-select');
if (sortSelect) {
sortSelect.querySelectorAll('option').forEach(opt => {
if (opt.dataset.i18n) opt.textContent = I18N.t(opt.dataset.i18n);
});
}
}
function translateAuthFields() {
const fields = [
{ id: 'login-username', key: 'auth.username' },
{ id: 'login-password', key: 'auth.password' },
{ id: 'reg-username', key: 'auth.username' },
{ id: 'reg-password', key: 'auth.password' },
{ id: 'reg-password-confirm', key: 'auth.confirm_password' },
{ id: 'forgot-username', key: 'auth.username' },
{ id: 'forgot-recovery-code', key: 'auth.recovery_code_placeholder' },
{ id: 'forgot-new-password', key: 'auth.new_password' },
{ id: 'forgot-new-password-confirm', key: 'auth.confirm_password' }
];
fields.forEach(field => {
const el = document.getElementById(field.id);
if (el && I18N.has(field.key)) el.placeholder = I18N.t(field.key);
});
}
document.addEventListener('DOMContentLoaded', async () => {
console.log('[Stellio] DOM chargé, initialisation...');


const firstLaunchPromise = fetch(`${API}/api/auth/first-launch`)
    .then(r => r.json())
    .catch(() => null);
await I18N.init({ folder: 'languages', autoApply: true });
populateLanguageSelectors();
translateSortOptions();
translateAuthFields();
checkAuth(firstLaunchPromise);
setupEventListeners();
initSettings();
setupHoverDelegation();
setupKeyboardShortcuts();
});


let stellioAppConfig = { allowed_source_types: ['folder', 'file', 'smb', 'nfs'], headless: false };

async function loadAppConfig() {
    try {
        const res = await fetch(`${API}/api/app-config`);
        if (!res.ok) return;
        stellioAppConfig = await res.json();
        applyAllowedSourceTypes(stellioAppConfig.allowed_source_types || ['folder', 'file', 'smb', 'nfs']);
    } catch (err) {
        console.error('[loadAppConfig] Erreur:', err);
    }
}

function applyAllowedSourceTypes(allowedTypes) {
    const allTypes = ['folder', 'file', 'smb', 'nfs'];
    const hiddenTypes = allTypes.filter(t => !allowedTypes.includes(t));

    document.querySelectorAll('#modal-select-type .type-card').forEach(card => {
        card.style.display = allowedTypes.includes(card.dataset.type) ? '' : 'none';
    });

    let note = document.getElementById('source-types-restricted-note');
    if (hiddenTypes.length > 0) {
        if (!note) {
            note = document.createElement('p');
            note.id = 'source-types-restricted-note';
            note.style.cssText = 'font-size:11.5px;color:var(--text-muted);text-align:center;margin-top:12px;line-height:1.5;';
            document.querySelector('#modal-select-type .modal-body')?.appendChild(note);
        }
        note.textContent = I18N.t('source.types_restricted_note') ||
            "Certains types de source sont désactivés sur ce serveur (déploiement Docker : uniquement les sources réseau SMB/NFS).";
    } else if (note) {
        note.remove();
    }
}

function openLocalManualModal(type) {
    const form = document.getElementById('local-manual-form');
    form?.reset();
    if (form) form.dataset.sourceType = type;
    const titleEl = document.getElementById('local-manual-title');
    const pathInput = document.getElementById('local-manual-path');
    if (type === 'file') {
        if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-file"></i> <span data-i18n="source.single_file">Fichier unique</span>`;
        if (pathInput) pathInput.placeholder = '/library/piece.stl';
    } else {
        if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-folder"></i> <span data-i18n="source.local_folder">Dossier local</span>`;
        if (pathInput) pathInput.placeholder = '/library';
    }
    I18N.apply();
    openModal('modal-local-manual');
}

document.getElementById('local-manual-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const type = e.target.dataset.sourceType || 'folder';
    const path = document.getElementById('local-manual-path').value.trim();
    if (!path) return;
    const name = document.getElementById('local-manual-name').value.trim() || path.split('/').pop() || path;
    const success = await addSource(type, name, path, {});
    if (success) {
        showToast(I18N.t('toast.source_added') || 'Source ajoutée', 'success');
        closeModal('modal-local-manual');
        loadSources();
        loadFiles();
    }
});


function exportBackup() {
    document.getElementById('backup-options-form')?.reset();
    openModal('modal-backup-options');
}

document.getElementById('backup-options-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    closeModal('modal-backup-options');
    const include = {
        library: document.getElementById('backup-opt-library').checked,
        accounts: document.getElementById('backup-opt-accounts').checked,
        printers: document.getElementById('backup-opt-printers').checked,
        history: document.getElementById('backup-opt-history').checked,
        settings: document.getElementById('backup-opt-settings').checked,
    };
    await runBackupExport(include);
});

async function runBackupExport(include) {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.save_backup) {
        showToast(I18N.t('toast.backup_exporting') || 'Préparation de la sauvegarde...', 'info');
        try {
            const result = await window.pywebview.api.save_backup(include);
            if (result && result.success) {
                showToast(I18N.t('toast.backup_export_done') || `Sauvegarde enregistrée : ${result.path}`, 'success');
            } else if (result && result.cancelled) {
            } else {
                showToast((result && result.error) || I18N.t('toast.error') || 'Erreur', 'error');
            }
        } catch (err) {
            showToast(I18N.t('toast.connection_error') || 'Erreur de connexion', 'error');
        }
        return;
    }

    showToast(I18N.t('toast.backup_exporting') || 'Préparation de la sauvegarde...', 'info');
    try {
        const res = await fetch(`${API}/api/backup/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ include })
        });
        if (!res.ok) {
            let msg = I18N.t('toast.error') || 'Erreur';
            try {
                const data = await res.json();
                msg = data.error || msg;
            } catch (e) {  }
            showToast(msg, 'error');
            return;
        }

        const blob = await res.blob();
        const disposition = res.headers.get('Content-Disposition') || '';
        const match = disposition.match(/filename="?([^"]+)"?/);
        const filename = match ? match[1] : `stellio_backup_${Date.now()}.zip`;

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        showToast(I18N.t('toast.backup_export_done') || 'Sauvegarde téléchargée', 'success');
    } catch (err) {
        showToast(I18N.t('toast.connection_error') || 'Erreur de connexion', 'error');
    }
}

async function importBackup(file) {
    if (!file) return;
    const confirmMsg = I18N.t('settings.backup_import_confirm') ||
        "Cette action va remplacer toutes vos données actuelles (bibliothèque, comptes, tags, historique) par celles de la sauvegarde. Continuer ?";
    const ok = await showConfirmDialog(confirmMsg, {
        title: I18N.t('settings.backup_import_confirm_title') || 'Restaurer la sauvegarde ?',
        confirmLabel: I18N.t('actions.continue') || 'Continuer',
        danger: true
    });
    if (!ok) {
        document.getElementById('backup-import-input').value = '';
        return;
    }

    const formData = new FormData();
    formData.append('backup', file);

    showToast(I18N.t('toast.backup_importing') || 'Import de la sauvegarde en cours...', 'info');
    try {
        const res = await fetch(`${API}/api/backup/import`, { method: 'POST', body: formData });
        const data = await res.json();
        if (res.ok && data.success) {
            showBackupRestartPopup();
        } else {
            showToast(data.error || I18N.t('toast.error') || 'Erreur', 'error');
        }
    } catch (err) {
        showToast(I18N.t('toast.connection_error') || 'Erreur de connexion', 'error');
    } finally {
        document.getElementById('backup-import-input').value = '';
    }
}

function showConfirmDialog(message, options = {}) {
    const {
        title = null,
        confirmLabel = I18N.t('actions.confirm') || 'Confirmer',
        cancelLabel = I18N.t('actions.cancel') || 'Annuler',
        danger = false,
        icon = danger ? 'fa-triangle-exclamation' : 'fa-circle-question'
    } = options;

    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.style.cssText = `position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); display: flex; align-items: center; justify-content: center; z-index: 100000; backdrop-filter: blur(5px);`;
        const popup = document.createElement('div');
        popup.style.cssText = `background: var(--bg-secondary); color: var(--text-primary); padding: 28px; border-radius: 14px; max-width: 420px; width: 90%; box-shadow: 0 12px 35px rgba(0,0,0,0.6); text-align: center; border: 1px solid var(--border);`;
        popup.innerHTML = `
            ${title ? `<h3 style="margin:0 0 10px 0; font-size:19px; font-weight:600;"><i class="fa-solid ${icon}" style="color:${danger ? 'var(--danger)' : 'var(--accent, #4f8cff)'};"></i> ${escapeHtml(title)}</h3>` : ''}
            <p style="color:var(--text-muted); margin:0 0 24px 0; line-height:1.5; font-size:14px;">${escapeHtml(message)}</p>
            <div style="display:flex; gap:10px; justify-content:center;">
                <button id="confirm-dialog-cancel" class="btn btn-ghost">${escapeHtml(cancelLabel)}</button>
                <button id="confirm-dialog-ok" class="btn ${danger ? 'btn-danger' : 'btn-primary'}">${escapeHtml(confirmLabel)}</button>
            </div>
        `;
        overlay.appendChild(popup);
        document.body.appendChild(overlay);

        const cleanup = (result) => {
            overlay.remove();
            resolve(result);
        };

        document.getElementById('confirm-dialog-ok').addEventListener('click', () => cleanup(true));
        document.getElementById('confirm-dialog-cancel').addEventListener('click', () => cleanup(false));
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) cleanup(false);
        });
        const onKey = (e) => {
            if (e.key === 'Escape') { cleanup(false); document.removeEventListener('keydown', onKey); }
        };
        document.addEventListener('keydown', onKey);
    });
}

function showBackupRestartPopup() {
    const overlay = document.createElement('div');
    overlay.style.cssText = `position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); display: flex; align-items: center; justify-content: center; z-index: 100000; backdrop-filter: blur(5px);`;
    const popup = document.createElement('div');
    popup.style.cssText = `background: var(--bg-secondary); color: var(--text-primary); padding: 28px; border-radius: 14px; max-width: 400px; width: 90%; box-shadow: 0 12px 35px rgba(0,0,0,0.6); text-align: center; border: 1px solid var(--border);`;
    popup.innerHTML = `
        <h3 style="margin:0 0 10px 0; font-size:19px; font-weight:600;"><i class="fa-solid fa-circle-check" style="color:var(--success);"></i> ${I18N.t('settings.backup_import_success') || 'Sauvegarde restaurée'}</h3>
        <p style="color:var(--text-muted); margin:0 0 24px 0; line-height:1.5; font-size:14px;">${I18N.t('settings.backup_restart_message') || 'Redémarrez Stellio pour finaliser la restauration de vos données.'}</p>
        <button id="backup-restart-btn" class="btn btn-primary">${I18N.t('settings.close_and_restart') || 'Fermer Stellio maintenant'}</button>
    `;
    overlay.appendChild(popup);
    document.body.appendChild(overlay);
    document.getElementById('backup-restart-btn').addEventListener('click', () => {
        fetch(`${API}/api/app/quit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}), keepalive: true }).catch(() => {});
        setTimeout(() => { window.close(); }, 1200);
    });
}


let integrityPollInterval = null;

async function startIntegrityCheck() {
    const btn = document.getElementById('integrity-check-btn');
    const progressContainer = document.getElementById('integrity-progress-container');
    const summary = document.getElementById('integrity-summary');
    const resultsEl = document.getElementById('integrity-results');
    btn.disabled = true;
    resultsEl.innerHTML = '';
    summary.classList.add('hidden');
    progressContainer.classList.remove('hidden');

    try {
        const filesRes = await fetch(`${API}/api/files`);
        const files = await filesRes.json();
        const paths = (files || []).map(f => f.path).filter(Boolean);

        if (paths.length === 0) {
            showToast(I18N.t('integrity.no_files') || 'Aucun fichier à vérifier.', 'info');
            btn.disabled = false;
            progressContainer.classList.add('hidden');
            return;
        }

        const res = await fetch(`${API}/api/integrity/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paths })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || I18N.t('toast.error') || 'Erreur', 'error');
            btn.disabled = false;
            progressContainer.classList.add('hidden');
            return;
        }
        pollIntegrityProgress();
    } catch (err) {
        showToast(I18N.t('toast.connection_error') || 'Erreur de connexion', 'error');
        btn.disabled = false;
        progressContainer.classList.add('hidden');
    }
}

function pollIntegrityProgress() {
    clearInterval(integrityPollInterval);
    integrityPollInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API}/api/integrity/progress`);
            const data = await res.json();
            updateIntegrityUI(data);
            if (!data.running) {
                clearInterval(integrityPollInterval);
                document.getElementById('integrity-check-btn').disabled = false;
                document.getElementById('integrity-progress-container').classList.add('hidden');
            }
        } catch (err) {
            clearInterval(integrityPollInterval);
            document.getElementById('integrity-check-btn').disabled = false;
        }
    }, 1000);
}

function updateIntegrityUI(data) {
    const text = document.getElementById('integrity-progress-text');
    const bar = document.getElementById('integrity-progress-bar');
    if (text) text.textContent = `${data.checked}/${data.total}`;
    if (bar) bar.style.width = data.total ? `${Math.round((data.checked / data.total) * 100)}%` : '0%';

    const summary = document.getElementById('integrity-summary');
    summary.classList.remove('hidden');
    document.getElementById('integrity-ok-count').textContent = data.ok || 0;
    document.getElementById('integrity-corrupted-count').textContent = (data.corrupted || 0) + (data.empty || 0);
    document.getElementById('integrity-missing-count').textContent = data.missing || 0;

    renderIntegrityResults(data.problems || []);
}

function renderIntegrityResults(problems) {
    const resultsEl = document.getElementById('integrity-results');
    if (!problems.length) {
        resultsEl.innerHTML = '';
        return;
    }
    resultsEl.innerHTML = problems.map(p => `
        <div class="integrity-result-row ${p.status}" data-path="${escapeHtml(p.path)}">
            <i class="fa-solid ${p.status === 'missing' ? 'fa-file-circle-xmark' : 'fa-triangle-exclamation'}"></i>
            <div class="integrity-result-info">
                <div class="integrity-result-name">${escapeHtml(p.name)}</div>
                <div class="integrity-result-path">${escapeHtml(p.path)}</div>
                <div class="integrity-result-error">${escapeHtml(p.error || '')}</div>
            </div>
            <div class="integrity-result-actions">
                ${p.status === 'missing'
                    ? `<span class="integrity-missing-note" data-i18n="integrity.missing_note">Sera retiré au prochain scan</span>`
                    : `<button class="btn btn-ghost btn-sm" onclick="repairFileFromIntegrity('${escapeJs(p.path)}', this)" data-i18n-title="integrity.try_repair" title="Tenter une réparation"><i class="fa-solid fa-wrench"></i></button>
                       <button class="btn btn-ghost btn-sm" style="color:var(--danger);" onclick="deleteFileFromIntegrity('${escapeJs(p.path)}')" data-i18n-title="actions.delete" title="Supprimer"><i class="fa-solid fa-trash"></i></button>`
                }
            </div>
        </div>
    `).join('');
}

async function deleteFileFromIntegrity(path) {
    const ok = await showConfirmDialog(
        I18N.t('integrity.confirm_delete') || 'Supprimer définitivement ce fichier de la bibliothèque ?',
        { title: I18N.t('actions.delete') || 'Supprimer', confirmLabel: I18N.t('actions.delete') || 'Supprimer', danger: true }
    );
    if (!ok) return;
    try {
        const res = await fetch(`${API}/api/files/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: path })
        });
        if (res.ok) {
            showToast(I18N.t('toast.file_deleted') || 'Fichier supprimé', 'success');
            document.querySelector(`.integrity-result-row[data-path="${CSS.escape(path)}"]`)?.remove();
        } else {
            const data = await res.json().catch(() => ({}));
            showToast(data.error || I18N.t('toast.error') || 'Erreur', 'error');
        }
    } catch (err) {
        showToast(I18N.t('toast.connection_error') || 'Erreur de connexion', 'error');
    }
}

async function repairFileFromIntegrity(path, btn) {
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
    try {
        const res = await fetch(`${API}/api/files/repair`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        });
        const data = await res.json().catch(() => ({}));

        if (res.ok && data.success) {
            const msg = data.watertight === false
                ? (data.message || I18N.t('toast.repair_partial') || 'Réparation partielle : problèmes non résolus automatiquement (.bak conservé)')
                : (data.message || I18N.t('toast.repair_success') || 'Fichier réparé');
            showToast(msg, data.watertight === false ? 'warning' : 'success');


            const row = document.querySelector(`.integrity-result-row[data-path="${CSS.escape(path)}"]`);
            row?.remove();
            const corruptedEl = document.getElementById('integrity-corrupted-count');
            const okEl = document.getElementById('integrity-ok-count');
            if (corruptedEl) corruptedEl.textContent = Math.max(0, (parseInt(corruptedEl.textContent) || 0) - 1);
            if (okEl) okEl.textContent = (parseInt(okEl.textContent) || 0) + 1;

            loadFiles();
        } else {
            btn.innerHTML = originalHtml;
            btn.disabled = false;
            showToast(data.error || I18N.t('toast.repair_failed') || 'Échec de la réparation', 'error');
        }
    } catch (err) {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
        showToast(I18N.t('toast.connection_error') || 'Erreur de connexion', 'error');
    }
}


function isTypingContext(e) {
    const tag = (e.target.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable;
}

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        const typing = isTypingContext(e);
        const ctrlOrCmd = e.ctrlKey || e.metaKey;

        if (e.key === 'Escape') {
            const openModalEl = document.querySelector('.modal:not(.hidden)');
            if (openModalEl) {
                if (openModalEl.id === 'modal-3d-viewer') close3DViewer();
                else closeModal(openModalEl.id);
                return;
            }
            const search = document.getElementById('global-search');
            if (search && document.activeElement === search && search.value) {
                search.value = '';
                search.dispatchEvent(new Event('input'));
            } else {
                search?.blur();
            }
            return;
        }

        if (!typing && !ctrlOrCmd && e.key === '?') {
            e.preventDefault();
            openModal('modal-shortcuts');
            return;
        }

        if (ctrlOrCmd && e.key.toLowerCase() === 'f') {
            e.preventDefault();
            document.getElementById('global-search')?.focus();
            return;
        }

        if (ctrlOrCmd && e.key.toLowerCase() === 'n') {
            e.preventDefault();
            openDownloadModal();
            return;
        }

        if (ctrlOrCmd && e.key === ',') {
            e.preventDefault();
            document.querySelector('.nav-btn[data-page="settings"]')?.click();
            return;
        }

        if (e.altKey && !ctrlOrCmd) {
            const navMap = {
                '1': 'library', '2': 'stats', '3': 'projects', '4': 'history',
                '5': 'printers', '6': 'spoolman', '7': 'repair', '8': 'converter'
            };
            const page = navMap[e.key];
            if (page) {
                e.preventDefault();
                document.querySelector(`.nav-btn[data-page="${page}"]`)?.click();
            }
            return;
        }

        if (!typing && !ctrlOrCmd && !e.altKey) {
            const key = e.key.toLowerCase();
            if (key === 'f') {
                e.preventDefault();
                toggleFavoritesFilterFromNav();
                return;
            }
            if (key === 't') {
                e.preventDefault();
                openTagManagerModal();
                return;
            }
        }
    });
}
function setupHoverDelegation() {
const grid = document.getElementById('files-grid');
if (!grid) return;
grid.addEventListener('mouseenter', (e) => {
const card = e.target.closest('.file-card');
if (!card) return;
const path = card.dataset.path;
if (!path) return;
    const now = Date.now();
    const last = hoverThrottle.get(path) || 0;
    if (now - last < HOVER_THROTTLE_MS) return;
    _hoverThrottleSet(path, now);

    const newBadge = card.querySelector('.file-new-badge');
    if (newBadge) {
        newBadge.remove();
        if (!seenFilesSet.has(path)) {
            seenFilesSet.add(path);
            fetch(`${API}/api/settings`).then(r => r.json()).then(settings => {
                const seenFiles = settings.seen_files || [];
                if (!seenFiles.includes(path)) {
                    seenFiles.push(path);
                    fetch(`${API}/api/settings`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ seen_files: seenFiles })
                    });
                }
            }).catch(() => {});
        }
    }

    if (!card.dataset.thumbChecked) {
        const file = filteredFiles.find(f => f.path === path);
        if (file && !file.has_thumb) {
            requestThumbGeneration(path);
        }
        card.dataset.thumbChecked = 'true';
    }

    loadFileMetadata(path, (meta) => {
        if (!meta) return;
        const safeId = path.replace(/[^\w]/g, '-');
        const dimsEl = document.getElementById(`dims-${safeId}`);
        const weightEl = document.getElementById(`weight-${safeId}`);
        const timeEl = document.getElementById(`time-${safeId}`);
        if (dimsEl) dimsEl.textContent = `${meta.dimensions.x} × ${meta.dimensions.y} × ${meta.dimensions.z} mm`;
        if (weightEl) weightEl.textContent = `PLA: ${meta.weights.pla}g • PETG: ${meta.weights.petg}g`;
        if (timeEl) timeEl.textContent = `~${meta.estimated_time.formatted}`;
    });
}, true);
}
function populateLanguageSelectors() {
const selectors = [document.getElementById('language-selector'), document.getElementById('language-selector-auth')].filter(el => el);
selectors.forEach(selector => {
selector.innerHTML = '';
I18N.getAvailableLanguages().forEach(lang => {
const opt = document.createElement('option');
opt.value = lang.code;
opt.textContent = lang.native;
if (lang.code === I18N.lang) opt.selected = true;
selector.appendChild(opt);
});
});
}
document.addEventListener('i18n:changed', () => {
translateSortOptions();
translateAuthFields();
const authSelector = document.getElementById('language-selector-auth');
if (authSelector && authSelector.value !== I18N.lang) authSelector.value = I18N.lang;
const activeBtn = document.querySelector('.nav-btn.active');
if (activeBtn) {
const titleKey = activeBtn.dataset.titleKey || 'app.title';
const iconClass = activeBtn.dataset.icon || 'fa-layer-group';
const headerTitle = document.getElementById('header-page-title');
if (headerTitle) headerTitle.innerHTML = `<i class="fa-solid ${iconClass}"></i> ${I18N.t(titleKey)}`;
}
const searchInput = document.getElementById('global-search');
if (searchInput) searchInput.placeholder = I18N.t('search.placeholder');
I18N.apply();
});


window.handleThumbnailError = function (img) {
if (img.dataset.loaded === 'true') return;
img.style.display = 'none';
const loader = img.nextElementSibling;
if (loader && loader.classList.contains('file-loading')) {
    const card = img.closest('.file-card');
    const filePath = card?.dataset.path;
    if (filePath && !loader.classList.contains('thumb-pending')) {
        loader.classList.add('thumb-pending');
        loader.dataset.path = filePath;
        loader.innerHTML = '<i class="fa-solid fa-spinner fa-spin" style="font-size:32px; color:var(--text-muted); opacity:0.6;"></i>';
        loader.style.setProperty('display', 'flex', 'important');
        img.dataset.loaded = 'false';
        startPendingThumbPolling();
        return;
    }
    loader.style.setProperty('display', 'flex', 'important');
    if (!loader.querySelector('.fallback-logo')) {
        const thumbIcon = loader.querySelector('.thumb-icon');
        if (thumbIcon) thumbIcon.remove();
        const fallbackImg = document.createElement('img');
        fallbackImg.src = '/assets/logo-nom-stellio.png';
        fallbackImg.className = 'fallback-logo';
        fallbackImg.style.cssText = 'width:70%;height:70%;object-fit:contain;opacity:0.6;';
        fallbackImg.onerror = function () { this.style.display = 'none'; };
        loader.appendChild(fallbackImg);
    }
}
};
function generateVisibleThumbnails() {
const cards = document.querySelectorAll('.file-card');
if (!cards.length) return;
const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const card = entry.target;
        obs.unobserve(card);
        const filePath = card.dataset.path;
        if (!filePath) return;
        const thumbImg = card.querySelector('.file-thumb img');
        const needsGeneration = (
            !thumbImg ||
            !thumbImg.src ||
            thumbImg.src === window.location.href ||
            thumbImg.dataset.loaded === 'false' ||
            (thumbImg.src && thumbImg.naturalWidth === 0 && thumbImg.complete)
        );
        if (needsGeneration) {
            window.requestThumbGeneration(filePath);
        }
    });
}, { rootMargin: '300px' });
cards.forEach(card => observer.observe(card));
}


(function applyThemeOnLoad() {
const savedTheme = localStorage.getItem('stellio-theme') || 'dark';
const savedFabricant = localStorage.getItem('stellio-fabricant') || 'stellio';
if (savedTheme === 'auto') {
const isLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
document.documentElement.setAttribute('data-theme', isLight ? 'light' : 'dark');
} else {
document.documentElement.setAttribute('data-theme', savedTheme);
}
document.documentElement.setAttribute('data-fabricant', savedFabricant);
const savedCustomAccent = localStorage.getItem('stellio-custom-accent');
if (savedCustomAccent) applyCustomAccent(savedCustomAccent);
console.log('[Theme] ✅ Appliqué:', savedTheme, savedFabricant);
})();


window.requestThumbGeneration = async function (filePath) {
if (generatingThumbs.has(filePath) || pendingThumbRequests.has(filePath)) return;
if (window.permanentlyIgnoredThumbs && window.permanentlyIgnoredThumbs.has(filePath)) return;
pendingThumbRequests.add(filePath);
generatingThumbs.add(filePath);
const ext = filePath.split('.').pop().toLowerCase();
try {
const res = await fetch(`${API}/api/thumb/generate-now`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ path: filePath })
});
const data = await res.json();
if (data.ignored) {
    if (!window.permanentlyIgnoredThumbs) window.permanentlyIgnoredThumbs = new Set();
    window.permanentlyIgnoredThumbs.add(filePath);
    generatingThumbs.delete(filePath);
    pendingThumbRequests.delete(filePath);
} else if (data.cached) {
    refreshFileThumbnail(filePath);
    generatingThumbs.delete(filePath);
    pendingThumbRequests.delete(filePath);
} else if (data.success) {
    const maxAttempts = ext === '3mf' ? 30 : 15;
    const interval   = ext === '3mf' ? 300 : 500;
    let attempts = 0;
    const poll = setInterval(async () => {
        attempts++;
        try {
            const checkRes = await fetch(`${API}/api/thumb/check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            });
            const checkData = await checkRes.json();
            if (checkData.exists) {
                clearInterval(poll);
                refreshFileThumbnail(filePath);
                generatingThumbs.delete(filePath);
                pendingThumbRequests.delete(filePath);
            } else if (attempts >= maxAttempts) {
                clearInterval(poll);
                generatingThumbs.delete(filePath);
                pendingThumbRequests.delete(filePath);
            }
        } catch (e) {
            clearInterval(poll);
            generatingThumbs.delete(filePath);
            pendingThumbRequests.delete(filePath);
        }
    }, interval);
} else {
generatingThumbs.delete(filePath);
pendingThumbRequests.delete(filePath);
}
} catch (err) {
console.error('[Thumb Gen] Erreur:', err);
generatingThumbs.delete(filePath);
pendingThumbRequests.delete(filePath);
}
};
function refreshFileThumbnail(filePath) {
const card = document.querySelector(`.file-card[data-path="${CSS.escape(filePath)}"]`);
if (!card) return;
const thumbContainer = card.querySelector('.file-thumb');
const img = card.querySelector('.file-thumb img');
const loader = card.querySelector('.file-loading');
const ext = filePath.split('.').pop().toLowerCase();
const newSrc = `${API}/api/thumb?path=${encodeURIComponent(filePath)}&t=${Date.now()}`;
const testImg = new Image();
testImg.onload = function() {
    if (img) {
        img.src = newSrc;
        img.style.display = 'block';
        if (loader) loader.style.display = 'none';
    } else if (thumbContainer) {
        thumbContainer.innerHTML = '<img src="' + newSrc + '" alt="' + escapeHtml(filePath) + '" style="width:100%;height:100%;object-fit:cover;border-radius:8px;" data-loaded="true"><div class="file-overlay"><span class="file-ext">' + ext.toUpperCase() + '</span></div>';
    }
};
testImg.onerror = function() {
    if (img) window.handleThumbnailError(img);
};
testImg.src = newSrc;
}


window.requestMetadataAnalysis = async function (filePath, callback) {
if (analysisCache[filePath]) {
callback(analysisCache[filePath]);
return;
}
if (pendingMetadataRequests.has(filePath)) return;
pendingMetadataRequests.add(filePath);
try {
await fetch(`${API}/api/files/analyze-now`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ path: filePath })
});
setTimeout(async () => {
try {
const res = await fetch(`${API}/api/files/analyze`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ path: filePath })
});
const data = await res.json();
if (data.success) {
if (Object.keys(analysisCache).length > 100) {
delete analysisCache[Object.keys(analysisCache)[0]];
}
analysisCache[filePath] = data.metadata;
callback(data.metadata);
} else callback(null);
} catch (err) {
console.error('[Metadata] Erreur:', err);
callback(null);
}
pendingMetadataRequests.delete(filePath);
}, 1500);
} catch (err) {
console.error('[Metadata Gen] Erreur:', err);
callback(null);
pendingMetadataRequests.delete(filePath);
}
};


function _showStockWarningToast(warning) {
    if (!warning) return;
    const msg = _t2('toast.stock_warning', `Stock insuffisant sur "${warning.label}" : il manque ${warning.missing_g}g (besoin ${warning.required_g}g, reste ${warning.remaining_g}g)`,
        { label: warning.label, missing: warning.missing_g, required: warning.required_g, remaining: warning.remaining_g });
    showToast(msg, 'warning');
}
window._showStockWarningToast = _showStockWarningToast;

async function checkFavoritesRestock() {
    try {
        const res = await fetch(`${API}/api/ai/restock-check`);
        if (!res.ok) return;
        const data = await res.json();
        return data.alerts || [];
    } catch (e) {
        return [];
    }
}
window.checkFavoritesRestock = checkFavoritesRestock;

async function _refreshFavoritesRestockBadge() {
    const badge = document.getElementById('favorites-restock-badge');
    if (!badge) return;
    const alerts = await checkFavoritesRestock();
    if (alerts && alerts.length) {
        badge.style.display = 'inline-flex';
        badge.title = alerts.map(a => `${a.label} : -${a.missing_g}g`).join(' · ');
        badge.textContent = alerts.length;
    } else {
        badge.style.display = 'none';
    }
}
window._refreshFavoritesRestockBadge = _refreshFavoritesRestockBadge;

async function loadFavorites() {
try {
const res = await fetch(`${API}/api/favorites`);
if (res.ok) {
favoriteFiles = new Set(await res.json());
console.log('[Favoris] ✅ Chargés:', favoriteFiles.size);
updateFavoritesCount();
_refreshFavoritesRestockBadge();
}
} catch (err) {
console.error('[Favoris] Erreur:', err);
}
}
async function loadSeenFiles() {
try {
const res = await fetch(`${API}/api/settings`);
if (res.ok) {
const settings = await res.json();
seenFilesSet = new Set(settings.seen_files || []);
}
} catch (err) {
console.error('[SeenFiles] Erreur:', err);
}
}
window.toggleFavorite = async function (filePath, event) {
if (event) {
event.preventDefault();
event.stopPropagation();
}
try {
const res = await fetch(`${API}/api/favorites`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ path: filePath })
});
if (res.ok) {
const data = await res.json();
if (data.favorited) {
favoriteFiles.add(filePath);
showToast(I18N.t('toast.favorites_added'), 'success');
} else {
favoriteFiles.delete(filePath);
showToast(I18N.t('toast.favorites_removed'), 'info');
 if (favoriteFiles.size === 0 && showFavoritesOnly) {
showFavoritesOnly = false;
const navBtn = document.getElementById('nav-favorites-btn');
if (navBtn) navBtn.classList.remove('active');
const btn = document.getElementById('favorites-filter-btn');
if (btn) btn.classList.remove('active');
const headerTitle = document.getElementById('header-page-title');
if (headerTitle) headerTitle.innerHTML = `<i class="fa-solid fa-layer-group"></i> ${I18N.t('nav.library')}`;
showToast(I18N.t('toast.no_favorites'), 'info');
}
}
renderFiles();
updateFavoritesCount();
}
} catch (err) {
console.error('[Favoris] Erreur:', err);
showToast(I18N.t('toast.error'), 'error');
}
return false;
};
function updateFavoritesCount() {
const countEl = document.getElementById('favorites-count');
if (countEl) {
const count = favoriteFiles.size;
countEl.textContent = count;
countEl.style.display = count > 0 ? 'inline-block' : 'none';
}
}
function toggleFavoritesFilter(forceState = null) {
console.group('[DEBUG] toggleFavoritesFilter()');
console.log('  forceState =', forceState);
console.log('  showFavoritesOnly =', showFavoritesOnly);
if (forceState === null) {
showFavoritesOnly = !showFavoritesOnly;
} else {
if (showFavoritesOnly === forceState) {
console.log('  ⚠️ Déjà dans cet état');
console.groupEnd();
return;
}
showFavoritesOnly = forceState;
}
console.log('  Nouveau état :', showFavoritesOnly);

document.querySelectorAll('.nav-btn').forEach(btn => {
    if (btn.id === 'nav-favorites-btn') {
        btn.classList.toggle('active', showFavoritesOnly);
    } else if (btn.dataset.page === 'library') {
        btn.classList.toggle('active', !showFavoritesOnly);
    } else {
        btn.classList.remove('active');
    }
});

const headerTitle = document.getElementById('header-page-title');
if (headerTitle) {
    const titleKey = showFavoritesOnly ? 'nav.favorites' : 'nav.library';
    const iconClass = showFavoritesOnly ? 'fa-star' : 'fa-layer-group';
    headerTitle.innerHTML = `<i class="fa-solid ${iconClass}"></i> ${I18N.t(titleKey)}`;
}

if (showFavoritesOnly) {
    const beforeCount = filteredFiles.length;
    filteredFiles = allFiles.filter(f => favoriteFiles.has(f.path));
    console.log(`✅ Filtrage : ${beforeCount} → ${filteredFiles.length}`);
} else {
    filteredFiles = [...allFiles];
}

applySorting();
renderFiles();
updateSidebarCounts(filteredFiles);
updateFavoritesCount();
console.groupEnd();
}
window.toggleFavoritesFilterFromNav = function () {
console.log('[Favoris] Activation depuis navigation');
const libraryPage = document.getElementById('page-library');
const currentPage = document.querySelector('.page.active');
if (libraryPage && currentPage !== libraryPage) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    libraryPage.classList.add('active');
    if (typeof updateHeaderVisibilityForPage === 'function') updateHeaderVisibilityForPage('library');
}

document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.remove('active');
});

const favBtn = document.getElementById('nav-favorites-btn');
if (favBtn) favBtn.classList.add('active');

const headerTitle = document.getElementById('header-page-title');
if (headerTitle) {
    headerTitle.innerHTML = `<i class="fa-solid fa-star"></i> ${I18N.t('nav.favorites')}`;
}

if (!showFavoritesOnly) {
    showFavoritesOnly = true;
    filteredFiles = allFiles.filter(f => favoriteFiles.has(f.path));
    applySorting();
    renderFiles();
    updateSidebarCounts(filteredFiles);
    updateFavoritesCount();
}
};


async function decompressFile(filePath, event) {
if (event) {
event.preventDefault();
event.stopPropagation();
}
try {
const res = await fetch(`${API}/api/files/decompress`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ file_path: filePath })
});
const data = await res.json();
if (!res.ok) {
showToast(`❌ ${data.error || I18N.t('toast.extraction_error')}`, 'error');
return;
}
const archiveName = filePath.split('/').pop() || filePath;
showDecompressConfirmToast(archiveName, data.found_3d_files?.length || 0, filePath, data.found_3d_files || []);
} catch (err) {
console.error('[Decompress] Erreur:', err);
showToast(I18N.t('toast.server_error'), 'error');
}
}
async function extractArchiveEntry(archivePath, internalPath, event) {
if (event) {
event.preventDefault();
event.stopPropagation();
}
const btn = event?.currentTarget;
if (btn) btn.disabled = true;
try {
const res = await fetch(`${API}/api/archive/extract-entry`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ archive_path: archivePath, internal_path: internalPath })
});
const data = await res.json();
if (!res.ok) {
showToast(`❌ ${data.error || I18N.t('toast.extraction_error')}`, 'error');
return;
}
showToast(`✅ ${data.message || I18N.t('toast.extract_success')}`, 'success');
loadFiles();
} catch (err) {
console.error('[ExtractEntry] Erreur:', err);
showToast(I18N.t('toast.server_error'), 'error');
} finally {
if (btn) btn.disabled = false;
}
}
function showDecompressConfirmToast(archiveName, extractedCount, archivePath, extractedFiles) {
const container = document.getElementById('toast-container');
if (!container) return ;
const toast = document.createElement('div');
toast.className = 'toast confirmation';
toast.innerHTML = `<p class="toast-message">🗜️ ${I18N.t('toast.extract_success')}</p><p class="toast-submessage">${extractedCount} ${I18N.t('toast.extract_found')} "${escapeHtml(archiveName)}".<br>${I18N.t('toast.delete_source')}</p><div class="toast-actions"><button class="btn-cancel" onclick="dismissDecompressToast(this)">${I18N.t('actions.save')}</button><button class="btn-confirm" onclick="confirmArchiveCleanup('${escapeJs(archivePath)}', this)">🗑️ ${I18N.t('actions.delete')}</button></div>`;
container.appendChild(toast);
setTimeout(() => {
if (toast.parentNode) {
toast.style.opacity = '0';
toast.style.transform = 'translateX(100%)';
setTimeout(() => toast.remove(), 300);
}
}, 10000);
}
window.dismissDecompressToast = function (btn) {
const toast = btn.closest('.toast');
if (toast) {
toast.style.opacity = '0';
toast.style.transform = 'translateX(100%)';
setTimeout(() => toast.remove(), 300);
}
showToast(I18N.t('toast.extract_keep'), 'info');
};
window.confirmArchiveCleanup = async function (archivePath, btn) {
const toast = btn.closest('.toast');
const buttons = toast.querySelectorAll('button');
buttons.forEach(b => b.disabled = true);
try {
const res = await fetch(`${API}/api/files/cleanup-archive`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ archive_path: archivePath })
});
const data = await res.json();
if (res.ok) {
showToast(I18N.t('toast.archive_deleted'), 'success');
loadFiles();
} else {
showToast(`❌ ${data.error || I18N.t('toast.archive_cleanup_error')}`, 'error');
}
} catch (err) {
console.error('[Cleanup] Erreur:', err);
showToast(I18N.t('toast.connection_error'), 'error');
} finally {
if (toast) {
toast.style.opacity = '0';
toast.style.transform = 'translateX(100%)';
setTimeout(() => toast.remove(), 300);
}
}
};


const REMEMBER_LOGIN_KEY = 'stellio_remember_login';

function _b64encodeUtf8(str) {
    return btoa(String.fromCharCode(...new TextEncoder().encode(str)));
}
function _b64decodeUtf8(str) {
    return new TextDecoder().decode(Uint8Array.from(atob(str), c => c.charCodeAt(0)));
}

function prefillRememberedLogin() {
    try {
        const raw = localStorage.getItem(REMEMBER_LOGIN_KEY);
        if (!raw) return;
        const { username, password } = JSON.parse(raw);
        const userEl = document.getElementById('login-username');
        const passEl = document.getElementById('login-password');
        const rememberEl = document.getElementById('login-remember');
        if (userEl && username) userEl.value = username;
        if (passEl && password) passEl.value = _b64decodeUtf8(password);
        if (rememberEl) rememberEl.checked = true;
    } catch (err) {
        localStorage.removeItem(REMEMBER_LOGIN_KEY);
    }
}

async function checkAuth(preFetchedFirstLaunch = null) {
try {


const firstLaunchData = preFetchedFirstLaunch
    ? await preFetchedFirstLaunch
    : await (await fetch(`${API}/api/auth/first-launch`)).json();
if (firstLaunchData && firstLaunchData.first_launch) {
showPanel('register-panel');
return;
}
showPanel('login-panel');
prefillRememberedLogin();
} catch (err) {
console.error('[checkAuth] Erreur:', err);
showPanel('login-panel');
prefillRememberedLogin();
}
}
function showPanel(panelId) {
document.querySelectorAll('.auth-panel').forEach(p => p.classList.add('hidden'));
document.getElementById(panelId)?.classList.remove('hidden');
document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder = I18N.t(el.dataset.i18nPlaceholder); });
I18N.apply();
translateAuthFields();
}
function showApp(user, filesPromise = null) {
document.getElementById('auth-screen').classList.add('hidden');
document.getElementById('app-screen').classList.remove('hidden');
document.getElementById('current-username').textContent = user.username;
loadAppVersion();
loadAppConfig();
loadSources();
loadAccountBadges();
loadTags();
loadFavorites();
loadSeenFiles();
loadPrinters();
loadSlicerProfiles();
checkAccountsStatusOnStartup();
startThumbProgressMonitor();
startMaintenanceDueChecker();
if (filesPromise) {
    filesPromise.then(async (cachedFiles) => {
        if (cachedFiles && Array.isArray(cachedFiles)) {
            allFiles = cachedFiles;
            filteredFiles = [...allFiles];
            applySorting();
            renderFiles();
            setTimeout(() => generateVisibleThumbnails(), 100);
            updateSidebarCounts(filteredFiles);
            updateFooterCounts();
        } else {
            loadFiles();
        }
    });
} else {
    loadFiles();
}
startThumbAutoRefresh();
startAutoFileMonitor();
startThumbFailureMonitor();
}
function showToast(message, type = 'info') {
const translated = I18N.has(`toast.${message}`) ? I18N.t(`toast.${message}`) : message;
const container = document.getElementById('toast-container');
if (!container) return;
const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle', warning: 'fa-exclamation-triangle' };
const toast = document.createElement('div');
toast.className = `toast ${type}`;
toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i><span class="toast-message">${escapeHtml(translated)}</span>`;
container.appendChild(toast);
setTimeout(() => {
toast.style.opacity = '0';
toast.style.transform = 'translateX(100%)';
toast.style.transition = 'all 0.3s ease';
setTimeout(() => toast.remove(), 300);
}, 3500);
}


async function checkAccountsStatusOnStartup() {
try {
const res = await fetch(`${API}/api/accounts/status`);
if (res.ok) {
const status = await res.json();
updateThingiverseFooterStatus(status.thingiverse, status.thingiverse ? null : I18N.t('settings.no_accounts'));
if (status.makerworld) {
    updateAccountBadge('makerworld', true);
    const emailDisplay = document.getElementById('makerworld-email-display');
    if (emailDisplay && status.makerworld_email) {
        emailDisplay.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${I18N.t('status.connected_email', { email: status.makerworld_email })}`;
    }
    document.getElementById('makerworld-step1') && (document.getElementById('makerworld-step1').style.display = 'none');
    document.getElementById('makerworld-step2') && (document.getElementById('makerworld-step2').style.display = 'none');
    const cr = document.getElementById('makerworld-connected-row');
    if (cr) cr.style.display = 'block';
}
console.log('[Startup] ✅ Statuts récupérés');
}
} catch (err) {
console.error('[Startup] ❌ Erreur statuts comptes:', err);
}
}
function startAutoFileMonitor() {
if (autoScanInterval) clearInterval(autoScanInterval);
autoScanInterval = setInterval(async () => {
try {
const changesRes = await fetch(`${API}/api/files/changes?since=${lastKnownTimestamp}`);
if (!changesRes.ok) return;
const changesData = await changesRes.json();
if (changesData.has_changes) {
const tagParams = activeTagFilters.size > 0 ? `&tags=${encodeURIComponent([...activeTagFilters].join(','))}` : '';
const filesRes = await fetch(`${API}/api/files?since=${lastKnownTimestamp}${tagParams}`);
if (!filesRes.ok) return;
const newFiles = await filesRes.json();
const oldHash = allFiles.map(f => `${f.name}-${f.size}-${f.path}`).join('|');
const newHash = newFiles.map(f => `${f.name}-${f.size}-${f.path}`).join('|');
if (oldHash !== newHash) {
allFiles = newFiles;
filteredFiles = showFavoritesOnly ? allFiles.filter(f => favoriteFiles.has(f.path)) : [...allFiles];
applySorting();
renderFiles();
startThumbnailGeneration();
updateSidebarCounts(filteredFiles);
updateFooterCounts();
}
lastKnownTimestamp = Date.now() / 1000;
}
} catch (err) {
console.debug('[AutoScan] Vérification échouée');
}
}, 15000);
}


function escapeHtml(str) {
if (!str) return '';
const div = document.createElement('div');
div.textContent = str;
return div.innerHTML;
}
function escapeJs(str) {
if (!str) return '';
return String(str)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
function formatSize(bytes) {
if (!bytes) return '—';
if (bytes < 1024) return bytes + ' B';
if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
function openModal(modalId) { document.getElementById(modalId)?.classList.remove('hidden'); }
function closeModal(modalId) {
    document.getElementById(modalId)?.classList.add('hidden');


    if (modalId === 'modal-slicer') _slicerLaunchedFromViewer = false;
}


async function loadFileMetadata(filePath, callback) {
if (analysisCache[filePath]) {
callback(analysisCache[filePath]);
return;
}
try {
const res = await fetch(`${API}/api/files/analyze`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ path: filePath })
});
const data = await res.json();
if (data.success) {
if (Object.keys(analysisCache).length > 100) {
delete analysisCache[Object.keys(analysisCache)[0]];
}
analysisCache[filePath] = data.metadata;
callback(data.metadata);
} else {
await requestMetadataAnalysis(filePath, callback);
}
} catch (err) {
console.error('[Metadata] Erreur:', err);
callback(null);
}
}


async function addSource(type, name, path, config) {
try {
const res = await fetch(`${API}/api/sources`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ name, type, path, config })
});
const data = await res.json();
if (!res.ok) {
showToast(data.error || I18N.t('toast.error'), 'error');
throw new Error(data.error || I18N.t('toast.error'));
}
return true;
} catch (err) {
console.error('[addSource]', err);
return false;
}
}
// ---------------------------------------------------------------------------
// Instances Stellio — échange direct de fichiers entre deux installations sur
// le même réseau local (voir _get_or_create_local_peer_key côté backend pour
// le modèle de confiance : appairage manuel par clé partagée, pas de vraie
// découverte mDNS/Bonjour automatique).
// ---------------------------------------------------------------------------

async function loadRemoteInstances() {
    try {
        const res = await fetch(`${API}/api/remote-instances`);
        if (!res.ok) throw new Error('http');
        const data = await res.json();
        const keyInput = document.getElementById('local-peer-key-display');
        if (keyInput) keyInput.value = data.local_peer_key || '';
        _renderRemoteInstances(data.instances || []);
    } catch (e) {
        console.error('[RemoteInstances]', e);
    }
}
window.loadRemoteInstances = loadRemoteInstances;

function _renderRemoteInstances(instances) {
    const container = document.getElementById('remote-instances-list');
    if (!container) return;
    if (!instances.length) {
        container.innerHTML = `<div class="empty-state small"><p>${_t2('settings.remote_instances_none', 'Aucune instance configurée')}</p></div>`;
        return;
    }
    const statusColors = { online: '#4ade80', offline: '#9ca3af', error: '#f87171' };
    container.innerHTML = instances.map(inst => `
        <div class="source-item" data-id="${inst.id}">
            <div class="source-info">
                <div class="source-icon"><i class="fa-solid fa-network-wired" style="color:${statusColors[inst.last_status] || '#9ca3af'};"></i></div>
                <div class="source-details">
                    <h4>${escapeHtml(inst.name)}</h4>
                    <p>${escapeHtml(inst.url)}</p>
                </div>
            </div>
            <button class="btn btn-ghost btn-sm" onclick="pingRemoteInstance(${inst.id})" data-i18n-title="settings.remote_instances_test" title="Tester la connexion"><i class="fa-solid fa-plug"></i></button>
            <button class="btn btn-ghost btn-sm" onclick="deleteRemoteInstance(${inst.id})" title="${I18N.t('actions.delete')}"><i class="fa-solid fa-trash"></i></button>
        </div>
    `).join('');
    I18N.apply();
}

function copyLocalPeerKey() {
    const input = document.getElementById('local-peer-key-display');
    if (!input || !input.value) return;
    navigator.clipboard.writeText(input.value).then(() => {
        showToast(_t2('toast.copied', 'Copié !'), 'success');
    }).catch(() => {});
}
window.copyLocalPeerKey = copyLocalPeerKey;

async function openAddRemoteInstanceModal() {
    document.getElementById('add-remote-instance-form')?.reset();
    const select = document.getElementById('remote-instance-inbox');
    if (select) {
        select.innerHTML = `<option value="" data-i18n="settings.remote_instances_inbox_default">${_t2('settings.remote_instances_inbox_default', 'Première source dossier disponible')}</option>`;
        try {
            const res = await fetch(`${API}/api/sources`);
            if (res.ok) {
                const sources = await res.json();
                sources.filter(s => s.type === 'folder').forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.path;
                    opt.textContent = s.name;
                    select.appendChild(opt);
                });
            }
        } catch (e) { /* select reste sur l'option par défaut */ }
    }
    openModal('modal-add-remote-instance');
}
window.openAddRemoteInstanceModal = openAddRemoteInstanceModal;

document.getElementById('add-remote-instance-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = {
        name: document.getElementById('remote-instance-name').value.trim(),
        url: document.getElementById('remote-instance-url').value.trim(),
        peer_key: document.getElementById('remote-instance-peer-key').value.trim(),
        inbox_folder: document.getElementById('remote-instance-inbox').value,
    };
    try {
        const res = await fetch(`${API}/api/remote-instances`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
        });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || _t2('toast.connection_error', 'Erreur de connexion'), 'error'); return; }
        closeModal('modal-add-remote-instance');
        showToast(_t2('settings.remote_instances_added', 'Instance ajoutée'), 'success');
        loadRemoteInstances();
    } catch (err) {
        showToast(_t2('toast.connection_error', 'Erreur de connexion'), 'error');
    }
});

async function pingRemoteInstance(id) {
    showToast(_t2('settings.remote_instances_testing', 'Test en cours...'), 'info');
    try {
        const res = await fetch(`${API}/api/remote-instances/${id}/ping`, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'online') {
            showToast(_t2('settings.remote_instances_online', `En ligne (${data.remote?.name || '?'})`, { name: data.remote?.name || '?' }), 'success');
        } else {
            showToast(data.error || _t2('settings.remote_instances_offline', 'Instance injoignable'), 'error');
        }
        loadRemoteInstances();
    } catch (e) {
        showToast(_t2('toast.connection_error', 'Erreur de connexion'), 'error');
    }
}
window.pingRemoteInstance = pingRemoteInstance;

async function deleteRemoteInstance(id) {
    const ok = await showConfirmDialog(_t2('settings.remote_instances_delete_confirm', 'Supprimer cette instance ?'));
    if (!ok) return;
    try {
        const res = await fetch(`${API}/api/remote-instances/${id}`, { method: 'DELETE' });
        if (res.ok) { showToast(_t2('toast.deleted', 'Supprimé'), 'success'); loadRemoteInstances(); }
    } catch (e) {
        showToast(_t2('toast.connection_error', 'Erreur de connexion'), 'error');
    }
}
window.deleteRemoteInstance = deleteRemoteInstance;

async function sendFileToRemoteInstance(filePath) {
    let instances = [];
    try {
        const res = await fetch(`${API}/api/remote-instances`);
        if (res.ok) instances = (await res.json()).instances || [];
    } catch (e) { /* liste vide, message ci-dessous */ }
    if (!instances.length) {
        showToast(_t2('settings.remote_instances_none_configured', "Aucune instance Stellio configurée — ajoute-en une dans Paramètres."), 'info');
        return;
    }
    if (instances.length === 1) {
        _doSendToRemoteInstance(filePath, instances[0]);
        return;
    }
    _openSendToInstancePicker(filePath, instances);
}
window.sendFileToRemoteInstance = sendFileToRemoteInstance;

function _openSendToInstancePicker(filePath, instances) {
    let modal = document.getElementById('modal-send-to-instance');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modal-send-to-instance';
        modal.className = 'modal hidden';
        modal.innerHTML = `
            <div class="modal-content" style="max-width:360px;">
                <div class="modal-header">
                    <h3><i class="fa-solid fa-network-wired"></i> <span data-i18n="settings.remote_instances_send_pick">Envoyer vers quelle instance ?</span></h3>
                    <button class="modal-close" onclick="closeModal('modal-send-to-instance')">×</button>
                </div>
                <div class="modal-body">
                    <select id="send-to-instance-select" class="settings-select" style="width:100%;"></select>
                    <button id="send-to-instance-confirm-btn" class="btn btn-primary" style="width:100%; margin-top:12px;">
                        <i class="fa-solid fa-paper-plane"></i> <span data-i18n="actions.send">Envoyer</span>
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    const select = modal.querySelector('#send-to-instance-select');
    select.innerHTML = instances.map((inst, i) => `<option value="${i}">${escapeHtml(inst.name)}</option>`).join('');
    modal.querySelector('#send-to-instance-confirm-btn').onclick = () => {
        const chosen = instances[parseInt(select.value, 10)];
        closeModal('modal-send-to-instance');
        _doSendToRemoteInstance(filePath, chosen);
    };
    openModal('modal-send-to-instance');
}

async function _doSendToRemoteInstance(filePath, target) {
    showToast(_t2('settings.remote_instances_sending', `Envoi vers ${target.name}...`, { name: target.name }), 'info');
    try {
        const res = await fetch(`${API}/api/remote-instances/${target.id}/send`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ file_path: filePath })
        });
        const data = await res.json();
        showToast(res.ok
            ? _t2('settings.remote_instances_sent', `Envoyé vers ${target.name}`, { name: target.name })
            : (data.error || _t2('settings.remote_instances_send_error', "Échec de l'envoi")), res.ok ? 'success' : 'error');
    } catch (e) {
        showToast(_t2('settings.remote_instances_send_error', "Échec de l'envoi"), 'error');
    }
}

async function loadSources() {
try {
const res = await fetch(`${API}/api/sources`);
if (!res.ok) throw new Error(I18N.t('toast.connection_error'));
renderSources(await res.json());
} catch (err) {
console.error('[loadSources]', err);
document.getElementById('sources-list').innerHTML = `<div class="empty-state small"><p>${I18N.t('toast.connection_error')}</p></div>`;
}
}
function renderSources(sources) {
const container = document.getElementById('sources-list');
if (!sources?.length) {
container.innerHTML = `<div class="empty-state small"><p>${I18N.t('settings.no_sources')}</p></div>`;
return;
}
const icons = { folder: 'fa-folder', file: 'fa-file', smb: 'fa-network-wired', nfs: 'fa-server' };
container.innerHTML = sources.map(s => `<div class="source-item" data-id="${s.id}"><div class="source-info"><div class="source-icon"><i class="fa-solid ${icons[s.type] || 'fa-database'}"></i></div><div class="source-details"><div style="display: flex; align-items: center; gap: 8px;"><h4>${escapeHtml(s.name)}</h4><button class="btn btn-ghost btn-sm" onclick="editSourceName(${s.id}, '${escapeJs(s.name)}')" title="${I18N.t('modal.rename_source')}"><i class="fa-solid fa-pen"></i></button></div><p>${escapeHtml(s.path)}</p></div></div><button class="btn btn-ghost btn-sm" onclick="deleteSource(${s.id})" title="${I18N.t('actions.delete')}"><i class="fa-solid fa-trash"></i></button></div>`).join('');
I18N.apply();
}
window.editSourceName = (id, currentName) => {
document.getElementById('rename-source-id').value = id;
document.getElementById('rename-source-name').value = currentName;
openModal('modal-rename-source');
setTimeout(() => {
const input = document.getElementById('rename-source-name');
input.focus();
input.select();
}, 100);
};
let confirmCallback = null;
function showConfirmModal(message, onConfirm) {
document.getElementById('confirm-message').textContent = message;
openModal('modal-confirm');
confirmCallback = onConfirm;
document.getElementById('confirm-ok-btn').onclick = () => {
closeModal('modal-confirm');
if (confirmCallback) { confirmCallback(); confirmCallback = null; }
};
document.getElementById('confirm-cancel-btn').onclick = () => {
closeModal('modal-confirm');
confirmCallback = null;
};
}
async function deleteSource(id) {
showConfirmModal(I18N.t('toast.delete_source'), async () => {
try {
const res = await fetch(`${API}/api/sources/${id}`, { method: 'DELETE' });
if (res.ok) {
showToast(I18N.t('toast.source_deleted'), 'success');
loadSources();
setTimeout(() => loadFiles(), 1500);
} else {
const data = await res.json();
showToast(data.error || I18N.t('toast.error'), 'error');
}
} catch (err) {
showToast(I18N.t('toast.network_error'), 'error');
console.error(err);
}
});
}


let scanPollingInterval = null;
let scanBadgeElement = null;
async function loadFiles() {
const authScreen = document.getElementById('auth-screen');
const appScreen = document.getElementById('app-screen');
if (authScreen && !authScreen.classList.contains('hidden')) return;
if (appScreen && appScreen.classList.contains('hidden')) return;
try {
const tagParams = activeTagFilters.size > 0 ? `?tags=${encodeURIComponent([...activeTagFilters].join(','))}` : '';
const res = await fetch(`${API}/api/files${tagParams}`);
if (res.status === 401) return;
if (!res.ok) {
const errorText = await res.text();
throw new Error(`${I18N.t('toast.server_error')}: ${res.status} - ${errorText.substring(0, 100)}`);
}
    const data = await res.json();
    if (!Array.isArray(data)) throw new Error(I18N.t('toast.parse_error'));

    allFiles = data;
    filteredFiles = showFavoritesOnly ? allFiles.filter(f => favoriteFiles.has(f.path)) : [...allFiles];
    applySorting();
    renderFiles();
    setTimeout(() => generateVisibleThumbnails(), 200);
    updateSidebarCounts(filteredFiles);
    updateFooterCounts();

    console.log(`✅ ${allFiles.length} fichiers chargés depuis le cache`);

     if (!scanPollingInterval) {
        pollScanProgress();
    }
} catch (err) {
    if (err.message?.includes('401')) return;
    console.error('❌ [loadFiles]', err);
    showToast(`${I18N.t('toast.error')}: ${err.message}`, 'error');
    document.getElementById('files-grid').innerHTML = `<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><p>${I18N.t('toast.connection_error')}</p><button onclick="loadFiles()" class="btn btn-primary" style="margin-top:10px;"><i class="fa-solid fa-rotate-right"></i> ${I18N.t('toast.refreshing')}</button></div>`;
}
}
async function pollScanProgress() {
if (scanPollingInterval) {
clearInterval(scanPollingInterval);
scanPollingInterval = null;
}
let lastFound = 0;
let lastStatus = '';
let noChangeCount = 0;
showScanBadge(I18N.t('scan.checking'));

scanPollingInterval = setInterval(async () => {
    try {
        const res = await fetch(`${API}/api/scan/delta`);
        if (!res.ok) {
            clearInterval(scanPollingInterval);
            scanPollingInterval = null;
            hideScanBadge();
            return;
        }
        const data = await res.json();

        if (data.status === 'done' || data.status === 'idle') {
             noChangeCount++;
            if (noChangeCount >= 5 || data.found === 0) {
                clearInterval(scanPollingInterval);
                scanPollingInterval = null;
                hideScanBadge();
                return;
            }
        } else {
            noChangeCount = 0;
        }

        if (data.status === 'scanning' && (data.found !== lastFound || data.status !== lastStatus)) {
            lastFound = data.found;
            lastStatus = data.status;
            updateScanBadge(I18N.t('scan.in_progress', { count: data.found }));

            if (data.new_files && data.new_files.length > 0) {
                allFiles = allFiles.concat(data.new_files);
                filteredFiles = showFavoritesOnly ? allFiles.filter(f => favoriteFiles.has(f.path)) : [...allFiles];
                applySorting();
                renderFiles();
                generateVisibleThumbnails();
                updateSidebarCounts(filteredFiles);
                updateFooterCounts();
            }
        } else if (data.status === 'done') {
            clearInterval(scanPollingInterval);
             scanPollingInterval = null;

            if (data.found > 0) {
                updateScanBadge(I18N.t('scan.done', { count: data.found }), 'success');
                setTimeout(() => hideScanBadge(), 4000);
            } else {
                hideScanBadge();
            }
        }
    } catch (e) {
        console.debug('[Scan] Erreur polling:', e);
    }
 }, 1000);

setTimeout(() => {
    if (scanPollingInterval) {
        clearInterval(scanPollingInterval);
        scanPollingInterval = null;
        hideScanBadge();
    }
}, 30000);
}
function updateScanBadge(text, type = 'info') {
if (!scanBadgeElement) {
showScanBadge(text, type);
return;
}
const span = scanBadgeElement.querySelector('span');
if (span && span.textContent !== text) {
span.textContent = text;
}
if (type === 'success' && scanBadgeElement.style.borderColor !== 'var(--success)') {
    scanBadgeElement.style.borderColor = 'var(--success)';
    const icon = scanBadgeElement.querySelector('i');
    if (icon) {
        icon.className = 'fa-solid fa-check-circle';
        icon.style.color = 'var(--success)';
    }
}
}
function showScanBadge(text, type = 'info') {
if (!scanBadgeElement) {
scanBadgeElement = document.createElement('div');
scanBadgeElement.id = 'scan-progress-badge';
scanBadgeElement.style.cssText = `background: var(--bg-secondary); color: var(--text-primary); padding: 12px 18px; border-radius: 12px; font-size: 13px; font-weight: 500; box-shadow: 0 4px 20px rgba(0,0,0,0.4); display: flex; align-items: center; gap: 10px; border: 1px solid var(--accent); animation: slideUp 0.3s ease; max-width: 350px; align-self: flex-end; transition: opacity 0.3s ease;`;
const container = document.getElementById('toast-container');
(container || document.body).appendChild(scanBadgeElement);
}
requestAnimationFrame(() => {
const icon = type === 'success' ? '<i class="fa-solid fa-check-circle" style="color:var(--success);"></i>' : '<i class="fa-solid fa-radar fa-spin" style="color:var(--accent);"></i>';
scanBadgeElement.innerHTML = `${icon} <span>${text}</span>`;
scanBadgeElement.style.display = 'flex';
scanBadgeElement.style.opacity = '1';
if (type === 'success') {
scanBadgeElement.style.borderColor = 'var(--success)';
} else {
scanBadgeElement.style.borderColor = 'var(--accent)';
}
});
}
function hideScanBadge() {
if (scanBadgeElement) {
scanBadgeElement.style.opacity = '0';
scanBadgeElement.style.transition = 'opacity 0.3s ease';
setTimeout(() => {
if (scanBadgeElement) {
scanBadgeElement.remove();
scanBadgeElement = null;
}
}, 300);
}
}
function updateFooterCounts() {
const countEl = document.getElementById('file-count-display');
const updateEl = document.getElementById('last-update');
if (countEl) {
const count = filteredFiles.length;
countEl.textContent = `${I18N.tp('common.file_count', count, { count })}`;
}
if (updateEl) {
updateEl.textContent = `${I18N.t('footer.updated')} ${new Date().toLocaleTimeString(I18N.lang, { hour: '2-digit', minute: '2-digit' })}`;
}
}
function applySorting() {
if (currentSort.startsWith('tag')) {
filteredFiles.sort((a, b) => {
const tagA = (a.tags?.length > 0) ? a.tags[0].name.toLowerCase() : 'zzz';
const tagB = (b.tags?.length > 0) ? b.tags[0].name.toLowerCase() : 'zzz';
return currentSort === 'tag-asc' ? tagA.localeCompare(tagB) : tagB.localeCompare(tagA);
});
} else if (currentSort.startsWith('folder')) {
filteredFiles.sort((a, b) => {
const getFolder = p => (p.split('/').filter(Boolean).slice(0, -1).join('/') || '/');
const folderA = getFolder(a.path);
const folderB = getFolder(b.path);
if (folderA !== folderB) return currentSort === 'folder-asc' ? folderA.localeCompare(folderB) : folderB.localeCompare(folderA);
return currentSort === 'folder-asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name);
});
} else {
filteredFiles.sort((a, b) => {
switch (currentSort) {
case 'name-asc': return a.name.localeCompare(b.name);
case 'name-desc': return b.name.localeCompare(a.name);
case 'size-asc': return (a.size || 0) - (b.size || 0);
case 'size-desc': return (b.size || 0) - (a.size || 0);
case 'date-desc': return (b.mtime || 0) - (a.mtime || 0);
case 'date-asc': return (a.mtime || 0) - (b.mtime || 0);
default: return 0;
}
});
}
}


let thumbProgressInterval = null;
let thumbProgressCompleted = false;
function startThumbProgressMonitor() {
if (thumbProgressInterval) clearInterval(thumbProgressInterval);
const container = document.getElementById('thumb-progress-container');
const progressBar = document.getElementById('thumb-progress-bar');
const progressText = document.getElementById('thumb-progress-text');
if (!container || !progressBar || !progressText) return;

let lastProgress = -1;
let lastPending = -1;

thumbProgressInterval = setInterval(async () => {
    try {
        const res = await fetch(`${API}/api/thumb/progress`);
        if (!res.ok) return;

        const data = await res.json();

        if (data.progress === lastProgress && data.pending === lastPending) {
            if (data.files_without_thumb === 0 && data.pending === 0) {
                if (!container.classList.contains('completed')) {
                    container.classList.add('completed');
                    progressText.textContent = `${data.files_with_thumb}/${data.total}`;
                    setTimeout(() => {
                        container.classList.add('hidden');
                    }, 5000);
                }
                clearInterval(thumbProgressInterval);
                 thumbProgressInterval = null;
            }
            return;
        }

        lastProgress = data.progress;
        lastPending = data.pending;

        if (data.is_generating || data.files_without_thumb > 0) {
            container.classList.remove('hidden');
            container.classList.remove('completed');

            requestAnimationFrame(() => {
                progressBar.style.width = `${data.progress}%`;
                progressText.textContent = `${data.files_with_thumb}/${data.total} (${data.pending} en attente)`;
            });

            if (data.files_without_thumb === 0 && data.pending === 0) {
                container.classList.add('completed');
                progressText.textContent = `${data.files_with_thumb}/${data.total}`;
                 clearInterval(thumbProgressInterval);
                thumbProgressInterval = null;
                setTimeout(() => {
                    container.classList.add('hidden');
                }, 5000);
            }
        } else {
            container.classList.add('hidden');
            clearInterval(thumbProgressInterval);
            thumbProgressInterval = null;
        }
    } catch (err) {
        console.debug('[ThumbProgress] Erreur:', err);
    }
}, 2000);
}


function renderFileCard(f, icons) {
const ext = f.extension || '';
const icon = icons[ext] || 'fa-file';
const thumbUrl = `${API}/api/thumb?path=${encodeURIComponent(f.path)}${f.thumb_mtime ? '&t=' + f.thumb_mtime : (f.mtime ? '&t=' + Math.floor(f.mtime) : '')}`;
const isFav = favoriteFiles.has(f.path);
const isArchive = ['.zip', '.rar', '.7z', '.tar.gz', '.tgz'].includes(ext.toLowerCase());
const inArchive = !!f.in_archive;
const archiveEntryHtml = (isArchive && f.archive_entry_count !== undefined)
    ? `<span class="file-archive-badge" title="${f.archive_entry_count} fichier(s) 3D détecté(s)">️ <i class="fa-solid fa-magnifying-glass"></i> ${f.archive_entry_count}</span>`
    : (isArchive ? `<span class="file-archive-badge"><i class="fa-solid fa-box-archive"></i> ${I18N.t('card.archive_label') || 'Archive'}</span>` : '');
const inArchiveBadgeHtml = inArchive
    ? `<span class="file-in-archive-badge" title="${escapeHtml(f.archive_name || '')}"><i class="fa-solid fa-box-archive"></i> ${escapeHtml(f.archive_name || '')}</span>`
    : '';
const extractEntryBtnHtml = inArchive
    ? `<button type="button" class="file-decompress-btn" onclick="extractArchiveEntry('${escapeJs(f.archive_path)}', '${escapeJs(f.internal_path)}', event)" title="${I18N.t('actions.extract_single_file') || 'Extraire uniquement ce fichier'}"><i class="fa-solid fa-download"></i></button>`
    : '';
const isSelected = selectedFiles.has(f.path);
const NEW_THRESHOLD_S = 48 * 3600;
const isNew = f.mtime && (Date.now() / 1000 - f.mtime) < NEW_THRESHOLD_S && !seenFilesSet.has(f.path);
const newBadgeHtml = isNew ? `<span class="file-new-badge"><i class="fa-solid fa-sparkles"></i> Nouveau</span>` : '';
const multiPlateLabel = I18N.t('card.multi_plate') || 'Plateau multiple';
const multiPlateBadgeHtml = f.multi_plate
    ? `<span class="file-multiplate-badge" title="${multiPlateLabel}"><i class="fa-solid fa-table-cells"></i></span>`
    : '';
const tooltipHtml = `<div class="file-metadata-tooltip" id="tooltip-${f.path.replace(/[^\w]/g, '-')}"><div class="meta-row"><i class="fa-solid fa-ruler-combined"></i><span id="dims-${f.path.replace(/[^\w]/g, '-')}">${I18N.t('library.loading')}</span></div><div class="meta-row"><i class="fa-solid fa-weight-scale"></i><span id="weight-${f.path.replace(/[^\w]/g, '-')}">PLA: -g • PETG: -g</span></div><div class="meta-row"><i class="fa-solid fa-clock"></i><span id="time-${f.path.replace(/[^\w]/g, '-')}">~--</span></div></div>`;
const thumbContent = f.has_thumb
    ? `<img src="${thumbUrl}" data-loaded="pending" onload="this.dataset.loaded='true'; this.style.display='block'; this.nextElementSibling?.style.setProperty('display','none','important');" onerror="window.handleThumbnailError(this)" style="width:100%; height:100%; object-fit:cover; display:block;"><div class="file-loading" style="display:none; align-items:center; justify-content:center;"><i class="fa-solid ${icon} thumb-icon" style="font-size:48px; color:var(--text-muted);"></i></div>`
    : `<img src="" data-loaded="false" style="display:none; width:100%; height:100%; object-fit:cover;"><div class="file-loading thumb-pending" data-path="${escapeHtml(f.path)}" style="display:flex; align-items:center; justify-content:center; flex-direction:column; gap:8px;"><i class="fa-solid fa-spinner fa-spin" style="font-size:32px; color:var(--text-muted); opacity:0.6;"></i></div>`;
const checkboxHtml = isSelectionMode ? `<div class="file-checkbox" onclick="event.stopPropagation(); toggleFileSelection('${escapeJs(f.path)}', event)" title="${isSelected ? I18N.t('actions.cancel') : I18N.t('actions.select')}"><i class="fa-solid ${isSelected ? 'fa-check-square' : 'fa-square'}"></i></div>` : '';
const fileMenuBtnHtml = isSelectionMode ? '' : `<button type="button" class="file-menu-btn" onclick="event.stopPropagation(); openFileCtxMenu(event, '${escapeJs(f.path)}', '${escapeJs(f.name)}')" title="${I18N.t('actions.more') || 'Actions'}"><i class="fa-solid fa-bars"></i></button>`;
const viewerClick = `onclick="open3DViewer('${escapeJs(f.name)}', '${escapeJs(f.path)}', ${f.plate_count || 1})" style="cursor:pointer;"`;
const selectedClass = isSelected ? ' selected' : '';
if (currentView === 'details') {
    const dirPath = escapeHtml(f.path.replace(/\\/g, '/').split('/').slice(0, -1).join('/') || I18N.t('source.local_folder'));
    const sizeStr = formatSize(f.size || 0);
    const safeId = f.path.replace(/[^\w]/g, '-');
    return `<div class="file-card file-card--details${selectedClass}" data-name="${escapeHtml(f.name)}" data-path="${escapeHtml(f.path)}" ${viewerClick}>
  <div class="dv-thumb">${checkboxHtml}${thumbContent}${isNew ? `<span class="file-new-badge file-new-badge--small"><i class="fa-solid fa-sparkles"></i></span>` : ''}${inArchiveBadgeHtml}${multiPlateBadgeHtml}</div>
  <div class="dv-name">
    <span class="dv-filename" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</span>
    <span class="dv-path" title="${dirPath}"><i class="fa-solid fa-folder"></i> ${dirPath}</span>
  </div>
  <div class="dv-tags">${f.tags?.length ? `<div class="file-tags">${f.tags.map(t => `<span class="file-tag" style="background:${t.color}20;color:${t.color};border-color:${t.color}">${escapeHtml(t.name)}</span>`).join('')}</div>` : ''}</div>
  <div class="dv-meta">
    <div class="dv-meta-row"><i class="fa-solid fa-ruler-combined"></i><span id="dims-${safeId}" class="dv-meta-val">—</span></div>
    <div class="dv-meta-row"><i class="fa-solid fa-weight-scale"></i><span id="weight-${safeId}" class="dv-meta-val">—</span></div>
    <div class="dv-meta-row"><i class="fa-solid fa-clock"></i><span id="time-${safeId}" class="dv-meta-val">—</span></div>
  </div>
  <div class="dv-size">${sizeStr}</div>
  <div class="dv-actions">
    ${isArchive ? `<button type="button" class="dv-btn" onclick="event.stopPropagation(); decompressFile('${escapeJs(f.path)}', event)" title="${I18N.t('toast.extract_success')}"><i class="fa-solid fa-file-zipper"></i></button>` : ''}
    ${extractEntryBtnHtml}
    <button type="button" class="dv-btn dv-btn--star ${isFav ? 'favorited' : ''}" onclick="event.stopPropagation(); toggleFavorite('${escapeJs(f.path)}', event)" title="${isFav ? I18N.t('toast.favorites_removed') : I18N.t('toast.favorites_added')}"><i class="${isFav ? 'fa-solid' : 'fa-regular'} fa-star"></i></button>
    <button type="button" class="dv-btn dv-btn--menu" onclick="event.stopPropagation(); openFileCtxMenu(event, '${escapeJs(f.path)}', '${escapeJs(f.name)}')" title="${I18N.t('actions.more') || 'Actions'}"><i class="fa-solid fa-ellipsis-vertical"></i></button>
  </div>
</div>`;
}
const isVirtualEntry = f.path.includes('::');
const deleteBtnHtml = (!isVirtualEntry && !isSelectionMode)
    ? `<button type="button" class="file-delete-btn" onclick="event.stopPropagation(); openDeleteFileModal('${escapeJs(f.path)}', '${escapeJs(f.name)}')" title="${I18N.t('actions.delete') || 'Supprimer'}"><i class="fa-solid fa-xmark"></i></button>`
    : '';
return `<div class="file-card${selectedClass}" data-name="${escapeHtml(f.name)}" data-path="${escapeHtml(f.path)}" ${viewerClick}><div class="file-thumb" style="position:relative;">${checkboxHtml}${fileMenuBtnHtml}${thumbContent}${tooltipHtml}<span class="file-ext-badge">${ext.replace('.', '')}</span>${deleteBtnHtml}${isArchive ? archiveEntryHtml : ''}${inArchiveBadgeHtml}${multiPlateBadgeHtml}${isNew ? newBadgeHtml : ''}${isArchive ? `<button type="button" class="file-decompress-btn" onclick="event.stopPropagation(); decompressFile('${escapeJs(f.path)}', event)" title="${I18N.t('toast.extract_success')}"><i class="fa-solid fa-file-zipper"></i> ${I18N.t('actions.add')}</button>` : ''}${inArchive ? `<button type="button" class="file-decompress-btn" onclick="event.stopPropagation(); extractArchiveEntry('${escapeJs(f.archive_path)}', '${escapeJs(f.internal_path)}', event)" title="${I18N.t('actions.extract_single_file') || 'Extraire uniquement ce fichier'}"><i class="fa-solid fa-download"></i></button>` : ''}<button type="button" class="file-favorite-btn ${isFav ? 'favorited' : ''}" onclick="toggleFavorite('${escapeJs(f.path)}', event); return false;" title="${isFav ? I18N.t('toast.favorites_removed') : I18N.t('toast.favorites_added')}"><i class="${isFav ? 'fa-solid' : 'fa-regular'} fa-star"></i></button><button type="button" class="file-tag-btn" onclick="event.stopPropagation(); openTagModal('${escapeJs(f.path)}')" title="${I18N.t('modal.manage_tags')}"><i class="fa-solid fa-tag"></i></button></div><div class="file-info"><div class="file-name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</div>${f.tags?.length ? `<div class="file-tags">${f.tags.map(t => `<span class="file-tag" style="background:${t.color}20;color:${t.color};border-color:${t.color}">${escapeHtml(t.name)}</span>`).join('')}</div>` : ''}</div></div>`;
}


window.toggleSelectionMode = function () {
isSelectionMode = !isSelectionMode;
selectedFiles.clear();
const btn = document.getElementById('select-all-btn');
if (btn) {
btn.classList.toggle('active', isSelectionMode);
btn.innerHTML = isSelectionMode ? `<i class="fa-solid fa-times"></i> ${I18N.t('actions.cancel')}` : `<i class="fa-solid fa-square-check"></i> ${I18N.t('actions.select')}`;
}
const actionBar = document.getElementById('selection-action-bar');
if (actionBar) actionBar.style.display = isSelectionMode ? 'flex' : 'none';
renderFiles();
updateSelectionCount();
};
window.toggleFileSelection = function (filePath, event) {
if (event) {
event.preventDefault();
event.stopPropagation();
}
if (selectedFiles.has(filePath)) selectedFiles.delete(filePath);
else selectedFiles.add(filePath);
renderFiles();
updateSelectionCount();
};
window.selectAllFiles = function () {
if (selectedFiles.size === filteredFiles.length) selectedFiles.clear();
else filteredFiles.forEach(f => selectedFiles.add(f.path));
renderFiles();
updateSelectionCount();
};
function updateSelectionCount() {
const countEl = document.getElementById('selection-count');
if (countEl) {
countEl.textContent = `${I18N.tp('common.file_count', selectedFiles.size, { count: selectedFiles.size })} ${I18N.t('actions.select').toLowerCase()}`;
}
}
window.sendSelectedToSlicer = async function () {
if (selectedFiles.size === 0) {
showToast(I18N.t('toast.no_selection'), 'warning');
return;
}
try {
const res = await fetch(`${API}/api/slicer/send-batch`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({
    files: [...selectedFiles],
    printer_id: document.getElementById('batch-slicer-printer-select')?.value || null
})
});
const data = await res.json();
if (res.ok) {
showToast(data.message || `${selectedFiles.size} ${I18N.t('toast.files_sent')}`, 'success');
if (data.stock_warnings && data.stock_warnings.length) data.stock_warnings.forEach(_showStockWarningToast);
selectedFiles.clear();
toggleSelectionMode();
} else {
showToast(data.error || I18N.t('toast.send_error'), 'error');
}
} catch (err) {
showToast(I18N.t('toast.connection_error'), 'error');
console.error('[Batch Slicer]', err);
}
};


window.deleteSelectedFiles = async function () {
if (selectedFiles.size === 0) {
showToast(I18N.t('toast.no_selection'), 'warning');
return;
}
const count = selectedFiles.size;
const confirmed = await showConfirmDialog(
    I18N.tp('modal.delete_selected_confirm', count, { count }) || `Supprimer définitivement ${count} fichier(s) ? Cette action est irréversible.`,
    { title: I18N.t('actions.delete') || 'Supprimer', confirmLabel: I18N.t('actions.delete') || 'Supprimer', danger: true }
);
if (!confirmed) return;

try {
const res = await fetch(`${API}/api/files/delete-batch`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ file_paths: [...selectedFiles] })
});
const data = await res.json();
if (res.ok) {
if (data.deleted_count > 0) {
showToast(I18N.tp('toast.files_deleted', data.deleted_count, { count: data.deleted_count }) || `${data.deleted_count} fichier(s) supprimé(s)`, 'success');
}
if (data.errors && data.errors.length > 0) {
showToast(`${data.errors.length} ${I18N.t('toast.delete_partial_error') || "fichier(s) n'ont pas pu être supprimés"}`, 'warning');
console.warn('[Batch Delete] Erreurs:', data.errors);
}
selectedFiles.clear();
toggleSelectionMode();
if (typeof loadFiles === 'function') loadFiles();
} else {
showToast(data.error || I18N.t('toast.delete_error'), 'error');
}
} catch (err) {
showToast(I18N.t('toast.connection_error'), 'error');
console.error('[Batch Delete]', err);
}
};


window.regenSelectedThumbnails = async function () {
if (selectedFiles.size === 0) {
showToast(I18N.t('toast.no_selection'), 'warning');
return;
}
const paths = [...selectedFiles];
paths.forEach(filePath => {
const card = document.querySelector(`.file-card[data-path="${CSS.escape(filePath)}"]`);
if (card) {
    const img = card.querySelector('.file-thumb img, .dv-thumb img');
    const loader = card.querySelector('.file-loading');
    if (img) { img.src = ''; img.style.display = 'none'; img.dataset.loaded = 'false'; }
    if (loader) loader.style.display = 'flex';
}
});
showToast(`${I18N.tp('common.file_count', paths.length, { count: paths.length })}${I18N.t('toast.regen_launched_suffix')}`, 'info');
try {
const res = await fetch(`${API}/api/thumb/regen-batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths })
});
const data = await res.json();
if (!res.ok) { showToast(data.error || I18N.t('toast.thumb_gen_error'), 'error'); return; }

const pending = new Set(paths);
let attempts = 0;
const maxAttempts = 60;

const poll = setInterval(async () => {
    attempts++;
    if (pending.size === 0) { clearInterval(poll); return; }
    try {
        const check = await fetch(`${API}/api/thumb/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paths: [...pending] })
        });
        const checkData = await check.json();
        (checkData.results || []).forEach(r => {
            if (!r.ready) return;
            pending.delete(r.path);
            const card = document.querySelector(`.file-card[data-path="${CSS.escape(r.path)}"]`);
            if (card) {
                const img = card.querySelector('.file-thumb img, .dv-thumb img');
                const loader = card.querySelector('.file-loading');
                const newSrc = `${API}/api/thumb?path=${encodeURIComponent(r.path)}&t=${Date.now()}`;
                const testImg = new Image();
                testImg.onload = () => {
                    if (img) { img.src = newSrc; img.style.display = 'block'; img.dataset.loaded = 'true'; }
                    if (loader) loader.style.display = 'none';
                };
                testImg.src = newSrc;
            }
            const f = allFiles.find(file => file.path === r.path);
            if (f) { f.has_thumb = true; f.thumb_mtime = r.thumb_mtime; }
        });
        if (pending.size === 0) {
            clearInterval(poll);
            showToast(I18N.t('toast.thumb_regenerated') || 'Miniatures régénérées', 'success');
        } else if (attempts >= maxAttempts) {
            clearInterval(poll);
            showToast(`${I18N.t('toast.timeout_retry')} (${pending.size} restante(s))`, 'warning');
        }
    } catch { clearInterval(poll); }
}, 2000);
} catch (err) {
showToast(I18N.t('toast.connection_error'), 'error');
console.error('[Batch Thumb Regen]', err);
}
};


function renderFiles(chunkSize = 50) {
const grid = document.getElementById('files-grid');
if (!filteredFiles?.length) {
grid.innerHTML = `<div class="empty-state"><i class="fa-solid fa-inbox"></i><p>${I18N.t('library.no_files')}</p></div>`;
I18N.apply();
return;
}
const icons = { '.stl': 'fa-cube', '.3mf': 'fa-file-lines', '.obj': 'fa-shapes' };
const isFolderSort = currentSort.startsWith('folder');
const isTagSort = currentSort.startsWith('tag');
let lastGroup = '';
const getFolderName = path => (path.split('/').filter(Boolean).slice(0, -1).join('/') || '/');
const filesToRender = [];
if (isFolderSort) {
    const filesByFolder = {};
    filteredFiles.forEach(f => {
        const folder = getFolderName(f.path);
        if (!filesByFolder[folder]) filesByFolder[folder] = [];
        filesByFolder[folder].push(f);
    });
    const sortedFolders = Object.keys(filesByFolder).sort((a, b) =>
        currentSort === 'folder-asc' ? a.localeCompare(b) : b.localeCompare(a)
    );
    const topLevel = [];
    const used = new Set();
    sortedFolders.forEach(folder => {
        const isChild = sortedFolders.some(other => other !== folder && folder.startsWith(other + '/'));
        if (!isChild) topLevel.push(folder);
    });
    topLevel.forEach(topFolder => {
        const children = sortedFolders.filter(f => f !== topFolder && f.startsWith(topFolder + '/'));
        const files = filesByFolder[topFolder].sort((a, b) =>
            currentSort === 'folder-asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name)
        );
        filesToRender.push({ type: 'folder-block', folder: topFolder, files, children: children.map(c => ({
            folder: c,
            files: (filesByFolder[c] || []).sort((a, b) =>
                currentSort === 'folder-asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name)
            )
        }))});
    });
} else if (isTagSort) {
    filteredFiles.forEach(f => {
        const currentTag = f.tags?.length > 0 ? f.tags[0].name : I18N.t('filters.tags');
        if (currentTag !== lastGroup) {
            lastGroup = currentTag;
            const tagFilesCount = filteredFiles.filter(item => (item.tags?.[0]?.name || I18N.t('filters.tags')) === currentTag).length;
            filesToRender.push({ type: 'tag-header', tag: currentTag, count: tagFilesCount });
        }
         filesToRender.push({ type: 'file', f });
    });
} else {
    filteredFiles.forEach(f => filesToRender.push({ type: 'file', f }));
}

let idx = 0;
grid.innerHTML = '';

function buildFolderBlock(folder, files, children, depth) {
    const previewFiles = files.slice(0, 4);
    const isGallery = currentView === 'gallery';
    const previewThumbs = previewFiles.map(f => {
        const ext = f.name.substring(f.name.lastIndexOf('.')).toLowerCase();
        const thumbUrl = `${API}/api/thumb?path=${encodeURIComponent(f.path)}`;
        return `<div class="folder-preview-thumb"><img src="${thumbUrl}" onerror="this.style.display='none';this.nextSibling.style.display='flex'" loading="lazy"><span class="folder-preview-icon" style="display:none"><i class="fa-solid ${icons[ext] || 'fa-cube'}"></i></span></div>`;
    }).join('');
    const folderLabel = folder.split('/').filter(Boolean).pop() || folder;
    const indent = depth > 0 ? `style="margin-left:${depth * 16}px;"` : '';
    const uid = 'fd_' + Math.random().toString(36).slice(2, 8);
    let subHtml = '';
    if (children && children.length > 0) {
        subHtml = children.map(c => buildFolderBlock(c.folder, c.files, [], depth + 1)).join('');
    }
    const filesHtml = files.map(f => renderFileCard(f, icons)).join('');
    return `<div class="folder-block${depth > 0 ? ' folder-block--child' : ''}" ${indent} data-folder-uid="${uid}">
  <div class="folder-block-header" onclick="toggleFolderBlock('${uid}')">
    <div class="folder-block-previews">${previewThumbs}</div>
    <div class="folder-block-meta">
      <span class="folder-block-name"><i class="fa-solid fa-folder"></i> ${escapeHtml(folderLabel)}</span>
      <span class="folder-block-path">${escapeHtml(folder)}</span>
      <span class="folder-block-count">${I18N.tp('common.file_count', files.length, { count: files.length })}${children && children.length > 0 ? ` · ${I18N.tp('common.subfolder_count', children.length, { count: children.length })}` : ''}</span>
    </div>
    <div class="folder-block-actions">
      <button class="btn btn-ghost btn-sm folder-select-btn" onclick="event.stopPropagation(); selectFolderFiles('${escapeJs(folder)}', this)" title="${I18N.t('actions.select')}"><i class="fa-regular fa-square"></i> ${I18N.t('actions.select')}</button>
      <i class="fa-solid fa-chevron-down folder-block-chevron"></i>
    </div>
  </div>
  <div class="folder-block-content" id="fbc_${uid}">
    ${subHtml}
    <div class="folder-block-grid ${isGallery ? 'gallery' : 'details'}">${filesHtml}</div>
  </div>
</div>`;
}

window.toggleFolderBlock = function(uid) {
    const content = document.getElementById('fbc_' + uid);
    const block = document.querySelector(`[data-folder-uid="${uid}"]`);
    if (!content || !block) return;
    const isOpen = block.classList.contains('folder-block--open');
    if (isOpen) {
        block.classList.remove('folder-block--open');
        content.style.maxHeight = '0';
        content.style.opacity = '0';
    } else {
        block.classList.add('folder-block--open');
        content.style.maxHeight = content.scrollHeight + 5000 + 'px';
        content.style.opacity = '1';
    }
};

function renderChunk() {
    const end = Math.min(idx + chunkSize, filesToRender.length);
    let chunkHtml = '';
    for (let i = idx; i < end; i++) {
        const item = filesToRender[i];
        if (item.type === 'folder-block') {
            chunkHtml += buildFolderBlock(item.folder, item.files, item.children, 0);
        } else if (item.type === 'tag-header') {
            chunkHtml += `<div class="tag-group-header"><i class="fa-solid fa-tag"></i>${escapeHtml(item.tag)}<span class="folder-file-count">${I18N.tp('common.file_count', item.count, { count: item.count })}</span></div>`;
        } else if (item.type === 'file') {
            chunkHtml += renderFileCard(item.f, icons);
        }
    }
    grid.insertAdjacentHTML('beforeend', chunkHtml);
    idx = end;
    if (idx < filesToRender.length) {
        if ('requestIdleCallback' in window) {
            requestIdleCallback(renderChunk, { timeout: 100 });
        } else {
            setTimeout(renderChunk, 0);
        }
    } else {
        I18N.apply();
        setTimeout(() => {
            grid.querySelectorAll('.file-thumb img').forEach(img => {
                if (img.complete && img.naturalWidth === 0) window.handleThumbnailError(img);
            });
        }, 100);
        startPendingThumbPolling();
    }
}
renderChunk();
}


let _pendingThumbTimer = null;
function startPendingThumbPolling() {
    if (_pendingThumbTimer) { clearTimeout(_pendingThumbTimer); _pendingThumbTimer = null; }
    const pending = document.querySelectorAll('.thumb-pending[data-path]');
    if (!pending.length) return;

    async function poll() {
        const stillPending = document.querySelectorAll('.thumb-pending[data-path]');
        if (!stillPending.length) return;

        const paths = Array.from(stillPending).map(el => el.dataset.path);
        try {
            const res = await fetch(`${API}/api/thumb/check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paths })
            });
            if (!res.ok) { _pendingThumbTimer = setTimeout(poll, 2000); return; }
            const data = await res.json();
            let anyUpdated = false;
            for (const { path, ready, url, thumb_mtime } of (data.results || [])) {
                if (!ready) continue;
                const el = document.querySelector(`.thumb-pending[data-path="${CSS.escape(path)}"]`);
                if (!el) continue;
                const img = el.previousElementSibling;
                if (!img || img.tagName !== 'IMG') continue;
                const finalUrl = url + (thumb_mtime ? '&t=' + thumb_mtime : '&t=' + Date.now());
                img.onload = () => {
                    img.style.display = 'block';
                    el.style.display = 'none';
                };
                img.src = finalUrl;
                el.classList.remove('thumb-pending');
                anyUpdated = true;
            }
            const remaining = document.querySelectorAll('.thumb-pending[data-path]');
            if (remaining.length > 0) {
                _pendingThumbTimer = setTimeout(poll, 2000);
            }
        } catch (e) {
            _pendingThumbTimer = setTimeout(poll, 3000);
        }
    }
    _pendingThumbTimer = setTimeout(poll, 1500);
}


function startThumbnailGeneration(limit = 200) {
const files = filteredFiles;
if (!files?.length) return;
const BATCH_SIZE = 25;
let idx = 0, processed = 0;

async function processBatch() {
if (idx >= files.length || processed >= limit) return;

const toCheck = [];
while (idx < files.length && toCheck.length < BATCH_SIZE && processed < limit) {
    const f = files[idx++];
    if (f.has_thumb) {
        const card = document.querySelector(`.file-card[data-path="${CSS.escape(f.path)}"]`);
        if (card) {
            const img = card.querySelector('.file-thumb img');
            if (img && img.dataset.loaded !== 'true') refreshFileThumbnail(f.path);
        }
        processed++;
        continue;
    }
    toCheck.push(f);
    processed++;
}

if (toCheck.length) {
    try {
        const res = await fetch(`${API}/api/thumb/check`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paths: toCheck.map(f => f.path) })
        });
        const data = await res.json();
        const byPath = new Map((data.results || []).map(r => [r.path, r]));
        for (const f of toCheck) {
            const r = byPath.get(f.path);
            if (r?.ready) {
                updateFileThumbnail(f.name, `${API}${r.url}&t=${Date.now()}`, f.path);
            } else {
                requestThumbGeneration(f.path);
            }
        }
    } catch {}
}
requestAnimationFrame(processBatch);
}
processBatch();
}
function updateFileThumbnail(fileName, thumbUrl, filePath) {
const card = filePath
    ? document.querySelector(`.file-card[data-path="${CSS.escape(filePath)}"]`)
    : document.querySelector(`.file-card[data-name="${CSS.escape(fileName)}"]`);
if (!card) return;
const img = card.querySelector('.file-thumb img');
const loader = card.querySelector('.file-loading');
if (img && img.dataset.loaded === 'true' && img.src && !img.src.includes('data:image') && img.naturalWidth > 0) return;
if (img) {
    const testImg = new Image();
    testImg.onload = () => {
        img.src = thumbUrl;
        img.style.display = 'block';
        img.dataset.loaded = 'true';
        if (loader) loader.style.display = 'none';
    };
    testImg.onerror = () => {
        if (img.dataset.loaded !== 'true') {
            window.handleThumbnailError(img);
        }
    };
    testImg.src = thumbUrl;
}
}
function startThumbAutoRefresh() {
if (thumbRefreshInterval) clearInterval(thumbRefreshInterval);
thumbRefreshInterval = setInterval(async () => {
    const cards = document.querySelectorAll('.file-card');
    const pending = [];
    for (const card of cards) {
        const img = card.querySelector('.file-thumb img');
        if (img && img.dataset.loaded === 'true' && img.naturalWidth > 0) continue;
        const filePath = card.dataset.path;
        if (!filePath) continue;
        pending.push({ card, filePath });
        if (pending.length >= 10) break;
    }
    if (!pending.length) return;
    try {
        const checkRes = await fetch(`${API}/api/thumb/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paths: pending.map(p => p.filePath) })
        });
        const checkData = await checkRes.json();
        const byPath = new Map((checkData.results || []).map(r => [r.path, r]));
        for (const { filePath } of pending) {
            const r = byPath.get(filePath);
            if (r?.ready) {
                refreshFileThumbnail(filePath);
            } else if (!generatingThumbs.has(filePath) && !pendingThumbRequests.has(filePath)) {
                window.requestThumbGeneration(filePath);
            }
        }
    } catch (err) {  }
}, 5000);
}


let thumbFailureInterval = null;
function startThumbFailureMonitor() {
if (thumbFailureInterval) clearInterval(thumbFailureInterval);
thumbFailureInterval = setInterval(async () => {
    try {
        const res = await fetch(`${API}/api/thumb/failures`);
        if (!res.ok) return;
        const data = await res.json();
        for (const f of (data.failures || [])) {
            showToast(I18N.t('toast.thumb_error_named', { name: f.name }), 'error');
        }
    } catch (err) {  }

    try {
        const res2 = await fetch(`${API}/api/thumb/summary`);
        if (!res2.ok) return;
        const data2 = await res2.json();
        if (data2.summary) showThumbSummaryModal(data2.summary);
    } catch (err) {  }
}, 20000);
}

function showThumbSummaryModal(summary) {
let modal = document.getElementById('modal-thumb-summary');
if (!modal) {
    modal = document.createElement('div');
    modal.id = 'modal-thumb-summary';
    modal.className = 'modal hidden';
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal('modal-thumb-summary'); });
}

const failed = summary.failed || [];
const failedListHtml = failed.length
    ? `<details style="margin-top:12px;" open>
        <summary style="cursor:pointer; color:var(--warning); font-size:13px;">
            <i class="fa-solid fa-triangle-exclamation"></i> ${failed.length} fichier(s) en erreur — voir la liste
        </summary>
        <ul style="margin:10px 0 0 0; padding-left:0; list-style:none; max-height:260px; overflow-y:auto; display:flex; flex-direction:column; gap:4px;">
            ${failed.map(f => `<li id="thumb-fail-${(f.path || f.name).replace(/[^\w]/g, '-')}" style="display:flex; align-items:center; justify-content:space-between; gap:8px; font-size:12px; color:var(--text-secondary); padding:6px 10px; background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius);">
                <span title="${escapeHtml(f.path || f.name)}" style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(f.name)}${f.reason === 'timeout' ? ` <span style="color:var(--warning);">(${I18N.t('repair.timeout_badge')})</span>` : ''}</span>
                ${f.path ? `<button type="button" class="btn btn-ghost btn-sm" style="flex-shrink:0;" onclick="repairAndRegenThumb('${escapeJs(f.path)}', this)"><i class="fa-solid fa-wrench"></i> ${I18N.t('actions.repair')}</button>` : ''}
            </li>`).join('')}
        </ul>
    </details>`
    : '';

modal.innerHTML = `<div class="modal-content">
    <div class="modal-header">
        <h3><i class="fa-solid fa-circle-check"></i> <span data-i18n="thumbs.summary_title">Génération des miniatures terminée</span></h3>
        <button class="modal-close" onclick="closeModal('modal-thumb-summary')">×</button>
    </div>
    <div class="modal-body">
        <div style="display:flex; flex-direction:column; gap:8px; background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius); padding:14px;">
            <div style="display:flex; justify-content:space-between; font-size:13px; color:var(--text-secondary);">
                <span data-i18n="thumbs.summary_processed">Fichiers traités cette session</span>
                <strong style="color:var(--text-primary);">${summary.total}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:13px; color:var(--text-secondary);">
                <span data-i18n="thumbs.summary_generated">Miniatures générées</span>
                <strong style="color:var(--success);">${summary.generated}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:13px; color:${failed.length ? 'var(--warning)' : 'var(--text-secondary)'};">
                <span data-i18n="thumbs.summary_errors">Erreurs</span>
                <strong>${failed.length}</strong>
            </div>
        </div>
        ${failedListHtml}
    </div>
</div>`;
openModal('modal-thumb-summary');
I18N.apply();
}


async function loadTags() {
try {
const res = await fetch(`${API}/api/tags`);
if (res.ok) {
allTags = await res.json();
renderTagFilters();
}
} catch (err) {
console.error('[Tags] Erreur:', err);
}
}
function renderTagFilters() {
const container = document.getElementById('filter-tags');
if (!container) return;
if (!allTags.length) {
container.innerHTML = `<p style="color:var(--text-muted);font-size:13px">${I18N.t('toast.tag_empty')}</p>`;
return;
}
container.innerHTML = allTags.map(t => `<label class="checkbox-label"><input type="checkbox" value="${escapeHtml(t.name)}" class="filter-tag" ${activeTagFilters.has(t.name) ? 'checked' : ''}><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${t.color};margin-right:6px;"></span>${escapeHtml(t.name)} <span class="tag-count" style="color:var(--text-muted)">(${t.count})</span></label>`).join('');
updateSidebarCounts(filteredFiles || allFiles);
I18N.apply();
}
function updateSidebarCounts(currentFiles) {
const counts = {};
allTags.forEach(tag => {
counts[tag.name.toLowerCase()] = currentFiles.filter(f => f.tags?.some(t => t.name.toLowerCase() === tag.name.toLowerCase())).length;
});
document.querySelectorAll('.filter-tag').forEach(checkbox => {
const tagName = checkbox.value.toLowerCase();
const countSpan = checkbox.closest('.checkbox-label')?.querySelector('.tag-count');
if (countSpan) {
countSpan.textContent = `(${counts[tagName] || 0})`;
checkbox.closest('.checkbox-label').style.opacity = (counts[tagName] === 0 && !checkbox.checked) ? '0.4' : '1';
}
});
}
function openTagModal(filePath) {
openTagManagerModal('file', filePath);
}
function openTagManagerModal(mode = 'global', filePath = null) {
const filePathEl = document.getElementById('tag-modal-file-path');
const currentTagsEl = document.getElementById('tag-modal-current-tags');
const tagsListEl = document.getElementById('tag-modal-list');
const newTagGroup = document.getElementById('tag-modal-new-tag')?.closest('.input-group');
const applyBtn = document.getElementById('add-tag-to-file-btn');
const modalTitle = document.querySelector('#modal-tag-manager .modal-header h3');
if (mode === 'global') {
    currentTagFile = null;
    if (modalTitle) modalTitle.innerHTML = `<i class="fa-solid fa-tags"></i> ${I18N.t('modal.manage_tags')}`;
    if (filePathEl?.closest('.input-group')) filePathEl.closest('.input-group').style.display = 'none';
    if (currentTagsEl?.parentElement) currentTagsEl.parentElement.style.display = 'none';
    const ollamaSection = document.getElementById('ollama-autotag-section');
    if (ollamaSection) ollamaSection.style.display = 'none';
    if (tagsListEl) {
        if (allTags.length === 0) {
            tagsListEl.innerHTML = `<p style="color:var(--text-muted);font-size:12px;padding:10px">${I18N.t('toast.tag_empty')}</p>`;
        } else {
            tagsListEl.innerHTML = allTags.map(t => `<div style="display:flex;justify-content:space-between;align-items:center;padding:10px;border-bottom:1px solid var(--border);"><div style="display:flex;align-items:center;gap:10px;"><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${t.color};"></span><strong>${escapeHtml(t.name)}</strong><span style="color:var(--text-muted);font-size:12px">(${t.count} ${I18N.t('library.no_files').toLowerCase()})</span></div><div style="display:flex;gap:6px;"><button class="btn btn-ghost btn-sm" onclick="editTag(${t.id}, '${escapeJs(t.name)}', '${t.color}')" title="${I18N.t('actions.rename')}" style="color:var(--accent)"><i class="fa-solid fa-pen"></i></button><button class="btn btn-ghost btn-sm" onclick="deleteTag(${t.id}, '${escapeJs(t.name)}')" title="${I18N.t('actions.delete')}" style="color:var(--danger)"><i class="fa-solid fa-trash"></i></button></div></div>`).join('');
        }
    }
    if (newTagGroup) newTagGroup.style.display = 'flex';
    if (applyBtn) {
        applyBtn.style.display = 'inline-flex';
        applyBtn.innerHTML = I18N.t('modal.create_tag');
        applyBtn.onclick = createGlobalTag;
    }
} else {
    currentTagFile = filePath;
    if (modalTitle) modalTitle.innerHTML = `<i class="fa-solid fa-tag"></i> ${I18N.t('modal.selected_file')}`;
    if (filePathEl && filePath) {
        filePathEl.closest('.input-group').style.display = 'block';
        filePathEl.value = filePath.split('/').pop() || filePath;
    }
    const ollamaSection = document.getElementById('ollama-autotag-section');
    if (ollamaSection) ollamaSection.style.display = 'block';
    const ollamaResult = document.getElementById('ollama-autotag-result');
    if (ollamaResult) ollamaResult.style.display = 'none';
    if (currentTagsEl?.parentElement) {
        currentTagsEl.parentElement.style.display = 'block';
        const file = allFiles.find(f => f.path === filePath);
        const currentTags = file?.tags?.map(t => t.name) || [];
        currentTagsEl.innerHTML = currentTags.length ? currentTags.map(t => `<span class="tag-badge">${escapeHtml(t)}</span>`).join('') : `<span style="color:var(--text-muted);font-size:12px">${I18N.t('toast.file_not_selected')}</span>`;
    }
    if (tagsListEl) {
        const file = allFiles.find(f => f.path === filePath);
        const currentTags = file?.tags?.map(t => t.name) || [];
        tagsListEl.innerHTML = allTags.map(t => `<label class="checkbox-label" style="margin:6px 0;"><input type="checkbox" value="${escapeHtml(t.name)}" class="tag-select" ${currentTags.includes(t.name) ? 'checked' : ''}><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${t.color};margin-right:8px;"></span>${escapeHtml(t.name)}</label>`).join('');
    }
    if (newTagGroup) newTagGroup.style.display = 'flex';
    if (applyBtn) {
        applyBtn.style.display = 'inline-flex';
        applyBtn.innerHTML = `<i class="fa-solid fa-check"></i> ${I18N.t('filters.apply')}`;
        applyBtn.onclick = applyTagsToFile;
    }
}
openModal('modal-tag-manager');
I18N.apply();
}
async function createGlobalTag() {
const newTagInput = document.getElementById('tag-modal-new-tag');
const newTagName = newTagInput?.value.trim();
if (!newTagName) {
showToast(I18N.t('toast.tag_empty'), 'warning');
return;
}
if (currentTagFile) {
await applyTagsToFile();
return;
}
try {
const res = await fetch(`${API}/api/tags`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ name: newTagName, color: '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0') })
});
const data = await res.json();
if (res.ok) {
showToast(I18N.t('toast.tag_created'), 'success');
if (newTagInput) newTagInput.value = '';
await loadTags();
openTagManagerModal('global');
} else {
showToast(data.error || I18N.t('toast.tag_error'), 'error');
}
} catch (err) {
showToast(I18N.t('toast.fetch_error'), 'error');
console.error('[Tags] Erreur:', err);
}
}
async function applyTagsToFile() {
if (!currentTagFile) {
showToast(I18N.t('toast.file_not_selected'), 'error');
return;
}
const selected = [...document.querySelectorAll('.tag-select:checked')].map(c => c.value);
const newTagInput = document.getElementById('tag-modal-new-tag');
const newTag = newTagInput?.value.trim();
const tagsToSave = [...new Set([...selected, ...(newTag ? [newTag] : [])])];
try {
const res = await fetch(`${API}/api/files/tags`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ path: currentTagFile, tags: tagsToSave })
});
const data = await res.json();
if (res.ok) {
showToast(I18N.t('toast.tags_updated'), 'success');
closeModal('modal-tag-manager');
await Promise.all([loadFiles(), loadTags()]);
} else {
showToast(data.error || I18N.t('toast.tag_assign_error'), 'error');
}
} catch (err) {
showToast(I18N.t('toast.fetch_error'), 'error');
console.error('[Tags] Erreur:', err);
}
}
window.deleteTag = (tagId, tagName) => {
closeModal('modal-tag-manager');
showConfirmModal(`${I18N.t('toast.delete_tag')} "${tagName}" ?`, async () => {
try {
const res = await fetch(`${API}/api/tags/${tagId}`, { method: 'DELETE' });
if (res.ok) {
showToast(I18N.t('toast.tags_deleted'), 'success');
await loadTags();
await loadFiles();
setTimeout(() => openTagManagerModal('global'), 200);
} else {
const data = await res.json();
showToast(data.error || I18N.t('toast.error'), 'error');
}
} catch (err) {
showToast(I18N.t('toast.fetch_error'), 'error');
console.error('[Tags] Erreur:', err);
}
});
};
window.editTag = async (tagId, currentName, currentColor) => {
const newName = prompt(`${I18N.t('modal.rename_source')} :`, currentName);
if (!newName || newName.trim() === currentName) return;
const newColor = prompt(`${I18N.t('settings.brand_color')} (hex, ex: #ff6b6b) :`, currentColor);
try {
const res = await fetch(`${API}/api/tags/${tagId}`, {
method: 'PUT',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ name: newName.trim(), color: newColor || currentColor })
});
const data = await res.json();
if (res.ok) {
showToast(I18N.t('toast.tags_updated_global'), 'success');
await loadTags();
openTagManagerModal('global');
} else {
showToast(data.error, 'error');
}
} catch (err) {
showToast(I18N.t('toast.fetch_error'), 'error');
console.error(err);
}
};


function updateThingiverseFooterStatus(connected, error = null) {
    updateAccountBadge('thingiverse', !!connected);
    if (connected) showAccountKeyConfigured('thingiverse');
}


async function loadDownloadSources() {
const select = document.getElementById('download-source');
if (!select) return;
select.innerHTML = `<option value=""> ${I18N.t('download.select_folder')}</option>`;
try {
const res = await fetch(`${API}/api/sources`);
if (!res.ok) throw new Error(I18N.t('toast.load_source_error'));
const sources = await res.json();
const folderSources = sources.filter(s => s.type === 'folder' || s.type === 'smb' || s.type === 'nfs');
    if (folderSources.length === 0) {
        select.innerHTML += `<option value="" disabled>${I18N.t('download.no_local_folders')}</option>`;
        return;
    }

    folderSources.forEach(source => {
        const option = document.createElement('option');
        option.value = source.id;
        const icon = source.type === 'smb' ? '🌐' : (source.type === 'nfs' ? '️' : '📁');
        option.textContent = `${icon} ${source.name} (${source.path})`;
        option.dataset.sourceType = source.type;
        select.appendChild(option);
    });
} catch  (err) {
    console.error('[Download Sources]', err);
    select.innerHTML += `<option value="" disabled>${I18N.t('download.load_error')}</option>`;
}
}
function openDownloadModal() {
loadDownloadSources();
document.getElementById('download-form').reset();
document.getElementById('download-progress').classList.add('hidden');
document.getElementById('download-result').style.display = 'none';
document.getElementById('download-btn').disabled = false;
openModal('modal-download');
setTimeout(() => { document.getElementById('download-url')?.focus(); }, 100);
}
let activeDownloads = [];
let downloadToastElements = {};
let downloadIdCounter = 0;
let isFormLocked = false;
async function handleDownload(e) {
e.preventDefault();
if (isFormLocked) { showToast(I18N.t('toast.please_wait'), 'warning'); return; }
const url = document.getElementById('download-url').value.trim();
const sourceId = document.getElementById('download-source').value;
const preferredFormat = document.getElementById('makerworld-format')?.value || '';
if (!url) { showToast(I18N.t('toast.url_required'), 'warning'); return; }
isFormLocked = true;
try {
const downloadId = ++downloadIdCounter;
const downloadInfo = { id: downloadId, url, sourceId, preferredFormat, status: 'starting', filename: '', progress: 0, current: 0, total: 0, toastElement: null };
activeDownloads.push(downloadInfo);
createDownloadToast(downloadInfo);
startDownload(downloadInfo);
document.getElementById('download-form').reset();
document.getElementById('makerworld-format-group').style.display = 'none';
setTimeout(() => { isFormLocked = false; }, 500);
} catch (err) {
console.error('[handleDownload] Erreur:', err);
isFormLocked = false;
showToast(I18N.t('toast.start_error'), 'error');
}
}
async function startDownload(downloadInfo) {
try {
const progressPollingInterval = setInterval(async () => {
try {
const res = await fetch(`${API}/api/download/progress/${downloadInfo.id}`);
const data = await res.json();
if (data.active && data.download_id === downloadInfo.id) {
downloadInfo.status = 'downloading';
downloadInfo.filename = data.filename || I18N.t('download.file_placeholder');
downloadInfo.progress = data.percentage || 0;
downloadInfo.current = data.current || 0;
downloadInfo.total = data.total || 0;
const currentMB = (downloadInfo.current / 1024 / 1024).toFixed(1);
const totalMB = (downloadInfo.total / 1024 / 1024).toFixed(1);
updateDownloadToast(downloadInfo, currentMB, totalMB);
}
} catch (err) { console.error('[Progress polling error]', err); }
}, 500);
    const res = await fetch(`${API}/api/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: downloadInfo.url, target_source_id: downloadInfo.sourceId || null, download_id: downloadInfo.id, preferred_format: downloadInfo.preferredFormat || '' })
    });
    clearInterval(progressPollingInterval);
    const data = await res.json();

    if (res.ok) {
        downloadInfo.status = 'completed';
        downloadInfo.progress = 100;
        downloadInfo.filename = data.filename || I18N.t('download.file_placeholder');
        updateDownloadToast(downloadInfo, (data.size / 1024 / 1024).toFixed(1), (data.size / 1024 / 1024).toFixed(1), true);
        showToast(`✓ ${downloadInfo.filename} ${I18N.t('toast.download_success')}`, 'success');
        setTimeout(() => { removeDownloadToast(downloadInfo.id); }, 3000);
        loadFiles();
    } else {
        downloadInfo.status = 'error';
        updateDownloadToast(downloadInfo, 0, 0, false, data.error || I18N.t('app.error'));
        setTimeout(() => { removeDownloadToast(downloadInfo.id); }, 5000);
    }
} catch (err) {
    downloadInfo.status = 'error';
    updateDownloadToast(downloadInfo, 0, 0, false, I18N.t('toast.connection_error'));
    console.error('[Download]', err);
    setTimeout(() => { removeDownloadToast(downloadInfo.id); }, 5000);
} finally {
    const index = activeDownloads.findIndex(d => d.id === downloadInfo.id);
    if (index > -1) activeDownloads.splice(index, 1);
    reorganizeDownloadToasts();
}
}
function createDownloadToast(downloadInfo) {
const container = document.getElementById('toast-container');
if (!container) return;
const toast = document.createElement('div');
toast.id = `download-toast-${downloadInfo.id}`;
toast.className = 'toast info';
toast.style.cssText = `min-width: 350px; pointer-events: auto; margin-bottom: 8px; transition: all 0.3s ease;`;
toast.innerHTML = `<i class="fa-solid fa-spinner fa-spin" style="color: var(--accent)"></i><div style="flex: 1; min-width: 0;"><div style="font-weight: 600; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center;"><span><i class="fa-solid fa-download"></i> ${I18N.t('download.title')} #${downloadInfo.id}</span><button onclick="cancelDownload(${downloadInfo.id})" class="btn btn-ghost btn-sm" style="padding: 2px 6px; font-size: 11px;"><i class="fa-solid fa-times"></i></button></div><div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;" id="toast-filename-${downloadInfo.id}">${I18N.t('download.connecting')}</div><div class="progress-track" style="height: 4px; margin-top: 4px;"><div id="toast-bar-${downloadInfo.id}" class="progress-bar" style="width: 0%"></div></div><div style="font-size: 11px; color: var(--text-muted); margin-top: 4px; text-align: right;" id="toast-progress-${downloadInfo.id}">0%</div></div>`;
container.appendChild(toast);
downloadInfo.toastElement = toast;
downloadToastElements[downloadInfo.id] = toast;
reorganizeDownloadToasts();
}
function updateDownloadToast(downloadInfo, currentMB, totalMB, isComplete = false, error = null) {
const toast = downloadInfo.toastElement;
if (!toast) return;
const bar = document.getElementById(`toast-bar-${downloadInfo.id}`);
const filenameEl = document.getElementById(`toast-filename-${downloadInfo.id}`);
const progressEl = document.getElementById(`toast-progress-${downloadInfo.id}`);
if (bar) bar.style.width = `${downloadInfo.progress}%`;
if (filenameEl) filenameEl.textContent = downloadInfo.filename || I18N.t('download.file_placeholder');
if (progressEl) {
if (error) { progressEl.textContent = `❌ ${error}`; progressEl.style.color = 'var(--danger)'; }
else if (isComplete) { progressEl.textContent = `✅ ${I18N.t('download.completed')} - ${currentMB} ${I18N.t('units.MB')}`; progressEl.style.color = 'var(--success)'; }
else { progressEl.textContent = `${Math.round(downloadInfo.progress)}% (${currentMB}/${totalMB} ${I18N.t('units.MB')})`; }
}
if (error) toast.className = 'toast error';
else if (isComplete) toast.className = 'toast success';
else toast.className = 'toast info';
}
function removeDownloadToast(downloadId) {
const toast = downloadToastElements[downloadId];
if (toast) {
toast.style.opacity = '0'; toast.style.transform = 'translateX(100%)';
setTimeout(() => { toast.remove(); delete downloadToastElements[downloadId]; }, 300);
}
const index = activeDownloads.findIndex(d => d.id === downloadId);
if (index > -1) activeDownloads.splice(index, 1);
reorganizeDownloadToasts();
}
function reorganizeDownloadToasts() {
const container = document.getElementById('toast-container');
if (!container) return;
const sortedDownloads = [...activeDownloads].sort((a, b) => b.id - a.id);
sortedDownloads.forEach((download, index) => {
if (download.toastElement) {
if (index === 0) container.insertBefore(download.toastElement, container.firstChild);
else { const nextToast = sortedDownloads[index - 1]?.toastElement; if (nextToast && nextToast.nextSibling) container.insertBefore(download.toastElement, nextToast.nextSibling); }
}
});
}
async function cancelDownload(downloadId) {
const download = activeDownloads.find(d => d.id === downloadId);
if (download) {
try {
const res = await fetch(`${API}/api/download/cancel/${downloadId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
if (!res.ok) throw new Error(`HTTP ${res.status}`);
download.status = 'cancelled';
updateDownloadToast(download, 0, 0, false, I18N.t('download.cancelled'));
setTimeout(() => { removeDownloadToast(downloadId); }, 2000);
showToast(I18N.t('download.cancelled_toast'), 'info');
} catch (err) { console.error('[cancelDownload] Erreur:', err); removeDownloadToast(downloadId); showToast(I18N.t('toast.cancel_error'), 'error'); }
}
}
window.openCreateFolderModal = async function() {
const sourceSelect = document.getElementById('download-source');
const selectedSourceId = sourceSelect ? sourceSelect.value : null;
let parentPath = null;
let sourceConfig = null;
if (selectedSourceId && selectedSourceId !== "") {
    const selectedOption = sourceSelect.options[sourceSelect.selectedIndex];
    const match = selectedOption.text.match(/\((.*?)\)$/);
    if (match) {
        parentPath = match[1];
    } else {
        showToast(I18N.t('toast.source_path_missing') || 'Impossible de trouver le chemin', 'warning');
        return;
    }
    try {
        const srcRes = await fetch(`${API}/api/sources`);
        if (srcRes.ok) {
            const allSources = await srcRes.json();
            const matchedSource = allSources.find(s => String(s.id) === String(selectedSourceId));
            if (matchedSource && matchedSource.config) {
                sourceConfig = matchedSource.config;
            }
        }
    } catch (err) {
        console.error('[Create Folder] Impossible de récupérer la config de la source', err);
    }
} else {
    showToast(I18N.t('toast.select_parent_folder') || 'Sélectionnez un dossier parent', 'info');
    try {
        const res = await fetch(`${API}/api/picker/folder`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok || !data.path) {
            showToast(I18N.t('toast.selection_cancelled'), 'info');
            return;
        }
        parentPath = data.path;
    } catch (err) {
        showToast(I18N.t('toast.connection_error'), 'error');
        return;
    }
}

const overlay = document.createElement('div');
overlay.style.cssText = `position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.75); display: flex; align-items: center; justify-content: center; z-index: 100000; backdrop-filter: blur(5px); animation: fadeIn 0.2s ease;`;
const modal = document.createElement('div');
modal.style.cssText = `background: var(--bg-secondary, #1e2129); border-radius: 16px; padding: 28px; max-width: 450px; width: 90%; box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6); border: 1px solid var(--border, #2a2f3a); animation: slideIn 0.3s ease;`;
modal.innerHTML = `
     <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
         <i class="fa-solid fa-folder-plus" style="font-size: 24px; color: var(--accent, #4ea1d3);"></i>
         <h3 style="margin: 0; color: var(--text-primary, #e6e6e6); font-size: 18px; font-weight: 600;">${I18N.t('download.create_folder') || 'Créer un dossier'}</h3>
     </div>
     <p style="color: var(--text-muted, #9ca3af); margin-bottom: 20px; line-height: 1.5; font-size: 14px;">
        ${I18N.t('download.enter_folder_name') || 'Entrez le nom du nouveau dossier'}
     </p>
     <input type="text" id="folder-name-input" placeholder="${I18N.t('download.folder_name_placeholder') || 'Nom du dossier'}" maxlength="50" style="width: 100%; padding: 12px 16px; border: 2px solid var(--border, #2a2f3a); border-radius: 10px; background: var(--bg-primary, #15181e); color: var(--text-primary, #e6e6e6); font-size: 15px; margin-bottom: 24px; box-sizing: border-box; transition: border-color 0.2s;" onfocus="this.style.borderColor='var(--accent, #4ea1d3)'" onblur="this.style.borderColor='var(--border, #2a2f3a)'">
     <div style="display: flex; gap: 12px; justify-content: flex-end;">
         <button id="folder-cancel-btn" style="padding: 11px 24px; border: none; border-radius: 10px; background: var(--bg-tertiary, #2a2f3a); color: var(--text-primary, #e6e6e6); cursor: pointer; font-weight: 500; transition: all 0.2s; font-size: 14px;" onmouseover="this.style.background='#3a3f4a'" onmouseout="this.style.background='var(--bg-tertiary, #2a2f3a)'">${I18N.t('actions.cancel') || 'Annuler'}</button>
         <button id="folder-ok-btn" style="padding: 11px 24px; border: none; border-radius: 10px; background: var(--accent, #4ea1d3); color: white; cursor: pointer; font-weight: 600; transition: all 0.2s; font-size: 14px;" onmouseover="this.style.background='#3d8fb8'" onmouseout="this.style.background='var(--accent, #4ea1d3)'">${I18N.t('actions.create') || 'Créer'}</button>
     </div>
`;
overlay.appendChild(modal);
document.body.appendChild(overlay);
if (!document.getElementById('folder-modal-styles')) {
    const style = document.createElement('style');
    style.id = 'folder-modal-styles';
    style.textContent = `@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } } @keyframes slideIn { from { transform: translateY(-20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }`;
    document.head.appendChild(style);
}
const input = modal.querySelector('#folder-name-input');
const okBtn = modal.querySelector('#folder-ok-btn');
const cancelBtn = modal.querySelector('#folder-cancel-btn');
setTimeout(() => input.focus(), 100);

const createFolder = async () => {
    const folderName = input.value.trim();
    if (!folderName) {
        input.style.borderColor = 'var(--danger, #ef4444)';
        return;
    }
    const cleanFolderName = folderName.replace(/[<>:"/\\|?*]/g, '_');
    const newFolderPath = `${parentPath}/${cleanFolderName}`;
    try {
        const createRes = await fetch(`${API}/api/download/create-folder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                folder_path: newFolderPath,
                folder_name: cleanFolderName,
                add_as_source: true,
                config: sourceConfig
            })
        });
        const result = await createRes.json();
        if (createRes.ok) {
            showToast(I18N.t('toast.folder_created') || 'Dossier créé avec succès', 'success');
            await loadSources();
            await loadDownloadSources();
            setTimeout(() => {
                const opts = sourceSelect.options;
                for (let i = 0; i < opts.length; i++) {
                    if (opts[i].text.includes(cleanFolderName)) {
                        sourceSelect.selectedIndex = i;
                        break;
                    }
                }
            }, 500);
        } else {
            showToast(result.error || I18N.t('toast.folder_create_error') || 'Erreur de création', 'error');
        }
    } catch (err) {
        console.error('[Create Folder]', err);
        showToast(I18N.t('toast.connection_error') || 'Erreur de connexion', 'error');
    }
    overlay.remove();
};

okBtn.addEventListener('click', createFolder);
cancelBtn.addEventListener('click', () => overlay.remove());
input.addEventListener('keypress', (e) => { if (e.key === 'Enter') createFolder(); });
input.addEventListener('input', () => { input.style.borderColor = 'var(--border, #2a2f3a)'; });
overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
};
window.browseDownloadLocation = async function() {
try {
const res = await fetch(`${API}/api/picker/folder`, { method: 'POST' });
const data = await res.json();
if (res.ok && data.path) {
showToast(`📍 ${I18N.t('toast.folder_selected')}: ${data.path}`, 'info');
await loadDownloadSources();
}
} catch (err) {
showToast(I18N.t('toast.picker_unavailable'), 'warning');
}
};


function applyFilters() {
let files = [...allFiles];
if (activeTypeFilters?.length > 0 && activeTypeFilters.length < 3) files = files.filter(f => activeTypeFilters.includes(f.extension));
if (currentSizeFilter) files = files.filter(f => { const mb = (f.size || 0) / (1024 * 1024); return mb >= (currentSizeFilter.min || 0) && mb <= (currentSizeFilter.max !== undefined ? currentSizeFilter.max : Infinity); });
if (currentWeightFilter) files = files.filter(f => { if (f.weight_g === null || f.weight_g === undefined) return false; return f.weight_g >= (currentWeightFilter.min || 0) && f.weight_g <= (currentWeightFilter.max !== undefined ? currentWeightFilter.max : Infinity); });
if (printStatusFilter) files = files.filter(f => (f.print_status || 'never') === printStatusFilter);
if (activeTagFilters.size > 0) files = files.filter(f => { const fileTags = new Set((f.tags || []).map(t => t.name.toLowerCase())); for (const tag of activeTagFilters) { if (!fileTags.has(tag.toLowerCase())) return false; } return true; });
if (noThumbFilterOnly) files = files.filter(f => !f.has_thumb);
if (failedThumbFilterOnly) files = files.filter(f => !!f.thumb_fallback);
filteredFiles = files;
applySorting();
renderFiles();
updateSidebarCounts(filteredFiles);
startThumbnailGeneration();
}
document.getElementById('toggle-astuces')?.addEventListener('click', function () {
const menu = document.getElementById('astuces-menu');
const icon = document.getElementById('astuces-icon');
if (menu.style.display === 'none') {
menu.style.display = 'block';
icon.classList.remove('fa-chevron-down');
icon.classList.add('fa-chevron-up');
} else {
menu.style.display = 'none';
icon.classList.remove('fa-chevron-up');
icon.classList.add('fa-chevron-down');
}
});
function toggleAstuceSubmenu(submenuId) {
const submenu = document.getElementById(submenuId);
const icon = document.getElementById(submenuId.replace('astuces', 'astuces-icon'));
if (submenu.style.display === 'none') {
submenu.style.display = 'block';
icon.classList.remove('fa-chevron-right');
icon.classList.add('fa-chevron-down');
} else {
submenu.style.display = 'none';
icon.classList.remove('fa-chevron-down');
icon.classList.add('fa-chevron-right');
}
}
function openFiltersModal() {
document.querySelectorAll('.filter-type').forEach(cb => { cb.checked = !activeTypeFilters || activeTypeFilters.length === 0 || activeTypeFilters.includes(cb.value); });
document.getElementById('size-min').value = currentSizeFilter?.min || '';
document.getElementById('size-max').value = currentSizeFilter?.max || '';
document.getElementById('weight-min').value = currentWeightFilter?.min || '';
document.getElementById('weight-max').value = currentWeightFilter?.max || '';
const printStatusSelect = document.getElementById('filter-print-status');
if (printStatusSelect) printStatusSelect.value = printStatusFilter || '';
const noThumbCb = document.getElementById('filter-no-thumb');
if (noThumbCb) noThumbCb.checked = noThumbFilterOnly;
const failedThumbCb = document.getElementById('filter-thumb-failed');
if (failedThumbCb) failedThumbCb.checked = failedThumbFilterOnly;
renderFilterTagsModal();
openModal('modal-filters');
}
function applyFiltersFromModal() {
const selectedTypes = [...document.querySelectorAll('.filter-type:checked')].map(cb => cb.value);
activeTypeFilters = selectedTypes.length === 3 ? [] : selectedTypes;
noThumbFilterOnly = document.getElementById('filter-no-thumb')?.checked || false;
failedThumbFilterOnly = document.getElementById('filter-thumb-failed')?.checked || false;
const minVal = parseFloat(document.getElementById('size-min').value);
const maxVal = parseFloat(document.getElementById('size-max').value);
currentSizeFilter = { min: isNaN(minVal) ? 0 : minVal, max: isNaN(maxVal) ? Infinity : maxVal };
const weightMinVal = parseFloat(document.getElementById('weight-min').value);
const weightMaxVal = parseFloat(document.getElementById('weight-max').value);
currentWeightFilter = (isNaN(weightMinVal) && isNaN(weightMaxVal)) ? null : { min: isNaN(weightMinVal) ? 0 : weightMinVal, max: isNaN(weightMaxVal) ? Infinity : weightMaxVal };
printStatusFilter = document.getElementById('filter-print-status')?.value || '';
closeModal('modal-filters');
applyFilters();
showToast(I18N.t('toast.filters_applied'), 'success');
}
function resetFilters() {
document.querySelectorAll('.filter-type').forEach(cb => cb.checked = true);
const noThumbCb = document.getElementById('filter-no-thumb');
if (noThumbCb) noThumbCb.checked = false;
noThumbFilterOnly = false;
const failedThumbCb = document.getElementById('filter-thumb-failed');
if (failedThumbCb) failedThumbCb.checked = false;
failedThumbFilterOnly = false;
document.getElementById('size-min').value = '';
document.getElementById('size-max').value = '';
document.getElementById('weight-min').value = '';
document.getElementById('weight-max').value = '';
const printStatusSelect = document.getElementById('filter-print-status');
if (printStatusSelect) printStatusSelect.value = '';
printStatusFilter = '';
activeTypeFilters = [];
currentSizeFilter = null;
currentWeightFilter = null;
activeTagFilters.clear();
closeModal('modal-filters');
applyFilters();
showToast(I18N.t('toast.filters_reset'), 'info');
}
function renderFilterTagsModal() {
const container = document.getElementById('filter-tags-modal');
if (!container) return;
if (!allTags.length) {
container.innerHTML = `<p style="color:var(--text-muted);font-size:13px">${I18N.t('toast.tag_empty')}</p>`;
return;
}
container.innerHTML = allTags.map(t => `<label class="checkbox-label" style="margin-bottom: 8px;"><input type="checkbox" value="${escapeHtml(t.name)}" class="filter-tag-modal" ${activeTagFilters.has(t.name) ? 'checked' : ''}><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${t.color};margin-right:6px;"></span>${escapeHtml(t.name)} <span style="color:var(--text-muted)">(${t.count})</span></label>`).join('');
container.querySelectorAll('.filter-tag-modal').forEach(checkbox => {
checkbox.addEventListener('change', (e) => {
if (e.target.checked) activeTagFilters.add(e.target.value);
else activeTagFilters.delete(e.target.value);
});
});
I18N.apply();
}


let currentSlicerOrientation = 'default';
let _slicerLaunchedFromViewer = false;

async function openFileWith(path, name) {
try {
    const res = await fetch(`${API}/api/files/open-with`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: path })
    });
    let data = {};
    try {
        data = await res.json();
    } catch (parseErr) {
        // Réponse non-JSON (page d'erreur HTML, proxy, etc.) : on affiche au
        // moins le code HTTP plutôt qu'un message générique inexploitable,
        // utile pour diagnostiquer sans accès à la console (devtools
        // désactivés en production, debug=False côté pywebview).
        showToast(`${I18N.t('toast.error')} (HTTP ${res.status})`, 'error');
        console.error('[OpenWith] Réponse non-JSON', res.status, parseErr);
        return;
    }
    if (!res.ok) {
        showToast(data.error || `${I18N.t('toast.error')} (HTTP ${res.status})`, 'error');
        return;
    }
    if (data.message) showToast(data.message, 'success');
} catch (e) {
    showToast(`${I18N.t('toast.network_error')}: ${e.message || e}`, 'error');
    console.error('[OpenWith] Erreur fetch', e);
}
}

function sendToSlicer(path, name, aiProfile, orientation) {
currentSlicerFile = path;
currentSlicerOrientation = orientation || 'default';
document.getElementById('slicer-file-name').textContent = `${I18N.t('modal.selected_file')}: ${name}`;
_lastAiRecommendedProfile = aiProfile || null;
const aiBox = document.getElementById('slicer-ai-recommend-result');
if (aiBox) { aiBox.style.display = 'none'; aiBox.innerHTML = ''; }
openModal('modal-slicer');
_loadSlicerSpoolBox(path);
_runPrePrintCheck(path);
}

async function _runPrePrintCheck(path) {
const box = document.getElementById('slicer-preprint-warnings');
if (!box) return;
box.style.display = 'none';
box.innerHTML = '';
const printerId = document.getElementById('slicer-ai-printer-select')?.value || null;
try {
    const res = await fetch(`${API}/api/files/pre-print-check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path, printer_id: printerId || null })
    });
    const data = await res.json();
    const warnings = data.warnings || [];
    if (!warnings.length) return;
    box.innerHTML = warnings.map(w => {
        const isError = w.level === 'error';
        return `<div style="display:flex; gap:8px; align-items:flex-start; padding:8px 10px; border-radius:var(--radius); font-size:12px; background:${isError ? 'rgba(220,53,69,0.12)' : 'rgba(245,166,35,0.12)'}; border:1px solid ${isError ? 'rgba(220,53,69,0.35)' : 'rgba(245,166,35,0.35)'}; color:${isError ? '#fc8181' : '#f6ad55'};">
            <i class="fa-solid ${isError ? 'fa-circle-exclamation' : 'fa-triangle-exclamation'}" style="margin-top:1px;"></i>
            <span>${escapeHtml(w.message)}</span>
        </div>`;
    }).join('');
    box.style.display = 'flex';
} catch (e) {  }
}
document.getElementById('slicer-ai-printer-select')?.addEventListener('change', () => {
if (currentSlicerFile) _runPrePrintCheck(currentSlicerFile);
});

async function _loadSlicerSpoolBox(path) {
const box = document.getElementById('slicer-spool-box');
const label = document.getElementById('slicer-spool-label');
if (!box || !label) return;
box.style.display = 'none';
try {
    const res = await fetch(`${API}/api/files/filament-assignment?path=${encodeURIComponent(path)}`);
    const data = await res.json();
    const a = data.assignment;
    if (!a) return;
    const badge = FILAMENT_SOURCE_BADGES[a.source_type] || '';
    label.textContent = `${badge} ` + _t2('spoolman.consume_on_send', `Décomptera ${a.name || ('#' + a.source_id)}${a.material ? ' (' + a.material + ')' : ''} au lancement de l'impression`, { name: a.name || `#${a.source_id}`, material: a.material ? ` (${a.material})` : '' });
    box.style.display = 'block';
} catch (e) {  }
}


let viewer3D = null, viewerControls = null, viewerScene = null, viewerCamera = null, viewerMesh = null, viewerRenderer = null;
let viewerOverhangMode = false;
let viewerCurrentOrientation = 'default';
const OVERHANG_THRESHOLD_DEG = 45;
let viewerActive = false, viewerAnimationId = null;
let viewerGizmoScene = null, viewerGizmoCamera = null;
let viewerHomeCameraPos = null;


function recenterViewerCamera() {
    if (!viewerCamera || !viewerControls || !viewerHomeCameraPos) return;
    viewerControls.target0.set(0, 0, 0);
    viewerControls.position0.copy(viewerHomeCameraPos);
    viewerControls.up0.set(0, 1, 0);
    viewerControls.reset();
}
window.recenterViewerCamera = recenterViewerCamera;

function disposeViewer3D() {
viewerActive = false;
if (viewerAnimationId !== null) {
cancelAnimationFrame(viewerAnimationId);
viewerAnimationId = null;
}
if (viewerScene) {
viewerScene.traverse((obj) => {
if (obj.geometry) obj.geometry.dispose();
if (obj.userData) {
    if (obj.userData.shadedMaterial && obj.userData.shadedMaterial !== obj.material) obj.userData.shadedMaterial.dispose();
    if (obj.userData.overhangMaterial && obj.userData.overhangMaterial !== obj.material) obj.userData.overhangMaterial.dispose();
}
if (obj.material) {
const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
materials.forEach((mat) => {
Object.keys(mat).forEach((key) => {
const val = mat[key];
if (val && typeof val.dispose === 'function') val.dispose();
});
mat.dispose();
});
}
});
}
if (viewerGizmoScene) {
viewerGizmoScene.traverse((obj) => {
if (obj.geometry) obj.geometry.dispose();
if (obj.material) {
const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
materials.forEach((mat) => {
if (mat.map && typeof mat.map.dispose === 'function') mat.map.dispose();
mat.dispose();
});
}
});
viewerGizmoScene = null;
}
viewerGizmoCamera = null;
if (viewerControls) {
viewerControls.dispose();
viewerControls = null;
}
if (viewerRenderer) {
viewerRenderer.dispose();
viewerRenderer.forceContextLoss?.();
viewerRenderer.domElement?.remove();
viewerRenderer = null;
}
viewerScene = null;
viewerCamera = null;
viewerMesh = null;
viewerHomeCameraPos = null;
}

let viewerCurrentPlate = 1;
let viewerPlateCount = 1;
let viewerCurrentPath = null;
let viewerCurrentFileName = null;

function open3DViewer(fileName, filePath, plateCount) {
document.getElementById('viewer-title').innerHTML = `<i class="fa-solid fa-cube"></i> ${fileName}`;
openModal('modal-3d-viewer');
viewerCurrentPath = filePath;
viewerCurrentFileName = fileName;
viewerPlateCount = (plateCount && plateCount > 1) ? plateCount : 1;
viewerCurrentPlate = 1;
load3DModel(filePath, viewerCurrentPlate);
updatePlateNavUI();
}


function sendViewerFileToSlicer() {
    if (!viewerCurrentPath) return;
    const orientation = viewerCurrentOrientation || 'default';
    _slicerLaunchedFromViewer = true;
    sendToSlicer(viewerCurrentPath, viewerCurrentFileName || viewerCurrentPath, null, orientation);
}
window.sendViewerFileToSlicer = sendViewerFileToSlicer;

function updatePlateNavUI() {
    const prevBtn = document.getElementById('viewer-plate-prev');
    const nextBtn = document.getElementById('viewer-plate-next');
    const label = document.getElementById('viewer-plate-label');
    if (!prevBtn || !nextBtn || !label) return;
    if (viewerPlateCount <= 1) {
        prevBtn.style.display = 'none';
        nextBtn.style.display = 'none';
        label.style.display = 'none';
        return;
    }
    prevBtn.style.display = viewerCurrentPlate > 1 ? 'flex' : 'none';
    nextBtn.style.display = viewerCurrentPlate < viewerPlateCount ? 'flex' : 'none';
    label.style.display = 'block';
    label.textContent = `${I18N.t('viewer.plate') || 'Plateau'} ${viewerCurrentPlate}/${viewerPlateCount}`;
}

function goToPlate(delta) {
    const newPlate = viewerCurrentPlate + delta;
    if (newPlate < 1 || newPlate > viewerPlateCount || !viewerCurrentPath) return;
    viewerCurrentPlate = newPlate;
    load3DModel(viewerCurrentPath, viewerCurrentPlate);
    updatePlateNavUI();
}

function close3DViewer() {
disposeViewer3D();
closeModal('modal-3d-viewer');
viewerCurrentPath = null;
viewerPlateCount = 1;
viewerCurrentPlate = 1;
viewerOverhangMode = false;
viewerCurrentOrientation = 'default';
const overhangBtn = document.getElementById('viewer-overhang-toggle');
const overhangLegend = document.getElementById('viewer-overhang-legend');
if (overhangBtn) {
    overhangBtn.checked = false;
}
if (overhangLegend) overhangLegend.style.display = 'none';
const orientationSelect = document.getElementById('viewer-orientation-select');
if (orientationSelect) orientationSelect.value = 'default';
const suggestionsPanel = document.getElementById('viewer-orientation-suggestions');
if (suggestionsPanel) { suggestionsPanel.style.display = 'none'; suggestionsPanel.innerHTML = ''; }
}
let viewer3DLoadToken = 0;

function makeAxisLabelSprite(text, hexColor) {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = hexColor;
    ctx.beginPath();
    ctx.arc(32, 32, 27, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 30px Arial, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 32, 34);
    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    const material = new THREE.SpriteMaterial({ map: texture, depthTest: false, depthWrite: false, transparent: true });
    const sprite = new THREE.Sprite(material);
    sprite.scale.set(4.6, 4.6, 1);
    return sprite;
}

function buildAxisGizmo() {
    const group = new THREE.Group();
    const axisLength = 9.5;
    const axes = [
        { dir: new THREE.Vector3(1, 0, 0), color: 0xe6453c, hex: '#e6453c', label: 'X' },
        { dir: new THREE.Vector3(0, 1, 0), color: 0x4dd977, hex: '#4dd977', label: 'Y' },
        { dir: new THREE.Vector3(0, 0, 1), color: 0x4ea1d3, hex: '#4ea1d3', label: 'Z' },
    ];
    axes.forEach(({ dir, color, hex, label }) => {
        const tip = dir.clone().multiplyScalar(axisLength);
        const posGeom = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), tip]);
        group.add(new THREE.Line(posGeom, new THREE.LineBasicMaterial({ color })));

        const negTip = dir.clone().multiplyScalar(-axisLength * 0.55);
        const negGeom = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), negTip]);
        group.add(new THREE.Line(negGeom, new THREE.LineBasicMaterial({ color: 0x777777, transparent: true, opacity: 0.6 })));

        const sprite = makeAxisLabelSprite(label, hex);
        sprite.position.copy(tip);
        group.add(sprite);
    });
    return group;
}

function _getViewerOrientationMatrix(key) {
    if (key === 'default' || !key) return null;
    switch (key) {
        case 'flipZ': return new THREE.Matrix4().makeRotationX(Math.PI);
        case 'posX': return new THREE.Matrix4().makeRotationY(Math.PI / 2);
        case 'negX': return new THREE.Matrix4().makeRotationY(-Math.PI / 2);
        case 'posY': return new THREE.Matrix4().makeRotationX(-Math.PI / 2);
        case 'negY': return new THREE.Matrix4().makeRotationX(Math.PI / 2);
        default: return null;
    }
}

function setViewerOrientation(key) {
    if (!viewerMesh) return;
    const geometry = viewerMesh.geometry;
    const orig = geometry.userData;
    if (!orig.originalPosition || !orig.originalNormal) return;

    const posAttr = geometry.getAttribute('position');
    const normAttr = geometry.getAttribute('normal');
    posAttr.array.set(orig.originalPosition);
    normAttr.array.set(orig.originalNormal);
    posAttr.needsUpdate = true;
    normAttr.needsUpdate = true;

    const matrix = _getViewerOrientationMatrix(key);
    if (matrix) geometry.applyMatrix4(matrix);

    const overhangColors = computeOverhangVertexColors(geometry);
    if (overhangColors) {
        geometry.setAttribute('color', overhangColors);
        if (!viewerMesh.userData.overhangMaterial || viewerMesh.userData.overhangMaterial === viewerMesh.userData.shadedMaterial) {
            viewerMesh.userData.overhangMaterial = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide });
        }
        if (viewerOverhangMode) viewerMesh.material = viewerMesh.userData.overhangMaterial;
    }
    viewerCurrentOrientation = key;
}
window.setViewerOrientation = setViewerOrientation;

function computeOverhangVertexColors(geometry, thresholdDeg = OVERHANG_THRESHOLD_DEG) {
    const normalAttr = geometry.getAttribute('normal');
    const posAttr = geometry.getAttribute('position');
    if (!normalAttr || !posAttr) return null;
    const count = normalAttr.count;
    const colors = new Float32Array(count * 3);
    const dThreshold = Math.cos(THREE.MathUtils.degToRad(thresholdDeg));
    const safeColor = new THREE.Color(0x4ea1d3);
    const warnColor = new THREE.Color(0xffcc33);
    const critColor = new THREE.Color(0xff3b30);
    const tmp = new THREE.Color();


    geometry.computeBoundingBox();
    const minZ = geometry.boundingBox.min.z;
    const heightZ = geometry.boundingBox.max.z - minZ;
    const bedEpsilon = Math.max(heightZ * 0.01, 0.15);

    for (let i = 0; i < count; i++) {
        const z = posAttr.getZ(i);
        let c;
        if (z - minZ <= bedEpsilon) {
            c = safeColor;
        } else {
            const nz = normalAttr.getZ(i);
            const downFactor = -nz;
            if (downFactor > dThreshold) {
                const t = Math.min(1, (downFactor - dThreshold) / (1 - dThreshold));
                c = tmp.copy(warnColor).lerp(critColor, t);
            } else {
                c = safeColor;
            }
        }
        colors[i * 3] = c.r;
        colors[i * 3 + 1] = c.g;
        colors[i * 3 + 2] = c.b;
    }
    return new THREE.BufferAttribute(colors, 3);
}

// ---------------------------------------------------------------------------
// Suggestion d'orientation — calcul géométrique pur (pas d'appel IA/slicer).
// Pour chaque orientation candidate (les 6 déjà proposées dans le menu),
// on rejoue le même calcul que computeOverhangVertexColors mais par triangle,
// pour obtenir des surfaces exploitables : surface en surplomb, surface de
// contact avec le plateau, hauteur totale. On combine ça en un score simple
// pour classer les orientations, sans jamais modifier le mesh affiché.
// ---------------------------------------------------------------------------

const ORIENTATION_CANDIDATE_KEYS = ['default', 'flipZ', 'posX', 'negX', 'posY', 'negY'];

function _scoreMeshOrientation(origPosition, key, thresholdDeg = OVERHANG_THRESHOLD_DEG) {
    const matrix = _getViewerOrientationMatrix(key);
    const triCount = Math.floor(origPosition.length / 9);
    const p0 = new THREE.Vector3(), p1 = new THREE.Vector3(), p2 = new THREE.Vector3();
    const e1 = new THREE.Vector3(), e2 = new THREE.Vector3(), n = new THREE.Vector3();
    const dThreshold = Math.cos(THREE.MathUtils.degToRad(thresholdDeg));

    // Passe 1 : bounding box en Z une fois orientée, pour situer le plateau.
    let minZ = Infinity, maxZ = -Infinity;
    for (let i = 2; i < origPosition.length; i += 3) {
        let z = origPosition[i];
        if (matrix) {
            p0.set(origPosition[i - 2], origPosition[i - 1], z).applyMatrix4(matrix);
            z = p0.z;
        }
        if (z < minZ) minZ = z;
        if (z > maxZ) maxZ = z;
    }
    const height = maxZ - minZ;
    const bedEpsilon = Math.max(height * 0.01, 0.15);

    let overhangArea = 0, contactArea = 0, totalArea = 0;
    for (let t = 0; t < triCount; t++) {
        const base = t * 9;
        p0.set(origPosition[base], origPosition[base + 1], origPosition[base + 2]);
        p1.set(origPosition[base + 3], origPosition[base + 4], origPosition[base + 5]);
        p2.set(origPosition[base + 6], origPosition[base + 7], origPosition[base + 8]);
        if (matrix) { p0.applyMatrix4(matrix); p1.applyMatrix4(matrix); p2.applyMatrix4(matrix); }

        e1.subVectors(p1, p0);
        e2.subVectors(p2, p0);
        n.crossVectors(e1, e2);
        const area = n.length() * 0.5;
        if (area <= 0) continue;
        n.normalize();
        totalArea += area;

        const centroidZ = (p0.z + p1.z + p2.z) / 3;
        if (centroidZ - minZ <= bedEpsilon) {
            contactArea += area;
            continue;
        }
        const downFactor = -n.z;
        if (downFactor > dThreshold) {
            const t2 = Math.min(1, (downFactor - dThreshold) / (1 - dThreshold));
            overhangArea += area * t2;
        }
    }
    return { key, height, contactArea, overhangArea, totalArea };
}

function computeOrientationSuggestions() {
    if (!viewerMesh) return [];
    const origPosition = viewerMesh.geometry.userData.originalPosition;
    if (!origPosition) return [];

    const results = ORIENTATION_CANDIDATE_KEYS.map(key => _scoreMeshOrientation(origPosition, key));
    const maxHeight = Math.max(...results.map(r => r.height), 1);

    results.forEach(r => {
        const overhangRatio = r.totalArea > 0 ? r.overhangArea / r.totalArea : 0;
        const contactRatio = r.totalArea > 0 ? r.contactArea / r.totalArea : 0;
        const heightRatio = r.height / maxHeight;
        // Score heuristique — plus bas = meilleur. Les surplombs pèsent le plus
        // (support matière + risque d'échec), la surface de contact aide
        // l'adhésion, la hauteur influe sur le temps et le risque de warping.
        r.score = overhangRatio * 0.6 - contactRatio * 0.25 + heightRatio * 0.15;
        r.overhangPct = Math.round(overhangRatio * 1000) / 10;
        r.contactPct = Math.round(contactRatio * 1000) / 10;
    });

    results.sort((a, b) => a.score - b.score);
    return results;
}

const ORIENTATION_LABEL_KEYS = {
    default: 'viewer.orientation_default', flipZ: 'viewer.orientation_flip_z',
    posX: 'viewer.orientation_pos_x', negX: 'viewer.orientation_neg_x',
    posY: 'viewer.orientation_pos_y', negY: 'viewer.orientation_neg_y'
};
const ORIENTATION_LABEL_FALLBACKS = {
    default: "Orientation d'origine", flipZ: 'Face opposée (haut ↔ bas)',
    posX: 'Face +X sur le plateau', negX: 'Face -X sur le plateau',
    posY: 'Face +Y sur le plateau', negY: 'Face -Y sur le plateau'
};

function suggestBestOrientation() {
    const panel = document.getElementById('viewer-orientation-suggestions');
    if (!panel) return;
    const results = computeOrientationSuggestions();
    if (!results.length) return;

    const top = results.slice(0, 3);
    panel.innerHTML = `
        <div style="font-size:11px; color:var(--text-secondary); margin-bottom:6px; font-weight:600;">
            <i class="fa-solid fa-wand-magic-sparkles"></i> ${_t2('viewer.orientation_suggest_title', 'Orientations suggérées (moins de surplombs)')}
        </div>
        ${top.map((r, i) => `
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; padding:5px 0; ${i > 0 ? 'border-top:1px solid var(--border);' : ''}">
                <div style="font-size:11px; color:var(--text-secondary);">
                    <strong style="color:var(--text-primary);">${i + 1}.</strong>
                    ${_t2(ORIENTATION_LABEL_KEYS[r.key], ORIENTATION_LABEL_FALLBACKS[r.key])}
                    <div style="color:var(--text-muted); font-size:10px;">
                        ${_t2('viewer.orientation_suggest_stats', `surplomb ${r.overhangPct}% · contact plateau ${r.contactPct}%`, { overhang: r.overhangPct, contact: r.contactPct })}
                    </div>
                </div>
                <button type="button" class="btn btn-ghost btn-sm" style="font-size:11px; padding:4px 8px;"
                    onclick="_applySuggestedOrientation('${r.key}')">
                    ${_t2('viewer.orientation_suggest_apply', 'Appliquer')}
                </button>
            </div>
        `).join('')}
        <div id="viewer-orientation-explain" style="margin-top:6px; font-size:11px; color:var(--text-secondary);"></div>
        <button type="button" class="btn btn-ghost btn-sm" style="font-size:11px; padding:4px 8px; margin-top:4px; width:100%;"
            onclick="_explainOrientationSuggestion()">
            <i class="fa-solid fa-comment-dots"></i> ${_t2('viewer.orientation_suggest_explain', 'Explique-moi pourquoi')}
        </button>
    `;
    panel.style.display = 'block';
    panel.dataset.suggestions = JSON.stringify(top);
}
window.suggestBestOrientation = suggestBestOrientation;

async function _explainOrientationSuggestion() {
    const panel = document.getElementById('viewer-orientation-suggestions');
    const explainEl = document.getElementById('viewer-orientation-explain');
    if (!panel || !explainEl || !panel.dataset.suggestions) return;
    explainEl.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${_t2('viewer.orientation_explain_loading', "L'IA locale réfléchit...")}`;
    try {
        const res = await fetch(`${API}/api/ollama/explain-orientation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: viewerCurrentFileName || viewerCurrentPath || '',
                suggestions: JSON.parse(panel.dataset.suggestions)
            })
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            explainEl.textContent = data.error || _t2('viewer.orientation_explain_error', 'Explication indisponible.');
            return;
        }
        explainEl.textContent = data.explanation;
    } catch (e) {
        explainEl.textContent = _t2('viewer.orientation_explain_error', 'Explication indisponible.');
    }
}
window._explainOrientationSuggestion = _explainOrientationSuggestion;

function _applySuggestedOrientation(key) {
    setViewerOrientation(key);
    const select = document.getElementById('viewer-orientation-select');
    if (select) select.value = key;
    if (!viewerOverhangMode) {
        const btn = document.getElementById('viewer-overhang-toggle');
        if (btn) { btn.checked = true; toggleOverhangView(); }
    }
}
window._applySuggestedOrientation = _applySuggestedOrientation;

function toggleOverhangView() {
    const btn = document.getElementById('viewer-overhang-toggle');
    viewerOverhangMode = btn ? btn.checked : !viewerOverhangMode;
    const legend = document.getElementById('viewer-overhang-legend');
    if (legend) legend.style.display = viewerOverhangMode ? 'block' : 'none';
    if (viewerMesh && viewerMesh.userData) {
        viewerMesh.material = viewerOverhangMode ? viewerMesh.userData.overhangMaterial : viewerMesh.userData.shadedMaterial;
    }
}


function _createViewerRenderer() {
const attemptOptions = [
    { antialias: true },
    { antialias: false, failIfMajorPerformanceCaveat: false, powerPreference: 'default' },
    { antialias: false, failIfMajorPerformanceCaveat: false, powerPreference: 'low-power' },
];
let lastError = null;
for (const opts of attemptOptions) {
    try {
        return new THREE.WebGLRenderer(opts);
    } catch (e) {
        lastError = e;
        console.warn('[3D Viewer] Échec création contexte WebGL avec', opts, e);
    }
}
const wrapped = new Error('WEBGL_CONTEXT_UNAVAILABLE');
wrapped.cause = lastError;
throw wrapped;
}

function load3DModel(filePath, plateIndex) {
disposeViewer3D();
const suggestionsPanel = document.getElementById('viewer-orientation-suggestions');
if (suggestionsPanel) { suggestionsPanel.style.display = 'none'; suggestionsPanel.innerHTML = ''; }
const myToken = ++viewer3DLoadToken;
const container = document.getElementById('viewer-canvas-container');
container.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin fa-2x"></i></div>`;
let meshUrl = `${API}/api/file/mesh?path=${encodeURIComponent(filePath)}`;
if (plateIndex) meshUrl += `&plate=${plateIndex}`;
fetch(meshUrl)
.then(res => {
if (!res.ok) {
    return res.json()
        .then(data => { throw new Error(data && data.error ? data.error : `${I18N.t('toast.file_not_found')} (HTTP ${res.status})`); })
        .catch(parseErr => {
            if (parseErr instanceof SyntaxError) throw new Error(`${I18N.t('toast.file_not_found')} (HTTP ${res.status})`);
            throw parseErr;
        });
}
return res.blob();
})
.then(blob => {
if (myToken !== viewer3DLoadToken) return;
const url = URL.createObjectURL(blob);
viewerScene = new THREE.Scene();
viewerScene.background = new THREE.Color('#1a1d23');
viewerCamera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 10000);
viewerCamera.position.set(50, 50, 50);
viewerRenderer = _createViewerRenderer();
viewerRenderer.setSize(container.clientWidth, container.clientHeight);
viewerRenderer.setPixelRatio(window.devicePixelRatio);
container.innerHTML = '';
container.appendChild(viewerRenderer.domElement);

    viewerGizmoScene = new THREE.Scene();
    viewerGizmoScene.add(buildAxisGizmo());
    viewerGizmoCamera = new THREE.OrthographicCamera(-15, 15, 15, -15, 0.1, 100);

    viewerControls = new THREE.TrackballControls(viewerCamera, viewerRenderer.domElement);
    viewerControls.rotateSpeed = 4.0;
    viewerControls.zoomSpeed = 1.2;
    viewerControls.panSpeed = 0.8;
    viewerControls.dynamicDampingFactor = 0.15;
    viewerControls.staticMoving = false;

    const ambientLight = new THREE.AmbientLight(0x404040, 1.3);
    viewerScene.add(ambientLight);


    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.7);
    directionalLight.position.set(0, 0, 1);
    viewerCamera.add(directionalLight);
    viewerScene.add(viewerCamera);

    const loader = new THREE.STLLoader();

    loader.load(url, function (geometry) {
        if (myToken !== viewer3DLoadToken) { URL.revokeObjectURL(url); return; }


        geometry.deleteAttribute('normal');
        geometry.computeVertexNormals();
        const shadedMaterial = new THREE.MeshPhongMaterial({ color: 0x4ea1d3, specular: 0x111111, shininess: 120, flatShading: false, side: THREE.DoubleSide });
        geometry.computeBoundingBox();
        const center = new THREE.Vector3();
        geometry.boundingBox.getCenter(center);
        geometry.translate(-center.x, -center.y, -center.z);
        geometry.userData.originalPosition = geometry.getAttribute('position').array.slice();
        geometry.userData.originalNormal = geometry.getAttribute('normal').array.slice();

        const overhangColors = computeOverhangVertexColors(geometry);
        let overhangMaterial = shadedMaterial;
        if (overhangColors) {
            geometry.setAttribute('color', overhangColors);
            overhangMaterial = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide });
        }

        viewerMesh = new THREE.Mesh(geometry, viewerOverhangMode ? overhangMaterial : shadedMaterial);
        viewerMesh.userData.shadedMaterial = shadedMaterial;
        viewerMesh.userData.overhangMaterial = overhangMaterial;
        viewerScene.add(viewerMesh);
        const overhangBtn = document.getElementById('viewer-overhang-toggle');
        const overhangLegend = document.getElementById('viewer-overhang-legend');
        if (overhangBtn) {
            overhangBtn.checked = viewerOverhangMode;
        }
        if (overhangLegend) overhangLegend.style.display = viewerOverhangMode ? 'block' : 'none';
        const size = new THREE.Vector3();
        geometry.boundingBox.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = viewerCamera.fov * (Math.PI / 180);
        const cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2)) * 1.5;
        viewerCamera.up.set(0, 1, 0);
        viewerCamera.position.set(cameraZ, cameraZ, cameraZ);
        viewerCamera.lookAt(0, 0, 0);
        viewerHomeCameraPos = viewerCamera.position.clone();

        viewerActive = true;
        function animate() {
            if (!viewerActive) return;
            viewerAnimationId = requestAnimationFrame(animate);
            viewerControls.update();

            const width = container.clientWidth;
            const height = container.clientHeight;

            viewerRenderer.autoClear = false;
            viewerRenderer.setViewport(0, 0, width, height);
            viewerRenderer.setScissorTest(false);
            viewerRenderer.clear(true, true, true);
            viewerRenderer.render(viewerScene, viewerCamera);

            if (viewerGizmoScene && viewerGizmoCamera) {
                const gizmoSize = 132;
                const margin = 16;
                viewerGizmoCamera.position.set(0, 0, 30).applyQuaternion(viewerCamera.quaternion);
                viewerGizmoCamera.up.copy(viewerCamera.up);
                viewerGizmoCamera.quaternion.copy(viewerCamera.quaternion);

                viewerRenderer.setScissorTest(true);
                viewerRenderer.setScissor(width - gizmoSize - margin, height - gizmoSize - margin, gizmoSize, gizmoSize);
                viewerRenderer.setViewport(width - gizmoSize - margin, height - gizmoSize - margin, gizmoSize, gizmoSize);
                viewerRenderer.clearDepth();
                viewerRenderer.render(viewerGizmoScene, viewerGizmoCamera);
                viewerRenderer.setScissorTest(false);
            }
        }
        animate();

        URL.revokeObjectURL(url);

    }, undefined, function (error) {
        if (myToken !== viewer3DLoadToken) return;
        console.error('[3D Viewer] Fichier illisible/corrompu:', error);
        viewerActive = false;
        container.innerHTML = `<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:8px;color:var(--danger);"><i class="fa-solid fa-triangle-exclamation fa-2x"></i><span>${I18N.t('toast.file_unreadable') || 'Fichier illisible ou corrompu'}</span></div>`;
    });
})
.catch(err => {
    if (myToken !== viewer3DLoadToken) return;
    console.error('[3D Viewer]', err);
    if (err && err.message === 'WEBGL_CONTEXT_UNAVAILABLE') {
        const hint = I18N.t('viewer.webgl_unavailable_hint') || "Impossible d'initialiser l'affichage 3D sur cette machine (accélération graphique indisponible ou bloquée). Vérifie que l'accélération matérielle n'est pas désactivée, que les pilotes GPU sont à jour, ou qu'un antivirus (Avast, etc.) ne bloque pas le rendu graphique de l'application.";
        container.innerHTML = `<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:10px;color:var(--danger);text-align:center;padding:0 24px;">
            <i class="fa-solid fa-display-slash fa-2x"></i>
            <span>${escapeHtml(hint)}</span>
            <button type="button" class="btn btn-ghost btn-sm" onclick="load3DModel('${escapeHtml(filePath)}', ${plateIndex || 1})"><i class="fa-solid fa-rotate-right"></i> ${I18N.t('actions.retry') || 'Réessayer'}</button>
        </div>`;
        return;
    }
    const message = (err && err.message) ? escapeHtml(err.message) : I18N.t('toast.connection_error');
    container.innerHTML = `<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:8px;color:var(--danger);text-align:center;padding:0 16px;"><i class="fa-solid fa-triangle-exclamation fa-2x"></i><span>${message}</span></div>`;
});
}


async function loadSlicerSettings() {
const select = document.getElementById('default-slicer-select');
const preferredSelect = document.getElementById('preferred-slicer-select');
if (select || preferredSelect) {
try {
const res = await fetch(`${API}/api/settings`);
if (res.ok) {
const data = await res.json();
if (select && data.default_slicer) select.value = data.default_slicer;
if (preferredSelect && data.preferred_slicer_id) preferredSelect.value = data.preferred_slicer_id;
}
} catch (err) { console.warn('[Slicer Settings] Échec'); }
}
loadSlicerProfiles();
}


const SLICER_NAME_LABELS = {
    prusaslicer: 'PrusaSlicer',
    superslicer: 'SuperSlicer',
    orcaslicer: 'OrcaSlicer',
    bambustudio: 'Bambu Studio',
    cura: 'Cura',
    creality_print: 'Creality Print',
    anycubic_slicer_next: 'Anycubic Slicer Next',
};


const PROFILE_TYPE_META = {
    printer:  { icon: 'fa-print',    color: 'var(--accent)',     i18nKey: 'settings.slicer_profiles_type_printer',  fallback: 'Imprimante' },
    filament: { icon: 'fa-droplet',  color: '#c084fc',           i18nKey: 'settings.slicer_profiles_type_filament', fallback: 'Filament' },
    process:  { icon: 'fa-sliders',  color: 'var(--text-muted)', i18nKey: 'settings.slicer_profiles_type_process',  fallback: 'Réglages' },
};

function _profileTypeMeta(type) {
    return PROFILE_TYPE_META[type] || PROFILE_TYPE_META.process;
}

let _lastSlicerProfiles = [];
let _slicerProfilesFilter = 'unassigned';
let _slicerProfilesTypeFilter = 'all';

async function loadSlicerProfiles() {
const list = document.getElementById('slicer-profiles-list');
if (!list) return;
try {
const res = await fetch(`${API}/api/slicer-profiles`);
const data = await res.json();
renderSlicerProfiles(data.profiles || []);
} catch (err) {
console.warn('[SlicerProfiles] Échec du chargement:', err);
}
}

function filterSlicerProfiles(value) {
_slicerProfilesFilter = value || 'unassigned';
renderSlicerProfiles(_lastSlicerProfiles);
}

function filterSlicerProfilesByType(value) {
_slicerProfilesTypeFilter = value || 'all';
renderSlicerProfiles(_lastSlicerProfiles);
}

function _populatePrinterSelects() {
const selects = [
    document.getElementById('slicer-profile-import-printer'),
    document.getElementById('slicer-profiles-filter'),
    document.getElementById('slicer-ai-printer-select'),
    document.getElementById('nesting-ai-printer-select'),
    document.getElementById('sosprint-printer-select'),
    document.getElementById('settings-printer-power-select'),
    document.getElementById('batch-slicer-printer-select'),
    document.getElementById('folder-batch-printer-select'),
];
selects.forEach(sel => {
    if (!sel) return;
    const current = sel.value;
    sel.querySelectorAll('option[data-dynamic]').forEach(o => o.remove());
    (printersList || []).forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        opt.setAttribute('data-dynamic', '1');
        sel.appendChild(opt);
    });
    if ([...sel.options].some(o => o.value === current)) sel.value = current;
});
}

function _populateMaterialSelects(profiles) {
    const selects = [
        document.getElementById('slicer-ai-material-select'),
        document.getElementById('nesting-ai-material-select'),
    ];

    (profiles || []).forEach(p => {
        if (p.profile_type === 'filament' && !p.material_type && p.name) {
            const nameLower = p.name.toLowerCase();
            const knownMats = ['pla', 'petg', 'abs', 'tpu', 'asa', 'nylon', 'pc', 'hips', 'pva'];
            for (const mat of knownMats) {
                if (nameLower.includes(mat)) {
                    p.material_type = mat.toUpperCase();
                    break;
                }
            }
        }
    });

    const materials = [...new Set((profiles || []).map(p => p.material_type).filter(Boolean))].sort();
    selects.forEach(sel => {
        if (!sel) return;
        const current = sel.value;
        sel.querySelectorAll('option[data-dynamic]').forEach(o => o.remove());
        materials.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = m;
            opt.setAttribute('data-dynamic', '1');
            sel.appendChild(opt);
        });
        if (materials.includes(current)) sel.value = current;
    });
}

function renderSlicerProfiles(profiles) {
const list = document.getElementById('slicer-profiles-list');
if (!list) return;
_lastSlicerProfiles = profiles || [];
_populatePrinterSelects();
_populateMaterialSelects(profiles);

if (!_lastSlicerProfiles.length) {
list.innerHTML = `<p class="settings-hint" data-i18n="settings.slicer_profiles_empty">${_t3('settings.slicer_profiles_empty', 'Aucun profil importé pour le moment.')}</p>`;
return;
}

const filter = _slicerProfilesFilter;
const typeFilter = _slicerProfilesTypeFilter;
const filtered = _lastSlicerProfiles.filter(p => {
    if (typeFilter !== 'all' && p.profile_type !== typeFilter) return false;
    if (filter === 'all') return true;
    if (filter === 'unassigned') return !p.printer_id || p.printer_match_confirmed === false;
    return String(p.printer_id) === String(filter);
});

if (!filtered.length) {
const emptyKey = filter === 'unassigned' ? 'settings.slicer_profiles_empty_unassigned' : 'settings.slicer_profiles_empty_filtered';
const emptyFallback = filter === 'unassigned' ? 'Aucun profil non assigné — tous tes profils sont déjà classés par imprimante.' : 'Aucun profil pour cette imprimante.';
list.innerHTML = `<p class="settings-hint" data-i18n="${emptyKey}">${_t3(emptyKey, emptyFallback)}</p>`;
return;
}

list.innerHTML = filtered.map(p => {
    const printerOptions = (printersList || []).map(pr =>
        `<option value="${pr.id}" ${pr.id === p.printer_id ? 'selected' : ''}>${escapeHtml(pr.name)}</option>`
    ).join('');
    const isSuggested = !!p.printer_id && p.printer_match_confirmed === false;
    const rawDetected = (!p.printer_id && p.compatible_printers && p.compatible_printers.length)
        ? p.compatible_printers[0] : null;
    const typeMeta = _profileTypeMeta(p.profile_type);


    const typeOptions = ['printer', 'filament', 'process'].map(t => {
        const m = _profileTypeMeta(t);
        return `<option value="${t}" ${t === p.profile_type ? 'selected' : ''}>${escapeHtml(_t3(m.i18nKey, m.fallback))}</option>`;
    }).join('');
    const typeBadge = `<select onchange="reassignSlicerProfileType('${p.id}', this.value)" style="flex-shrink:0; appearance:none; -webkit-appearance:none; cursor:pointer; display:inline-flex; align-items:center; gap:4px; padding:2px 18px 2px 7px; border-radius:999px; font-size:10px; font-weight:600; color:${typeMeta.color}; background:color-mix(in srgb, ${typeMeta.color} 16%, transparent) url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 10 6%22><path fill=%22${encodeURIComponent(typeMeta.color)}%22 d=%22M0 0l5 6 5-6z%22/></svg>') no-repeat right 6px center/8px 5px; border:1px solid color-mix(in srgb, ${typeMeta.color} 40%, transparent);" title="${_t3('settings.slicer_profiles_type_hint', 'Nature du profil — corrige si la détection auto s’est trompée')}">
        ${typeOptions}
    </select>`;
    return `
    <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; padding:8px 10px; background:var(--bg-input); border:1px solid ${isSuggested ? 'var(--warning, #d9a441)' : 'var(--border)'}; border-radius:var(--radius); font-size:12.5px;">
        <div style="min-width:0; flex:1;">
            <div style="display:flex; align-items:center; gap:6px; min-width:0;">
                ${typeBadge}
                <div style="font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(p.name)}</div>
            </div>
            <div style="color:var(--text-muted); font-size:11px; margin-top:2px;">
                ${escapeHtml(SLICER_NAME_LABELS[p.slicer] || p.slicer)}${p.material_type ? ' · ' + escapeHtml(p.material_type) : ''}${p.layer_height ? ' · ' + p.layer_height + 'mm' : ''}
            </div>
            ${isSuggested ? `<div style="color:var(--warning, #d9a441); font-size:10.5px; margin-top:2px;"><i class="fa-solid fa-wand-magic-sparkles"></i> ${_t3('settings.slicer_profiles_suggested_match', 'Imprimante suggérée — à confirmer')}</div>` : ''}
            ${rawDetected ? `<div style="color:var(--text-muted); font-size:10.5px; margin-top:2px; font-style:italic;"><i class="fa-solid fa-tag"></i> ${_t3('settings.slicer_profiles_raw_detected', 'Nom détecté')} : ${escapeHtml(rawDetected)}</div>` : ''}
        </div>
        ${isSuggested ? `<button class="btn btn-ghost btn-sm" style="flex-shrink:0; color:var(--success, #4caf50);" onclick="confirmSlicerProfileMatch('${p.id}', '${p.printer_id}')" data-i18n-title="settings.slicer_profiles_confirm_match" title="${_t3('settings.slicer_profiles_confirm_match', 'Confirmer cette imprimante')}">
            <i class="fa-solid fa-check"></i>
        </button>` : ''}
        <select class="settings-select settings-select-sm" onchange="reassignSlicerProfilePrinter('${p.id}', this.value)" style="flex-shrink:0;" title="${_t3('settings.slicer_profiles_target_printer', 'Pour quelle imprimante ?')}">
            <option value="">${_t3('settings.slicer_profiles_no_printer', 'Non assigné')}</option>
            ${printerOptions}
        </select>
        <button class="btn btn-ghost btn-sm" style="flex-shrink:0;" onclick="deleteSlicerProfile('${p.id}')" data-i18n-title="actions.delete" title="Supprimer">
            <i class="fa-solid fa-trash-can"></i>
        </button>
    </div>
`;
}).join('');
}

async function reassignSlicerProfilePrinter(profileId, printerId) {
try {
    const res = await fetch(`${API}/api/slicer-profiles/${profileId}/printer`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ printer_id: printerId || null })
    });
    const data = await res.json();
    if (!res.ok) { showToast(data.error || _t3('toast.error', 'Erreur'), 'error'); return; }
    renderSlicerProfiles(data.profiles || []);
} catch (err) {
    showToast(_t3('toast.connection_error', 'Erreur de connexion'), 'error');
}
}

async function confirmSlicerProfileMatch(profileId, printerId) {
    await reassignSlicerProfilePrinter(profileId, printerId);
}

async function reassignSlicerProfileType(profileId, profileType) {
try {
    const res = await fetch(`${API}/api/slicer-profiles/${profileId}/type`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_type: profileType })
    });
    const data = await res.json();
    if (!res.ok) { showToast(data.error || _t3('toast.error', 'Erreur'), 'error'); return; }
    renderSlicerProfiles(data.profiles || []);
    showToast(_t3('settings.slicer_profiles_type_updated', 'Type de profil mis à jour'), 'success');
} catch (err) {
    showToast(_t3('toast.connection_error', 'Erreur de connexion'), 'error');
}
}

async function importSlicerProfiles(fileList) {
if (!fileList || !fileList.length) return;
const formData = new FormData();
for (const file of fileList) formData.append('profiles', file);
const printerSel = document.getElementById('slicer-profile-import-printer');
if (printerSel && printerSel.value) formData.append('printer_id', printerSel.value);
try {
showToast(_t3('toast.importing', 'Import en cours...'), 'info');
const res = await fetch(`${API}/api/slicer-profiles/import`, { method: 'POST', body: formData });
const data = await res.json();
if (!res.ok) {
    showToast(data.error || I18N.t('toast.error') || 'Erreur', 'error');
    return;
}
renderSlicerProfiles(data.profiles || []);
const n = (data.imported || []).length;
showToast(_t3('settings.slicer_profiles_imported', `${n} profil(s) importé(s)`, { count: n }), 'success');
if ((data.errors || []).length) {
    console.warn('[SlicerProfiles] Erreurs:', data.errors);
}
} catch (err) {
showToast(I18N.t('toast.connection_error') || 'Erreur de connexion', 'error');
}
}

async function _confirmSlicerImportWithoutPrinters() {
    if ((printersList || []).length > 0) return true;
    return await showConfirmDialog(
        _t3('settings.slicer_profiles_no_printer_warning',
            "Tu n'as pas encore enregistré d'imprimante. Les profils importés ne pourront pas être assignés tant qu'aucune imprimante n'existe. Ajoute d'abord une imprimante dans la page « Imprimantes », ou continue et assigne-les plus tard."),
        {
            title: _t3('settings.slicer_profiles_no_printer_warning_title', 'Aucune imprimante enregistrée'),
            confirmLabel: _t3('settings.slicer_profiles_continue_anyway', 'Importer quand même'),
            cancelLabel: _t3('actions.cancel', 'Annuler')
        }
    );
}

window.openSlicerProfileFilePicker = async function () {
    if (!(await _confirmSlicerImportWithoutPrinters())) return;
    document.getElementById('slicer-profile-file-input').click();
};


let _pendingSlicerImportFiles = [];

window.openSlicerImportAssignModal = function (fileList) {
    if (!fileList || !fileList.length) return;
    _pendingSlicerImportFiles = Array.from(fileList);
    const list = document.getElementById('slicer-import-assign-list');
    if (!list) { importSlicerProfiles(_pendingSlicerImportFiles); return; }

    const defaultPrinterId = document.getElementById('slicer-profile-import-printer')?.value || '';
    const printerOptions = (printersList || []).map(pr =>
        `<option value="${pr.id}" ${String(pr.id) === String(defaultPrinterId) ? 'selected' : ''}>${escapeHtml(pr.name)}</option>`
    ).join('');

    list.innerHTML = _pendingSlicerImportFiles.map((file, idx) => `
        <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; padding:8px 10px; background:var(--bg-input); border:1px solid var(--border); border-radius:var(--radius); font-size:12.5px;">
            <span style="min-width:0; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(file.name)}</span>
            <select class="settings-select settings-select-sm" data-file-index="${idx}" style="flex-shrink:0; min-width:150px;">
                <option value="" ${!defaultPrinterId ? 'selected' : ''}>${_t3('settings.slicer_profiles_no_printer', 'Non assigné')}</option>
                ${printerOptions}
            </select>
        </div>
    `).join('');

    openModal('modal-slicer-import-assign');
};

async function confirmSlicerImportAssign() {
    if (!_pendingSlicerImportFiles.length) { closeModal('modal-slicer-import-assign'); return; }

    const rows = document.querySelectorAll('#slicer-import-assign-list select[data-file-index]');
    const groups = new Map();
    rows.forEach(sel => {
        const idx = parseInt(sel.dataset.fileIndex, 10);
        const file = _pendingSlicerImportFiles[idx];
        if (!file) return;
        const printerId = sel.value || '';
        if (!groups.has(printerId)) groups.set(printerId, []);
        groups.get(printerId).push(file);
    });

    closeModal('modal-slicer-import-assign');
    showToast(_t3('toast.importing', 'Import en cours...'), 'info');

    let totalImported = 0, hadError = false, lastProfiles = null;
    for (const [printerId, files] of groups) {
        const formData = new FormData();
        for (const file of files) formData.append('profiles', file);
        if (printerId) formData.append('printer_id', printerId);
        try {
            const res = await fetch(`${API}/api/slicer-profiles/import`, { method: 'POST', body: formData });
            const data = await res.json();
            if (!res.ok) {
                hadError = true;
                showToast(data.error || I18N.t('toast.error') || 'Erreur', 'error');
                continue;
            }
            totalImported += (data.imported || []).length;
            lastProfiles = data.profiles || lastProfiles;
            if ((data.errors || []).length) console.warn('[SlicerProfiles] Erreurs:', data.errors);
        } catch (err) {
            hadError = true;
            showToast(I18N.t('toast.connection_error') || 'Erreur de connexion', 'error');
        }
    }

    if (lastProfiles) renderSlicerProfiles(lastProfiles);
    else loadSlicerProfiles();

    if (totalImported > 0) {
        showToast(_t3('settings.slicer_profiles_imported', `${totalImported} profil(s) importé(s)`, { count: totalImported }), 'success');
    } else if (!hadError) {
        showToast(I18N.t('toast.error') || 'Erreur', 'error');
    }
    _pendingSlicerImportFiles = [];
}

async function autoDetectSlicerProfiles() {
if (!(await _confirmSlicerImportWithoutPrinters())) return;
const btn = document.getElementById('slicer-profiles-autodetect-btn');
if (btn) btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${_t3('settings.slicer_profiles_scanning', 'Recherche...')}`;
try {
const res = await fetch(`${API}/api/slicer-profiles/auto-detect`, { method: 'POST' });
let data = null;
try { data = await res.json(); } catch (parseErr) {  }
if (!res.ok) {
    const msg = (data && data.error) ? data.error : `Erreur serveur (HTTP ${res.status})`;
    showToast(msg, 'error');
    console.warn('[SlicerProfiles] Auto-detect KO', res.status, data);
    return;
}
renderSlicerProfiles((data && data.profiles) || []);
const n = (data && data.count) || 0;
showToast(n > 0
    ? _t3('settings.slicer_profiles_autodetected', `${n} nouveau(x) profil(s) détecté(s)`, { count: n })
    : _t3('settings.slicer_profiles_none_found', 'Aucun nouveau profil trouvé sur cette machine'), n > 0 ? 'success' : 'info');
} catch (err) {
showToast(_t3('toast.connection_error', 'Erreur de connexion'), 'error');
console.warn('[SlicerProfiles] Auto-detect erreur réseau', err);
} finally {
if (btn) btn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> <span data-i18n="settings.slicer_profiles_autodetect">${_t3('settings.slicer_profiles_autodetect', 'Détecter automatiquement')}</span>`;
}
}

async function refreshSlicerProfiles() {
const btn = document.getElementById('slicer-profiles-refresh-btn');
if (btn) btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${_t3('settings.slicer_profiles_refreshing', 'Actualisation...')}`;
try {
const res = await fetch(`${API}/api/slicer-profiles/refresh`, { method: 'POST' });
let data = null;
try { data = await res.json(); } catch (parseErr) {  }
if (!res.ok) {
    showToast((data && data.error) || `Erreur serveur (HTTP ${res.status})`, 'error');
    return;
}
renderSlicerProfiles((data && data.profiles) || []);
const n = (data && data.updated) || 0;
showToast(n > 0
    ? _t3('settings.slicer_profiles_refreshed', `${n} profil(s) actualisé(s) depuis le slicer`, { count: n })
    : _t3('settings.slicer_profiles_refresh_none', 'Rien à actualiser (déjà à jour)'), n > 0 ? 'success' : 'info');
if (data && data.errors && data.errors.length) console.warn('[SlicerProfiles] Erreurs de rafraîchissement:', data.errors);
} catch (err) {
showToast(_t3('toast.connection_error', 'Erreur de connexion'), 'error');
} finally {
if (btn) btn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> <span data-i18n="settings.slicer_profiles_refresh">${_t3('settings.slicer_profiles_refresh', 'Actualiser depuis le slicer')}</span>`;
}
}

async function deleteSlicerProfile(profileId) {
const ok = await showConfirmDialog(
    _t3('settings.slicer_profiles_delete_confirm', 'Supprimer ce profil importé ?'),
    { danger: true }
);
if (!ok) return;
try {
const res = await fetch(`${API}/api/slicer-profiles/${profileId}`, { method: 'DELETE' });
const data = await res.json();
if (!res.ok) {
    showToast(data.error || I18N.t('toast.error') || 'Erreur', 'error');
    return;
}
renderSlicerProfiles(data.profiles || []);
} catch (err) {
showToast(I18N.t('toast.connection_error') || 'Erreur de connexion', 'error');
}
}

function _t3(key, fallback, params) {
try {
const val = params ? I18N.t(key, params) : I18N.t(key);
if (!val || val === key) return fallback;
return val;
} catch (e) { return fallback; }
}

async function requestProfileRecommendation() {
if (!currentSlicerFile) return;
if (!window.aiEnabled) {
    showToast(_t3('toast.ai_disabled_warning', "L'assistant IA est désactivé dans Paramètres."), 'warning');
    return;
}
const btn = document.getElementById('slicer-ai-recommend-btn');
const box = document.getElementById('slicer-ai-recommend-result');
if (!box) return;
box.style.display = 'block';
box.innerHTML = `<div style="color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> ${_t3('modal.ai_recommend_loading', 'Analyse de la pièce et de vos profils...')}</div>`;
if (btn) btn.disabled = true;
try {
const res = await fetch(`${API}/api/ollama/recommend-profile`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        path: currentSlicerFile,
        printer_id: document.getElementById('slicer-ai-printer-select')?.value || null,
        material_type: document.getElementById('slicer-ai-material-select')?.value || null
    })
});
const data = await res.json();
if (!res.ok) {
    if (data.no_profiles) {
        box.innerHTML = `<div style="color:var(--text-muted);"><i class="fa-solid fa-circle-info"></i> ${_t3('modal.ai_recommend_no_profiles', "Aucun profil importé. Ajoute tes profils dans Paramètres → Slicer pour activer l'assistant.")}</div>`;
    } else {
        box.innerHTML = `<div style="color:var(--danger);">${escapeHtml(data.error || I18N.t('toast.error') || 'Erreur')}</div>`;
    }
    return;
}
renderProfileRecommendation(box, data);
} catch (err) {
box.innerHTML = `<div style="color:var(--danger);">${I18N.t('toast.connection_error') || 'Erreur de connexion'}</div>`;
} finally {
if (btn) btn.disabled = false;
}
}

function renderProfileRecommendation(box, data) {
_lastAiRecommendedProfile = data.profil_recommande_id
    ? { id: data.profil_recommande_id, name: data.profil_recommande }
    : null;
const mods = data.modifications || [];
const modsHtml = mods.length
    ? mods.map(m => `
        <div style="display:flex; gap:8px; align-items:flex-start; padding:6px 0; border-top:1px solid var(--border);">
            <i class="fa-solid fa-check" style="color:var(--accent, #4f8cff); margin-top:2px; flex-shrink:0;"></i>
            <div>
                <div><strong>${escapeHtml(m.parametre || '')}</strong>${(m.valeur_actuelle !== undefined && m.valeur_actuelle !== null) ? ` : ${escapeHtml(String(m.valeur_actuelle))} → ` : ' : '}<strong>${escapeHtml(String(m.valeur_suggeree ?? ''))}</strong></div>
                ${m.raison ? `<div style="color:var(--text-muted); margin-top:2px;">${escapeHtml(m.raison)}</div>` : ''}
            </div>
        </div>
    `).join('')
    : `<p style="color:var(--text-muted); margin-top:6px;">${_t3('modal.ai_recommend_no_changes', 'Ce profil convient tel quel, aucune modification nécessaire.')}</p>`;

box.innerHTML = `
    <div style="padding:8px 10px; background:var(--bg-secondary); border-radius:var(--radius); border:1px solid var(--border);">
        <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.03em;">${_t3('modal.ai_recommend_profile_label', 'Profil recommandé')}</div>
        <div style="font-size:15px; font-weight:700; margin-top:2px;"><i class="fa-solid fa-star" style="color:#f5a623;"></i> ${escapeHtml(data.profil_recommande || '—')}</div>
        ${modsHtml}
    </div>
`;
}


let _lastNestingResult = null;
let _lastAiRecommendedProfile = null;

function openNestingModal() {
if (selectedFiles.size < 2) {
    showToast(_t3('toast.nesting_need_two', 'Sélectionne au moins 2 fichiers pour nester un plateau'), 'warning');
    return;
}
_lastNestingResult = null;
document.getElementById('nesting-preview-wrap').style.display = 'none';
document.getElementById('nesting-send-to-slicer-btn').style.display = 'none';
const aiBox = document.getElementById('nesting-ai-recommend-result');
if (aiBox) { aiBox.style.display = 'none'; aiBox.innerHTML = ''; }
openModal('modal-nesting');
}

async function runNesting() {
const bedW = parseFloat(document.getElementById('nesting-bed-width')?.value) || 220;
const bedH = parseFloat(document.getElementById('nesting-bed-height')?.value) || 220;
const bedZ = parseFloat(document.getElementById('nesting-bed-height-z')?.value) || 250;
const spacing = parseFloat(document.getElementById('nesting-spacing')?.value) || 3;
const paths = [...selectedFiles];

const wrap = document.getElementById('nesting-preview-wrap');
wrap.style.display = 'block';
const bedEl = document.getElementById('nesting-bed-preview');
bedEl.innerHTML = `<div style="padding:30px; text-align:center; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> ${_t3('modal.nesting_loading', 'Calcul du meilleur arrangement...')}</div>`;
document.getElementById('nesting-send-to-slicer-btn').style.display = 'none';

try {
const res = await fetch(`${API}/api/nesting/arrange`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paths, bed_width: bedW, bed_height: bedH, bed_height_z: bedZ, spacing })
});
let data = null;
try { data = await res.json(); } catch (e) {  }
if (!res.ok) {
    bedEl.innerHTML = `<div style="padding:20px; color:var(--danger);">${escapeHtml((data && data.error) || `Erreur serveur (HTTP ${res.status})`)}</div>`;
    return;
}
_lastNestingResult = data;
renderNestingPreview(data, bedW, bedH);
document.getElementById('nesting-send-to-slicer-btn').style.display = (data.placed || []).length ? 'inline-flex' : 'none';
} catch (err) {
bedEl.innerHTML = `<div style="padding:20px; color:var(--danger);">${_t3('toast.connection_error', 'Erreur de connexion')}</div>`;
console.warn('[Nesting] Erreur', err);
}
}

function renderNestingPreview(data, bedW, bedH) {
const bedEl = document.getElementById('nesting-bed-preview');
const maxPreviewWidth = 460;
const scale = Math.min(maxPreviewWidth / bedW, 340 / bedH);
bedEl.style.width = `${Math.round(bedW * scale)}px`;
bedEl.style.height = `${Math.round(bedH * scale)}px`;

const colors = ['#4f8cff', '#38c172', '#f5a623', '#e85d75', '#9b6bff', '#20c9c9', '#ff8c42'];
const placed = data.placed || [];
bedEl.innerHTML = placed.map((p, i) => `
    <div title="${escapeHtml(p.filename)}" style="position:absolute; left:${Math.round(p.x * scale)}px; top:${Math.round((bedH - p.y - p.h) * scale)}px; width:${Math.max(Math.round(p.w * scale), 4)}px; height:${Math.max(Math.round(p.h * scale), 4)}px; background:${colors[i % colors.length]}55; border:1.5px solid ${colors[i % colors.length]}; border-radius:3px; display:flex; align-items:center; justify-content:center; overflow:hidden;">
        <span style="font-size:9px; color:var(--text-primary); padding:2px; text-align:center; line-height:1.1; word-break:break-word;">${escapeHtml(p.filename.length > 14 ? p.filename.slice(0, 12) + '…' : p.filename)}</span>
    </div>
`).join('');

const unplaced = data.unplaced || [];
const errors = data.errors || [];
const warnEl = document.getElementById('nesting-unplaced-warning');
const warnLines = [];
if (unplaced.length) {
    warnLines.push(`<i class="fa-solid fa-triangle-exclamation"></i> ${_t3('modal.nesting_unplaced', 'Ne rentrent pas sur ce plateau :')} ${unplaced.map(u => escapeHtml(u.filename)).join(', ')}`);
}
if (errors.length) {
    errors.forEach(e => {
        const name = e.path ? escapeHtml(e.path.split(/[\\/]/).pop()) : '';
        warnLines.push(`<i class="fa-solid fa-circle-exclamation"></i> ${name} — ${escapeHtml(e.error)}`);
    });
}
if (warnLines.length) {
    warnEl.style.display = 'block';
    warnEl.innerHTML = warnLines.join('<br>');
} else {
    warnEl.style.display = 'none';
}
}

async function requestBatchProfileRecommendation() {
if (!_lastNestingResult || !(_lastNestingResult.piece_stats || []).length) return;
if (!window.aiEnabled) {
    showToast(_t3('toast.ai_disabled_warning', "L'assistant IA est désactivé dans Paramètres."), 'warning');
    return;
}
const btn = document.getElementById('nesting-ai-recommend-btn');
const box = document.getElementById('nesting-ai-recommend-result');
if (!box) return;
box.style.display = 'block';
box.innerHTML = `<div style="color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> ${_t3('modal.ai_recommend_loading', 'Analyse de la pièce et de vos profils...')}</div>`;
if (btn) btn.disabled = true;
try {
const res = await fetch(`${API}/api/ollama/recommend-profile-batch`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        pieces: _lastNestingResult.piece_stats,
        printer_id: document.getElementById('nesting-ai-printer-select')?.value || null,
        material_type: document.getElementById('nesting-ai-material-select')?.value || null
    })
});
let data = null;
try { data = await res.json(); } catch (e) {  }
if (!res.ok) {
    if (data && data.no_profiles) {
        box.innerHTML = `<div style="color:var(--text-muted);"><i class="fa-solid fa-circle-info"></i> ${_t3('modal.ai_recommend_no_profiles', "Aucun profil importé. Ajoute tes profils dans Paramètres → Slicer pour activer l'assistant.")}</div>`;
    } else {
        box.innerHTML = `<div style="color:var(--danger);">${escapeHtml((data && data.error) || `Erreur serveur (HTTP ${res.status})`)}</div>`;
    }
    return;
}
renderProfileRecommendation(box, data);
} catch (err) {
box.innerHTML = `<div style="color:var(--danger);">${_t3('toast.connection_error', 'Erreur de connexion')}</div>`;
} finally {
if (btn) btn.disabled = false;
}
}

function sendNestedPlateToSlicer() {
if (!_lastNestingResult || !_lastNestingResult.output_path) return;
const aiProfile = _lastAiRecommendedProfile;
closeModal('modal-nesting');
sendToSlicer(_lastNestingResult.output_path, _lastNestingResult.output_filename || 'plateau_nesté.3mf', aiProfile);
}

function _hexToRgb(hex) {
const m = hex.replace('#', '').match(/.{1,2}/g);
return m ? m.map(x => parseInt(x, 16)) : [78, 161, 211];
}
function _shadeColor(hex, percent) {
const [r, g, b] = _hexToRgb(hex);
const clamp = v => Math.max(0, Math.min(255, Math.round(v)));
const factor = percent / 100;
const shade = (c) => factor > 0 ? c + (255 - c) * factor : c * (1 + factor);
return `#${[r, g, b].map(c => clamp(shade(c)).toString(16).padStart(2, '0')).join('')}`;
}
function applyCustomAccent(hex) {
if (!hex) return;
const [r, g, b] = _hexToRgb(hex);
document.documentElement.style.setProperty('--accent', hex);
document.documentElement.style.setProperty('--accent-hover', _shadeColor(hex, -15));
document.documentElement.style.setProperty('--accent-glow', `rgba(${r}, ${g}, ${b}, 0.25)`);
}
function clearCustomAccent() {
document.documentElement.style.removeProperty('--accent');
document.documentElement.style.removeProperty('--accent-hover');
document.documentElement.style.removeProperty('--accent-glow');
}

function applyTheme(mode) {
if (mode === 'auto') {
const isLight = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches;
document.documentElement.setAttribute('data-theme', isLight ? 'light' : 'dark');
} else {
document.documentElement.setAttribute('data-theme', mode);
}
}
function applyFabricant(fabricant) {
document.documentElement.setAttribute('data-fabricant', fabricant);
}
async function initSettings() {
const themeSelector = document.getElementById('theme-selector');
const fabricantSelector = document.getElementById('fabricant-selector');
if (!themeSelector || !fabricantSelector) {
console.warn('[Theme] ⚠️ Sélecteurs introuvables');
return;
}
let savedTheme = 'dark', savedFabricant = 'stellio';
try {
const res = await fetch(`${API}/api/settings`);
if (res.ok) {
const data = await res.json();
savedTheme = data.theme || savedTheme;
savedFabricant = data.fabricant || savedFabricant;
}
} catch (e) { console.warn('[Theme] Backend indisponible'); }
if (!savedTheme || savedTheme === 'undefined') savedTheme = localStorage.getItem('stellio-theme') || 'dark';
if (!savedFabricant || savedFabricant === 'undefined') savedFabricant = localStorage.getItem('stellio-fabricant') || 'stellio';
themeSelector.value = savedTheme;
fabricantSelector.value = savedFabricant;
applyTheme(savedTheme);
applyFabricant(savedFabricant);

let savedCustomAccent = null;
try {
const res2 = await fetch(`${API}/api/settings`);
if (res2.ok) savedCustomAccent = (await res2.json()).custom_accent || null;
} catch (e) {  }
if (!savedCustomAccent || savedCustomAccent === 'undefined') savedCustomAccent = localStorage.getItem('stellio-custom-accent') || null;
const accentPicker = document.getElementById('custom-accent-picker');
if (savedCustomAccent) {
if (accentPicker) accentPicker.value = savedCustomAccent;
applyCustomAccent(savedCustomAccent);
}
accentPicker?.addEventListener('input', async (e) => {
const hex = e.target.value;
applyCustomAccent(hex);
localStorage.setItem('stellio-custom-accent', hex);
try {
    await fetch(`${API}/api/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ custom_accent: hex }) });
} catch (err) { console.warn('[Theme] Échec sauvegarde couleur:', err); }
});
document.getElementById('custom-accent-reset-btn')?.addEventListener('click', async () => {
clearCustomAccent();
localStorage.removeItem('stellio-custom-accent');
if (accentPicker) accentPicker.value = '#4ea1d3';
try {
    await fetch(`${API}/api/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ custom_accent: null }) });
} catch (err) { console.warn('[Theme] Échec réinitialisation couleur:', err); }
showToast(I18N.t('toast.custom_accent_reset') || 'Couleur réinitialisée', 'info');
});
themeSelector.addEventListener('change', async (e) => {
const mode = e.target.value;
localStorage.setItem('stellio-theme', mode);
try {
await fetch(`${API}/api/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ theme: mode }) });
} catch (err) { console.warn('[Theme] Échec sauvegarde:', err); }
applyTheme(mode);
});
fabricantSelector.addEventListener('change', async (e) => {
const fabricant = e.target.value;
localStorage.setItem('stellio-fabricant', fabricant);
clearCustomAccent();
localStorage.removeItem('stellio-custom-accent');
if (accentPicker) accentPicker.value = '#4ea1d3';
try {
await fetch(`${API}/api/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fabricant, custom_accent: null }) });
} catch (err) { console.warn('[Theme] Échec sauvegarde:', err); }
applyFabricant(fabricant);
});
if (window.matchMedia) {
window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', e => {
if (localStorage.getItem('stellio-theme') === 'auto') {
applyTheme('auto');
console.log('[Theme] 🔄 Système:', e.matches ? I18N.t('settings.theme_light') : I18N.t('settings.theme_dark'));
}
});
}
loadSlicerSettings();
loadSpoolmanSettings();
loadOllamaSettings();
loadAutoScanSettings();
loadStartupSettings();
loadPrintCostSettings();
loadAccountBadges();
loadNavOrder();
}


function toggleAccord(headerEl) {
    const section = headerEl.closest('.accord-section');
    if (!section) return;
    const isOpening = !section.classList.contains('open');

    if (isOpening) {
        // .settings-grid (Paramètres) est scindée en 2 colonnes fixes pour éviter que les
        // sections ne changent de côté visuellement à l'ouverture — mais on garde le
        // comportement "une seule section ouverte à la fois" sur toute la page, pas juste
        // dans la colonne courante.
        const grid = headerEl.closest('.settings-grid');
        const scope = grid || section.parentElement;
        scope.querySelectorAll('.accord-section.open').forEach(other => {
            if (other === section) return;
            if (other.contains(section) || section.contains(other)) return; // accordéons imbriqués : ne pas toucher ancêtres/descendants
            other.classList.remove('open');
        });
    }

    section.classList.toggle('open');
}
window.toggleAccord = toggleAccord;


function normalizeSpoolmanUrl(raw) {
let url = (raw || '').trim();
if (!url) return '';
if (!/^https?:\/\//i.test(url)) url = `http://${url}`;
try {
const u = new URL(url);
if (!u.port) u.port = '7912';
return u.origin;
} catch (e) {
return url.replace(/\/$/, '');
}
}
async function saveSpoolmanUrl() {
const input = document.getElementById('spoolman-url-input');
if (!input) return;
const url = normalizeSpoolmanUrl(input.value);
if (!url) { showToast(I18N.t('toast.enter_address'), 'error'); return; }
try {
const res = await fetch(`${API}/api/settings`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ spoolman_url: url })
});
if (res.ok) {
localStorage.setItem('stellio-spoolman-url', url);
input.value = url;
showToast(I18N.t('toast.spoolman_url_saved'), 'success');
} else {
const data = await res.json().catch(() => ({}));
showToast(data.error || I18N.t('toast.save_error'), 'error');
}
} catch (err) {
console.error('[saveSpoolmanUrl]', err);
showToast(I18N.t('toast.network_error_backend'), 'error');
}
}
window.saveSpoolmanUrl = saveSpoolmanUrl;
async function loadSpoolmanSettings() {
const input = document.getElementById('spoolman-url-input');
if (!input) return;
try {
const res = await fetch(`${API}/api/settings`);
if (res.ok) {
const data = await res.json();
if (data.spoolman_url) input.value = data.spoolman_url;
}
} catch (e) { console.warn('[Spoolman] Réglages indisponibles'); }
}
async function deleteSpoolmanUrl() {
    try {
        const res = await fetch(`${API}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ spoolman_url: '' })
        });
        if (res.ok) {
            const input = document.getElementById('spoolman-url-input');
            if (input) input.value = '';
            localStorage.removeItem('stellio-spoolman-url');
            showToast(I18N.t('toast.spoolman_url_deleted') || 'URL Spoolman supprimée', 'success');
            if (typeof loadSpoolmanPage === 'function') loadSpoolmanPage();
        } else {
            const data = await res.json().catch(() => ({}));
            showToast(data.error || I18N.t('toast.save_error'), 'error');
        }
    } catch (err) {
        console.error('[deleteSpoolmanUrl]', err);
        showToast(I18N.t('toast.network_error_backend'), 'error');
    }
}
window.deleteSpoolmanUrl = deleteSpoolmanUrl;


async function loadOllamaSettings() {
    try {
        const res = await fetch(`${API}/api/settings`);
        if (!res.ok) return;
        const data = await res.json();
        const urlInput = document.getElementById('ollama-url-input');
        if (urlInput && data.ollama_url) urlInput.value = data.ollama_url;
        if (data.ollama_model) {
            const sel = document.getElementById('ollama-model-select');
            if (sel) {
                if (![...sel.options].some(o => o.value === data.ollama_model)) {
                    const opt = document.createElement('option');
                    opt.value = data.ollama_model;
                    opt.textContent = data.ollama_model;
                    sel.appendChild(opt);
                }
                sel.value = data.ollama_model;
            }
        }
        const aiToggle = document.getElementById('ai-enabled-toggle');
        const aiEnabled = data.ai_enabled === true;
        if (aiToggle) aiToggle.checked = aiEnabled;
        applyAiEnabledUI(aiEnabled);
    } catch (e) { console.warn('[Ollama] Réglages indisponibles'); }
}

window.aiEnabled = false;

function applyAiEnabledUI(enabled) {
    window.aiEnabled = enabled;

    const configBlock = document.getElementById('ollama-config-block');
    if (configBlock) {
        configBlock.style.opacity = enabled ? '1' : '0.45';
        configBlock.style.pointerEvents = enabled ? 'auto' : 'none';
    }

    if (!enabled && typeof setSearchMode === 'function') {
        setSearchMode('normal');
    }

    const searchAiDisabledHint = document.getElementById('search-ai-disabled-hint');
    if (searchAiDisabledHint) searchAiDisabledHint.style.display = enabled ? 'none' : 'flex';

    const mobileSearchAiDisabledHint = document.getElementById('mobile-search-ai-disabled-hint');
    if (mobileSearchAiDisabledHint) mobileSearchAiDisabledHint.style.display = enabled ? 'none' : 'flex';

    applySosprintAiState(enabled);
    applyProfileRecommendAiState(enabled);
    applyOrientationSuggestAiState(enabled);
}

function applyOrientationSuggestAiState(enabled) {
    const btn = document.getElementById('viewer-orientation-suggest-btn');
    if (btn) btn.style.display = enabled ? '' : 'none';
    if (!enabled) {
        const panel = document.getElementById('viewer-orientation-suggestions');
        if (panel) { panel.style.display = 'none'; panel.innerHTML = ''; }
    }
}

function applyProfileRecommendAiState(enabled) {
    const slicerBtn = document.getElementById('slicer-ai-recommend-btn');
    const slicerHint = document.getElementById('slicer-ai-disabled-hint');
    if (slicerBtn) { slicerBtn.disabled = !enabled; slicerBtn.style.opacity = enabled ? '1' : '0.5'; }
    if (slicerHint) slicerHint.style.display = enabled ? 'none' : 'block';

    const nestingBtn = document.getElementById('nesting-ai-recommend-btn');
    const nestingHint = document.getElementById('nesting-ai-disabled-hint');
    if (nestingBtn) { nestingBtn.disabled = !enabled; nestingBtn.style.opacity = enabled ? '1' : '0.5'; }
    if (nestingHint) nestingHint.style.display = enabled ? 'none' : 'block';
}

function applySosprintAiState(enabled) {
    const banner    = document.getElementById('sosprint-ai-disabled-banner');
    const form      = document.getElementById('sosprint-form');
    const submitBtn = document.getElementById('sosprint-submit-btn');

    if (banner) banner.style.display = enabled ? 'none' : 'flex';
    if (form) form.style.opacity = enabled ? '1' : '0.5';
    if (submitBtn) {
        submitBtn.disabled = !enabled;
        submitBtn.style.cursor = enabled ? '' : 'not-allowed';
    }
}

async function toggleAiEnabled(enabled) {
    applyAiEnabledUI(enabled);
    try {
        const res = await fetch(`${API}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ai_enabled: enabled })
        });
        if (res.ok) {
            showToast(enabled ? I18N.t('toast.ai_enabled') : I18N.t('toast.ai_disabled'), 'success');
        } else {
            showToast(I18N.t('toast.save_error'), 'error');
        }
    } catch (_) {
        showToast(I18N.t('toast.network_error'), 'error');
    }
}
window.toggleAiEnabled = toggleAiEnabled;

function applyAutoScanUI(enabled) {
    const intervalBlock = document.getElementById('auto-scan-interval-block');
    if (intervalBlock) {
        intervalBlock.style.opacity = enabled ? '1' : '0.45';
        intervalBlock.style.pointerEvents = enabled ? 'auto' : 'none';
    }
}

async function toggleAutoScanEnabled(enabled) {
    applyAutoScanUI(enabled);
    try {
        const res = await fetch(`${API}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ auto_scan_enabled: enabled })
        });
        if (res.ok) {
            showToast(enabled ? I18N.t('toast.auto_scan_enabled') : I18N.t('toast.auto_scan_disabled'), 'success');
        } else {
            showToast(I18N.t('toast.save_error'), 'error');
        }
    } catch (_) {
        showToast(I18N.t('toast.network_error'), 'error');
    }
}
window.toggleAutoScanEnabled = toggleAutoScanEnabled;

async function saveAutoScanInterval(value) {
    let minutes = parseInt(value, 10);
    if (!Number.isFinite(minutes) || minutes < 1) minutes = 1;
    if (minutes > 180) minutes = 180;
    const input = document.getElementById('auto-scan-interval-input');
    if (input) input.value = minutes;
    try {
        const res = await fetch(`${API}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ auto_scan_interval_minutes: minutes })
        });
        if (res.ok) {
            showToast(I18N.t('toast.settings_saved'), 'success');
        } else {
            showToast(I18N.t('toast.save_error'), 'error');
        }
    } catch (_) {
        showToast(I18N.t('toast.network_error'), 'error');
    }
}
window.saveAutoScanInterval = saveAutoScanInterval;

async function loadAutoScanSettings() {
    try {
        const res = await fetch(`${API}/api/settings`);
        if (!res.ok) return;
        const data = await res.json();
        const toggle = document.getElementById('auto-scan-enabled-toggle');
        const enabled = data.auto_scan_enabled !== false;
        if (toggle) toggle.checked = enabled;
        applyAutoScanUI(enabled);
        const input = document.getElementById('auto-scan-interval-input');
        if (input) input.value = data.auto_scan_interval_minutes || 5;
    } catch (e) { console.warn('[AutoScan] Réglages indisponibles'); }
}

function applyLaunchAtStartupUI(enabled, supported) {
    const block = document.getElementById('launch-minimized-block');
    if (block) {
        const active = enabled && supported;
        block.style.opacity = active ? '1' : '0.45';
        block.style.pointerEvents = active ? 'auto' : 'none';
    }
}

async function toggleLaunchAtStartup(enabled) {
    const supported = document.getElementById('launch-at-startup-toggle')?.disabled !== true;
    applyLaunchAtStartupUI(enabled, supported);
    try {
        const res = await fetch(`${API}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ launch_at_startup: enabled })
        });
        if (res.ok) {
            showToast(enabled ? I18N.t('toast.launch_at_startup_enabled') : I18N.t('toast.launch_at_startup_disabled'), 'success');
        } else {
            const toggle = document.getElementById('launch-at-startup-toggle');
            if (toggle) toggle.checked = !enabled;
            applyLaunchAtStartupUI(!enabled, supported);
            showToast(I18N.t('toast.save_error'), 'error');
        }
    } catch (_) {
        const toggle = document.getElementById('launch-at-startup-toggle');
        if (toggle) toggle.checked = !enabled;
        applyLaunchAtStartupUI(!enabled, supported);
        showToast(I18N.t('toast.network_error'), 'error');
    }
}
window.toggleLaunchAtStartup = toggleLaunchAtStartup;

async function toggleLaunchMinimized(enabled) {
    try {
        const res = await fetch(`${API}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ launch_minimized: enabled })
        });
        if (res.ok) {
            showToast(I18N.t('toast.settings_saved'), 'success');
        } else {
            const toggle = document.getElementById('launch-minimized-toggle');
            if (toggle) toggle.checked = !enabled;
            showToast(I18N.t('toast.save_error'), 'error');
        }
    } catch (_) {
        const toggle = document.getElementById('launch-minimized-toggle');
        if (toggle) toggle.checked = !enabled;
        showToast(I18N.t('toast.network_error'), 'error');
    }
}
window.toggleLaunchMinimized = toggleLaunchMinimized;

async function loadStartupSettings() {
    try {
        const res = await fetch(`${API}/api/settings`);
        if (!res.ok) return;
        const data = await res.json();
        const toggle = document.getElementById('launch-at-startup-toggle');
        const minimizedToggle = document.getElementById('launch-minimized-toggle');
        const unsupportedHint = document.getElementById('startup-unsupported-hint');
        const supported = data.launch_at_startup_supported === true;
        const enabled = data.launch_at_startup === true;
        if (toggle) {
            toggle.checked = enabled;
            toggle.disabled = !supported;
        }
        if (minimizedToggle) {
            minimizedToggle.checked = data.launch_minimized === true;
            minimizedToggle.disabled = !supported;
        }
        applyLaunchAtStartupUI(enabled, supported);
        if (unsupportedHint) unsupportedHint.style.display = supported ? 'none' : 'block';
    } catch (e) { console.warn('[Startup] Réglages indisponibles'); }
}


let printCostSpools = [];
let printCostDefaultSpoolId = null;
let printCostCurrency = 'EUR';

function formatCost(value) {
    const amount = Number(value) || 0;
    return printCostCurrency === 'USD' ? `$${amount.toFixed(2)}` : `${amount.toFixed(2)} €`;
}
window.formatCost = formatCost;

function applyCurrencySymbols() {
    const symbol = printCostCurrency === 'USD' ? '$' : '€';
    document.querySelectorAll('.currency-symbol').forEach(el => { el.textContent = symbol; });
}
window.applyCurrencySymbols = applyCurrencySymbols;

function _genSpoolId() {
    return (crypto.randomUUID ? crypto.randomUUID() : 'spool_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8));
}

function renderSpoolsList() {
    const container = document.getElementById('settings-spools-list');
    const countBadge = document.getElementById('settings-spools-count');
    if (countBadge) countBadge.textContent = printCostSpools.length;
    if (!container) return;
    if (printCostSpools.length === 0) {
        container.innerHTML = `<p class="settings-hint" style="margin:0;">${I18N.t('cost.spools_empty') || 'Aucune bobine — ajoute-en une.'}</p>`;
        return;
    }
    container.innerHTML = printCostSpools.map(s => {
        const isDefault = s.id === printCostDefaultSpoolId;
        return `
        <div class="settings-spool-row" data-spool-id="${s.id}" style="display:flex; align-items:center; gap:8px;">
            <button type="button" class="btn btn-ghost btn-sm" style="padding:4px 8px; color:${isDefault ? 'var(--accent)' : 'var(--text-muted)'};" onclick="setDefaultSpool('${s.id}')" title="${I18N.t('cost.spool_default_title') || 'Bobine par défaut'}">
                <i class="fa-${isDefault ? 'solid' : 'regular'} fa-star"></i>
            </button>
            <input type="color" value="${escapeHtml(s.color || '#888888')}" title="${I18N.t('cost.spool_color_title') || 'Couleur de la bobine'}"
                oninput="updateSpoolField('${s.id}', 'color', this.value)">
            <input type="text" value="${escapeHtml(s.name || '')}" placeholder="${I18N.t('cost.spool_name_placeholder') || 'Nom (ex : PLA blanc)'}"
                oninput="updateSpoolField('${s.id}', 'name', this.value)"
                style="flex:1; min-width:0; padding:8px 10px; background:var(--bg-input); border:1px solid var(--border); border-radius:var(--radius); color:var(--text-primary); font-size:13px;">
            <input type="number" min="0" step="0.01" value="${s.price ?? ''}" placeholder="${I18N.t('cost.spool_price_placeholder') || 'Prix'} (${printCostCurrency === 'USD' ? '$' : '€'})"
                oninput="updateSpoolField('${s.id}', 'price', this.value)"
                style="width:90px; padding:8px 10px; background:var(--bg-input); border:1px solid var(--border); border-radius:var(--radius); color:var(--text-primary); font-size:13px;">
            <input type="number" min="1" step="1" value="${s.weight ?? ''}" placeholder="${I18N.t('cost.spool_weight_placeholder') || 'Poids (g)'}"
                oninput="updateSpoolField('${s.id}', 'weight', this.value)"
                style="width:90px; padding:8px 10px; background:var(--bg-input); border:1px solid var(--border); border-radius:var(--radius); color:var(--text-primary); font-size:13px;">
            <button type="button" class="btn btn-ghost btn-sm" style="color:var(--danger);" onclick="removeSpoolRow('${s.id}')" title="${I18N.t('actions.delete') || 'Supprimer'}">
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>`;
    }).join('');
}

function addSpoolRow() {
    const id = _genSpoolId();
    const spoolNumber = printCostSpools.length + 1;
    printCostSpools.push({ id, name: `${I18N.t('cost.spool_default_name') || 'Bobine'} ${spoolNumber}`, price: 20, weight: 1000, color: '#888888' });
    if (!printCostDefaultSpoolId) printCostDefaultSpoolId = id;
    renderSpoolsList();
}

function removeSpoolRow(id) {
    printCostSpools = printCostSpools.filter(s => s.id !== id);
    if (printCostDefaultSpoolId === id) printCostDefaultSpoolId = printCostSpools[0]?.id || null;
    renderSpoolsList();
}

function setDefaultSpool(id) {
    printCostDefaultSpoolId = id;
    renderSpoolsList();
}

function updateSpoolField(id, field, value) {
    const spool = printCostSpools.find(s => s.id === id);
    if (!spool) return;
    spool[field] = (field === 'name' || field === 'color') ? value : parseFloat(value);
}
window.addSpoolRow = addSpoolRow;
window.removeSpoolRow = removeSpoolRow;
window.setDefaultSpool = setDefaultSpool;
window.updateSpoolField = updateSpoolField;

function onSettingsPrinterPowerSelectChange() {
    const sel = document.getElementById('settings-printer-power-select');
    const powerInput = document.getElementById('settings-printer-power');
    if (!sel || !powerInput) return;
    if (!sel.value) return;
    const printer = (printersList || []).find(p => String(p.id) === sel.value);
    if (printer) powerInput.value = printer.power_w ?? 120;
}
window.onSettingsPrinterPowerSelectChange = onSettingsPrinterPowerSelectChange;

async function loadPrintCostSettings() {
    try {
        const res = await fetch(`${API}/api/settings`);
        if (!res.ok) return;
        const data = await res.json();

        if (Array.isArray(data.print_cost_spools) && data.print_cost_spools.length > 0) {
            printCostSpools = data.print_cost_spools.map(s => ({
                id: s.id || _genSpoolId(),
                name: s.name || (I18N.t('cost.spool_default_name') || 'Bobine'),
                price: Number(s.price) || 0,
                weight: Number(s.weight) || 0,
                color: s.color || '#888888',
            }));
        } else if (data.print_cost_spool_price != null || data.print_cost_spool_weight != null) {

            printCostSpools = [{
                id: _genSpoolId(),
                name: I18N.t('cost.spool_default_name') || 'Bobine 1',
                price: data.print_cost_spool_price ?? 20,
                weight: data.print_cost_spool_weight ?? 1000,
                color: '#888888',
            }];
        } else {

            printCostSpools = [];
        }
        printCostDefaultSpoolId = (data.print_cost_default_spool_id && printCostSpools.some(s => s.id === data.print_cost_default_spool_id))
            ? data.print_cost_default_spool_id
            : (printCostSpools[0]?.id || null);
        renderSpoolsList();

        printCostCurrency = data.print_cost_currency === 'USD' ? 'USD' : 'EUR';
        const currencySelect = document.getElementById('settings-currency-select');
        if (currencySelect) currencySelect.value = printCostCurrency;
        applyCurrencySymbols();

        const elecPrice = document.getElementById('settings-elec-price');
        const printerPower = document.getElementById('settings-printer-power');
        if (elecPrice) elecPrice.value = data.print_cost_elec_price ?? '';
        if (printerPower) printerPower.value = data.print_cost_printer_power ?? 120;

        const printerSel = document.getElementById('settings-printer-power-select');
        if (printerSel) {
            _populatePrinterSelects();
            printerSel.value = (data.print_cost_printer_id != null && [...printerSel.options].some(o => o.value == data.print_cost_printer_id))
                ? String(data.print_cost_printer_id)
                : '';
        }
    } catch (e) { console.warn('[PrintCost] Réglages indisponibles'); }
}

async function savePrintCostSettings() {
    const elecPriceRaw = document.getElementById('settings-elec-price')?.value;
    const printerPower = parseFloat(document.getElementById('settings-printer-power')?.value);
    const printerSel = document.getElementById('settings-printer-power-select');
    const selectedPrinterId = printerSel && printerSel.value ? printerSel.value : null;

    const cleanSpools = printCostSpools
        .map(s => ({ id: s.id, name: (s.name || '').trim() || (I18N.t('cost.spool_default_name') || 'Bobine'), price: Number(s.price) || 0, weight: Number(s.weight) || 0, color: s.color || '#888888' }))
        .filter(s => s.price > 0 && s.weight > 0);

    if (printCostSpools.length > 0 && cleanSpools.length === 0) {
        showToast(I18N.t('cost.spools_invalid') || 'Renseigne au moins une bobine valide (prix et poids > 0)', 'error');
        return;
    }

    const defaultId = cleanSpools.some(s => s.id === printCostDefaultSpoolId) ? printCostDefaultSpoolId : (cleanSpools[0]?.id || null);

    const currencySelect = document.getElementById('settings-currency-select');
    const currency = currencySelect && currencySelect.value === 'USD' ? 'USD' : 'EUR';

    const payload = {
        print_cost_spools: cleanSpools,
        print_cost_default_spool_id: defaultId,
        print_cost_currency: currency,
        print_cost_elec_price: (elecPriceRaw === '' || elecPriceRaw == null) ? '' : parseFloat(elecPriceRaw),
        print_cost_printer_id: selectedPrinterId,
    };
    if (Number.isFinite(printerPower)) payload.print_cost_printer_power = printerPower;

    try {
        if (selectedPrinterId && Number.isFinite(printerPower)) {
            await fetch(`${API}/api/printers/${selectedPrinterId}/power`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ power_w: printerPower })
            }).catch(() => {});
        }

        const res = await fetch(`${API}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast(I18N.t('toast.settings_saved') || 'Réglages enregistrés', 'success');
            printCostSpools = cleanSpools;
            printCostDefaultSpoolId = defaultId;
            printCostCurrency = currency;
            renderSpoolsList();
            applyCurrencySymbols();
            if (selectedPrinterId) loadPrinters();
        } else {
            showToast(I18N.t('toast.save_error') || 'Erreur', 'error');
        }
    } catch (_) {
        showToast(I18N.t('toast.network_error') || 'Erreur de connexion', 'error');
    }
}
window.savePrintCostSettings = savePrintCostSettings;

function toggleOllamaGuide(forceOpen) {
    const guide = document.getElementById('ollama-guide');
    if (!guide) return;
    const shouldOpen = typeof forceOpen === 'boolean' ? forceOpen : !guide.classList.contains('open');
    guide.classList.toggle('open', shouldOpen);
}

function copyOllamaCmd(btn, text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast(I18N.t('toast.copied'), 'success');
        const icon = btn.querySelector('i');
        if (icon) {
            icon.className = 'fa-solid fa-check';
            setTimeout(() => { icon.className = 'fa-regular fa-copy'; }, 1500);
        }
    }).catch(() => showToast(I18N.t('toast.error'), 'error'));
}

function copyOllamaGuideCmd(btn) {
    const code = document.getElementById('ollama-guide-pull-cmd');
    if (!code) return;
    copyOllamaCmd(btn, code.textContent.trim());
}

function ollamaErrorMessage(data, res) {
    const codeMap = {
        ollama_unreachable: 'settings.ollama_err_unreachable',
        ollama_timeout: 'settings.ollama_err_timeout',
        internal_error: 'settings.ollama_err_internal',
    };
    if (data && data.error_code && codeMap[data.error_code]) {
        return I18N.t(codeMap[data.error_code], data.error_params || {});
    }
    return I18N.t('settings.ollama_err_generic', { status: res.status });
}

async function testOllamaConnection() {
    const urlInput = document.getElementById('ollama-url-input');
    const statusEl = document.getElementById('ollama-status');
    const modelSel = document.getElementById('ollama-model-select');

    const url = (urlInput?.value || '').trim() || 'http://localhost:11434';
    try {
        await fetch(`${API}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ollama_url: url })
        });
    } catch (_) {}

    if (statusEl) {
        statusEl.style.display = 'block';
        statusEl.style.background = 'var(--bg-input)';
        statusEl.style.color = 'var(--text-secondary)';
        statusEl.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${I18N.t('settings.ollama_connecting')}`;
    }

    try {
        const res = await fetch(`${API}/api/ollama/models`);
        const data = await res.json();
        if (!res.ok) throw new Error(ollamaErrorMessage(data, res));

        const models = data.models || [];
        if (modelSel) {
            modelSel.innerHTML = models.length
                ? models.map(m => `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`).join('')
                : `<option value="">${I18N.t('settings.ollama_no_models')}</option>`;
        }

        if (statusEl) {
            statusEl.style.background = '#16a34a20';
            statusEl.style.color = '#16a34a';
            statusEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${I18N.t('settings.ollama_connected', { count: models.length })}`;
        }
        showToast(I18N.t('settings.ollama_connected', { count: models.length }), 'success');
    } catch (err) {
        if (statusEl) {
            statusEl.style.background = 'var(--danger)20';
            statusEl.style.color = 'var(--danger)';
            statusEl.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> ${escapeHtml(err.message)}`;
        }
        showToast(I18N.t('settings.ollama_unreachable'), 'error');
        toggleOllamaGuide(true);
    }
}

async function recommendOllamaModel() {
    const btn = document.getElementById('ollama-recommend-btn');
    const resultEl = document.getElementById('ollama-recommend-result');
    if (!resultEl) return;

    const originalBtnHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${I18N.t('settings.ollama_recommend_analyzing')}`;
    resultEl.style.display = 'block';
    resultEl.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${I18N.t('settings.ollama_recommend_analyzing')}`;

    try {
        const res = await fetch(`${API}/api/ollama/recommend-model`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);

        const hw = data.hardware || {};
        const rec = data.recommendation || {};

        // La commande d'installation affichée dans le guide (étape 2) doit toujours pointer
        // vers le modèle réellement recommandé, pas un "llama3" générique par défaut.
        const guideCmdEl = document.getElementById('ollama-guide-pull-cmd');
        if (guideCmdEl) {
            guideCmdEl.textContent = rec.pull_command || (rec.model ? `ollama pull ${rec.model}` : guideCmdEl.textContent);
        }

        const hwParts = [];
        hwParts.push(`<i class="fa-solid fa-microchip"></i> ${I18N.t('settings.ollama_hw_cores', { count: hw.cpu_cores || '?' })}`);
        hwParts.push(hw.ram_gb != null
            ? `<i class="fa-solid fa-memory"></i> ${I18N.t('settings.ollama_hw_ram', { value: hw.ram_gb })}`
            : `<i class="fa-solid fa-memory"></i> ${I18N.t('settings.ollama_hw_unknown')}`);
        hwParts.push(hw.gpu_name
            ? `<i class="fa-solid fa-display"></i> ${escapeHtml(hw.gpu_name)} (${I18N.t('settings.ollama_hw_vram', { value: hw.vram_gb })})`
            : `<i class="fa-solid fa-display"></i> ${I18N.t('settings.ollama_hw_no_gpu')}`);

        const visionNote = rec.vision
            ? `<div style="margin-top:6px; color:var(--text-secondary);"><i class="fa-solid fa-camera"></i> ${I18N.t('settings.ollama_rec_vision_note')}</div>`
            : '';
        const installedNote = rec.already_installed
            ? `<div style="margin-top:8px; color:#16a34a;"><i class="fa-solid fa-circle-check"></i> ${I18N.t('settings.ollama_rec_already_installed')}</div>`
            : `<div style="margin-top:10px; padding-top:10px; border-top:1px solid var(--border);">
                 <div style="color:var(--text-secondary); margin-bottom:6px;">${I18N.t('settings.ollama_rec_install_hint')}</div>
                 <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                   <code style="background:var(--bg-secondary); padding:4px 8px; border-radius:6px; font-size:11px;">${escapeHtml(rec.pull_command)}</code>
                   <button type="button" class="btn btn-ghost btn-sm" onclick="navigator.clipboard.writeText('${escapeJs(rec.pull_command)}').then(() => showToast(I18N.t('toast.copied'), 'success'))"><i class="fa-solid fa-copy"></i> ${I18N.t('actions.copy')}</button>
                 </div>
                 <p class="settings-hint" style="margin-top:6px;">${I18N.t('settings.ollama_rec_install_next')}</p>
               </div>`;

        resultEl.innerHTML = `
            <div style="display:flex; gap:14px; flex-wrap:wrap; color:var(--text-secondary); margin-bottom:10px;">
                ${hwParts.map(p => `<span>${p}</span>`).join('')}
            </div>
            <div style="font-size:14px; font-weight:600; color:var(--accent);">
                <i class="fa-solid fa-star"></i> ${escapeHtml(rec.model)}
            </div>
            <div style="margin-top:4px; color:var(--text-secondary);">${I18N.t(rec.label_key) || ''}</div>
            ${visionNote}
            ${installedNote}
        `;
    } catch (err) {
        resultEl.innerHTML = `<span style="color:var(--danger);"><i class="fa-solid fa-circle-xmark"></i> ${escapeHtml(err.message)}</span>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalBtnHtml;
    }
}

async function saveOllamaSettings() {
    const url   = document.getElementById('ollama-url-input')?.value.trim() || 'http://localhost:11434';
    const model = document.getElementById('ollama-model-select')?.value || 'llama3';
    try {
        const res = await fetch(`${API}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ollama_url: url, ollama_model: model })
        });
        if (res.ok) showToast(I18N.t('toast.ollama_saved'), 'success');
        else showToast(I18N.t('toast.save_error'), 'error');
    } catch (_) {
        showToast(I18N.t('toast.network_error'), 'error');
    }
}

async function ollamaAutoTag() {
    if (!currentTagFile) return;

    const btn      = document.getElementById('ollama-autotag-btn');
    const resultEl = document.getElementById('ollama-autotag-result');
    const tagsEl   = document.getElementById('ollama-suggested-tags');

    const filename = currentTagFile.split('/').pop() || currentTagFile;

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${I18N.t('ollama.analyzing')}`;
    }
    if (resultEl) resultEl.style.display = 'none';

    try {
        const res = await fetch(`${API}/api/ollama/auto-tag`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename,
                file_path: currentTagFile,
                existing_tags: allTags.map(t => t.name)
            })
        });
        const data = await res.json();

        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);

        const suggestions = data.tags || [];
        if (!suggestions.length) {
            showToast(I18N.t('toast.ollama_no_tags'), 'warning');
            return;
        }

        const sourceLabel = `🖥️ ${I18N.t('ollama.source_local')}`;

        if (tagsEl) {
            tagsEl.innerHTML = suggestions.map(tag => {
                const alreadyExists = allTags.some(t => t.name.toLowerCase() === tag.toLowerCase());
                const color = alreadyExists ? (allTags.find(t => t.name.toLowerCase() === tag.toLowerCase())?.color || 'var(--accent)') : 'var(--accent)';
                return `<button type="button"
                    onclick="ollamaAddSuggestedTag('${escapeJs(tag)}')"
                    style="padding:4px 10px; border-radius:20px; border:1px solid ${color}; background:${color}20; color:${color}; font-size:12px; cursor:pointer;">
                    <i class="fa-solid fa-plus" style="font-size:10px;"></i> ${escapeHtml(tag)}
                </button>`;
            }).join('');
        }
        if (resultEl) resultEl.style.display = 'block';
        showToast(I18N.t('toast.ollama_tags_suggested', { count: suggestions.length, source: sourceLabel }), 'success');
    } catch (err) {
        console.error('[Ollama]', err);
        showToast(`Ollama : ${err.message}`, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> ${I18N.t('ollama.suggest_tags')}`;
        }
    }
}

function ollamaAddSuggestedTag(tagName) {
    const existing = [...document.querySelectorAll('.tag-select')].find(
        cb => cb.value.toLowerCase() === tagName.toLowerCase()
    );
    if (existing) {
        existing.checked = true;
        existing.closest('label')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        showToast(I18N.t('toast.tag_checked', { tag: tagName }), 'success');
    } else {
        const input = document.getElementById('tag-modal-new-tag');
        if (input) {
            input.value = tagName;
            input.focus();
        }
        showToast(I18N.t('toast.tag_ready_to_create', { tag: tagName }), 'info');
    }
}

window.testOllamaConnection = testOllamaConnection;
window.saveOllamaSettings   = saveOllamaSettings;
window.ollamaAutoTag        = ollamaAutoTag;
window.ollamaAddSuggestedTag = ollamaAddSuggestedTag;


let sosprintPhotoFile = null;
let sosprintCandidateCauses = [];
let sosprintEliminatedCauses = [];
let sosprintQaHistory = [];
let sosprintCurrentQuestion = null;
let sosprintConversationId = null;
let sosprintLastCauses = [];
let sosprintHistoryLoaded = { open: false, resolved: false };
let sosprintHistoryActiveTab = 'open';

function getSosprintFormValues() {
    return {
        material: document.querySelector('input[name="sosprint-material"]:checked')?.value || '',
        description: document.getElementById('sosprint-description')?.value.trim() || ''
    };
}

function setSosprintPhoto(file) {
    if (!file) return;
    const allowed = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowed.includes(file.type)) {
        showToast(I18N.t('sosprint.image_format_error'), 'error');
        return;
    }
    if (file.size > 8 * 1024 * 1024) {
        showToast(I18N.t('sosprint.image_too_large'), 'error');
        return;
    }
    sosprintPhotoFile = file;

    const placeholderEl = document.getElementById('sosprint-photo-placeholder');
    const previewEl = document.getElementById('sosprint-photo-preview');
    const previewImgEl = document.getElementById('sosprint-photo-preview-img');

    const reader = new FileReader();
    reader.onload = (e) => {
        if (previewImgEl) previewImgEl.src = e.target.result;
        if (placeholderEl) placeholderEl.style.display = 'none';
        if (previewEl) previewEl.style.display = 'flex';
    };
    reader.readAsDataURL(file);
}

function clearSosprintPhoto() {
    sosprintPhotoFile = null;
    const photoInput = document.getElementById('sosprint-photo-input');
    const placeholderEl = document.getElementById('sosprint-photo-placeholder');
    const previewEl = document.getElementById('sosprint-photo-preview');
    const previewImgEl = document.getElementById('sosprint-photo-preview-img');
    if (photoInput) photoInput.value = '';
    if (previewImgEl) previewImgEl.src = '';
    if (previewEl) previewEl.style.display = 'none';
    if (placeholderEl) placeholderEl.style.display = 'flex';
}

(() => {
    const zone = document.getElementById('sosprint-photo-zone');
    const input = document.getElementById('sosprint-photo-input');
    const removeBtn = document.getElementById('sosprint-photo-remove');

    zone?.addEventListener('click', (e) => {
        if (e.target.closest('.sosprint-photo-remove')) return;
        input?.click();
    });

    input?.addEventListener('change', (e) => {
        const file = e.target.files?.[0];
        if (file) setSosprintPhoto(file);
    });

    removeBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        clearSosprintPhoto();
    });

    ['dragover', 'dragleave', 'drop'].forEach(evt => {
        zone?.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.toggle('dragover', evt === 'dragover');
        });
    });
    zone?.addEventListener('drop', (e) => {
        const file = e.dataTransfer?.files?.[0];
        if (file) setSosprintPhoto(file);
    });
})();

// --- Ajout d'une photo à n'importe quel moment de l'enquête (pas seulement au démarrage) ---
(() => {
    const addBtn = document.getElementById('sosprint-add-photo-btn');
    const input = document.getElementById('sosprint-extra-photo-input');
    const statusEl = document.getElementById('sosprint-extra-photo-status');

    addBtn?.addEventListener('click', () => input?.click());

    input?.addEventListener('change', async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        if (!sosprintConversationId) {
            showToast(_t2('sosprint.no_conversation_yet', "Démarrez d'abord une enquête avant d'ajouter une photo"), 'warning');
            return;
        }
        addBtn.disabled = true;
        if (statusEl) statusEl.textContent = _t2('sosprint.uploading_photo', 'Envoi de la photo...');
        try {
            const formData = new FormData();
            formData.append('photo', file);
            const res = await fetch(`${API}/api/sos-print/conversations/${sosprintConversationId}/photo`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
            if (statusEl) statusEl.textContent = _t2('sosprint.photo_added', 'Photo ajoutée ✓');
            showToast(_t2('sosprint.photo_added_toast', "Photo ajoutée à l'enquête, elle sera analysée avec le diagnostic"), 'success');
        } catch (err) {
            console.error('[SOS Print Photo]', err);
            if (statusEl) statusEl.textContent = '';
            showToast(`${_t2('sosprint.photo_add_error', "Échec de l'ajout de la photo")} : ${err.message}`, 'error');
        } finally {
            addBtn.disabled = false;
            input.value = '';
        }
    });
})();

async function runSosprintDiagnosis(material, description, answers) {
    const btn = document.getElementById('sosprint-next-question-btn') || document.getElementById('sosprint-submit-btn');
    const skipBtn = document.getElementById('sosprint-skip-questions-btn');
    const resultEl = document.getElementById('sosprint-result');
    const causesEl = document.getElementById('sosprint-causes-list');
    const questionsEl = document.getElementById('sosprint-questions');

    const originalBtnHtml = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${I18N.t('sosprint.analyzing')}`;
    }
    if (skipBtn) skipBtn.disabled = true;
    if (resultEl) resultEl.style.display = 'none';
    const _recurringHintReset = document.getElementById('sosprint-recurring-hint');
    if (_recurringHintReset) _recurringHintReset.style.display = 'none';
    const _referenceHintReset = document.getElementById('sosprint-reference-hint');
    if (_referenceHintReset) _referenceHintReset.style.display = 'none';
    resetSosprintResolveBox();

    try {
        let res;
        const printerId = document.getElementById('sosprint-printer-select')?.value || '';
        const candidateCauses = sosprintCandidateCauses || [];
        if (sosprintPhotoFile) {
            const formData = new FormData();
            formData.append('material', material);
            formData.append('description', description);
            formData.append('answers', JSON.stringify(answers || []));
            formData.append('candidate_causes', JSON.stringify(candidateCauses));
            formData.append('photo', sosprintPhotoFile);
            if (printerId) formData.append('printer_id', printerId);
            if (sosprintConversationId) formData.append('conversation_id', sosprintConversationId);
            res = await fetch(`${API}/api/ollama/sos-print`, {
                method: 'POST',
                body: formData
            });
        } else {
            res = await fetch(`${API}/api/ollama/sos-print`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    material, description, answers: answers || [],
                    candidate_causes: candidateCauses,
                    printer_id: printerId || null,
                    conversation_id: sosprintConversationId || null
                })
            });
        }
        const data = await res.json();

        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);

        const causes = data.causes || [];
        if (!causes.length) {
            showToast(I18N.t('toast.sosprint_no_result'), 'warning');
            return;
        }

        if (data.conversation_id) sosprintConversationId = data.conversation_id;
        sosprintLastCauses = causes.map(c => c.split(/\s*:\s*/)[0].trim()).filter(Boolean);

        const sourceBadge = `<span style="display:inline-flex;align-items:center;gap:5px;font-size:11px;color:#22c55e;background:#22c55e15;padding:3px 8px;border-radius:20px;margin-bottom:10px;">
                <i class="fa-solid fa-server"></i> ${I18N.t('sosprint.source_local')}
               </span>`;
        const photoBadge = data.had_photo
            ? `<span style="display:inline-flex;align-items:center;gap:5px;font-size:11px;color:#a855f7;background:#a855f715;padding:3px 8px;border-radius:20px;margin-bottom:10px;margin-left:6px;">
                <i class="fa-solid fa-camera"></i> ${I18N.t('sosprint.photo_analyzed')}
               </span>`
            : (data.photo_ignored
                ? `<span style="display:inline-flex;align-items:center;gap:5px;font-size:11px;color:#f59e0b;background:#f59e0b15;padding:3px 8px;border-radius:20px;margin-bottom:10px;margin-left:6px;">
                <i class="fa-solid fa-triangle-exclamation"></i> ${I18N.t('sosprint.photo_ignored')}
               </span>`
                : '');

        if (causesEl) {
            causesEl.innerHTML = sourceBadge + photoBadge + causes.map((cause, i) => {
                const parts = cause.split(/\s*:\s*/);
                const title = parts.length > 1 ? parts[0] : `${I18N.t('sosprint.cause')} ${i + 1}`;
                const fix = parts.length > 1 ? parts.slice(1).join(': ') : cause;
                return `
                    <div class="sosprint-cause-card">
                        <div class="sosprint-cause-rank">#${i + 1}</div>
                        <div class="sosprint-cause-content">
                            <div class="sosprint-cause-title">${escapeHtml(title)}</div>
                            <div class="sosprint-cause-detail">${escapeHtml(fix)}</div>
                        </div>
                    </div>`;
            }).join('');
        }

        const recurringHint = document.getElementById('sosprint-recurring-hint');
        const recurringHintText = document.getElementById('sosprint-recurring-hint-text');
        if (recurringHint && recurringHintText) {
            if (data.recurring && (data.recurring_history || []).length) {
                const count = data.recurring_history.length;
                const printerLabel = data.printer_name || '';
                const items = data.recurring_history.map(h => {
                    const when = h.created_at ? new Date(h.created_at).toLocaleDateString() : '';
                    const cause = (h.causes && h.causes[0]) ? h.causes[0] : '';
                    return `<li>${when ? `<strong>${when}</strong> — ` : ''}${escapeHtml(cause)}</li>`;
                }).join('');
                recurringHintText.innerHTML = `<strong>${_t2('sosprint.recurring_title', 'Problème potentiellement récurrent')}</strong>
                    <div style="margin-top:2px;">${_t2('sosprint.recurring_body', 'Cette imprimante a eu {count} autre(s) diagnostic(s) ces 90 derniers jours{printer} :').replace('{count}', count).replace('{printer}', printerLabel ? ` (${printerLabel})` : '')}</div>
                    <ul style="margin:6px 0 0 18px; padding:0;">${items}</ul>`;
                recurringHint.style.display = 'flex';
            } else {
                recurringHint.style.display = 'none';
            }
        }

        const referenceHint = document.getElementById('sosprint-reference-hint');
        const referenceHintText = document.getElementById('sosprint-reference-hint-text');
        if (referenceHint && referenceHintText) {
            const refs = data.reference_cases || [];
            if (refs.length) {
                const items = refs.map(r => `<li><strong>${escapeHtml((r.description || '').slice(0, 80))}</strong> → ${escapeHtml(r.resolution_note || '')}</li>`).join('');
                referenceHintText.innerHTML = `<strong>${_t2('sosprint.reference_title', 'Diagnostic aidé par vos cas déjà résolus')}</strong>
                    <ul style="margin:6px 0 0 18px; padding:0;">${items}</ul>`;
                referenceHint.style.display = 'flex';
            } else {
                referenceHint.style.display = 'none';
            }
        }

        if (questionsEl) questionsEl.style.display = 'none';
        if (resultEl) {
            resultEl.style.display = 'block';
            resultEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        showToast(I18N.t('toast.sosprint_done'), 'success');
    } catch (err) {
        console.error('[SOS Print]', err);
        showToast(`${I18N.t('toast.sosprint_failed')} : ${err.message}`, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalBtnHtml;
        }
        if (skipBtn) skipBtn.disabled = false;
    }
}

function renderSosprintSuspects() {
    const listEl = document.getElementById('sosprint-suspects-list');
    if (!listEl) return;
    if (!sosprintCandidateCauses.length && !sosprintEliminatedCauses.length) {
        listEl.innerHTML = '';
        listEl.style.display = 'none';
        return;
    }
    listEl.style.display = 'flex';
    const remaining = sosprintCandidateCauses.map(c => `
        <div class="sosprint-suspect">
            <i class="fa-solid fa-magnifying-glass"></i> ${escapeHtml(c)}
        </div>
    `).join('');
    const eliminated = sosprintEliminatedCauses.map(c => `
        <div class="sosprint-suspect sosprint-suspect-eliminated">
            <i class="fa-solid fa-xmark"></i> <span>${escapeHtml(c)}</span>
        </div>
    `).join('');
    listEl.innerHTML = remaining + eliminated;
}

function renderSosprintQuestionStep(questionNumber) {
    const questionsEl = document.getElementById('sosprint-questions');
    const labelEl = document.getElementById('sosprint-current-question-label');
    const inputEl = document.getElementById('sosprint-current-answer');
    const counterEl = document.getElementById('sosprint-question-counter');
    const nextBtn = document.getElementById('sosprint-next-question-btn');
    const photoStatusEl = document.getElementById('sosprint-extra-photo-status');

    if (labelEl) labelEl.textContent = sosprintCurrentQuestion || '';
    if (inputEl) { inputEl.value = ''; inputEl.focus(); }
    if (photoStatusEl) photoStatusEl.textContent = '';
    // Plus de limite affichée : le nombre de questions est illimité, l'IA conclut dès qu'elle est confiante.
    if (counterEl) {
        counterEl.textContent = _t2('sosprint.question_counter_unlimited', 'Question {n}', { n: questionNumber }).replace('{n}', questionNumber);
    }
    if (nextBtn) {
        nextBtn.disabled = false;
        nextBtn.innerHTML = `<i class="fa-solid fa-arrow-right"></i> ${I18N.t('sosprint.next_question')}`;
    }
    renderSosprintSuspects();
    if (questionsEl) {
        questionsEl.style.display = 'flex';
        questionsEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function resetSosprintInvestigation() {
    sosprintCandidateCauses = [];
    sosprintEliminatedCauses = [];
    sosprintQaHistory = [];
    sosprintCurrentQuestion = null;
    sosprintConversationId = null;
}

function resetSosprintResolveBox() {
    const formBox = document.getElementById('sosprint-resolve-form');
    const badge = document.getElementById('sosprint-resolved-badge');
    const note = document.getElementById('sosprint-resolution-note');
    if (formBox) formBox.style.display = 'block';
    if (badge) badge.style.display = 'none';
    if (note) note.value = '';
}

document.getElementById('sosprint-resolve-btn')?.addEventListener('click', async () => {
    if (!sosprintConversationId) {
        showToast(_t2('sosprint.no_conversation_yet', "Aucune enquête en cours à marquer comme résolue"), 'warning');
        return;
    }
    const btn = document.getElementById('sosprint-resolve-btn');
    const note = document.getElementById('sosprint-resolution-note')?.value.trim() || '';
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i>`;
    try {
        const res = await fetch(`${API}/api/sos-print/conversations/${sosprintConversationId}/resolve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ resolution_note: note })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);

        const formBox = document.getElementById('sosprint-resolve-form');
        const badge = document.getElementById('sosprint-resolved-badge');
        if (formBox) formBox.style.display = 'none';
        if (badge) badge.style.display = 'block';
        showToast(_t2('sosprint.resolved_toast', 'Diagnostic marqué comme résolu'), 'success');
        sosprintHistoryLoaded = { open: false, resolved: false };
        if (document.getElementById('sosprint-history-body')?.style.display !== 'none') {
            loadSosprintHistory(sosprintHistoryActiveTab, true);
        }
    } catch (err) {
        console.error('[SOS Print Resolve]', err);
        showToast(`${_t2('sosprint.resolve_error', 'Échec du marquage comme résolu')} : ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
});

document.getElementById('sosprint-not-resolved-btn')?.addEventListener('click', async () => {
    if (!sosprintConversationId) {
        showToast(_t2('sosprint.no_conversation_yet', "Aucune enquête en cours à reprendre"), 'warning');
        return;
    }
    const btn = document.getElementById('sosprint-not-resolved-btn');
    const extraNote = document.getElementById('sosprint-resolution-note')?.value.trim() || '';
    const { material, description } = getSosprintFormValues();

    const originalHtml2 = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i>`;

    // On informe l'IA que les causes précédemment proposées n'ont pas résolu le problème,
    // pour qu'elle les élimine et continue l'enquête sur d'autres pistes.
    const triedCauses = sosprintLastCauses.length
        ? sosprintLastCauses.join(', ')
        : _t2('sosprint.not_resolved_unknown_causes', 'le diagnostic précédent');
    let answerText = _t2('sosprint.not_resolved_answer_template', 'Non, toujours pas résolu après avoir vérifié : {causes}').replace('{causes}', triedCauses);
    if (extraNote) answerText += ` (${extraNote})`;

    sosprintQaHistory.push({
        question: _t2('sosprint.not_resolved_question', 'Ce diagnostic a-t-il résolu le problème ?'),
        answer: answerText
    });
    sosprintLastCauses.forEach(c => {
        if (!sosprintEliminatedCauses.includes(c)) sosprintEliminatedCauses.push(c);
    });
    if (!sosprintCandidateCauses.length) sosprintCandidateCauses = sosprintLastCauses.slice();

    const resultEl2 = document.getElementById('sosprint-result');
    const questionsEl2 = document.getElementById('sosprint-questions');
    if (resultEl2) resultEl2.style.display = 'none';
    if (questionsEl2) {
        questionsEl2.style.display = 'flex';
        questionsEl2.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    const labelEl2 = document.getElementById('sosprint-current-question-label');
    if (labelEl2) labelEl2.textContent = I18N.t('sosprint.thinking');

    try {
        const res = await fetch(`${API}/api/ollama/sos-print/next-question`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                material, description,
                candidate_causes: sosprintCandidateCauses,
                qa_history: sosprintQaHistory,
                conversation_id: sosprintConversationId
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);

        (data.eliminated || []).forEach(c => {
            if (!sosprintEliminatedCauses.includes(c)) sosprintEliminatedCauses.push(c);
        });
        sosprintCandidateCauses = data.candidate_causes || sosprintCandidateCauses;
        if (data.conversation_id) sosprintConversationId = data.conversation_id;

        if (data.status === 'question' && data.question) {
            sosprintCurrentQuestion = data.question;
            renderSosprintQuestionStep(sosprintQaHistory.length + 1);
            showToast(_t2('sosprint.resumed_toast', 'Enquête reprise'), 'success');
        } else {
            // L'IA n'a pas de nouvelle piste distincte à explorer : on relance quand même
            // un diagnostic, qui tiendra compte des causes désormais écartées.
            await runSosprintDiagnosis(material, description, sosprintQaHistory);
        }
    } catch (err) {
        console.error('[SOS Print Not Resolved]', err);
        showToast(`${_t2('sosprint.resume_error', 'Impossible de reprendre cette enquête')} : ${err.message}`, 'error');
        if (questionsEl2) questionsEl2.style.display = 'none';
        if (resultEl2) resultEl2.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml2;
    }
});

// --- Historique des conversations : liste, reprise, suppression ---

async function loadSosprintHistory(status, force) {
    if (!force && sosprintHistoryLoaded[status]) return;
    const listEl = document.getElementById('sosprint-history-list');
    const countEl = document.getElementById('sosprint-history-count');
    if (!listEl) return;
    listEl.innerHTML = `<div class="sosprint-history-loading"><i class="fa-solid fa-circle-notch fa-spin"></i></div>`;
    try {
        const res = await fetch(`${API}/api/sos-print/conversations?status=${status}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        sosprintHistoryLoaded[status] = true;
        const convs = data.conversations || [];
        if (countEl) countEl.textContent = convs.length ? `(${convs.length})` : '';
        if (!convs.length) {
            listEl.innerHTML = `<div class="sosprint-history-empty">
                <i class="fa-solid ${status === 'resolved' ? 'fa-circle-check' : 'fa-magnifying-glass'}"></i>
                <span>${status === 'resolved'
                ? _t2('sosprint.history_empty_resolved', 'Aucun diagnostic résolu pour le moment')
                : _t2('sosprint.history_empty_open', 'Aucune enquête en cours')}</span>
            </div>`;
            return;
        }
        listEl.innerHTML = convs.map(c => {
            const date = c.updated_at ? new Date(c.updated_at).toLocaleDateString() : '';
            const badge = status === 'resolved'
                ? `<span class="sosprint-history-badge resolved"><i class="fa-solid fa-circle-check"></i> ${_t2('sosprint.history_tab_resolved', 'Résolu')}</span>`
                : `<span class="sosprint-history-badge open"><i class="fa-solid fa-magnifying-glass"></i> ${_t2('sosprint.history_tab_open', 'En cours')}</span>`;
            return `
                <div class="sosprint-history-item" data-conv-id="${c.id}">
                    <div class="sosprint-history-item-main">
                        <div class="sosprint-history-item-title">${escapeHtml(c.title || c.description)}</div>
                        <div class="sosprint-history-item-meta">${escapeHtml(c.material || '')} · ${date} ${badge}</div>
                    </div>
                    <div class="sosprint-history-item-actions">
                        <button type="button" class="btn btn-ghost btn-sm sosprint-history-resume" data-conv-id="${c.id}" title="${_t2('sosprint.resume', 'Reprendre')}">
                            <i class="fa-solid fa-arrow-rotate-right"></i> ${_t2('sosprint.resume', 'Reprendre')}
                        </button>
                        <button type="button" class="btn btn-ghost btn-sm sosprint-history-delete" data-conv-id="${c.id}" title="${_t2('actions.delete', 'Supprimer')}">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>`;
        }).join('');
    } catch (err) {
        console.error('[SOS Print History]', err);
        listEl.innerHTML = `<div class="sosprint-history-empty"><i class="fa-solid fa-triangle-exclamation"></i><span>${_t2('sosprint.history_load_error', "Impossible de charger l'historique")}</span></div>`;
    }
}

async function resumeSosprintConversation(convId) {
    try {
        const res = await fetch(`${API}/api/sos-print/conversations/${convId}`);
        const conv = await res.json();
        if (!res.ok) throw new Error(conv.error || `HTTP ${res.status}`);

        resetSosprintInvestigation();
        clearSosprintPhoto();
        resetSosprintResolveBox();

        sosprintConversationId = conv.id;
        sosprintCandidateCauses = conv.candidate_causes || [];
        sosprintEliminatedCauses = conv.eliminated_causes || [];

        // Reconstruit l'historique question/réponse à partir des messages persistés.
        sosprintQaHistory = [];
        let pendingQuestion = null;
        (conv.messages || []).forEach(m => {
            if (m.role === 'question') {
                pendingQuestion = m.content;
            } else if (m.role === 'answer' && pendingQuestion) {
                sosprintQaHistory.push({ question: pendingQuestion, answer: m.content });
                pendingQuestion = null;
            }
        });
        sosprintCurrentQuestion = pendingQuestion;

        const materialInput = document.querySelector(`input[name="sosprint-material"][value="${CSS.escape(conv.material || 'PLA')}"]`);
        if (materialInput) materialInput.checked = true;
        const descEl = document.getElementById('sosprint-description');
        if (descEl) descEl.value = conv.description || '';

        const resultEl = document.getElementById('sosprint-result');
        if (resultEl) resultEl.style.display = 'none';

        if (conv.status === 'resolved') {
            // On affiche le dernier diagnostic connu, en lecture seule (déjà marqué résolu).
            const causesEl = document.getElementById('sosprint-causes-list');
            if (causesEl && conv.last_causes && conv.last_causes.length) {
                causesEl.innerHTML = conv.last_causes.map((cause, i) => {
                    const parts = cause.split(/\s*:\s*/);
                    const title = parts.length > 1 ? parts[0] : `${I18N.t('sosprint.cause')} ${i + 1}`;
                    const fix = parts.length > 1 ? parts.slice(1).join(': ') : cause;
                    return `<div class="sosprint-cause-card"><div class="sosprint-cause-rank">#${i + 1}</div><div class="sosprint-cause-content"><div class="sosprint-cause-title">${escapeHtml(title)}</div><div class="sosprint-cause-detail">${escapeHtml(fix)}</div></div></div>`;
                }).join('');
            }
            const formBox = document.getElementById('sosprint-resolve-form');
            const badge = document.getElementById('sosprint-resolved-badge');
            if (formBox) formBox.style.display = 'none';
            if (badge) badge.style.display = 'block';
            if (resultEl) resultEl.style.display = 'block';
        } else if (sosprintCurrentQuestion) {
            renderSosprintQuestionStep(sosprintQaHistory.length + 1);
        } else {
            await runSosprintDiagnosis(conv.material, conv.description, sosprintQaHistory);
        }

        document.getElementById('page-sosprint')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        showToast(_t2('sosprint.resumed_toast', 'Enquête reprise'), 'success');
    } catch (err) {
        console.error('[SOS Print Resume]', err);
        showToast(`${_t2('sosprint.resume_error', 'Impossible de reprendre cette enquête')} : ${err.message}`, 'error');
    }
}

async function deleteSosprintConversation(convId) {
    const ok = await showConfirmDialog(
        _t2('sosprint.delete_confirm', 'Supprimer définitivement ce diagnostic ?'),
        { title: _t2('actions.delete', 'Supprimer'), danger: true }
    );
    if (!ok) return;
    try {
        const res = await fetch(`${API}/api/sos-print/conversations/${convId}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        sosprintHistoryLoaded = { open: false, resolved: false };
        loadSosprintHistory(sosprintHistoryActiveTab, true);
        showToast(_t2('sosprint.deleted_toast', 'Diagnostic supprimé'), 'success');
    } catch (err) {
        console.error('[SOS Print Delete]', err);
        showToast(`${_t2('sosprint.delete_error', 'Échec de la suppression')} : ${err.message}`, 'error');
    }
}

(() => {
    const toggle = document.getElementById('sosprint-history-toggle');
    const body = document.getElementById('sosprint-history-body');
    const chevron = document.getElementById('sosprint-history-chevron');
    const tabs = document.querySelectorAll('.sosprint-history-tab');
    const list = document.getElementById('sosprint-history-list');

    toggle?.addEventListener('click', () => {
        const isOpen = body.style.display !== 'none';
        body.style.display = isOpen ? 'none' : 'block';
        chevron?.classList.toggle('rotated', !isOpen);
        if (!isOpen) loadSosprintHistory(sosprintHistoryActiveTab);
    });

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            sosprintHistoryActiveTab = tab.dataset.status;
            // Toujours recharger au changement d'onglet : la liste HTML est partagée entre
            // les deux onglets, donc s'appuyer sur le cache "déjà chargé" affichait le contenu
            // périmé de l'autre onglet au lieu de rafraîchir celui qu'on vient de sélectionner.
            loadSosprintHistory(sosprintHistoryActiveTab, true);
        });
    });

    list?.addEventListener('click', (e) => {
        const resumeBtn = e.target.closest('.sosprint-history-resume');
        const deleteBtn = e.target.closest('.sosprint-history-delete');
        if (resumeBtn) resumeSosprintConversation(resumeBtn.dataset.convId);
        else if (deleteBtn) deleteSosprintConversation(deleteBtn.dataset.convId);
    });
})();

document.getElementById('sosprint-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!window.aiEnabled) {
        showToast(I18N.t('toast.ai_disabled_warning'), 'warning');
        return;
    }

    const { material, description } = getSosprintFormValues();
    if (!description) {
        showToast(I18N.t('sosprint.describe_required'), 'error');
        return;
    }

    const submitBtn = document.getElementById('sosprint-submit-btn');
    const questionsEl = document.getElementById('sosprint-questions');
    const resultEl = document.getElementById('sosprint-result');

    resetSosprintInvestigation();

    const originalBtnHtml = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${I18N.t('sosprint.preparing_questions')}`;
    if (resultEl) resultEl.style.display = 'none';
    if (questionsEl) questionsEl.style.display = 'none';

    try {
        const printerId = document.getElementById('sosprint-printer-select')?.value || '';
        const res = await fetch(`${API}/api/ollama/sos-print/questions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ material, description, printer_id: printerId || null })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);

        sosprintConversationId = data.conversation_id || null;
        sosprintCandidateCauses = data.candidate_causes || [];
        sosprintCurrentQuestion = data.question || null;

        // Si une photo a déjà été jointe au formulaire initial, on l'attache tout de suite
        // à la conversation pour qu'elle profite aussi aux questions de clarification.
        if (sosprintPhotoFile && sosprintConversationId) {
            const fd = new FormData();
            fd.append('photo', sosprintPhotoFile);
            fetch(`${API}/api/sos-print/conversations/${sosprintConversationId}/photo`, { method: 'POST', body: fd }).catch(() => {});
        }

        if (!sosprintCurrentQuestion) {
            await runSosprintDiagnosis(material, description, []);
            return;
        }

        renderSosprintQuestionStep(1);
    } catch (err) {
        console.error('[SOS Print Questions]', err);
        showToast(`${I18N.t('sosprint.prepare_error')} : ${err.message}`, 'error');
        await runSosprintDiagnosis(material, description, []);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnHtml;
    }
});

document.getElementById('sosprint-next-question-btn')?.addEventListener('click', async () => {
    const { material, description } = getSosprintFormValues();
    const inputEl = document.getElementById('sosprint-current-answer');
    const nextBtn = document.getElementById('sosprint-next-question-btn');
    const answer = inputEl?.value.trim() || '';

    if (sosprintCurrentQuestion) {
        sosprintQaHistory.push({ question: sosprintCurrentQuestion, answer: answer || I18N.t('sosprint.no_precision') });
    }

    if (nextBtn) {
        nextBtn.disabled = true;
        nextBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${I18N.t('sosprint.thinking')}`;
    }

    try {
        const res = await fetch(`${API}/api/ollama/sos-print/next-question`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                material, description,
                candidate_causes: sosprintCandidateCauses,
                qa_history: sosprintQaHistory,
                conversation_id: sosprintConversationId
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);

        (data.eliminated || []).forEach(c => {
            if (!sosprintEliminatedCauses.includes(c)) sosprintEliminatedCauses.push(c);
        });
        sosprintCandidateCauses = data.candidate_causes || sosprintCandidateCauses;
        if (data.conversation_id) sosprintConversationId = data.conversation_id;

        if (data.status === 'done') {
            await runSosprintDiagnosis(material, description, sosprintQaHistory);
            return;
        }

        sosprintCurrentQuestion = data.question;
        renderSosprintQuestionStep(sosprintQaHistory.length + 1);
    } catch (err) {
        console.error('[SOS Print Next Question]', err);
        showToast(`${I18N.t('sosprint.prepare_error')} : ${err.message}`, 'error');
        await runSosprintDiagnosis(material, description, sosprintQaHistory);
    }
});

document.getElementById('sosprint-current-answer')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('sosprint-next-question-btn')?.click();
    }
});

document.getElementById('sosprint-skip-questions-btn')?.addEventListener('click', async () => {
    const { material, description } = getSosprintFormValues();
    // "Conclure maintenant" : on demande explicitement à l'IA de conclure avec ce qu'elle a déjà,
    // plutôt que de forcer un arrêt côté client après un nombre fixe de questions.
    if (sosprintQaHistory.length === 0 && !sosprintCurrentQuestion) {
        await runSosprintDiagnosis(material, description, sosprintQaHistory);
        return;
    }
    try {
        const res = await fetch(`${API}/api/ollama/sos-print/next-question`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                material, description,
                candidate_causes: sosprintCandidateCauses,
                qa_history: sosprintQaHistory,
                conversation_id: sosprintConversationId,
                conclude_now: true
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        (data.eliminated || []).forEach(c => {
            if (!sosprintEliminatedCauses.includes(c)) sosprintEliminatedCauses.push(c);
        });
        sosprintCandidateCauses = data.candidate_causes || sosprintCandidateCauses;
    } catch (err) {
        console.debug('[SOS Print Conclude]', err);
    }
    await runSosprintDiagnosis(material, description, sosprintQaHistory);
});

async function getSpoolmanUrl() {
    try {
        const res = await fetch(`${API}/api/settings`);
        if (res.ok) {
            const data = await res.json();
            if ('spoolman_url' in data) return data.spoolman_url || '';
        }
    } catch (e) {}
    return localStorage.getItem('stellio-spoolman-url') || '';
}

async function loadSpoolmanPage() {
    const grid = document.getElementById('spoolman-grid');
    const label = document.getElementById('spoolman-server-label');
    const addBtn = document.getElementById('add-manual-spool-btn');
    const filtersBar = document.getElementById('spoolman-filters');
    const headerFilterEls = [
        document.getElementById('spool-header-search-wrap'),
        document.getElementById('spool-header-material'),
        document.getElementById('spool-header-location'),
        document.getElementById('spool-header-sort')
    ];
    if (!grid) return;

    const url = await getSpoolmanUrl();
    // Le filtrage/tri (mobile comme header) n'est proposé que pour
    // l'inventaire local : un serveur Spoolman distant n'est pas indexé
    // côté Stellio, donc pas de recherche/tri possible dessus.
    const isSpoolmanPageActive = document.getElementById('page-spoolman')?.classList.contains('active');
    headerFilterEls.forEach(el => {
        if (!el) return;
        el.classList.toggle('header-hide', !!url || !isSpoolmanPageActive);
    });

    if (label) {
        label.innerHTML = url
            ? `<i class="fa-solid fa-circle-nodes"></i> ${escapeHtml(url)}`
            : `<i class="fa-solid fa-box-open"></i> ${_t2('spoolman.local_inventory_label', 'Inventaire local (sans serveur Spoolman)')}`;
    }

    if (!url) {
        if (addBtn) addBtn.style.display = '';
        if (filtersBar) filtersBar.style.display = 'flex';
        await loadManualSpoolInventory();
        return;
    }

    if (addBtn) addBtn.style.display = 'none';
    if (filtersBar) filtersBar.style.display = 'none';
    grid.innerHTML = `
        <div class="empty-state">
            <i class="fa-solid fa-spinner fa-spin"></i>
            <p>${I18N.t('spoolman.loading')}</p>
        </div>`;

    try {
        const res = await fetch(`${API}/api/spoolman/spools?url=${encodeURIComponent(url)}`);
        const data = await res.json();
        if (!res.ok) {
            grid.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <p>${escapeHtml(data.error || I18N.t('spoolman.connection_error'))}</p>
                    <button class="btn btn-ghost btn-sm" style="margin-top:10px;" onclick="loadSpoolmanPage()">${I18N.t('actions.retry')}</button>
                </div>`;
            return;
        }
        renderSpoolmanGrid(Array.isArray(data) ? data : []);
    } catch (err) {
        console.error('[Spoolman]', err);
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>${_t2('spoolman.server_unreachable', 'Serveur injoignable')}</p>
                <button class="btn btn-ghost btn-sm" style="margin-top:10px;" onclick="loadSpoolmanPage()">${I18N.t('actions.retry')}</button>
            </div>`;
    }
}
window.loadSpoolmanPage = loadSpoolmanPage;


async function loadManualSpoolInventory() {
    const grid = document.getElementById('spoolman-grid');
    if (!grid) return;
    grid.innerHTML = `
        <div class="empty-state">
            <i class="fa-solid fa-spinner fa-spin"></i>
            <p>${I18N.t('spoolman.loading')}</p>
        </div>`;
    try {
        const res = await fetch(`${API}/api/filament/manual`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Erreur');
        renderManualSpoolGrid(Array.isArray(data) ? data : []);
    } catch (err) {
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>${_t2('spoolman.server_unreachable', 'Erreur de connexion')}</p>
                <button class="btn btn-ghost btn-sm" style="margin-top:10px;" onclick="loadManualSpoolInventory()">${I18N.t('actions.retry')}</button>
            </div>`;
    }
}
window.loadManualSpoolInventory = loadManualSpoolInventory;

let _manualSpoolCache = [];
let _manualSpoolFiltersBound = false;

// Recherche / matière / rangement / tri existent en double : une fois dans le
// header (desktop, page inventaire filament) et une fois dans le bandeau en
// page (repris uniquement en mobile, header masqué sous 860px — cf. CSS
// .spoolman-filters-mobile-only). Les deux jeux sont tenus synchronisés.
const _SPOOL_FILTER_PAIRS = [
    ['spool-filter-search', 'spool-header-search'],
    ['spool-filter-material', 'spool-header-material'],
    ['spool-filter-location', 'spool-header-location'],
    ['spool-sort', 'spool-header-sort']
];

function _manualSpoolFilterValue(mobileId, headerId, fallback = '') {
    const mobileEl = document.getElementById(mobileId);
    const headerEl = document.getElementById(headerId);
    // Le champ actuellement visible (l'autre est masqué par CSS selon la
    // largeur d'écran) fait foi ; à défaut on retombe sur celui qui a une
    // valeur non vide.
    if (headerEl && headerEl.offsetParent !== null) return headerEl.value;
    if (mobileEl && mobileEl.offsetParent !== null) return mobileEl.value;
    return headerEl?.value || mobileEl?.value || fallback;
}

function _manualSpoolFilterState() {
    return {
        search: _manualSpoolFilterValue('spool-filter-search', 'spool-header-search').trim().toLowerCase(),
        material: _manualSpoolFilterValue('spool-filter-material', 'spool-header-material'),
        location: _manualSpoolFilterValue('spool-filter-location', 'spool-header-location'),
        sort: _manualSpoolFilterValue('spool-sort', 'spool-header-sort', 'created_desc') || 'created_desc'
    };
}

function _populateManualSpoolFilterOptions(spools) {
    const keepFirstOption = (sel) => sel.querySelector('option')?.outerHTML || '';
    const materials = [...new Set(spools.map(s => (s.material || '').trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b));
    const locations = [...new Set(spools.map(s => (s.storage_location || '').trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b));

    [document.getElementById('spool-filter-material'), document.getElementById('spool-header-material')].forEach(materialSel => {
        if (!materialSel) return;
        const prevMaterial = materialSel.value;
        materialSel.innerHTML = keepFirstOption(materialSel) + materials.map(m => `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`).join('');
        if (materials.includes(prevMaterial)) materialSel.value = prevMaterial;
    });

    [document.getElementById('spool-filter-location'), document.getElementById('spool-header-location')].forEach(locationSel => {
        if (!locationSel) return;
        const prevLocation = locationSel.value;
        locationSel.innerHTML = keepFirstOption(locationSel) + locations.map(l => `<option value="${escapeHtml(l)}">${escapeHtml(l)}</option>`).join('');
        if (locations.includes(prevLocation)) locationSel.value = prevLocation;
    });
}

function _applyManualSpoolFiltersAndSort(spools) {
    const { search, material, location, sort } = _manualSpoolFilterState();
    let result = spools.filter(s => {
        if (material && (s.material || '').trim() !== material) return false;
        if (location && (s.storage_location || '').trim() !== location) return false;
        if (search) {
            const haystack = `${s.name || ''} ${s.vendor || ''} ${s.material || ''} ${s.storage_location || ''} ${s.notes || ''}`.toLowerCase();
            if (!haystack.includes(search)) return false;
        }
        return true;
    });
    const cmp = {
        created_desc: () => 0, // déjà trié par created_at DESC côté serveur
        name_asc: (a, b) => (a.name || '').localeCompare(b.name || ''),
        material_asc: (a, b) => (a.material || '').localeCompare(b.material || '') || (a.name || '').localeCompare(b.name || ''),
        color: (a, b) => (a.color_hex || '').localeCompare(b.color_hex || ''),
        location_asc: (a, b) => (a.storage_location || '').localeCompare(b.storage_location || '') || (a.name || '').localeCompare(b.name || ''),
        remaining_asc: (a, b) => (a.remaining_g ?? Infinity) - (b.remaining_g ?? Infinity),
        remaining_desc: (a, b) => (b.remaining_g ?? -Infinity) - (a.remaining_g ?? -Infinity),
    }[sort];
    if (sort !== 'created_desc') result = [...result].sort(cmp);
    return result;
}

function _bindManualSpoolFilterListeners() {
    if (_manualSpoolFiltersBound) return;
    _manualSpoolFiltersBound = true;
    _SPOOL_FILTER_PAIRS.forEach(([mobileId, headerId]) => {
        [mobileId, headerId].forEach((id, idx) => {
            const el = document.getElementById(id);
            if (!el) return;
            const mirrorId = idx === 0 ? headerId : mobileId;
            const evt = el.tagName === 'SELECT' ? 'change' : 'input';
            el.addEventListener(evt, () => {
                const mirrorEl = document.getElementById(mirrorId);
                if (mirrorEl) mirrorEl.value = el.value;
                _renderManualSpoolCards(_applyManualSpoolFiltersAndSort(_manualSpoolCache));
            });
        });
    });
    document.getElementById('spool-header-search-clear')?.addEventListener('click', () => {
        const headerInput = document.getElementById('spool-header-search');
        const mobileInput = document.getElementById('spool-filter-search');
        if (headerInput) headerInput.value = '';
        if (mobileInput) mobileInput.value = '';
        _renderManualSpoolCards(_applyManualSpoolFiltersAndSort(_manualSpoolCache));
        headerInput?.focus();
    });
}

function renderManualSpoolGrid(spools) {
    _manualSpoolCache = spools;
    _populateManualSpoolFilterOptions(spools);
    _bindManualSpoolFilterListeners();
    _renderManualSpoolCards(_applyManualSpoolFiltersAndSort(spools));
}
window.renderManualSpoolGrid = renderManualSpoolGrid;

function _renderManualSpoolCards(spools) {
    const grid = document.getElementById('spoolman-grid');
    if (!grid) return;
    if (!_manualSpoolCache.length) {
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-box-open"></i>
                <p>${_t2('spoolman.no_manual_spools', 'Aucune bobine dans ton inventaire')}</p>
            </div>`;
        return;
    }
    if (!spools.length) {
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-filter-circle-xmark"></i>
                <p>${_t2('spoolman.no_matching_spools', 'Aucune bobine ne correspond à ces filtres')}</p>
            </div>`;
        return;
    }
    grid.innerHTML = spools.map(s => {
        const color = s.color_hex || '#888888';
        const remaining = typeof s.remaining_g === 'number' ? s.remaining_g : null;
        const capacity = s.capacity_g || null;
        const pct = (remaining !== null && capacity) ? Math.max(0, Math.min(100, (remaining / capacity) * 100)) : null;
        const archived = !!s.archived;
        return `
            <div class="spool-card ${archived ? 'archived' : ''}">
                <div class="spool-card-header">
                    <span class="spool-color-dot" style="background:${escapeHtml(color)};"></span>
                    <div class="spool-title">
                        <span class="spool-name">${escapeHtml(s.name)}</span>
                        ${s.vendor ? `<span class="spool-vendor">${escapeHtml(s.vendor)}</span>` : ''}
                    </div>
                    ${archived ? `<span class="spool-badge">${_t2('spoolman.archived', 'Archivée')}</span>` : ''}
                </div>
                <div class="spool-card-body">
                    ${(s.material || s.storage_location) ? `
                        <div class="spool-tags-row">
                            ${s.material ? `<span class="spool-material-tag">${escapeHtml(s.material)}</span>` : ''}
                            ${s.storage_location ? `<span class="spool-storage-tag"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(s.storage_location)}</span>` : ''}
                        </div>
                    ` : ''}
                    ${pct !== null ? `
                        <div class="spool-weight-row">
                            <span>${Math.round(remaining)} ${I18N.t('units.g_remaining')}</span>
                            <span>${Math.round(pct)}%</span>
                        </div>
                        <div class="spool-progress-track">
                            <div class="spool-progress-bar" style="width:${pct}%; background:${escapeHtml(color)};"></div>
                        </div>
                    ` : remaining !== null ? `<p class="spool-weight-row"><span>${Math.round(remaining)} ${I18N.t('units.g_remaining')}</span></p>` : ''}
                    ${s.price ? `<p class="spool-location"><i class="fa-solid fa-tag"></i> ${Number(s.price).toFixed(2)} €</p>` : ''}
                    ${s.diameter_mm ? `<p class="spool-location"><i class="fa-solid fa-ruler"></i> Ø${s.diameter_mm} mm</p>` : ''}
                    ${s.notes ? `<p class="spool-location" style="white-space:normal;"><i class="fa-solid fa-note-sticky"></i> ${escapeHtml(s.notes)}</p>` : ''}
                </div>
                <div class="spool-card-actions" style="display:flex; gap:6px; margin-top:10px; padding-top:10px; border-top:1px solid var(--border);">
                    <button class="btn btn-ghost btn-sm" style="flex:1;" onclick="openSpoolInventoryModal(${s.id})">
                        <i class="fa-solid fa-pen"></i> ${_t2('actions.edit', 'Modifier')}
                    </button>
                    <button class="btn btn-ghost btn-sm" onclick="toggleArchiveManualSpool(${s.id}, ${!archived})" data-i18n-title="${archived ? 'spoolman.unarchive' : 'spoolman.archive'}" title="${archived ? _t2('spoolman.unarchive', 'Désarchiver') : _t2('spoolman.archive', 'Archiver')}">
                        <i class="fa-solid ${archived ? 'fa-box-open' : 'fa-box-archive'}"></i>
                    </button>
                    <button class="btn btn-ghost btn-sm" style="color:var(--danger);" onclick="deleteManualSpoolFromInventory(${s.id})" data-i18n-title="actions.delete" title="${_t2('actions.delete', 'Supprimer')}">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>`;
    }).join('');
}

function openSpoolInventoryModal(spoolId) {
    const existing = spoolId ? _manualSpoolCache.find(s => s.id === spoolId) : null;
    let modal = document.getElementById('modal-spool-inventory');
    if (modal) modal.remove();
    modal = document.createElement('div');
    modal.id = 'modal-spool-inventory';
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content small">
            <div class="modal-header">
                <h2>${existing ? _t2('spoolman.edit_spool', 'Modifier la bobine') : _t2('spoolman.add_spool_btn', 'Ajouter bobine')}</h2>
                <button class="modal-close" onclick="closeModal('modal-spool-inventory')">×</button>
            </div>
            <div class="modal-body" style="display:flex; flex-direction:column; gap:10px;">
                <div class="input-group">
                    <label>${_t2('spoolman.name', 'Nom')}</label>
                    <input type="text" id="spool-inv-name" class="form-input" placeholder="${_t2('spoolman.name', 'Nom')} (ex: PLA Noir Geeetech)" value="${escapeHtml(existing?.name || '')}">
                </div>
                <div style="display:flex; gap:8px;">
                    <div class="input-group" style="flex:1;">
                        <label>${_t2('spoolman.material', 'Matière')}</label>
                        <input type="text" id="spool-inv-material" class="form-input" placeholder="PLA, PETG, ABS..." value="${escapeHtml(existing?.material || '')}">
                    </div>
                    <div class="input-group" style="width:70px;">
                        <label>${_t2('spoolman.color', 'Couleur')}</label>
                        <input type="color" id="spool-inv-color" value="${existing?.color_hex || '#888888'}" style="width:100%; height:38px; padding:2px; border-radius:var(--radius); border:1px solid var(--border); cursor:pointer;">
                    </div>
                </div>
                <div class="input-group">
                    <label>${_t2('spoolman.vendor', 'Marque')}</label>
                    <input type="text" id="spool-inv-vendor" class="form-input" placeholder="${_t2('spoolman.vendor', 'Marque')} (ex: Geeetech, eSun...)" value="${escapeHtml(existing?.vendor || '')}">
                </div>
                <div style="display:flex; gap:8px;">
                    <div class="input-group" style="flex:1;">
                        <label>${_t2('spoolman.remaining_g', 'Poids restant (g)')}</label>
                        <input type="number" id="spool-inv-remaining" class="form-input" placeholder="1000" value="${existing?.remaining_g ?? ''}">
                    </div>
                    <div class="input-group" style="flex:1;">
                        <label>${_t2('spoolman.capacity_g', 'Poids total (g)')}</label>
                        <input type="number" id="spool-inv-capacity" class="form-input" placeholder="1000" value="${existing?.capacity_g ?? 1000}">
                    </div>
                </div>
                <div style="display:flex; gap:8px;">
                    <div class="input-group" style="flex:1;">
                        <label>${_t2('spoolman.price', 'Prix (€)')}</label>
                        <input type="number" step="0.01" id="spool-inv-price" class="form-input" placeholder="19.99" value="${existing?.price ?? ''}">
                    </div>
                    <div class="input-group" style="flex:1;">
                        <label>${_t2('spoolman.diameter', 'Diamètre (mm)')}</label>
                        <input type="number" step="0.01" id="spool-inv-diameter" class="form-input" placeholder="1.75" value="${existing?.diameter_mm ?? 1.75}">
                    </div>
                </div>
                <div class="input-group">
                    <label>${_t2('spoolman.notes', 'Notes')}</label>
                    <textarea id="spool-inv-notes" class="form-input" rows="2" placeholder="${_t2('spoolman.notes_placeholder', 'Remarques...')}">${escapeHtml(existing?.notes || '')}</textarea>
                </div>
                <div class="input-group">
                    <label>${_t2('spoolman.storage_location', 'Rangement')}</label>
                    <input type="text" id="spool-inv-storage" class="form-input" list="spool-storage-suggestions" placeholder="${_t2('spoolman.storage_placeholder', 'ex: Étagère A3, Tiroir 2...')}" value="${escapeHtml(existing?.storage_location || '')}">
                    <datalist id="spool-storage-suggestions">
                        ${[...new Set(_manualSpoolCache.map(s => (s.storage_location || '').trim()).filter(Boolean))].map(l => `<option value="${escapeHtml(l)}">`).join('')}
                    </datalist>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-ghost" onclick="closeModal('modal-spool-inventory')">${_t2('actions.cancel', 'Annuler')}</button>
                <button class="btn btn-primary" onclick="saveSpoolInventoryEntry(${existing ? existing.id : 'null'})">
                    <i class="fa-solid fa-check"></i> ${_t2('actions.save', 'Enregistrer')}
                </button>
            </div>
        </div>`;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal('modal-spool-inventory'); });
    openModal('modal-spool-inventory');
}
window.openSpoolInventoryModal = openSpoolInventoryModal;

async function saveSpoolInventoryEntry(spoolId) {
    const name = document.getElementById('spool-inv-name')?.value.trim();
    if (!name) { showToast(_t2('spoolman.name_required', 'Le nom est requis'), 'error'); return; }
    const payload = {
        name,
        material: document.getElementById('spool-inv-material')?.value.trim() || '',
        color_hex: document.getElementById('spool-inv-color')?.value || '#888888',
        vendor: document.getElementById('spool-inv-vendor')?.value.trim() || '',
        remaining_g: parseFloat(document.getElementById('spool-inv-remaining')?.value) || null,
        capacity_g: parseFloat(document.getElementById('spool-inv-capacity')?.value) || 1000,
        price: parseFloat(document.getElementById('spool-inv-price')?.value) || null,
        diameter_mm: parseFloat(document.getElementById('spool-inv-diameter')?.value) || 1.75,
        notes: document.getElementById('spool-inv-notes')?.value.trim() || '',
        storage_location: document.getElementById('spool-inv-storage')?.value.trim() || '',
    };
    try {
        const url = spoolId ? `${API}/api/filament/manual/${spoolId}` : `${API}/api/filament/manual`;
        const method = spoolId ? 'PUT' : 'POST';
        const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || _t2('toast.error', 'Erreur'), 'error'); return; }
        closeModal('modal-spool-inventory');
        showToast(_t2('spoolman.spool_saved', 'Bobine enregistrée'), 'success');
        await loadManualSpoolInventory();
    } catch (err) {
        showToast(_t2('toast.connection_error', 'Erreur de connexion'), 'error');
    }
}
window.saveSpoolInventoryEntry = saveSpoolInventoryEntry;

async function toggleArchiveManualSpool(spoolId, archived) {
    try {
        await fetch(`${API}/api/filament/manual/${spoolId}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ archived: archived ? 1 : 0 })
        });
        await loadManualSpoolInventory();
    } catch (err) {
        showToast(_t2('toast.connection_error', 'Erreur de connexion'), 'error');
    }
}
window.toggleArchiveManualSpool = toggleArchiveManualSpool;

async function deleteManualSpoolFromInventory(spoolId) {
    const ok = await showConfirmDialog(_t2('spoolman.confirm_delete', 'Supprimer cette bobine de l\u2019inventaire ?'), { title: _t2('actions.delete', 'Supprimer') });
    if (!ok) return;
    try {
        const res = await fetch(`${API}/api/filament/manual/${spoolId}`, { method: 'DELETE' });
        if (!res.ok) { showToast(_t2('toast.error', 'Erreur'), 'error'); return; }
        showToast(_t2('spoolman.spool_deleted', 'Bobine supprimée'), 'success');
        await loadManualSpoolInventory();
    } catch (err) {
        showToast(_t2('toast.connection_error', 'Erreur de connexion'), 'error');
    }
}
window.deleteManualSpoolFromInventory = deleteManualSpoolFromInventory;

function renderSpoolmanGrid(spools) {
    const grid = document.getElementById('spoolman-grid');
    if (!grid) return;
    if (!spools.length) {
        grid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-circle-nodes"></i>
                <p>${_t2('spoolman.no_spools', 'Aucune bobine trouvée')}</p>
            </div>`;
        return;
    }
    grid.innerHTML = spools.map(s => {
        const filament = s.filament || {};
        const vendor = filament.vendor || {};
        const color = filament.color_hex ? `#${String(filament.color_hex).replace('#', '')}` : '#888888';
        const material = filament.material || '—';
        const name = filament.name || vendor.name || I18N.t('spoolman.spool');
        const vendorName = vendor.name || '';
        const remaining = typeof s.remaining_weight === 'number' ? s.remaining_weight : null;
        const initial = filament.weight || s.initial_weight || null;
        const pct = (remaining !== null && initial) ? Math.max(0, Math.min(100, (remaining / initial) * 100)) : null;
        const archived = !!s.archived;
        return `
            <div class="spool-card ${archived ? 'archived' : ''}">
                <div class="spool-card-header">
                    <span class="spool-color-dot" style="background:${color};"></span>
                    <div class="spool-title">
                        <span class="spool-name">${escapeHtml(name)}</span>
                        ${vendorName ? `<span class="spool-vendor">${escapeHtml(vendorName)}</span>` : ''}
                    </div>
                    ${archived ? `<span class="spool-badge">${I18N.t('spoolman.archived')}</span>` : ''}
                </div>
                <div class="spool-card-body">
                    <span class="spool-material-tag">${escapeHtml(material)}</span>
                    ${pct !== null ? `
                        <div class="spool-weight-row">
                            <span>${Math.round(remaining)} ${I18N.t('units.g_remaining')}</span>
                            <span>${Math.round(pct)}%</span>
                        </div>
                        <div class="spool-progress-track">
                            <div class="spool-progress-bar" style="width:${pct}%; background:${color};"></div>
                        </div>
                    ` : remaining !== null ? `<p class="spool-weight-row"><span>${Math.round(remaining)} ${I18N.t('units.g_remaining')}</span></p>` : ''}
                    ${s.location ? `<p class="spool-location"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(s.location)}</p>` : ''}
                </div>
            </div>`;
    }).join('');
}
window.renderSpoolmanGrid = renderSpoolmanGrid;


function updateAccountBadge(platform, connected) {
const badge = document.getElementById(`${platform}-status-badge`);
if (!badge) return;


const key = connected ? 'settings.account_configured' : 'settings.account_not_configured';
badge.setAttribute('data-i18n', key);
badge.textContent = I18N.t(key);
if (connected) {
badge.classList.remove('disconnected');
badge.classList.add('connected');
} else {
badge.classList.add('disconnected');
badge.classList.remove('connected');
}
}
function showAccountKeyConfigured(platform) {
const row = document.getElementById(`${platform}-key-row`);
const editBtn = document.getElementById(`${platform}-edit-btn`);
if (row) row.style.display = 'none';
if (editBtn) editBtn.style.display = 'inline-flex';
}
async function showAccountKeyInput(platform, focusInput = true) {
const row = document.getElementById(`${platform}-key-row`);
const editBtn = document.getElementById(`${platform}-edit-btn`);
if (row) row.style.display = 'flex';
if (editBtn) editBtn.style.display = 'none';

const inputId = 'thingiverse-api-key';
const input = document.getElementById(inputId);
if (input) {
    input.value = '';
    try {
        const res = await fetch(`${API}/api/accounts/${platform}/key`);
        if (res.ok) {
            const data = await res.json();
            if (data.api_key) input.value = data.api_key;
        }
    } catch (e) {  }
    if (focusInput) input.focus();
}
}
window.showAccountKeyInput = showAccountKeyInput;
async function saveAccountKey(platform) {
const inputId = 'thingiverse-api-key';
const input = document.getElementById(inputId);
const apiKey = input ? input.value.trim() : '';
if (!apiKey) { showToast(I18N.t('toast.api_key_required'), 'error'); return; }
try {
const res = await fetch(`${API}/api/accounts`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ platform, api_key: apiKey })
});
const data = await res.json().catch(() => ({}));
if (res.ok) {
showToast(data.message || I18N.t('toast.account_saved'), 'success');
updateAccountBadge(platform, true);
showAccountKeyConfigured(platform);
} else {
showToast(data.error || I18N.t('toast.save_error'), 'error');
}
} catch (err) {
console.error('[saveAccountKey]', err);
showToast(I18N.t('toast.network_error_backend'), 'error');
}
}
window.saveAccountKey = saveAccountKey;


let _makerWorldEmail = '';

async function makerWorldStep1() {
    const emailEl    = document.getElementById('makerworld-email');
    const passwordEl = document.getElementById('makerworld-password');
    const email    = emailEl    ? emailEl.value.trim()    : '';
    const password = passwordEl ? passwordEl.value.trim() : '';
    if (!email || !password) { showToast(I18N.t('toast.email_password_required'), 'warning'); return; }
    _makerWorldEmail = email;
    try {
        const r = await fetch(`${API}/api/accounts/makerworld/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await r.json().catch(() => ({}));
        if (data.needCode) {
            document.getElementById('makerworld-step1').style.display = 'none';
            document.getElementById('makerworld-step2').style.display = 'block';
            if (document.getElementById('makerworld-code')) document.getElementById('makerworld-code').focus();
            showToast(I18N.t('toast.code_sent'), 'info');
        } else if (data.success) {
            makerWorldOnConnected(email);
        } else {
            showToast(data.error || I18N.t('toast.login_failed'), 'error');
        }
    } catch (e) {
        showToast(I18N.t('toast.network_error'), 'error');
    }
}
window.makerWorldStep1 = makerWorldStep1;

async function makerWorldStep2() {
    const codeEl = document.getElementById('makerworld-code');
    const code = codeEl ? codeEl.value.trim() : '';
    if (!code) { showToast(I18N.t('toast.enter_code'), 'warning'); return; }
    try {
        const r = await fetch(`${API}/api/accounts/makerworld/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: _makerWorldEmail, code })
        });
        const data = await r.json().catch(() => ({}));
        if (data.success) {
            makerWorldOnConnected(_makerWorldEmail);
        } else {
            showToast(data.error || I18N.t('toast.invalid_code'), 'error');
        }
    } catch (e) {
        showToast(I18N.t('toast.network_error'), 'error');
    }
}
window.makerWorldStep2 = makerWorldStep2;

function makerWorldReset() {
    const step2 = document.getElementById('makerworld-step2');
    const step1 = document.getElementById('makerworld-step1');
    if (step2) step2.style.display = 'none';
    if (step1) step1.style.display = 'block';
    const codeEl = document.getElementById('makerworld-code');
    if (codeEl) codeEl.value = '';
}
window.makerWorldReset = makerWorldReset;

function makerWorldShowLogin() {
    const cr = document.getElementById('makerworld-connected-row');
    const step1 = document.getElementById('makerworld-step1');
    if (cr) cr.style.display = 'none';
    if (step1) step1.style.display = 'block';
}
window.makerWorldShowLogin = makerWorldShowLogin;

function makerWorldOnConnected(email) {
    updateAccountBadge('makerworld', true);
    const emailDisplay = document.getElementById('makerworld-email-display');
    if (emailDisplay) emailDisplay.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${I18N.t('status.connected_email', { email })}`;
    const step1 = document.getElementById('makerworld-step1');
    const step2 = document.getElementById('makerworld-step2');
    const cr    = document.getElementById('makerworld-connected-row');
    if (step1) step1.style.display = 'none';
    if (step2) step2.style.display = 'none';
    if (cr)    cr.style.display    = 'block';
    const pwEl = document.getElementById('makerworld-password');
    const codeEl = document.getElementById('makerworld-code');
    if (pwEl)   pwEl.value   = '';
    if (codeEl) codeEl.value = '';
    showToast(I18N.t('toast.makerworld_connected'), 'success');
}

async function makerWorldDisconnect() {
    try {
        await fetch(`${API}/api/accounts/makerworld/disconnect`, { method: 'DELETE' });
        updateAccountBadge('makerworld', false);
        const cr    = document.getElementById('makerworld-connected-row');
        const step1 = document.getElementById('makerworld-step1');
        const emailEl = document.getElementById('makerworld-email');
        if (cr)    cr.style.display    = 'none';
        if (step1) step1.style.display = 'block';
        if (emailEl) emailEl.value = '';
        showToast(I18N.t('toast.makerworld_removed'), 'info');
    } catch (e) {
        showToast(I18N.t('toast.disconnect_error'), 'error');
    }
}
window.makerWorldDisconnect = makerWorldDisconnect;
async function loadAccountBadges() {
for (const platform of ['thingiverse']) {
try {
const res = await fetch(`${API}/api/accounts/${platform}`);
if (res.status === 401) continue;
updateAccountBadge(platform, res.ok);
if (res.ok) showAccountKeyConfigured(platform);
else showAccountKeyInput(platform, false);
} catch (e) {
updateAccountBadge(platform, false);
}
}
try {
    const res = await fetch(`${API}/api/accounts/status`);
    if (res.ok) {
        const status = await res.json();
        if (status.makerworld) {
            updateAccountBadge('makerworld', true);
            const emailDisplay = document.getElementById('makerworld-email-display');
            if (emailDisplay && status.makerworld_email) {
                emailDisplay.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${I18N.t('status.connected_email', { email: status.makerworld_email })}`;
            }
            const step1 = document.getElementById('makerworld-step1');
            const step2 = document.getElementById('makerworld-step2');
            const cr = document.getElementById('makerworld-connected-row');
            if (step1) step1.style.display = 'none';
            if (step2) step2.style.display = 'none';
            if (cr) cr.style.display = 'block';
        }
    }
} catch (e) {  }
}


let draggedNavRow = null;
function setupNavDragAndDrop() {
const list = document.getElementById('nav-toggle-list');
if (!list || list.dataset.dndInit) return;
list.dataset.dndInit = 'true';
list.querySelectorAll('.nav-toggle-row').forEach(row => {
row.addEventListener('dragstart', () => {
draggedNavRow = row;
row.classList.add('dragging');
});
row.addEventListener('dragend', () => {
row.classList.remove('dragging');
list.querySelectorAll('.nav-toggle-row').forEach(r => r.classList.remove('drag-over-top', 'drag-over-bottom'));
draggedNavRow = null;
});
row.addEventListener('dragover', (e) => {
e.preventDefault();
if (!draggedNavRow || draggedNavRow === row) return;
const rect = row.getBoundingClientRect();
const isAfter = (e.clientY - rect.top) > rect.height / 2;
row.classList.toggle('drag-over-bottom', isAfter);
row.classList.toggle('drag-over-top', !isAfter);
});
row.addEventListener('dragleave', () => {
row.classList.remove('drag-over-top', 'drag-over-bottom');
});
row.addEventListener('drop', (e) => {
e.preventDefault();
row.classList.remove('drag-over-top', 'drag-over-bottom');
if (!draggedNavRow || draggedNavRow === row) return;
const rect = row.getBoundingClientRect();
const isAfter = (e.clientY - rect.top) > rect.height / 2;
if (isAfter) row.after(draggedNavRow);
else row.before(draggedNavRow);
onNavOrderChanged();
});
});
}
function getNavOrderFromList() {
return Array.from(document.querySelectorAll('#nav-toggle-list .nav-toggle-row')).map(r => r.dataset.navId);
}
function applyNavOrderToSidebar(order) {
const container = document.getElementById('reorderable-nav-items');
if (!container) return;
order.forEach(navId => {
const btn = container.querySelector(`[data-nav-id="${navId}"]`);
if (btn) container.appendChild(btn);
});
}
function applyNavOrderToList(order) {
const list = document.getElementById('nav-toggle-list');
if (!list) return;
order.forEach(navId => {
const row = list.querySelector(`.nav-toggle-row[data-nav-id="${navId}"]`);
if (row) list.appendChild(row);
});
}
async function onNavOrderChanged() {
const order = getNavOrderFromList();
applyNavOrderToSidebar(order);
localStorage.setItem('stellio-nav-order', JSON.stringify(order));
try {
await fetch(`${API}/api/settings`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ nav_order: order })
});
} catch (err) {
console.warn('[NavOrder] Échec de la sauvegarde:', err);
}
}
async function loadNavOrder() {
let order = null;
try {
const res = await fetch(`${API}/api/settings`);
if (res.ok) {
const data = await res.json();
if (Array.isArray(data.nav_order) && data.nav_order.length) order = data.nav_order;
}
} catch (e) {  }
if (!order) {
try {
const stored = localStorage.getItem('stellio-nav-order');
if (stored) order = JSON.parse(stored);
} catch (e) {  }
}
if (Array.isArray(order) && order.length) {
applyNavOrderToList(order);
applyNavOrderToSidebar(order);
}
setupNavDragAndDrop();
}


function setupEventListeners() {
document.getElementById('reg-security-question')?.addEventListener('change', (e) => {
    document.getElementById('reg-security-question-custom-group')?.classList.toggle('hidden', e.target.value !== 'custom');
    document.getElementById('reg-security-answer-group')?.classList.toggle('hidden', !e.target.value);
});

document.getElementById('register-form')?.addEventListener('submit', async (e) => {
e.preventDefault();
const username = document.getElementById('reg-username').value.trim();
const password = document.getElementById('reg-password').value;
const confirm = document.getElementById('reg-password-confirm').value;
const security_question_key = document.getElementById('reg-security-question').value;
const security_question_custom = document.getElementById('reg-security-question-custom').value.trim();
const security_answer = document.getElementById('reg-security-answer').value;
if (password !== confirm) { showToast(I18N.t('toast.password_mismatch'), 'error'); return; }
if (password.length < 3) { showToast(I18N.t('toast.password_short'), 'error'); return; }
if (security_question_key === 'custom' && !security_question_custom) { showToast(I18N.t('toast.security_question_required'), 'error'); return; }
if (!security_answer.trim()) { showToast(I18N.t('toast.security_answer_required'), 'error'); return; }
try {
const res = await fetch(`${API}/api/auth/register`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password, security_question_key, security_question_custom, security_answer }) });
const data = await res.json();
if (res.ok) {
showToast(I18N.t('toast.account_created'), 'success');
showRecoveryCodeModal(data.recovery_code, () => showApp(data.user));
}
else showToast(data.error, 'error');
} catch (err) { showToast(I18N.t('toast.server_error'), 'error'); }
});
document.getElementById('login-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const remember = document.getElementById('login-remember')?.checked ?? true;
    try {
        const res = await fetch(`${API}/api/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password, remember }) });
        const data = await res.json();
        if (res.ok) {
            if (remember) {
                try { localStorage.setItem(REMEMBER_LOGIN_KEY, JSON.stringify({ username, password: _b64encodeUtf8(password) })); } catch (err) {}
            } else {
                localStorage.removeItem(REMEMBER_LOGIN_KEY);
            }
            showToast(I18N.t('toast.logged_in'), 'success'); showApp(data.user);
        }
        else showToast(data.error, 'error');
    } catch (err) { showToast(I18N.t('toast.connection_error'), 'error'); }
});

document.getElementById('show-register')?.addEventListener('click', (e) => { e.preventDefault(); showPanel('register-panel'); });
document.getElementById('show-forgot')?.addEventListener('click', (e) => { e.preventDefault(); showPanel('forgot-panel'); });

const SECURITY_QUESTION_LABELS = {
    pet: 'auth.security_q_pet',
    city: 'auth.security_q_city',
    school: 'auth.security_q_school',
    nickname: 'auth.security_q_nickname'
};
async function loadSecurityQuestionFor(username, displayEl) {
    if (!username) {
        displayEl.classList.add('hidden');
        return;
    }
    try {
        const res = await fetch(`${API}/api/auth/security-question?username=${encodeURIComponent(username)}`);
        const data = await res.json();
        if (res.ok) {
            const text = data.security_question_key === 'custom'
                ? data.security_question_custom
                : I18N.t(SECURITY_QUESTION_LABELS[data.security_question_key] || '');
            displayEl.textContent = text;
            displayEl.classList.remove('hidden');
        } else {
            displayEl.textContent = I18N.t('auth.security_question_load_error') || 'Impossible de charger la question secrète.';
            displayEl.classList.remove('hidden');
        }
    } catch (err) {
        displayEl.textContent = I18N.t('auth.security_question_load_error') || 'Impossible de charger la question secrète.';
        displayEl.classList.remove('hidden');
    }
}
document.getElementById('forgot-username')?.addEventListener('blur', (e) => {
    loadSecurityQuestionFor(e.target.value.trim(), document.getElementById('forgot-security-question-display'));
});

document.getElementById('forgot-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('forgot-username').value.trim();
    const recovery_code = document.getElementById('forgot-recovery-code').value.trim().toUpperCase();
    const security_answer = document.getElementById('forgot-security-answer').value;
    const password = document.getElementById('forgot-new-password').value;
    const confirm = document.getElementById('forgot-new-password-confirm').value;
    if (password !== confirm) { showToast(I18N.t('toast.password_mismatch'), 'error'); return; }
    if (password.length < 3) { showToast(I18N.t('toast.password_short'), 'error'); return; }
    const btn = e.target.querySelector('button[type="submit"]');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
    try {
        const res = await fetch(`${API}/api/auth/reset-with-recovery`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, recovery_code, security_answer, password }) });
        const data = await res.json();
        if (res.ok) {
            showToast(I18N.t('toast.password_reset'), 'success');
            document.getElementById('forgot-form').reset();
            document.getElementById('forgot-security-question-display')?.classList.add('hidden');
            showRecoveryCodeModal(data.recovery_code, () => showPanel('login-panel'));
        } else showToast(data.error, 'error');
    } catch (err) { showToast(I18N.t('toast.network_error'), 'error'); }
    finally { btn.disabled = false; btn.innerHTML = originalText; }
});

document.getElementById('regenerate-recovery-code-btn')?.addEventListener('click', async () => {
    const answerInput = document.getElementById('regenerate-confirm-answer');
    const questionEl = document.getElementById('regenerate-confirm-question');
    const username = document.getElementById('current-username')?.textContent?.trim();
    answerInput.value = '';
    questionEl.textContent = '';
    openModal('regenerate-confirm-modal');
    if (username) await loadSecurityQuestionFor(username, questionEl);
    answerInput.focus();
});

document.getElementById('regenerate-confirm-submit-btn')?.addEventListener('click', async () => {
    const security_answer = document.getElementById('regenerate-confirm-answer').value;
    const btn = document.getElementById('regenerate-confirm-submit-btn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
    try {
        const res = await fetch(`${API}/api/auth/recovery-code/regenerate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ security_answer }) });
        const data = await res.json();
        if (res.ok) {
            closeModal('regenerate-confirm-modal');
            showRecoveryCodeModal(data.recovery_code, null);
        } else showToast(data.error, 'error');
    } catch (err) { showToast(I18N.t('toast.network_error'), 'error'); }
    finally { btn.disabled = false; btn.innerHTML = originalText; }
});

function showRecoveryCodeModal(code, onContinue) {
    const display = document.getElementById('recovery-code-display');
    const ack = document.getElementById('recovery-code-ack');
    const continueBtn = document.getElementById('recovery-code-continue-btn');
    const copyBtn = document.getElementById('recovery-code-copy-btn');
    if (!display || !continueBtn) return;

    display.textContent = code;
    ack.checked = false;
    continueBtn.disabled = true;

    const onAckChange = () => { continueBtn.disabled = !ack.checked; };
    ack.onchange = onAckChange;

    copyBtn.onclick = async () => {
        try {
            await navigator.clipboard.writeText(code);
            showToast(I18N.t('toast.copied'), 'success');
        } catch (err) {
            display.focus();
            document.execCommand && document.execCommand('copy');
        }
    };

    continueBtn.onclick = () => {
        closeModal('recovery-code-modal');
        if (typeof onContinue === 'function') onContinue();
    };

    openModal('recovery-code-modal');
}

document.getElementById('global-logout-btn')?.addEventListener('click', async () => {
    await fetch(`${API}/api/auth/logout`, { method: 'POST' });
    location.reload();
});

document.getElementById('default-slicer-select')?.addEventListener('change', async (e) => {
    try {
        await fetch(`${API}/api/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ default_slicer: e.target.value }) });
        showToast(I18N.t('toast.slicer_updated'), 'success');
    } catch (err) { showToast(I18N.t('toast.error'), 'error'); }
});

document.getElementById('preferred-slicer-select')?.addEventListener('change', async (e) => {
    try {
        await fetch(`${API}/api/settings`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ preferred_slicer_id: e.target.value }) });
        showToast(I18N.t('toast.slicer_updated'), 'success');
    } catch (err) { showToast(I18N.t('toast.error'), 'error'); }
});


function updateHeaderVisibilityForPage(page) {
    const isLibrary = page === 'library';
    const isSpoolman = page === 'spoolman';

    const headerCenter = document.querySelector('.header-center');
    if (headerCenter) headerCenter.classList.toggle('header-hide', !isLibrary && !isSpoolman);

    const libraryOnlyEls = [
        document.getElementById('library-search-wrap'),
        document.getElementById('mobile-search-toggle'),
        document.getElementById('sort-select'),
        document.querySelector('.view-modes'),
        document.getElementById('refresh-files'),
        document.getElementById('select-all-btn'),
        document.querySelector('.header-library-info')
    ];
    libraryOnlyEls.forEach(el => {
        if (!el) return;
        el.classList.toggle('header-hide', !isLibrary);
    });

    const spoolmanOnlyEls = [
        document.getElementById('spool-header-search-wrap'),
        document.getElementById('spool-header-material'),
        document.getElementById('spool-header-location'),
        document.getElementById('spool-header-sort')
    ];
    spoolmanOnlyEls.forEach(el => {
        if (!el) return;
        el.classList.toggle('header-hide', !isSpoolman);
    });
}
window.updateHeaderVisibilityForPage = updateHeaderVisibilityForPage;

function resetGlobalSearch() {
    const hadQuery = !!(globalSearchInput?.value || mobileSearchInput?.value);
    if (globalSearchInput) globalSearchInput.value = '';
    if (mobileSearchInput) mobileSearchInput.value = '';
    if (hadQuery && typeof handleSearchInput === 'function') {
        handleSearchInput('', null);
    }
}
window.resetGlobalSearch = resetGlobalSearch;

document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const page = btn.dataset.page;
        if (btn.id === 'nav-favorites-btn') { toggleFavoritesFilterFromNav(); return; }
        if (page === 'library') {
            if (showFavoritesOnly) {
                showFavoritesOnly = false;
                document.getElementById('nav-favorites-btn')?.classList.remove('active');
                document.getElementById('favorites-filter-btn')?.classList.remove('active');
                const headerTitle = document.getElementById('header-page-title');
                if (headerTitle) headerTitle.innerHTML = `<i class="fa-solid fa-layer-group"></i> ${I18N.t('nav.library')}`;
            }
            document.querySelector('.nav-btn[data-page="library"]')?.classList.add('active');
        } else {
            resetGlobalSearch();
        }
        if (btn.innerHTML.includes('fa-filter')) { openFiltersModal(); return; }
        if (!page) return;
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`page-${page}`)?.classList.add('active');
        const titleKey = btn.dataset.titleKey || 'app.title';
        document.getElementById('header-page-title').innerHTML = `<i class="fa-solid ${btn.dataset.icon || 'fa-layer-group'}"></i> ${I18N.t(titleKey)}`;
        updateHeaderVisibilityForPage(page);
        if (page === 'library') loadFiles();
        if (page === 'printers') loadPrinters();
        if (page === 'settings') { loadSources(); loadRemoteInstances(); }
        else stopDiagnosticConsolePoll();
        if (page === 'spoolman') loadSpoolmanPage();
        if (page === 'stats') loadStats();
        if (page === 'history') { loadHistory(); loadDownloadHistory(); }
        if (page === 'gallery') loadGalleryPage();
        if (page === 'projects') loadProjects();
        closeMobileSidebar();
    });
});


function openMobileSidebar() {
    document.getElementById('app-sidebar')?.classList.add('mobile-open');
    document.getElementById('sidebar-overlay')?.classList.add('visible');
}

function closeMobileSidebar() {
    document.getElementById('app-sidebar')?.classList.remove('mobile-open');
    document.getElementById('sidebar-overlay')?.classList.remove('visible');
}

function toggleMobileSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    if (sidebar?.classList.contains('mobile-open')) {
        closeMobileSidebar();
    } else {
        openMobileSidebar();
    }
}

document.getElementById('mobile-menu-toggle')?.addEventListener('click', toggleMobileSidebar);
document.getElementById('sidebar-overlay')?.addEventListener('click', closeMobileSidebar);

document.getElementById('nav-favorites-btn')?.addEventListener('click', closeMobileSidebar);
document.querySelector('.nav-btn[data-nav-id="filters"]')?.addEventListener('click', closeMobileSidebar);

window.addEventListener('resize', () => {
    if (window.innerWidth > 860) closeMobileSidebar();
});

document.querySelectorAll('.view-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentView = btn.dataset.view;
        document.getElementById('files-grid').className = `files-grid ${currentView}`;
        renderFiles();
    });
});

document.getElementById('select-all-btn')?.addEventListener('click', () => toggleSelectionMode());
document.getElementById('select-toggle-all')?.addEventListener('click', () => selectAllFiles());
document.getElementById('send-selected-to-slicer-btn')?.addEventListener('click', () => sendSelectedToSlicer());
document.getElementById('nesting-btn')?.addEventListener('click', () => openNestingModal());
document.getElementById('add-selected-to-project-btn')?.addEventListener('click', () => openSelectionProjectModal());
document.getElementById('slicer-profile-file-input')?.addEventListener('change', (e) => {
    openSlicerImportAssignModal(e.target.files);
    e.target.value = '';
});
document.getElementById('confirm-slicer-import-assign')?.addEventListener('click', () => confirmSlicerImportAssign());
document.getElementById('cancel-selection-btn')?.addEventListener('click', () => toggleSelectionMode());
document.getElementById('regen-selected-thumbs-btn')?.addEventListener('click', () => regenSelectedThumbnails());
document.getElementById('delete-selected-btn')?.addEventListener('click', () => deleteSelectedFiles());


(function initDragDropSources() {
    const dropZone = document.querySelector('.main-content');
    if (!dropZone) return;
    let dragCounter = 0;

    dropZone.addEventListener('dragenter', (e) => {
        e.preventDefault();
        dragCounter++;
        dropZone.classList.add('drop-zone-active');
    });
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
    });
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dragCounter = Math.max(0, dragCounter - 1);
        if (dragCounter === 0) dropZone.classList.remove('drop-zone-active');
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dragCounter = 0;
        dropZone.classList.remove('drop-zone-active');
    });
})();

window.__stellioHandleDroppedPaths = async function (paths) {
    if (!paths || !paths.length) return;
    if (!document.getElementById('modal-print-photos')?.classList.contains('hidden')) return;
    showToast(I18N.t('toast.drop_processing', { count: paths.length }) || `Ajout de ${paths.length} élément(s)...`, 'info');
    try {
        const res = await fetch(`${API}/api/sources/drop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paths })
        });
        const data = await res.json();
        if (!res.ok) {
            showToast(data.error || I18N.t('toast.connection_error'), 'error');
            return;
        }
        const addedCount = data.added?.length || 0;
        const skippedCount = data.skipped?.length || 0;
        if (addedCount) {
            showToast(
                I18N.t('toast.drop_added', { count: addedCount }) || `${addedCount} source(s) ajoutée(s)`,
                'success'
            );
            await loadSources?.();
            await loadFiles?.();
        }
        if (skippedCount) {
            console.warn('[DragDrop] Éléments ignorés:', data.skipped);
            showToast(
                I18N.t('toast.drop_skipped', { count: skippedCount }) || `${skippedCount} élément(s) ignoré(s) (voir console)`,
                addedCount ? 'info' : 'error'
            );
        }
    } catch (err) {
        console.error('[DragDrop] Erreur', err);
        showToast(I18N.t('toast.connection_error'), 'error');
    }
};

document.getElementById('add-source-btn')?.addEventListener('click', () => openModal('modal-select-type'));
document.querySelectorAll('.type-card').forEach(card => {
    card.addEventListener('click', async () => {
        const type = card.dataset.type;
        closeModal('modal-select-type');
        if (type === 'folder' || type === 'file') {
            if (stellioAppConfig.headless) openLocalManualModal(type);
            else await handleFilePicker(type);
        }
        else if (type === 'smb') {
            document.getElementById('smb-form')?.reset();
            document.getElementById('smb-name').value = '';
            if (document.getElementById('add-smb-btn')) document.getElementById('add-smb-btn').disabled = true;
            openModal('modal-smb');
        } else if (type === 'nfs') {
            document.getElementById('nfs-form')?.reset();
            document.getElementById('nfs-name').value = '';
            if (document.getElementById('add-nfs-btn')) document.getElementById('add-nfs-btn').disabled = true;
            openModal('modal-nfs');
        }
    });
});

document.getElementById('rename-source-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('rename-source-id').value;
    const newName = document.getElementById('rename-source-name').value.trim();
    if (!newName) { showToast(I18N.t('toast.rename_empty'), 'error'); return; }
    try {
        const res = await fetch(`${API}/api/sources/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: newName }) });
        const data = await res.json();
        if (res.ok) { showToast(I18N.t('toast.source_renamed'), 'success'); closeModal('modal-rename-source'); loadSources(); }
        else showToast(data.error || I18N.t('toast.error'), 'error');
    } catch (err) { showToast(I18N.t('toast.fetch_error'), 'error'); }
});

const addSmbBtn = document.getElementById('add-smb-btn');
const addNfsBtn = document.getElementById('add-nfs-btn');
['smb-host', 'smb-share', 'smb-user', 'smb-pass'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', () => { if (addSmbBtn) addSmbBtn.disabled = true; });
});
['nfs-host', 'nfs-path'].forEach(id => {
    document.getElementById(id)?.addEventListener('input', () => { if (addNfsBtn) addNfsBtn.disabled = true; });
});

document.getElementById('smb-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (addSmbBtn?.disabled) { showToast(I18N.t('toast.test_required'), 'warning'); return; }
    const name = document.getElementById('smb-name').value.trim();
    const host = document.getElementById('smb-host').value.trim();
    const share = document.getElementById('smb-share').value.trim();
    const username = document.getElementById('smb-user').value.trim();
    const password = document.getElementById('smb-pass').value;
    if (await addSource('smb', name, `\\\\${host}\\${share}`, { username, password, type: 'smb' })) {
        showToast(I18N.t('toast.source_added'), 'success');
        closeModal('modal-smb');
        loadSources();
        loadFiles();
    }
});

document.getElementById('nfs-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (addNfsBtn?.disabled) { showToast(I18N.t('toast.test_required'), 'warning'); return; }
    const data = { name: document.getElementById('nfs-name').value.trim(), host: document.getElementById('nfs-host').value.trim(), path: document.getElementById('nfs-path').value.trim() };
    if (await addSource('nfs', data.name, `${data.host}:${data.path}`, data)) {
        showToast(I18N.t('toast.source_added'), 'success');
        closeModal('modal-nfs');
        loadSources();
    }
});

document.getElementById('test-smb-btn')?.addEventListener('click', async () => {
    const host = document.getElementById('smb-host').value.trim();
    const share = document.getElementById('smb-share').value.trim();
    const username = document.getElementById('smb-user').value.trim();
    const password = document.getElementById('smb-pass').value;
    const resultDiv = document.getElementById('smb-test-result');
    const btn = document.getElementById('test-smb-btn');
    if (!host || !share) { resultDiv.innerHTML = `<span style="color: var(--warning)"><i class="fa-solid fa-exclamation-triangle"></i> ${I18N.t('toast.fill_required')}</span>`; return; }
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t('toast.refreshing')}`;
    resultDiv.innerHTML = '';
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);
    try {
        const res = await fetch(`${API}/api/test-connection`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'smb', host, share, username, password }), signal: controller.signal });
        const data = await res.json();
        if (res.ok) { resultDiv.innerHTML = `<span style="color: var(--success)"><i class="fa-solid fa-check-circle"></i> ${data.message}</span>`; if (addSmbBtn) addSmbBtn.disabled = false; }
        else { resultDiv.innerHTML = `<span style="color: var(--danger)"><i class="fa-solid fa-times-circle"></i> ${data.error}</span>`; if (addSmbBtn) addSmbBtn.disabled = true; }
    } catch (err) {
        const msg = err.name === 'AbortError' ? I18N.t('toast.timeout_unreachable') : I18N.t('toast.connection_error');
        resultDiv.innerHTML = `<span style="color: var(--danger)"><i class="fa-solid fa-times-circle"></i> ${msg}</span>`;
        if (addSmbBtn) addSmbBtn.disabled = true;
    }
    finally { clearTimeout(timeoutId); btn.disabled = false; btn.innerHTML = `<i class="fa-solid fa-plug"></i> ${I18N.t('actions.test_connection')}`; }
});

document.getElementById('test-nfs-btn')?.addEventListener('click', async () => {
    const host = document.getElementById('nfs-host').value.trim();
    const path = document.getElementById('nfs-path').value.trim();
    const resultDiv = document.getElementById('nfs-test-result');
    const btn = document.getElementById('test-nfs-btn');
    if (!host || !path) { resultDiv.innerHTML = `<span style="color: var(--warning)"><i class="fa-solid fa-exclamation-triangle"></i> ${I18N.t('toast.fill_nfs')}</span>`; return; }
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t('toast.refreshing')}`;
    resultDiv.innerHTML = '';
    try {
        const res = await fetch(`${API}/api/test-connection`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'nfs', host, path }) });
        const data = await res.json();
        if (res.ok) { resultDiv.innerHTML = `<span style="color: var(--success)"><i class="fa-solid fa-check-circle"></i> ${data.message}</span>`; if (addNfsBtn) addNfsBtn.disabled = false; }
        else { resultDiv.innerHTML = `<span style="color: var(--danger)"><i class="fa-solid fa-times-circle"></i> ${data.error}</span>`; if (addNfsBtn) addNfsBtn.disabled = true; }
    } catch (err) { resultDiv.innerHTML = `<span style="color: var(--danger)"><i class="fa-solid fa-times-circle"></i> ${I18N.t('toast.connection_error')}</span>`; if (addNfsBtn) addNfsBtn.disabled = true; }
    finally { btn.disabled = false; btn.innerHTML = `<i class="fa-solid fa-plug"></i> ${I18N.t('actions.test_connection')}`; }
});

async function handleFilePicker(type) {
    const url = type === 'folder' ? `${API}/api/picker/folder` : `${API}/api/picker/file`;
    try {
        showToast(I18N.t('toast.refreshing'), 'info');
        const res = await fetch(url, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) {
            const errorMsg = data.error || I18N.t('actions.cancel');
            if (errorMsg.includes('tkinter')) showToast(I18N.t('toast.explorer_unavailable'), 'warning');
            else if (errorMsg === I18N.t('actions.cancel')) showToast(I18N.t('toast.selection_cancelled_user'), 'info');
            else showToast(`❌ ${errorMsg}`, 'error');
            return;
        }
        let success = false;
        if (type === 'folder' && data.path) {
            const folderName = data.path.split('/').pop() || I18N.t('source.local_folder');
            success = await addSource('folder', folderName, data.path, {});
            if (success) showToast(`📁 ${I18N.t('source.local_folder')} "${folderName}" ${I18N.t('toast.source_added').toLowerCase()}`, 'success');
        } else if (type === 'file' && data.paths?.length) {
            if (data.paths.length === 1) {
                success = await addSource('file', data.paths[0].split('/').pop(), data.paths[0], {});
                if (success) showToast(I18N.t('toast.source_added'), 'success');
            } else {
                for (const p of data.paths) await addSource('file', p.split('/').pop(), p, {});
                showToast(`✅ ${data.paths.length} ${I18N.t('toast.source_added')}`, 'success');
                success = true;
            }
        }
        if (success) { loadSources(); loadFiles(); }
    } catch (err) { showToast(I18N.t('toast.picker_error'), 'error'); console.error('[handleFilePicker]', err); }
}

document.getElementById('refresh-files')?.addEventListener('click', () => { loadFiles(); showToast(I18N.t('toast.refreshing'), 'info'); });


const SEMANTIC_INTENT_WORDS = [
    'je cherche', 'trouver', 'quelque chose', 'un truc', 'un objet', 'une pièce',
    'pour ranger', 'pour fixer', 'pour accrocher', 'pour réparer', 'pour organiser',
    'pour imprimer', 'qui sert', 'qui permet', 'capable de', 'genre', 'type de',
    'ressemblant', 'similaire', 'comme un', 'comme une', 'afin de',
    'cherche', 'besoin', 'veux', 'voudrais', 'support', 'boîtier', 'rangement',
    'fixation', 'protection', 'holder', 'peut-on', 'a-t-on',
];

let semanticSearchTimeout = null;
let lastSemanticQuery     = '';
let isSemanticMode        = false;

function isSemanticQuery(query) {
    if (!query || query.length < 6) return false;
    const q = query.toLowerCase();
    const wordCount = q.trim().split(/\s+/).length;
    if (wordCount >= 4) return true;
    return SEMANTIC_INTENT_WORDS.some(w => q.includes(w));
}

function setSearchMode(mode) {
    const boxes = document.querySelectorAll('.search-box');
    const hint = document.getElementById('semantic-search-hint');
    const mobileHint = document.getElementById('mobile-semantic-search-hint');
    if (mode === 'semantic') {
        isSemanticMode = true;
        boxes.forEach(box => {
            box.classList.add('semantic-active');
            const icon = box.querySelector('i');
            if (icon) { icon.className = 'fa-solid fa-wand-magic-sparkles'; icon.style.color = 'var(--accent)'; }
        });
        if (hint) hint.style.display = 'flex';
        if (mobileHint) mobileHint.style.display = 'flex';
    } else {
        isSemanticMode = false;
        boxes.forEach(box => {
            box.classList.remove('semantic-active');
            const icon = box.querySelector('i');
            if (icon) { icon.className = 'fa-solid fa-search'; icon.style.color = ''; }
        });
        if (hint) hint.style.display = 'none';
        if (mobileHint) mobileHint.style.display = 'none';
    }
}

async function runSemanticSearch(query) {
    if (query === lastSemanticQuery) return;
    lastSemanticQuery = query;
    const boxes = document.querySelectorAll('.search-box');
    boxes.forEach(box => box.classList.add('semantic-loading'));
    try {
        const res = await fetch(`${API}/api/ollama/semantic-search`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({
                query,
                files: allFiles.map(f => ({
                    path:   f.path,
                    name:   f.name,
                    tags:   f.tags || [],
                    source: f.source || ''
                }))
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Erreur Ollama');

        const resultSet = new Set(data.results || []);
        if (resultSet.size === 0) {
            showToast(I18N.t('toast.no_match_found'), 'info');
            return;
        }

        const ordered = (data.results || []).filter(p => resultSet.has(p));
        filteredFiles = ordered.map(p => allFiles.find(f => f.path === p)).filter(Boolean);

        if (typeof activeTagFilters !== 'undefined' && activeTagFilters.size > 0) {
            filteredFiles = filteredFiles.filter(f => {
                const ft = new Set((f.tags || []).map(t => t.name.toLowerCase()));
                for (const tag of activeTagFilters) { if (!ft.has(tag.toLowerCase())) return false; }
                return true;
            });
        }
        if (typeof showFavoritesOnly !== 'undefined' && showFavoritesOnly) {
            filteredFiles = filteredFiles.filter(f => favoriteFiles.has(f.path));
        }

        applySorting();
        renderFiles();
        updateSidebarCounts(filteredFiles);

        if (data.fallback) {
            showToast(I18N.t('toast.ollama_slow_fallback'), 'warning');
        }
    } catch (err) {
        console.error('[SemanticSearch]', err);
        const q = query.toLowerCase();
        filteredFiles = allFiles.filter(f =>
            f.name.toLowerCase().includes(q) ||
            (f.tags || []).some(t => t.name.toLowerCase().includes(q))
        );
        applySorting();
        renderFiles();
        updateSidebarCounts(filteredFiles);
        showToast(I18N.t('toast.ai_unavailable_fallback'), 'warning');
    } finally {
        boxes.forEach(box => box.classList.remove('semantic-loading'));
    }
}

function handleSearchInput(query, sourceInput) {
    const trimmed = query.trim();
    clearTimeout(semanticSearchTimeout);

    [globalSearchInput, mobileSearchInput].forEach(input => {
        if (input && input !== sourceInput && input.value !== query) {
            input.value = query;
        }
    });

    if (!trimmed) {
        setSearchMode('normal');
        lastSemanticQuery = '';
        filteredFiles = (typeof showFavoritesOnly !== 'undefined' && showFavoritesOnly)
            ? allFiles.filter(f => favoriteFiles.has(f.path))
            : [...allFiles];
        applySorting();
        renderFiles();
        updateSidebarCounts(filteredFiles);
        return;
    }

    const q = trimmed.toLowerCase();
    filteredFiles = allFiles.filter(f =>
        f.name.toLowerCase().includes(q) ||
        f.path.toLowerCase().includes(q) ||
        (f.tags || []).some(t => t.name.toLowerCase().includes(q))
    );
    applySorting();
    renderFiles();
    updateSidebarCounts(filteredFiles);

    if (isSemanticQuery(trimmed) && window.aiEnabled) {
        setSearchMode('semantic');
        semanticSearchTimeout = setTimeout(() => runSemanticSearch(trimmed), 900);
    } else {
        setSearchMode('normal');
    }
}

const globalSearchInput = document.getElementById('global-search');
const mobileSearchInput = document.getElementById('mobile-search-input');

globalSearchInput?.addEventListener('input', (e) => handleSearchInput(e.target.value, e.target));
mobileSearchInput?.addEventListener('input', (e) => handleSearchInput(e.target.value, e.target));


function clearSearchInput(input) {
    if (!input) return;
    input.value = '';
    handleSearchInput('', input);
    input.focus();
}
document.getElementById('global-search-clear')?.addEventListener('click', () => clearSearchInput(globalSearchInput));
document.getElementById('mobile-search-clear')?.addEventListener('click', () => clearSearchInput(mobileSearchInput));

window.runSemanticSearch = runSemanticSearch;
window.setSearchMode     = setSearchMode;


function openMobileSearch() {
    document.getElementById('mobile-search-overlay')?.classList.add('open');
    setTimeout(() => mobileSearchInput?.focus(), 50);
}

function closeMobileSearch() {
    document.getElementById('mobile-search-overlay')?.classList.remove('open');
}

document.getElementById('mobile-search-toggle')?.addEventListener('click', openMobileSearch);
document.getElementById('mobile-search-close')?.addEventListener('click', closeMobileSearch);


function toggleNavItem(navId, visible) {
    try {
        const navBtn = document.querySelector(
            `.nav-btn[data-page="${navId}"], .nav-btn[data-nav-id="${navId}"]`
        );
        if (navBtn) {
            navBtn.style.display = visible ? '' : 'none';
        }
        const prefs = JSON.parse(localStorage.getItem('stellio-nav-prefs') || '{}');
        prefs[navId] = visible;
        localStorage.setItem('stellio-nav-prefs', JSON.stringify(prefs));
    } catch (err) {
        console.warn('[toggleNavItem] Erreur:', err);
    }
}
window.toggleNavItem = toggleNavItem;

document.addEventListener('DOMContentLoaded', function restoreNavPrefs() {
    try {
        const prefs = JSON.parse(localStorage.getItem('stellio-nav-prefs') || '{}');
        Object.entries(prefs).forEach(([navId, visible]) => {
            if (!visible) toggleNavItem(navId, false);
            const cb = document.querySelector(`.nav-visibility-toggle[data-nav-id="${navId}"]`);
            if (cb) cb.checked = visible;
        });
    } catch (_) {}
});


document.getElementById('sort-select')?.addEventListener('change', (e) => { currentSort = e.target.value; applySorting(); renderFiles(); });
document.getElementById('apply-filters')?.addEventListener('click', applyFilters);

document.getElementById('confirm-slicer')?.addEventListener('click', async () => {
    if (!currentSlicerFile) return;
    const consumeSpool = document.getElementById('slicer-spool-box')?.style.display !== 'none'
        && document.getElementById('slicer-consume-spool-checkbox')?.checked;
    try {
        const body = {
            file_path: currentSlicerFile,
            consume_spool: !!consumeSpool,
            orientation: currentSlicerOrientation || 'default',
            printer_id: document.getElementById('slicer-ai-printer-select')?.value || null,
            material_type: document.getElementById('slicer-ai-material-select')?.value || null
        };
        if (_lastAiRecommendedProfile && _lastAiRecommendedProfile.id) {
            body.slicer_profile_id = _lastAiRecommendedProfile.id;
            body.slicer_profile_name = _lastAiRecommendedProfile.name;
        }
        const res = await fetch(`${API}/api/slicer/send`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        const data = await res.json();
        showToast(res.ok ? I18N.t('toast.files_sent') : data.error, res.ok ? 'success' : 'error');
        if (res.ok && data.stock_warning) _showStockWarningToast(data.stock_warning);
    } catch (err) { showToast(I18N.t('toast.send_error'), 'error'); }
    currentSlicerOrientation = 'default';
    closeModal('modal-slicer');
    if (_slicerLaunchedFromViewer) {
        _slicerLaunchedFromViewer = false;
        close3DViewer();
    }
});

document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target !== modal) return;
        if (modal.id === 'modal-3d-viewer') close3DViewer();
        else modal.classList.add('hidden');
    });
});
document.getElementById('modal-about')?.addEventListener('click', (e) => { if (e.target.id === 'modal-about') closeModal('modal-about'); });

const mainContent = document.querySelector('.main-content');
const scrollToTopBtn = document.getElementById('scroll-to-top');
if (mainContent && scrollToTopBtn) {
    mainContent.addEventListener('scroll', () => {
        if (mainContent.scrollTop > 300) scrollToTopBtn.classList.add('visible');
        else scrollToTopBtn.classList.remove('visible');
    });
    scrollToTopBtn.addEventListener('click', () => { mainContent.scrollTo({ top: 0, behavior: 'smooth' }); });
}

document.getElementById('force-refresh-btn')?.addEventListener('click', async () => {
    showToast(I18N.t('toast.refreshing'), 'info');
    try { await fetch(`${API}/api/files/invalidate-cache`, { method: 'POST' }); } catch (e) {  }
    await loadFiles();
    showToast(I18N.t('toast.refreshed'), 'success');
});

document.getElementById('manage-tags-btn')?.addEventListener('click', () => openTagManagerModal('global'));
document.getElementById('manage-tags-modal-btn')?.addEventListener('click', () => { closeModal('modal-filters'); setTimeout(() => openTagManagerModal('global'), 100); });

document.getElementById('filter-tags')?.addEventListener('change', (e) => {
    if (e.target.classList.contains('filter-tag')) {
        if (e.target.checked) activeTagFilters.add(e.target.value);
        else activeTagFilters.delete(e.target.value);
        applyFilters();
    }
});

document.getElementById('favorites-filter-btn')?.addEventListener('click', () => toggleFavoritesFilter(null));
document.getElementById('download-form')?.addEventListener('submit', handleDownload);

document.getElementById('download-url')?.addEventListener('input', function() {
    const fmtGroup = document.getElementById('makerworld-format-group');
    if (!fmtGroup) return;
    fmtGroup.style.display = this.value.includes('makerworld.com') ? 'block' : 'none';
});

document.getElementById('language-selector')?.addEventListener('change', (e) => { I18N.setLanguage(e.target.value); translateSortOptions(); });

document.getElementById('language-selector-auth')?.addEventListener('change', (e) => {
    I18N.setLanguage(e.target.value);
    setTimeout(() => {
        translateAuthFields();
        I18N.apply(document.querySelector('.auth-panel:not(.hidden)') || document);
    }, 100);
});

document.addEventListener('i18n:changed', (e) => {
    const authSelector = document.getElementById('language-selector-auth');
    if (authSelector && authSelector.value !== e.detail.lang) authSelector.value = e.detail.lang;
    translateSortOptions();
    translateAuthFields();
    const activeBtn = document.querySelector('.nav-btn.active');
    if (activeBtn) {
        const titleKey = activeBtn.dataset.titleKey || 'app.title';
        const iconClass = activeBtn.dataset.icon || 'fa-layer-group';
        const headerTitle = document.getElementById('header-page-title');
        if (headerTitle) headerTitle.innerHTML = `<i class="fa-solid ${iconClass}"></i> ${I18N.t(titleKey)}`;
    }
    const searchInput = document.getElementById('global-search');
    if (searchInput) searchInput.placeholder = I18N.t('search.placeholder');
    I18N.apply();
});
}


let selectedFolderFiles = new Set();
window.selectFolderFiles = function (folderPath, btnElement) {
const icon = btnElement.querySelector('i');
const folderCards = document.querySelectorAll(`.file-card[data-path^="${folderPath}/"], .file-card[data-path="${folderPath}"]`);
const allSelected = Array.from(folderCards).every(card => selectedFolderFiles.has(card.dataset.path));
if (allSelected) {
folderCards.forEach(card => { selectedFolderFiles.delete(card.dataset.path); card.classList.remove('selected'); });
icon.classList.remove('fa-check-square');
icon.classList.add('fa-square');
btnElement.innerHTML = `<i class="fa-regular fa-square"></i> ${I18N.t('actions.select')}`;
} else {
folderCards.forEach(card => { selectedFolderFiles.add(card.dataset.path); card.classList.add('selected'); });
icon.classList.remove('fa-square');
icon.classList.add('fa-check-square');
btnElement.innerHTML = `<i class="fa-solid fa-check-square"></i> ${I18N.t('actions.cancel')}`;
}
updateFolderSelectionBar();
};
function updateFolderSelectionBar() {
const count = selectedFolderFiles.size;
let bar = document.getElementById('folder-selection-bar');
const countEl = document.getElementById('folder-selection-count');
if (count > 0) {
if (!bar) {
bar = document.createElement('div');
bar.id = 'folder-selection-bar';
bar.className = 'folder-selection-bar';
bar.style.display = 'flex';
bar.innerHTML = `<span id="folder-selection-count">${I18N.tp('common.file_count', count, { count })} ${I18N.t('actions.select').toLowerCase()}</span><select id="folder-batch-printer-select" class="settings-select" style="min-width:0; width:auto; max-width:150px; font-size:12px; padding:6px 8px;"><option value="" data-i18n="modal.ai_all_printers">Toutes les imprimantes</option></select><button onclick="sendFolderSelectionToSlicer()" class="btn btn-primary btn-sm"><i class="fa-solid fa-scissors"></i> ${I18N.t('actions.send_to_slicer')}</button><button onclick="clearFolderSelection()" class="btn btn-ghost btn-sm"><i class="fa-solid fa-times"></i> ${I18N.t('actions.cancel')}</button>`;
document.querySelector('.main-content').appendChild(bar);
_populatePrinterSelects();
} else {
bar.style.display = 'flex';
if (countEl) countEl.textContent = `${I18N.tp('common.file_count', count, { count })} ${I18N.t('actions.select').toLowerCase()}`;
}
} else {
if (bar) bar.style.display = 'none';
}
}
window.sendFolderSelectionToSlicer = async function () {
if (selectedFolderFiles.size === 0) { showToast(I18N.t('toast.no_selection'), 'warning'); return; }
try {
const res = await fetch(`${API}/api/slicer/send-batch`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ files: [...selectedFolderFiles], printer_id: document.getElementById('folder-batch-printer-select')?.value || null }) });
const data = await res.json();
if (res.ok) { showToast(`✅ ${data.message}`, 'success'); if (data.stock_warnings && data.stock_warnings.length) data.stock_warnings.forEach(_showStockWarningToast); clearFolderSelection(); }
else { showToast(data.error || I18N.t('toast.send_error'), 'error'); }
} catch (err) { showToast(I18N.t('toast.connection_error'), 'error'); }
};
window.clearFolderSelection = function () {
selectedFolderFiles.clear();
document.querySelectorAll('.file-card.selected').forEach(card => card.classList.remove('selected'));
document.querySelectorAll('.folder-select-btn').forEach(btn => {
const icon = btn.querySelector('i');
if (icon) { icon.classList.remove('fa-check-square'); icon.classList.add('fa-square'); }
btn.innerHTML = `<i class="fa-regular fa-square"></i> ${I18N.t('actions.select')}`;
});
const bar = document.getElementById('folder-selection-bar');
if (bar) bar.style.display = 'none';
};
window.testFolderFiles = async function (sourceId) {  };
window.testBatchSend = async function (filePaths, slicerPath = null) {  };
window.testBatchPreview = async function (filePaths) {  };


let repairFilesList = [];
let isRepairScanning = false;
const MAX_FILES_TO_SCAN = 30;
document.querySelector('.nav-btn[data-page="repair"]')?.addEventListener('click', () => {
document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
document.querySelector('.nav-btn[data-page="repair"]')?.classList.add('active');
document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
document.getElementById('page-repair')?.classList.add('active');
const titleEl = document.getElementById('header-page-title');
if (titleEl) {
titleEl.innerHTML = `<i class="fa-solid fa-screwdriver-wrench"></i> ${I18N.t('nav.repair')}`;
}
loadRepairFiles();
});
async function loadRepairFiles() {
const grid = document.getElementById('repair-grid');
const empty = document.getElementById('repair-empty');
grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><p style="margin-top:12px;color:var(--text-muted);">${I18N.t('repair.loading')}</p></div>`;
empty.classList.add('hidden');
repairFilesList = [];
isRepairScanning = false;
try {
const res = await fetch(`${API}/api/files`);
if (!res.ok) throw new Error(I18N.t('toast.connection_error'));
const files = await res.json();
repairFilesList = files.filter(f => f.metadata?.needs_repair === true || f.metadata?.is_manifold === false);
const unanalyzedFiles = files.filter(f => !f.metadata).slice(0, MAX_FILES_TO_SCAN);
renderRepairFiles(unanalyzedFiles);
updateRepairBadge();
} catch (err) {
grid.innerHTML = `<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><p>${err.message}</p></div>`;
}
}
function renderRepairFiles(unanalyzedFiles = []) {
const grid = document.getElementById('repair-grid');
const empty = document.getElementById('repair-empty');
if (repairFilesList.length === 0 && unanalyzedFiles.length === 0) {
grid.innerHTML = '';
empty.classList.remove('hidden');
updateRepairBadge();
return;
}
empty.classList.add('hidden');
let html = '';
repairFilesList.forEach(f => {
html += `<div class="repair-card" data-path="${escapeHtml(f.path)}"><div class="repair-thumb">${f.has_thumb ? `<img src="${API}/api/thumb?path=${encodeURIComponent(f.path)}" alt="${escapeHtml(f.name)}">` : `<i class="fa-solid fa-cube"></i>`}<span class="repair-badge-warn"><i class="fa-solid fa-triangle-exclamation"></i> ${I18N.t('repair.non_manifold_badge')}</span></div><div class="repair-info"><div class="repair-name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</div><div class="repair-meta">${formatSize(f.size)} • ${(f.extension || '.stl').toUpperCase()}</div><button class="btn btn-primary btn-sm repair-btn" onclick="repairFile('${escapeJs(f.path)}', this)"><i class="fa-solid fa-wrench"></i> ${I18N.t('actions.repair') || 'Réparer'}</button></div></div>`;
});
if (unanalyzedFiles.length > 0 && !isRepairScanning) {
html += `<div class="repair-card" style="grid-column:1/-1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:30px;border:2px dashed var(--border);background:transparent;"><i class="fa-solid fa-magnifying-glass" style="font-size:32px;color:var(--text-muted);margin-bottom:12px;"></i><p style="color:var(--text-secondary);margin-bottom:16px;font-size:14px;">${I18N.tp('repair.unanalyzed_count', unanalyzedFiles.length, { count: unanalyzedFiles.length })}</p><button class="btn btn-primary" onclick="scanUnanalyzedFiles()" style="gap:8px;"><i class="fa-solid fa-play"></i> ${I18N.t('repair.analyze_btn')}</button><p style="color:var(--text-muted);font-size:12px;margin-top:10px;">${I18N.t('repair.scan_limit', { max: MAX_FILES_TO_SCAN })}</p></div>`;
}
grid.innerHTML = html;
updateRepairBadge();
}
async function scanUnanalyzedFiles() {
if (isRepairScanning) return;
isRepairScanning = true;
const grid = document.getElementById('repair-grid');
grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;"><i class="fa-solid fa-spinner fa-spin fa-2x" style="color:var(--accent);"></i><p style="margin-top:12px;color:var(--text-muted);">${I18N.t('repair.scanning')}</p><p id="repair-progress-text" style="margin-top:8px;color:var(--text-secondary);font-size:12px;">${I18N.t('repair.progress_zero')}</p></div>`;
const res = await fetch(`${API}/api/files`);
const files = await res.json();
const unanalyzed = files.filter(f => !f.metadata).slice(0, MAX_FILES_TO_SCAN);
let analyzed = 0;
let found = 0;
for (const f of unanalyzed) {
try {
const analyzeRes = await fetch(`${API}/api/files/analyze`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ path: f.path })
});
const data = await analyzeRes.json();
analyzed++;
if (analyzed % 5 === 0) {
const progressEl = document.getElementById('repair-progress-text');
if (progressEl) progressEl.textContent = I18N.t('repair.progress', { analyzed, total: unanalyzed.length, found });
}
if (data.success && data.metadata?.needs_repair) {
found++;
repairFilesList.push({ ...f, metadata: data.metadata });
}
await new Promise(r => setTimeout(r, 100));
} catch (err) {
console.debug(`[Repair] Erreur analyse ${f.name}:`, err);
}
}
isRepairScanning = false;
renderRepairFiles();
showToast(I18N.t('toast.repair_scan_done', { found, analyzed }), 'success');
}
function updateRepairBadge() {
const badge = document.getElementById('repair-count');
if (badge) {
const count = repairFilesList.length;
badge.textContent = count > 0 ? count : '';
badge.style.display = count > 0 ? 'inline-block' : 'none';
}
}
window.repairFile = async function(filePath, btn) {
const originalHtml = btn.innerHTML;
btn.disabled = true;
btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t('actions.repairing') || 'Réparation'}...`;
try {
const res = await fetch(`${API}/api/files/repair`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ path: filePath })
});
const data = await res.json();
if (res.ok && data.success && data.watertight !== false) {
btn.innerHTML = `<i class="fa-solid fa-check"></i> ${I18N.t('actions.repaired') || 'Réparé'}`;
btn.classList.replace('btn-primary', 'btn-success');
showToast(I18N.t('toast.repair_success'), 'success');
setTimeout(() => {
repairFilesList = repairFilesList.filter(f => f.path !== filePath);
renderRepairFiles();
loadFiles();
}, 1200);
} else if (res.ok && data.success && data.watertight === false) {
btn.innerHTML = `<i class="fa-solid fa-check"></i> ${I18N.t('actions.repaired') || 'Traité'}`;
btn.classList.replace('btn-primary', 'btn-success');
showToast(data.message || I18N.t('toast.repair_partial') || 'Réparation partielle : problèmes non résolus automatiquement (sauvegarde .bak conservée)', 'warning');
setTimeout(() => {
repairFilesList = repairFilesList.filter(f => f.path !== filePath);
renderRepairFiles();
loadFiles();
}, 1200);
} else {
btn.innerHTML = originalHtml;
btn.disabled = false;
showToast(data.error || I18N.t('toast.repair_failed'), 'error');
}
} catch (err) {
btn.innerHTML = originalHtml;
btn.disabled = false;
showToast(I18N.t('toast.connection_error'), 'error');
}
};

window.repairAndRegenThumb = async function (filePath, btn) {
const originalHtml = btn.innerHTML;
btn.disabled = true;
btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t('actions.repairing')}`;
try {
    const res = await fetch(`${API}/api/files/repair`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: filePath })
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
        showToast(data.error || I18N.t('toast.repair_failed'), 'error');
        return;
    }
    const regenPath = data.new_path || filePath;
    await fetch(`${API}/api/thumb/generate-now`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: regenPath, force: true })
    });
    btn.innerHTML = `<i class="fa-solid fa-check"></i> ${I18N.t('actions.repaired')}`;
    showToast(I18N.t('toast.repaired_generic'), 'success');
    const li = document.getElementById(`thumb-fail-${filePath.replace(/[^\w]/g, '-')}`);
    setTimeout(() => { li?.remove(); }, 1500);
    if (typeof loadFiles === 'function') loadFiles();
} catch (err) {
    btn.innerHTML = originalHtml;
    btn.disabled = false;
    showToast(I18N.t('toast.connection_error'), 'error');
}
};


let converterAllFiles = [];
let converterSelectedFiles = new Set();

document.querySelector('.nav-btn[data-page="converter"]')?.addEventListener('click', () => {
document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
document.querySelector('.nav-btn[data-page="converter"]')?.classList.add('active');
document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
document.getElementById('page-converter')?.classList.add('active');
const titleEl = document.getElementById('header-page-title');
if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-file-export"></i> Convertisseur`;
loadConverterFiles();
});

async function loadConverterFiles() {
const grid = document.getElementById('converter-grid');
if (!grid) return;
grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;"><i class="fa-solid fa-spinner fa-spin fa-2x"></i></div>`;
converterSelectedFiles.clear();
try {
    const res = await fetch(`${API}/api/files`);
    if (!res.ok) throw new Error(I18N.t('toast.connection_error'));
    converterAllFiles = await res.json();
    renderConverterFiles();
} catch (err) {
    grid.innerHTML = `<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><p>${err.message}</p></div>`;
}
}

function getConverterFilteredList() {
const inputFormat = document.getElementById('converter-input-format')?.value || 'all';
const outputFormat = document.getElementById('converter-output-format')?.value || 'stl';
const search = (document.getElementById('converter-search')?.value || '').toLowerCase().trim();
return (converterAllFiles || []).filter(f => {
    const ext = (f.extension || '').toLowerCase();
    if (!['.stl', '.3mf', '.obj'].includes(ext)) return false;
    if (inputFormat !== 'all' && ext !== inputFormat) return false;
    if (ext === '.' + outputFormat) return false;
    if (search && !f.name.toLowerCase().includes(search)) return false;
    return true;
});
}

function renderConverterFiles() {
const grid = document.getElementById('converter-grid');
const empty = document.getElementById('converter-empty');
if (!grid || !empty) return;
const list = getConverterFilteredList();
if (list.length === 0) {
    grid.innerHTML = '';
    empty.classList.remove('hidden');
    updateConverterActionState();
    return;
}
empty.classList.add('hidden');
grid.innerHTML = list.map(f => {
    const isSelected = converterSelectedFiles.has(f.path);
    const extLabel = (f.extension || '').replace('.', '').toUpperCase();
    return `<div class="repair-card converter-card${isSelected ? ' selected' : ''}" data-path="${escapeHtml(f.path)}">
        <div class="converter-card-checkbox" onclick="event.stopPropagation(); toggleConverterFileSelection('${escapeJs(f.path)}')">
            <input type="checkbox" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation();" onchange="toggleConverterFileSelection('${escapeJs(f.path)}')">
        </div>
        <div class="repair-thumb">${f.has_thumb ? `<img src="${API}/api/thumb?path=${encodeURIComponent(f.path)}" alt="${escapeHtml(f.name)}">` : `<i class="fa-solid fa-cube"></i>`}<span class="repair-badge-warn" style="background:rgba(59,130,246,0.92);">${extLabel}</span></div>
        <div class="repair-info">
            <div class="repair-name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</div>
            <div class="repair-meta">${formatSize(f.size || 0)}</div>
            <button type="button" class="btn btn-primary btn-sm repair-btn" onclick="convertSingleFile('${escapeJs(f.path)}', this)">
                <i class="fa-solid fa-arrows-rotate"></i> Convertir
            </button>
        </div>
    </div>`;
}).join('');
updateConverterActionState();
}

window.toggleConverterFileSelection = function (filePath) {
if (converterSelectedFiles.has(filePath)) converterSelectedFiles.delete(filePath);
else converterSelectedFiles.add(filePath);
const card = document.querySelector(`.converter-card[data-path="${CSS.escape(filePath)}"]`);
if (card) card.classList.toggle('selected', converterSelectedFiles.has(filePath));
updateConverterActionState();
};

function updateConverterActionState() {
const btn = document.getElementById('converter-convert-btn');
const label = document.getElementById('converter-convert-btn-label');
if (label) label.textContent = I18N.tp('converter.convert_btn', converterSelectedFiles.size, { count: converterSelectedFiles.size });
if (btn) btn.disabled = converterSelectedFiles.size === 0;
}

document.getElementById('converter-input-format')?.addEventListener('change', () => { converterSelectedFiles.clear(); renderConverterFiles(); });
document.getElementById('converter-output-format')?.addEventListener('change', () => { converterSelectedFiles.clear(); renderConverterFiles(); });
document.getElementById('converter-search')?.addEventListener('input', renderConverterFiles);

document.getElementById('converter-select-all-btn')?.addEventListener('click', () => {
const list = getConverterFilteredList();
if (converterSelectedFiles.size === list.length && list.length > 0) converterSelectedFiles.clear();
else list.forEach(f => converterSelectedFiles.add(f.path));
renderConverterFiles();
});

window.convertSingleFile = async function (filePath, btn) {
const targetFormat = document.getElementById('converter-output-format')?.value || 'stl';
const deleteOriginal = document.getElementById('converter-delete-original')?.checked || false;
const repair = document.getElementById('converter-repair')?.checked || false;
const sourceUnit = document.getElementById('converter-source-unit')?.value || 'mm';
const originalHtml = btn.innerHTML;
btn.disabled = true;
btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t('converter.converting')}`;
try {
    const res = await fetch(`${API}/api/files/convert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: filePath, target_format: targetFormat, delete_original: deleteOriginal, repair, source_unit: sourceUnit })
    });
    const data = await res.json();
    if (res.ok && data.success) {
        let msg = I18N.t('converter.converted_success', { format: targetFormat, suffix: data.deleted_original ? I18N.t('converter.deleted_original_suffix') : I18N.t('converter.kept_original_suffix') });
        if (typeof data.size_reduction_pct === 'number' && data.size_reduction_pct > 0) {
            msg += I18N.t('converter.size_reduction_suffix', { newSize: formatSize(data.new_size), oldSize: formatSize(data.original_size), pct: data.size_reduction_pct });
        }
        showToast(msg, 'success');
        converterSelectedFiles.delete(filePath);
        converterAllFiles = converterAllFiles.filter(f => f.path !== filePath);
        renderConverterFiles();
        if (typeof loadFiles === 'function') loadFiles();
    } else {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
        showToast(data.error || I18N.t('converter.failed'), 'error');
    }
} catch (err) {
    btn.innerHTML = originalHtml;
    btn.disabled = false;
    showToast(I18N.t('toast.connection_error'), 'error');
}
};

document.getElementById('converter-convert-btn')?.addEventListener('click', async () => {
if (converterSelectedFiles.size === 0) return;
const targetFormat = document.getElementById('converter-output-format')?.value || 'stl';
const deleteOriginal = document.getElementById('converter-delete-original')?.checked || false;
const repair = document.getElementById('converter-repair')?.checked || false;
const sourceUnit = document.getElementById('converter-source-unit')?.value || 'mm';
const paths = [...converterSelectedFiles];
const btn = document.getElementById('converter-convert-btn');
const originalHtml = btn.innerHTML;
btn.disabled = true;
btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t('converter.converting_progress')}`;
try {
    const res = await fetch(`${API}/api/files/convert-batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paths, target_format: targetFormat, delete_original: deleteOriginal, repair, source_unit: sourceUnit })
    });
    const data = await res.json();
    if (res.ok) {
        const okCount = data.converted || 0;
        const failCount = paths.length - okCount;
        let msg = I18N.t('converter.batch_result', { count: okCount, failSuffix: failCount ? I18N.t('converter.batch_fail_suffix', { count: failCount }) : '' });
        const okResults = (data.results || []).filter(r => r.success && typeof r.size_reduction_pct === 'number');
        if (okResults.length) {
            const avgReduction = okResults.reduce((sum, r) => sum + r.size_reduction_pct, 0) / okResults.length;
            if (avgReduction > 0) msg += I18N.t('converter.avg_reduction_suffix', { pct: avgReduction.toFixed(1) });
        }
        showToast(msg, failCount ? 'warning' : 'success');
    } else {
        showToast(data.error || I18N.t('converter.batch_failed'), 'error');
    }
} catch (err) {
    showToast(I18N.t('toast.connection_error'), 'error');
} finally {
    converterSelectedFiles.clear();
    btn.innerHTML = originalHtml;
    await loadConverterFiles();
    if (typeof loadFiles === 'function') loadFiles();
}
});


const PRINTER_DEFAULT_PORTS = { octoprint: '80', klipper: '7125', marlin: '80' };

window.togglePrinterFields = function() {
    const type = document.getElementById('printer-type')?.value;
    const gIp = document.getElementById('group-ip'), gPort = document.getElementById('group-port');
    const gApi = document.getElementById('group-api-key'), gBambu = document.getElementById('group-bambu');
    const portIn = document.getElementById('printer-port'), apiLbl = document.querySelector('#group-api-key label');
    const apiIn = document.getElementById('printer-api-key'), help = document.getElementById('printer-type-help');
    [gIp, gPort, gApi, gBambu].forEach(g => { if (g) g.style.display = 'none'; });
    if (!type) return;
    if (gIp) gIp.style.display = '';
    if (portIn && PRINTER_DEFAULT_PORTS[type]) portIn.value = PRINTER_DEFAULT_PORTS[type];
    if (type === 'octoprint') {
        if (gApi) gApi.style.display = ''; if (gPort) gPort.style.display = '';
        if (apiLbl) apiLbl.textContent = I18N.t('printers.octoprint_api_key'); if (apiIn) apiIn.placeholder = I18N.t('printers.octoprint_api_placeholder');
        if (help) help.textContent = I18N.t('printers.octoprint_port_hint');
    } else if (type === 'klipper') {
        if (gPort) gPort.style.display = ''; if (gApi) gApi.style.display = '';
        if (apiLbl) apiLbl.textContent = I18N.t('printers.moonraker_api_key'); if (apiIn) apiIn.placeholder = I18N.t('printers.optional');
        if (help) help.textContent = I18N.t('printers.klipper_port_hint');
    } else if (type === 'marlin') {
        if (gPort) gPort.style.display = '';
        if (help) help.textContent = I18N.t('printers.marlin_port_hint');
    } else if (type === 'bambu') {
        if (gBambu) gBambu.style.display = '';
        if (help) help.textContent = I18N.t('printers.bambu_mqtt_hint');
    }
};

window.openAddPrinterModal = function() {
    openModal('modal-add-printer');
    ['printer-name','printer-ip','printer-api-key','printer-brand','printer-bambu-code','printer-bambu-serial'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    const bambuModelReset = document.getElementById('printer-bambu-model');
    if (bambuModelReset) bambuModelReset.value = 'A1';
    const ts = document.getElementById('printer-type'); if (ts) ts.value = '';
    ['group-ip','group-port','group-api-key','group-bambu'].forEach(id => { const el = document.getElementById(id); if (el) el.style.display = 'none'; });
    const th = document.getElementById('printer-type-help'); if (th) th.textContent = '';
    if (typeof displayCompatibilityIndicator === 'function') displayCompatibilityIndicator('');
};

window.addPrinter = async function() {
    const name = document.getElementById('printer-name')?.value.trim();
    const type = document.getElementById('printer-type')?.value;
    const ipRaw = document.getElementById('printer-ip')?.value.trim();
    const apiKey = document.getElementById('printer-api-key')?.value.trim() || '';
    const port = document.getElementById('printer-port')?.value.trim() || PRINTER_DEFAULT_PORTS[type] || '80';
    const brand = document.getElementById('printer-brand')?.value.trim() || '';
    if (!name || !ipRaw || !type) { showToast(I18N.t('toast.fill_required_fields'), 'warning'); return; }
    const ip = ipRaw.replace(/^https?:\/\//, '').split(':')[0].split('/')[0];
    try {
        const res = await fetch(API + '/api/printers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, type, ip, port, api_key: apiKey, config: { brand, port } }) });
        const data = await res.json();
        if (res.ok) { showToast(I18N.t('toast.printer_added'), 'success'); closeModal('modal-add-printer'); loadPrinters(); }
        else showToast('❌ ' + (data.error || I18N.t('toast.error')), 'error');
    } catch(e) { showToast(I18N.t('toast.connection_error'), 'error'); }
};


const PRINTER_COMPATIBILITY = {
    'octoprint_generic': {
        status: 'compatible',
        type: 'octoprint',
        brands: ['octoprint'],
        note: 'printers.note_octoprint_generic'
    },
    'klipper_generic': {
        status: 'compatible',
        type: 'klipper',
        brands: ['klipper', 'moonraker', 'voron', 'rat rig', 'ratrig', 'annex', 'vzbot'],
        note: 'printers.note_klipper_generic'
    },
    'bambu': {
        status: 'compatible',
        type: 'bambu',
        brands: ['bambu lab', 'bambu', 'x1', 'x1c', 'p1p', 'p1s', 'a1', 'a1 mini'],
        note: 'printers.note_bambu'
    },
    'creality_k2': {
        status: 'compatible',
        type: 'klipper',
        brands: ['k2', 'k2 pro', 'k2 plus', 'k2-plus', 'k2 se'],
        note: 'printers.note_creality_k2'
    },
    'creality_k1': {
        status: 'partial',
        type: 'klipper',
        brands: ['k1', 'k1c', 'k1 max', 'k1-max', 'k1 se'],
        note: 'printers.note_creality_k1'
    },
    'creality_classic': {
        status: 'partial',
        type: 'octoprint',
        brands: ['ender', 'ender 3', 'ender 5', 'cr-10', 'cr-10s', 'ender 2', 'ender 6'],
        note: 'printers.note_marlin_octoprint'
    },
    'creality_generic': {
        status: 'partial',
        type: null,
        generic: true,
        brands: ['creality'],
        note: 'printers.note_creality_generic'
    },
    'prusa_prusalink': {
        status: 'compatible',
        type: 'prusalink',
        brands: ['mk4', 'mk4s', 'mk3.9', 'mk3.5', 'mini+', 'xl', 'core one'],
        note: 'printers.note_prusalink'
    },
    'prusa_octoprint': {
        status: 'partial',
        type: 'octoprint',
        brands: ['mk3', 'mk3s', 'mk2.5'],
        note: 'printers.note_marlin_octoprint'
    },
    'prusa_generic': {
        status: 'partial',
        type: null,
        generic: true,
        brands: ['prusa'],
        note: 'printers.note_prusa_generic'
    },
    'anycubic_kobra_os': {
        status: 'partial',
        type: 'klipper',
        brands: ['kobra 3', 'kobra s1', 'kobra 2 pro'],
        note: 'printers.note_anycubic_kobra_os'
    },
    'anycubic_marlin': {
        status: 'partial',
        type: 'octoprint',
        brands: ['i3 mega', 'mega s', 'chiron', 'kossel', 'vyper'],
        note: 'printers.note_marlin_octoprint'
    },
    'anycubic_generic': {
        status: 'partial',
        type: null,
        generic: true,
        brands: ['anycubic'],
        note: 'printers.note_anycubic_generic'
    },
    'qidi': {
        status: 'compatible',
        type: 'klipper',
        brands: ['qidi', 'q1 pro', 'x-max', 'x max'],
        note: 'printers.note_qidi'
    },
    'flsun': {
        status: 'compatible',
        type: 'klipper',
        brands: ['flsun', 'v400', 'super racer', 'q5'],
        note: 'printers.note_flsun'
    },
    'snapmaker_u1': {
        status: 'compatible',
        type: 'klipper',
        brands: ['snapmaker u1', 'u1'],
        note: 'printers.note_snapmaker_u1'
    },
    'snapmaker_artisan': {
        status: 'partial',
        type: 'octoprint',
        brands: ['snapmaker artisan', 'artisan'],
        note: 'printers.note_snapmaker_artisan'
    },
    'snapmaker_legacy': {
        status: 'incompatible',
        type: null,
        brands: ['snapmaker', 'snapmaker 2.0', 'snapmaker j1', 'a150', 'a250', 'a350'],
        note: 'printers.note_snapmaker_legacy'
    },
    'artillery': {
        status: 'partial',
        type: 'octoprint',
        brands: ['artillery', 'sidewinder', 'genius', 'hornet'],
        note: 'printers.note_marlin_octoprint'
    },
    'tevo': {
        status: 'partial',
        type: 'octoprint',
        brands: ['tevo', 'tarantula', 'tornado', 'black widow'],
        note: 'printers.note_marlin_octoprint'
    },
    'monoprice': {
        status: 'partial',
        type: 'octoprint',
        brands: ['monoprice', 'maker select', 'select mini'],
        note: 'printers.note_marlin_octoprint'
    },
    'flashforge_legacy': {
        status: 'partial',
        type: 'octoprint',
        brands: ['flashforge', 'creator', 'finder', 'dreamer', 'guider'],
        note: 'printers.note_flashforge_legacy'
    },
    'flashforge_ad5m': {
        status: 'incompatible',
        type: null,
        brands: ['adventurer 5m', 'ad5m', 'adventurer 5m pro'],
        note: 'printers.note_flashforge_ad5m'
    },
    'ultimaker': {
        status: 'partial',
        type: 'octoprint',
        brands: ['ultimaker', 's3', 's5', 's7'],
        note: 'printers.note_marlin_octoprint'
    },
    'elegoo_centauri': {
        status: 'incompatible',
        type: null,
        brands: ['centauri', 'centauri carbon'],
        note: 'printers.note_elegoo_centauri'
    },
    'elegoo_neptune': {
        status: 'partial',
        type: 'octoprint',
        brands: ['neptune'],
        note: 'printers.note_marlin_octoprint'
    },
    'elegoo_generic': {
        status: 'partial',
        type: null,
        generic: true,
        brands: ['elegoo'],
        note: 'printers.note_elegoo_generic'
    },
    'sovol': {
        status: 'partial',
        type: 'octoprint',
        brands: ['sovol', 'sv06', 'sv01'],
        note: 'printers.note_marlin_octoprint'
    },
    'raise3d': {
        status: 'partial',
        type: 'octoprint',
        brands: ['raise3d', 'raise 3d', 'pro2', 'pro3', 'e2'],
        note: 'printers.note_marlin_octoprint'
    },
    'tiertime': {
        status: 'partial',
        type: 'octoprint',
        brands: ['tiertime', 'up box', 'up mini', 'up studio'],
        note: 'printers.note_tiertime'
    },
    'xyzprinting': {
        status: 'incompatible',
        type: null,
        brands: ['xyzprinting', 'xyz printing', 'da vinci'],
        note: 'printers.note_xyzprinting'
    },
    'makerbot': {
        status: 'incompatible',
        type: null,
        brands: ['makerbot', 'method', 'replicator+', 'sketch'],
        note: 'printers.note_makerbot'
    },
    'cel_robox': {
        status: 'incompatible',
        type: null,
        brands: ['cel', 'robox'],
        note: 'printers.note_proprietary_defunct'
    },
    'pirate3d': {
        status: 'incompatible',
        type: null,
        brands: ['pirate3d', 'buccaneer'],
        note: 'printers.note_proprietary_defunct'
    },
    'bigtreetech': {
        status: 'compatible',
        type: 'klipper',
        brands: ['bigtreetech', 'biqu', 'btt'],
        note: 'printers.note_bigtreetech'
    },
    'generic_marlin_brands': {
        status: 'partial',
        type: 'octoprint',
        brands: [
            '3d modular systems', 'alfawise', 'longer3d', 'longer 3d', 'anet',
            'bq', 'createbot', 'ctc', 'dagoma', 'dremel', 'emotion tech',
            'eryone', 'easythreed', 'feider', 'freesculpt', 'geeetech',
            'jgaurora', 'jgmaker', 'kingroon', 'lotmaxx', 'm3d', 'ortur',
            'sculptr', 'smartcub3d', 'spiderbot', 'sunlu', 'tenlog',
            'tobeca', 'trinus', 'tronxy', 'two trees', 'velleman', 'velta 3d',
            'volumic', 'wanhao', 'zatsit', 'zonestar', 'flying bear'
        ],
        note: 'printers.note_marlin_octoprint'
    }
};

function checkPrinterCompatibility(brandName) {
    if (!brandName || brandName.trim().length === 0) {
        return null;
    }

    const brand = brandName.toLowerCase().trim();
    let bestSpecific = null, bestSpecificLen = 0;
    let bestGeneric = null, bestGenericLen = 0;

    for (const [key, data] of Object.entries(PRINTER_COMPATIBILITY)) {
        for (const b of data.brands) {
            const bl = b.toLowerCase();
            if (brand === bl || brand.includes(bl) || bl.includes(brand)) {
                const match = { status: data.status, type: data.type, note: data.note, matchedBrand: key };
                if (data.generic) {
                    if (bl.length > bestGenericLen) { bestGenericLen = bl.length; bestGeneric = match; }
                } else {
                    if (bl.length > bestSpecificLen) { bestSpecificLen = bl.length; bestSpecific = match; }
                }
            }
        }
    }

    if (bestSpecific) return bestSpecific;
    if (bestGeneric) return bestGeneric;

    return {
        status: 'compatible',
        type: null,
        note: 'printers.compatible_generic',
        matchedBrand: 'generic'
    };
}

function displayCompatibilityIndicator(brandName) {
    const indicator = document.getElementById('brand-compatibility-indicator');
    const icon = document.getElementById('brand-check-icon');
    const text = document.getElementById('brand-check-text');
    const helpText = document.getElementById('brand-help-text');

    if (!indicator || !icon || !text) return;

    const result = checkPrinterCompatibility(brandName);

    if (!result) {
        indicator.style.display = 'none';
        if (helpText) helpText.textContent = I18N.t('printers.enter_brand_hint');
        return;
    }

    indicator.style.display = 'flex';
    indicator.className = 'compatibility-indicator ' + result.status;

    const iconClass = { compatible: 'fa-circle-check', partial: 'fa-triangle-exclamation', incompatible: 'fa-circle-xmark' }[result.status];
    icon.className = 'fa-solid ' + iconClass;
    text.textContent = I18N.t(result.note) || result.note;

    const typeSelect = document.getElementById('printer-type');
    if (typeSelect && result.type && result.status !== 'incompatible') {
        typeSelect.value = result.type;
        togglePrinterFields();
    }

    if (helpText) {
        helpText.textContent = result.matchedBrand === 'generic'
            ? I18N.t('printers.compatible_generic')
            : (I18N.t('printers.detected_brand') || 'Détecté') + ': ' + result.matchedBrand.replace(/_/g, ' ');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const brandInput = document.getElementById('printer-brand');
    if (brandInput) {
        let debounceTimer;
        brandInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                displayCompatibilityIndicator(e.target.value);
            }, 300);
        });
    }
});


window.addPrinter = async function() {
    const editId = document.getElementById('printer-edit-id')?.value.trim() || '';
    const name = document.getElementById('printer-name').value.trim();
    const type = document.getElementById('printer-type').value;
    const ip = document.getElementById('printer-ip').value.trim();
    const apiKey = document.getElementById('printer-api-key').value.trim();
    const port = document.getElementById('printer-port').value.trim();
    const bambuCode = document.getElementById('printer-bambu-code').value.trim();
    const bambuSerial = document.getElementById('printer-bambu-serial')?.value.trim() || '';
    const bambuModel = document.getElementById('printer-bambu-model')?.value || 'A1';
    const elegooCc2Code = document.getElementById('printer-elegoo-cc2-code')?.value.trim() || '';
    const flashforgeSerial = document.getElementById('printer-flashforge-serial')?.value.trim() || '';
    const flashforgeCode = document.getElementById('printer-flashforge-code')?.value.trim() || '';

    if (!name || !ip || !type) {
        showToast(I18N.t('toast.fill_required') || 'Champs requis manquants', 'warning');
        return;
    }

    const config = {};
    if (type === 'klipper' && port) config.port = port;
    if (type === 'bambu') {
        config.code = bambuCode;
        config.serial = bambuSerial;
        config.model = bambuModel;
        config.user = 'bblp';
    }
    if (type === 'elegoo_cc2') {
        config.code = elegooCc2Code || '123456';
    }
    if (type === 'flashforge') {
        config.serial = flashforgeSerial;
        config.code = flashforgeCode;
    }

    const isEdit = !!editId;
    const btn = document.getElementById('add-printer-submit-btn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t(isEdit ? 'printers.saving' : 'printers.adding') || '...'}`;
    }

    try {
        const res = await fetch(`${API}/api/printers${isEdit ? '/' + editId : ''}`, {
            method: isEdit ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },

            body: JSON.stringify({ name, type, ip, api_key: apiKey || (isEdit ? undefined : null), config })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(`✅ ${data.message}`, 'success');
            closeModal('modal-add-printer');
            document.getElementById('add-printer-form').reset();
            document.getElementById('printer-edit-id').value = '';
            loadPrinters();
        } else {
            showToast(`❌ ${data.error || I18N.t('toast.printer_add_error')}`, 'error');
        }
    } catch (err) {
        console.error('[Add/Edit Printer]', err);
        showToast(I18N.t('toast.connection_error'), 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = isEdit
                ? `<i class="fa-solid fa-check"></i> ${I18N.t('printers.save') || 'Enregistrer'}`
                : `<i class="fa-solid fa-plus"></i> ${I18N.t('printers.add')}`;
        }
    }
};


window.editPrinter = function(pid) {
    const p = printersList.find(pr => pr.id === pid);
    if (!p) return;

    document.getElementById('add-printer-form').reset();
    document.getElementById('printer-edit-id').value = pid;
    document.getElementById('printer-name').value = p.name || '';
    document.getElementById('printer-type').value = p.type || '';
    document.getElementById('printer-ip').value = p.ip || '';
    document.getElementById('printer-brand').value = '';

    const cfg = (p.config && typeof p.config === 'object') ? p.config : {};


    const apiKeyField = document.getElementById('printer-api-key');
    if (apiKeyField) {
        apiKeyField.value = '';
        apiKeyField.placeholder = I18N.t('printers.keep_current_key') || 'Laisser vide pour conserver la clé actuelle';
    }
    const portField = document.getElementById('printer-port');
    if (portField) portField.value = cfg.port || PRINTER_DEFAULT_PORTS?.[p.type] || '7125';
    const bambuCodeField = document.getElementById('printer-bambu-code');
    if (bambuCodeField) bambuCodeField.value = cfg.code || '';
    const bambuSerialField = document.getElementById('printer-bambu-serial');
    if (bambuSerialField) bambuSerialField.value = cfg.serial || '';
    const bambuModelField = document.getElementById('printer-bambu-model');
    if (bambuModelField) bambuModelField.value = cfg.model || 'A1';
    const elegooCc2CodeField = document.getElementById('printer-elegoo-cc2-code');
    if (elegooCc2CodeField) elegooCc2CodeField.value = cfg.code || '';
    const flashforgeSerialField = document.getElementById('printer-flashforge-serial');
    if (flashforgeSerialField) flashforgeSerialField.value = cfg.serial || '';
    const flashforgeCodeField = document.getElementById('printer-flashforge-code');
    if (flashforgeCodeField) flashforgeCodeField.value = cfg.code || '';

    togglePrinterFields();

    const title = document.getElementById('add-printer-modal-title');
    if (title) title.textContent = I18N.t('printers.edit') || 'Modifier l\'imprimante';
    const submitBtn = document.getElementById('add-printer-submit-btn');
    if (submitBtn) submitBtn.innerHTML = `<i class="fa-solid fa-check"></i> ${I18N.t('printers.save') || 'Enregistrer'}`;

    openModal('modal-add-printer');
};


window.loadStats = async function () {
    const loading = document.getElementById('stats-loading');
    const content = document.getElementById('stats-content');
    loading?.classList.remove('hidden');
    content?.classList.add('hidden');
    try {
        const res  = await fetch(`${API}/api/stats`);
        const data = await res.json();
        if (!res.ok) { showToast(data.error || I18N.t('toast.stats_error'), 'error'); return; }

        document.getElementById('stat-total-files').textContent  = data.total_files.toLocaleString();
        document.getElementById('stat-total-size').textContent   = formatSize(data.total_size);
        document.getElementById('stat-favorites').textContent    = data.favorites.toLocaleString();
        document.getElementById('stat-new-month').textContent    = data.new_this_month.toLocaleString();
        document.getElementById('stat-total-prints').textContent = data.total_prints.toLocaleString();

        const totalCostEl = document.getElementById('stat-total-cost');
        if (totalCostEl) totalCostEl.textContent = formatCost(data.total_spent || 0);
        const avgCostEl = document.getElementById('stat-avg-cost');
        if (avgCostEl) avgCostEl.textContent = data.avg_cost_per_print != null ? formatCost(data.avg_cost_per_print) : '—';
        const failedCostEl = document.getElementById('stat-failed-cost');
        if (failedCostEl) {
            failedCostEl.textContent = formatCost(data.failed_prints_cost || 0);
            failedCostEl.title = data.failed_prints_count
                ? _t2('stats.failed_cost_hint', `Sur ${data.failed_prints_count} impression(s) marquée(s) en échec`, { count: data.failed_prints_count })
                : '';
        }

        const fmtEl = document.getElementById('stat-formats');
        const fmtColors = { '.stl':'#63b3ed', '.3mf':'#68d391', '.obj':'#f6ad55', '.zip':'#fc8181', '.rar':'#b794f4' };
        const total = data.total_files || 1;
        fmtEl.innerHTML = Object.entries(data.by_format)
            .sort((a,b) => b[1]-a[1])
            .map(([ext, cnt]) => {
                const pct = Math.round(cnt / total * 100);
                const col = fmtColors[ext] || '#a0aec0';
                return `<div class="stat-fmt-row">
                    <span class="stat-fmt-ext" style="color:${col};">${ext.replace('.','').toUpperCase()}</span>
                    <div class="stat-fmt-bar-wrap">
                        <div class="stat-fmt-bar" style="width:${pct}%;background:${col};"></div>
                    </div>
                    <span class="stat-fmt-count">${cnt} <span style="color:var(--text-muted);font-size:11px;">(${pct}%)</span></span>
                </div>`;
            }).join('') || `<p style="color:var(--text-muted);font-size:13px;">${I18N.t('library.no_files')}</p>`;

        const topEl = document.getElementById('stat-top-printed');
        if (data.top_printed?.length) {
            const maxCnt = data.top_printed[0].count;
            topEl.innerHTML = data.top_printed.map((f, i) => `
                <div class="stat-top-row">
                    <span class="stat-top-rank">#${i+1}</span>
                    <span class="stat-top-name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</span>
                    <span class="stat-top-count">${f.count}×</span>
                </div>`).join('');
        } else {
            topEl.innerHTML = `<p style="color:var(--text-muted);font-size:13px;">${I18N.t('stats.no_slicer_sends')}</p>`;
        }

        const platEl = document.getElementById('stat-platforms');
        if (platEl) {
            const platColors = { 'Thingiverse': '#0d9bf0', 'Printables': '#fa6831', 'MakerWorld': '#22c55e' };
            const platIcons = { 'Thingiverse': 'fa-cube', 'Printables': 'fa-print', 'MakerWorld': 'fa-globe' };
            const platEntries = Object.entries(data.by_platform || {}).sort((a,b) => b[1]-a[1]);
            if (platEntries.length) {
                const platTotal = platEntries.reduce((s,[,v]) => s+v, 0) || 1;
                platEl.innerHTML = platEntries.map(([name, cnt]) => {
                    const pct = Math.round(cnt / platTotal * 100);
                    const col = platColors[name] || '#a0aec0';
                    const icon = platIcons[name] || 'fa-download';
                    return `<div class="stat-fmt-row">
                        <span class="stat-fmt-ext" style="color:${col};min-width:90px;"><i class="fa-solid ${icon}"></i> ${escapeHtml(name)}</span>
                        <div class="stat-fmt-bar-wrap">
                            <div class="stat-fmt-bar" style="width:${pct}%;background:${col};"></div>
                        </div>
                        <span class="stat-fmt-count">${cnt} <span style="color:var(--text-muted);font-size:11px;">(${pct}%)</span></span>
                    </div>`;
                }).join('');
            } else {
                platEl.innerHTML = `<p style="color:var(--text-muted);font-size:13px;">${I18N.t('stats.no_platform')}<br><span style="font-size:11px;">${I18N.t('stats.platform_hint')}</span></p>`;
            }
        }

        const relEl = document.getElementById('stat-profile-reliability');
        if (relEl) {
            const rel = data.profile_reliability || [];
            if (rel.length) {
                relEl.innerHTML = rel.map(p => {
                    const hasRate = p.success_rate !== null && p.success_rate !== undefined;
                    const rate = hasRate ? p.success_rate : null;
                    const col = !hasRate ? '#a0aec0' : rate >= 80 ? '#68d391' : rate >= 50 ? '#f6ad55' : '#fc8181';
                    const rateLabel = hasRate ? `${rate}%` : I18N.t('stats.profile_reliability_unrated') || 'non noté';
                    const detail = `${p.success}✓ / ${p.failed}✗${p.unrated ? ` / ${p.unrated} ${I18N.t('stats.profile_reliability_unrated_short') || 'non notées'}` : ''}`;
                    return `<div class="stat-top-row" title="${escapeHtml(detail)}">
                        <span class="stat-top-name" style="flex:1;" title="${escapeHtml(p.name)}">${escapeHtml(p.name)}</span>
                        <span class="stat-top-count" style="color:${col};font-weight:600;">${rateLabel}</span>
                    </div>`;
                }).join('');
            } else {
                relEl.innerHTML = `<p style="color:var(--text-muted);font-size:13px;">${I18N.t('stats.profile_reliability_empty') || "Note tes impressions dans l'Historique pour voir apparaître ce classement."}</p>`;
            }
        }

        loading?.classList.add('hidden');
        content?.classList.remove('hidden');
    } catch(e) {
        loading?.classList.add('hidden');
        showToast(I18N.t('toast.connection_error'), 'error');
    }
};


let _historyOffset = 0;
let _historyEntries = [];
const HISTORY_LIMIT = 30;


function _getRatingReasonLabels() {
    return {
        warping:          _t3('history.reason_warping', 'Décollement / warping'),
        stringing:        _t3('history.reason_stringing', 'Filage (stringing)'),
        layer_shift:      _t3('history.reason_layer_shift', 'Décalage de couches'),
        spaghetti:        _t3('history.reason_spaghetti', 'Spaghetti'),
        support_failure:  _t3('history.reason_support_failure', 'Échec des supports'),
        adhesion:         _t3('history.reason_adhesion', 'Mauvaise adhérence plateau'),
        other:            _t3('history.reason_other', 'Autre'),
    };
}

function _renderHistoryCostBadge(entry) {
    if (entry.total_cost != null) {
        return `<span onclick="toggleCostEditor(${entry.id})" style="cursor:pointer;" title="${I18N.t('cost.click_to_edit') || 'Cliquer pour modifier'}">
            <i class="fa-solid fa-coins"></i> ${formatCost(entry.total_cost)}
        </span>`;
    }
    return `<span onclick="toggleCostEditor(${entry.id})" style="cursor:pointer; color:var(--text-muted);" title="${I18N.t('cost.click_to_add') || 'Renseigner le coût'}">
        <i class="fa-solid fa-circle-plus"></i> ${I18N.t('cost.add_cost') || 'Coût'}
    </span>`;
}

function toggleCostEditor(id) {
    const el = document.getElementById(`hcost-${id}`);
    if (!el) return;
    if (el.dataset.editing === '1') {
        _historyLastData = _historyLastData || {};
        const entry = (_historyEntries || []).find(e => e.id === id);
        el.innerHTML = _renderHistoryCostBadge(entry || {});
        el.dataset.editing = '0';
        return;
    }
    const entry = (_historyEntries || []).find(e => e.id === id) || {};
    el.dataset.editing = '1';
    el.innerHTML = `
        <span style="display:inline-flex; align-items:center; gap:4px;" onclick="event.stopPropagation();">
            <input type="number" id="cost-mat-${id}" min="0" step="0.01" placeholder="${I18N.t('cost.material_label') || 'Matière'}"
                value="${entry.material_cost ?? ''}"
                style="width:64px; padding:3px 6px; background:var(--bg-input); border:1px solid var(--border); border-radius:4px; color:var(--text-primary); font-size:12px;">
            <input type="number" id="cost-elec-${id}" min="0" step="0.01" placeholder="${I18N.t('cost.elec_price_label') || 'Élec'}"
                value="${entry.elec_cost ?? ''}"
                style="width:64px; padding:3px 6px; background:var(--bg-input); border:1px solid var(--border); border-radius:4px; color:var(--text-primary); font-size:12px;">
            <button class="history-rate-btn" onclick="saveHistoryCost(${id})" title="${I18N.t('actions.confirm') || 'Confirmer'}"><i class="fa-solid fa-check"></i></button>
        </span>`;
}

async function saveHistoryCost(id) {
    const matInput = document.getElementById(`cost-mat-${id}`);
    const elecInput = document.getElementById(`cost-elec-${id}`);
    const material_cost = matInput && matInput.value !== '' ? parseFloat(matInput.value) : null;
    const elec_cost = elecInput && elecInput.value !== '' ? parseFloat(elecInput.value) : null;
    try {
        const res = await fetch(`${API}/api/print-history/${id}/cost`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ material_cost, elec_cost })
        });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || I18N.t('toast.error') || 'Erreur', 'error'); return; }

        const entry = (_historyEntries || []).find(e => e.id === id);
        if (entry) {
            entry.material_cost = data.material_cost;
            entry.elec_cost = data.elec_cost;
            entry.total_cost = data.total_cost;
        }
        const el = document.getElementById(`hcost-${id}`);
        if (el) {
            el.dataset.editing = '0';
            el.innerHTML = _renderHistoryCostBadge(entry || data);
        }
        showToast(I18N.t('toast.settings_saved') || 'Enregistré', 'success');
        if (typeof loadStats === 'function' && document.getElementById('page-stats')?.classList.contains('active')) {
            loadStats();
        }
    } catch (err) {
        showToast(I18N.t('toast.network_error') || 'Erreur de connexion', 'error');
    }
}
window.toggleCostEditor = toggleCostEditor;
window.saveHistoryCost = saveHistoryCost;

function _renderHistoryRatingBlock(entry) {
    if (entry.result === 'success') {
        return `<span class="history-rating-badge" style="color:#38c172;" title="${_t3('history.rated_success','Marqué réussi — cliquer pour modifier')}" onclick="_resetHistoryRating(${entry.id})"><i class="fa-solid fa-circle-check"></i></span>`;
    }
    if (entry.result === 'failed') {
        const reasonLabel = _getRatingReasonLabels()[entry.failure_reason] || entry.failure_reason || '';
        return `<span class="history-rating-badge" style="color:#e85d75;" title="${escapeHtml(reasonLabel)} — ${_t3('history.click_to_edit','cliquer pour modifier')}" onclick="_resetHistoryRating(${entry.id})"><i class="fa-solid fa-circle-xmark"></i></span>`;
    }
    if (entry.result === 'partial') {
        return `<span class="history-rating-badge" style="color:#f5a623;" title="${_t3('history.rated_partial','Marqué partiel — cliquer pour modifier')}" onclick="_resetHistoryRating(${entry.id})"><i class="fa-solid fa-circle-half-stroke"></i></span>`;
    }
    return `
        <div class="history-rating-pending" id="rating-pending-${entry.id}">
            <button class="history-rate-btn history-rate-success" onclick="rateHistoryEntry(${entry.id}, 'success')" title="${_t3('history.rate_success','Impression réussie')}">
                <i class="fa-solid fa-circle-check"></i>
            </button>
            <button class="history-rate-btn history-rate-fail" onclick="toggleFailureReasonPicker(${entry.id})" title="${_t3('history.rate_failed','Impression ratée')}">
                <i class="fa-solid fa-circle-xmark"></i>
            </button>
        </div>
    `;
}

function _resetHistoryRating(id) {
    const el = document.getElementById(`hentry-${id}`)?.querySelector('.history-entry-rating');
    if (!el) return;
    el.innerHTML = `
        <div class="history-rating-pending" id="rating-pending-${id}">
            <button class="history-rate-btn history-rate-success" onclick="rateHistoryEntry(${id}, 'success')" title="${_t3('history.rate_success','Impression réussie')}">
                <i class="fa-solid fa-circle-check"></i>
            </button>
            <button class="history-rate-btn history-rate-fail" onclick="toggleFailureReasonPicker(${id})" title="${_t3('history.rate_failed','Impression ratée')}">
                <i class="fa-solid fa-circle-xmark"></i>
            </button>
        </div>
    `;
}

function toggleFailureReasonPicker(id) {
    const wrap = document.getElementById(`rating-pending-${id}`);
    if (!wrap) return;
    wrap.innerHTML = `
        <select id="failure-reason-${id}" class="history-reason-select" onchange="_onFailureReasonChange(${id})">
            ${Object.entries(_getRatingReasonLabels()).map(([k, label]) => `<option value="${k}">${escapeHtml(label)}</option>`).join('')}
        </select>
        <input type="text" id="failure-reason-custom-${id}" class="history-reason-select hidden" style="width:140px;"
            placeholder="${_t3('history.reason_custom_placeholder','Préciser...')}" maxlength="100"
            onkeydown="if(event.key==='Enter'){event.preventDefault();confirmFailureRating(${id});}">
        <button class="history-rate-btn" onclick="confirmFailureRating(${id})" title="${_t3('actions.confirm','Confirmer')}"><i class="fa-solid fa-check"></i></button>
    `;
}

function _onFailureReasonChange(id) {
    const sel = document.getElementById(`failure-reason-${id}`);
    const custom = document.getElementById(`failure-reason-custom-${id}`);
    if (!sel || !custom) return;
    if (sel.value === 'other') {
        custom.classList.remove('hidden');
        custom.focus();
    } else {
        custom.classList.add('hidden');
    }
}
window._onFailureReasonChange = _onFailureReasonChange;

function confirmFailureRating(id) {
    const sel = document.getElementById(`failure-reason-${id}`);
    const custom = document.getElementById(`failure-reason-custom-${id}`);
    let reason = sel ? sel.value : 'other';
    if (reason === 'other' && custom && custom.value.trim()) {
        reason = custom.value.trim();
    }
    rateHistoryEntry(id, 'failed', reason);
}

async function rateHistoryEntry(id, result, failureReason) {
    try {
        const res = await fetch(`${API}/api/print-history/${id}/rate`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ result, failure_reason: failureReason || '' })
        });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || _t3('toast.error', 'Erreur'), 'error'); return; }

        const el = document.getElementById(`hentry-${id}`)?.querySelector('.history-entry-rating');
        if (el) {
            el.innerHTML = _renderHistoryRatingBlock({ id, result, failure_reason: failureReason || '' });
        }
        showToast(_t3('toast.rating_saved', 'Notation enregistrée, merci !'), 'success');
    } catch (err) {
        showToast(_t3('toast.connection_error', 'Erreur de connexion'), 'error');
    }
}

window.loadHistory = async function (reset = true) {
    if (reset) {
        _historyOffset = 0;
        _historyEntries = [];
        document.getElementById('history-list').innerHTML = '';
        document.getElementById('history-list').classList.add('hidden');
        document.getElementById('history-empty').classList.add('hidden');
        document.getElementById('history-load-more').classList.add('hidden');
    }
    document.getElementById('history-loading')?.classList.remove('hidden');
    try {
        const res  = await fetch(`${API}/api/print-history?limit=${HISTORY_LIMIT}&offset=${_historyOffset}`);
        const data = await res.json();
        document.getElementById('history-loading')?.classList.add('hidden');
        if (!res.ok) { showToast(data.error || I18N.t('toast.history_error'), 'error'); return; }
        if (data.total === 0) {
            document.getElementById('history-empty').classList.remove('hidden');
            return;
        }
        const badge = document.getElementById('history-count');
        if (badge) { badge.textContent = data.total; badge.style.display = data.total > 0 ? 'inline-block' : 'none'; }

        const listEl = document.getElementById('history-list');
        listEl.classList.remove('hidden');
        let lastDate = '';
        data.history.forEach(entry => {
            _historyEntries.push(entry);
            const d = new Date(entry.sent_at);
            const dateStr = d.toLocaleDateString(I18N.lang, { weekday:'long', day:'numeric', month:'long', year:'numeric' });
            if (dateStr !== lastDate) {
                listEl.insertAdjacentHTML('beforeend', `<div class="history-date-sep">${dateStr}</div>`);
                lastDate = dateStr;
            }
            const timeStr = d.toLocaleTimeString(I18N.lang, { hour:'2-digit', minute:'2-digit' });
            const extColor = { '.stl':'#63b3ed', '.3mf':'#68d391', '.obj':'#f6ad55' }[entry.file_ext] || '#a0aec0';
            const platformIcons = { 'Thingiverse': 'fa-cube', 'Printables': 'fa-print', 'MakerWorld': 'fa-globe' };
            const platformColors = { 'Thingiverse': '#0d9bf0', 'Printables': '#fa6831', 'MakerWorld': '#22c55e' };
            const platformBadge = entry.source_platform
                ? `<span class="history-platform-badge" style="background:${platformColors[entry.source_platform] || '#a0aec0'}22;color:${platformColors[entry.source_platform] || '#a0aec0'};border:1px solid ${platformColors[entry.source_platform] || '#a0aec0'}44;">
                       <i class="fa-solid ${platformIcons[entry.source_platform] || 'fa-download'}"></i> ${entry.source_platform}
                   </span>`
                : '';
            const costBadge = `<span class="history-entry-cost" id="hcost-${entry.id}">${_renderHistoryCostBadge(entry)}</span>`;
            listEl.insertAdjacentHTML('beforeend', `
                <div class="history-entry" id="hentry-${entry.id}">
                    <div class="history-entry-icon" style="background:${extColor}22;color:${extColor};">
                        <i class="fa-solid fa-cube"></i>
                    </div>
                    <div class="history-entry-body">
                        <div class="history-entry-name" title="${escapeHtml(entry.file_path)}">${escapeHtml(entry.file_name)}</div>
                        <div class="history-entry-meta">
                            <span><i class="fa-solid fa-scissors"></i> ${escapeHtml(entry.slicer || I18N.t('common.unknown'))}</span>
                            <span><i class="fa-solid fa-weight-scale"></i> ${formatSize(entry.file_size)}</span>
                            <span class="history-entry-ext" style="color:${extColor};">${(entry.file_ext||'').replace('.','').toUpperCase()}</span>
                            ${costBadge}
                            ${platformBadge}
                        </div>
                    </div>
                    <div class="history-entry-time">${timeStr}</div>
                    <div class="history-entry-rating">${_renderHistoryRatingBlock(entry)}</div>
                    <button class="history-entry-del" onclick="deleteHistoryEntry(${entry.id})" title="${I18N.t('actions.delete')}">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>`);
        });
        _historyOffset += data.history.length;
        const moreBtn = document.getElementById('history-load-more');
        if (_historyOffset < data.total) {
            moreBtn.classList.remove('hidden');
        } else {
            moreBtn.classList.add('hidden');
        }
    } catch(e) {
        document.getElementById('history-loading')?.classList.add('hidden');
        showToast(I18N.t('toast.connection_error'), 'error');
    }
};

window.loadMoreHistory = function () { loadHistory(false); };

async function loadDownloadHistory() {
    const sel = document.getElementById('download-history-select');
    const empty = document.getElementById('download-history-empty');
    if (!sel || !empty) return;
    try {
        const res = await fetch(`${API}/api/download-history`);
        if (!res.ok) return;
        const data = await res.json();
        if (!data.length) {
            sel.classList.add('hidden');
            empty.classList.remove('hidden');
            return;
        }
        empty.classList.add('hidden');
        sel.classList.remove('hidden');
        sel.innerHTML = '';
        const platformIcons = { 'Thingiverse': '\u25a0', 'Printables': '\u25a0', 'MakerWorld': '\u25a0' };
        data.forEach(entry => {
            const d = new Date(entry.downloaded_at);
            const dateStr = d.toLocaleDateString(I18N.lang, { day: '2-digit', month: '2-digit', year: 'numeric' });
            const timeStr = d.toLocaleTimeString(I18N.lang, { hour: '2-digit', minute: '2-digit' });
            const platform = entry.platform ? ` [${entry.platform}]` : '';
            const size = entry.file_size ? ` \u2014 ${(entry.file_size / 1024).toFixed(0)} ${I18N.t('units.KB')}` : '';
            const opt = document.createElement('option');
            opt.value = entry.file_path;
            opt.title = entry.file_path;
            opt.textContent = `${dateStr} ${timeStr}${platform}  \u2014  ${entry.file_name}${size}`;
            opt.dataset.path = entry.file_path;
            opt.dataset.name = entry.file_name;
            sel.appendChild(opt);
        });
    } catch (e) {
        console.error('[DownloadHistory]', e);
    }
}


document.getElementById('download-history-select')?.addEventListener('change', (e) => {
    const sel = e.target;
    const opt = sel.selectedOptions?.[0];
    const path = opt?.dataset.path || sel.value;
    const name = opt?.dataset.name;
    if (path) goToFileInLibrary(path, name);
});

window.goToFileInLibrary = function (filePath, fileName) {

    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-library')?.classList.add('active');
    if (typeof updateHeaderVisibilityForPage === 'function') updateHeaderVisibilityForPage('library');
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.nav-btn[data-page="library"]')?.classList.add('active');
    const headerTitle = document.getElementById('header-page-title');
    if (headerTitle) headerTitle.innerHTML = `<i class="fa-solid fa-layer-group"></i> ${I18N.t('nav.library')}`;
    closeMobileSidebar?.();


    showFavoritesOnly = false;
    if (typeof activeTypeFilters !== 'undefined') activeTypeFilters = [];
    if (typeof currentSizeFilter !== 'undefined') currentSizeFilter = null;
    if (typeof currentWeightFilter !== 'undefined') currentWeightFilter = null;
    if (typeof printStatusFilter !== 'undefined') printStatusFilter = '';
    if (typeof noThumbFilterOnly !== 'undefined') noThumbFilterOnly = false;
if (typeof failedThumbFilterOnly !== 'undefined') failedThumbFilterOnly = false;
    activeTagFilters?.clear?.();
    if (globalSearchInput) globalSearchInput.value = '';
    if (mobileSearchInput) mobileSearchInput.value = '';
    if (typeof setSearchMode === 'function') setSearchMode('normal');

    filteredFiles = [...allFiles];
    applySorting();
    renderFiles();
    updateSidebarCounts(filteredFiles);

    const exists = allFiles.some(f => f.path === filePath);
    if (!exists) {
        showToast(`${I18N.t('toast.file_not_found_library') || "Fichier introuvable dans la bibliothèque"}${fileName ? ' : ' + fileName : ''}`, 'warning');
        return;
    }

    let attempts = 0;
    const tryHighlight = () => {
        const card = document.querySelector(`.file-card[data-path="${CSS.escape(filePath)}"]`);
        if (card) {

            let parent = card.closest('.folder-block');
            while (parent) {
                if (!parent.classList.contains('folder-block--open')) {
                    parent.classList.add('folder-block--open');
                    const content = parent.querySelector(':scope > .folder-block-content');
                    if (content) {
                        content.style.maxHeight = content.scrollHeight + 5000 + 'px';
                        content.style.opacity = '1';
                    }
                }
                parent = parent.parentElement?.closest('.folder-block');
            }
            card.scrollIntoView({ behavior: 'auto', block: 'center' });
            card.classList.add('file-card--highlight');
            setTimeout(() => card.classList.remove('file-card--highlight'), 2600);
        } else if (attempts < 30) {
            attempts++;
            setTimeout(tryHighlight, 100);
        }
    };
    setTimeout(tryHighlight, 60);
};

window.clearDownloadHistory = async function () {
    showConfirmModal(I18N.t('history.confirm_clear_downloads'), async () => {
        try {
            const res = await fetch(`${API}/api/download-history/clear`, { method: 'DELETE' });
            if (res.ok) {
                loadDownloadHistory();
                showToast(I18N.t('history.cleared'), 'success');
            }
        } catch { showToast(I18N.t('toast.error'), 'error'); }
    });
};

window.deleteHistoryEntry = async function (id) {
    try {
        const res = await fetch(`${API}/api/print-history/${id}`, { method: 'DELETE' });
        if (res.ok) {
            document.getElementById(`hentry-${id}`)?.remove();
            showToast(I18N.t('history.entry_deleted'), 'success');
        }
    } catch { showToast(I18N.t('toast.error'), 'error'); }
};

window.clearAllHistory = async function () {
    showConfirmModal(I18N.t('history.confirm_clear_all'), async () => {
        try {
            const res = await fetch(`${API}/api/print-history/clear`, { method: 'DELETE' });
            if (res.ok) {
                loadHistory();
                showToast(I18N.t('history.cleared'), 'success');
            }
        } catch { showToast(I18N.t('toast.error'), 'error'); }
    });
};

let printersList = [];
let printerPollingInterval = null;
let printerMonitorInterval = null;
let currentMonitorPid = null;

function loadPrinters() {
    fetch(`${API}/api/printers`)
        .then(res => res.json())
        .then(data => {
            printersList = data;
            renderPrinters();
            if (printerPollingInterval) clearInterval(printerPollingInterval);
            printerPollingInterval = setInterval(refreshAllPrinters, 5000);
        });
}

function formatDuration(seconds) {
    if (!seconds || seconds <= 0) return '—';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (h > 0) return `${h}h ${m.toString().padStart(2,'0')}m ${s.toString().padStart(2,'0')}s`;
    if (m > 0) return `${m}m ${s.toString().padStart(2,'0')}s`;
    return `${s}s`;
}

function renderPrinters() {
    const grid = document.getElementById('printers-grid');
    if (!grid) return;
    if (printersList.length === 0) {
        grid.innerHTML = `<div class="empty-state"><i class="fa-solid fa-print"></i><p>${I18N.t('printers.none')}</p></div>`;
        _populatePrinterSelects();
        return;
    }
    grid.innerHTML = printersList.map(p => `
        <div class="printer-card" data-id="${p.id}" style="cursor:pointer" onclick="openPrinterMonitor(${p.id})">
            <div class="printer-header">
                <i class="mdi ${getPrinterIcon(p.type)}" style="font-size:22px;"></i>
                <span class="printer-name">${escapeHtml(p.name)}</span>
                <span id="printer-status-${p.id}" class="printer-status ${p.is_connected ? 'connected' : 'disconnected'}">${p.is_connected ? I18N.t('printers.online') : I18N.t('printers.offline')}</span>
            </div>
            <div class="printer-body">
                <p style="font-size: 12px; color: var(--text-muted); margin-bottom:6px;">${p.ip}</p>
                <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted);">
                    <span id="card-status-${p.id}">—</span>
                    <span id="card-progress-${p.id}">0%</span>
                </div>
                <div class="progress-track" style="margin-top:6px">
                    <div class="progress-bar" id="progress-${p.id}" style="width: 0%;"></div>
                </div>
                <div style="display:flex; gap:10px; margin-top:8px; font-size:11px; color:var(--text-secondary);">
                    <span title="${I18N.t('printers.extruder')}">🔥 <span id="card-ext-${p.id}">--°C</span></span>
                    <span title="${I18N.t('printers.bed')}">🛏️ <span id="card-bed-${p.id}">--°C</span></span>
                </div>
                <div id="card-spools-${p.id}" class="printer-card-spools"></div>
            </div>
            <div class="printer-actions" onclick="event.stopPropagation()">
                <button class="btn btn-ghost btn-sm" onclick="openPrinterMonitor(${p.id})" title="${I18N.t('printers.monitoring')}"><i class="fa-solid fa-chart-line"></i></button>
                <button class="btn btn-ghost btn-sm" style="position:relative;" onclick="openMaintenanceModal(${p.id}, '${escapeHtml(p.name).replace(/'/g, "\\'")}', '${(p.brand || '').replace(/'/g, "\\'")}')" title="${_t3('printers.maintenance', 'Maintenance')}">
                    <i class="fa-solid fa-wrench"></i>
                    <span id="maintenance-badge-${p.id}" style="display:none; position:absolute; top:2px; right:2px; width:7px; height:7px; border-radius:50%; background:var(--danger);"></span>
                </button>
                <button class="btn btn-ghost btn-sm" onclick="refreshPrinterStatus(${p.id})" title="${I18N.t('actions.refresh')}"><i class="fa-solid fa-rotate"></i></button>
                <button class="btn btn-ghost btn-sm" onclick="editPrinter(${p.id})" title="${I18N.t('actions.edit') || 'Modifier'}"><i class="fa-solid fa-pen"></i></button>
                <button class="btn btn-ghost btn-sm" style="color:var(--danger)" onclick="deletePrinter(${p.id})" title="${I18N.t('actions.delete')}"><i class="fa-solid fa-trash"></i></button>
            </div>
        </div>
    `).join('');
    refreshAllPrinters();
    printersList.forEach(p => _checkMaintenanceBadge(p.id));
    _populatePrinterSelects();
}

function getPrinterIcon(type) {
    if (type === 'klipper') return 'mdi-printer-3d-nozzle';
    if (type === 'octoprint') return 'mdi-printer-3d-nozzle';
    if (type === 'bambu') return 'mdi-printer-3d-nozzle';
    return 'mdi-printer';
}


function _renderSpoolChips(ams) {
    if (!ams || !ams.length) return '';
    return ams.map(t => {
        const color = t.color ? `#${String(t.color).replace('#', '').substring(0, 6)}` : 'var(--text-muted)';
        const label = t.material || t.name || '—';
        let pct = null;
        if (typeof t.remain_pct === 'number' && t.remain_pct >= 0) {
            pct = Math.round(t.remain_pct);
        } else if (typeof t.remaining_g === 'number' && typeof t.tray_weight === 'number' && t.tray_weight > 0) {
            pct = Math.round((t.remaining_g / t.tray_weight) * 100);
        }
        const tooltip = `${t.name || label}${pct !== null ? ' · ' + pct + '%' : ''}`;
        return `<span class="spool-chip" title="${escapeHtml(tooltip)}">
            <span class="spool-chip-dot" style="background:${color};"></span>
            <span class="spool-chip-label">${escapeHtml(label)}</span>
            ${pct !== null ? `<span class="spool-chip-pct">${pct}%</span>` : ''}
        </span>`;
    }).join('');
}

let _refreshAllPrintersRunning = false;

async function refreshAllPrinters() {
    if (_refreshAllPrintersRunning) return;
    _refreshAllPrintersRunning = true;
    try {
        for (const p of printersList) {
            try {
                const res = await fetch(`${API}/api/printers/${p.id}/status`);
                const data = await res.json();

                const progressBar = document.getElementById(`progress-${p.id}`);
                const cardStatus = document.getElementById(`card-status-${p.id}`);
                const cardProg = document.getElementById(`card-progress-${p.id}`);
                const cardExt = document.getElementById(`card-ext-${p.id}`);
                const cardBed = document.getElementById(`card-bed-${p.id}`);
                const statusBadge = document.getElementById(`printer-status-${p.id}`);

                if (progressBar) progressBar.style.width = `${data.progress || 0}%`;
                if (cardProg) cardProg.textContent = `${Math.round(data.progress || 0)}%`;

                if (statusBadge) {


                    const isOnline = !['error', 'offline', 'timeout'].includes(data.status);
                    statusBadge.className = `printer-status ${isOnline ? 'connected' : 'disconnected'}`;
                    statusBadge.textContent = isOnline ? I18N.t('printers.online') : I18N.t('printers.offline');
                    p.is_connected = isOnline;
                }

                if (cardStatus) {
                    const statusMap = {
                        printing: `🖨️ ${I18N.t('printers.status.printing')}`,
                        idle: `✅ ${I18N.t('printers.status.idle')}`,
                        paused: `⏸️ ${I18N.t('printers.status.paused')}`,
                        error: `❌ ${I18N.t('printers.status.error')}`,
                        offline: `🔌 ${I18N.t('printers.status.offline')}`,
                        timeout: `⏳ ${I18N.t('printers.status.timeout')}`
                    };
                    cardStatus.textContent = statusMap[data.status] || data.status;
                }

                if (cardExt) cardExt.textContent = `${data.temps?.extruder?.current || 0}°C`;
                if (cardBed) cardBed.textContent = `${data.temps?.bed?.current || 0}°C`;

                const cardSpools = document.getElementById(`card-spools-${p.id}`);
                if (cardSpools) cardSpools.innerHTML = _renderSpoolChips(data.ams);

                if (currentMonitorPid === p.id) updateMonitorUI(data);
            } catch (_) {  }
        }
    } finally {
        _refreshAllPrintersRunning = false;
    }
}


let _currentMaintenancePid = null;

async function _checkMaintenanceBadge(pid) {
    try {
        const res = await fetch(`${API}/api/printers/${pid}/maintenance`);
        if (!res.ok) return;
        const data = await res.json();
        const badge = document.getElementById(`maintenance-badge-${pid}`);
        if (!badge) return;
        const hasDue = (data.tasks || []).some(t => t.due);
        badge.style.display = hasDue ? 'block' : 'none';
    } catch (err) {  }
}

function openMaintenanceModal(pid, printerName, brand) {
    _currentMaintenancePid = pid;
    let modal = document.getElementById('modal-maintenance');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modal-maintenance';
        modal.className = 'modal hidden';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3><i class="fa-solid fa-wrench"></i> <span data-i18n="printers.maintenance">Maintenance</span> — <span id="maintenance-printer-name"></span></h3>
                    <button class="modal-close" onclick="closeModal('modal-maintenance')">&times;</button>
                </div>
                <div class="modal-body">
                    <div style="margin-bottom:14px; padding:12px; background:var(--bg-input); border:1px solid var(--border); border-radius:var(--radius);">
                        <label style="font-size:12px; font-weight:600; display:block; margin-bottom:6px;">
                            <i class="fa-solid fa-industry"></i> <span data-i18n="printers.maintenance_brand_label">Marque de l'imprimante</span>
                        </label>
                        <select id="maintenance-brand-select" class="settings-select" style="width:100%; margin-bottom:4px;" onchange="onMaintenanceBrandChange()">
                            <option value="" data-i18n="printers.maintenance_brand_none">— Sélectionner —</option>
                            <option value="bambu">Bambu Lab</option>
                            <option value="prusa">Prusa Research</option>
                            <option value="creality">Creality</option>
                            <option value="anycubic">Anycubic</option>
                            <option value="elegoo">Elegoo</option>
                            <option value="voron" data-i18n="printers.maintenance_brand_voron">Voron / DIY</option>
                            <option value="generic" data-i18n="printers.maintenance_brand_generic">Autre / Générique</option>
                        </select>
                        <div id="maintenance-brand-recommendations"></div>
                    </div>

                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; padding:10px 12px; background:var(--bg-input); border:1px solid var(--border); border-radius:var(--radius);">
                        <div style="font-size:13px;">
                            <i class="fa-solid fa-clock"></i> <span data-i18n="printers.maintenance_total_hours">Heures d'impression cumulées</span> :
                            <strong id="maintenance-total-hours">—</strong>
                            <span id="maintenance-hours-source" style="font-size:10.5px; color:var(--text-muted); margin-left:4px;"></span>
                        </div>
                        <div style="display:flex; gap:6px; align-items:center;">
                            <input type="number" id="maintenance-add-hours-input" placeholder="+h" min="0.1" step="0.5" style="width:70px; font-size:12px;">
                            <button class="btn btn-ghost btn-sm" onclick="addManualHours()" title="${_t3('printers.maintenance_add_hours', 'Ajouter des heures manuellement')}">
                                <i class="fa-solid fa-plus"></i>
                            </button>
                        </div>
                    </div>

                    <div id="maintenance-tasks-list" style="display:flex; flex-direction:column; gap:8px; margin-bottom:16px;"></div>

                    <div style="padding-top:14px; border-top:1px solid var(--border);">
                        <label style="font-size:13px; font-weight:500;" data-i18n="printers.maintenance_new_task">Nouvelle tâche</label>
                        <div style="display:flex; gap:8px; margin-top:8px; flex-wrap:wrap; align-items:flex-end;">
                            <label style="display:flex; flex-direction:column; gap:3px; font-size:11px; color:var(--text-muted); flex:1; min-width:140px;">
                                <span data-i18n="printers.maintenance_task_name">Nom (ex: Changer la buse)</span>
                                <input type="text" id="maintenance-new-name" maxlength="100">
                            </label>
                            <label style="display:flex; flex-direction:column; gap:3px; font-size:11px; color:var(--text-muted);">
                                <span data-i18n="printers.maintenance_every_hours">Tous les (h)</span>
                                <input type="number" id="maintenance-new-hours" min="1" step="1" style="width:80px;">
                            </label>
                            <label style="display:flex; flex-direction:column; gap:3px; font-size:11px; color:var(--text-muted);">
                                <span data-i18n="printers.maintenance_every_days">Tous les (jours)</span>
                                <input type="number" id="maintenance-new-days" min="1" step="1" style="width:80px;">
                            </label>
                            <button class="btn btn-primary btn-sm" onclick="addMaintenanceTask()">
                                <i class="fa-solid fa-plus"></i> <span data-i18n="actions.add">Ajouter</span>
                            </button>
                        </div>
                        <p class="settings-hint" style="margin-top:6px;" data-i18n="printers.maintenance_hint">Renseigne un intervalle en heures et/ou en jours — la tâche s'affichera comme à faire dès que l'un des deux est dépassé.</p>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => { if (e.target === modal) closeModal('modal-maintenance'); });
    }
    document.getElementById('maintenance-printer-name').textContent = printerName || '';
    const brandSelect = document.getElementById('maintenance-brand-select');
    if (brandSelect) brandSelect.value = brand || '';
    renderMaintenanceBrandRecommendations(brand || '');
    openModal('modal-maintenance');
    loadMaintenanceTasks(pid);
}

const PRINTER_MAINTENANCE_RECOMMENDATIONS = {
    bambu: [
        { nameKey: 'printers.maintenance_task.nettoyer_remplacer_la_buse', interval: '~250h', hours: 250 },
        { nameKey: 'printers.maintenance_task.graisser_les_rails_et_tiges', interval: '~500h', hours: 500 },
        { nameKey: 'printers.maintenance_task.nettoyer_la_plaque_de_plateau', interval: '~20h', hours: 20 },
        { nameKey: 'printers.maintenance_task.verifier_la_tension_des_courroies', interval: '~500h', hours: 500 },
        { nameKey: 'printers.maintenance_task.recalibrer_le_flux_niveau_du', interval: '~100h', hours: 100 },
        { nameKey: 'printers.maintenance_task.nettoyer_ventilateur_et_filtres_de', interval: '~250h', hours: 250 }
    ],
    prusa: [
        { nameKey: 'printers.maintenance_task.graisser_les_tiges_filetees_de', intervalKey: 'printers.maintenance_interval_months', intervalParams: { count: 3 }, days: 90 },
        { nameKey: 'printers.maintenance_task.graisser_les_barres_lisses_x', interval: '~250h', hours: 250 },
        { nameKey: 'printers.maintenance_task.verifier_retendre_les_courroies', interval: '~500h', hours: 500 },
        { nameKey: 'printers.maintenance_task.calibrer_le_first_layer_live', interval: '~100h', hours: 100 },
        { nameKey: 'printers.maintenance_task.nettoyer_remplacer_la_buse', interval: '~300h', hours: 300 },
        { nameKey: 'printers.maintenance_task.verifier_le_serrage_des_roulettes', interval: '~500h', hours: 500 }
    ],
    creality: [
        { nameKey: 'printers.maintenance_task.graisser_tiges_filetees_et_rails', interval: '~100h', hours: 100 },
        { nameKey: 'printers.maintenance_task.verifier_tendre_les_courroies_x', interval: '~200h', hours: 200 },
        { nameKey: 'printers.maintenance_task.re_nivelage_manuel_du_plateau', interval: '~25h', hours: 25 },
        { nameKey: 'printers.maintenance_task.nettoyer_remplacer_la_buse', interval: '~250h', hours: 250 },
        { nameKey: 'printers.maintenance_task.verifier_le_serrage_des_roulettes_2', interval: '~300h', hours: 300 }
    ],
    anycubic: [
        { nameKey: 'printers.maintenance_task.nettoyer_lubrifier_les_axes_lineaires', interval: '~150h', hours: 150 },
        { nameKey: 'printers.maintenance_task.verifier_la_tension_des_courroies', interval: '~250h', hours: 250 },
        { nameKey: 'printers.maintenance_task.recalibrer_le_nivellement_automatique', interval: '~30h', hours: 30 },
        { nameKey: 'printers.maintenance_task.nettoyer_remplacer_la_buse', interval: '~250h', hours: 250 }
    ],
    elegoo: [
        { nameKey: 'printers.maintenance_task.graisser_axes_et_vis', interval: '~150h', hours: 150 },
        { nameKey: 'printers.maintenance_task.verifier_la_tension_des_courroies', interval: '~250h', hours: 250 },
        { nameKey: 'printers.maintenance_task.nettoyer_remplacer_la_buse', interval: '~250h', hours: 250 },
        { nameKey: 'printers.maintenance_task.nivellement_du_plateau', interval: '~30h', hours: 30 }
    ],
    voron: [
        { nameKey: 'printers.maintenance_task.inspecter_graisser_les_rails_lineaires', interval: '~150h', hours: 150 },
        { nameKey: 'printers.maintenance_task.verifier_la_tension_des_courroies_2', interval: '~200h', hours: 200 },
        { nameKey: 'printers.maintenance_task.controler_le_serrage_de_la', interval: '~300h', hours: 300 },
        { nameKey: 'printers.maintenance_task.verifier_l_alignement_du_portique', interval: '~500h', hours: 500 },
        { nameKey: 'printers.maintenance_task.nettoyer_remplacer_la_buse', interval: '~250h', hours: 250 }
    ],
    generic: [
        { nameKey: 'printers.maintenance_task.nettoyer_remplacer_la_buse', interval: '~250h', hours: 250 },
        { nameKey: 'printers.maintenance_task.graisser_les_axes', interval: '~200h', hours: 200 },
        { nameKey: 'printers.maintenance_task.verifier_la_tension_des_courroies', interval: '~200h', hours: 200 },
        { nameKey: 'printers.maintenance_task.verifier_le_serrage_general_des', interval: '~300h', hours: 300 }
    ]
};

function renderMaintenanceBrandRecommendations(brand) {
    const box = document.getElementById('maintenance-brand-recommendations');
    if (!box) return;
    const items = PRINTER_MAINTENANCE_RECOMMENDATIONS[brand];
    if (!brand || !items) {
        box.innerHTML = `<p class="settings-hint" style="margin:0;" data-i18n="printers.maintenance_brand_hint">Choisis la marque de ton imprimante pour afficher les recommandations de maintenance du constructeur.</p>`;
        return;
    }
    box.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:5px; margin-top:6px;">
            ${items.map(it => { const taskName = I18N.t(it.nameKey); const interval = it.intervalKey ? I18N.t(it.intervalKey, it.intervalParams || {}) : it.interval; return `
                <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; font-size:12px; padding:5px 8px; background:var(--bg-secondary); border-radius:6px;">
                    <span>${escapeHtml(taskName)} <span style="color:var(--text-muted); font-size:11px;">— ${escapeHtml(interval)}</span></span>
                    <button class="btn btn-ghost btn-sm" style="padding:2px 8px;" onclick="quickAddRecommendedTask('${escapeHtml(taskName).replace(/'/g, "\\'")}', ${it.hours || 'null'}, ${it.days || 'null'})" title="${_t3('printers.maintenance_brand_add_task', 'Ajouter à mon suivi')}">
                        <i class="fa-solid fa-plus"></i>
                    </button>
                </div>
            `; }).join('')}
        </div>
        <p class="settings-hint" style="margin:8px 0 0;" data-i18n="printers.maintenance_brand_disclaimer">Recommandations générales à titre indicatif — vérifie la documentation officielle de ton imprimante pour des valeurs précises.</p>
    `;
}

async function onMaintenanceBrandChange() {
    if (!_currentMaintenancePid) return;
    const brand = document.getElementById('maintenance-brand-select')?.value || '';
    renderMaintenanceBrandRecommendations(brand);
    try {
        await fetch(`${API}/api/printers/${_currentMaintenancePid}/brand`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ brand })
        });
        if (typeof loadPrinters === 'function') loadPrinters();
    } catch (e) {
        showToast(I18N.t('toast.connection_error'), 'error');
    }
}

async function quickAddRecommendedTask(name, hours, days) {
    if (!_currentMaintenancePid) return;
    try {
        const res = await fetch(`${API}/api/printers/${_currentMaintenancePid}/maintenance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, interval_hours: hours || null, interval_days: days || null })
        });
        if (!res.ok) { const d = await res.json(); showToast(d.error || I18N.t('toast.error'), 'error'); return; }
        showToast(_t3('printers.maintenance_task_added', 'Tâche ajoutée à ton suivi'), 'success');
        loadMaintenanceTasks(_currentMaintenancePid);
        _checkMaintenanceBadge(_currentMaintenancePid);
    } catch (e) {
        showToast(I18N.t('toast.connection_error'), 'error');
    }
}

async function loadMaintenanceTasks(pid) {
    const list = document.getElementById('maintenance-tasks-list');
    if (!list) return;
    list.innerHTML = `<div style="text-align:center; padding:14px; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i></div>`;
    try {
        const res = await fetch(`${API}/api/printers/${pid}/maintenance`);
        const data = await res.json();
        if (!res.ok) {
            list.innerHTML = `<div style="color:var(--danger); font-size:12.5px;">${escapeHtml(data.error || _t3('toast.error', 'Erreur'))}</div>`;
            return;
        }
        document.getElementById('maintenance-total-hours').textContent = `${data.total_print_hours}h`;
        const sourceEl = document.getElementById('maintenance-hours-source');
        if (sourceEl) {
            if (data.hours_source === 'moonraker') {
                sourceEl.innerHTML = `<i class="fa-solid fa-circle-check" style="color:#38c172;"></i> ${_t3('printers.maintenance_source_moonraker', 'valeur exacte (Moonraker)')}`;
            } else {
                sourceEl.innerHTML = `<i class="fa-solid fa-circle-info"></i> ${_t3('printers.maintenance_source_estimated', 'estimation Stellio')}`;
            }
        }
        renderMaintenanceTasks(data.tasks || []);
    } catch (err) {
        list.innerHTML = `<div style="color:var(--danger); font-size:12.5px;">${_t3('toast.connection_error', 'Erreur de connexion')}</div>`;
    }
}

function renderMaintenanceTasks(tasks) {
    const list = document.getElementById('maintenance-tasks-list');
    if (!list) return;
    if (!tasks.length) {
        list.innerHTML = `<p class="settings-hint" data-i18n="printers.maintenance_empty">Aucune tâche de maintenance configurée.</p>`;
        return;
    }
    window._maintenanceTasksCache = tasks;
    list.innerHTML = tasks.map(t => {
        const ratio = Math.min(t.progress_ratio || 0, 1);
        const barColor = t.due ? 'var(--danger)' : (ratio > 0.75 ? '#f5a623' : 'var(--accent, #4f8cff)');
        const parts = [];
        if (t.interval_hours) parts.push(`${t.hours_since_reset ?? 0}h / ${t.interval_hours}h`);
        if (t.interval_days) parts.push(`${t.days_since_reset ?? 0}j / ${t.interval_days}j`);
        return `
            <div id="maintenance-task-row-${t.id}" style="padding:8px 10px; background:var(--bg-input); border:1px solid var(--border); border-radius:var(--radius);">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
                    <div style="font-size:13px; font-weight:600;">
                        ${t.due ? '<i class="fa-solid fa-triangle-exclamation" style="color:var(--danger);"></i> ' : ''}${escapeHtml(t.name)}
                    </div>
                    <div style="display:flex; gap:4px; flex-shrink:0;">
                        <button class="btn btn-ghost btn-sm" onclick="toggleEditMaintenanceTask(${t.id})" title="${_t3('printers.maintenance_edit', "Modifier l'intervalle")}">
                            <i class="fa-solid fa-pen"></i>
                        </button>
                        <button class="btn btn-ghost btn-sm" onclick="resetMaintenanceTask(${t.id})" title="${_t3('printers.maintenance_mark_done', 'Marquer comme fait')}">
                            <i class="fa-solid fa-check"></i>
                        </button>
                        <button class="btn btn-ghost btn-sm" onclick="deleteMaintenanceTask(${t.id})" title="${I18N.t('actions.delete')}">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </div>
                </div>
                <div id="maintenance-task-info-${t.id}" style="font-size:11px; color:var(--text-muted); margin-top:4px;">${parts.join(' · ')}</div>
                <div class="progress-track" style="margin-top:6px;">
                    <div class="progress-bar" style="width:${Math.round(ratio*100)}%; background:${barColor};"></div>
                </div>
            </div>
        `;
    }).join('');
}

function toggleEditMaintenanceTask(taskId) {
    const task = (window._maintenanceTasksCache || []).find(t => t.id === taskId);
    const infoEl = document.getElementById(`maintenance-task-info-${taskId}`);
    if (!task || !infoEl) return;
    infoEl.innerHTML = `
        <div style="display:flex; gap:6px; align-items:center; margin-top:2px; flex-wrap:wrap;">
            <label style="display:flex; align-items:center; gap:4px;">
                <span data-i18n="printers.maintenance_every_hours">Tous les (h)</span>
                <input type="number" id="edit-hours-${taskId}" value="${task.interval_hours ?? ''}" min="1" step="1" style="width:60px;">
            </label>
            <label style="display:flex; align-items:center; gap:4px;">
                <span data-i18n="printers.maintenance_every_days">Tous les (jours)</span>
                <input type="number" id="edit-days-${taskId}" value="${task.interval_days ?? ''}" min="1" step="1" style="width:60px;">
            </label>
            <button class="btn btn-primary btn-sm" onclick="saveMaintenanceTaskEdit(${taskId})"><i class="fa-solid fa-check"></i></button>
            <button class="btn btn-ghost btn-sm" onclick="loadMaintenanceTasks(_currentMaintenancePid)"><i class="fa-solid fa-xmark"></i></button>
        </div>
    `;
}

async function saveMaintenanceTaskEdit(taskId) {
    const hours = document.getElementById(`edit-hours-${taskId}`)?.value || null;
    const days = document.getElementById(`edit-days-${taskId}`)?.value || null;
    if (!hours && !days) { showToast(_t3('printers.maintenance_interval_required', "Renseigne au moins un intervalle (heures ou jours)"), 'error'); return; }
    try {
        const res = await fetch(`${API}/api/printers/maintenance/${taskId}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ interval_hours: hours, interval_days: days })
        });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || _t3('toast.error', 'Erreur'), 'error'); return; }
        showToast(_t3('printers.maintenance_updated', 'Intervalle mis à jour'), 'success');
        loadMaintenanceTasks(_currentMaintenancePid);
        _checkMaintenanceBadge(_currentMaintenancePid);
    } catch (err) {
        showToast(_t3('toast.connection_error', 'Erreur de connexion'), 'error');
    }
}

async function addMaintenanceTask() {
    if (!_currentMaintenancePid) return;
    const name = document.getElementById('maintenance-new-name').value.trim();
    const hours = document.getElementById('maintenance-new-hours').value;
    const days = document.getElementById('maintenance-new-days').value;
    if (!name) { showToast(_t3('printers.maintenance_name_required', 'Donne un nom à la tâche'), 'error'); return; }
    if (!hours && !days) { showToast(_t3('printers.maintenance_interval_required', "Renseigne au moins un intervalle (heures ou jours)"), 'error'); return; }
    try {
        const res = await fetch(`${API}/api/printers/${_currentMaintenancePid}/maintenance`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, interval_hours: hours || null, interval_days: days || null })
        });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || _t3('toast.error', 'Erreur'), 'error'); return; }
        document.getElementById('maintenance-new-name').value = '';
        document.getElementById('maintenance-new-hours').value = '';
        document.getElementById('maintenance-new-days').value = '';
        loadMaintenanceTasks(_currentMaintenancePid);
        _checkMaintenanceBadge(_currentMaintenancePid);
    } catch (err) {
        showToast(_t3('toast.connection_error', 'Erreur de connexion'), 'error');
    }
}

async function resetMaintenanceTask(taskId) {
    try {
        const res = await fetch(`${API}/api/printers/maintenance/${taskId}/reset`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || _t3('toast.error', 'Erreur'), 'error'); return; }
        showToast(_t3('printers.maintenance_done_saved', 'Entretien enregistré !'), 'success');
        loadMaintenanceTasks(_currentMaintenancePid);
        _checkMaintenanceBadge(_currentMaintenancePid);
    } catch (err) {
        showToast(_t3('toast.connection_error', 'Erreur de connexion'), 'error');
    }
}

async function deleteMaintenanceTask(taskId) {
    const ok = await showConfirmDialog(_t3('printers.maintenance_delete_confirm', 'Supprimer cette tâche de maintenance ?'), { danger: true });
    if (!ok) return;
    try {
        const res = await fetch(`${API}/api/printers/maintenance/${taskId}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || _t3('toast.error', 'Erreur'), 'error'); return; }
        loadMaintenanceTasks(_currentMaintenancePid);
        _checkMaintenanceBadge(_currentMaintenancePid);
    } catch (err) {
        showToast(_t3('toast.connection_error', 'Erreur de connexion'), 'error');
    }
}

async function addManualHours() {
    if (!_currentMaintenancePid) return;
    const input = document.getElementById('maintenance-add-hours-input');
    const hours = parseFloat(input.value);
    if (!hours || hours <= 0) { showToast(_t3('printers.maintenance_invalid_hours', "Nombre d'heures invalide"), 'error'); return; }
    try {
        const res = await fetch(`${API}/api/printers/${_currentMaintenancePid}/hours/add`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hours })
        });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || _t3('toast.error', 'Erreur'), 'error'); return; }
        input.value = '';
        loadMaintenanceTasks(_currentMaintenancePid);
    } catch (err) {
        showToast(_t3('toast.connection_error', 'Erreur de connexion'), 'error');
    }
}

const _maintenanceAlertedTaskIds = new Set();
let _maintenanceDueCheckInterval = null;

function startMaintenanceDueChecker() {
    if (_maintenanceDueCheckInterval) clearInterval(_maintenanceDueCheckInterval);
    checkMaintenanceDueGlobal();
    _maintenanceDueCheckInterval = setInterval(checkMaintenanceDueGlobal, 60000);
}

async function checkMaintenanceDueGlobal() {
    try {
        const res = await fetch(`${API}/api/printers/maintenance/due`);
        if (!res.ok) return;
        const data = await res.json();
        const stillDueIds = new Set((data.due || []).map(d => d.task_id));
        for (const id of [..._maintenanceAlertedTaskIds]) {
            if (!stillDueIds.has(id)) _maintenanceAlertedTaskIds.delete(id);
        }
        (data.due || []).forEach(d => {
            if (_maintenanceAlertedTaskIds.has(d.task_id)) return;
            _maintenanceAlertedTaskIds.add(d.task_id);
            showMaintenanceAlertPopup(d.printer_name, d.task_name);
        });
    } catch (err) {  }
}

function showMaintenanceAlertPopup(printerName, taskName) {
    const overlay = document.createElement('div');
    overlay.style.cssText = `position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); display: flex; align-items: center; justify-content: center; z-index: 100000; backdrop-filter: blur(5px);`;
    const popup = document.createElement('div');
    popup.style.cssText = `background: var(--bg-secondary); color: var(--text-primary); padding: 28px; border-radius: 14px; max-width: 420px; width: 90%; box-shadow: 0 12px 35px rgba(0,0,0,0.6); text-align: center; border: 1px solid var(--border);`;
    const message = _t3('printers.maintenance_popup_message', 'La maintenance pour l\'imprimante "{{name}}" est requise', { name: printerName })
        .replace('{{name}}', escapeHtml(printerName));
    popup.innerHTML = `
        <h3 style="margin:0 0 10px 0; font-size:19px; font-weight:600;"><i class="fa-solid fa-wrench" style="color:var(--danger);"></i> ${_t3('printers.maintenance_popup_title', 'Maintenance requise')}</h3>
        <p style="color:var(--text-muted); margin:0 0 6px 0; line-height:1.5; font-size:14px;">${message}</p>
        <p style="color:var(--text-secondary); margin:0 0 24px 0; font-size:13px;">${escapeHtml(taskName)}</p>
        <div style="display:flex; gap:10px; justify-content:center;">
            <button id="maintenance-alert-ok" class="btn btn-primary">${_t3('actions.confirm', 'Compris')}</button>
        </div>
    `;
    overlay.appendChild(popup);
    document.body.appendChild(overlay);
    const close = () => overlay.remove();
    document.getElementById('maintenance-alert-ok').addEventListener('click', close);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
}

function openPrinterMonitor(pid) {
    const printer = printersList.find(p => p.id === pid);
    if (!printer) return;
    currentMonitorPid = pid;
    let modal = document.getElementById('modal-printer-monitor');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modal-printer-monitor';
        modal.className = 'modal hidden';
        modal.innerHTML = `<div class="modal-content monitor-modal-content"><div class="modal-header"><h3><i class="fa-solid fa-gauge-high"></i> <span id="monitor-title">${I18N.t('printers.monitoring')}</span></h3><button class="modal-close" onclick="closePrinterMonitor()">×</button></div><div class="modal-body" id="monitor-body"><div style="text-align:center; padding:40px; color:var(--text-muted)"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><p style="margin-top:10px">${I18N.t('printers.connecting')}</p></div></div></div>`;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => { if (e.target === modal) closePrinterMonitor(); });
    }
    document.getElementById('monitor-title').textContent = `🖨️ ${printer.name}`;
    initMonitorUI(printer);
    openModal('modal-printer-monitor');
    if (printerMonitorInterval) clearInterval(printerMonitorInterval);
    fetchAndUpdateMonitor(pid);
    printerMonitorInterval = setInterval(() => fetchAndUpdateMonitor(pid), 2000);
}

function initMonitorUI(printer) {
    const body = document.getElementById('monitor-body');
    if (!body) return;
    const klipperUrl = printer ? `http://${printer.ip}` : '#';
    const klipperBtn = printer && printer.type === 'klipper' ? `<a href="${klipperUrl}" target="_blank" class="btn btn-sm" style="background:var(--accent); color:white; text-decoration:none; display:inline-flex; align-items:center; gap:6px;"><i class="fa-solid fa-external-link-alt"></i> Klipper</a>` : '';
    const octoprintUrl = printer ? `http://${printer.ip}` : '#';
    const octoprintBtn = printer && printer.type === 'octoprint' ? `<a href="${octoprintUrl}" target="_blank" class="btn btn-sm" style="background:var(--accent); color:white; text-decoration:none; display:inline-flex; align-items:center; gap:6px;"><i class="fa-solid fa-external-link-alt"></i> OctoPrint</a>` : '';

    body.innerHTML = `
     <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">
         <span id="monitor-status-badge" class="monitor-status-badge idle">
             <span id="monitor-live-dot" class="live-dot" style="display:none;"></span>
         <span id="monitor-status-label">${I18N.t('printers.connecting')}</span>
         </span>
         <div style="display:flex; gap:8px; align-items:center;">
            ${klipperBtn}
            ${octoprintBtn}
         </div>
     </div>
     <div id="printer-camera-container" class="monitor-card full" style="display:none;">
         <h4><i class="fa-solid fa-camera"></i> ${I18N.t('printers.camera')}</h4>
         <div id="camera-content" style="position:relative; width:100%; min-height:200px; background:#000; border-radius:8px; overflow:hidden; display:flex; align-items:center; justify-content:center;">
             <div style="color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t('common.loading')}</div>
         </div>
     </div>
     <div class="monitor-grid">
         <div class="monitor-card">
             <h4><i class="fa-solid fa-temperature-half"></i> ${I18N.t('printers.temperatures')}</h4>
             <div id="monitor-temps-container"></div>
         </div>
         <div class="monitor-card">
             <h4><i class="fa-solid fa-clock"></i> ${I18N.t('printers.progression')}</h4>
             <div class="monitor-progress-bar">
                 <div id="monitor-progress-fill" class="monitor-progress-fill" style="width: 0%"></div>
             </div>
             <div id="monitor-progress-pct" class="time-big">0%</div>
             <div class="stat-row">
                 <span class="stat-label">⏱️ ${I18N.t('printers.elapsed')}</span>
                 <span id="monitor-time-elapsed" class="stat-value">—</span>
             </div>
             <div class="stat-row">
                 <span class="stat-label">⏳ ${I18N.t('printers.remaining')}</span>
                 <span id="monitor-time-remaining" class="stat-value">—</span>
             </div>
             <div class="stat-row">
                 <span class="stat-label">📊 ${I18N.t('printers.total_estimated')}</span>
                 <span id="monitor-time-total" class="stat-value">—</span>
             </div>
         </div>
         <div class="monitor-card full">
             <h4><i class="fa-solid fa-history"></i> ${I18N.t('printers.last_print')}</h4>
             <div id="monitor-last-print-container">
                 <p style="color:var(--text-muted); font-size:13px">${I18N.t('common.loading')}</p>
             </div>
         </div>
     </div>
    `;
    loadPrinterCamera(currentMonitorPid);
}

function fetchAndUpdateMonitor(pid) {
    fetch(`${API}/api/printers/${pid}/status`)
        .then(res => res.json())
        .then(data => updateMonitorUI(data))
        .catch(() => {});
}

function updateMonitorUI(data) {
    const body = document.getElementById('monitor-body');
    if (!body) return;
    const statusClass = ['printing','idle','paused','error','offline','timeout'].includes(data.status) ? data.status : 'idle';
    const statusLabel = {
        printing: I18N.t('printers.status.printing_long'),
        idle: I18N.t('printers.status.idle'),
        paused: I18N.t('printers.status.paused'),
        complete: I18N.t('printers.status.complete'),
        error: I18N.t('printers.status.error'),
        offline: I18N.t('printers.status.offline'),
        timeout: I18N.t('printers.status.timeout'),
        unknown: I18N.t('printers.status.unknown')
    }[data.status] || data.status;
    const isPrinting = data.status === 'printing' || data.status === 'paused';
    const badge = document.getElementById('monitor-status-badge');
    if (badge) badge.className = `monitor-status-badge ${statusClass}`;
    const liveDot = document.getElementById('monitor-live-dot');
    if (liveDot) liveDot.style.display = isPrinting ? 'inline-block' : 'none';
    const statusLbl = document.getElementById('monitor-status-label');
    if (statusLbl) statusLbl.textContent = statusLabel;
    const tempsContainer = document.getElementById('monitor-temps-container');
    if (tempsContainer) {
        let tempsHtml = renderTempRow(I18N.t('printers.extruder'), data.temps?.extruder);
        tempsHtml += renderTempRow(I18N.t('printers.bed'), data.temps?.bed);
        if (data.temps?.chamber?.current > 0) tempsHtml += renderTempRow(I18N.t('printers.chamber'), data.temps?.chamber);
        tempsContainer.innerHTML = tempsHtml;
    }
    let bambuExtras = document.getElementById('monitor-bambu-extras');
    if (data.layers || (data.ams && data.ams.length > 0)) {
        if (!bambuExtras) {
            bambuExtras = document.createElement('div');
            bambuExtras.id = 'monitor-bambu-extras';
            bambuExtras.className = 'monitor-card full';
            const monitorGrid = document.querySelector('.monitor-grid');
            if (monitorGrid) monitorGrid.appendChild(bambuExtras);
        }
        let extrasHtml = '';
        if (data.layers && data.layers.total > 0) {
            extrasHtml += `<div class="stat-row"><span class="stat-label">📐 ${I18N.t('printer.layer_label')}</span><span class="stat-value">${data.layers.current} / ${data.layers.total}</span></div>`;
        }
        if (data.ams && data.ams.length > 0) {
            extrasHtml += `<h4 style="margin:10px 0 6px;font-size:13px;">🎨 ${I18N.t('printer.multimaterial_label') || 'Multi-matière'} — ${I18N.t('printer.filaments_label')}</h4><div style="display:flex;gap:8px;flex-wrap:wrap;">`;
            data.ams.forEach(t => {
                const color = t.color ? `#${t.color.substring(0,6)}` : 'var(--text-muted)';
                extrasHtml += `<div style="display:flex;align-items:center;gap:5px;font-size:12px;background:var(--bg-card);border-radius:6px;padding:4px 8px;"><span style="width:12px;height:12px;border-radius:50%;background:${color};display:inline-block;border:1px solid rgba(255,255,255,0.2);"></span><span>${t.material || '—'}</span></div>`;
            });
            extrasHtml += '</div>';
        }
        bambuExtras.innerHTML = extrasHtml;
    }
    const progressFill = document.getElementById('monitor-progress-fill');
    if (progressFill) progressFill.style.width = `${data.progress || 0}%`;
    const progressPct = document.getElementById('monitor-progress-pct');
    if (progressPct) progressPct.textContent = `${Math.round(data.progress || 0)}%`;
    const elapsedEl = document.getElementById('monitor-time-elapsed');
    if (elapsedEl) elapsedEl.textContent = formatDuration(data.time?.elapsed);
    const remainingEl = document.getElementById('monitor-time-remaining');
    if (remainingEl) remainingEl.textContent = formatDuration(data.time?.remaining);
    const totalEl = document.getElementById('monitor-time-total');
    if (totalEl) totalEl.textContent = formatDuration(data.time?.total);
    const lastPrintContainer = document.getElementById('monitor-last-print-container');
    if (lastPrintContainer && data.last_print) {
        if (data.last_print.filename) {
            let lpHtml = `<div class="stat-row"><span class="stat-label">${I18N.t('printers.last_print_file')}</span><span class="stat-value" style="font-size:12px">${escapeHtml(data.last_print.filename)}</span></div><div class="stat-row"><span class="stat-label">${I18N.t('printers.duration')}</span><span class="stat-value">${formatDuration(data.last_print.duration)}</span></div>`;
            if (data.last_print.finished_at) {
                lpHtml += `<div class="stat-row"><span class="stat-label">${I18N.t('printers.finished_at')}</span><span class="stat-value" style="font-size:12px">${new Date(data.last_print.finished_at * 1000).toLocaleString(I18N.lang)}</span></div>`;
            }
            lastPrintContainer.innerHTML = lpHtml;
        } else {
            lastPrintContainer.innerHTML = `<p style="color:var(--text-muted); font-size:13px">${I18N.t('printers.no_recent_print')}</p>`;
        }
    }
}

let cameraLoadedForPid = null;
async function loadPrinterCamera(pid) {
    if (cameraLoadedForPid === pid) return;
    const container = document.getElementById('printer-camera-container');
    const content = document.getElementById('camera-content');
    if (!container || !content) return;
    try {
        const res = await fetch(`${API}/api/printers/${pid}/camera`);
        if (!res.ok) { container.style.display = 'none'; return; }
        const camData = await res.json();
        if (!camData.available) { container.style.display = 'none'; cameraLoadedForPid = null; return; }
        cameraLoadedForPid = pid;
        container.style.display = 'block';
        const streamUrl = camData.stream_url || '';
        const snapshotUrl = camData.snapshot_url || '';
        if (streamUrl) {
            content.innerHTML = `<img src="${streamUrl}" alt="${camData.name || I18N.t('printers.camera')}" style="width:100%; height:auto; max-height:400px; object-fit:contain; display:block;" onerror="this.parentElement.innerHTML='<div style=\\'color:var(--danger);padding:20px;text-align:center;\\'>❌ ${I18N.t('printers.stream_unavailable')}</div>'">`;
        } else if (snapshotUrl) {
            const refreshSnapshot = () => {
                const img = content.querySelector('#camera-snapshot');
                if (img) img.src = snapshotUrl + (snapshotUrl.includes('?') ? '&' : '?') + '_t=' + Date.now();
            };
            content.innerHTML = `<img id="camera-snapshot" src="${snapshotUrl}?_t=${Date.now()}" alt="${camData.name || I18N.t('printers.camera')}" style="width:100%; height:auto; max-height:400px; object-fit:contain; display:block;" onerror="this.parentElement.innerHTML='<div style=\\'color:var(--danger);padding:20px;text-align:center;\\'>${I18N.t('printers.snapshot_unavailable')}</div>'">`;
            if (window.cameraRefreshInterval) clearInterval(window.cameraRefreshInterval);
            window.cameraRefreshInterval = setInterval(refreshSnapshot, 2000);
        } else {
            content.innerHTML = `<div style="color:var(--text-muted); padding:20px; text-align:center;"><i class="fa-solid fa-video-slash" style="font-size:32px; margin-bottom:10px;"></i><p>${I18N.t('printers.no_video_stream')}</p></div>`;
        }
    } catch (err) {
        console.error('[Camera] Erreur:', err);
        container.style.display = 'none';
        cameraLoadedForPid = null;
    }
}

function closePrinterMonitor() {
    closeModal('modal-printer-monitor');
    if (printerMonitorInterval) { clearInterval(printerMonitorInterval); printerMonitorInterval = null; }
    if (window.cameraRefreshInterval) { clearInterval(window.cameraRefreshInterval); window.cameraRefreshInterval = null; }
    cameraLoadedForPid = null;
    currentMonitorPid = null;
}

function renderTempRow(label, data) {
    if (!data) return '';
    const current = data.current || 0;
    const target = data.target || 0;
    const isHeating = target > 0 && current < target - 2;
    const color = isHeating ? 'var(--warning)' : (current > 0 ? 'var(--accent)' : 'var(--text-muted)');
    return `<div class="temp-row"><span class="temp-label">${label}</span><span class="temp-values"><span class="temp-current" style="color:${color}">${current}°C</span><span class="temp-target">/ ${target}°C</span></span></div>`;
}

function refreshPrinterStatus(pid) {
    fetchAndUpdateMonitor(pid);
    showToast(I18N.t('toast.status_updated'), "info");
}

function deletePrinter(pid) {
    showConfirmModal(I18N.t('toast.delete_printer') || 'Supprimer cette imprimante ?', async () => {
        try {
            const res = await fetch(`${API}/api/printers/${pid}`, { method: 'DELETE' });
            if (res.ok) {
                showToast(I18N.t('toast.printer_deleted') || 'Imprimante supprimée', 'success');
                loadPrinters();
            } else {
                const data = await res.json();
                showToast(data.error || I18N.t('toast.error'), 'error');
            }
        } catch (err) {
            showToast(I18N.t('toast.connection_error'), 'error');
            console.error('[Delete Printer]', err);
        }
    });
}

window.openAddPrinterModal = function() {
    document.getElementById('add-printer-form').reset();
    document.getElementById('printer-edit-id').value = '';
    const title = document.getElementById('add-printer-modal-title');
    if (title) title.textContent = I18N.t('printers.add') || 'Ajouter une imprimante';
    const submitBtn = document.getElementById('add-printer-submit-btn');
    if (submitBtn) submitBtn.innerHTML = `<i class="fa-solid fa-plus"></i> ${I18N.t('printers.add') || 'Ajouter'}`;
    const apiKeyField = document.getElementById('printer-api-key');
    if (apiKeyField) apiKeyField.placeholder = I18N.t('printers.octoprint_key_ph') || 'Clé API OctoPrint';
    togglePrinterFields();
    openModal('modal-add-printer');
}

window.togglePrinterFields = function() {
    const type = document.getElementById('printer-type').value;
    document.getElementById('group-api-key').style.display = (type === 'octoprint' || type === 'prusalink') ? 'block' : 'none';
    document.getElementById('group-port').style.display = type === 'klipper' ? 'block' : 'none';
    document.getElementById('group-bambu').style.display = type === 'bambu' ? 'block' : 'none';
    document.getElementById('group-octoprint-hint').style.display = type === 'octoprint' ? 'block' : 'none';
    document.getElementById('group-klipper-hint').style.display = type === 'klipper' ? 'block' : 'none';
    document.getElementById('group-prusalink-hint').style.display = type === 'prusalink' ? 'block' : 'none';
    document.getElementById('group-elegoo-sdcp-hint').style.display = type === 'elegoo_sdcp' ? 'block' : 'none';
    document.getElementById('group-elegoo-cc2').style.display = type === 'elegoo_cc2' ? 'block' : 'none';
    document.getElementById('group-creality-hint').style.display = type === 'creality' ? 'block' : 'none';
    document.getElementById('group-flashforge').style.display = type === 'flashforge' ? 'block' : 'none';
    const apiKeyLabel = document.getElementById('printer-api-key');
    if (apiKeyLabel) {
        apiKeyLabel.placeholder = type === 'prusalink'
            ? (I18N.t('printers.prusalink_key_ph') || 'Mot de passe / clé API PrusaLink')
            : (I18N.t('printers.octoprint_key_ph') || 'Clé API OctoPrint');
    }
    const help = document.getElementById('printer-type-help');
    if (help && type === 'bambu') help.textContent = I18N.t('printers.bambu_access_found_hint');
}


window.manualCheckUpdate = async function () {
    const btn = document.getElementById('nav-check-update-btn');
    const icon = btn?.querySelector('i');
    const originalIcon = icon?.className || 'fa-solid fa-arrows-rotate';

    if (icon) icon.className = 'fa-solid fa-spinner fa-spin';

    try {
        const res = await fetch(`${API}/api/update/check`);
        const data = await res.json();

        if (data.update_available) {
            const dot = document.getElementById('update-available-dot');
            if (dot) dot.classList.remove('hidden');

            if (window.UpdateManager) {
                window.UpdateManager.showUpdateModal({
                    version: data.version,
                    current_version: data.current_version,
                    release_notes: data.release_notes,
                    download_url: data.download_url,
                    release_url: data.release_url,
                    published_at: data.published_at
                });
            }
            showToast(I18N.t('toast.update_available', { version: data.version }), 'success');
        } else {
            showToast(I18N.t('toast.up_to_date', { version: data.current_version }), 'info');
        }
    } catch (err) {
        console.error('[CheckUpdate]', err);
        showToast(I18N.t('toast.update_check_error'), 'error');
    } finally {
        if (icon) icon.className = originalIcon;
    }
};


const UpdateManager = {
lastCheck: 0,
checkInterval: 6 * 60 * 60 * 1000,
currentVersion: '1.0.0',
async init() {
console.log('[UpdateManager] 🔄 Initialisation...');
try {
const res = await fetch(`${API}/api/update/version`);
if (res.ok) {
const data = await res.json();
this.currentVersion = data.version;
console.log(`[UpdateManager] Version actuelle: ${this.currentVersion}`);
}
} catch (e) {
console.warn('[UpdateManager] Impossible de récupérer la version');
}
await this.checkAndShowChangelog();
setTimeout(() => this.checkForUpdates(true), 5000);
setInterval(() => this.checkForUpdates(false), this.checkInterval);
},
async checkAndShowChangelog() {
try {
const lastSeenVersion = localStorage.getItem('stellio-last-seen-version');
const response = await fetch('https://api.github.com/repos/stellio-app/stellio/releases/latest');
if (!response.ok) return;
const release = await response.json();
const latestVersion = release.tag_name.replace('v', '');
if (lastSeenVersion && lastSeenVersion !== latestVersion && latestVersion === this.currentVersion) {
console.log(`[UpdateManager] 🎉 Mise à jour détectée: ${lastSeenVersion} → ${latestVersion}`);
this.showChangelogModal(release);
}
localStorage.setItem('stellio-last-seen-version', latestVersion);
} catch (e) {
console.warn('[UpdateManager] Erreur check changelog:', e);
}
},
async checkForUpdates(showModal = true) {
try {
console.log('[UpdateManager] 🔍 Vérification des mises à jour...');
const res = await fetch(`${API}/api/update/check`);
if (!res.ok) {
console.warn('[UpdateManager] Impossible de vérifier');
return;
}
const data = await res.json();
console.log('[UpdateManager] Réponse:', data);
if (data.update_available) {
console.log(`[UpdateManager] ✅ Nouvelle version: ${data.version}`);
if (showModal) {
this.showUpdateModal(data);
} else {
this.showUpdateToast(data);
}
} else {
console.log('[UpdateManager] ✅ Application à jour');
}
} catch (err) {
console.error('[UpdateManager] Erreur:', err);
}
},
showUpdateModal(updateInfo) {
const overlay = document.createElement('div');
overlay.className = 'modal-overlay update-modal-overlay';
overlay.style.cssText = `position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.75); display: flex; align-items: center; justify-content: center; z-index: 100000; backdrop-filter: blur(5px); animation: fadeIn 0.3s ease;`;
const modal = document.createElement('div');
modal.style.cssText = `background: var(--bg-secondary, #1e2129); border-radius: 16px; padding: 32px; max-width: 600px; width: 90%; max-height: 85vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5); border: 1px solid var(--border, #2a2f3a); animation: slideIn 0.3s ease;`;
const releaseNotes = this.parseMarkdown(updateInfo.release_notes || I18N.t('update.default_notes'));
const hasInstaller = !!updateInfo.download_url;
const releaseUrl = updateInfo.release_url || `https://github.com/stellio-app/stellio/releases/latest`;
modal.innerHTML = `<div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;"><div style="width: 56px; height: 56px; background: linear-gradient(135deg, var(--accent, #4ea1d3), #00d9ff); border-radius: 12px; display: flex; align-items: center; justify-content: center;"><i class="fa-solid fa-download" style="font-size: 28px; color: white;"></i></div><div style="flex: 1;"><h3 style="margin: 0; color: var(--text-primary, #e6e6e6); font-size: 22px; font-weight: 700;">${I18N.t('update.available_title')}</h3><p style="margin: 4px 0 0 0; color: var(--text-muted, #9ca3af); font-size: 14px;">${I18N.t('update.version_transition', { from: updateInfo.current_version, to: updateInfo.version })}</p></div></div><div style="background: var(--bg-primary, #15181e); padding: 20px; border-radius: 12px; margin-bottom: 24px; max-height: 300px; overflow-y: auto; border: 1px solid var(--border, #2a2f3a);"><h4 style="margin: 0 0 12px 0; color: var(--accent, #4ea1d3); font-size: 14px; text-transform: uppercase; letter-spacing: 1px;"><i class="fa-solid fa-list-check"></i> ${I18N.t('update.release_notes')}</h4><div style="color: var(--text-secondary, #b0b3b8); font-size: 14px; line-height: 1.7;" class="release-notes-content">${releaseNotes}</div></div><div id="update-progress-container" style="display: none; margin-bottom: 24px; padding: 16px; background: var(--bg-primary, #15181e); border-radius: 12px; border: 1px solid var(--border, #2a2f3a);"><div style="display: flex; justify-content: space-between; margin-bottom: 10px; align-items: center;"><span style="color: var(--text-secondary, #b0b3b8); font-size: 13px; font-weight: 500;"><i class="fa-solid fa-download"></i> ${I18N.t('update.downloading')}</span><span id="update-percent" style="color: var(--accent, #4ea1d3); font-size: 14px; font-weight: 700;">0%</span></div><div style="height: 8px; background: var(--bg-tertiary, #2a2f3a); border-radius: 4px; overflow: hidden;"><div id="update-bar" style="height: 100%; background: linear-gradient(90deg, var(--accent, #4ea1d3), #00d9ff); width: 0%; transition: width 0.3s ease; border-radius: 4px;"></div></div></div><div style="display: flex; gap: 12px; justify-content: flex-end; flex-wrap: wrap;">${!hasInstaller ? `<a href="${releaseUrl}" target="_blank" style="padding: 12px 24px; border: none; border-radius: 10px; background: linear-gradient(135deg, var(--accent, #4ea1d3), #3d8fb8); color: white; cursor: pointer; font-weight: 600; font-size: 14px; box-shadow: 0 4px 12px rgba(78, 161, 211, 0.3); text-decoration: none; display: inline-flex; align-items: center; gap: 8px;"><i class="fa-solid fa-external-link-alt"></i> ${I18N.t('update.download_github')}</a>` : ''}<button id="update-later-btn" style="padding: 12px 24px; border: 1px solid var(--border, #363c4a); border-radius: 10px; background: var(--bg-tertiary, #2a2f3a); color: var(--text-primary, #e6e6e6); cursor: pointer; font-weight: 500; font-size: 14px;">${I18N.t('update.later')}</button>${hasInstaller ? `<button id="update-now-btn" style="padding: 12px 28px; border: none; border-radius: 10px; background: linear-gradient(135deg, var(--accent, #4ea1d3), #3d8fb8); color: white; cursor: pointer; font-weight: 600; font-size: 14px; box-shadow: 0 4px 12px rgba(78, 161, 211, 0.3);"><i class="fa-solid fa-download"></i> ${I18N.t('update.update_now')}</button>` : ''}</div>`;
overlay.appendChild(modal);
document.body.appendChild(overlay);
document.getElementById('update-later-btn').addEventListener('click', () => {
overlay.style.animation = 'fadeOut 0.3s ease';
setTimeout(() => overlay.remove(), 300);
});
if (hasInstaller) {
document.getElementById('update-now-btn').addEventListener('click', async () => {
const btn = document.getElementById('update-now-btn');
btn.disabled = true;
btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t('update.preparing')}`;
document.getElementById('update-progress-container').style.display = 'block';
try {
const downloadRes = await fetch(`${API}/api/update/download`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ download_url: updateInfo.download_url })
});
const downloadData = await downloadRes.json();
if (downloadData.success) {
btn.innerHTML = `<i class="fa-solid fa-check"></i> ${I18N.t('update.installing')}`;
document.getElementById('update-percent').textContent = '100%';
document.getElementById('update-bar').style.width = '100%';
setTimeout(async () => {
const installRes = await fetch(`${API}/api/update/install`, {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({ installer_path: downloadData.installer_path })
});
if (installRes.ok) {
btn.innerHTML = `<i class="fa-solid fa-rotate"></i> ${I18N.t('update.restarting')}`;
showToast(I18N.t('toast.update_restarting'), 'success');
}
}, 1000);
} else {
showToast(I18N.t('toast.update_download_error'), 'error');
btn.disabled = false;
btn.innerHTML = `<i class="fa-solid fa-download"></i> ${I18N.t('actions.retry')}`;
document.getElementById('update-progress-container').style.display = 'none';
}
} catch (err) {
showToast(I18N.t('toast.connection_error'), 'error');
btn.disabled = false;
btn.innerHTML = `<i class="fa-solid fa-download"></i> ${I18N.t('actions.retry')}`;
document.getElementById('update-progress-container').style.display = 'none';
}
});
}
overlay.addEventListener('click', (e) => {
if (e.target === overlay) {
overlay.style.animation = 'fadeOut 0.3s ease';
setTimeout(() => overlay.remove(), 300);
}
});
},
showUpdateToast(updateInfo) {
const toast = document.createElement('div');
toast.className = 'toast info';
toast.style.cssText = `position: fixed; bottom: 24px; right: 24px; background: var(--bg-secondary, #1e2129); border: 1px solid var(--accent, #4ea1d3); padding: 16px 20px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3); cursor: pointer; z-index: 9999; animation: slideInRight 0.3s ease; max-width: 350px;`;
toast.innerHTML = `<div style="display: flex; align-items: center; gap: 12px;"><div style="width: 40px; height: 40px; background: linear-gradient(135deg, var(--accent, #4ea1d3), #00d9ff); border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;"><i class="fa-solid fa-download" style="font-size: 18px; color: white;"></i></div><div style="flex: 1; min-width: 0;"><div style="font-weight: 600; color: var(--text-primary, #e6e6e6); font-size: 14px;">${I18N.t('update.available_title')}</div><div style="font-size: 12px; color: var(--text-muted, #9ca3af); margin-top: 2px;">${I18N.t('update.toast_subtitle', { version: updateInfo.version })}</div></div></div>`;
toast.addEventListener('click', () => {
toast.remove();
this.showUpdateModal(updateInfo);
});
document.body.appendChild(toast);
setTimeout(() => {
if (toast.parentNode) {
toast.style.animation = 'slideOutRight 0.3s ease';
setTimeout(() => toast.remove(), 300);
}
}, 15000);
},
showChangelogModal(release) {
const overlay = document.createElement('div');
overlay.className = 'modal-overlay changelog-modal-overlay';
overlay.style.cssText = `position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.75); display: flex; align-items: center; justify-content: center; z-index: 100000; backdrop-filter: blur(5px); animation: fadeIn 0.3s ease;`;
const modal = document.createElement('div');
modal.style.cssText = `background: var(--bg-secondary, #1e2129); border-radius: 16px; padding: 32px; max-width: 650px; width: 90%; max-height: 85vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5); border: 1px solid var(--border, #2a2f3a); animation: slideIn 0.3s ease;`;
const version = release.tag_name || this.currentVersion;
const changelog = this.parseMarkdown(release.body || I18N.t('update.default_notes'));
const publishedDate = new Date(release.published_at).toLocaleDateString(I18N.lang, { year: 'numeric', month: 'long', day: 'numeric' });
modal.innerHTML = `<div style="text-align: center; margin-bottom: 28px;"><div style="display: inline-flex; align-items: center; justify-content: center; width: 72px; height: 72px; background: linear-gradient(135deg, #10b981, #059669); border-radius: 50%; margin-bottom: 16px; box-shadow: 0 8px 24px rgba(16, 185, 129, 0.3);"><i class="fa-solid fa-party-horn" style="font-size: 32px; color: white;"></i></div><h2 style="margin: 0 0 8px 0; color: var(--text-primary, #e6e6e6); font-size: 26px; font-weight: 700;">${I18N.t('update.updated_title')}</h2><p style="margin: 0; color: var(--text-muted, #9ca3af); font-size: 15px;">${I18N.t('update.version_date', { version, date: publishedDate })}</p></div><div style="background: var(--bg-primary, #15181e); padding: 24px; border-radius: 12px; margin-bottom: 24px; border: 1px solid var(--border, #2a2f3a);"><h3 style="margin: 0 0 16px 0; color: var(--accent, #4ea1d3); font-size: 16px; text-transform: uppercase; letter-spacing: 1px; display: flex; align-items: center; gap: 8px;"><i class="fa-solid fa-sparkles"></i> ${I18N.t('update.whats_new')}</h3><div style="color: var(--text-secondary, #b0b3b8); font-size: 14px; line-height: 1.8;" class="changelog-content">${changelog}</div></div><div style="text-align: center;"><button id="changelog-close-btn" style="padding: 14px 32px; border: none; border-radius: 10px; background: linear-gradient(135deg, #10b981, #059669); color: white; cursor: pointer; font-weight: 600; font-size: 15px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);"><i class="fa-solid fa-thumbs-up"></i> ${I18N.t('update.lets_go')}</button></div>`;
overlay.appendChild(modal);
document.body.appendChild(overlay);
document.getElementById('changelog-close-btn').addEventListener('click', () => {
overlay.style.animation = 'fadeOut 0.3s ease';
setTimeout(() => overlay.remove(), 300);
});
overlay.addEventListener('click', (e) => {
if (e.target === overlay) {
overlay.style.animation = 'fadeOut 0.3s ease';
setTimeout(() => overlay.remove(), 300);
}
});
},
parseMarkdown(text) {
return text
.replace(/^### (.*$)/gim, '<h4 style="color: var(--accent, #4ea1d3); margin: 16px 0 8px 0; font-size: 15px;">$1</h4>')
.replace(/^## (.*$)/gim, '<h3 style="color: var(--accent, #4ea1d3); margin: 20px 0 10px 0; font-size: 17px;">$1</h3>')
.replace(/^# (.*$)/gim, '<h2 style="color: var(--accent, #4ea1d3); margin: 24px 0 12px 0; font-size: 19px;">$1</h2>')
.replace(/^\- (.*$)/gim, '<div style="display: flex; align-items: flex-start; gap: 8px; margin: 6px 0;"><span style="color: #10b981; flex-shrink: 0;">✓</span><span>$1</span></div>')
.replace(/^\* (.*$)/gim, '<div style="display: flex; align-items: flex-start; gap: 8px; margin: 6px 0;"><span style="color: #10b981; flex-shrink: 0;">✓</span><span>$1</span></div>')
.replace(/\*\*(.*?)\*\*/g, '<strong style="color: var(--text-primary, #e6e6e6);">$1</strong>')
.replace(/\*(.*?)\*/g, '<em>$1</em>')
.replace(/`(.*?)`/g, '<code style="background: var(--bg-tertiary, #2a2f3a); padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 13px;">$1</code>')
.replace(/\n\n/g, '<br><br>')
.replace(/\n/g, '<br>');
}
};
window.UpdateManager = UpdateManager;
document.addEventListener('DOMContentLoaded', () => {
setTimeout(() => UpdateManager.init(), 2000);
});
if (!document.getElementById('update-animations')) {
const style = document.createElement('style');
style.id = 'update-animations';
style.textContent = `@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } } @keyframes fadeOut { from { opacity: 1; } to { opacity: 0; } } @keyframes slideIn { from { transform: translateY(-20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } } @keyframes slideInRight { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } } @keyframes slideOutRight { from { transform: translateX(0); opacity: 1; } to { transform: translateX(400px); opacity: 0; } }`;
document.head.appendChild(style);
}


window.showQuitConfirmation = function() {
fetch(`${API}/api/app/save-cache`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}), keepalive: true }).catch(() => {});
const overlay = document.createElement('div');
overlay.id = 'quit-confirmation-overlay';
overlay.style.cssText = `position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.75); backdrop-filter: blur(5px); display: flex; align-items: center; justify-content: center; z-index: 999999; animation: fadeIn 0.2s ease;`;
const modal = document.createElement('div');
modal.style.cssText = `background: var(--bg-secondary, #22262e); border: 1px solid var(--border, #363c4a); border-radius: 16px; padding: 32px; max-width: 420px; width: 90%; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5); text-align: center; animation: slideUp 0.3s ease;`;
modal.innerHTML = `<div style="margin-bottom: 20px;"><div style="width: 64px; height: 64px; background: linear-gradient(135deg, var(--accent, #4ea1d3), #3d8fb8); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; box-shadow: 0 8px 24px rgba(78, 161, 211, 0.3);"><i class="fa-solid fa-power-off" style="font-size: 28px; color: white;"></i></div><h3 style="margin: 0 0 8px 0; color: var(--text-primary, #e8e9eb); font-size: 20px; font-weight: 600;">${I18N.t('app.quit_title') || 'Quitter Stellio'}</h3><p style="margin: 0 0 24px 0; color: var(--text-secondary, #9ca0ab); font-size: 14px; line-height: 1.5;">${I18N.t('app.quit_message') || 'Voulez-vous vraiment quitter l\'application ?'}</p></div><div style="display: flex; gap: 12px; justify-content: center;"><button id="quit-cancel-btn" style="padding: 12px 28px; border: 1px solid var(--border, #363c4a); border-radius: 8px; background: var(--bg-tertiary, #2a2e38); color: var(--text-primary, #e8e9eb); cursor: pointer; font-weight: 500; font-size: 14px; transition: all 0.2s;">${I18N.t('actions.cancel') || 'Annuler'}</button><button id="quit-confirm-btn" style="padding: 12px 28px; border: none; border-radius: 8px; background: linear-gradient(135deg, var(--danger, #f87171), #ef4444); color: white; cursor: pointer; font-weight: 600; font-size: 14px; box-shadow: 0 4px 12px rgba(248, 113, 113, 0.3); transition: all 0.2s; display: flex; align-items: center; gap: 6px;"><i class="fa-solid fa-power-off"></i>${I18N.t('actions.quit') || 'Quitter'}</button></div>`;
overlay.appendChild(modal);
document.body.appendChild(overlay);
document.getElementById('quit-cancel-btn').addEventListener('click', () => {
overlay.style.animation = 'fadeOut 0.2s ease';
setTimeout(() => overlay.remove(), 200);
});
document.getElementById('quit-confirm-btn').addEventListener('click', () => {
const btn = document.getElementById('quit-confirm-btn');
btn.disabled = true;
btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t('app.closing')}`;
fetch(`${API}/api/app/quit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}), keepalive: true }).catch(() => {});
setTimeout(() => { window.close(); }, 2000);
});
overlay.addEventListener('click', (e) => {
if (e.target === overlay) {
overlay.style.animation = 'fadeOut 0.2s ease';
setTimeout(() => overlay.remove(), 200);
}
});
const escHandler = (e) => {
if (e.key === 'Escape') {
overlay.style.animation = 'fadeOut 0.2s ease';
setTimeout(() => overlay.remove(), 200);
document.removeEventListener('keydown', escHandler);
}
};
document.addEventListener('keydown', escHandler);
};
window.addEventListener('beforeunload', () => {
try {
navigator.sendBeacon(`${API}/api/app/save-cache`, JSON.stringify({}));
} catch (err) {}
});


let lastProgressUpdate = 0;
const PROGRESS_THROTTLE = 500;


async function loadAppVersion() {
try {
const res = await fetch(`${API}/api/update/version`);
if (res.ok) {
const data = await res.json();
const versionEl = document.getElementById('app-version-display');
if (versionEl) {
versionEl.textContent = data.version;
}
if (window.UpdateManager) {
window.UpdateManager.currentVersion = data.version;
}
}
} catch (err) {
console.warn('[Version] Impossible de charger la version:', err);
const versionEl = document.getElementById('app-version-display');
if (versionEl) versionEl.textContent = I18N.t('common.unknown') || 'Inconnue';
}
}


let diagConsoleInterval = null;
let diagConsoleOffset = -1;
let diagConsoleFetching = false;
const DIAG_CONSOLE_MAX_CHARS = 500000;

function onDiagnosticAccordToggle(headerEl) {
    const section = headerEl.closest('.accord-section');
    if (!section) return;
    if (section.classList.contains('open')) {
        diagConsoleOffset = -1;
        const box = document.getElementById('diag-console');
        if (box) box.textContent = '';
        startDiagnosticConsolePoll();
        refreshDebugSessionStatus();
    } else {
        stopDiagnosticConsolePoll();
    }
}
window.onDiagnosticAccordToggle = onDiagnosticAccordToggle;

async function refreshDebugSessionStatus() {
    const hint = document.getElementById('diag-debug-active-hint');
    if (!hint) return;
    try {
        const res = await fetch(`${API}/api/debug/session`);
        if (!res.ok) return;
        const data = await res.json();
        hint.style.display = data.active ? 'block' : 'none';
    } catch (err) {

    }
}
window.refreshDebugSessionStatus = refreshDebugSessionStatus;

async function enableDebugSessionAndRestart(btn) {
    const confirmMsg = I18N.t('settings.diagnostic_debug_confirm') ||
        "Stellio va redémarrer et afficher le maximum de logs dans la console pour cette session. Continuer ?";
    const ok = await showConfirmDialog(confirmMsg, {
        title: I18N.t('settings.diagnostic_debug_confirm_title') || 'Activer le mode debug ?',
        confirmLabel: I18N.t('settings.diagnostic_debug_confirm_btn') || 'Redémarrer'
    });
    if (!ok) return;

    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t('settings.diagnostic_debug_restarting') || 'Redémarrage...'}`;

    try {
        const res = await fetch(`${API}/api/debug/enable`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
        if (!res.ok) throw new Error();
    } catch (err) {
        showToast(I18N.t('toast.connection_error') || 'Erreur de connexion', 'error');
        btn.disabled = false;
        btn.innerHTML = originalHtml;
        return;
    }

    fetch(`${API}/api/app/quit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}), keepalive: true }).catch(() => {});
    setTimeout(() => { window.close(); }, 1200);
}
window.enableDebugSessionAndRestart = enableDebugSessionAndRestart;

function startDiagnosticConsolePoll() {
    if (diagConsoleInterval) return;
    pollDiagnosticConsole();
    diagConsoleInterval = setInterval(pollDiagnosticConsole, 2000);
}
window.startDiagnosticConsolePoll = startDiagnosticConsolePoll;

function stopDiagnosticConsolePoll() {
    if (diagConsoleInterval) { clearInterval(diagConsoleInterval); diagConsoleInterval = null; }
}
window.stopDiagnosticConsolePoll = stopDiagnosticConsolePoll;

async function pollDiagnosticConsole() {
    const section = document.getElementById('accord-diagnostic');
    if (!section || !section.classList.contains('open')) return;
    if (diagConsoleFetching) return;
    diagConsoleFetching = true;
    try {
        const res = await fetch(`${API}/api/logs/tail?offset=${diagConsoleOffset}`);
        if (!res.ok) return;
        const data = await res.json();
        const box = document.getElementById('diag-console');
        if (!box) return;

        if (data.reset) box.textContent = '';
        const placeholder = box.querySelector('.diag-console-placeholder');
        if (placeholder) placeholder.remove();

        if (data.lines) {
            box.textContent += data.lines;
            if (box.textContent.length > DIAG_CONSOLE_MAX_CHARS) {
                box.textContent = box.textContent.slice(-Math.floor(DIAG_CONSOLE_MAX_CHARS * 0.6));
            }
            const autoscroll = document.getElementById('diag-console-autoscroll');
            if (!autoscroll || autoscroll.checked) box.scrollTop = box.scrollHeight;
        }
        diagConsoleOffset = data.offset;
    } catch (err) {
        console.warn('[Diagnostic] Erreur récupération logs:', err);
    } finally {
        diagConsoleFetching = false;
    }
}
window.pollDiagnosticConsole = pollDiagnosticConsole;

function clearDiagnosticConsole() {
    const box = document.getElementById('diag-console');
    if (box) box.textContent = '';
}
window.clearDiagnosticConsole = clearDiagnosticConsole;

async function exportDiagnosticLogs(btn) {
const originalHtml = btn.innerHTML;
btn.disabled = true;
btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t('settings.diagnostic_exporting') || 'Génération...'}`;


if (window.pywebview && window.pywebview.api && window.pywebview.api.save_diagnostic_logs) {
    try {
        const result = await window.pywebview.api.save_diagnostic_logs();
        if (result && result.success) {
            showToast(I18N.t('toast.logs_exported') || `Logs exportés : ${result.path}`, 'success');
        } else if (!(result && result.cancelled)) {
            showToast((result && result.error) || I18N.t('toast.connection_error'), 'error');
        }
    } catch (err) {
        showToast(err.message || I18N.t('toast.connection_error'), 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
    return;
}

try {
const res = await fetch(`${API}/api/logs/export`);
if (!res.ok) {
const data = await res.json().catch(() => ({}));
throw new Error(data.error || I18N.t('toast.connection_error'));
}
const blob = await res.blob();
const disposition = res.headers.get('Content-Disposition') || '';
const match = disposition.match(/filename="?([^"]+)"?/);
const filename = match ? match[1] : `stellio-diagnostic-${Date.now()}.zip`;
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = filename;
document.body.appendChild(a);
a.click();
a.remove();
URL.revokeObjectURL(url);
showToast(I18N.t('toast.logs_exported') || 'Logs exportés', 'success');
} catch (err) {
showToast(err.message || I18N.t('toast.connection_error'), 'error');
} finally {
btn.disabled = false;
btn.innerHTML = originalHtml;
}
}


document.addEventListener('visibilitychange', () => {
if (document.hidden) {
if (autoScanInterval) { clearInterval(autoScanInterval); autoScanInterval = null; }
if (thumbRefreshInterval) { clearInterval(thumbRefreshInterval); thumbRefreshInterval = null; }
if (scanPollingInterval) { clearInterval(scanPollingInterval); scanPollingInterval = null; }
} else {
startAutoFileMonitor();
startThumbAutoRefresh();
}
});


(function () {
    let _ctxPath = null;
    let _ctxName = null;

    window.openFileCtxMenu = function (e, filePath, fileName) {
        e.preventDefault();
        e.stopPropagation();
        _ctxPath = filePath;
        _ctxName = fileName;

        const nameEl = document.getElementById('file-actions-name');
        if (nameEl) nameEl.textContent = fileName;

        const isVirtualEntry = filePath.includes('::');
        ['ctx-rename-btn', 'ctx-move-btn', 'ctx-share-btn', 'ctx-regen-btn', 'ctx-openwith-btn', 'ctx-send-instance-btn'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = isVirtualEntry ? 'none' : '';
        });

        openModal('modal-file-actions');
    };

    document.addEventListener('DOMContentLoaded', () => {
        document.getElementById('ctx-rename-btn')?.addEventListener('click', () => {
            closeModal('modal-file-actions');
            openRenameFileModal(_ctxPath, _ctxName);
        });
        document.getElementById('ctx-photos-btn')?.addEventListener('click', () => {
            closeModal('modal-file-actions');
            openPrintPhotosModal(_ctxPath, _ctxName);
        });
        document.getElementById('ctx-metadata-btn')?.addEventListener('click', () => {
            closeModal('modal-file-actions');
            openFileMetadataModal(_ctxPath, _ctxName);
        });
        document.getElementById('ctx-slicer-btn')?.addEventListener('click', () => {
            closeModal('modal-file-actions');
            sendToSlicer(_ctxPath, _ctxName);
        });
        document.getElementById('ctx-openwith-btn')?.addEventListener('click', () => {
            closeModal('modal-file-actions');
            openFileWith(_ctxPath, _ctxName);
        });
        document.getElementById('ctx-share-btn')?.addEventListener('click', () => {
            closeModal('modal-file-actions');
            openShareFileModal(_ctxPath, _ctxName);
        });
        document.getElementById('ctx-send-instance-btn')?.addEventListener('click', () => {
            closeModal('modal-file-actions');
            sendFileToRemoteInstance(_ctxPath);
        });
        document.getElementById('ctx-cost-btn')?.addEventListener('click', () => {
            closeModal('modal-file-actions');
            openPrintCostModal(_ctxPath, _ctxName);
        });
        document.getElementById('ctx-move-btn')?.addEventListener('click', () => {
            closeModal('modal-file-actions');
            openMoveFileModal(_ctxPath, _ctxName);
        });
        document.getElementById('ctx-regen-btn')?.addEventListener('click', () => {
            closeModal('modal-file-actions');
            regenFileThumbnail(_ctxPath, _ctxName);
        });
        document.getElementById('ctx-project-btn')?.addEventListener('click', () => {
            closeModal('modal-file-actions');
            openAddToProjectModal(_ctxPath, _ctxName);
        });
    });

    window.openShareFileModal = async function (filePath, fileName) {
        openModal('modal-share-file');
        document.getElementById('share-file-name').textContent = fileName;
        document.getElementById('share-loading').classList.remove('hidden');
        document.getElementById('share-content').classList.add('hidden');
        document.getElementById('share-error').classList.add('hidden');
        try {
            const res = await fetch(`${API}/api/files/share`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: filePath })
            });
            const data = await res.json();
            if (!res.ok || !data.url) throw new Error(data.error || 'Erreur serveur');
            document.getElementById('share-url-input').value = data.url;
            document.getElementById('share-loading').classList.add('hidden');
            document.getElementById('share-content').classList.remove('hidden');
        } catch (e) {
            document.getElementById('share-loading').classList.add('hidden');
            document.getElementById('share-error-msg').textContent = e.message || I18N.t('share.error');
            document.getElementById('share-error').classList.remove('hidden');
        }
    };

    window.copyShareUrl = function () {
        const input = document.getElementById('share-url-input');
        if (!input) return;
        input.select();
        input.setSelectionRange(0, 99999);
        navigator.clipboard.writeText(input.value).then(() => {
            if (typeof showToast === 'function') showToast(I18N.t('share.copied') || 'Lien copié', 'success');
        }).catch(() => {});
    };

    let _renamePath = null;
    window.openRenameFileModal = function (filePath, fileName) {
        _renamePath = filePath;
        const input = document.getElementById('rename-input');
        if (input) {
            input.value = fileName.replace(/\.[^/.]+$/, '');
            setTimeout(() => { input.focus(); input.select(); }, 100);
        }
        openModal('modal-rename-file');
    };
    window.confirmRenameFile = async function () {
        const input = document.getElementById('rename-input');
        const newName = input?.value?.trim();
        if (!newName || !_renamePath) return;
        try {
            const res = await fetch(`${API}/api/files/rename`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: _renamePath, new_name: newName })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                showToast(data.message || I18N.t('toast.file_renamed'), 'success');
                closeModal('modal-rename-file');
                loadFiles();
            } else {
                showToast(data.error || I18N.t('toast.rename_error'), 'error');
            }
        } catch {
            showToast(I18N.t('toast.connection_error'), 'error');
        }
    };
    document.getElementById('rename-input')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') window.confirmRenameFile();
    });

    let duplicatesCurrentMode = 'exact';

    window.openDuplicatesModal = async function () {
        duplicatesCurrentMode = 'exact';
        openModal('modal-duplicates');
        await loadDuplicates('exact');
    };

    window.switchDuplicatesMode = async function (mode) {
        if (mode === duplicatesCurrentMode) return;
        duplicatesCurrentMode = mode;
        document.getElementById('duplicates-tab-exact')?.classList.toggle('btn-primary', mode === 'exact');
        document.getElementById('duplicates-tab-exact')?.classList.toggle('btn-ghost', mode !== 'exact');
        document.getElementById('duplicates-tab-similar')?.classList.toggle('btn-primary', mode === 'similar');
        document.getElementById('duplicates-tab-similar')?.classList.toggle('btn-ghost', mode !== 'similar');
        document.getElementById('duplicates-similar-hint')?.classList.toggle('hidden', mode !== 'similar');
        await loadDuplicates(mode);
    };

    async function loadDuplicates(mode) {
        const loadingEl     = document.getElementById('duplicates-loading');
        const loadingTextEl = document.getElementById('duplicates-loading-text');
        const listEl        = document.getElementById('duplicates-list');
        const emptyEl       = document.getElementById('duplicates-empty');
        const emptyTextEl   = document.getElementById('duplicates-empty-text');

        loadingEl?.classList.remove('hidden');
        listEl?.classList.add('hidden');
        emptyEl?.classList.add('hidden');
        if (loadingTextEl) {
            loadingTextEl.textContent = mode === 'similar'
                ? I18N.t('duplicates.searching_similar', 'Analyse géométrique des fichiers…')
                : I18N.t('duplicates.searching', 'Recherche des doublons…');
        }

        const endpoint = mode === 'similar' ? '/api/files/duplicates/similar' : '/api/files/duplicates';

        try {
            const res  = await fetch(`${API}${endpoint}`);
            const data = await res.json();
            loadingEl?.classList.add('hidden');
            if (!res.ok) { showToast(data.error || I18N.t('toast.generic_error'), 'error'); closeModal('modal-duplicates'); return; }
            if (!data.groups || data.groups.length === 0) {
                if (emptyTextEl) {
                    emptyTextEl.textContent = mode === 'similar'
                        ? I18N.t('duplicates.none_found_similar', 'Aucun doublon géométrique détecté 🎉')
                        : I18N.t('duplicates.none_found', 'Aucun doublon détecté 🎉');
                }
                emptyEl?.classList.remove('hidden');
                return;
            }

            let html = `<p style="font-size:13px; color:var(--text-secondary); margin-bottom:16px;">${I18N.t('duplicates.groups_found', { count: data.total_groups })}</p>`;
            if (mode === 'similar' && data.truncated) {
                html += `<p style="font-size:12px; color:var(--warning); margin-bottom:16px;"><i class="fa-solid fa-triangle-exclamation"></i> ${I18N.t('duplicates.truncated_notice', `Analyse limitée aux ${data.candidate_count} plus gros fichiers pour préserver les performances.`, { count: data.candidate_count })}</p>`;
            }

            data.groups.forEach(group => {
                const sizeOrVolume = mode === 'similar'
                    ? `${group.volume_cm3} cm³ × ${group.count}`
                    : `${formatSize(group.size)} × ${group.count}`;
                html += `<div style="border:1px solid var(--border); border-radius:var(--radius); margin-bottom:12px; overflow:hidden;">
                    <div style="background:var(--bg-card); padding:10px 14px; display:flex; align-items:center; gap:10px; border-bottom:1px solid var(--border);">
                        <i class="fa-solid ${mode === 'similar' ? 'fa-shapes' : 'fa-copy'}" style="color:var(--accent);"></i>
                        <strong style="font-size:13px; color:var(--text-primary); flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(group.name)}">${escapeHtml(group.name)}</strong>
                        <span style="font-size:12px; color:var(--text-muted); white-space:nowrap;">${sizeOrVolume}</span>
                    </div>`;
                group.files.forEach((f, i) => {
                    const dims = mode === 'similar' && f.dimensions
                        ? ` <span style="color:var(--text-muted);">(${f.dimensions.x}×${f.dimensions.y}×${f.dimensions.z} mm)</span>`
                        : '';
                    const archiveBadge = f.in_archive
                        ? ` <span style="color:var(--warning);" title="${escapeHtml(I18N.t('duplicates.in_archive_tooltip', `Dans l'archive ${f.archive_name || ''} — suppression non disponible`, { archive: f.archive_name || '' }))}"><i class="fa-solid fa-file-zipper"></i> ${escapeHtml(I18N.t('duplicates.in_archive_badge', 'Dans une archive'))}</span>`
                        : '';
                    const actionBtn = f.in_archive
                        ? `<span class="btn btn-ghost btn-sm" style="font-size:11px; padding:3px 8px; color:var(--text-muted); cursor:default;" title="${escapeHtml(I18N.t('duplicates.in_archive_no_delete', "Suppression impossible : fichier situé dans une archive"))}">
                               <i class="fa-solid fa-lock"></i>
                           </span>`
                        : `<button class="btn btn-ghost btn-sm" style="font-size:11px; padding:3px 8px; color:var(--danger);"
                            onclick="deleteDuplicate('${escapeJs(f.path)}', this)">
                            <i class="fa-solid fa-trash"></i>
                        </button>`;
                    html += `<div style="padding:8px 14px; display:flex; align-items:center; gap:10px; ${i < group.files.length-1 ? 'border-bottom:1px solid var(--border);' : ''}">
                        <i class="fa-solid fa-folder" style="color:var(--text-muted); font-size:12px;"></i>
                        <span style="font-size:12px; color:var(--text-secondary); flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(f.path)}">${escapeHtml(f.name || f.path)}${dims}${archiveBadge}</span>
                        ${actionBtn}
                    </div>`;
                });
                html += `</div>`;
            });
            listEl.innerHTML = html;
            listEl?.classList.remove('hidden');
        } catch (err) {
            loadingEl?.classList.add('hidden');
            showToast(I18N.t('toast.connection_error'), 'error');
        }
    }
    window.deleteDuplicate = async function (filePath, btn) {
        showConfirmModal(`${I18N.t('modal.confirm_delete_file')}\n${filePath}`, async () => {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        try {
            const res = await fetch(`${API}/api/files/delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: filePath })
            });
            const data = await res.json();
            if (res.ok) {
                showToast(I18N.t('toast.deleted'), 'success');
                const row = btn.closest('div[style*="padding:8px"]');
                row?.remove();
                loadFiles();
            } else {
                showToast(data.error || I18N.t('toast.error'), 'error');
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-trash"></i>';
            }
        } catch {
            showToast(I18N.t('toast.connection_error'), 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-trash"></i>';
        }
        });
    };

    let _movePath = null;
    window.openMoveFileModal = async function (filePath, fileName) {
        _movePath = filePath;
        const select = document.getElementById('move-dest-select');
        if (!select) return;
        select.innerHTML = `<option value="" data-i18n="common.loading_ellipsis">${I18N.t('common.loading_ellipsis')}</option>`;
        openModal('modal-move-file');

        try {
            const res  = await fetch(`${API}/api/sources`);
            const srcs = await res.json();

            const knownDirs = [...new Set(
                (window.allFiles || []).map(f => {
                    const parts = f.path.replace(/\\/g, '/').split('/');
                    parts.pop();
                    return parts.join('/');
                }).filter(Boolean)
            )].sort();

            const roots = Array.isArray(srcs)
                ? srcs.map(s => s.path || s.root || '').filter(Boolean)
                : [];

            const all = [...new Set([...roots, ...knownDirs])].sort();

            if (all.length === 0) {
                select.innerHTML = `<option value="">${I18N.t('modal.no_folder_available')}</option>`;
                return;
            }
            select.innerHTML = all.map(d =>
                `<option value="${d.replace(/"/g, '&quot;')}">${d}</option>`
            ).join('');
        } catch {
            select.innerHTML = `<option value="">${I18N.t('toast.load_source_error')}</option>`;
        }
    };

	window.confirmMoveFile = async function () {
		const dest = document.getElementById('move-dest-select')?.value;
		if (!dest || !_movePath) return;
		try {
			const res = await fetch(`${API}/api/files/move`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ source_path: _movePath, destination_folder: dest })
			});
			const data = await res.json();
			if (res.ok) {
				showToast(data.message || I18N.t('toast.file_moved'), 'success');
				closeModal('modal-move-file');
				if (typeof loadFiles === 'function') loadFiles();
			} else {
				showToast(data.error || I18N.t('toast.move_error'), 'error');
			}
		} catch {
			showToast(I18N.t('toast.connection_error'), 'error');
		}
	};

	window.browseFolderForMove = async function () {
		try {
			const res = await fetch(`${API}/api/browse-folder`, { method: 'POST' });
			const data = await res.json();
			if (data.success && data.path) {
				const select = document.getElementById('move-dest-select');
				if (select) {
					const exists = [...select.options].some(o => o.value === data.path);
					if (!exists) {
						const opt = new Option(data.path, data.path);
						select.add(opt);
					}
					select.value = data.path;
				}
			}
		} catch {
			showToast(I18N.t('toast.explorer_error'), 'error');
		}
	};
    let _deletePath = null;
    window.openDeleteFileModal = function (filePath, fileName) {
        _deletePath = filePath;
        const msg = document.getElementById('delete-file-msg');
        if (msg) {
            msg.innerHTML = `${I18N.t('modal.delete_confirm_text')}<br><strong style="color:var(--text-primary);">${escapeHtml(fileName)}</strong><br><br><span style="color:var(--danger); font-size:12px;"><i class="fa-solid fa-triangle-exclamation"></i> ${I18N.t('modal.delete_irreversible')}</span>`;
        }
        openModal('modal-delete-file');
    };

    window.confirmDeleteFile = async function () {
        if (!_deletePath) return;
        try {
            const res  = await fetch(`${API}/api/files/delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: _deletePath })
            });
            const data = await res.json();
            if (res.ok) {
                showToast(data.message || I18N.t('toast.file_deleted'), 'success');
                closeModal('modal-delete-file');
                if (typeof loadFiles === 'function') loadFiles();
            } else {
                showToast(data.error || I18N.t('toast.delete_error'), 'error');
            }
        } catch {
            showToast(I18N.t('toast.connection_error'), 'error');
        }
    };

    window.regenFileThumbnail = async function (filePath, fileName) {
        const card = document.querySelector(`.file-card[data-path="${CSS.escape(filePath)}"]`);
        if (card) {
            const img = card.querySelector('.file-thumb img');
            const loader = card.querySelector('.file-loading');
            if (img) { img.src = ''; img.style.display = 'none'; img.dataset.loaded = 'false'; }
            if (loader) loader.style.display = 'flex';
        }
        showToast(I18N.t('toast.thumb_regenerating'), 'info');
        try {
            const res = await fetch(`${API}/api/thumb/generate-now`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath, force: true })
            });
            const data = await res.json();
            if (!res.ok) { showToast(data.error || I18N.t('toast.thumb_gen_error'), 'error'); return; }
            let attempts = 0;
            const poll = setInterval(async () => {
                attempts++;
                try {
                    const check = await fetch(`${API}/api/thumb/check`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: filePath })
                    });
                    const checkData = await check.json();
                    if (checkData.exists) {
                        clearInterval(poll);
                        const newSrc = `${API}/api/thumb?path=${encodeURIComponent(filePath)}&t=${Date.now()}`;
                        const testImg = new Image();
                        testImg.onload = () => {
                            if (card) {
                                const img = card.querySelector('.file-thumb img');
                                const loader = card.querySelector('.file-loading');
                                if (img) { img.src = newSrc; img.style.display = 'block'; img.dataset.loaded = 'true'; }
                                if (loader) loader.style.display = 'none';
                            }
                            showToast(I18N.t('toast.thumb_regenerated'), 'success');
                        };
                        testImg.onerror = () => showToast(I18N.t('toast.thumb_load_error'), 'error');
                        testImg.src = newSrc;
                    } else if (attempts >= 30) {
                        clearInterval(poll);
                        showToast(I18N.t('toast.timeout_retry'), 'warning');
                    }
                } catch { clearInterval(poll); }
            }, 1000);
        } catch {
            showToast(I18N.t('toast.connection_error'), 'error');
        }
    };


    let _costMetadata = null;
    let _costSaveTimer = null;
    let _preciseEstimate = null;
    let _preciseEstimateStatus = 'idle';
    let _preciseEstimateTimer = null;
    let _aiTimePrediction = null;
    let _ecoEstimate = null;

    function _costSaveSettings() {
        clearTimeout(_costSaveTimer);
        _costSaveTimer = setTimeout(async () => {
            const material = document.getElementById('cost-material-select')?.value;
            const spoolId = document.getElementById('cost-spool-select')?.value;
            const spoolPrice = parseFloat(document.getElementById('cost-spool-price')?.value);
            const spoolWeight = parseFloat(document.getElementById('cost-spool-weight')?.value);
            const elecPrice = document.getElementById('cost-elec-price')?.value;
            const printerPower = document.getElementById('cost-printer-power')?.value;

            try {
                const res = await fetch(`${API}/api/settings`);
                const settings = res.ok ? await res.json() : {};
                let spools = Array.isArray(settings.print_cost_spools) ? settings.print_cost_spools.slice() : [];
                if (spools.length === 0) {
                    spools = [{
                        id: (spoolId && spoolId !== '__legacy') ? spoolId : (crypto.randomUUID ? crypto.randomUUID() : 'spool_' + Date.now()),
                        name: I18N.t('cost.spool_default_name') || 'Bobine',
                        price: Number.isFinite(spoolPrice) ? spoolPrice : 20,
                        weight: Number.isFinite(spoolWeight) ? spoolWeight : 1000,
                    }];
                } else if (spoolId && spoolId !== '__legacy') {
                    spools = spools.map(s => s.id === spoolId
                        ? { ...s, price: Number.isFinite(spoolPrice) ? spoolPrice : s.price, weight: Number.isFinite(spoolWeight) ? spoolWeight : s.weight }
                        : s);
                }
                await fetch(`${API}/api/settings`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        print_cost_material: material,
                        print_cost_spools: spools,
                        print_cost_elec_price: elecPrice,
                        print_cost_printer_power: printerPower
                    })
                });
            } catch (_) {  }
        }, 600);
    }

    function _recomputeCost() {
        const resultsEl = document.getElementById('cost-results');
        if (!resultsEl || !_costMetadata) return;

        const material = document.getElementById('cost-material-select')?.value || 'pla';
        const spoolPrice = parseFloat(document.getElementById('cost-spool-price')?.value) || 0;
        const spoolWeight = parseFloat(document.getElementById('cost-spool-weight')?.value) || 1000;
        const elecPriceRaw = document.getElementById('cost-elec-price')?.value ?? '';
        const elecPrice = parseFloat(elecPriceRaw);
        const printerPower = parseFloat(document.getElementById('cost-printer-power')?.value) || 120;

        const weightG = _preciseEstimate?.weight_g ?? (_costMetadata.weights?.[material] ?? 0);
        const timeSeconds = _preciseEstimate?.time_seconds ?? (_costMetadata.estimated_time?.seconds ?? 0);
        const timeFormatted = _preciseEstimate?.time_formatted ?? (_costMetadata.estimated_time?.formatted ?? '—');
        const timeHours = timeSeconds / 3600;

        const pricePerGram = spoolWeight > 0 ? (spoolPrice / spoolWeight) : 0;
        const materialCost = weightG * pricePerGram;

        const hasElec = elecPriceRaw !== '' && !isNaN(elecPrice) && elecPrice > 0;
        const elecCost = hasElec ? timeHours * (printerPower / 1000) * elecPrice : 0;

        const total = materialCost + elecCost;

        const preciseBadgeHtml = {
            done: `<div style="display:flex; align-items:center; gap:6px; font-size:11px; color:#68d391; margin-bottom:10px;"><i class="fa-solid fa-circle-check"></i> ${I18N.t('cost.precise_via_slicer', { slicer: escapeHtml(_preciseEstimate?.slicer_name || '') })}</div>`,
            pending: `<div style="display:flex; align-items:center; gap:6px; font-size:11px; color:var(--text-muted); margin-bottom:10px;"><i class="fa-solid fa-spinner fa-spin"></i> ${I18N.t('cost.precise_searching')}</div>`,
            unavailable: `<div style="display:flex; align-items:center; gap:6px; font-size:11px; color:var(--text-muted); margin-bottom:10px;"><i class="fa-solid fa-circle-info"></i> ${I18N.t('cost.precise_no_slicer')}</div>`,
            error: `<div style="display:flex; align-items:center; gap:6px; font-size:11px; color:var(--text-muted); margin-bottom:10px;"><i class="fa-solid fa-circle-info"></i> ${I18N.t('cost.precise_failed')}</div>`,
            idle: ''
        }[_preciseEstimateStatus] || '';

        resultsEl.innerHTML = `
            <div style="display:flex; flex-direction:column; gap:8px; background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius); padding:14px; margin-top:14px;">
                ${preciseBadgeHtml}
                <div style="display:flex; justify-content:space-between; font-size:13px; color:var(--text-secondary);">
                    <span><i class="fa-solid fa-weight-hanging" style="width:16px;"></i> ${I18N.t('cost.estimated_weight_label', { material: material.toUpperCase() })}</span>
                    <strong style="color:var(--text-primary);">${weightG.toFixed(1)} g</strong>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:13px; color:var(--text-secondary);">
                    <span><i class="fa-solid fa-clock" style="width:16px;"></i> ${I18N.t('cost.estimated_time_label')}</span>
                    <strong style="color:var(--text-primary);">${timeFormatted}</strong>
                </div>
                ${_aiTimePrediction && ['medium', 'high'].includes(_aiTimePrediction.confidence) ? `
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; color:var(--text-muted); margin-top:-4px;">
                    <span><i class="fa-solid fa-brain" style="width:16px;"></i> ${_t2('cost.ai_corrected_time_label', 'Estimation ajustée (historique local)')}</span>
                    <strong style="color:var(--accent);">${_aiTimePrediction.corrected_formatted}</strong>
                </div>
                <div style="font-size:10px; color:var(--text-muted); text-align:right; margin-top:-6px;">
                    ${_t2('cost.ai_corrected_time_hint', `Basé sur ${_aiTimePrediction.sample_size} impression(s) précédente(s) — facteur x${_aiTimePrediction.correction_factor}`, { n: _aiTimePrediction.sample_size, f: _aiTimePrediction.correction_factor })}
                </div>` : ''}
                <div style="border-top:1px solid var(--border); margin:4px 0;"></div>
                <div style="display:flex; justify-content:space-between; font-size:13px; color:var(--text-secondary);">
                    <span><i class="fa-solid fa-spool" style="width:16px;"></i> ${I18N.t('cost.material_cost_label')}</span>
                    <strong style="color:var(--text-primary);">${formatCost(materialCost)}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:13px; color:${hasElec ? 'var(--text-secondary)' : 'var(--text-muted)'};">
                    <span><i class="fa-solid fa-bolt" style="width:16px;"></i> ${I18N.t('cost.electricity_cost_label')}</span>
                    <strong style="color:${hasElec ? 'var(--text-primary)' : 'var(--text-muted)'};">${hasElec ? formatCost(elecCost) : I18N.t('printers.no_value_set')}</strong>
                </div>
                <div style="border-top:1px solid var(--border); margin:4px 0;"></div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:15px;">
                    <span style="color:var(--text-primary); font-weight:600;">${I18N.t('cost.total_estimated_label')}</span>
                    <strong style="color:var(--accent); font-size:18px;">${formatCost(total)}</strong>
                </div>
				<div style="display:flex; justify-content:space-between; font-size:13px; color:var(--text-secondary);">
					<span>${I18N.t('cost.slicer_estimate_note')}</span>
				</div>
                ${_ecoEstimate ? `
                <div style="border-top:1px solid var(--border); margin:4px 0;"></div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:13px; color:var(--text-secondary);">
                    <span><i class="fa-solid fa-leaf" style="width:16px; color:#4ade80;"></i> ${_t2('cost.eco_score_label', 'Empreinte carbone estimée')}</span>
                    <strong style="color:#4ade80;">${_ecoEstimate.total_co2_g} g CO₂e</strong>
                </div>
                <div style="font-size:10px; color:var(--text-muted); text-align:right; margin-top:-4px;">
                    ${_t2('cost.eco_score_hint', 'Estimation indicative (matériau' + (_ecoEstimate.elec_co2_g != null ? ' + électricité' : '') + '), pas une mesure certifiée')}
                </div>` : ''}
            </div>
        `;
    }

    function _handlePreciseEstimateStatus(data, filePath) {
        if (!data || filePath !== _costCurrentFilePath) return;
        if (data.status === 'done' && data.data) {
            _preciseEstimate = data.data;
            _preciseEstimateStatus = 'done';
            _recomputeCost();
            _loadFilamentCompatibility(filePath);
            _fetchAiTimePrediction(filePath);
            _fetchEcoEstimate(filePath);
            return;
        }
        if (data.status === 'unavailable' || data.status === 'error') {
            _preciseEstimateStatus = data.status;
            _recomputeCost();
            return;
        }
        _preciseEstimateStatus = 'pending';
        _recomputeCost();
        clearTimeout(_preciseEstimateTimer);
        _preciseEstimateTimer = setTimeout(async () => {
            try {
                const res = await fetch(`${API}/api/slicer/pre-slice-estimate?path=${encodeURIComponent(filePath)}`);
                const d = await res.json();
                _handlePreciseEstimateStatus(d, filePath);
            } catch (e) {  }
        }, 3000);
    }

    async function _startPreciseEstimate(filePath) {
        try {
            const res = await fetch(`${API}/api/slicer/pre-slice-estimate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            });
            const data = await res.json();
            _handlePreciseEstimateStatus(data, filePath);
        } catch (e) {
            console.debug('[PreSlice] Requête impossible:', e);
        }
    }

    async function _fetchAiTimePrediction(filePath) {
        try {
            const res = await fetch(`${API}/api/ai/predict-print-time`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            });
            if (!res.ok) return;
            const data = await res.json();
            if (data.status !== 'done' || filePath !== _costCurrentFilePath) return;
            _aiTimePrediction = data;
            _recomputeCost();
        } catch (e) {
            console.debug('[AI][PrintTime] Requête impossible:', e);
        }
    }

    async function _fetchEcoEstimate(filePath) {
        try {
            const res = await fetch(`${API}/api/eco/estimate?path=${encodeURIComponent(filePath)}`);
            if (!res.ok) return;
            const data = await res.json();
            if (data.status !== 'done' || filePath !== _costCurrentFilePath) return;
            _ecoEstimate = data;
            _recomputeCost();
        } catch (e) {
            console.debug('[Eco] Requête impossible:', e);
        }
    }

    let _costCurrentFilePath = null;

    function _t2(key, fallback, params) {
        try {
            const val = params ? I18N.t(key, params) : I18N.t(key);
            if (!val || val === key) return fallback;
            return val;
        } catch (e) {
            return fallback;
        }
    }


    window._t2 = _t2;

    const FILAMENT_SOURCE_BADGES = {
        spoolman: '🔵',
        bambu_ams: '🟠',
        creality_cfs: '🟢',
        manual: '⚪'
    };
    const FILAMENT_SOURCE_LABELS = {
        spoolman: 'Spoolman',
        bambu_ams: 'AMS',
        creality_cfs: 'CFS',
        manual: _t2('spoolman.manual_source', 'Manuel')
    };

    let _compatSlotsCache = {};

    async function _loadFilamentCompatibility(filePath) {
        const container = document.getElementById('cost-filament-compat');
        if (!container) return;
        container.innerHTML = `<div style="margin-top:14px; padding-top:14px; border-top:1px solid var(--border);">
            <p style="font-size:13px; font-weight:600; margin-bottom:4px; display:flex; align-items:center; justify-content:space-between;">
                <span><i class="fa-solid fa-layer-group"></i> ${_t2('spoolman.compat_title', 'Compatibilité filament')}</span>
                <button class="btn btn-ghost btn-sm" style="padding:2px 8px; font-size:11px;" onclick="openManualSpoolModal('${escapeJs(filePath)}')"><i class="fa-solid fa-plus"></i> ${_t2('spoolman.add_manual', 'Bobine manuelle')}</button>
            </p>
            <p style="font-size:10px; color:var(--text-muted); margin-bottom:8px;">
                ${_t2('spoolman.legend_source', '🔵 Spoolman · 🟠 AMS · 🟢 CFS · ⚪ Manuel')}
                &nbsp;—&nbsp;
                ${_t2('spoolman.legend_compat', '🟢 quantité suffisante · 🔴 insuffisante · ⚪ poids inconnu')}
            </p>
            <div id="cost-filament-compat-list" style="display:flex; flex-direction:column; gap:6px;">
                <p style="font-size:12px; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> ${_t2('spoolman.compat_loading', 'Recherche des bobines compatibles...')}</p>
            </div>
        </div>`;

        try {
            const res = await fetch(`${API}/api/filament/compatibility?path=${encodeURIComponent(filePath)}`);
            const data = await res.json();
            const list = document.getElementById('cost-filament-compat-list');
            if (!list || filePath !== _costCurrentFilePath) return;
            if (!res.ok) {
                list.innerHTML = `<p style="font-size:12px; color:var(--text-muted);">${escapeHtml(data.error || _t2('spoolman.compat_error', 'Erreur lors de la vérification de compatibilité'))}</p>`;
                return;
            }
            const slots = data.slots || [];
            if (!slots.length) {
                list.innerHTML = `<p style="font-size:12px; color:var(--text-muted);">${_t2('spoolman.no_spools', 'Aucune bobine trouvée')}</p>
                    <p style="font-size:11px; color:var(--text-muted); margin-top:4px;">${_t2('spoolman.no_source_hint', 'Configurez Spoolman, connectez une imprimante AMS Bambu, ou ajoutez une bobine manuelle.')}</p>`;
                return;
            }
            const assignedKey = data.assigned ? `${data.assigned.source_type}:${data.assigned.source_id}` : null;
            const rows = slots.slice(0, 12).map(s => _renderCompatSlotRow(s, filePath, assignedKey)).join('');
            const noWeightNote = data.required_weight_g == null
                ? `<p style="font-size:11px; color:var(--text-muted); margin-bottom:6px;">${_t2('spoolman.compat_no_weight', 'Poids non estimé pour ce fichier — la compatibilité ne peut pas être calculée précisément.')}</p>` : '';
            const errorsNote = (data.errors || []).length
                ? `<p style="font-size:11px; color:var(--text-muted); margin-bottom:6px;"><i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(data.errors.join(' · '))}</p>` : '';
            list.innerHTML = noWeightNote + errorsNote + rows;
        } catch (e) {
            const list = document.getElementById('cost-filament-compat-list');
            if (list) list.innerHTML = `<p style="font-size:12px; color:var(--text-muted);">${_t2('spoolman.server_unreachable', 'Serveur injoignable')}</p>`;
        }
    }

    function _renderCompatSlotRow(s, filePath, assignedKey) {
        const color = s.color_hex || '#888888';
        const name = s.name || '—';
        const material = s.material || '';
        const remaining = typeof s.remaining_g === 'number' ? Math.round(s.remaining_g) : null;
        const compatible = s.compatible;
        const slotKey = `${s.source_type}:${s.source_id}`;
        const isAssigned = assignedKey === slotKey;
        const compatIcon = compatible === true ? '🟢' : compatible === false ? '🔴' : '⚪';
        const compatTitle = compatible === true
            ? (_t2('spoolman.compat_ok_title', 'Quantité suffisante pour cette impression'))
            : compatible === false
                ? (_t2('spoolman.compat_ko_title', 'Quantité restante insuffisante pour cette impression'))
                : (_t2('spoolman.compat_unknown_title', 'Poids restant inconnu — compatibilité non calculable'));
        const sourceBadge = FILAMENT_SOURCE_BADGES[s.source_type] || '⚪';
        const sourceLabel = FILAMENT_SOURCE_LABELS[s.source_type] || s.source_type;

        _compatSlotsCache[slotKey] = s;

        let actionHtml;
        if (isAssigned) {
            actionHtml = `<span style="color:#68d391; font-size:11px; white-space:nowrap;"><i class="fa-solid fa-check"></i> ${_t2('spoolman.assigned', 'Assignée')}</span>
                <button class="btn btn-ghost btn-sm" style="padding:3px 8px;" onclick="unassignFilamentFromFile('${escapeJs(filePath)}')">${_t2('spoolman.unassign', 'Retirer')}</button>`;
        } else if (compatible === false) {
            actionHtml = `<span style="color:#fc8181; white-space:nowrap; font-size:11px;">${_t2('spoolman.insufficient', 'Quantité insuffisante')}</span>`;
        } else {
            actionHtml = `<button class="btn btn-ghost btn-sm" style="padding:3px 8px;" onclick="assignFilamentToFile('${escapeJs(filePath)}', '${escapeJs(s.source_type)}', '${escapeJs(s.source_id)}')">${_t2('spoolman.assign', 'Assigner')}</button>`;
        }

        return `<div style="display:flex; align-items:center; gap:8px; padding:6px 8px; border-radius:var(--radius); background:var(--bg-card); border:1px solid ${isAssigned ? '#68d391' : 'var(--border)'}; font-size:12px;">
            <span title="${escapeHtml(_t2('spoolman.source_title', 'Source') + ' : ' + sourceLabel)}">${sourceBadge}</span>
            <span title="${escapeHtml(compatTitle)}">${compatIcon}</span>
            <span title="${escapeHtml(_t2('spoolman.color_title', 'Couleur du filament'))}" style="background:${color}; width:10px; height:10px; border-radius:50%; flex-shrink:0; display:inline-block; border:1px solid rgba(255,255,255,0.15);"></span>
            <span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(name)} <span style="color:var(--text-muted);">(${escapeHtml(material)})</span></span>
            <span style="color:var(--text-muted); white-space:nowrap;">${remaining !== null ? remaining + 'g' : '—'}</span>
            ${actionHtml}
        </div>`;
    }

    window.unassignFilamentFromFile = async function (filePath) {
        try {
            await fetch(`${API}/api/files/unassign-filament`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            });
            showToast(`✅ ${_t2('spoolman.unassigned_success', 'Bobine retirée')}`, 'success');
            _loadFilamentCompatibility(filePath);
        } catch (e) {
            showToast(I18N.t('toast.server_error'), 'error');
        }
    };

    window.assignFilamentToFile = async function (filePath, sourceType, sourceId) {
        const slotKey = `${sourceType}:${sourceId}`;
        const info = _compatSlotsCache[slotKey] || {};
        try {
            await fetch(`${API}/api/files/assign-filament`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path: filePath, source_type: sourceType, source_id: sourceId,
                    name: info.name || '', material: info.material || '', color_hex: info.color_hex || '',
                    spoolman_url: info.spoolman_url || '', printer_id: info.printer_id || null
                })
            });
            showToast(`✅ ${_t2('spoolman.assigned_success', `${info.name || ('#' + sourceId)} assignée à ce fichier`, { name: info.name || ('#' + sourceId) })}`, 'success');
            _loadFilamentCompatibility(filePath);
        } catch (e) {
            showToast(I18N.t('toast.server_error'), 'error');
        }
    };

    window.openManualSpoolModal = function (filePath) {
        let modal = document.getElementById('modal-manual-spool');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'modal-manual-spool';
            modal.className = 'modal hidden';
            modal.innerHTML = `<div class="modal-content" style="max-width:420px;">
                <div class="modal-header">
                    <h3><i class="fa-solid fa-spool"></i> ${_t2('spoolman.add_manual', 'Bobine manuelle')}</h3>
                    <button class="modal-close" onclick="closeModal('modal-manual-spool')">×</button>
                </div>
                <div class="modal-body" style="display:flex; flex-direction:column; gap:10px;">
                    <p style="font-size:12px; color:var(--text-muted);">${_t2('spoolman.manual_hint', "Pour les systèmes multicolores non connectés nativement (ex: Creality CFS) — déclarez la bobine à la main.")}</p>
                    <input type="text" id="manual-spool-name" class="form-input" placeholder="${_t2('spoolman.name', 'Nom')} (ex: PLA Noir CFS)">
                    <div style="display:flex; gap:8px;">
                        <input type="text" id="manual-spool-material" class="form-input" placeholder="${_t2('spoolman.material', 'Matière')} (PLA, PETG...)" style="flex:1;">
                        <input type="color" id="manual-spool-color" value="#888888" style="width:44px; height:38px; padding:2px; border-radius:var(--radius); border:1px solid var(--border);">
                    </div>
                    <div style="display:flex; gap:8px;">
                        <input type="number" id="manual-spool-remaining" class="form-input" placeholder="${_t2('spoolman.remaining_g', 'Poids restant (g)')}" style="flex:1;">
                        <input type="number" id="manual-spool-capacity" class="form-input" placeholder="${_t2('spoolman.capacity_g', 'Poids total (g)')}" value="1000" style="flex:1;">
                    </div>
                    <button class="btn btn-primary" onclick="createManualSpool()"><i class="fa-solid fa-check"></i> ${_t2('actions.save', 'Enregistrer')}</button>
                    <div id="manual-spool-existing-list" style="display:flex; flex-direction:column; gap:6px; margin-top:6px; border-top:1px solid var(--border); padding-top:10px;"></div>
                </div>
            </div>`;
            document.body.appendChild(modal);
            modal.addEventListener('click', (e) => { if (e.target === modal) closeModal('modal-manual-spool'); });
        }
        modal.dataset.filePath = filePath || '';
        openModal('modal-manual-spool');
        _refreshManualSpoolList();
    };

    async function _refreshManualSpoolList() {
        const box = document.getElementById('manual-spool-existing-list');
        if (!box) return;
        box.innerHTML = `<p style="font-size:11px; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i></p>`;
        try {
            const res = await fetch(`${API}/api/filament/manual`);
            const spools = await res.json();
            if (!Array.isArray(spools) || !spools.length) {
                box.innerHTML = `<p style="font-size:11px; color:var(--text-muted);">${_t2('spoolman.no_spools', 'Aucune bobine trouvée')}</p>`;
                return;
            }
            box.innerHTML = spools.map(s => `
                <div style="display:flex; align-items:center; gap:8px; font-size:12px;">
                    <span style="background:${s.color_hex || '#888'}; width:10px; height:10px; border-radius:50%; display:inline-block; flex-shrink:0;"></span>
                    <span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(s.name)} <span style="color:var(--text-muted);">(${escapeHtml(s.material || '')})</span></span>
                    <span style="color:var(--text-muted);">${s.remaining_g != null ? Math.round(s.remaining_g) + 'g' : '—'}</span>
                    <button class="btn btn-ghost btn-sm" style="padding:2px 6px;" onclick="deleteManualSpool(${s.id})"><i class="fa-solid fa-trash"></i></button>
                </div>`).join('');
        } catch (e) {
            box.innerHTML = `<p style="font-size:11px; color:var(--text-muted);">${_t2('spoolman.server_unreachable', 'Serveur injoignable')}</p>`;
        }
    }

    window.deleteManualSpool = async function (id) {
        try {
            await fetch(`${API}/api/filament/manual/${id}`, { method: 'DELETE' });
            _refreshManualSpoolList();
            const modal = document.getElementById('modal-manual-spool');
            const filePath = modal?.dataset.filePath;
            if (filePath) _loadFilamentCompatibility(filePath);
        } catch (e) {
            showToast(I18N.t('toast.server_error'), 'error');
        }
    };

    window.createManualSpool = async function () {
        const modal = document.getElementById('modal-manual-spool');
        const name = document.getElementById('manual-spool-name')?.value.trim();
        if (!name) { showToast(_t2('toast.enter_name', 'Nom requis'), 'error'); return; }
        const material = document.getElementById('manual-spool-material')?.value.trim() || '';
        const color_hex = document.getElementById('manual-spool-color')?.value || '#888888';
        const remaining_g = parseFloat(document.getElementById('manual-spool-remaining')?.value);
        const capacity_g = parseFloat(document.getElementById('manual-spool-capacity')?.value) || 1000;
        try {
            const res = await fetch(`${API}/api/filament/manual`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, material, color_hex, remaining_g: isNaN(remaining_g) ? null : remaining_g, capacity_g })
            });
            if (!res.ok) throw new Error();
            showToast(`✅ ${_t2('spoolman.manual_created', 'Bobine ajoutée')}`, 'success');
            closeModal('modal-manual-spool');
            const filePath = modal?.dataset.filePath;
            if (filePath) _loadFilamentCompatibility(filePath);
        } catch (e) {
            showToast(I18N.t('toast.server_error'), 'error');
        }
    };


    let _photosCurrentPath = null;
    let _photosSelectedResult = 'success';
    let _photosCurrentFilter = '';

    window.openPrintPhotosModal = async function (filePath, fileName) {
        _photosCurrentPath = filePath;
        _photosCurrentFilter = '';
        document.getElementById('print-photos-file-name').textContent = fileName;
        document.getElementById('print-photo-note-input').value = '';
        setPrintPhotoResult('success');
        document.querySelectorAll('#modal-print-photos .print-photo-filter-btn').forEach(b => b.classList.toggle('active', b.dataset.filter === ''));
        openModal('modal-print-photos');
        await _reloadPrintPhotos();
    };

    window.setPrintPhotoResult = function (result) {
        _photosSelectedResult = result;
        document.querySelectorAll('.print-photo-result-btn').forEach(btn => {
            const active = btn.dataset.result === result;
            btn.classList.toggle('active', active);
            btn.style.background = active ? 'var(--accent)' : 'var(--bg-card)';
            btn.style.color = active ? '#fff' : 'var(--text-secondary)';
        });
    };

    window.filterPrintPhotos = function (filter) {
        _photosCurrentFilter = filter;
        document.querySelectorAll('#modal-print-photos .print-photo-filter-btn').forEach(b => b.classList.toggle('active', b.dataset.filter === filter));
        _reloadPrintPhotos();
    };

    function _photoCardHtml(p) {
        const isFailed = p.result === 'failed';
        return `
            <div style="position:relative; border-radius:var(--radius); overflow:hidden; background:var(--bg-card); border:1px solid var(--border);">
                <img src="${API}${p.url}" loading="lazy" style="width:100%; aspect-ratio:1; object-fit:cover; display:block; cursor:pointer;" onclick="openPhotoLightbox('${API}${p.url}', '${escapeHtml(p.file_name)}')">
                <span style="position:absolute; top:4px; left:4px; padding:2px 7px; border-radius:10px; font-size:10px; font-weight:600; color:#fff; background:${isFailed ? 'rgba(220,53,69,0.85)' : 'rgba(40,167,69,0.85)'};">
                    <i class="fa-solid ${isFailed ? 'fa-xmark' : 'fa-check'}"></i> ${isFailed ? (I18N.t('modal.print_photos_failed') || 'Raté') : (I18N.t('modal.print_photos_success') || 'Réussi')}
                </span>
                <button onclick="deletePrintPhoto(${p.id})" title="${I18N.t('actions.delete') || 'Supprimer'}" style="position:absolute; top:4px; right:4px; width:24px; height:24px; border-radius:50%; background:rgba(0,0,0,0.6); color:#fff; border:none; cursor:pointer; display:flex; align-items:center; justify-content:center;">
                    <i class="fa-solid fa-xmark" style="font-size:11px;"></i>
                </button>
                ${p.note ? `<div style="padding:6px 8px; font-size:11px; color:var(--text-secondary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${escapeHtml(p.note)}">${escapeHtml(p.note)}</div>` : ''}
            </div>
        `;
    }

    async function _reloadPrintPhotos() {
        const grid = document.getElementById('print-photos-grid');
        grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:20px; color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i></div>`;
        try {
            let url = `${API}/api/print-photos?path=${encodeURIComponent(_photosCurrentPath)}`;
            if (_photosCurrentFilter) url += `&result=${_photosCurrentFilter}`;
            const res = await fetch(url);
            const photos = await res.json();
            if (!res.ok || !Array.isArray(photos) || !photos.length) {
                grid.innerHTML = `<p style="grid-column:1/-1; color:var(--text-muted); font-size:13px; text-align:center; padding:20px;">${I18N.t('modal.print_photos_empty') || "Aucune photo pour ce fichier. Ajoute la première !"}</p>`;
                return;
            }
            grid.innerHTML = photos.map(_photoCardHtml).join('');
        } catch (e) {
            grid.innerHTML = `<p style="grid-column:1/-1; color:var(--danger); font-size:13px; text-align:center; padding:20px;">${I18N.t('toast.connection_error')}</p>`;
        }
    }

    window.deletePrintPhoto = async function (photoId) {
        try {
            const res = await fetch(`${API}/api/print-photos/${photoId}`, { method: 'DELETE' });
            if (!res.ok) { showToast(I18N.t('toast.error') || 'Erreur', 'error'); return; }
            if (document.getElementById('page-gallery')?.classList.contains('active')) {
                await loadGalleryPage();
            } else {
                await _reloadPrintPhotos();
            }
        } catch (e) {
            showToast(I18N.t('toast.connection_error'), 'error');
        }
    };

    let _galleryCurrentFilter = '';

    window.filterGallery = function (filter) {
        _galleryCurrentFilter = filter;
        document.querySelectorAll('#page-gallery .gallery-filter-btn').forEach(b => b.classList.toggle('active', b.dataset.filter === filter));
        loadGalleryPage();
    };

    window.loadGalleryPage = async function () {
        const loading = document.getElementById('gallery-loading');
        const empty = document.getElementById('gallery-empty');
        const grid = document.getElementById('gallery-grid');
        loading?.classList.remove('hidden');
        empty?.classList.add('hidden');
        grid?.classList.add('hidden');
        try {
            let url = `${API}/api/print-photos`;
            if (_galleryCurrentFilter) url += `?result=${_galleryCurrentFilter}`;
            const res = await fetch(url);
            const photos = await res.json();
            loading?.classList.add('hidden');
            if (!res.ok || !Array.isArray(photos) || !photos.length) {
                empty?.classList.remove('hidden');
                return;
            }
            grid.innerHTML = photos.map(p => {
                const isFailed = p.result === 'failed';
                return `
                <div style="position:relative; border-radius:var(--radius); overflow:hidden; background:var(--bg-card); border:1px solid var(--border);">
                    <img src="${API}${p.url}" loading="lazy" style="width:100%; aspect-ratio:1; object-fit:cover; display:block; cursor:pointer;" onclick="openPhotoLightbox('${API}${p.url}', '${escapeHtml(p.file_name)}')">
                    <span style="position:absolute; top:4px; left:4px; padding:2px 7px; border-radius:10px; font-size:10px; font-weight:600; color:#fff; background:${isFailed ? 'rgba(220,53,69,0.85)' : 'rgba(40,167,69,0.85)'};">
                        <i class="fa-solid ${isFailed ? 'fa-xmark' : 'fa-check'}"></i> ${isFailed ? (I18N.t('modal.print_photos_failed') || 'Raté') : (I18N.t('modal.print_photos_success') || 'Réussi')}
                    </span>
                    <button onclick="deletePrintPhoto(${p.id})" title="${I18N.t('actions.delete') || 'Supprimer'}" style="position:absolute; top:4px; right:4px; width:24px; height:24px; border-radius:50%; background:rgba(0,0,0,0.6); color:#fff; border:none; cursor:pointer; display:flex; align-items:center; justify-content:center;">
                        <i class="fa-solid fa-xmark" style="font-size:11px;"></i>
                    </button>
                    <div style="padding:6px 8px;">
                        <div style="font-size:11px; font-weight:600; color:var(--text-primary); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; cursor:pointer;" title="${escapeHtml(p.file_name)}" onclick="openPrintPhotosModal('${escapeJs(p.file_path)}', '${escapeJs(p.file_name)}')">
                            <i class="fa-solid fa-cube" style="color:var(--text-muted);"></i> ${escapeHtml(p.file_name)}
                        </div>
                        ${p.note ? `<div style="font-size:11px; color:var(--text-secondary); margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${escapeHtml(p.note)}">${escapeHtml(p.note)}</div>` : ''}
                    </div>
                </div>
            `;
            }).join('');
            grid?.classList.remove('hidden');
        } catch (e) {
            loading?.classList.add('hidden');
            showToast(I18N.t('toast.connection_error'), 'error');
        }
    };


	window.openPhotoLightbox = function(url, filename) {
		let overlay = document.getElementById('photo-lightbox-overlay');
		if (!overlay) {
			overlay = document.createElement('div');
			overlay.id = 'photo-lightbox-overlay';
			overlay.style.cssText = `
				position: fixed; inset: 0;
				background: rgba(0,0,0,0.92);
				backdrop-filter: blur(6px);
				display: flex; align-items: center; justify-content: center;
				z-index: 100000;
				animation: fadeIn 0.2s ease;
			`;
			overlay.addEventListener('click', (e) => {
				if (e.target === overlay) closePhotoLightbox();
			});

			const img = document.createElement('img');
			img.id = 'photo-lightbox-img';
			img.style.cssText = `
				max-width: 92vw; max-height: 90vh;
				object-fit: contain;
				border-radius: 8px;
				box-shadow: 0 8px 40px rgba(0,0,0,0.6);
			`;
			overlay.appendChild(img);

			const caption = document.createElement('div');
			caption.id = 'photo-lightbox-caption';
			caption.style.cssText = `
				position: absolute; bottom: 20px; left: 50%;
				transform: translateX(-50%);
				color: #fff; font-size: 13px;
				background: rgba(0,0,0,0.6);
				padding: 6px 16px; border-radius: 20px;
				white-space: nowrap; max-width: 80vw;
				overflow: hidden; text-overflow: ellipsis;
			`;
			overlay.appendChild(caption);

			const closeBtn = document.createElement('button');
			closeBtn.innerHTML = '×';
			closeBtn.style.cssText = `
				position: absolute; top: 16px; right: 20px;
				background: rgba(0,0,0,0.5); color: #fff;
				border: none; border-radius: 50%;
				width: 40px; height: 40px;
				font-size: 22px; cursor: pointer;
				display: flex; align-items: center; justify-content: center;
				transition: background 0.2s;
			`;
			closeBtn.addEventListener('mouseenter', () => closeBtn.style.background = 'var(--accent)');
			closeBtn.addEventListener('mouseleave', () => closeBtn.style.background = 'rgba(0,0,0,0.5)');
			closeBtn.addEventListener('click', closePhotoLightbox);
			overlay.appendChild(closeBtn);

			document.body.appendChild(overlay);
		}

		const imgEl = document.getElementById('photo-lightbox-img');
		const captionEl = document.getElementById('photo-lightbox-caption');
		imgEl.src = url;
		captionEl.textContent = filename || '';
		overlay.style.display = 'flex';

		document.addEventListener('keydown', _photoLightboxEscHandler);
	};

	window.closePhotoLightbox = function() {
		const overlay = document.getElementById('photo-lightbox-overlay');
		if (overlay) {
			overlay.style.display = 'none';
			document.getElementById('photo-lightbox-img').src = '';
		}
		document.removeEventListener('keydown', _photoLightboxEscHandler);
	};

	function _photoLightboxEscHandler(e) {
		if (e.key === 'Escape') closePhotoLightbox();
	}
    async function _uploadPrintPhoto(file) {
        if (!file || !_photosCurrentPath) return;
        const note = document.getElementById('print-photo-note-input')?.value || '';
        const formData = new FormData();
        formData.append('path', _photosCurrentPath);
        formData.append('note', note);
        formData.append('result', _photosSelectedResult);
        formData.append('photo', file);

        try {
            const res = await fetch(`${API}/api/print-photos`, { method: 'POST', body: formData });
            const data = await res.json();
            if (!res.ok) { showToast(data.error || I18N.t('toast.error') || 'Erreur', 'error'); return; }
            document.getElementById('print-photo-note-input').value = '';
            showToast(I18N.t('toast.print_photo_added') || 'Photo ajoutée !', 'success');
            await _reloadPrintPhotos();
        } catch (err) {
            showToast(I18N.t('toast.connection_error'), 'error');
        }
    }

    document.getElementById('print-photo-file-input')?.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        e.target.value = '';
        await _uploadPrintPhoto(file);
    });

    (function initPrintPhotoDropZone() {
        const modalBody = document.querySelector('#modal-print-photos .modal-body');
        if (!modalBody) return;
        let dragCounter = 0;

        modalBody.addEventListener('dragenter', (e) => {
            e.preventDefault();
            dragCounter++;
            modalBody.classList.add('drop-zone-active');
        });
        modalBody.addEventListener('dragover', (e) => e.preventDefault());
        modalBody.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dragCounter = Math.max(0, dragCounter - 1);
            if (dragCounter === 0) modalBody.classList.remove('drop-zone-active');
        });
        modalBody.addEventListener('drop', async (e) => {
            e.preventDefault();
            dragCounter = 0;
            modalBody.classList.remove('drop-zone-active');

            const files = [...(e.dataTransfer?.files || [])].filter(f => f.type.startsWith('image/'));
            if (!files.length) {
                showToast(I18N.t('toast.drop_image_only') || "Seules les images (jpg, png, webp) peuvent être déposées ici.", 'error');
                return;
            }
            for (const file of files) {
                await _uploadPrintPhoto(file);
            }
        });
    })();

    window.openFileMetadataModal = async function (filePath, fileName) {
        const body = document.getElementById('file-metadata-body');
        openModal('modal-file-metadata');
        body.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-muted)"><i class="fa-solid fa-spinner fa-spin fa-2x"></i></div>`;

        const f = (allFiles || []).find(x => x.path === filePath) || {};
        const row = (label, value) => value === null || value === undefined || value === '' ? '' :
            `<div style="display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid var(--border); font-size:13px;">
                <span style="color:var(--text-muted);">${escapeHtml(label)}</span>
                <span style="font-weight:500; text-align:right; max-width:60%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(String(value))}">${escapeHtml(String(value))}</span>
            </div>`;

        let metadata = null;
        try {
            const res = await fetch(`${API}/api/files/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            });
            const data = await res.json();
            if (res.ok) metadata = data.metadata || null;
        } catch (e) {  }

        const dims = metadata?.dimensions ? `${metadata.dimensions.x} × ${metadata.dimensions.y} × ${metadata.dimensions.z} mm` : null;
        const weight = metadata?.weights?.pla ? `${metadata.weights.pla} g (PLA)` : null;

        body.innerHTML = `
            <p style="font-size:13px; color:var(--text-secondary); margin-bottom:14px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(fileName)}">
                <i class="fa-solid fa-cube"></i> ${escapeHtml(fileName)}
            </p>
            <h4 style="font-size:12px; text-transform:uppercase; color:var(--text-muted); margin:14px 0 4px;" data-i18n="modal.metadata_file_section">Fichier</h4>
            ${row(I18N.t('modal.metadata_path') || 'Chemin', f.path)}
            ${row(I18N.t('modal.metadata_size') || 'Taille', formatSize(f.size || 0))}
            ${row(I18N.t('modal.metadata_extension') || 'Format', (f.extension || '').replace('.', '').toUpperCase())}
            ${row(I18N.t('modal.metadata_source') || 'Source', f.source)}
            ${row(I18N.t('modal.metadata_added') || 'Ajouté le', f.date_added)}
            ${f.tags?.length ? `<div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:8px;">${f.tags.map(t => `<span class="file-tag" style="background:${t.color}20;color:${t.color};border-color:${t.color}">${escapeHtml(t.name)}</span>`).join('')}</div>` : ''}

            <h4 style="font-size:12px; text-transform:uppercase; color:var(--text-muted); margin:16px 0 4px;" data-i18n="modal.metadata_geometry_section">Géométrie</h4>
            ${metadata ? `
                ${row(I18N.t('modal.metadata_dimensions') || 'Dimensions', dims)}
                ${row(I18N.t('modal.metadata_volume') || 'Volume', metadata.volume_cm3 ? `${metadata.volume_cm3} cm³` : null)}
                ${row(I18N.t('modal.metadata_surface') || 'Surface', metadata.surface_cm2 ? `${metadata.surface_cm2} cm²` : null)}
                ${row(I18N.t('modal.metadata_weight') || 'Poids estimé', weight)}
                ${row(I18N.t('modal.metadata_triangles') || 'Triangles', metadata.triangle_count?.toLocaleString())}
                ${row(I18N.t('modal.metadata_manifold') || 'Maillage', metadata.is_manifold ? (I18N.t('modal.metadata_manifold_ok') || '✅ Sain (watertight)') : (I18N.t('modal.metadata_manifold_ko') || '⚠️ Non-manifold'))}
                ${row(I18N.t('modal.metadata_print_time') || 'Temps estimé', metadata.estimated_time?.formatted)}
            ` : `<p style="color:var(--text-muted); font-size:13px;">${I18N.t('cost.analyze_error') || "Analyse impossible pour ce fichier."}</p>`}

            <h4 style="font-size:12px; text-transform:uppercase; color:var(--text-muted); margin:16px 0 4px; display:flex; justify-content:space-between; align-items:center;">
                <span data-i18n="modal.metadata_ai_description_section">Description IA</span>
                <button class="btn btn-ghost btn-sm" id="ai-describe-btn" onclick="generateFileDescription('${escapeJs(filePath)}')" style="font-size:11px; padding:3px 8px;">
                    <i class="fa-solid fa-wand-magic-sparkles"></i> <span data-i18n="modal.metadata_ai_generate">Générer</span>
                </button>
            </h4>
            <p id="ai-description-text" style="font-size:13px; color:var(--text-secondary); line-height:1.5; font-style:italic;">${I18N.t('common.loading_ellipsis') || 'Chargement...'}</p>
        `;

        try {
            const descRes = await fetch(`${API}/api/file-description?path=${encodeURIComponent(filePath)}`);
            const descData = await descRes.json();
            const descEl = document.getElementById('ai-description-text');
            if (descEl) {
                descEl.textContent = descData.description || (I18N.t('modal.metadata_ai_none') || "Pas encore de description — clique sur \"Générer\".");
            }
        } catch (e) {
            const descEl = document.getElementById('ai-description-text');
            if (descEl) descEl.textContent = '';
        }
    };

    window.generateFileDescription = async function (filePath) {
        const btn = document.getElementById('ai-describe-btn');
        const descEl = document.getElementById('ai-description-text');
        if (btn) { btn.disabled = true; btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`; }
        if (descEl) descEl.textContent = I18N.t('modal.metadata_ai_generating') || 'Génération en cours...';
        try {
            const res = await fetch(`${API}/api/ollama/describe-file`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            });
            const data = await res.json();
            if (!res.ok) {
                if (descEl) descEl.textContent = data.error || (I18N.t('toast.error') || 'Erreur');
                showToast(data.error || I18N.t('toast.error'), 'error');
                return;
            }
            if (descEl) descEl.textContent = data.description;
        } catch (e) {
            if (descEl) descEl.textContent = '';
            showToast(I18N.t('toast.connection_error'), 'error');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> ${I18N.t('modal.metadata_ai_generate') || 'Générer'}`; }
        }
    };

function _applyCostSpoolSelection(spoolId) {
    const sel = document.getElementById('cost-spool-select');
    const priceInput = document.getElementById('cost-spool-price');
    const weightInput = document.getElementById('cost-spool-weight');
    if (!sel || !priceInput || !weightInput) return;
    const opt = [...sel.options].find(o => o.value === spoolId);
    if (!opt) return;
    priceInput.value = opt.dataset.price;
    weightInput.value = opt.dataset.weight;
}
window._applyCostSpoolSelection = _applyCostSpoolSelection;

    window.openPrintCostModal = async function (filePath, fileName) {
        let modal = document.getElementById('modal-print-cost');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'modal-print-cost';
            modal.className = 'modal hidden';
            modal.innerHTML = `<div class="modal-content">
                <div class="modal-header">
                    <h3><i class="fa-solid fa-coins"></i> ${I18N.t('modal.print_cost')}</h3>
                    <button class="modal-close" onclick="closeModal('modal-print-cost')">×</button>
                </div>
                <div class="modal-body" id="cost-modal-body"></div>
            </div>`;
            document.body.appendChild(modal);
            modal.addEventListener('click', (e) => { if (e.target === modal) closeModal('modal-print-cost'); });
        }

        const body = document.getElementById('cost-modal-body');
        body.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-muted)"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><p style="margin-top:10px">${I18N.t('cost.analyzing')}</p></div>`;
        openModal('modal-print-cost');
        _costMetadata = null;
        _costCurrentFilePath = filePath;
        _preciseEstimate = null;
        _preciseEstimateStatus = 'idle';
        _aiTimePrediction = null;
        _ecoEstimate = null;
        clearTimeout(_preciseEstimateTimer);

        let settings = {};
        try {
            const settingsRes = await fetch(`${API}/api/settings`);
            if (settingsRes.ok) settings = await settingsRes.json();
        } catch (e) {  }

        try {
            const res = await fetch(`${API}/api/files/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            });
            const data = await res.json();
            if (!res.ok || !data.metadata) {
                body.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-muted)">
                    <i class="fa-solid fa-triangle-exclamation" style="font-size:28px; color:var(--danger);"></i>
                    <p style="margin-top:10px;">${I18N.t('cost.analyze_error')}</p>
                </div>`;
                return;
            }
            _costMetadata = data.metadata;

            const material = settings.print_cost_material || 'pla';
            const settingsSpools = Array.isArray(settings.print_cost_spools) ? settings.print_cost_spools : [];
            const defaultSpool = settingsSpools.find(s => s.id === settings.print_cost_default_spool_id) || settingsSpools[0] || null;
            const spoolPrice = defaultSpool ? (defaultSpool.price ?? 20) : (settings.print_cost_spool_price ?? 20);
            const spoolWeight = defaultSpool ? (defaultSpool.weight ?? 1000) : (settings.print_cost_spool_weight ?? 1000);
            const elecPrice = settings.print_cost_elec_price ?? '';
            const printerPower = settings.print_cost_printer_power ?? 120;
            const spoolOptions = settingsSpools.length > 0 ? settingsSpools : [{ id: '__legacy', name: I18N.t('cost.spool_default_name') || 'Bobine', price: spoolPrice, weight: spoolWeight }];
            const materials = ['pla', 'petg', 'abs', 'tpu', 'nylon'];
            const fieldStyle = 'width:100%; padding:8px 10px; background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius); color:var(--text-primary);';
            const labelStyle = 'display:block; font-size:12px; color:var(--text-secondary); margin-bottom:4px;';

            body.innerHTML = `
                <p style="font-size:13px; color:var(--text-secondary); margin-bottom:14px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(fileName)}">
                    <i class="fa-solid fa-cube"></i> ${escapeHtml(fileName)}
                </p>
                <div style="display:flex; flex-direction:column; gap:12px;">
                    <div>
                        <label style="${labelStyle}">${I18N.t('cost.material_label')}</label>
                        <select id="cost-material-select" style="${fieldStyle}">
                            ${materials.map(m => `<option value="${m}" ${m === material ? 'selected' : ''}>${m.toUpperCase()}</option>`).join('')}
                        </select>
                    </div>
                    <div>
                        <label style="${labelStyle}">${I18N.t('cost.spool_select_label') || 'Bobine'}</label>
                        <select id="cost-spool-select" style="${fieldStyle}" onchange="_applyCostSpoolSelection(this.value)">
                            ${spoolOptions.map(s => `<option value="${escapeHtml(String(s.id))}" data-price="${s.price}" data-weight="${s.weight}" ${s.id === (defaultSpool?.id) ? 'selected' : ''}>${escapeHtml(s.name || (I18N.t('cost.spool_default_name') || 'Bobine'))}</option>`).join('')}
                        </select>
                    </div>
                    <div style="display:flex; gap:10px;">
                        <div style="flex:1;">
                            <label style="${labelStyle}">${I18N.t('cost.spool_price_label')} (<span class="currency-symbol">${printCostCurrency === 'USD' ? '$' : '€'}</span>)</label>
                            <input type="number" id="cost-spool-price" min="0" step="0.01" value="${spoolPrice}" style="${fieldStyle}">
                        </div>
                        <div style="flex:1;">
                            <label style="${labelStyle}">${I18N.t('cost.spool_weight_label')}</label>
                            <input type="number" id="cost-spool-weight" min="1" step="1" value="${spoolWeight}" style="${fieldStyle}">
                        </div>
                    </div>
                    <div style="display:flex; gap:10px;">
                        <div style="flex:1;">
                            <label style="${labelStyle}">${I18N.t('cost.elec_price_label')} (<span class="currency-symbol">${printCostCurrency === 'USD' ? '$' : '€'}</span>/kWh) <span style="color:var(--text-muted);">${I18N.t('cost.optional_suffix')}</span></label>
                            <input type="number" id="cost-elec-price" min="0" step="0.001" value="${elecPrice}" placeholder="ex: 0.2062" style="${fieldStyle}">
                        </div>
                        <div style="flex:1;">
                            <label style="${labelStyle}">${I18N.t('cost.printer_power_label')}</label>
                            <input type="number" id="cost-printer-power" min="1" step="1" value="${printerPower}" style="${fieldStyle}">
                        </div>
                    </div>
                </div>
                <div id="cost-results"></div>
                <div id="cost-filament-compat"></div>
                <p style="display:flex; align-items:flex-start; gap:8px; font-size:12px; color:var(--text-muted); margin-top:12px; padding-top:12px; border-top:1px solid var(--border);">
                    <i class="fa-solid fa-triangle-exclamation" style="margin-top:1px; color:var(--warning);"></i>
                    <span>${I18N.t('cost.slicer_settings_disclaimer')}</span>
                </p>
            `;

            ['cost-material-select', 'cost-spool-price', 'cost-spool-weight', 'cost-elec-price', 'cost-printer-power'].forEach(id => {
                const el = document.getElementById(id);
                el?.addEventListener('input', () => { _recomputeCost(); _costSaveSettings(); });
                el?.addEventListener('change', () => { _recomputeCost(); _costSaveSettings(); });
            });

            _recomputeCost();
            _startPreciseEstimate(filePath);
            _loadFilamentCompatibility(filePath);
        } catch (err) {
            body.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-muted)">
                <i class="fa-solid fa-triangle-exclamation" style="font-size:28px; color:var(--danger);"></i>
                <p style="margin-top:10px;" data-i18n="toast.connection_error">Erreur de connexion.</p>
            </div>`;
            I18N.apply(body);
        }
    };
})();


let allProjects = [];
let _currentProjectDetailId = null;
let _projectPickerSelected = new Set();

function projectFileThumb(filePath) {
    const f = allFiles.find(x => x.path === filePath);
    if (f && f.has_thumb) {
        return `${API}/api/thumb?path=${encodeURIComponent(filePath)}${f.thumb_mtime ? '&t=' + f.thumb_mtime : ''}`;
    }
    return null;
}

async function loadProjects() {
    const loading = document.getElementById('projects-loading');
    const empty = document.getElementById('projects-empty');
    const grid = document.getElementById('projects-grid');
    loading?.classList.remove('hidden');
    empty?.classList.add('hidden');
    grid?.classList.add('hidden');
    try {
        const res = await fetch(`${API}/api/projects`);
        const data = await res.json();
        allProjects = Array.isArray(data) ? data : [];
        loading?.classList.add('hidden');
        if (allProjects.length === 0) {
            empty?.classList.remove('hidden');
            return;
        }
        grid.innerHTML = allProjects.map(renderProjectCard).join('');
        grid?.classList.remove('hidden');
        I18N.apply();
    } catch (err) {
        loading?.classList.add('hidden');
        showToast(I18N.t('toast.connection_error'), 'error');
        console.error('[Projects] loadProjects', err);
    }
}

function renderProjectCard(p) {
    const thumbs = (p.files || []).map(fp => {
        const url = projectFileThumb(fp);
        return url
            ? `<div class="folder-preview-thumb"><img src="${url}" loading="lazy"></div>`
            : `<div class="folder-preview-thumb"><span class="folder-preview-icon"><i class="fa-solid fa-cube"></i></span></div>`;
    }).join('');
    const progress = p.progress || 0;
    const statusLabel = p.status === 'done' ? I18N.t('projects.status_done') : I18N.t('projects.status_in_progress');
    return `<div class="project-card" onclick="openProjectDetailModal(${p.id})">
        <div class="project-card-thumbs">${thumbs || `<div class="folder-preview-thumb"><span class="folder-preview-icon"><i class="fa-solid fa-diagram-project"></i></span></div>`}</div>
        <div class="project-card-body">
            <div class="project-card-header">
                <span class="project-card-color" style="background:${p.color || '#4ea1d3'}"></span>
                <h4 title="${escapeHtml(p.name)}">${escapeHtml(p.name)}</h4>
                <div class="project-card-actions">
                    <button type="button" class="dv-btn" onclick="event.stopPropagation(); openProjectFormModal(${p.id})" title="${I18N.t('actions.rename')}"><i class="fa-solid fa-pencil"></i></button>
                    <button type="button" class="dv-btn" onclick="event.stopPropagation(); deleteProjectConfirm(${p.id}, '${escapeJs(p.name)}')" title="${I18N.t('modal.delete_file')}" style="color:var(--danger)"><i class="fa-solid fa-trash"></i></button>
                </div>
            </div>
            ${p.description ? `<p class="project-card-desc">${escapeHtml(p.description)}</p>` : ''}
            <div class="project-progress-bar"><div class="project-progress-fill" style="width:${progress}%; background:${p.color || '#4ea1d3'}"></div></div>
            <div class="project-card-meta">
                <span><i class="fa-solid fa-cube"></i> ${p.file_count} ${I18N.t('projects.parts')}</span>
                <span>${p.total_printed}/${p.total_needed} ${I18N.t('projects.printed')}</span>
                <span class="project-status-badge project-status-badge--${p.status}">${statusLabel}</span>
            </div>
        </div>
    </div>`;
}

window.openProjectFormModal = function (projectId = null) {
    let modal = document.getElementById('modal-project-form');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modal-project-form';
        modal.className = 'modal hidden';
        modal.innerHTML = `<div class="modal-content small">
            <div class="modal-header">
                <h3><i class="fa-solid fa-diagram-project"></i> <span id="project-form-title">${I18N.t('projects.new')}</span></h3>
                <button class="modal-close" onclick="closeModal('modal-project-form')">×</button>
            </div>
            <div class="modal-body">
                <div class="input-group">
                    <label>${I18N.t('projects.name_label')}</label>
                    <input type="text" id="project-form-name" placeholder="${I18N.t('projects.name_placeholder')}">
                </div>
                <div class="input-group">
                    <label>${I18N.t('projects.description_label')}</label>
                    <textarea id="project-form-description" rows="2" placeholder="${I18N.t('projects.description_placeholder')}"></textarea>
                </div>
                <div class="input-group">
                    <label>${I18N.t('projects.color_label')}</label>
                    <input type="color" id="project-form-color" value="#4ea1d3" style="width:60px; height:32px; padding:2px; border:1px solid var(--border); border-radius:var(--radius); background:var(--bg-card);">
                </div>
                <button class="btn btn-primary" style="width:100%; margin-top:10px;" onclick="saveProjectForm()">
                    <i class="fa-solid fa-check"></i> <span id="project-form-submit-label">${I18N.t('actions.save')}</span>
                </button>
            </div>
        </div>`;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => { if (e.target === modal) closeModal('modal-project-form'); });
    }
    const p = projectId ? allProjects.find(x => x.id === projectId) : null;
    document.getElementById('project-form-title').textContent = p ? I18N.t('projects.edit') : I18N.t('projects.new');
    document.getElementById('project-form-name').value = p?.name || '';
    document.getElementById('project-form-description').value = p?.description || '';
    document.getElementById('project-form-color').value = p?.color || '#4ea1d3';
    modal.dataset.editId = projectId || '';
    delete modal.dataset.attachSelection;
    openModal('modal-project-form');
    setTimeout(() => document.getElementById('project-form-name')?.focus(), 100);
};

window.saveProjectForm = async function () {
    const modal = document.getElementById('modal-project-form');
    const name = document.getElementById('project-form-name')?.value?.trim();
    const description = document.getElementById('project-form-description')?.value?.trim() || '';
    const color = document.getElementById('project-form-color')?.value || '#4ea1d3';
    if (!name) { showToast(I18N.t('projects.name_required'), 'warning'); return; }
    const editId = modal?.dataset.editId;
    const attachSelection = !editId && modal?.dataset.attachSelection === '1';
    const payload = { name, description, color };
    if (attachSelection) payload.files = [...selectedFiles].map(path => ({ path, quantity: 1 }));
    try {
        const url = editId ? `${API}/api/projects/${editId}` : `${API}/api/projects`;
        const method = editId ? 'PUT' : 'POST';
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || I18N.t('toast.error'), 'error'); return; }
        showToast(editId ? I18N.t('toast.updated') : I18N.t('projects.created'), 'success');
        closeModal('modal-project-form');
        delete modal.dataset.attachSelection;
        if (attachSelection) {
            selectedFiles.clear();
            toggleSelectionMode();
        }
        await loadProjects();
        if (editId && _currentProjectDetailId === parseInt(editId)) openProjectDetailModal(parseInt(editId));
    } catch (err) {
        showToast(I18N.t('toast.connection_error'), 'error');
        console.error('[Projects] saveProjectForm', err);
    }
};

window.deleteProjectConfirm = async function (projectId, name) {
    const ok = await showConfirmDialog(
        `${I18N.t('projects.delete_confirm')} "${name}" ?`,
        { title: I18N.t('actions.delete') || 'Supprimer', confirmLabel: I18N.t('actions.delete') || 'Supprimer', danger: true }
    );
    if (!ok) return;
    try {
        const res = await fetch(`${API}/api/projects/${projectId}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || I18N.t('toast.error'), 'error'); return; }
        showToast(I18N.t('projects.deleted'), 'success');
        closeModal('modal-project-detail');
        await loadProjects();
    } catch (err) {
        showToast(I18N.t('toast.connection_error'), 'error');
        console.error('[Projects] deleteProjectConfirm', err);
    }
};

window.openProjectDetailModal = async function (projectId) {
    _currentProjectDetailId = projectId;
    let modal = document.getElementById('modal-project-detail');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modal-project-detail';
        modal.className = 'modal hidden';
        modal.innerHTML = `<div class="modal-content" style="max-width:640px;">
            <div class="modal-header">
                <h3><i class="fa-solid fa-diagram-project"></i> <span id="project-detail-name"></span></h3>
                <button class="modal-close" onclick="closeModal('modal-project-detail')">×</button>
            </div>
            <div class="modal-body" id="project-detail-body"></div>
        </div>`;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => { if (e.target === modal) closeModal('modal-project-detail'); });
    }
    const body = document.getElementById('project-detail-body');
    body.innerHTML = `<div style="text-align:center; padding:30px;"><i class="fa-solid fa-spinner fa-spin fa-2x" style="color:var(--accent);"></i></div>`;
    openModal('modal-project-detail');
    await refreshProjectDetail(projectId);
};

async function refreshProjectDetail(projectId) {
    const body = document.getElementById('project-detail-body');
    try {
        const res = await fetch(`${API}/api/projects/${projectId}`);
        const p = await res.json();
        if (!res.ok) { body.innerHTML = `<p style="color:var(--danger)">${p.error || I18N.t('toast.error')}</p>`; return; }
        document.getElementById('project-detail-name').textContent = p.name;

        const totalNeeded = p.files.reduce((s, f) => s + f.quantity_needed, 0);
        const totalPrinted = p.files.reduce((s, f) => s + Math.min(f.quantity_printed, f.quantity_needed), 0);
        const progress = totalNeeded > 0 ? Math.round((totalPrinted / totalNeeded) * 100) : 0;

        const rows = p.files.map(f => {
            const file = allFiles.find(x => x.path === f.file_path);
            const thumbUrl = projectFileThumb(f.file_path);
            const isDone = f.quantity_printed >= f.quantity_needed;
            const safeId = f.file_path.replace(/[^\w]/g, '-');
            return `<div class="project-file-row${isDone ? ' project-file-row--done' : ''}" data-path="${escapeHtml(f.file_path)}">
                <div class="project-file-thumb">${thumbUrl ? `<img src="${thumbUrl}">` : `<i class="fa-solid fa-cube"></i>`}</div>
                <div class="project-file-info">
                    <span class="project-file-name" title="${escapeHtml(f.file_path)}">${escapeHtml(file?.name || f.file_path.split(/[\\/]/).pop())}</span>
                    ${!file ? `<span class="project-file-missing">${I18N.t('projects.file_missing')}</span>` : ''}
                </div>
                <div class="project-file-qty">
                    <button type="button" class="qty-btn" onclick="updateProjectFileQty(${projectId}, '${escapeJs(f.file_path)}', -1)">−</button>
                    <span>${f.quantity_printed}/${f.quantity_needed}</span>
                    <button type="button" class="qty-btn" onclick="updateProjectFileQty(${projectId}, '${escapeJs(f.file_path)}', 1)">+</button>
                </div>
                <button type="button" class="dv-btn" title="${I18N.t('actions.delete')}" style="color:var(--danger)" onclick="removeProjectFile(${projectId}, '${escapeJs(f.file_path)}')"><i class="fa-solid fa-xmark"></i></button>
            </div>`;
        }).join('');

        body.innerHTML = `
            <div class="project-progress-bar" style="margin-bottom:14px;"><div class="project-progress-fill" style="width:${progress}%; background:${p.color}"></div></div>
            <p style="font-size:12px; color:var(--text-muted); margin-bottom:14px;">${totalPrinted}/${totalNeeded} ${I18N.t('projects.pieces_printed')} · ${p.files.length} ${I18N.t('projects.parts')}</p>
            <div class="project-file-list">${rows || `<p style="color:var(--text-muted); font-size:13px;">${I18N.t('projects.no_files_yet')}</p>`}</div>
            <button class="btn btn-ghost" style="width:100%; margin-top:14px;" onclick="openProjectFilePicker(${projectId})">
                <i class="fa-solid fa-plus"></i> ${I18N.t('projects.add_files')}
            </button>
        `;
        I18N.apply();
    } catch (err) {
        body.innerHTML = `<p style="color:var(--danger)">${I18N.t('toast.connection_error')}</p>`;
        console.error('[Projects] refreshProjectDetail', err);
    }
}

window.updateProjectFileQty = async function (projectId, filePath, delta) {
    const p = await fetch(`${API}/api/projects/${projectId}`).then(r => r.json()).catch(() => null);
    if (!p) return;
    const f = p.files.find(x => x.file_path === filePath);
    if (!f) return;
    let newPrinted = f.quantity_printed + delta;
    newPrinted = Math.max(0, Math.min(newPrinted, f.quantity_needed));
    try {
        await fetch(`${API}/api/projects/${projectId}/files`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: filePath, quantity_printed: newPrinted })
        });
        await refreshProjectDetail(projectId);
        loadProjects();
    } catch (err) {
        showToast(I18N.t('toast.connection_error'), 'error');
    }
};

window.removeProjectFile = async function (projectId, filePath) {
    try {
        await fetch(`${API}/api/projects/${projectId}/files`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: filePath })
        });
        await refreshProjectDetail(projectId);
        loadProjects();
    } catch (err) {
        showToast(I18N.t('toast.connection_error'), 'error');
    }
};

window.openProjectFilePicker = function (projectId) {
    closeModal('modal-project-detail');
    openAddToProjectModal(null, null, projectId);
};

window.openAddToProjectModal = async function (filePath, fileName, forceProjectId = null) {
    let modal = document.getElementById('modal-add-to-project');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modal-add-to-project';
        modal.className = 'modal hidden';
        modal.innerHTML = `<div class="modal-content small">
            <div class="modal-header">
                <h3><i class="fa-solid fa-diagram-project"></i> <span id="add-to-project-title">${I18N.t('projects.add_to_project')}</span></h3>
                <button class="modal-close" onclick="closeModal('modal-add-to-project')">×</button>
            </div>
            <div class="modal-body" id="add-to-project-body"></div>
        </div>`;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => { if (e.target === modal) closeModal('modal-add-to-project'); });
    }
    const body = document.getElementById('add-to-project-body');
    _projectPickerSelected = new Set();

    if (forceProjectId) {
        document.getElementById('add-to-project-title').textContent = I18N.t('projects.add_files');
        const notInProject = allFiles.filter(f => f.path);
        body.innerHTML = `
            <input type="text" id="project-picker-search" placeholder="${I18N.t('library.search_placeholder') || 'Rechercher...'}" style="width:100%; margin-bottom:10px; padding:8px 10px; background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius); color:var(--text-primary);">
            <div id="project-picker-file-list" style="max-height:320px; overflow-y:auto;"></div>
            <button class="btn btn-primary" style="width:100%; margin-top:10px;" onclick="confirmAddFilesToProject(${forceProjectId})">
                <i class="fa-solid fa-check"></i> ${I18N.t('actions.add')}
            </button>
        `;
        const renderList = (filter = '') => {
            const list = document.getElementById('project-picker-file-list');
            const filtered = notInProject.filter(f => f.name.toLowerCase().includes(filter.toLowerCase()));
            list.innerHTML = filtered.slice(0, 200).map(f => `
                <label class="checkbox-label" style="display:flex; align-items:center; gap:8px; padding:6px 4px; border-bottom:1px solid var(--border);">
                    <input type="checkbox" value="${escapeHtml(f.path)}" class="project-picker-checkbox">
                    <span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(f.name)}</span>
                </label>`).join('') || `<p style="color:var(--text-muted); font-size:13px; padding:10px;">${I18N.t('library.no_files')}</p>`;
        };
        renderList();
        document.getElementById('project-picker-search')?.addEventListener('input', (e) => renderList(e.target.value));
        openModal('modal-add-to-project');
        return;
    }

    document.getElementById('add-to-project-title').textContent = fileName || I18N.t('projects.add_to_project');
    await loadProjects();
    const listHtml = allProjects.length
        ? allProjects.map(p => `
            <label class="checkbox-label" style="display:flex; align-items:center; gap:10px; padding:8px 4px; border-bottom:1px solid var(--border);">
                <input type="checkbox" value="${p.id}" class="project-picker-project-checkbox">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color};"></span>
                <span style="flex:1;">${escapeHtml(p.name)}</span>
                <span style="color:var(--text-muted); font-size:12px;">${p.file_count} ${I18N.t('projects.parts')}</span>
            </label>`).join('')
        : `<p style="color:var(--text-muted); font-size:13px; padding:10px 0;">${I18N.t('projects.no_projects_yet')}</p>`;
    body.innerHTML = `
        <p style="font-size:12px; color:var(--text-muted); margin-bottom:10px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(fileName || '')}</p>
        <div style="max-height:260px; overflow-y:auto; margin-bottom:12px;">${listHtml}</div>
        <button class="btn btn-primary" style="width:100%;" onclick="confirmAddFileToProjects('${escapeJs(filePath)}')">
            <i class="fa-solid fa-check"></i> ${I18N.t('actions.add')}
        </button>
        <button class="btn btn-ghost" style="width:100%; margin-top:8px;" onclick="closeModal('modal-add-to-project'); openProjectFormModal();">
            <i class="fa-solid fa-plus"></i> ${I18N.t('projects.new')}
        </button>
    `;
    openModal('modal-add-to-project');
};

window.confirmAddFileToProjects = async function (filePath) {
    const checked = [...document.querySelectorAll('.project-picker-project-checkbox:checked')].map(el => parseInt(el.value));
    if (checked.length === 0) { showToast(I18N.t('projects.select_at_least_one'), 'warning'); return; }
    try {
        await Promise.all(checked.map(projectId =>
            fetch(`${API}/api/projects/${projectId}/files`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ files: [{ path: filePath, quantity: 1 }] })
            })
        ));
        showToast(I18N.t('projects.added_to_project'), 'success');
        closeModal('modal-add-to-project');
        loadProjects();
    } catch (err) {
        showToast(I18N.t('toast.connection_error'), 'error');
        console.error('[Projects] confirmAddFileToProjects', err);
    }
};

window.confirmAddFilesToProject = async function (projectId) {
    const checked = [...document.querySelectorAll('.project-picker-checkbox:checked')].map(el => ({ path: el.value, quantity: 1 }));
    if (checked.length === 0) { showToast(I18N.t('projects.select_at_least_one'), 'warning'); return; }
    try {
        await fetch(`${API}/api/projects/${projectId}/files`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files: checked })
        });
        showToast(I18N.t('projects.added_to_project'), 'success');
        closeModal('modal-add-to-project');
        openProjectDetailModal(projectId);
    } catch (err) {
        showToast(I18N.t('toast.connection_error'), 'error');
        console.error('[Projects] confirmAddFilesToProject', err);
    }
};


window.openSelectionProjectModal = function () {
    if (selectedFiles.size === 0) {
        showToast(I18N.t('toast.no_selection'), 'warning');
        return;
    }
    let modal = document.getElementById('modal-selection-project');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modal-selection-project';
        modal.className = 'modal hidden';
        modal.innerHTML = `<div class="modal-content small">
            <div class="modal-header">
                <h3><i class="fa-solid fa-diagram-project"></i> <span id="selection-project-title">${I18N.t('projects.add_to_project')}</span></h3>
                <button class="modal-close" onclick="closeModal('modal-selection-project')">×</button>
            </div>
            <div class="modal-body" id="selection-project-body"></div>
        </div>`;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => { if (e.target === modal) closeModal('modal-selection-project'); });
    }
    const count = selectedFiles.size;
    document.getElementById('selection-project-title').textContent = I18N.tp('common.file_count', count, { count });
    document.getElementById('selection-project-body').innerHTML = `
        <button class="btn btn-primary" style="width:100%; margin-bottom:10px; justify-content:flex-start; gap:10px;" onclick="selectionOpenNewProject()">
            <i class="fa-solid fa-plus"></i> ${I18N.t('projects.create_with_selection') || 'Créer un nouveau projet avec ces fichiers'}
        </button>
        <button class="btn btn-sm" style="width:100%; justify-content:flex-start; gap:10px;" onclick="selectionOpenExistingProjectList()">
            <i class="fa-solid fa-list"></i> ${I18N.t('projects.send_to_existing') || 'Envoyer vers un projet existant'}
        </button>
    `;
    openModal('modal-selection-project');
};

window.selectionOpenNewProject = function () {
    closeModal('modal-selection-project');
    openProjectFormModal();
    const formModal = document.getElementById('modal-project-form');
    if (formModal) formModal.dataset.attachSelection = '1';
};

window.selectionOpenExistingProjectList = async function () {
    const body = document.getElementById('selection-project-body');
    body.innerHTML = `<p style="color:var(--text-muted); font-size:13px; padding:10px 0;">${I18N.t('common.loading') || 'Chargement...'}</p>`;
    await loadProjects();
    const listHtml = allProjects.length
        ? allProjects.map(p => `
            <label class="checkbox-label" style="display:flex; align-items:center; gap:10px; padding:8px 4px; border-bottom:1px solid var(--border);">
                <input type="checkbox" value="${p.id}" class="selection-project-checkbox">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color};"></span>
                <span style="flex:1;">${escapeHtml(p.name)}</span>
                <span style="color:var(--text-muted); font-size:12px;">${p.file_count} ${I18N.t('projects.parts')}</span>
            </label>`).join('')
        : `<p style="color:var(--text-muted); font-size:13px; padding:10px 0;">${I18N.t('projects.no_projects_yet')}</p>`;
    body.innerHTML = `
        <div style="max-height:260px; overflow-y:auto; margin-bottom:12px;">${listHtml}</div>
        <button class="btn btn-primary" style="width:100%;" onclick="confirmSendSelectionToProjects()">
            <i class="fa-solid fa-check"></i> ${I18N.t('actions.add')}
        </button>
        <button class="btn btn-ghost" style="width:100%; margin-top:8px;" onclick="selectionOpenNewProject()">
            <i class="fa-solid fa-plus"></i> ${I18N.t('projects.new')}
        </button>
    `;
};

window.confirmSendSelectionToProjects = async function () {
    const checked = [...document.querySelectorAll('.selection-project-checkbox:checked')].map(el => parseInt(el.value));
    if (checked.length === 0) { showToast(I18N.t('projects.select_at_least_one'), 'warning'); return; }
    const files = [...selectedFiles].map(path => ({ path, quantity: 1 }));
    try {
        await Promise.all(checked.map(projectId =>
            fetch(`${API}/api/projects/${projectId}/files`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ files })
            })
        ));
        showToast(I18N.t('projects.added_to_project'), 'success');
        closeModal('modal-selection-project');
        selectedFiles.clear();
        toggleSelectionMode();
        loadProjects();
    } catch (err) {
        showToast(I18N.t('toast.connection_error'), 'error');
        console.error('[Projects] confirmSendSelectionToProjects', err);
    }
};
window.openQRModal = async function () {
    openModal('modal-qrcode');
    document.getElementById('qr-loading').classList.remove('hidden');
    document.getElementById('qr-content').classList.add('hidden');
    document.getElementById('qr-error').classList.add('hidden');
    try {
        const res = await fetch(`${API}/api/qrcode`);
        const data = await res.json();
        if (!res.ok || !data.qr_image) throw new Error(data.error || 'Erreur serveur');
        document.getElementById('qr-image').src = 'data:image/png;base64,' + data.qr_image;
        document.getElementById('qr-url-display').textContent = data.url;
        document.getElementById('qr-loading').classList.add('hidden');
        document.getElementById('qr-content').classList.remove('hidden');
    } catch (e) {
        document.getElementById('qr-loading').classList.add('hidden');
        document.getElementById('qr-error-msg').textContent = e.message || I18N.t('qr.error');
        document.getElementById('qr-error').classList.remove('hidden');
    }
};


window.toggleRemoteAccessEnabled = async function (enabled) {
    const container = document.getElementById('remote-access-content');
    if (container) {
        container.innerHTML = `<p class="settings-hint"><i class="fa-solid fa-spinner fa-spin"></i> <span data-i18n="settings.remote_starting">Initialisation de l'accès distant…</span></p>`;
    }
    try {
        const res = await fetch(`${API}/api/remote-access/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });
        if (res.ok) {
            showToast(enabled ? (I18N.t('toast.remote_access_enabled') || 'Accès à distance activé') : (I18N.t('toast.remote_access_disabled') || 'Accès à distance désactivé'), 'success');
            if (enabled) setTimeout(loadRemoteAccess, 2000);
            else loadRemoteAccess();
        } else {
            showToast(I18N.t('toast.save_error') || 'Erreur', 'error');
        }
    } catch (e) {
        showToast(I18N.t('toast.network_error') || 'Erreur de connexion', 'error');
    }
};

window.loadRemoteAccess = async function () {
    const container = document.getElementById('remote-access-content');
    const toggle = document.getElementById('remote-access-enabled-toggle');
    if (!container) return;
    try {
        const res = await fetch(`${API}/api/remote-access`);
        const data = await res.json();

        if (toggle) toggle.checked = !!data.enabled;

        if (!data.enabled) {
            container.innerHTML = `<p class="settings-hint" data-i18n="settings.remote_access_disabled_hint">Activez l'accès à distance ci-dessus pour générer une adresse publique.</p>`;
            return;
        }

        if (data.status === 'ready' && data.url) {
            const isFixed = data.mode === 'fixed';
            const badge = isFixed
                ? `<span style="background:var(--success)20;color:var(--success);padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;"><i class="fa-solid fa-lock"></i> <span data-i18n="settings.remote_mode_fixed">URL fixe</span></span>`
                : `<span style="background:var(--accent)20;color:var(--accent);padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;"><i class="fa-solid fa-shuffle"></i> <span data-i18n="settings.remote_mode_quick">URL aléatoire</span></span>`;

            const warning = isFixed
                ? `<p class="settings-hint" style="margin-top:12px;font-size:12px;text-align:left;color:var(--text-muted);">
                       <i class="fa-solid fa-circle-info"></i> <span data-i18n="settings.remote_fixed_notice">Cette adresse reste la même à chaque redémarrage (configurée via votre compte Cloudflare).</span>
                   </p>`
                : `<div style="background:var(--danger)15;border:1px solid var(--danger)30;border-radius:8px;padding:10px 12px;margin-top:12px;text-align:left;">
                       <p class="settings-hint" style="font-size:12px;margin:0;color:var(--text-secondary);">
                           <i class="fa-solid fa-triangle-exclamation" style="color:var(--danger);"></i>
                           <span data-i18n="settings.remote_dynamic_warning"><strong>Cette adresse changera au prochain redémarrage de Stellio.</strong> Pensez à consulter à nouveau cette page pour récupérer la nouvelle adresse, ou configurez une URL fixe ci-dessous.</span>
                       </p>
                   </div>`;

            container.innerHTML = `
                <p class="settings-hint" style="color:var(--success);margin-bottom:10px;display:flex;align-items:center;justify-content:center;gap:8px;">
                    <i class="fa-solid fa-circle-check"></i> <span data-i18n="settings.remote_active">Accès distant actif</span> ${badge}
                </p>
                <div style="display:flex;gap:8px;margin-bottom:10px;">
                    <input type="text" readonly value="${data.url}" class="settings-select" id="remote-url-input" style="flex:1;">
                    <button class="btn btn-ghost remote-copy-btn" onclick="copyRemoteUrl()" data-i18n-title="actions.copy" title="${I18N.t('actions.copy') || 'Copier'}">
                        <i class="fa-solid fa-copy"></i>
                    </button>
                </div>
                <button class="btn btn-primary" onclick="openRemoteQRModal()" style="width:100%;">
                    <i class="fa-solid fa-qrcode"></i> <span data-i18n="settings.remote_qr">Générer le QR code distant</span>
                </button>
                ${warning}
            `;
        } else if (data.status === 'error') {
            container.innerHTML = `
                <p class="settings-hint" style="color:var(--danger);">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <span data-i18n="settings.remote_error">Accès distant indisponible</span>${data.error ? ' (' + data.error + ')' : ''}
                </p>
                <button class="btn btn-ghost" onclick="loadRemoteAccess()" style="margin-top:8px;">
                    <i class="fa-solid fa-rotate-right"></i> <span data-i18n="actions.retry">Réessayer</span>
                </button>
            `;
        } else {
            container.innerHTML = `<p class="settings-hint"><i class="fa-solid fa-spinner fa-spin"></i> <span data-i18n="settings.remote_starting">Initialisation de l'accès distant…</span></p>`;
            setTimeout(loadRemoteAccess, 3000);
        }
    } catch (e) {
        container.innerHTML = `<p class="settings-hint" data-i18n="settings.remote_load_error">Erreur de chargement.</p>`;
    }
};

window.saveFixedRemoteAccess = async function () {
    const token = document.getElementById('cf-tunnel-token').value.trim();
    const url = document.getElementById('cf-fixed-url').value.trim();
    const statusEl = document.getElementById('cf-fixed-url-status');

    if (!token || !url) {
        statusEl.textContent = I18N.t('settings.fixed_url_missing_fields') || 'Le token et l\'URL sont requis.';
        statusEl.style.color = 'var(--danger)';
        return;
    }

    statusEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ' + (I18N.t('settings.remote_starting') || 'Connexion en cours…');
    statusEl.style.color = 'var(--text-muted)';

    try {
        const res = await fetch(`${API}/api/remote-access/configure`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, url })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Erreur serveur');

        statusEl.textContent = data.message;
        statusEl.style.color = 'var(--success)';
        setTimeout(loadRemoteAccess, 3000);
    } catch (e) {
        statusEl.textContent = e.message;
        statusEl.style.color = 'var(--danger)';
    }
};

window.disableFixedRemoteAccess = async function () {
    const statusEl = document.getElementById('cf-fixed-url-status');
    statusEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ' + (I18N.t('settings.remote_starting') || 'Reconnexion en cours…');
    statusEl.style.color = 'var(--text-muted)';

    try {
        const res = await fetch(`${API}/api/remote-access/disable-fixed`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Erreur serveur');

        document.getElementById('cf-tunnel-token').value = '';
        document.getElementById('cf-fixed-url').value = '';
        statusEl.textContent = data.message;
        statusEl.style.color = 'var(--success)';
        setTimeout(loadRemoteAccess, 3000);
    } catch (e) {
        statusEl.textContent = e.message;
        statusEl.style.color = 'var(--danger)';
    }
};

window.copyRemoteUrl = function () {
    const input = document.getElementById('remote-url-input');
    if (!input) return;
    input.select();
    input.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(input.value).then(() => {
        if (typeof showToast === 'function') showToast(I18N.t('settings.remote_copied') || 'Adresse copiée', 'success');
    }).catch(() => {});
};

window.openRemoteQRModal = async function () {
    openModal('modal-qrcode-remote');
    document.getElementById('qr-remote-loading').classList.remove('hidden');
    document.getElementById('qr-remote-content').classList.add('hidden');
    document.getElementById('qr-remote-error').classList.add('hidden');
    try {
        const res = await fetch(`${API}/api/qrcode?source=remote`);
        const data = await res.json();
        if (!res.ok || !data.qr_image) throw new Error(data.error || 'Erreur serveur');
        document.getElementById('qr-remote-image').src = 'data:image/png;base64,' + data.qr_image;
        document.getElementById('qr-remote-url-display').textContent = data.url;
        document.getElementById('qr-remote-loading').classList.add('hidden');
        document.getElementById('qr-remote-content').classList.remove('hidden');
    } catch (e) {
        document.getElementById('qr-remote-loading').classList.add('hidden');
        document.getElementById('qr-remote-error-msg').textContent = e.message || I18N.t('qr.error');
        document.getElementById('qr-remote-error').classList.remove('hidden');
    }
};