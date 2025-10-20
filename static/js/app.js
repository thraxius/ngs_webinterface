/**
 * NGS Analysis Interface - Main Application
 * Separated JavaScript for better maintainability
 */

// ============================================================================
// CONSTANTS AND CONFIGURATION
// ============================================================================

const CONFIG = {
  ANALYSIS_TYPES: {
    wgs: {
      basePath: '/bacteria',
      name: 'Bakterien-WGS',
      icon: 'fas fa-bacteria'
    },
    species: {
      basePath: '/animalSpecies',
      name: 'Tierartendifferenzierung',
      icon: 'fas fa-paw'
    }
  },
  
  STATUS_CONFIG: {
    running: { 
      class: 'status-running', 
      text: 'Läuft', 
      icon: 'fas fa-spinner fa-spin' 
    },
    finished: { 
      class: 'status-finished', 
      text: 'Fertig', 
      icon: 'fas fa-check' 
    },
    failed: { 
      class: 'status-failed', 
      text: 'Fehler', 
      icon: 'fas fa-times' 
    },
    queued: { 
      class: 'status-queued', 
      text: 'Wartend', 
      icon: 'fas fa-clock' 
    }
  },
  
  SOURCE_ICONS: {
    'Lebensmittel': '<i class="fas fa-burger text-transparent"></i>',
    'Humanmedizinisch': '<i class="fas fa-user-md text-transparent"></i>',
    'Veterinärmedizinisch': '<i class="fas fa-paw text-transparent"></i>',
    'Umgebung': '<i class="fas fa-globe text-transparent"></i>',
    'Referenz': '<i class="fas fa-chart-bar text-transparent"></i>',
    'Tierart': '<i class="fas fa-paw text-transparent"></i>',
    'Negativkontrolle': '<i class="fas fa-times-circle text-danger"></i>',
    'Positivkontrolle': '<i class="fas fa-check-circle text-success"></i>'
  },
  
  LOG_UPDATE_INTERVAL: 2000,
  STATUS_CHECK_INTERVAL: 3000,
  TOAST_DURATION: 5000,
  DOUBLE_CLICK_TIMEOUT: 300
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

const Utils = {
  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },

  /**
   * Create DOM element from HTML string
   */
  createElementFromHTML(htmlString) {
    const template = document.createElement('template');
    template.innerHTML = htmlString.trim();
    return template.content.firstChild;
  },

  /**
   * Show toast notification
   */
  showToast(message, type = 'info') {
    const toast = Utils.createElementFromHTML(`
      <div class="alert alert-${type} alert-dismissible fade show position-fixed" 
           style="top: 20px; right: 20px; z-index: 9999; min-width: 300px;">
        ${Utils.escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
    `);
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
      if (toast.parentNode) {
        toast.remove();
      }
    }, CONFIG.TOAST_DURATION);
  },

  /**
   * Confirm dialog wrapper
   */
  confirm(message) {
    return window.confirm(message);
  },

  /**
   * Fetch with error handling
   */
  async fetchJSON(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    return response.json();
  }
};

// ============================================================================
// MAIN APPLICATION CLASS
// ============================================================================

class NGSInterface {
  constructor() {
    this.state = {
      selectedRunFolder: null,
      runFolderModalSelected: null,
      selectedAnalysisType: null,
      intervals: []
    };
    
    this.elements = {};
    this.modalInstances = {};
    
    this.init();
  }

  // --------------------------------------------------------------------------
  // INITIALIZATION
  // --------------------------------------------------------------------------

  init() {
    document.addEventListener('DOMContentLoaded', () => {
      this.cacheElements();
      this.setupEventListeners();
      this.setupModals();
      this.setupFlashMessages();
      this.initializeRunningJob();
    });
  }

  cacheElements() {
    const elementIds = [
      'analysisForm',
      'selectedRunFolderInput',
      'analysisTypeInput',
      'runFolderSection',
      'selectedRunFolder',
      'sampleSection',
      'sampleTable',
      'runFolderModal',
      'runFolderList',
      'runCurrentPath',
      'folderLoading',
      'historyTableBody',
      'historyLoading',
      'usersTableBody',
      'usersLoading',
      'logOutput',
      'progressBar',
      'analysisBanner',
      'logContent',
      'logFileSelect'
    ];

    elementIds.forEach(id => {
      this.elements[id] = document.getElementById(id);
    });
  }

  setupEventListeners() {
    // Analysis type cards
    document.querySelectorAll('.analysis-type-card').forEach(card => {
      card.addEventListener('click', () => {
        this.selectAnalysisType(card.dataset.type);
      });
    });

    // Run folder button
    const openRunFolderBtn = document.getElementById('openRunFolderBtn');
    if (openRunFolderBtn) {
      openRunFolderBtn.addEventListener('click', () => this.openRunFolderBrowser());
    }

    // Confirm run folder button
    const confirmRunFolderBtn = document.getElementById('confirmRunFolderBtn');
    if (confirmRunFolderBtn) {
      confirmRunFolderBtn.addEventListener('click', () => this.confirmRunFolder());
    }

    // Analysis form submit
    if (this.elements.analysisForm) {
      this.elements.analysisForm.addEventListener('submit', (e) => {
        if (!this.validateAnalysisForm()) {
          e.preventDefault();
        }
      });
    }

    // History tab
    const historyTab = document.getElementById('history-tab');
    if (historyTab) {
      historyTab.addEventListener('shown.bs.tab', () => this.loadAnalysisHistory());
    }

    // Refresh history button
    const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');
    if (refreshHistoryBtn) {
      refreshHistoryBtn.addEventListener('click', () => this.loadAnalysisHistory());
    }

    // Users tab
    const usersTab = document.getElementById('users-tab');
    if (usersTab) {
      usersTab.addEventListener('shown.bs.tab', () => this.loadUsers());
    }

    // Refresh users button
    const refreshUsersBtn = document.getElementById('refreshUsersBtn');
    if (refreshUsersBtn) {
      refreshUsersBtn.addEventListener('click', () => this.loadUsers());
    }

    // Create user button
    const createUserBtn = document.getElementById('createUserBtn');
    if (createUserBtn) {
      createUserBtn.addEventListener('click', () => this.openCreateUserModal());
    }

    // Save new user button
    const saveNewUserBtn = document.getElementById('saveNewUserBtn');
    if (saveNewUserBtn) {
      saveNewUserBtn.addEventListener('click', () => this.createUser());
    }

    // Save edit user button
    const saveEditUserBtn = document.getElementById('saveEditUserBtn');
    if (saveEditUserBtn) {
      saveEditUserBtn.addEventListener('click', () => this.updateUser());
    }

    // Save password button
    const savePasswordBtn = document.getElementById('savePasswordBtn');
    if (savePasswordBtn) {
      savePasswordBtn.addEventListener('click', () => this.changePassword());
    }

    // Refresh logs button
    const refreshLogsBtn = document.getElementById('refreshLogsBtn');
    if (refreshLogsBtn) {
      refreshLogsBtn.addEventListener('click', () => this.refreshLogs());
    }

    // Log file select
    if (this.elements.logFileSelect) {
      this.elements.logFileSelect.addEventListener('change', (e) => {
        this.switchLogFile(e.target.value);
      });
    }

    // Confirm buttons with data-confirm attribute
    document.querySelectorAll('[data-confirm]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        if (!Utils.confirm(btn.dataset.confirm)) {
          e.preventDefault();
        }
      });
    });
  }

  setupModals() {
    const modalIds = ['runFolderModal', 'createUserModal', 'editUserModal', 'changePasswordModal'];
    
    modalIds.forEach(id => {
      const element = document.getElementById(id);
      if (element) {
        this.modalInstances[id] = new bootstrap.Modal(element);
      }
    });
  }

  setupFlashMessages() {
    document.querySelectorAll('.flash').forEach(flash => {
      setTimeout(() => {
        flash.style.transition = 'opacity 0.5s ease-out';
        flash.style.opacity = '0';
        setTimeout(() => flash.remove(), 500);
      }, CONFIG.TOAST_DURATION);
    });
  }

  initializeRunningJob() {
    const appConfig = document.getElementById('app-config');
    if (appConfig) {
      try {
        const config = JSON.parse(appConfig.textContent);
        if (config.runningJobId) {
          this.initLiveLog(config.runningJobId);
        }
      } catch (error) {
        console.error('Error parsing app config:', error);
      }
    }
  }

  // --------------------------------------------------------------------------
  // ANALYSIS TYPE SELECTION
  // --------------------------------------------------------------------------

  selectAnalysisType(type) {
    if (!CONFIG.ANALYSIS_TYPES[type]) {
      Utils.showToast('Ungültiger Analyse-Typ', 'danger');
      return;
    }

    // Remove previous selection
    document.querySelectorAll('.analysis-type-card').forEach(card => {
      card.classList.remove('selected');
    });
    
    // Add selection to clicked card
    const selectedCard = document.querySelector(`[data-type="${type}"]`);
    if (selectedCard) {
      selectedCard.classList.add('selected');
    }
    
    // Store selection
    this.state.selectedAnalysisType = type;
    if (this.elements.analysisTypeInput) {
      this.elements.analysisTypeInput.value = type;
    }
    
    // Show run folder section with animation
    if (this.elements.runFolderSection) {
      this.elements.runFolderSection.classList.add('visible');
    }
    
    // Reset run folder selection
    this.resetRunFolderSelection();
    
    Utils.showToast(`${CONFIG.ANALYSIS_TYPES[type].name} ausgewählt`, 'success');
  }

  resetRunFolderSelection() {
    this.state.selectedRunFolder = null;
    this.state.runFolderModalSelected = null;
    
    if (this.elements.selectedRunFolder) {
      this.elements.selectedRunFolder.style.display = 'none';
    }
    
    if (this.elements.selectedRunFolderInput) {
      this.elements.selectedRunFolderInput.value = '';
    }
    
    if (this.elements.sampleSection) {
      this.elements.sampleSection.style.display = 'none';
    }
  }

  // --------------------------------------------------------------------------
  // FOLDER BROWSING
  // --------------------------------------------------------------------------

  async openRunFolderBrowser() {
    if (!this.state.selectedAnalysisType) {
      Utils.showToast('Bitte zuerst einen Analyse-Typ auswählen.', 'warning');
      return;
    }
    
    this.state.runFolderModalSelected = null;
    
    if (this.modalInstances.runFolderModal) {
      this.modalInstances.runFolderModal.show();
    }
    
    const basePath = CONFIG.ANALYSIS_TYPES[this.state.selectedAnalysisType].basePath;
    await this.fetchRunFolder(basePath);
  }

  async fetchRunFolder(path) {
    if (!this.elements.folderLoading || !this.elements.runFolderList) {
      return;
    }

    try {
      this.elements.folderLoading.style.display = 'block';
      this.elements.runFolderList.innerHTML = '';

      const data = await Utils.fetchJSON(`/browse_folder?path=${encodeURIComponent(path)}`);
      
      if (this.elements.runCurrentPath) {
        this.elements.runCurrentPath.textContent = data.current;
      }

      const basePath = CONFIG.ANALYSIS_TYPES[this.state.selectedAnalysisType].basePath;

      // Back button (only if not at base path)
      if (data.current !== basePath) {
        const upPath = data.current.split('/').slice(0, -1).join('/') || basePath;
        const backItem = this.createFolderItem('.. (zurück)', upPath, 'fas fa-arrow-up text-muted', true);
        this.elements.runFolderList.appendChild(backItem);
      }

      // Folders
      data.folders.forEach(folder => {
        const item = this.createFolderItem(folder.name, folder.path, 'fas fa-folder text-transparent');
        this.elements.runFolderList.appendChild(item);
      });

    } catch (error) {
      console.error('Fehler beim Laden der Ordner:', error);
      this.elements.runFolderList.innerHTML = `
        <li class="list-group-item text-danger">
          <i class="fas fa-exclamation-triangle me-2"></i>Fehler beim Laden: ${Utils.escapeHtml(error.message)}
        </li>
      `;
    } finally {
      this.elements.folderLoading.style.display = 'none';
    }
  }

  createFolderItem(name, path, iconClass, isBack = false) {
    const li = document.createElement('li');
    li.className = 'list-group-item list-group-item-action d-flex align-items-center';
    
    const icon = document.createElement('i');
    icon.className = `${iconClass} me-3`;
    
    const span = document.createElement('span');
    span.textContent = name;
    
    li.appendChild(icon);
    li.appendChild(span);

    if (this.state.runFolderModalSelected === path && !isBack) {
      li.classList.add('selected');
    }

    let clickTimeout;

    li.addEventListener('click', () => {
      if (isBack) {
        this.fetchRunFolder(path);
        return;
      }

      if (clickTimeout) {
        // Double click
        clearTimeout(clickTimeout);
        clickTimeout = null;
        this.fetchRunFolder(path);
      } else {
        // Single click
        clickTimeout = setTimeout(() => {
          clickTimeout = null;
          this.state.runFolderModalSelected = path;
          document.querySelectorAll('#runFolderList li').forEach(el => el.classList.remove('selected'));
          li.classList.add('selected');
        }, CONFIG.DOUBLE_CLICK_TIMEOUT);
      }
    });

    return li;
  }

  confirmRunFolder() {
    if (!this.state.runFolderModalSelected) {
      Utils.showToast('Bitte zuerst einen Ordner auswählen.', 'warning');
      return;
    }

    this.state.selectedRunFolder = this.state.runFolderModalSelected;
    
    if (this.elements.selectedRunFolder) {
      const span = this.elements.selectedRunFolder.querySelector('span');
      if (span) {
        span.textContent = this.state.selectedRunFolder;
      }
      this.elements.selectedRunFolder.style.display = 'block';
    }
    
    if (this.elements.selectedRunFolderInput) {
      this.elements.selectedRunFolderInput.value = this.state.selectedRunFolder;
    }
    
    this.loadSamples(this.state.selectedRunFolder);
    
    if (this.modalInstances.runFolderModal) {
      this.modalInstances.runFolderModal.hide();
    }
  }

  // --------------------------------------------------------------------------
  // SAMPLE LOADING
  // --------------------------------------------------------------------------

  async loadSamples(path) {
    try {
      const response = await fetch('/get_samples', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `folder_path=${encodeURIComponent(path)}&recursive=true`
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      
      if (!data.samples || data.samples.length === 0) {
        Utils.showToast('Keine FASTQ-Dateien in diesem Ordner (und Unterordnern) gefunden', 'warning');
        if (this.elements.sampleSection) {
          this.elements.sampleSection.style.display = 'none';
        }
        return;
      }

      this.renderSampleTable(data.samples);
      
      if (this.elements.sampleSection) {
        this.elements.sampleSection.style.display = 'block';
      }
      
      Utils.showToast(`${data.samples.length} Proben gefunden`, 'success');

    } catch (error) {
      console.error('Fehler beim Laden der Proben:', error);
      Utils.showToast(`Fehler beim Laden der Proben: ${error.message}`, 'danger');
      
      if (this.elements.sampleSection) {
        this.elements.sampleSection.style.display = 'none';
      }
    }
  }

  renderSampleTable(samples) {
    if (!this.elements.sampleTable) {
      return;
    }

    const tbody = this.elements.sampleTable.querySelector('tbody');
    if (!tbody) {
      return;
    }

    tbody.innerHTML = samples.map((sample, index) => {
      const icon = CONFIG.SOURCE_ICONS[sample.source] || '<i class="fas fa-question-circle"></i>';
      
      return `
        <tr>
          <td><strong>${index + 1}</strong></td>
          <td>
            <span class="badge table-badge">
              ${icon} ${Utils.escapeHtml(sample.source)}
            </span>
          </td>
          <td><code>${Utils.escapeHtml(sample.probennummer)}</code></td>
          <input type="hidden" name="selected_samples" value="${Utils.escapeHtml(sample.probennummer)}">
        </tr>
      `;
    }).join('');
  }

  // --------------------------------------------------------------------------
  // FORM VALIDATION
  // --------------------------------------------------------------------------

  validateAnalysisForm() {
    if (!this.state.selectedAnalysisType) {
      Utils.showToast('Bitte zuerst einen Analyse-Typ auswählen.', 'warning');
      return false;
    }

    if (!this.elements.selectedRunFolderInput || !this.elements.selectedRunFolderInput.value) {
      Utils.showToast('Bitte zuerst einen Run-Ordner auswählen.', 'warning');
      return false;
    }

    return true;
  }

  // --------------------------------------------------------------------------
  // ANALYSIS HISTORY
  // --------------------------------------------------------------------------

  async loadAnalysisHistory() {
    if (!this.elements.historyLoading || !this.elements.historyTableBody) {
      return;
    }

    const refreshBtn = document.getElementById('refreshHistoryBtn');

    try {
      this.elements.historyLoading.style.display = 'block';
      
      if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<div class="loading-spinner me-1"></div>Laden...';
      }

      const data = await Utils.fetchJSON('/api/analysis_history');
      
      if (data.jobs && data.jobs.length > 0) {
        this.elements.historyTableBody.innerHTML = data.jobs.map(job => 
          this.createHistoryRow(job)
        ).join('');
        
        const countBadge = document.getElementById('historyCount');
        if (countBadge) {
          countBadge.value = data.jobs.length;
        }
      } else {
        this.elements.historyTableBody.innerHTML = `
          <tr>
            <td colspan="6" class="text-center text-muted py-4">Keine Analysen gefunden</td>
          </tr>
        `;
      }

    } catch (error) {
      console.error('Fehler beim Laden der Historie:', error);
      this.elements.historyTableBody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center text-danger py-4">
            <i class="fas fa-exclamation-triangle me-2"></i>
            Fehler beim Laden der Historie: ${Utils.escapeHtml(error.message)}
          </td>
        </tr>
      `;
    } finally {
      this.elements.historyLoading.style.display = 'none';
      
      if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Aktualisieren';
      }
    }
  }

  createHistoryRow(job) {
    const status = CONFIG.STATUS_CONFIG[job.status] || CONFIG.STATUS_CONFIG.queued;
    const typeIcon = CONFIG.ANALYSIS_TYPES[job.job_type]?.icon || 'fas fa-file-alt';

    const reportsHtml = job.reports && job.reports.length > 0
      ? job.reports.map(report => {
          const icon = report.name.endsWith('.pdf') ? 'fas fa-file-pdf' : 
                      report.name.endsWith('.html') ? 'fas fa-file-code' : 'fas fa-file-alt';
          return `
            <a href="/show_report?filepath=${encodeURIComponent(report.path)}" 
               target="_blank" 
               class="report-link">
              <i class="${icon}"></i>${Utils.escapeHtml(report.name)}
            </a>
          `;
        }).join('')
      : '<span class="text-muted">Keine Reports</span>';

    return `
      <tr>
        <td><code>${Utils.escapeHtml(job.job_code)}</code></td>
        <td>
          <span class="badge table-badge">
            <i class="${typeIcon} text-transparent"></i> ${Utils.escapeHtml(job.job_type)}
          </span>
        </td>
        <td><small>${Utils.escapeHtml(job.created_at)}</small></td>
        <td><code>${Utils.escapeHtml(job.run_name)}</code></td>
        <td>
          <span class="badge ${status.class} status-badge">
            <i class="${status.icon} me-1"></i>${status.text}
          </span>
        </td>
        <td>${reportsHtml}</td>
      </tr>
    `;
  }

  // --------------------------------------------------------------------------
  // LIVE LOG
  // --------------------------------------------------------------------------

  initLiveLog(jobId) {
    if (!jobId || !this.elements.logOutput) {
      return;
    }

    const updateLog = async () => {
      try {
        const data = await Utils.fetchJSON(`/api/log/${jobId}`);
        const log = data.log || '(Noch kein Log verfügbar)';
        
        this.elements.logOutput.innerHTML = log.split('\n')
          .map(line => this.highlightLogLine(line))
          .join('\n');
        
        this.elements.logOutput.scrollTo({
          top: this.elements.logOutput.scrollHeight,
          behavior: 'smooth'
        });
        
      } catch (error) {
        console.error('Fehler beim Log-Update:', error);
      }
    };

    const checkStatus = async () => {
      try {
        const data = await Utils.fetchJSON(`/api/progress/${jobId}`);
        
        if (data.status === 'finished') {
          this.handleAnalysisComplete(true);
          this.clearIntervals();
          setTimeout(() => window.location.reload(), 3000);
        } else if (data.status === 'failed') {
          this.handleAnalysisComplete(false);
          this.clearIntervals();
        }
        
      } catch (error) {
        console.error('Fehler beim Status-Check:', error);
      }
    };

    // Start intervals
    const logInterval = setInterval(updateLog, CONFIG.LOG_UPDATE_INTERVAL);
    const statusInterval = setInterval(checkStatus, CONFIG.STATUS_CHECK_INTERVAL);
    this.state.intervals.push(logInterval, statusInterval);

    // Initial calls
    updateLog();
    checkStatus();
  }

  highlightLogLine(line) {
    const patterns = [
      { regex: /\[ERROR\]/, class: 'log-error' },
      { regex: /\[WARNING\]/, class: 'log-warn' },
      { regex: /\[PROCESS\]/, class: 'log-process' },
      { regex: /\[SUCCESS\]/, class: 'log-success' }
    ];

    const pattern = patterns.find(p => p.regex.test(line));
    const className = pattern ? pattern.class : 'log-default';
    
    return `<span class="${className}">${Utils.escapeHtml(line)}</span>`;
  }

  handleAnalysisComplete(success) {
    if (!this.elements.analysisBanner || !this.elements.progressBar) {
      return;
    }

    if (success) {
      this.elements.analysisBanner.classList.replace('alert-info', 'alert-success');
      const strong = this.elements.analysisBanner.querySelector('strong');
      if (strong) {
        strong.innerHTML = '<i class="fas fa-check-circle me-2"></i>Analyse abgeschlossen:';
      }
      
      this.elements.progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
      this.elements.progressBar.innerHTML = '<i class="fas fa-check me-1"></i>Abgeschlossen';
    } else {
      this.elements.analysisBanner.classList.replace('alert-info', 'alert-danger');
      const strong = this.elements.analysisBanner.querySelector('strong');
      if (strong) {
        strong.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Analyse fehlgeschlagen:';
      }
      
      this.elements.progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
      this.elements.progressBar.classList.add('bg-danger');
      this.elements.progressBar.innerHTML = '<i class="fas fa-times me-1"></i>Fehler';
    }
  }

  clearIntervals() {
    this.state.intervals.forEach(interval => clearInterval(interval));
    this.state.intervals = [];
  }

  // --------------------------------------------------------------------------
  // USER MANAGEMENT
  // --------------------------------------------------------------------------

  async loadUsers() {
    if (!this.elements.usersLoading || !this.elements.usersTableBody) {
      return;
    }

    const refreshBtn = document.getElementById('refreshUsersBtn');

    try {
      this.elements.usersLoading.style.display = 'block';
      
      if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<div class="loading-spinner me-1"></div>Laden...';
      }

      const data = await Utils.fetchJSON('/api/users');
      
      if (data.users && data.users.length > 0) {
        this.elements.usersTableBody.innerHTML = data.users.map(user => 
          this.createUserRow(user)
        ).join('');
      } else {
        this.elements.usersTableBody.innerHTML = `
          <tr>
            <td colspan="5" class="text-center text-muted py-4">Keine Benutzer gefunden</td>
          </tr>
        `;
      }

    } catch (error) {
      console.error('Fehler beim Laden der Benutzer:', error);
      this.elements.usersTableBody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center text-danger py-4">
            <i class="fas fa-exclamation-triangle me-2"></i>
            Fehler beim Laden: ${Utils.escapeHtml(error.message)}
          </td>
        </tr>
      `;
    } finally {
      this.elements.usersLoading.style.display = 'none';
      
      if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Aktualisieren';
      }
    }
  }

  createUserRow(user) {
    const roleBadge = user.role ? 
      (user.role === 'admin' ? 
        '<span class="badge role-admin"><i class="fas fa-crown me-1"></i>Admin</span>' :
        '<span class="badge role-user"><i class="fas fa-user me-1"></i>User</span>') :
        '<span class="badge role-norole"><i class="fas fa-question-circle me-1"></i>Keine Rolle</span>';

    const actionsHtml = `
      <div class="btn-group">
        <button class="btn btn-outline-primary btn-sm" data-action="edit-user" data-user-id="${user.id}">
          <i class="fas fa-edit me-1"></i>Bearbeiten
        </button>
        ${!user.is_current_user ? 
          `<button class="btn btn-cancel btn-sm" data-action="delete-user" data-user-id="${user.id}" data-username="${Utils.escapeHtml(user.username)}">
            <i class="fas fa-trash me-1"></i>Löschen
          </button>` : ''}
        ${user.is_current_user ? 
          `<button class="btn btn-outline-primary btn-sm" data-action="change-password">
            <i class="fas fa-key me-1"></i>Passwort ändern
          </button>` : ''}
      </div>
    `;

    return `
      <tr>
        <td><strong>#${user.id}</strong></td>
        <td>
          <div class="d-flex align-items-center">
            <i class="fas fa-user-circle text-muted me-2"></i>
            <span class="fw-medium">${Utils.escapeHtml(user.username)}</span>
            ${user.is_current_user ? '<span class="badge table-badge ms-2">Sie</span>' : ''}
          </div>
        </td>
        <td>
          ${user.email ? 
            `<i class="fas fa-envelope text-muted me-2"></i>${Utils.escapeHtml(user.email)}` :
            '<span class="text-muted"><i class="fas fa-minus me-2"></i>Nicht angegeben</span>'}
        </td>
        <td>${roleBadge}</td>
        <td class="text-center">${actionsHtml}</td>
      </tr>
    `;
  }

  openCreateUserModal() {
    const form = document.getElementById('createUserForm');
    if (form) {
      form.reset();
    }
    
    if (this.modalInstances.createUserModal) {
      this.modalInstances.createUserModal.show();
    }
  }

  async createUser() {
    const form = document.getElementById('createUserForm');
    if (!form) {
      return;
    }

    const formData = new FormData(form);
    
    try {
      await Utils.fetchJSON('/api/users', {
        method: 'POST',
        body: JSON.stringify(Object.fromEntries(formData))
      });
      
      Utils.showToast('Benutzer erfolgreich erstellt', 'success');
      
      if (this.modalInstances.createUserModal) {
        this.modalInstances.createUserModal.hide();
      }
      
      this.loadUsers();
      
    } catch (error) {
      console.error('Fehler beim Erstellen des Benutzers:', error);
      Utils.showToast(`Fehler: ${error.message}`, 'danger');
    }
  }

  async openEditUserModal(userId) {
    try {
      const user = await Utils.fetchJSON(`/api/users/${userId}`);
      
      const form = document.getElementById('editUserForm');
      if (form) {
        form.elements.id.value = user.id;
        form.elements.username.value = user.username;
        form.elements.email.value = user.email || '';
        form.elements.role.value = user.role || 'user';
        form.elements.password.value = '';
      }
      
      if (this.modalInstances.editUserModal) {
        this.modalInstances.editUserModal.show();
      }
      
    } catch (error) {
      console.error('Fehler beim Laden des Benutzers:', error);
      Utils.showToast(`Fehler: ${error.message}`, 'danger');
    }
  }

  async updateUser() {
    const form = document.getElementById('editUserForm');
    if (!form) {
      return;
    }

    const formData = new FormData(form);
    const userId = formData.get('id');
    
    try {
      await Utils.fetchJSON(`/api/users/${userId}`, {
        method: 'PUT',
        body: JSON.stringify(Object.fromEntries(formData))
      });
      
      Utils.showToast('Benutzer erfolgreich aktualisiert', 'success');
      
      if (this.modalInstances.editUserModal) {
        this.modalInstances.editUserModal.hide();
      }
      
      this.loadUsers();
      
    } catch (error) {
      console.error('Fehler beim Aktualisieren des Benutzers:', error);
      Utils.showToast(`Fehler: ${error.message}`, 'danger');
    }
  }

  async deleteUser(userId, username) {
    if (!Utils.confirm(`Benutzer "${username}" wirklich löschen?`)) {
      return;
    }

    try {
      await Utils.fetchJSON(`/api/users/${userId}`, {
        method: 'DELETE'
      });
      
      Utils.showToast('Benutzer erfolgreich gelöscht', 'success');
      this.loadUsers();
      
    } catch (error) {
      console.error('Fehler beim Löschen des Benutzers:', error);
      Utils.showToast(`Fehler: ${error.message}`, 'danger');
    }
  }

  openChangePasswordModal() {
    const form = document.getElementById('changePasswordForm');
    if (form) {
      form.reset();
    }
    
    if (this.modalInstances.changePasswordModal) {
      this.modalInstances.changePasswordModal.show();
    }
  }

  async changePassword() {
    const form = document.getElementById('changePasswordForm');
    if (!form) {
      return;
    }

    const formData = new FormData(form);
    
    // Validate password confirmation
    if (formData.get('new_password') !== formData.get('confirm_password')) {
      Utils.showToast('Passwörter stimmen nicht überein', 'warning');
      return;
    }
    
    try {
      await Utils.fetchJSON('/api/change_password', {
        method: 'POST',
        body: JSON.stringify(Object.fromEntries(formData))
      });
      
      Utils.showToast('Passwort erfolgreich geändert', 'success');
      
      if (this.modalInstances.changePasswordModal) {
        this.modalInstances.changePasswordModal.hide();
      }
      
    } catch (error) {
      console.error('Fehler beim Ändern des Passworts:', error);
      Utils.showToast(`Fehler: ${error.message}`, 'danger');
    }
  }

  // --------------------------------------------------------------------------
  // LOG MANAGEMENT
  // --------------------------------------------------------------------------

  async switchLogFile(logType) {
    if (!this.elements.logContent) {
      return;
    }

    try {
      const data = await Utils.fetchJSON(`/api/logs/${logType}`);
      this.elements.logContent.textContent = data.content || '(Kein Log verfügbar)';
      
      // Scroll to bottom
      this.elements.logContent.scrollTop = this.elements.logContent.scrollHeight;
      
    } catch (error) {
      console.error('Fehler beim Laden des Logs:', error);
      Utils.showToast(`Fehler beim Laden des Logs: ${error.message}`, 'danger');
    }
  }

  refreshLogs() {
    if (this.elements.logFileSelect) {
      this.switchLogFile(this.elements.logFileSelect.value);
    }
  }
}

// ============================================================================
// EVENT DELEGATION FOR DYNAMIC ELEMENTS
// ============================================================================

document.addEventListener('click', (e) => {
  const target = e.target.closest('[data-action]');
  if (!target) return;

  const action = target.dataset.action;
  const userId = target.dataset.userId;
  const username = target.dataset.username;

  switch (action) {
    case 'edit-user':
      if (window.ngsInterface && userId) {
        window.ngsInterface.openEditUserModal(userId);
      }
      break;
    case 'delete-user':
      if (window.ngsInterface && userId && username) {
        window.ngsInterface.deleteUser(userId, username);
      }
      break;
    case 'change-password':
      if (window.ngsInterface) {
        window.ngsInterface.openChangePasswordModal();
      }
      break;
  }
});

// ============================================================================
// INITIALIZE APPLICATION
// ============================================================================

// Create global instance
window.ngsInterface = new NGSInterface();