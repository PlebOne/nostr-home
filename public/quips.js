// Quips page functionality
class QuipsPage {
    constructor() {
        this.currentPage = 1;
        this.hasMore = false;
        this.totalPages = 0;
        this.init();
    }

    async init() {
        await this.loadQuips();
    }

    async loadQuips() {
        try {
            const container = document.getElementById('quips-container');
            container.innerHTML = '<div class="loading">Loading quips...</div>';

            const response = await fetch(`/api/quips?page=${this.currentPage}`);
            const data = await response.json();

            if (data.quips && data.quips.length > 0) {
                container.innerHTML = data.quips.map(quip => `
                    <article class="quip-item">
                        <div class="quip-content">${this.formatContent(quip.content)}</div>
                        <div class="quip-meta">
                            <span>${this.formatDate(quip.created_at)}</span>
                            <span>ID: ${quip.id.substring(0, 8)}...</span>
                            <a href="${this.getNostrLink(quip)}" target="_blank" rel="noopener noreferrer" class="nostr-link">
                                View on Nostr
                            </a>
                        </div>
                    </article>
                `).join('');

                this.hasMore = data.hasMore;
                this.totalPages = data.totalPages || 0;
                this.updatePagination();
            } else {
                container.innerHTML = '<div class="loading">No quips found</div>';
                this.hasMore = false;
                this.totalPages = 0;
                this.updatePagination();
            }
        } catch (error) {
            console.error('Error loading quips:', error);
            document.getElementById('quips-container').innerHTML = 
                '<div class="loading">Error loading quips. Please try again.</div>';
        }
    }

    updatePagination() {
        const pagination = document.getElementById('pagination');
        const prevButton = document.getElementById('prev-page');
        const nextButton = document.getElementById('next-page');
        const pageInfo = document.getElementById('page-info');

        if (this.totalPages <= 1) {
            pagination.style.display = 'none';
            return;
        }

        pagination.style.display = 'flex';
        prevButton.disabled = this.currentPage === 1;
        nextButton.disabled = this.currentPage >= this.totalPages;
        pageInfo.textContent = `Page ${this.currentPage} of ${this.totalPages}`;
    }

    async nextPage() {
        if (this.currentPage < this.totalPages) {
            this.currentPage++;
            await this.loadQuips();
        }
    }

    async previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            await this.loadQuips();
        }
    }

    formatContent(content) {
        // Convert URLs to clickable links with better regex to avoid capturing trailing punctuation
        const urlRegex = /(https?:\/\/[^\s<>"'\]\)]+)/g;
        return content.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    }

    getNostrLink(quip) {
        // Create a link to view the original Nostr post
        // The id field is the Nostr event ID which can be converted to note format
        if (quip.id) {
            return `https://njump.me/${quip.id}`;
        }
        return '#';
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffInHours = (now - date) / (1000 * 60 * 60);
        
        if (diffInHours < 1) {
            return 'Just now';
        } else if (diffInHours < 24) {
            const hours = Math.floor(diffInHours);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else if (diffInHours < 168) { // 7 days
            const days = Math.floor(diffInHours / 24);
            return `${days} day${days > 1 ? 's' : ''} ago`;
        } else {
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
    }
}

// Theme management
class ThemeManager {
    constructor() {
        this.init();
    }

    init() {
        // Check for saved theme or default to light
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.setTheme(savedTheme);
        
        // Set up theme toggle button
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    setTheme(theme) {
        if (theme === 'dark') {
            document.documentElement.classList.add('theme-transition');
            document.documentElement.setAttribute('data-theme', 'dark');
            this.updateToggleIcon('☀️');
        } else {
            document.documentElement.classList.add('theme-transition');
            document.documentElement.removeAttribute('data-theme');
            this.updateToggleIcon('🌙');
        }
        localStorage.setItem('theme', theme);
    }

    toggleTheme() {
        const currentTheme = localStorage.getItem('theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }

    updateToggleIcon(icon) {
        const themeIcon = document.querySelector('.theme-icon');
        if (themeIcon) {
            themeIcon.textContent = icon;
        }
    }
}

// Initialize the quips page
document.addEventListener('DOMContentLoaded', () => {
    window.quipsPage = new QuipsPage();
    new ThemeManager();
});
