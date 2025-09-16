/**
 * Flipkart Automation Control Panel - JavaScript
 * Handles real-time updates, session management, and UI interactions
 */

class FlipkartControlPanel {
    constructor() {
        this.sessions = [];
        this.config = {};
        this.logEventSources = {};
        this.currentView = 'grid';
        this.autoScroll = true;
        this.refreshInterval = null;
        this.connectionStatus = 'connected';
        
        this.init();
    }
    
    init() {
        console.log('🚀 Initializing Flipkart Control Panel...');
        
        // Initialize components
        this.setupEventListeners();
        this.startClock();
        this.loadConfig();
        this.loadSessions();
        this.startAutoRefresh();
        
        console.log('✅ Control Panel initialized successfully');
    }
    
    setupEventListeners() {
        // Configuration form
        document.getElementById('config-form')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveConfig();
        });
        
        // Session control buttons
        document.getElementById('start-all-btn')?.addEventListener('click', () => {
            this.startAllSessions();
        });
        
        document.getElementById('stop-all-btn')?.addEventListener('click', () => {
            this.stopAllSessions();
        });
        
        document.getElementById('refresh-sessions-btn')?.addEventListener('click', () => {
            this.loadSessions();
        });
        
        // View toggle buttons
        document.getElementById('view-grid-btn')?.addEventListener('click', () => {
            this.setView('grid');
        });
        
        document.getElementById('view-list-btn')?.addEventListener('click', () => {
            this.setView('list');
        });
        
        // Log modal controls
        document.getElementById('auto-scroll-btn')?.addEventListener('click', () => {
            this.toggleAutoScroll();
        });
        
        document.getElementById('clear-logs-btn')?.addEventListener('click', () => {
            this.clearLogs();
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey) {
                switch (e.key) {
                    case 'r':
                        e.preventDefault();
                        this.loadSessions();
                        break;
                    case 's':
                        e.preventDefault();
                        this.saveConfig();
                        break;
                }
            }
        });
    }
    
    startClock() {
        const updateTime = () => {
            const now = new Date();
            const timeString = now.toLocaleString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            
            const timeElement = document.getElementById('current-time');
            if (timeElement) {
                timeElement.textContent = timeString;
            }
        };
        
        updateTime();
        setInterval(updateTime, 1000);
    }
    
    startAutoRefresh() {
        // Refresh sessions every 5 seconds
        this.refreshInterval = setInterval(() => {
            this.loadSessions();
        }, 5000);
    }
    
    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.config = data.config;
                this.populateConfigForm();
            }
        } catch (error) {
            console.error('Failed to load config:', error);
            this.showToast('Failed to load configuration', 'error');
        }
    }
    
    populateConfigForm() {
        // Populate form fields with current config
        const searchQuery = document.getElementById('search-query');
        const minPrice = document.getElementById('min-price');
        const maxPrice = document.getElementById('max-price');
        const brandFilter = document.getElementById('brand-filter');
        const sortBy = document.getElementById('sort-by');
        const headlessMode = document.getElementById('headless-mode');
        const saleDetection = document.getElementById('sale-detection');
        
        if (searchQuery) searchQuery.value = this.config.search_settings?.search_query || '';
        if (minPrice) minPrice.value = this.config.search_settings?.min_price || 1;
        if (maxPrice) maxPrice.value = this.config.search_settings?.max_price || 999999;
        if (brandFilter) brandFilter.value = this.config.filters?.brand || '';
        if (sortBy) sortBy.value = this.config.filters?.sort_by || 'price_low_to_high';
        if (headlessMode) headlessMode.checked = this.config.automation_settings?.headless_mode || false;
        if (saleDetection) saleDetection.checked = this.config.sale_settings?.enable_sale_detection || false;
    }
    
    async saveConfig() {
        try {
            // Collect form data
            const newConfig = {
                search_settings: {
                    product_name: "iPhone",
                    search_query: document.getElementById('search-query')?.value || '',
                    min_price: parseInt(document.getElementById('min-price')?.value) || 1,
                    max_price: parseInt(document.getElementById('max-price')?.value) || 999999
                },
                automation_settings: {
                    wait_time: 3,
                    max_retries: 3,
                    headless_mode: document.getElementById('headless-mode')?.checked || false,
                    page_load_timeout: 30
                },
                user_credentials: {
                    email: "",
                    password: ""
                },
                sale_settings: {
                    enable_sale_detection: document.getElementById('sale-detection')?.checked || false,
                    min_discount_percentage: 10,
                    max_discount_percentage: 50,
                    prefer_sale_items: false
                },
                filters: {
                    brand: document.getElementById('brand-filter')?.value || '',
                    sort_by: document.getElementById('sort-by')?.value || 'price_low_to_high',
                    condition: "new"
                }
            };
            
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newConfig)
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.config = data.config;
                this.showToast('Configuration saved successfully!', 'success');
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Failed to save config:', error);
            this.showToast('Failed to save configuration: ' + error.message, 'error');
        }
    }
    
    async loadSessions() {
        try {
            this.setConnectionStatus('connecting');
            
            const response = await fetch('/api/sessions');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.sessions = data.sessions;
                this.updateSessionsDisplay();
                this.updateStats();
                this.setConnectionStatus('connected');
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Failed to load sessions:', error);
            this.setConnectionStatus('disconnected');
            this.showToast('Failed to load sessions: ' + error.message, 'error');
        }
    }
    
    updateSessionsDisplay() {
        const container = document.getElementById('sessions-container');
        const loadingIndicator = document.getElementById('loading-indicator');
        const noSessionsMsg = document.getElementById('no-sessions');
        
        if (!container) return;
        
        // Hide loading indicator
        if (loadingIndicator) loadingIndicator.style.display = 'none';
        
        if (this.sessions.length === 0) {
            container.innerHTML = '';
            if (noSessionsMsg) noSessionsMsg.classList.remove('d-none');
            return;
        }
        
        if (noSessionsMsg) noSessionsMsg.classList.add('d-none');
        
        // Generate session cards
        const sessionCards = this.sessions.map(session => this.createSessionCard(session)).join('');
        container.innerHTML = sessionCards;
        
        // Add event listeners to session buttons
        this.addSessionEventListeners();
    }
    
    createSessionCard(session) {
        const statusClass = `status-${session.status}`;
        const statusIcon = this.getStatusIcon(session.status);
        const createdDate = new Date(session.created).toLocaleDateString();
        const lastUsedDate = new Date(session.last_used).toLocaleDateString();
        
        return `
            <div class="col-lg-6 col-xl-4 mb-4">
                <div class="session-card fade-in">
                    <div class="session-header">
                        <div class="session-info">
                            <div class="session-user">
                                <i class="fas fa-user me-2"></i>${session.user}
                            </div>
                            <small>Created: ${createdDate}</small>
                            <small>Last Used: ${lastUsedDate}</small>
                        </div>
                        <span class="status-badge ${statusClass}">
                            <i class="${statusIcon} me-1"></i>${session.status}
                        </span>
                    </div>
                    
                    <div class="session-body">
                        <div class="row text-center mb-3">
                            <div class="col-6">
                                <small class="text-muted">Status</small>
                                <div class="fw-bold ${this.getStatusColor(session.status)}">${session.status.toUpperCase()}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">Valid</small>
                                <div class="fw-bold ${session.valid ? 'text-success' : 'text-danger'}">
                                    ${session.valid ? 'YES' : 'NO'}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="session-footer">
                        <div class="action-buttons">
                            ${session.can_start ? `
                                <button class="btn btn-success btn-sm start-session-btn" data-session="${session.id}">
                                    <i class="fas fa-play me-1"></i>Start
                                </button>
                            ` : ''}
                            
                            ${session.can_stop ? `
                                <button class="btn btn-danger btn-sm stop-session-btn" data-session="${session.id}">
                                    <i class="fas fa-stop me-1"></i>Stop
                                </button>
                            ` : ''}
                            
                            <button class="btn btn-outline-primary btn-sm logs-btn" data-session="${session.id}">
                                <i class="fas fa-file-alt me-1"></i>Logs
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    addSessionEventListeners() {
        // Start session buttons
        document.querySelectorAll('.start-session-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.target.closest('.start-session-btn').dataset.session;
                this.startSession(sessionId);
            });
        });
        
        // Stop session buttons
        document.querySelectorAll('.stop-session-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.target.closest('.stop-session-btn').dataset.session;
                this.stopSession(sessionId);
            });
        });
        
        // Log viewer buttons
        document.querySelectorAll('.logs-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sessionId = e.target.closest('.logs-btn').dataset.session;
                this.showLogs(sessionId);
            });
        });
    }
    
    async startSession(sessionId) {
        try {
            const btn = document.querySelector(`[data-session="${sessionId}"].start-session-btn`);
            if (btn) {
                btn.classList.add('btn-loading');
                btn.disabled = true;
            }
            
            const response = await fetch(`/api/sessions/${sessionId}/start`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showToast(`Session ${sessionId} started successfully!`, 'success');
                this.loadSessions(); // Refresh sessions
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error(`Failed to start session ${sessionId}:`, error);
            this.showToast(`Failed to start session: ${error.message}`, 'error');
        } finally {
            const btn = document.querySelector(`[data-session="${sessionId}"].start-session-btn`);
            if (btn) {
                btn.classList.remove('btn-loading');
                btn.disabled = false;
            }
        }
    }
    
    async stopSession(sessionId) {
        try {
            const btn = document.querySelector(`[data-session="${sessionId}"].stop-session-btn`);
            if (btn) {
                btn.classList.add('btn-loading');
                btn.disabled = true;
            }
            
            const response = await fetch(`/api/sessions/${sessionId}/stop`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showToast(`Session ${sessionId} stopped successfully!`, 'success');
                this.loadSessions(); // Refresh sessions
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error(`Failed to stop session ${sessionId}:`, error);
            this.showToast(`Failed to stop session: ${error.message}`, 'error');
        } finally {
            const btn = document.querySelector(`[data-session="${sessionId}"].stop-session-btn`);
            if (btn) {
                btn.classList.remove('btn-loading');
                btn.disabled = false;
            }
        }
    }
    
    async startAllSessions() {
        try {
            const btn = document.getElementById('start-all-btn');
            if (btn) {
                btn.classList.add('btn-loading');
                btn.disabled = true;
            }
            
            const response = await fetch('/api/sessions/start-all', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showToast(`Started ${data.started_sessions.length} sessions successfully!`, 'success');
                
                if (data.failed_sessions.length > 0) {
                    this.showToast(`${data.failed_sessions.length} sessions failed to start`, 'warning');
                }
                
                this.loadSessions(); // Refresh sessions
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Failed to start all sessions:', error);
            this.showToast('Failed to start all sessions: ' + error.message, 'error');
        } finally {
            const btn = document.getElementById('start-all-btn');
            if (btn) {
                btn.classList.remove('btn-loading');
                btn.disabled = false;
            }
        }
    }
    
    async stopAllSessions() {
        try {
            const btn = document.getElementById('stop-all-btn');
            if (btn) {
                btn.classList.add('btn-loading');
                btn.disabled = true;
            }
            
            const response = await fetch('/api/sessions/stop-all', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showToast(`Stopped ${data.stopped_sessions.length} sessions successfully!`, 'success');
                this.loadSessions(); // Refresh sessions
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Failed to stop all sessions:', error);
            this.showToast('Failed to stop all sessions: ' + error.message, 'error');
        } finally {
            const btn = document.getElementById('stop-all-btn');
            if (btn) {
                btn.classList.remove('btn-loading');
                btn.disabled = false;
            }
        }
    }
    
    showLogs(sessionId) {
        const modal = new bootstrap.Modal(document.getElementById('logModal'));
        document.getElementById('current-log-session').textContent = sessionId;
        
        // Clear existing logs
        this.clearLogs();
        
        // Start log streaming
        this.startLogStreaming(sessionId);
        
        modal.show();
    }
    
    async startLogStreaming(sessionId) {
        // Stop any existing log streaming
        this.stopLogStreaming();
        
        try {
            // First, load existing logs
            const response = await fetch(`/api/logs/${sessionId}`);
            const data = await response.json();
            
            if (data.status === 'success' && data.logs.length > 0) {
                this.displayLogs(data.logs);
            }
            
            // Start real-time streaming
            const eventSource = new EventSource(`/api/logs/${sessionId}/stream`);
            this.logEventSources[sessionId] = eventSource;
            
            eventSource.onmessage = (event) => {
                const logData = JSON.parse(event.data);
                
                if (logData.log) {
                    this.addLogEntry(logData.log);
                }
            };
            
            eventSource.onerror = (error) => {
                console.error('Log streaming error:', error);
                this.stopLogStreaming();
            };
            
        } catch (error) {
            console.error('Failed to start log streaming:', error);
            this.showToast('Failed to load logs: ' + error.message, 'error');
        }
    }
    
    stopLogStreaming() {
        Object.values(this.logEventSources).forEach(eventSource => {
            eventSource.close();
        });
        this.logEventSources = {};
    }
    
    displayLogs(logs) {
        const logContainer = document.getElementById('log-container');
        if (!logContainer) return;
        
        logs.forEach(log => {
            this.addLogEntry(log);
        });
    }
    
    addLogEntry(logData) {
        const logContainer = document.getElementById('log-container');
        if (!logContainer) return;
        
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        
        let logClass = '';
        const message = typeof logData === 'string' ? logData : logData.message || '';
        
        // Determine log level based on content
        if (message.toLowerCase().includes('error')) {
            logClass = 'error';
        } else if (message.toLowerCase().includes('warning')) {
            logClass = 'warning';
        } else if (message.toLowerCase().includes('success')) {
            logClass = 'success';
        } else if (message.toLowerCase().includes('info')) {
            logClass = 'info';
        }
        
        logEntry.className += ` ${logClass}`;
        
        const timestamp = logData.timestamp ? new Date(logData.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
        logEntry.innerHTML = `<span class="text-muted">[${timestamp}]</span> ${message}`;
        
        logContainer.appendChild(logEntry);
        
        // Auto-scroll if enabled
        if (this.autoScroll) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    }
    
    clearLogs() {
        const logContainer = document.getElementById('log-container');
        if (logContainer) {
            logContainer.innerHTML = '';
        }
    }
    
    toggleAutoScroll() {
        this.autoScroll = !this.autoScroll;
        const btn = document.getElementById('auto-scroll-btn');
        if (btn) {
            btn.classList.toggle('active', this.autoScroll);
            btn.innerHTML = this.autoScroll 
                ? '<i class="fas fa-arrow-down me-1"></i>Auto Scroll' 
                : '<i class="fas fa-pause me-1"></i>Manual';
        }
    }
    
    updateStats() {
        const totalSessions = this.sessions.length;
        const activeSessions = this.sessions.filter(s => s.status === 'running').length;
        
        const totalElement = document.getElementById('total-sessions');
        const activeElement = document.getElementById('active-sessions');
        
        if (totalElement) totalElement.textContent = totalSessions;
        if (activeElement) activeElement.textContent = activeSessions;
    }
    
    setView(view) {
        this.currentView = view;
        
        // Update button states
        const gridBtn = document.getElementById('view-grid-btn');
        const listBtn = document.getElementById('view-list-btn');
        
        if (gridBtn && listBtn) {
            gridBtn.classList.toggle('active', view === 'grid');
            listBtn.classList.toggle('active', view === 'list');
        }
        
        // Update container classes
        const container = document.getElementById('sessions-container');
        if (container) {
            container.className = view === 'grid' ? 'row' : 'list-view';
        }
    }
    
    setConnectionStatus(status) {
        this.connectionStatus = status;
        const statusElement = document.getElementById('connection-status');
        
        if (statusElement) {
            statusElement.className = 'badge';
            
            switch (status) {
                case 'connected':
                    statusElement.classList.add('bg-success');
                    statusElement.innerHTML = '<i class="fas fa-circle"></i> Connected';
                    break;
                case 'connecting':
                    statusElement.classList.add('bg-warning');
                    statusElement.innerHTML = '<i class="fas fa-circle"></i> Connecting...';
                    break;
                case 'disconnected':
                    statusElement.classList.add('bg-danger');
                    statusElement.innerHTML = '<i class="fas fa-circle"></i> Disconnected';
                    break;
            }
        }
    }
    
    getStatusIcon(status) {
        switch (status) {
            case 'running': return 'fas fa-play-circle';
            case 'stopped': return 'fas fa-stop-circle';
            case 'finished': return 'fas fa-check-circle';
            case 'error': return 'fas fa-exclamation-circle';
            default: return 'fas fa-question-circle';
        }
    }
    
    getStatusColor(status) {
        switch (status) {
            case 'running': return 'text-success';
            case 'stopped': return 'text-secondary';
            case 'finished': return 'text-info';
            case 'error': return 'text-danger';
            default: return 'text-muted';
        }
    }
    
    showToast(message, type = 'info', duration = 5000) {
        const container = document.getElementById('status-messages');
        if (!container) return;
        
        const toastId = `toast-${Date.now()}`;
        const iconMap = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        
        const toastHtml = `
            <div id="${toastId}" class="toast toast-${type}" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-body d-flex align-items-center">
                    <i class="${iconMap[type]} me-2"></i>
                    <span>${message}</span>
                    <button type="button" class="btn-close ms-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: duration
        });
        
        toast.show();
        
        // Clean up after toast is hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
    
    destroy() {
        // Clean up intervals and event sources
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        this.stopLogStreaming();
    }
}

// Initialize the control panel when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.controlPanel = new FlipkartControlPanel();
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (window.controlPanel) {
        window.controlPanel.destroy();
    }
});