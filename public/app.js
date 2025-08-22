// Main application JavaScript
class NostrHome {
    constructor() {
        this.currentPage = 1;
        this.init();
    }

    async init() {
        await this.loadStats();
        await this.loadPreviewContent();
    }

    // Load statistics
    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            
            document.getElementById('posts-count').textContent = stats.posts || 0;
            document.getElementById('quips-count').textContent = stats.quips || 0;
            document.getElementById('images-count').textContent = stats.images || 0;
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    // Load preview content
    async loadPreviewContent() {
        await Promise.all([
            this.loadLatestPosts(),
            this.loadLatestQuips(),
            this.loadLatestImages()
        ]);
    }

    // Load latest posts
    async loadLatestPosts() {
        try {
            const response = await fetch('/api/posts?page=1');
            const data = await response.json();
            const container = document.getElementById('latest-posts');
            
            if (data.posts && data.posts.length > 0) {
                container.innerHTML = data.posts.slice(0, 3).map(post => {
                    const title = this.extractTitle(post);
                    const featuredImage = this.extractFeaturedImage(post.content, post.tags);
                    const excerpt = this.extractExcerpt(post.content, 100);
                    
                    return `
                        <div class="preview-post-item" onclick="window.location.href='/post?id=${post.id}'">
                            ${featuredImage ? `<div class="preview-thumbnail">
                                <img src="${featuredImage.url}" alt="${featuredImage.alt}" class="preview-image" loading="lazy">
                            </div>` : ''}
                            <div class="preview-content">
                                <h3 class="preview-title">${title || 'Untitled Post'}</h3>
                                <p class="preview-excerpt">${excerpt}</p>
                                <div class="preview-meta">${this.formatDate(post.created_at)}</div>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                container.innerHTML = '<div class="content-item">No posts yet</div>';
            }
        } catch (error) {
            console.error('Error loading latest posts:', error);
            document.getElementById('latest-posts').innerHTML = '<div class="content-item">Error loading posts</div>';
        }
    }

    // Load latest quips
    async loadLatestQuips() {
        try {
            const response = await fetch('/api/quips?page=1');
            const data = await response.json();
            const container = document.getElementById('latest-quips');
            
            if (data.quips && data.quips.length > 0) {
                container.innerHTML = data.quips.slice(0, 5).map(quip => `
                    <div class="content-item">
                        <div class="content-text">${this.truncateText(quip.content, 100)}</div>
                        <div class="content-meta">${this.formatDate(quip.created_at)}</div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<div class="content-item">No quips yet</div>';
            }
        } catch (error) {
            console.error('Error loading latest quips:', error);
            document.getElementById('latest-quips').innerHTML = '<div class="content-item">Error loading quips</div>';
        }
    }

    // Load latest images
    async loadLatestImages() {
        try {
            const response = await fetch('/api/images?page=1');
            const data = await response.json();
            const container = document.getElementById('latest-images');
            
            if (data.images && data.images.length > 0) {
                container.innerHTML = data.images.slice(0, 3).map(image => `
                    <div class="content-item">
                        <div class="preview-thumbnail">
                            <img src="${image.image_url}" alt="Preview" class="preview-image" loading="lazy" 
                                 onerror="this.style.display='none'; this.parentNode.innerHTML='<div style=&quot;padding: 1rem; text-align: center; color: var(--text-muted); font-size: 0.8rem;&quot;>Image unavailable</div>';">
                        </div>
                        <div class="content-meta">${this.formatDate(image.created_at)}</div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<div class="content-item">No images yet</div>';
            }
        } catch (error) {
            console.error('Error loading latest images:', error);
            document.getElementById('latest-images').innerHTML = '<div class="content-item">Error loading images</div>';
        }
    }

    // Helper methods for post preview
    extractTitle(post) {
        // Extract title from tags (NIP-23 style)
        if (post.tags) {
            for (const tag of post.tags) {
                if (tag[0] === 'title' && tag[1]) {
                    return this.escapeHtml(tag[1]);
                }
            }
        }
        return null;
    }

    extractFeaturedImage(content, tags = []) {
        // Extract the first image from content or tags for featured image
        
        // First check tags for image tag (NIP-23 style)
        if (tags && Array.isArray(tags)) {
            for (const tag of tags) {
                if (Array.isArray(tag) && tag[0] === 'image' && tag[1]) {
                    const url = tag[1];
                    // Skip local file paths
                    if (!url.startsWith('/home/') && !url.startsWith('file://') && 
                        !url.startsWith('/Users/') && !url.startsWith('C:\\')) {
                        return { url, alt: 'Featured image' };
                    }
                }
            }
        }
        
        // Then try to find markdown images ![alt](url)
        const markdownImageMatch = content.match(/!\[([^\]]*)\]\(([^)]+)\)/);
        if (markdownImageMatch) {
            const url = markdownImageMatch[2];
            const alt = markdownImageMatch[1] || 'Featured image';
            
            // Skip local file paths
            if (!url.startsWith('/home/') && !url.startsWith('file://') && 
                !url.startsWith('/Users/') && !url.startsWith('C:\\')) {
                return { url, alt };
            }
        }
        
        // Then try to find plain HTTP image URLs
        const httpImageMatch = content.match(/(https?:\/\/[^\s<>"']+\.(jpg|jpeg|png|gif|webp|svg|bmp|tiff)(\?[^\s<>"']*)?)/i);
        if (httpImageMatch) {
            return { url: httpImageMatch[1], alt: 'Featured image' };
        }
        
        return null;
    }

    extractExcerpt(content, maxLength = 100) {
        // Remove markdown formatting and get plain text excerpt
        let text = content
            .replace(/!\[([^\]]*)\]\([^)]+\)/g, '') // Remove images
            .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Convert links to text
            .replace(/[#*`_]/g, '') // Remove markdown formatting
            .replace(/\n+/g, ' ') // Replace line breaks with spaces
            .trim();
        
        if (text.length > maxLength) {
            text = text.substring(0, maxLength) + '...';
        }
        
        return this.escapeHtml(text);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Utility functions
    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
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
            return date.toLocaleDateString();
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
            document.documentElement.setAttribute('data-theme', 'dark');
            this.updateToggleIcon('☀️');
        } else {
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

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new NostrHome();
    new ThemeManager();
});
