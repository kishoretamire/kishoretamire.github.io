const CHANNEL_ID = 'UCHf0witGYPnp5RYuijgV3Vw'; // Cricket Australia channel ID

class VideoPlayer {
    constructor() {
        this.videos = [];        // Current filtered/displayed videos
        this.allVideos = [];     // Store all videos for searching
        this.currentPage = 1;
        this.loading = false;
        this.currentCategory = 'matches';
        this.modal = null;
        this.categories = {
            'matches': 'Latest Highlights',
            'classic': 'Classic Matches',
            'interviews': 'Interviews & Press',
            'other': 'Other Videos'
        };

        // Get base path dynamically based on current URL
        this.basePath = this.getBasePath();
        this.init();
        this.initTheme();
        this.initSearch();
        this.initEventListeners();
    }

    getBasePath() {
        // Get the current path excluding the file name
        const currentPath = window.location.pathname;
        const pathParts = currentPath.split('/');
        
        // Remove the last part if it's a file
        if (currentPath.endsWith('.html') || currentPath.endsWith('/')) {
            pathParts.pop();
        }
        
        // Join the remaining parts to form the base path
        const basePath = pathParts.join('/');
        
        // If base path is empty, return '.' for root
        return basePath || '.';
    }

    renderCategories() {
        const tabsList = document.getElementById('category-tabs');
        if (!tabsList) return;

        const categoriesHtml = Object.entries(this.categories).map(([key, label]) => `
            <li class="nav-item">
                <a class="nav-link ${key === 'matches' ? 'active' : ''}" 
                   data-category="${key}" 
                   href="#"
                   role="tab">
                    ${label}
                </a>
            </li>
        `).join('');

        tabsList.innerHTML = categoriesHtml;
    }

    async init() {
        try {
            document.getElementById('loading').style.display = 'block';
            
            // Initialize Bootstrap modal only if element exists
            const modalElement = document.getElementById('videoModal');
            if (modalElement) {
                this.modal = new bootstrap.Modal(modalElement, {
                    keyboard: true,
                    backdrop: true,
                    focus: true
                });
                
                // Add event listener to clear video when modal is closed
                modalElement.addEventListener('hidden.bs.modal', () => {
                    document.getElementById('player').innerHTML = '';
                });
            }
            
            // Load categories
            this.renderCategories();
            
            // Load initial videos
            await this.loadVideos();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Initialize header scroll effect
            this.initHeaderScroll();
            
        } catch (error) {
            console.error('Error initializing:', error);
            this.showError(`Failed to initialize video player: ${error.message}`);
        } finally {
            document.getElementById('loading').style.display = 'none';
        }
    }

    async loadVideos() {
        try {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('load-more').style.display = 'none';
            
            const url = `${this.basePath}/static/data/${this.currentCategory}_videos.json`;
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`Failed to load videos: ${response.status}`);
            }

            this.allVideos = await response.json();  // Store all videos
            
            // Calculate pagination
            const startIndex = (this.currentPage - 1) * 20;
            const endIndex = startIndex + 20;
            const pageVideos = this.allVideos.slice(startIndex, endIndex);

            if (pageVideos.length > 0) {
                this.videos = pageVideos;
                this.renderVideos();
                
                // Show/hide load more button
                const hasMore = endIndex < this.allVideos.length;
                document.getElementById('load-more').style.display = hasMore ? 'block' : 'none';
                if (!hasMore) {
                    this.showNoMoreVideos();
                }
            } else {
                this.showError('No videos found.');
            }
        } catch (error) {
            console.error('Error loading videos:', error);
            this.showError(`Failed to load videos: ${error.message}`);
        } finally {
            document.getElementById('loading').style.display = 'none';
        }
    }

    renderVideos() {
        const grid = document.getElementById('video-grid');
        
        if (!this.videos || this.videos.length === 0) {
            grid.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-info">No videos found for the selected filters.</div>
                </div>
            `;
            return;
        }

        const videosHtml = this.videos.map(video => {
            const isExternal = video.source === 'IPL' || video.source === 'BCCI';
            
            return `
                <div class="col">
                    ${isExternal ? `
                        <!-- External Video (IPL/BCCI) -->
                        <a href="${video.external_url}" target="_blank" rel="noopener noreferrer" class="video-link">
                            <div class="video-card" data-video-id="${video.id}" data-source="${video.source}">
                                <div class="video-thumbnail">
                                    <img src="${video.thumbnail_url}" alt="${video.title}" loading="lazy">
                                    <div class="play-button external">
                                        <i class="bi bi-box-arrow-up-right"></i>
                                    </div>
                                    <div class="ipl-disclaimer">
                                        ${video.disclaimer}
                                    </div>
                                </div>
                                <div class="video-info">
                                    <h5 class="video-title">${video.title}</h5>
                                    <div class="video-meta">
                                        <span><i class="bi bi-calendar3"></i> ${this.formatDate(video.upload_date)}</span>
                                        <span><i class="bi bi-camera-video"></i> ${video.channel_name || 'Cricket'}</span>
                                    </div>
                                </div>
                            </div>
                        </a>
                    ` : `
                        <!-- YouTube Video -->
                        <div class="video-card" data-video-id="${video.id}" data-source="${video.source || 'youtube'}">
                            <div class="video-thumbnail">
                                <img src="${video.thumbnail_url}" alt="${video.title}" loading="lazy">
                                <div class="play-button">
                                    <i class="bi bi-play-fill"></i>
                                </div>
                            </div>
                            <div class="video-info">
                                <h5 class="video-title">${video.title}</h5>
                                <div class="video-meta">
                                    <span><i class="bi bi-calendar3"></i> ${this.formatDate(video.upload_date)}</span>
                                    <span><i class="bi bi-camera-video"></i> ${video.channel_name || 'Cricket'}</span>
                                </div>
                            </div>
                        </div>
                    `}
                </div>
            `;
        }).join('');

        grid.innerHTML = `<div class="row g-4">${videosHtml}</div>`;
    }

    async changeCategory(category) {
        if (category === this.currentCategory) return;
        
        // Clear search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = '';
        }
        
        this.currentCategory = category;
        this.currentPage = 1;
        
        // Update active tab
        document.querySelectorAll('#category-tabs .nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.category === category);
        });

        await this.loadVideos();
    }

    async loadMoreVideos() {
        try {
            this.loading = true;
            document.getElementById('loading').style.display = 'block';
            
            const startIndex = this.currentPage * 20;
            const endIndex = startIndex + 20;
            const nextPageVideos = this.allVideos.slice(startIndex, endIndex);
            
            if (nextPageVideos.length > 0) {
                this.currentPage++;
                this.videos = [...this.videos, ...nextPageVideos];
                
                // Append new videos instead of re-rendering all
                const grid = document.querySelector('#video-grid .row');
                const newVideosHtml = nextPageVideos.map(video => {
                    const isExternal = video.source === 'IPL' || video.source === 'BCCI';
                    
                    return `
                        <div class="col">
                            ${isExternal ? `
                                <!-- External Video (IPL/BCCI) -->
                                <a href="${video.external_url}" target="_blank" rel="noopener noreferrer" class="video-link">
                                    <div class="video-card" data-video-id="${video.id}" data-source="${video.source}">
                                        <div class="video-thumbnail">
                                            <img src="${video.thumbnail_url}" alt="${video.title}" loading="lazy">
                                            <div class="play-button external">
                                                <i class="bi bi-box-arrow-up-right"></i>
                                            </div>
                                            <div class="ipl-disclaimer">
                                                ${video.disclaimer}
                                            </div>
                                        </div>
                                        <div class="video-info">
                                            <h5 class="video-title">${video.title}</h5>
                                            <div class="video-meta">
                                                <span><i class="bi bi-calendar3"></i> ${this.formatDate(video.upload_date)}</span>
                                                <span><i class="bi bi-camera-video"></i> ${video.channel_name || 'Cricket'}</span>
                                            </div>
                                        </div>
                                    </div>
                                </a>
                            ` : `
                                <!-- YouTube Video -->
                                <div class="video-card" data-video-id="${video.id}" data-source="${video.source || 'youtube'}">
                                    <div class="video-thumbnail">
                                        <img src="${video.thumbnail_url}" alt="${video.title}" loading="lazy">
                                        <div class="play-button">
                                            <i class="bi bi-play-fill"></i>
                                        </div>
                                    </div>
                                    <div class="video-info">
                                        <h5 class="video-title">${video.title}</h5>
                                        <div class="video-meta">
                                            <span><i class="bi bi-calendar3"></i> ${this.formatDate(video.upload_date)}</span>
                                            <span><i class="bi bi-camera-video"></i> ${video.channel_name || 'Cricket'}</span>
                                        </div>
                                    </div>
                                </div>
                            `}
                        </div>
                    `;
                }).join('');
                
                grid.insertAdjacentHTML('beforeend', newVideosHtml);
                
                // Show/hide load more button
                const hasMore = endIndex < this.allVideos.length;
                document.getElementById('load-more').style.display = hasMore ? 'block' : 'none';
                if (!hasMore) {
                    this.showNoMoreVideos();
                }
            } else {
                document.getElementById('load-more').style.display = 'none';
                this.showNoMoreVideos();
            }
        } catch (error) {
            console.error('Error loading more videos:', error);
            this.showError('Failed to load more videos.');
        } finally {
            this.loading = false;
            document.getElementById('loading').style.display = 'none';
        }
    }

    showNoMoreVideos() {
        // Remove any existing "no more videos" message
        const existingMessage = document.querySelector('.no-more-videos-message');
        if (existingMessage) {
            existingMessage.remove();
        }

        // Create a new row for the message
        const messageDiv = document.createElement('div');
        messageDiv.className = 'row mt-4 no-more-videos-message';
        messageDiv.innerHTML = `
            <div class="col-12">
                <div class="text-center">
                    <p class="no-more-videos">No more videos to load</p>
                </div>
            </div>
        `;
        
        // Add the new row after the video grid
        document.getElementById('video-grid').appendChild(messageDiv);
        
        // Hide the load more button
        document.getElementById('load-more').style.display = 'none';
    }

    formatDuration(duration) {
        // Convert ISO 8601 duration to readable format
        // Example: PT1H2M10S -> 1:02:10
        try {
            const matches = duration.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
            if (!matches) return duration;

            const hours = matches[1] ? parseInt(matches[1]) : 0;
            const minutes = matches[2] ? parseInt(matches[2]) : 0;
            const seconds = matches[3] ? parseInt(matches[3]) : 0;

            if (hours > 0) {
                return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
            return `${minutes}:${seconds.toString().padStart(2, '0')}`;
        } catch (e) {
            return duration;
        }
    }

    formatViews(views) {
        // Format view count
        try {
            const num = parseInt(views);
            if (isNaN(num)) return views;
            if (num >= 1000000) {
                return `${(num / 1000000).toFixed(1)}M`;
            }
            if (num >= 1000) {
                return `${(num / 1000).toFixed(1)}K`;
            }
            return num.toString();
        } catch (e) {
            return views;
        }
    }

    formatDate(dateStr) {
        if (!dateStr) return 'Unknown date';
        
        // Handle BCCI date format (e.g., "2nd Nov, 2024")
        if (dateStr.includes(',')) {
            const parts = dateStr.split(',');
            const year = parts[1].trim();
            const monthDay = parts[0].trim().split(' ');
            const month = monthDay[1];
            const day = monthDay[0].replace(/(?:st|nd|rd|th)/, ''); // Remove ordinal suffixes
            
            const date = new Date(`${month} ${day}, ${year}`);
            const timeDiff = new Date() - date;
            const daysAgo = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
            
            if (daysAgo < 1) return 'Today';
            if (daysAgo === 1) return 'Yesterday';
            if (daysAgo < 7) return `${daysAgo} days ago`;
            if (daysAgo < 30) return `${Math.floor(daysAgo / 7)} weeks ago`;
            if (daysAgo < 365) return `${Math.floor(daysAgo / 30)} months ago`;
            return `${Math.floor(daysAgo / 365)} years ago`;
        }
        
        // Handle regular ISO date format
        try {
            const date = new Date(dateStr);
            const timeDiff = new Date() - date;
            const daysAgo = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
            
            if (daysAgo < 1) return 'Today';
            if (daysAgo === 1) return 'Yesterday';
            if (daysAgo < 7) return `${daysAgo} days ago`;
            if (daysAgo < 30) return `${Math.floor(daysAgo / 7)} weeks ago`;
            if (daysAgo < 365) return `${Math.floor(daysAgo / 30)} months ago`;
            return `${Math.floor(daysAgo / 365)} years ago`;
        } catch (e) {
            return 'Unknown date';
        }
    }

    setupEventListeners() {
        // Category tabs
        const categoryTabs = document.getElementById('category-tabs');
        if (categoryTabs) {
            categoryTabs.addEventListener('click', (e) => {
                if (e.target.classList.contains('nav-link')) {
                    e.preventDefault();
                    const category = e.target.dataset.category;
                    this.changeCategory(category);
                    
                    // Close mobile menu after category selection
                    const navbarCollapse = document.getElementById('navbarContent');
                    if (navbarCollapse) {
                        const bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
                        if (bsCollapse && window.innerWidth < 992) {  // 992px is Bootstrap's lg breakpoint
                            bsCollapse.hide();
                        }
                    }
                }
            });
        }

        // Video clicks
        const videoGrid = document.getElementById('video-grid');
        if (videoGrid) {
            videoGrid.addEventListener('click', (e) => {
                const videoCard = e.target.closest('.video-card');
                if (!videoCard) return;

                // Check if it's an IPL or BCCI video
                if (videoCard.dataset.source === 'IPL' || videoCard.dataset.source === 'BCCI') {
                    // Let the default link behavior handle it
                    return;
                }

                // Prevent default only for YouTube videos
                e.preventDefault();

                // Regular YouTube video
                const videoId = videoCard.dataset.videoId;
                if (videoId) {
                    window.location.href = `video.html?v=${videoId}`;
                }
            });
        }

        // Load more button
        const loadMoreBtn = document.getElementById('load-more');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                this.loadMoreVideos();
            });
        }
    }

    playVideo(videoId) {
        // Navigate to video page with video ID
        window.location.href = `video.html?v=${videoId}`;
    }

    showError(message) {
        const grid = document.getElementById('video-grid');
        grid.innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger">
                    <p>${message}</p>
                    <button class="btn btn-outline-danger mt-2" onclick="window.location.reload()">
                        Try Again
                    </button>
                </div>
            </div>
        `;
    }

    initTheme() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
            // Set initial icon
            this.updateThemeIcon();
        }
    }

    toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-bs-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        html.setAttribute('data-bs-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        this.updateThemeIcon();
    }

    updateThemeIcon() {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const darkIcon = document.querySelector('.dark-icon');
        const lightIcon = document.querySelector('.light-icon');
        
        if (darkIcon && lightIcon) {
            if (currentTheme === 'dark') {
                darkIcon.style.display = 'none';
                lightIcon.style.display = 'inline-block';
            } else {
                darkIcon.style.display = 'inline-block';
                lightIcon.style.display = 'none';
            }
        }
    }

    initHeaderScroll() {
        const header = document.querySelector('.site-header');
        if (header) {
            window.addEventListener('scroll', () => {
                if (window.scrollY > 10) {
                    header.classList.add('scrolled');
                } else {
                    header.classList.remove('scrolled');
                }
            });
        }
    }

    initSearch() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                const query = searchInput.value;
                this.filterVideos(query);
            }, 300));
        }
    }

    filterVideos(query) {
        if (!query) {
            // If search is empty, restore original videos for current category
            const startIndex = (this.currentPage - 1) * 20;
            const endIndex = startIndex + 20;
            this.videos = this.allVideos.slice(startIndex, endIndex);
            
            // Show load more button if there are more videos
            const hasMore = endIndex < this.allVideos.length;
            document.getElementById('load-more').style.display = hasMore ? 'block' : 'none';
            if (!hasMore) {
                this.showNoMoreVideos();
            }
        } else {
            // Filter videos based on search query
            this.videos = this.allVideos.filter(video => {
                const titleMatch = video.title.toLowerCase().includes(query.toLowerCase());
                const teamsMatch = video.teams && video.teams.some(team => 
                    team.toLowerCase().includes(query.toLowerCase())
                );
                const sourceMatch = video.source && video.source.toLowerCase().includes(query.toLowerCase());
                
                return titleMatch || teamsMatch || sourceMatch;
            });
            
            // Hide load more button during search
            document.getElementById('load-more').style.display = 'none';
            
            // Remove any existing "no more videos" message
            const existingMessage = document.querySelector('.no-more-videos-message');
            if (existingMessage) {
                existingMessage.remove();
            }
        }
        this.renderVideos();
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    async loadTeams() {
        try {
            const response = await fetch(`${this.basePath}/static/data/teams.json`);
            const data = await response.json();
            this.renderTeamFilters(data.teams);
        } catch (error) {
            console.error('Error loading teams:', error);
        }
    }

    renderTeamFilters(teams) {
        const filterContainer = document.getElementById('teamFilters');
        if (!filterContainer) return;

        const html = teams.map(team => `
            <div class="team-filter">
                <input type="checkbox" id="team-${team.name}" value="${team.name}">
                <label for="team-${team.name}">${team.name} (${team.video_count})</label>
            </div>
        `).join('');

        filterContainer.innerHTML = html;
    }

    // Add share functionality to video page
    initShareButtons() {
        const url = window.location.href;
        const title = document.getElementById('videoTitle').textContent;

        document.getElementById('shareWhatsapp').href = `whatsapp://send?text=${encodeURIComponent(title + ' ' + url)}`;
        document.getElementById('shareFacebook').href = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
        document.getElementById('shareTwitter').href = `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}`;
    }

    // Track watched videos
    trackVideoWatch(videoId) {
        let watched = JSON.parse(localStorage.getItem('watchedVideos') || '[]');
        if (!watched.includes(videoId)) {
            watched.push(videoId);
            localStorage.setItem('watchedVideos', JSON.stringify(watched));
        }
    }

    // Mark watched videos in the grid
    markWatchedVideos() {
        const watched = JSON.parse(localStorage.getItem('watchedVideos') || '[]');
        watched.forEach(videoId => {
            const card = document.querySelector(`[data-video-id="${videoId}"]`);
            if (card) {
                card.classList.add('watched');
            }
        });
    }

    // Implement infinite scroll
    initInfiniteScroll() {
        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting && !this.loading && this.hasMore) {
                    this.loadMoreVideos();
                }
            },
            { threshold: 0.1 }
        );

        const sentinel = document.getElementById('infinite-scroll-sentinel');
        if (sentinel) {
            observer.observe(sentinel);
        }
    }

    // Implement lazy loading for images
    initLazyLoading() {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    observer.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img.lazy').forEach(img => {
            imageObserver.observe(img);
        });
    }

    initEventListeners() {
        document.getElementById('video-grid').addEventListener('click', (e) => {
            const videoCard = e.target.closest('.video-card');
            if (!videoCard) return;

            // Check if it's an IPL or BCCI video
            if (videoCard.dataset.source === 'IPL' || videoCard.dataset.source === 'BCCI') {
                // Let the default link behavior handle it
                return;
            }

            // Prevent default only for YouTube videos
            e.preventDefault();

            // Regular YouTube video
            const videoId = videoCard.dataset.videoId;
            if (videoId) {
                window.location.href = `video.html?v=${videoId}`;
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.videoPlayer = new VideoPlayer();
});

// Add error tracking
window.addEventListener('error', function(e) {
    if (typeof gtag !== 'undefined') {
        gtag('event', 'javascript_error', {
            'error_message': e.message,
            'error_url': e.filename,
            'error_line': e.lineno
        });
    }
});

// Add performance monitoring
if ('performance' in window) {
    window.addEventListener('load', function() {
        const timing = performance.timing;
        const loadTime = timing.loadEventEnd - timing.navigationStart;
        
        if (typeof gtag !== 'undefined') {
            gtag('event', 'performance', {
                'page_load_time': loadTime
            });
        }
    });
} 