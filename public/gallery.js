// Gallery page functionality
class GalleryPage {
    constructor() {
        this.currentPage = 1;
        this.hasMore = false;
        this.allImages = []; // Store all loaded images for lightbox navigation
        this.currentLightboxIndex = 0;
        this.init();
    }

    async init() {
        await this.loadImages();
        this.setupLightbox();
    }

    async loadImages() {
        try {
            const container = document.getElementById('gallery-container');
            container.innerHTML = '<div class="loading">Loading images...</div>';

            const response = await fetch(`/api/images?page=${this.currentPage}`);
            const data = await response.json();

            if (data.images && data.images.length > 0) {
                // Store images for lightbox navigation
                if (this.currentPage === 1) {
                    this.allImages = [...data.images];
                } else {
                    this.allImages.push(...data.images);
                }

                container.innerHTML = data.images.map((image, index) => `
                    <article class="image-item" data-image-index="${this.allImages.length - data.images.length + index}">
                        <div class="image-container">
                            <img src="${image.image_url}" alt="Nostr image" loading="lazy" 
                                 onclick="galleryPage.openLightbox(${this.allImages.length - data.images.length + index})"
                                 style="cursor: pointer;"
                                 onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                            <div class="image-error" style="display: none; padding: 2rem; text-align: center; color: #6b7280;">
                                Image unavailable
                            </div>
                        </div>
                        <div class="image-meta">
                            <span class="image-date">${this.formatDate(image.created_at)}</span>
                            <a href="${this.getNostrLink(image)}" target="_blank" rel="noopener noreferrer" class="nostr-link">
                                View on Nostr
                            </a>
                        </div>
                    </article>
                `).join('');

                this.hasMore = data.hasMore;
                this.updatePagination();
            } else {
                container.innerHTML = '<div class="loading">No images found</div>';
                this.hasMore = false;
                this.updatePagination();
            }
        } catch (error) {
            console.error('Error loading images:', error);
            document.getElementById('gallery-container').innerHTML = 
                '<div class="loading">Error loading images. Please try again.</div>';
        }
    }

    updatePagination() {
        const pagination = document.getElementById('pagination');
        const prevButton = document.getElementById('prev-page');
        const nextButton = document.getElementById('next-page');
        const pageInfo = document.getElementById('page-info');

        if (this.currentPage === 1 && !this.hasMore) {
            pagination.style.display = 'none';
            return;
        }

        pagination.style.display = 'flex';
        prevButton.disabled = this.currentPage === 1;
        nextButton.disabled = !this.hasMore;
        pageInfo.textContent = `Page ${this.currentPage}`;
    }

    async nextPage() {
        if (this.hasMore) {
            this.currentPage++;
            await this.loadImages();
        }
    }

    async previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            await this.loadImages();
        }
    }

    formatContent(content) {
        // Convert URLs to clickable links (excluding the image URL)
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        return content.replace(urlRegex, (match) => {
            // Don't make image URLs clickable since they're already displayed
            if (match.match(/\.(jpg|jpeg|png|gif|webp|svg)$/i)) {
                return match;
            }
            return `<a href="${match}" target="_blank" rel="noopener noreferrer">${match}</a>`;
        });
    }

    getNostrLink(item) {
        // Create a link to view the original Nostr post
        // The id field is the Nostr event ID which can be converted to note format
        if (item.id) {
            return `https://njump.me/${item.id}`;
        }
        return '#';
    }

    setupLightbox() {
        // Create lightbox HTML if it doesn't exist
        if (!document.getElementById('lightbox')) {
            const lightboxHTML = `
                <div id="lightbox" class="lightbox" style="display: none;">
                    <div class="lightbox-overlay" onclick="galleryPage.closeLightbox()"></div>
                    <div class="lightbox-content">
                        <button class="lightbox-close" onclick="galleryPage.closeLightbox()">&times;</button>
                        <button class="lightbox-prev" onclick="galleryPage.prevImage()">&#8249;</button>
                        <button class="lightbox-next" onclick="galleryPage.nextImage()">&#8250;</button>
                        <img id="lightbox-image" src="" alt="Full size image">
                        <div class="lightbox-info">
                            <span id="lightbox-date"></span>
                            <a id="lightbox-nostr-link" href="#" target="_blank" rel="noopener noreferrer" class="nostr-link">
                                View on Nostr
                            </a>
                        </div>
                        <div class="lightbox-counter">
                            <span id="lightbox-counter-text">1 / 1</span>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', lightboxHTML);
        }

        // Setup keyboard navigation
        document.addEventListener('keydown', (e) => {
            const lightbox = document.getElementById('lightbox');
            if (lightbox.style.display === 'flex') {
                switch(e.key) {
                    case 'Escape':
                        this.closeLightbox();
                        break;
                    case 'ArrowLeft':
                        this.prevImage();
                        break;
                    case 'ArrowRight':
                        this.nextImage();
                        break;
                }
            }
        });
    }

    openLightbox(index) {
        this.currentLightboxIndex = index;
        const lightbox = document.getElementById('lightbox');
        const image = document.getElementById('lightbox-image');
        const dateElement = document.getElementById('lightbox-date');
        const nostrLink = document.getElementById('lightbox-nostr-link');
        const counter = document.getElementById('lightbox-counter-text');
        const prevBtn = document.querySelector('.lightbox-prev');
        const nextBtn = document.querySelector('.lightbox-next');

        const currentImage = this.allImages[index];
        
        image.src = currentImage.image_url;
        dateElement.textContent = this.formatDate(currentImage.created_at);
        nostrLink.href = this.getNostrLink(currentImage);
        counter.textContent = `${index + 1} / ${this.allImages.length}`;

        // Update navigation button states
        prevBtn.disabled = index === 0;
        nextBtn.disabled = index === this.allImages.length - 1;

        lightbox.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // Prevent scrolling
    }

    closeLightbox() {
        const lightbox = document.getElementById('lightbox');
        lightbox.style.display = 'none';
        document.body.style.overflow = 'auto'; // Restore scrolling
    }

    async nextImage() {
        if (this.currentLightboxIndex < this.allImages.length - 1) {
            this.openLightbox(this.currentLightboxIndex + 1);
        } else if (this.hasMore && this.currentLightboxIndex >= this.allImages.length - 3) {
            // Auto-load next page if we're near the end and there are more images
            await this.loadMoreImagesInBackground();
            if (this.currentLightboxIndex < this.allImages.length - 1) {
                this.openLightbox(this.currentLightboxIndex + 1);
            }
        }
    }

    async loadMoreImagesInBackground() {
        if (!this.hasMore) return;
        
        try {
            const nextPage = this.currentPage + 1;
            const response = await fetch(`/api/images?page=${nextPage}`);
            const data = await response.json();
            
            if (data.images && data.images.length > 0) {
                this.allImages.push(...data.images);
                this.currentPage = nextPage;
                this.hasMore = data.hasMore;
                
                // Update the gallery display as well
                const container = document.getElementById('gallery-container');
                const newImages = data.images.map((image, index) => `
                    <article class="image-item" data-image-index="${this.allImages.length - data.images.length + index}">
                        <div class="image-container">
                            <img src="${image.image_url}" alt="Nostr image" loading="lazy" 
                                 onclick="galleryPage.openLightbox(${this.allImages.length - data.images.length + index})"
                                 style="cursor: pointer;"
                                 onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                            <div class="image-error" style="display: none; padding: 2rem; text-align: center; color: #6b7280;">
                                Image unavailable
                            </div>
                        </div>
                        <div class="image-meta">
                            <span class="image-date">${this.formatDate(image.created_at)}</span>
                            <a href="${this.getNostrLink(image)}" target="_blank" rel="noopener noreferrer" class="nostr-link">
                                View on Nostr
                            </a>
                        </div>
                    </article>
                `).join('');
                
                container.insertAdjacentHTML('beforeend', newImages);
                this.updatePagination();
            }
        } catch (error) {
            console.error('Error loading more images:', error);
        }
    }

    prevImage() {
        if (this.currentLightboxIndex > 0) {
            this.openLightbox(this.currentLightboxIndex - 1);
        }
    }

    formatDate(timestamp) {
        // Handle both Unix timestamps and ISO strings
        const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp * 1000);
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

// Initialize the gallery page
document.addEventListener('DOMContentLoaded', () => {
    window.galleryPage = new GalleryPage();
    new ThemeManager();
});
