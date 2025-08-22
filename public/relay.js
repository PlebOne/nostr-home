// Relay page JavaScript functionality
class RelayDashboard {
    constructor() {
        this.wsConnection = null;
        this.statsUpdateInterval = null;
        this.activityUpdateInterval = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.init();
    }

    init() {
        this.loadNIPsList();
        this.startStatsUpdates();
        this.startActivityUpdates();
        this.checkRelayStatus();
        this.updateConnectionUrls();
    }

    updateConnectionUrls() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        
        document.getElementById('websocket-url').textContent = `${protocol}//${host}/ws`;
        document.getElementById('http-url').textContent = `${window.location.protocol}//${host}/api`;
    }

    async checkRelayStatus() {
        const statusIndicator = document.getElementById('relay-status');
        const statusDot = statusIndicator.querySelector('.status-dot');
        const statusText = statusIndicator.querySelector('.status-text');

        try {
            const response = await fetch('/api/relay/info');
            if (response.ok) {
                const data = await response.json();
                statusDot.className = 'status-dot online';
                statusText.textContent = `Online - ${data.name || 'Enhanced Nostr Relay'}`;
                
                // Update description and features based on relay info
                this.updateRelayDescription(data);
            } else {
                throw new Error('Relay not responding');
            }
        } catch (error) {
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'Offline';
        }
    }

    updateRelayDescription(relayInfo) {
        // Update description
        const descriptionElement = document.getElementById('relay-description');
        if (descriptionElement && relayInfo.description) {
            descriptionElement.textContent = relayInfo.description;
        }

        // Show owner-only feature if restricted writes are enabled
        if (relayInfo.limitation && relayInfo.limitation.restricted_writes) {
            const ownerOnlyFeature = document.getElementById('owner-only-feature');
            if (ownerOnlyFeature) {
                ownerOnlyFeature.style.display = 'list-item';
            }
        }
    }

    async loadNIPsList() {
        const nipsContainer = document.getElementById('nips-list');
        
        try {
            const response = await fetch('/api/relay/nips');
            if (response.ok) {
                const data = await response.json();
                this.renderNIPs(data.nips || [], nipsContainer);
            } else {
                // Fallback to known NIPs
                const fallbackNIPs = [1, 2, 3, 4, 5, 9, 10, 11, 12, 13, 15, 16, 20, 22, 25, 26, 28, 33, 40, 42, 45, 50, 65];
                this.renderNIPs(fallbackNIPs, nipsContainer);
            }
        } catch (error) {
            nipsContainer.innerHTML = '<p class="error">Failed to load NIPs information</p>';
        }
    }

    renderNIPs(nips, container) {
        const nipDescriptions = {
            1: { title: 'Basic Protocol', desc: 'Basic protocol flow', category: 'basic' },
            2: { title: 'Contact List', desc: 'Contact list and petnames', category: 'social' },
            3: { title: 'Address Book', desc: 'OpenTimestamps attestations', category: 'basic' },
            4: { title: 'Encrypted DMs', desc: 'Encrypted direct messages', category: 'auth' },
            5: { title: 'Event Deletion', desc: 'Event deletion requests', category: 'advanced' },
            9: { title: 'Event Deletion', desc: 'Event deletion', category: 'advanced' },
            10: { title: 'Conventions', desc: 'On "e" and "p" tags', category: 'basic' },
            11: { title: 'Relay Info', desc: 'Relay information document', category: 'basic' },
            12: { title: 'Generic Tags', desc: 'Generic tag queries', category: 'advanced' },
            13: { title: 'Proof of Work', desc: 'Proof of work', category: 'auth' },
            15: { title: 'Marketplace', desc: 'End of stored events notice', category: 'advanced' },
            16: { title: 'Replaceable Events', desc: 'Event treatment', category: 'advanced' },
            20: { title: 'Command Results', desc: 'Command results', category: 'advanced' },
            22: { title: 'Event Created At', desc: 'Event created_at limits', category: 'basic' },
            25: { title: 'Reactions', desc: 'Reactions', category: 'social' },
            26: { title: 'Delegated Events', desc: 'Delegated event signing', category: 'auth' },
            28: { title: 'Public Chat', desc: 'Public chat', category: 'social' },
            33: { title: 'Parameterized Replaceable Events', desc: 'Parameterized replaceable events', category: 'advanced' },
            40: { title: 'Expiration', desc: 'Expiration timestamp', category: 'advanced' },
            42: { title: 'Authentication', desc: 'Authentication of clients to relays', category: 'auth' },
            45: { title: 'Event Counts', desc: 'Counting results', category: 'advanced' },
            50: { title: 'Search', desc: 'Search capability', category: 'advanced' },
            65: { title: 'Relay List', desc: 'Relay list metadata', category: 'basic' }
        };

        const nipElements = nips.map(nipNumber => {
            const nip = nipDescriptions[nipNumber] || { 
                title: `NIP-${nipNumber}`, 
                desc: 'Advanced feature', 
                category: 'advanced' 
            };
            
            return `
                <div class="nip-item">
                    <div class="nip-header">
                        <span class="nip-number">NIP-${nipNumber}</span>
                        <span class="nip-badge ${nip.category}">${nip.category}</span>
                    </div>
                    <div class="nip-title">${nip.title}</div>
                    <div class="nip-desc">${nip.desc}</div>
                </div>
            `;
        }).join('');

        container.innerHTML = nipElements;
    }

    async startStatsUpdates() {
        await this.updateStats();
        this.statsUpdateInterval = setInterval(() => {
            this.updateStats();
        }, 10000); // Update every 10 seconds
    }

    async updateStats() {
        try {
            const response = await fetch('/api/relay/stats');
            if (response.ok) {
                const stats = await response.json();
                this.renderStats(stats);
            }
        } catch (error) {
            console.error('Failed to update stats:', error);
        }
    }

    renderStats(stats) {
        const elements = {
            'total-events': stats.total_events || 0,
            'unique-pubkeys': stats.unique_pubkeys || 0,
            'websocket-connections': stats.active_connections || 0,
            'events-24h': stats.events_24h || 0
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                this.animateNumber(element, parseInt(value) || 0);
            }
        });
    }

    animateNumber(element, targetValue) {
        const currentValue = parseInt(element.textContent) || 0;
        const difference = targetValue - currentValue;
        const duration = 1000; // 1 second
        const steps = 60; // 60 FPS
        const stepValue = difference / steps;
        let currentStep = 0;

        const timer = setInterval(() => {
            currentStep++;
            const newValue = Math.round(currentValue + (stepValue * currentStep));
            element.textContent = newValue.toLocaleString();

            if (currentStep >= steps) {
                clearInterval(timer);
                element.textContent = targetValue.toLocaleString();
            }
        }, duration / steps);
    }

    async startActivityUpdates() {
        await this.updateActivity();
        this.activityUpdateInterval = setInterval(() => {
            this.updateActivity();
        }, 15000); // Update every 15 seconds
    }

    async updateActivity() {
        try {
            const response = await fetch('/api/relay/activity');
            if (response.ok) {
                const activity = await response.json();
                this.renderActivity(activity.recent || []);
            }
        } catch (error) {
            console.error('Failed to update activity:', error);
            // Show sample activity if API fails
            this.renderSampleActivity();
        }
    }

    renderActivity(activities) {
        const activityFeed = document.getElementById('activity-feed');
        
        if (activities.length === 0) {
            activityFeed.innerHTML = '<div class="activity-item"><div class="activity-content">No recent activity</div></div>';
            return;
        }

        const activityElements = activities.slice(0, 10).map(activity => {
            const timeAgo = this.formatTimeAgo(activity.timestamp);
            const kindName = this.getEventKindName(activity.kind);
            
            return `
                <div class="activity-item">
                    <div class="activity-time">${timeAgo}</div>
                    <div class="activity-content">
                        <span class="activity-kind">${kindName}</span> event from 
                        <span class="activity-pubkey">${this.truncateString(activity.pubkey, 16)}</span>
                    </div>
                </div>
            `;
        }).join('');

        activityFeed.innerHTML = activityElements;
    }

    renderSampleActivity() {
        const activityFeed = document.getElementById('activity-feed');
        const sampleActivities = [
            { kind: 1, pubkey: '8dc8688200b447ec2e4018ea5e42dc5d480940cb3f19ca8f361d28179dc4ba5e', timestamp: Date.now() - 30000 },
            { kind: 0, pubkey: 'abc123def456789012345678901234567890123456789012345678901234567890', timestamp: Date.now() - 120000 },
            { kind: 1, pubkey: 'def456abc123789012345678901234567890123456789012345678901234567890', timestamp: Date.now() - 300000 }
        ];

        this.renderActivity(sampleActivities);
    }

    formatTimeAgo(timestamp) {
        const now = Date.now();
        const diff = now - timestamp;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}d ago`;
        if (hours > 0) return `${hours}h ago`;
        if (minutes > 0) return `${minutes}m ago`;
        return `${seconds}s ago`;
    }

    getEventKindName(kind) {
        const kindNames = {
            0: 'Profile',
            1: 'Text Note',
            2: 'Relay Rec',
            3: 'Contacts',
            4: 'DM',
            5: 'Deletion',
            7: 'Reaction',
            40: 'Channel Create',
            41: 'Channel Meta',
            42: 'Channel Message'
        };
        return kindNames[kind] || `Kind ${kind}`;
    }

    truncateString(str, length) {
        if (str.length <= length) return str;
        return str.substring(0, length) + '...';
    }

    destroy() {
        if (this.statsUpdateInterval) {
            clearInterval(this.statsUpdateInterval);
        }
        if (this.activityUpdateInterval) {
            clearInterval(this.activityUpdateInterval);
        }
        if (this.wsConnection) {
            this.wsConnection.close();
        }
    }
}

// Initialize the dashboard when the page loads
let relayDashboard;
document.addEventListener('DOMContentLoaded', () => {
    relayDashboard = new RelayDashboard();
});

// Cleanup when leaving the page
window.addEventListener('beforeunload', () => {
    if (relayDashboard) {
        relayDashboard.destroy();
    }
});
