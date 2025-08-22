// Individual post page functionality
class PostPage {
    constructor() {
        this.postId = null;
        this.init();
    }

    async init() {
        // Get post ID from URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        this.postId = urlParams.get('id');
        
        if (!this.postId) {
            this.showError('No post ID provided');
            return;
        }
        
        await this.loadPost();
    }

    async loadPost() {
        try {
            const container = document.getElementById('post-container');
            container.innerHTML = '<div class="loading">Loading post...</div>';

            const response = await fetch(`/api/posts/${this.postId}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    this.showError('Post not found');
                } else {
                    this.showError('Failed to load post');
                }
                return;
            }
            
            const post = await response.json();
            this.renderPost(post);
            
        } catch (error) {
            console.error('Error loading post:', error);
            this.showError('Error loading post. Please try again.');
        }
    }

    renderPost(post) {
        const container = document.getElementById('post-container');
        const title = this.extractTitle(post);
        const featuredImage = this.extractFeaturedImage(post.content, post.tags);
        
        // Update page title
        if (title) {
            document.title = `${title} - Nostr Home`;
        }
        
        container.innerHTML = `
            ${featuredImage ? `<div class="single-post-featured-image">
                <img src="${featuredImage.url}" alt="${featuredImage.alt}" class="single-featured-image" loading="lazy">
            </div>` : ''}
            
            ${title ? `<h1 class="single-post-title">${title}</h1>` : ''}
            
            <div class="single-post-meta">
                <span class="post-date">${this.formatDate(post.created_at)}</span>
                <span class="post-kind">Kind: ${post.kind || 1}</span>
                <span class="post-id">ID: ${post.id.substring(0, 16)}...</span>
                <a href="${this.getNostrLink(post)}" target="_blank" rel="noopener noreferrer" class="nostr-link">
                    View on Nostr
                </a>
            </div>
            
            <div class="single-post-content">${this.formatContent(post.content, title, featuredImage)}</div>
        `;
    }

    showError(message) {
        const container = document.getElementById('post-container');
        container.innerHTML = `
            <div class="error-message">
                <h2>Error</h2>
                <p>${message}</p>
                <a href="/posts" class="error-back-link">← Back to Posts</a>
            </div>
        `;
    }

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

    formatContent(content, title = null, featuredImage = null) {
        let formatted = content;
        
        // Remove title from content if it appears at the beginning
        if (title) {
            const plainTitle = title.replace(/<[^>]*>/g, ''); // Remove HTML tags for comparison
            if (formatted.startsWith(plainTitle)) {
                formatted = formatted.substring(plainTitle.length).trim();
            }
        }
        
        // Remove featured image from content if it exists
        if (featuredImage) {
            // Remove markdown image format: ![alt](url)
            const markdownImageRegex = new RegExp(`!\\[[^\\]]*\\]\\(\\s*${featuredImage.url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\)`, 'g');
            formatted = formatted.replace(markdownImageRegex, '').trim();
            
            // Remove plain URL if it appears on its own line
            const plainUrlRegex = new RegExp(`^\\s*${featuredImage.url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*$`, 'gm');
            formatted = formatted.replace(plainUrlRegex, '').trim();
            
            // Clean up any double line breaks left behind
            formatted = formatted.replace(/\n\n\n+/g, '\n\n');
        }
        
        // Convert markdown formatting FIRST (before HTML escaping)
        formatted = this.renderMarkdown(formatted);
        
        // Convert URLs to clickable links (after markdown to avoid conflicts)
        formatted = this.linkifyUrls(formatted);
        
        // Now escape any remaining HTML that isn't our generated tags
        formatted = this.escapeRemainingHtml(formatted);
        
        // Convert line breaks to HTML
        formatted = formatted.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
        
        // Wrap in paragraphs if not already wrapped
        if (!formatted.startsWith('<')) {
            formatted = `<p>${formatted}</p>`;
        }
        
        return formatted;
    }

    renderMarkdown(content) {
        let formatted = content;
        
        // Images first (before links to avoid conflicts)
        // ![alt text](url) format
        formatted = formatted.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, url) => {
            const safeAlt = this.escapeHtml(alt);
            if (this.isImageUrl(url)) {
                // Skip local file paths and show placeholder
                if (url.startsWith('/home/') || url.startsWith('file://') || 
                    url.startsWith('/Users/') || url.startsWith('C:\\')) {
                    return `<div class="local-image-placeholder">[Local Image: ${safeAlt || 'Image'}]</div>`;
                }
                return `<img src="${url}" alt="${safeAlt}" class="content-image" loading="lazy">`;
            }
            return match;
        });
        
        // Links [text](url) format (after images to avoid conflicts)
        formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
            const safeText = this.escapeHtml(text);
            return `<a href="${url}" target="_blank" rel="noopener noreferrer">${safeText}</a>`;
        });
        
        // Headers (# ## ###)
        formatted = formatted.replace(/^### (.*$)/gm, '<h3>$1</h3>');
        formatted = formatted.replace(/^## (.*$)/gm, '<h2>$1</h2>');
        formatted = formatted.replace(/^# (.*$)/gm, '<h1>$1</h1>');
        
        // Bold **text**
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Italic *text*
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Code blocks ```code```
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        
        // Inline code `code`
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        return formatted;
    }

    linkifyUrls(content) {
        const urlRegex = /(https?:\/\/[^\s<>"'()]+(?:\([^\s<>"']*\))*[^\s<>"'().,!?;:])/g;
        return content.replace(urlRegex, (url) => {
            // Don't linkify if already inside an HTML tag
            return `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
        });
    }

    escapeRemainingHtml(content) {
        // Only escape HTML that's not our generated tags
        const protectedTags = /<(\/?)(?:h[1-6]|p|a|strong|em|code|pre|img|br|div)(?:\s[^>]*)?>|<\/(?:h[1-6]|p|a|strong|em|code|pre|img|br|div)>/gi;
        const protectedContent = [];
        let index = 0;
        
        // Store protected HTML tags
        content = content.replace(protectedTags, (match) => {
            const placeholder = `__PROTECTED_${index}__`;
            protectedContent[index] = match;
            index++;
            return placeholder;
        });
        
        // Escape remaining HTML
        content = content.replace(/</g, '&lt;').replace(/>/g, '&gt;');
        
        // Restore protected tags
        protectedContent.forEach((tag, i) => {
            content = content.replace(`__PROTECTED_${i}__`, tag);
        });
        
        return content;
    }

    isImageUrl(url) {
        const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff'];
        const lowerUrl = url.toLowerCase();
        return imageExtensions.some(ext => lowerUrl.includes(ext));
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getNostrLink(post) {
        // Create a link to view the original Nostr post
        // The id field is the Nostr event ID which can be converted to note format
        if (post.id) {
            return `https://njump.me/${post.id}`;
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

// Initialize the post page
document.addEventListener('DOMContentLoaded', () => {
    new PostPage();
    new ThemeManager();
});
