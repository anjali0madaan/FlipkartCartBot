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
        
        document.getElementById('start-sequential-btn')?.addEventListener('click', () => {
            this.startSequentialSessions();
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
        
        // Session Creation Controls
        document.getElementById('add-session-btn')?.addEventListener('click', () => {
            this.openSessionCreationModal();
        });
        
        document.getElementById('start-session-creation')?.addEventListener('click', () => {
            this.startSessionCreation();
        });
        
        document.getElementById('finalize-session')?.addEventListener('click', () => {
            this.finalizeSessionCreation();
        });
        
        document.getElementById('vnc-reconnect')?.addEventListener('click', () => {
            this.reconnectVNC();
        });
        
        document.getElementById('vnc-fullscreen')?.addEventListener('click', () => {
            this.toggleVNCFullscreen();
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
        // Removed excessive polling - sessions will refresh only on user actions
        // Use manual refresh button or event-driven updates instead
        console.log('Auto-refresh disabled - using event-driven updates');
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
            // Only show connecting status for manual refreshes, not automatic ones
            if (!this.isAutomaticRefresh) {
                this.setConnectionStatus('connecting');
            }
            
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
                // Refresh sessions only after successful action
                setTimeout(() => this.loadSessions(), 1000);
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
                // Refresh sessions only after successful action
                setTimeout(() => this.loadSessions(), 1000);
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
                
                // Refresh sessions only after successful action
                setTimeout(() => this.loadSessions(), 1000);
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
    
    async startSequentialSessions() {
        try {
            const btn = document.getElementById('start-sequential-btn');
            if (btn) {
                btn.classList.add('btn-loading');
                btn.disabled = true;
            }
            
            const response = await fetch('/api/sessions/start-sequential', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showToast(`Sequential execution started for ${data.total_sessions} sessions!`, 'success');
                this.showToast('Sessions will run one after another', 'info');
                // Refresh sessions only after successful action
                setTimeout(() => this.loadSessions(), 1000);
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Failed to start sequential execution:', error);
            this.showToast('Failed to start sequential execution: ' + error.message, 'error');
        } finally {
            const btn = document.getElementById('start-sequential-btn');
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
                // Refresh sessions only after successful action
                setTimeout(() => this.loadSessions(), 1000);
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
    
    // ===== SESSION CREATION METHODS =====
    
    async openSessionCreationModal() {
        console.log('🔧 Opening session creation modal...');
        
        // Reset modal state
        this.resetSessionCreationModal();
        
        // Open the modal
        const modal = new bootstrap.Modal(document.getElementById('sessionCreationModal'));
        modal.show();
        
        console.log('✅ Session creation modal opened');
    }
    
    resetSessionCreationModal() {
        // Reset form fields
        document.getElementById('session-user-identifier').value = '';
        
        // Reset status and progress
        this.updateSessionStatus('Ready to start session creation', 'info');
        this.updateProgress(0, 'Not started');
        
        // Reset buttons
        document.getElementById('start-session-creation').disabled = false;
        document.getElementById('finalize-session').disabled = true;
        
        // Hide VNC iframe
        document.getElementById('vnc-iframe').style.display = 'none';
        document.getElementById('vnc-loading').style.display = 'flex';
        
        // Reset VNC status
        const vncStatus = document.getElementById('vnc-status');
        if (vncStatus) {
            vncStatus.innerHTML = 'VNC Connection: <span class="text-warning">Ready</span>';
        }
    }
    
    async startSessionCreation() {
        const userIdentifier = document.getElementById('session-user-identifier').value.trim();
        
        if (!userIdentifier) {
            this.showToast('Please enter email or mobile number', 'error');
            return;
        }
        
        try {
            console.log('🚀 Starting session creation for:', userIdentifier);
            
            // Update UI
            document.getElementById('start-session-creation').disabled = true;
            this.updateSessionStatus('Creating session...', 'warning');
            this.updateProgress(10, 'Initializing session creation');
            
            // Create session
            const response = await fetch('/api/sessions/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_identifier: userIdentifier
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                console.log('✅ Session creation started:', data);
                
                this.currentSessionId = data.session_id;
                document.getElementById('session-id-display').textContent = `Session ID: ${data.session_id}`;
                
                this.updateProgress(25, 'Session initialized');
                this.updateSessionStatus('Setting up VNC connection...', 'info');
                
                // Setup manual login session
                await this.setupManualLogin();
                
            } else {
                throw new Error(data.message || 'Failed to create session');
            }
            
        } catch (error) {
            console.error('❌ Session creation failed:', error);
            this.updateSessionStatus(`Error: ${error.message}`, 'danger');
            document.getElementById('start-session-creation').disabled = false;
            this.showToast('Failed to create session: ' + error.message, 'error');
        }
    }
    
    async setupManualLogin() {
        try {
            console.log('🔌 Setting up manual login session...');
            
            this.updateProgress(50, 'Session created successfully');
            
            // Hide VNC iframe and show manual login instructions
            document.getElementById('vnc-loading').style.display = 'none';
            document.getElementById('vnc-iframe').style.display = 'none';
            
            // Show manual login instructions
            this.showManualLoginInstructions();
            
            this.updateProgress(80, 'Chrome launched in VNC');
            this.updateSessionStatus('Chrome auto-launched - Complete login in VNC tab', 'success');
            
            const vncStatus = document.getElementById('vnc-status');
            if (vncStatus) {
                vncStatus.innerHTML = 'Chrome Status: <span class="text-success">Launched in VNC</span>';
            }
            
            // Enable finalize button immediately
            setTimeout(() => {
                const finalizeBtn = document.getElementById('finalize-session');
                if (finalizeBtn) {
                    finalizeBtn.disabled = false;
                    console.log('✅ Finalize button enabled');
                } else {
                    console.error('❌ Finalize button not found!');
                }
                this.updateProgress(100, 'Ready for login completion');
            }, 1000);
            
        } catch (error) {
            console.error('❌ Session setup failed:', error);
            this.updateSessionStatus(`Setup Error: ${error.message}`, 'danger');
            this.showToast('Session setup failed: ' + error.message, 'error');
        }
    }
    
    showManualLoginInstructions() {
        const rightPanel = document.querySelector('.col-md-9');
        const userIdentifier = document.getElementById('session-user-identifier').value;
        rightPanel.innerHTML = `
            <div class="h-100 d-flex align-items-center justify-content-center">
                <div class="text-center p-5">
                    <div class="mb-4">
                        <i class="fas fa-rocket fa-4x text-success mb-3"></i>
                        <h3>Chrome Auto-Launched in VNC!</h3>
                        <p class="text-muted">Session for: <strong>${userIdentifier}</strong></p>
                    </div>
                    
                    <div class="card border-success mb-4">
                        <div class="card-body">
                            <h5 class="card-title text-success">
                                <i class="fas fa-chrome me-2"></i>
                                Chrome is Ready for Login
                            </h5>
                            <p class="card-text">Chrome has automatically opened in the <strong>VNC tab</strong> with the Flipkart login page loaded</p>
                            <div class="alert alert-info small mt-3">
                                <i class="fas fa-lightbulb me-2"></i>
                                The VNC tab provides a desktop environment where you can use Chrome to login to Flipkart
                            </div>
                        </div>
                    </div>
                    
                    <div class="alert alert-success text-start">
                        <h6><i class="fas fa-check-circle me-2"></i>What happened automatically:</h6>
                        <ul class="mb-2">
                            <li><strong>Profile directory created:</strong> <code>flipkart_profiles/profile_${this.currentSessionId}</code></li>
                            <li><strong>Chrome launched in VNC</strong> with your specific profile</li>
                            <li><strong>Flipkart login page opened</strong> automatically</li>
                        </ul>
                    </div>
                    
                    <div class="alert alert-info text-start">
                        <h6><i class="fas fa-list-ol me-2"></i>Complete these simple steps:</h6>
                        <ol class="mb-0">
                            <li><strong>Switch to the "VNC" tab</strong> in your Replit workspace</li>
                            <li><strong>You'll see Chrome is already open</strong> with Flipkart login page</li>
                            <li><strong>Enter your credentials:</strong> <code>${userIdentifier}</code></li>
                            <li><strong>Complete OTP verification</strong></li>
                            <li><strong>Return here</strong> and click "Finalize Session" below</li>
                        </ol>
                    </div>
                    
                    <div class="mt-4">
                        <div class="alert alert-warning small">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            <strong>Important:</strong> Make sure to complete the entire login process including OTP verification before finalizing the session.
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // This function is no longer needed in the manual login workflow
    
    async finalizeSessionCreation() {
        const userIdentifier = document.getElementById('session-user-identifier').value.trim();
        
        if (!this.currentSessionId) {
            this.showToast('No active session to finalize', 'error');
            return;
        }
        
        try {
            console.log('✅ Finalizing session creation...');
            
            document.getElementById('finalize-session').disabled = true;
            this.updateProgress(95, 'Finalizing session...');
            this.updateSessionStatus('Saving session...', 'info');
            
            const response = await fetch(`/api/sessions/${this.currentSessionId}/finalize`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_identifier: userIdentifier,
                    login_completed: true
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                console.log('🎉 Session creation completed!');
                
                this.updateProgress(100, 'Session created successfully!');
                this.updateSessionStatus('Session created successfully!', 'success');
                
                this.showToast('Session created successfully!', 'success');
                
                // Close modal after short delay
                setTimeout(() => {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('sessionCreationModal'));
                    modal.hide();
                    
                    // Refresh sessions list
                    this.loadSessions();
                }, 2000);
                
            } else {
                throw new Error(data.message || 'Failed to finalize session');
            }
            
        } catch (error) {
            console.error('❌ Session finalization failed:', error);
            this.updateSessionStatus(`Error: ${error.message}`, 'danger');
            document.getElementById('finalize-session').disabled = false;
            this.showToast('Failed to finalize session: ' + error.message, 'error');
        }
    }
    
    reconnectVNC() {
        console.log('🔄 Reconnecting VNC...');
        
        const iframe = document.getElementById('vnc-iframe');
        const currentSrc = iframe.src;
        
        // Hide iframe and show loading
        iframe.style.display = 'none';
        document.getElementById('vnc-loading').style.display = 'flex';
        const vncStatusReconnect = document.getElementById('vnc-status');
        if (vncStatusReconnect) {
            vncStatusReconnect.innerHTML = 'VNC Connection: <span class="text-warning">Reconnecting...</span>';
        }
        
        // Reload iframe
        iframe.src = '';
        setTimeout(() => {
            iframe.src = currentSrc;
            
            setTimeout(() => {
                document.getElementById('vnc-loading').style.display = 'none';
                iframe.style.display = 'block';
                const vncStatusConnected = document.getElementById('vnc-status');
                if (vncStatusConnected) {
                    vncStatusConnected.innerHTML = 'VNC Connection: <span class="text-success">Connected</span>';
                }
            }, 3000);
        }, 1000);
    }
    
    toggleVNCFullscreen() {
        const iframe = document.getElementById('vnc-iframe');
        
        if (iframe.requestFullscreen) {
            iframe.requestFullscreen();
        } else if (iframe.webkitRequestFullscreen) {
            iframe.webkitRequestFullscreen();
        } else if (iframe.mozRequestFullScreen) {
            iframe.mozRequestFullScreen();
        } else if (iframe.msRequestFullscreen) {
            iframe.msRequestFullscreen();
        }
    }
    
    updateSessionStatus(message, type = 'info') {
        const statusElement = document.getElementById('session-status');
        if (!statusElement) {
            console.warn('Session status element not found');
            return;
        }
        
        const iconMap = {
            'info': 'fas fa-info-circle',
            'success': 'fas fa-check-circle',
            'warning': 'fas fa-exclamation-triangle',
            'danger': 'fas fa-times-circle'
        };
        
        statusElement.className = `alert alert-${type}`;
        statusElement.innerHTML = `<i class="${iconMap[type]} me-2"></i>${message}`;
    }
    
    updateProgress(percentage, text) {
        const progressBar = document.getElementById('creation-progress');
        const progressText = document.getElementById('progress-text');
        
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', percentage);
        
        if (progressText) {
            progressText.textContent = text;
        }
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