// Common site configuration and branding
class SiteConfig {
    constructor() {
        this.config = null;
        this.init();
    }

    async init() {
        await this.loadConfig();
        this.updateSiteBranding();
        this.updateFooter();
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            if (response.ok) {
                this.config = await response.json();
            } else {
                console.warn('Failed to load site config, using defaults');
                this.config = {
                    site_name: 'Nostr Home',
                    site_subtitle: 'Your Decentralized Content',
                    npub: ''
                };
            }
        } catch (error) {
            console.warn('Error loading site config:', error);
            this.config = {
                site_name: 'Nostr Home',
                site_subtitle: 'Your Decentralized Content',
                npub: ''
            };
        }
    }

    updateSiteBranding() {
        if (!this.config) return;

        // Update site name in navigation
        const navBrandElements = document.querySelectorAll('.nav-brand h1');
        navBrandElements.forEach(element => {
            element.textContent = this.config.site_name;
        });

        // Update page titles
        const currentTitle = document.title;
        if (currentTitle.includes('Nostr Home')) {
            document.title = currentTitle.replace('Nostr Home', this.config.site_name);
        }

        // Update hero title on index page
        const heroTitle = document.querySelector('.hero-title');
        if (heroTitle && heroTitle.textContent.includes('Your Nostr Content')) {
            heroTitle.textContent = `Your ${this.config.site_name.replace('Nostr ', '')} Content, Beautifully Displayed`;
        }

        // Update hero subtitle
        const heroSubtitle = document.querySelector('.hero-subtitle');
        if (heroSubtitle && heroSubtitle.textContent.includes('A decentralized blog')) {
            heroSubtitle.textContent = this.config.site_subtitle;
        }
    }

    updateFooter() {
        if (!this.config) return;

        // Find all footer paragraphs and update them
        const footerElements = document.querySelectorAll('footer p, .footer p');
        footerElements.forEach(element => {
            if (element.textContent.includes('© 2024 Nostr Home')) {
                element.innerHTML = `© 2025 ${this.config.site_name}. Powered by Nostr protocol and Created by <a href="https://pleb.one" target="_blank" rel="noopener noreferrer" class="footer-link">PlebOne</a>`;
            }
        });

        // Also check for any element that might contain the old footer text
        const allElements = document.querySelectorAll('*');
        allElements.forEach(element => {
            if (element.children.length === 0 && element.textContent.includes('© 2024 Nostr Home')) {
                element.innerHTML = `© 2025 ${this.config.site_name}. Powered by Nostr protocol and Created by <a href="https://pleb.one" target="_blank" rel="noopener noreferrer" class="footer-link">PlebOne</a>`;
            }
        });
    }

    getSiteName() {
        return this.config ? this.config.site_name : 'Nostr Home';
    }

    getSiteSubtitle() {
        return this.config ? this.config.site_subtitle : 'Your Decentralized Content';
    }
}

// Initialize site config when DOM is loaded
let siteConfig;
document.addEventListener('DOMContentLoaded', () => {
    siteConfig = new SiteConfig();
});

// Export for use in other scripts
window.SiteConfig = SiteConfig;
