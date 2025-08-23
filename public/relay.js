// Enhanced Relay Dashboard with rnostr Prometheus metrics support
class RelayDashboard {
    constructor() {
        this.statsUpdateInterval = null;
        this.activityUpdateInterval = null;
        this.lastUpdateTime = null;
        this.isUpdating = false;
        this.recentActivity = [];
        this.init();
    }

    init() {
        this.loadRelayInfo();
        this.startStatsUpdates();
        this.startActivityUpdates();
        this.checkRelayStatus();
        this.setupUpdateIndicators();
    }

    setupUpdateIndicators() {
        this.updateLastUpdatedTime();
        
        const manualRefresh = document.getElementById('manual-refresh');
        if (manualRefresh) {
            manualRefresh.addEventListener('click', () => this.forceRefresh());
        }
    }

    updateLastUpdatedTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        const updateTimeEl = document.getElementById('update-time');
        if (updateTimeEl) {
            updateTimeEl.textContent = timeString;
        }
        this.lastUpdateTime = now;
    }

    setUpdateIndicator(isUpdating) {
        const indicator = document.getElementById('update-indicator');
        const refreshBtn = document.getElementById('manual-refresh');
        
        if (indicator) {
            indicator.style.color = isUpdating ? '#10b981' : '#6b7280';
            indicator.style.animation = isUpdating ? 'pulse-indicator 1s infinite' : 'none';
        }
        
        if (refreshBtn) {
            refreshBtn.disabled = isUpdating;
            refreshBtn.style.opacity = isUpdating ? '0.5' : '1';
        }
        
        this.isUpdating = isUpdating;
    }

    async forceRefresh() {
        if (this.isUpdating) return;
        
        console.log('Force refreshing all data...');
        this.setUpdateIndicator(true);
        
        try {
            await Promise.all([
                this.updateStats(),
                this.updateActivity(),
                this.loadRelayInfo(),
                this.checkRelayStatus()
            ]);
            this.updateLastUpdatedTime();
        } finally {
            this.setUpdateIndicator(false);
        }
    }

    async loadRelayInfo() {
        try {
            const response = await fetch('/api/relay/stats');
            if (response.ok) {
                const info = await response.json();
                
                if (info.relay_software) {
                    const softwareEl = document.getElementById('relay-software');
                    if (softwareEl) {
                        softwareEl.textContent = info.relay_software;
                    }
                }
                
                if (info.supported_nips) {
                    const nipCountEl = document.getElementById('nip-count');
                    if (nipCountEl) {
                        nipCountEl.textContent = info.supported_nips.length;
                    }
                    this.displayNIPs(info.supported_nips);
                }
            }
        } catch (error) {
            console.error('Error loading relay info:', error);
        }
    }

    displayNIPs(nips) {
        const nipsContainer = document.getElementById('nips-list');
        if (!nipsContainer) return;
        
        nipsContainer.innerHTML = '';
        
        const nipCategories = {
            basic: [1, 2, 4, 11],
            auth: [22, 26, 42],
            advanced: [9, 12, 15, 16, 20, 70],
            social: [25, 28, 33, 40]
        };
        
        nips.sort((a, b) => a - b).forEach(nip => {
            const nipElement = document.createElement('div');
            nipElement.className = 'nip-item';
            
            let category = 'advanced';
            for (const [cat, nipList] of Object.entries(nipCategories)) {
                if (nipList.includes(nip)) {
                    category = cat;
                    break;
                }
            }
            
            nipElement.innerHTML = `
                <span class="nip-badge ${category}">NIP-${nip.toString().padStart(2, '0')}</span>
            `;
            
            nipsContainer.appendChild(nipElement);
        });
    }

    async checkRelayStatus() {
        const statusIndicator = document.getElementById('relay-status');
        if (!statusIndicator) return;
        
        const statusDot = statusIndicator.querySelector('.status-dot');
        const statusText = statusIndicator.querySelector('.status-text');

        try {
            const response = await fetch('/api/relay/stats');
            if (response.ok) {
                const stats = await response.json();
                if (statusDot) statusDot.className = 'status-dot online';
                if (statusText) statusText.textContent = `Online - ${stats.relay_software || 'rnostr'}`;
            } else {
                throw new Error('Stats not responding');
            }
        } catch (error) {
            if (statusDot) statusDot.className = 'status-dot offline';
            if (statusText) statusText.textContent = 'Offline';
        }
    }

    async updateStats() {
        try {
            this.setUpdateIndicator(true);
            const response = await fetch('/api/relay/stats');
            if (!response.ok) throw new Error('Failed to fetch stats');
            
            const stats = await response.json();
            
            this.updateStatElement('active-sessions', stats.active_sessions || 0);
            this.updateStatElement('total-events', stats.relay_events || stats.new_events || stats.local_content || 0);
            this.updateStatElement('total-sessions', stats.total_sessions || 0);
            this.updateStatElement('total-requests', 
                (stats.total_requests || 0) + (stats.event_commands || 0) + (stats.close_commands || 0));
            this.updateStatElement('database-operations', 
                (stats.database_reads || 0) + (stats.database_writes || 0));
            this.updateStatElement('uptime', 
                stats.uptime_hours ? `${stats.uptime_hours}h` : '0h');
            
            this.updateLastUpdatedTime();
            
            // Track activity changes for recent events
            this.trackActivityChanges(stats);
            
        } catch (error) {
            console.error('Error updating stats:', error);
            const statElements = ['active-sessions', 'total-events', 'total-sessions', 
                                'total-requests', 'database-operations', 'uptime'];
            statElements.forEach(id => this.updateStatElement(id, '?'));
        } finally {
            this.setUpdateIndicator(false);
        }
    }

    trackActivityChanges(currentStats) {
        const now = new Date();
        
        // Check for new database reads (indicates new requests)
        if (this.lastStats && currentStats.database_reads > this.lastStats.database_reads) {
            const newReads = currentStats.database_reads - this.lastStats.database_reads;
            this.addActivityItem({
                type: 'query',
                content: `${newReads} database read${newReads > 1 ? 's' : ''} - Client query processed`,
                timestamp: now
            });
        }
        
        // Check for new sessions
        if (this.lastStats && currentStats.total_sessions > this.lastStats.total_sessions) {
            const newSessions = currentStats.total_sessions - this.lastStats.total_sessions;
            this.addActivityItem({
                type: 'connect',
                content: `New client connection (Session #${currentStats.total_sessions})`,
                timestamp: now
            });
        }
        
        // Check for active session changes
        if (this.lastStats && currentStats.active_sessions !== this.lastStats.active_sessions) {
            const change = currentStats.active_sessions - this.lastStats.active_sessions;
            if (change > 0) {
                this.addActivityItem({
                    type: 'connect',
                    content: `Client connected (${currentStats.active_sessions} active)`,
                    timestamp: now
                });
            } else if (change < 0) {
                this.addActivityItem({
                    type: 'disconnect',
                    content: `Client disconnected (${currentStats.active_sessions} active)`,
                    timestamp: now
                });
            }
        }
        
        // Check for new requests
        if (this.lastStats && currentStats.total_requests > this.lastStats.total_requests) {
            const newRequests = currentStats.total_requests - this.lastStats.total_requests;
            this.addActivityItem({
                type: 'request',
                content: `${newRequests} new request${newRequests > 1 ? 's' : ''} processed`,
                timestamp: now
            });
        }
        
        // Store current stats for next comparison
        this.lastStats = { ...currentStats };
    }

    addActivityItem(item) {
        this.recentActivity.unshift(item);
        
        // Keep only last 10 items
        if (this.recentActivity.length > 10) {
            this.recentActivity = this.recentActivity.slice(0, 10);
        }
        
        // Update the display
        this.displayRecentActivity();
    }

    displayRecentActivity() {
        const activityFeed = document.getElementById('activity-feed');
        const activityStatus = document.getElementById('activity-status');
        
        if (!activityFeed) return;
        
        if (this.recentActivity.length > 0) {
            activityFeed.innerHTML = this.recentActivity.map(item => `
                <div class="activity-item">
                    <div class="activity-time">${this.formatTime(item.timestamp)}</div>
                    <div class="activity-content">
                        <span class="activity-type activity-type-${item.type}">${item.type.toUpperCase()}</span>
                        <span class="activity-text">${item.content}</span>
                    </div>
                </div>
            `).join('');
            
            if (activityStatus) {
                activityStatus.textContent = `${this.recentActivity.length} recent events`;
            }
        } else {
            activityFeed.innerHTML = `
                <div class="activity-item">
                    <div class="activity-content">
                        <span class="activity-text">Waiting for relay activity...</span>
                    </div>
                </div>
            `;
            
            if (activityStatus) {
                activityStatus.textContent = 'No recent activity';
            }
        }
    }

    updateStatElement(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            const oldValue = element.textContent;
            element.textContent = value;
            
            if (oldValue !== value.toString() && oldValue !== '-') {
                element.classList.add('stat-pulse');
                setTimeout(() => element.classList.remove('stat-pulse'), 500);
            }
        }
    }

    async updateActivity() {
        // Just refresh our tracked activity display
        this.displayRecentActivity();
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        
        if (hours > 0) return `${hours}h ago`;
        if (minutes > 0) return `${minutes}m ago`;
        if (seconds > 10) return `${seconds}s ago`;
        return 'Just now';
    }

    startStatsUpdates() {
        this.updateStats();
        
        this.statsUpdateInterval = setInterval(() => {
            if (!this.isUpdating) {
                this.updateStats();
            }
        }, 10000);
    }

    startActivityUpdates() {
        this.updateActivity();
        
        this.activityUpdateInterval = setInterval(() => {
            if (!this.isUpdating) {
                this.updateActivity();
            }
        }, 5000); // More frequent updates for activity
    }

    destroy() {
        if (this.statsUpdateInterval) {
            clearInterval(this.statsUpdateInterval);
        }
        if (this.activityUpdateInterval) {
            clearInterval(this.activityUpdateInterval);
        }
    }
}

function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const text = element.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        const button = element.nextElementSibling;
        if (button) {
            const originalText = button.textContent;
            button.textContent = '✓';
            button.style.color = '#10b981';
            
            setTimeout(() => {
                button.textContent = originalText;
                button.style.color = '';
            }, 2000);
        }
    }).catch(err => {
        console.error('Failed to copy text: ', err);
    });
}

let dashboard = null;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new RelayDashboard();
    
    window.addEventListener('beforeunload', () => {
        if (dashboard) {
            dashboard.destroy();
        }
    });
});

// Enhanced CSS with centered headers and activity styling
const style = document.createElement('style');
style.textContent = `
    .stat-pulse {
        animation: stat-pulse-anim 0.5s ease-in-out;
    }
    
    @keyframes stat-pulse-anim {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    @keyframes pulse-indicator {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* CENTERED HEADERS */
    .stats-header-centered {
        text-align: center;
        margin: 2rem 0 1.5rem 0;
    }
    
    .stats-header-centered h2 {
        margin: 0 0 0.5rem 0;
        font-size: 1.8rem;
    }
    
    .stats-info {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.875rem;
        color: #6b7280;
        justify-content: center;
    }
    
    .activity-header-centered {
        text-align: center;
        margin: 2rem 0 1.5rem 0;
    }
    
    .activity-header-centered h2 {
        margin: 0 0 0.5rem 0;
        font-size: 1.8rem;
    }
    
    .activity-info {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.875rem;
        color: #6b7280;
        justify-content: center;
    }
    
    .refresh-controls {
        text-align: center;
        margin: 1rem 0;
        font-size: 0.875rem;
    }
    
    .refresh-controls > * {
        margin: 0 0.5rem;
        vertical-align: middle;
    }
    
    .refresh-btn {
        background: #2563eb;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.875rem;
        transition: all 0.2s;
        margin-left: 1rem;
    }
    
    .refresh-btn:hover:not(:disabled) {
        background: #1d4ed8;
    }
    
    .refresh-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
    
    .last-updated {
        color: #6b7280;
        font-size: 0.875rem;
    }
    
    .update-indicator {
        font-size: 0.75rem;
        color: #6b7280;
    }
    
    /* ACTIVITY STYLING */
    .activity-item {
        padding: 0.75rem;
        border-bottom: 1px solid #e5e7eb;
        display: flex;
        gap: 1rem;
        align-items: flex-start;
    }
    
    .activity-item:last-child {
        border-bottom: none;
    }
    
    .activity-time {
        font-size: 0.75rem;
        color: #6b7280;
        min-width: 60px;
        flex-shrink: 0;
    }
    
    .activity-content {
        flex: 1;
        display: flex;
        gap: 0.5rem;
        align-items: center;
        flex-wrap: wrap;
    }
    
    .activity-type {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        padding: 0.2rem 0.5rem;
        border-radius: 3px;
        flex-shrink: 0;
    }
    
    .activity-type-connect { background: #dcfce7; color: #166534; }
    .activity-type-disconnect { background: #fee2e2; color: #dc2626; }
    .activity-type-query { background: #dbeafe; color: #1e40af; }
    .activity-type-request { background: #fef3c7; color: #92400e; }
    
    .activity-text {
        font-size: 0.875rem;
        color: #374151;
        flex: 1;
    }
    
    /* NIP badges */
    .nips-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 1rem 0;
    }
    
    .nip-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .nip-badge.basic { background: #dbeafe; color: #1e40af; }
    .nip-badge.auth { background: #fef3c7; color: #92400e; }
    .nip-badge.advanced { background: #e5e7eb; color: #374151; }
    .nip-badge.social { background: #fce7f3; color: #be185d; }
    
    /* Dark theme */
    [data-theme="dark"] .stats-info,
    [data-theme="dark"] .activity-info { color: #9ca3af; }
    [data-theme="dark"] .last-updated { color: #9ca3af; }
    [data-theme="dark"] .activity-item { border-color: #374151; }
    [data-theme="dark"] .activity-time { color: #9ca3af; }
    [data-theme="dark"] .activity-text { color: #d1d5db; }
    [data-theme="dark"] .activity-type-connect { background: #166534; color: #dcfce7; }
    [data-theme="dark"] .activity-type-disconnect { background: #dc2626; color: #fee2e2; }
    [data-theme="dark"] .activity-type-query { background: #1e40af; color: #dbeafe; }
    [data-theme="dark"] .activity-type-request { background: #92400e; color: #fef3c7; }
    [data-theme="dark"] .nip-badge.basic { background: #1e40af; color: #dbeafe; }
    [data-theme="dark"] .nip-badge.auth { background: #92400e; color: #fef3c7; }
    [data-theme="dark"] .nip-badge.advanced { background: #374151; color: #e5e7eb; }
    [data-theme="dark"] .nip-badge.social { background: #be185d; color: #fce7f3; }
`;
document.head.appendChild(style);
