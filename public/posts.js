// Posts page functionality
class PostsPage {
    constructor() {
        this.currentPage = 1;
        this.hasMore = false;
        this.totalPages = 0;
        this.init();
    }

    async init() {
        await this.loadPosts();
    }

    async loadPosts() {
        try {
            const container = document.getElementById('posts-container');
            container.innerHTML = '<div class="loading">Loading posts...</div>';

            const response = await fetch(`/api/posts?page=${this.currentPage}`);
            const data = await response.json();

            if (data.posts && data.posts.length > 0) {
                container.innerHTML = data.posts.map(post => {
                    const title = this.extractTitle(post);
                    const featuredImage = this.extractFeaturedImage(post.content, post.tags);
                    const excerpt = this.extractExcerpt(post.content, 120);
                    
                    return `
                        <article class="post-list-item" data-post-id="${post.id}">
                            <div class="post-list-content">
                                ${featuredImage ? `<div class="post-thumbnail">
                                    <img src="${featuredImage.url}" alt="${featuredImage.alt}" class="thumbnail-image" loading="lazy">
                                </div>` : ''}
                                <div class="post-info">
                                    <h2 class="post-list-title">${title || 'Untitled Post'}</h2>
                                    <p class="post-excerpt">${excerpt}</p>
                                    <div class="post-meta">
                                        <span class="post-date">${this.formatDate(post.created_at)}</span>
                                        <span class="post-kind">Kind: ${post.kind || 1}</span>
                                        <a href="${this.getNostrLink(post)}" target="_blank" rel="noopener noreferrer" class="nostr-link">
                                            View on Nostr
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </article>
                    `;
                }).join('');

                this.hasMore = data.hasMore;
                this.totalPages = data.totalPages || 0;
                this.updatePagination();
                this.attachClickHandlers();
            } else {
                container.innerHTML = '<div class="loading">No posts found</div>';
                this.hasMore = false;
                this.totalPages = 0;
                this.updatePagination();
            }
        } catch (error) {
            console.error('Error loading posts:', error);
            document.getElementById('posts-container').innerHTML = 
                '<div class="loading">Error loading posts. Please try again.</div>';
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
            await this.loadPosts();
        }
    }

    async previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            await this.loadPosts();
        }
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

    extractExcerpt(content, maxLength = 120) {
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

    attachClickHandlers() {
        const postItems = document.querySelectorAll('.post-list-item');
        postItems.forEach(item => {
            item.style.cursor = 'pointer';
            item.addEventListener('click', (e) => {
                const postId = e.currentTarget.dataset.postId;
                if (postId) {
                    this.openPost(postId);
                }
            });
        });
    }

    openPost(postId) {
        // Navigate to individual post view
        window.location.href = `/post?id=${postId}`;
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
            
            // Skip local file paths
            if (url.startsWith('/home/') || url.startsWith('file://') || url.startsWith('/Users/') || url.startsWith('C:\\')) {
                return `<div class="local-image-placeholder">
                    <span class="local-image-icon">🖼️</span>
                    <span class="local-image-text">Local image: ${safeAlt || 'Image'}</span>
                </div>`;
            }
            
            return `<img src="${url}" alt="${safeAlt}" class="post-image" loading="lazy">`;
        });
        
        // Markdown links [text](url)
        formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
            // Check if it's an image link
            if (/\.(jpg|jpeg|png|gif|webp|svg|bmp|tiff)(\?.*)?$/i.test(url)) {
                const safeAlt = this.escapeHtml(text);
                return `<img src="${url}" alt="${safeAlt}" class="post-image" loading="lazy">`;
            }
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
        formatted = formatted.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');
        
        // Code `code`
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Code blocks ```
        formatted = formatted.replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>');
        
        // Lists (basic support)
        formatted = formatted.replace(/^[\*\-\+] (.*$)/gm, '<li>$1</li>');
        formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        
        // Numbered lists
        formatted = formatted.replace(/^\d+\. (.*$)/gm, '<li>$1</li>');
        
        // Blockquotes
        formatted = formatted.replace(/^> (.*$)/gm, '<blockquote>$1</blockquote>');
        
        return formatted;
    }

    linkifyUrls(content) {
        // First, let's find all existing HTML tags and mark their positions
        const htmlTagRegex = /<[^>]+>/g;
        const htmlRanges = [];
        let match;
        
        while ((match = htmlTagRegex.exec(content)) !== null) {
            htmlRanges.push({
                start: match.index,
                end: match.index + match[0].length
            });
        }
        
        // Function to check if a position is inside an HTML tag
        const isInsideHtmlTag = (pos) => {
            return htmlRanges.some(range => pos >= range.start && pos < range.end);
        };
        
        // Now find URLs that are NOT inside HTML tags
        const urlRegex = /(https?:\/\/[^\s<>"']+)/g;
        let result = content;
        const urlMatches = [];
        
        while ((match = urlRegex.exec(content)) !== null) {
            // Check if this URL is inside an HTML tag
            if (!isInsideHtmlTag(match.index)) {
                urlMatches.push({
                    match: match[0],
                    url: match[1],
                    start: match.index,
                    end: match.index + match[0].length
                });
            }
        }
        
        // Replace URLs from end to start to avoid position shifts
        urlMatches.reverse().forEach(urlMatch => {
            const { match, url, start, end } = urlMatch;
            let replacement;
            
            // Check if it's a local file path
            if (url.startsWith('/home/') || url.startsWith('file://') || url.startsWith('/Users/') || url.startsWith('C:\\')) {
                // Skip local file paths - just leave as text
                replacement = url;
            }
            // Check if it's an image URL
            else if (this.isImageUrl(url)) {
                replacement = `<img src="${url}" alt="Image" class="post-image" loading="lazy">`;
            } else {
                replacement = `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
            }
            
            result = result.substring(0, start) + replacement + result.substring(end);
        });
        
        return result;
    }

    isImageUrl(url) {
        const imageExtensions = /\.(jpg|jpeg|png|gif|webp|svg|bmp|tiff)(\?.*)?$/i;
        return imageExtensions.test(url);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    escapeRemainingHtml(content) {
        // This function escapes HTML outside of our generated tags
        // Split by our generated tags and escape the text parts
        const parts = content.split(/(<[^>]+>)/g);
        return parts.map(part => {
            // If it's an HTML tag we generated, leave it alone
            if (part.startsWith('<') && part.endsWith('>')) {
                return part;
            }
            // Otherwise, escape any HTML characters
            return part.replace(/[<>&"']/g, function(match) {
                return {'<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&#39;'}[match];
            });
        }).join('');
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

// Initialize the posts page
document.addEventListener('DOMContentLoaded', () => {
    window.postsPage = new PostsPage();
    new ThemeManager();
});
