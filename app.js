const CHANNEL_ID = 'UCHf0witGYPnp5RYuijgV3Vw'; // Cricket Australia channel ID

class VideoPlayer {
    constructor() {
        this.videos = [];
        this.currentPage = 1;
        this.loading = false;
        this.currentCategory = 'all';
        this.currentTeam = null;
        this.modal = null;
        this.categories = {
            'all': 'All Videos',
            'teams': 'Teams',
            'matches': 'Match Highlights',
            'interviews': 'Interviews & Press',
            'training': 'Training & Behind the Scenes',
            'classic': 'Classic Matches',
            'other': 'Other Videos'
        };
        this.teams = {
            'australia': { name: 'Australia', flag: 'au' },
            'india': { name: 'India', flag: 'in' },
            'england': { name: 'England', flag: 'gb-eng' },
            'pakistan': { name: 'Pakistan', flag: 'pk' },
            'south africa': { name: 'South Africa', flag: 'za' },
            'new zealand': { name: 'New Zealand', flag: 'nz' },
            'west indies': { name: 'West Indies', flag: 'bb' },
            'sri lanka': { name: 'Sri Lanka', flag: 'lk' },
            'bangladesh': { name: 'Bangladesh', flag: 'bd' }
        };
        this.init();
    }

    async init() {
        try {
            document.getElementById('loading').style.display = 'block';
            
            // Initialize Bootstrap modal
            this.modal = new bootstrap.Modal(document.getElementById('videoModal'));
            
            // Load categories
            this.renderCategories();
            
            // Load initial content
            await this.loadContent();
            
            // Setup event listeners
            this.setupEventListeners();
            
        } catch (error) {
            console.error('Error initializing:', error);
            this.showError('Failed to initialize video player. Please refresh the page.');
        } finally {
            document.getElementById('loading').style.display = 'none';
        }
    }

    async loadContent() {
        if (this.currentCategory === 'teams') {
            await this.renderTeamsGrid();
        } else {
            document.getElementById('teams-grid').style.display = 'none';
            document.getElementById('video-grid').style.display = 'block';
            document.getElementById('selected-team-header').style.display = 'none';
            await this.loadVideos();
        }
    }

    async loadVideos() {
        try {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('load-more').style.display = 'none'; // Hide initially
            
            const url = this.currentTeam && this.currentCategory !== 'teams'
                ? './static/data/matches_videos.json'
                : `./static/data/${this.currentCategory}_videos.json`;
            
            console.log('Fetching videos from:', url);
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to load videos: ${response.status}`);
            }

            const allVideos = await response.json();
            
            // Filter by team if needed
            const filteredVideos = this.currentTeam 
                ? allVideos.filter(video => this.extractTeams(video.title).includes(this.currentTeam))
                : allVideos;
            
            // Calculate pagination
            const startIndex = (this.currentPage - 1) * 20;
            const endIndex = startIndex + 20;
            const pageVideos = filteredVideos.slice(startIndex, endIndex);

            if (pageVideos.length > 0) {
                this.videos = pageVideos;
                this.renderVideos();
                
                // Show load more button only if there are more videos
                const hasMore = endIndex < filteredVideos.length;
                document.getElementById('load-more').style.display = hasMore ? 'block' : 'none';
            } else {
                this.showError('No videos found for the selected filters.');
                document.getElementById('load-more').style.display = 'none';
            }
        } catch (error) {
            console.error('Error loading videos:', error);
            this.showError('Failed to load videos. Please try again.');
            document.getElementById('load-more').style.display = 'none';
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

        const videosHtml = this.videos.map(video => `
            <div class="col">
                <div class="video-card" data-video-id="${video.id}">
                    <div class="video-thumbnail">
                        <img src="${video.thumbnail_src || video.thumbnail_url}" 
                             alt="${video.title}"
                             loading="lazy"
                             onerror="this.src='https://i.ytimg.com/vi/${video.id}/hqdefault.jpg'">
                        <div class="play-button">
                            <i class="bi bi-play-fill"></i>
                        </div>
                        ${video.duration ? `
                            <span class="duration-badge">
                                <i class="bi bi-clock"></i> 
                                ${this.formatDuration(video.duration)}
                            </span>
                        ` : ''}
                        ${video.views && video.views !== 'N/A' ? `
                            <span class="views-badge">
                                <i class="bi bi-eye"></i> 
                                ${this.formatViews(video.views)}
                            </span>
                        ` : ''}
                    </div>
                    <div class="video-info">
                        <h5 class="video-title">${video.title}</h5>
                        <div class="video-meta">
                            <span>
                                <i class="bi bi-calendar3"></i> 
                                ${this.formatDate(video.upload_date)}
                            </span>
                            <span>
                                <i class="bi bi-camera-video"></i> 
                                ${video.channel_name || 'Cricket'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');

        grid.innerHTML = `
            <div class="row g-4">
                ${videosHtml}
            </div>
        `;
    }

    async renderTeamsGrid() {
        document.getElementById('video-grid').style.display = 'none';
        document.getElementById('teams-grid').style.display = 'block';
        document.getElementById('load-more').style.display = 'none';
        document.getElementById('selected-team-header').style.display = 'none';

        const teamsGrid = document.getElementById('teams-grid');
        
        try {
            const response = await fetch('./static/data/matches_videos.json');
            const allVideos = await response.json();
            
            const teamsHtml = Object.entries(this.teams).map(([key, team]) => {
                const teamVideos = allVideos.filter(video => 
                    this.extractTeams(video.title).includes(team.name)
                );
                
                return `
                    <div class="col">
                        <div class="team-card" data-team="${key}">
                            <div class="team-flag-container">
                                <img src="https://flagcdn.com/w640/${team.flag}.png" 
                                     alt="${team.name} flag"
                                     class="team-flag">
                            </div>
                            <div class="team-info">
                                <h3 class="team-name">${team.name}</h3>
                                <p class="team-stats">${teamVideos.length} videos</p>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            teamsGrid.innerHTML = `
                <div class="row row-cols-2 row-cols-md-3 row-cols-lg-4 g-4">
                    ${teamsHtml}
                </div>
            `;
        } catch (error) {
            console.error('Error rendering teams grid:', error);
            teamsGrid.innerHTML = `
                <div class="alert alert-danger">
                    Failed to load teams data. Please try again.
                </div>
            `;
        }
    }

    async selectTeam(teamKey) {
        this.currentTeam = teamKey;
        const team = this.teams[teamKey];

        // Update UI
        document.getElementById('teams-grid').style.display = 'none';
        document.getElementById('video-grid').style.display = 'flex';
        document.getElementById('selected-team-header').style.display = 'block';

        // Update team header
        document.getElementById('selected-team-flag').src = `https://flagcdn.com/w640/${team.flag}.png`;
        document.getElementById('selected-team-name').textContent = team.name;

        // Reset and load team videos
        this.currentPage = 1;
        await this.loadVideos();
    }

    clearTeamSelection() {
        this.currentTeam = null;
        this.currentPage = 1;
        this.renderTeamsGrid();
    }

    renderCategories() {
        const tabsList = document.getElementById('category-tabs');
        tabsList.innerHTML = Object.entries(this.categories).map(([key, label]) => `
            <li class="nav-item">
                <a class="nav-link ${key === 'all' ? 'active' : ''}" 
                   data-category="${key}" href="#">
                    ${label}
                </a>
            </li>
        `).join('');
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

    formatDate(dateString) {
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diff = now - date;
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));

            if (days === 0) return 'Today';
            if (days === 1) return 'Yesterday';
            if (days < 7) return `${days} days ago`;
            if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
            if (days < 365) return `${Math.floor(days / 30)} months ago`;
            return `${Math.floor(days / 365)} years ago`;
        } catch (e) {
            return dateString;
        }
    }

    setupEventListeners() {
        // Category tabs
        document.getElementById('category-tabs').addEventListener('click', (e) => {
            if (e.target.classList.contains('nav-link')) {
                e.preventDefault();
                const category = e.target.dataset.category;
                this.changeCategory(category);
            }
        });

        // Team selection
        document.getElementById('teams-grid').addEventListener('click', (e) => {
            const teamCard = e.target.closest('.team-card');
            if (teamCard) {
                const teamKey = teamCard.dataset.team;
                this.selectTeam(teamKey);
            }
        });

        // Video clicks
        document.getElementById('video-grid').addEventListener('click', (e) => {
            const card = e.target.closest('.video-card');
            if (card) {
                const videoId = card.dataset.videoId;
                this.playVideo(videoId);
            }
        });

        // Load more button
        document.getElementById('load-more').addEventListener('click', () => {
            this.loadMoreVideos();
        });
    }

    async changeCategory(category) {
        if (category === this.currentCategory) return;
        
        this.currentCategory = category;
        this.currentPage = 1;
        
        // Only clear team selection when not in teams category
        if (category !== 'teams') {
            this.currentTeam = null;
        }
        
        // Update active tab
        document.querySelectorAll('#category-tabs .nav-link').forEach(link => {
            link.classList.toggle('active', link.dataset.category === category);
        });

        await this.loadContent();
    }

    async loadMoreVideos() {
        if (this.loading) return;
        
        try {
            this.loading = true;
            document.getElementById('loading').style.display = 'block';
            
            // Load all videos again
            const response = await fetch(`static/data/${this.currentCategory}_videos.json`);
            if (!response.ok) {
                throw new Error('Failed to load more videos');
            }

            const allVideos = await response.json();
            
            // Filter by team if needed
            const filteredVideos = this.currentTeam === 'all' 
                ? allVideos 
                : allVideos.filter(video => this.extractTeams(video.title).includes(this.currentTeam));
            
            // Calculate next page
            this.currentPage++;
            const startIndex = (this.currentPage - 1) * 20;
            const endIndex = startIndex + 20;
            const newPageVideos = filteredVideos.slice(startIndex, endIndex);

            if (newPageVideos.length > 0) {
                // Append new videos to existing ones
                this.videos = [...this.videos, ...newPageVideos];
                this.renderMoreVideos(newPageVideos);
                
                // Show/hide load more button and message
                const hasMore = endIndex < filteredVideos.length;
                document.getElementById('load-more').style.display = 'none'; // Hide first
                if (hasMore) {
                    document.getElementById('load-more').style.display = 'block';
                } else {
                    this.showNoMoreVideos();
                }
            } else {
                document.getElementById('load-more').style.display = 'none';
                this.showNoMoreVideos();
            }
        } catch (error) {
            console.error('Error loading more videos:', error);
            this.showError('Failed to load more videos.');
            document.getElementById('load-more').style.display = 'none';
        } finally {
            this.loading = false;
            document.getElementById('loading').style.display = 'none';
        }
    }

    renderMoreVideos(newVideos) {
        const grid = document.getElementById('video-grid').querySelector('.row');
        
        const newHtml = newVideos.map(video => `
            <div class="col">
                <div class="video-card" data-video-id="${video.id}">
                    <div class="video-thumbnail">
                        <img src="${video.thumbnail_src || video.thumbnail_url}" 
                             alt="${video.title}"
                             loading="lazy"
                             onerror="this.src='https://i.ytimg.com/vi/${video.id}/hqdefault.jpg'">
                        <div class="play-button">
                            <i class="bi bi-play-fill"></i>
                        </div>
                        ${video.duration ? `
                            <span class="duration-badge">
                                <i class="bi bi-clock"></i> 
                                ${this.formatDuration(video.duration)}
                            </span>
                        ` : ''}
                        ${video.views && video.views !== 'N/A' ? `
                            <span class="views-badge">
                                <i class="bi bi-eye"></i> 
                                ${this.formatViews(video.views)}
                            </span>
                        ` : ''}
                    </div>
                    <div class="video-info">
                        <h5 class="video-title">${video.title}</h5>
                        <div class="video-meta">
                            <span>
                                <i class="bi bi-calendar3"></i> 
                                ${this.formatDate(video.upload_date)}
                            </span>
                            <span>
                                <i class="bi bi-camera-video"></i> 
                                ${video.channel_name || 'Cricket'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        grid.insertAdjacentHTML('beforeend', newHtml);
    }

    showNoMoreVideos() {
        // Remove any existing "no more videos" message
        const existingMessage = document.querySelector('.no-more-videos-message');
        if (existingMessage) {
            existingMessage.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = 'col-12 text-center mt-4 no-more-videos-message';
        messageDiv.innerHTML = '<p class="no-more-videos">No more videos to load</p>';
        document.getElementById('video-grid').querySelector('.row').appendChild(messageDiv);
        
        // Hide the load more button
        document.getElementById('load-more').style.display = 'none';
    }

    extractTeams(title) {
        const teams = new Set();
        const title_lower = title.toLowerCase();
        
        // Common cricket team names
        const team_names = [
            'australia', 'india', 'england', 'pakistan', 
            'south africa', 'new zealand', 'west indies', 
            'sri lanka', 'bangladesh', 'zimbabwe'
        ];
        
        for (const team of team_names) {
            if (title_lower.includes(team)) {
                teams.add(team.split(' ').map(word => 
                    word.charAt(0).toUpperCase() + word.slice(1)
                ).join(' '));
            }
        }
        
        return Array.from(teams);
    }

    playVideo(videoId) {
        const video = this.videos.find(v => v.id === videoId);
        if (!video) return;

        document.getElementById('videoModalTitle').textContent = video.title;
        document.getElementById('player').innerHTML = `
            <iframe 
                src="https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0" 
                frameborder="0" 
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen>
            </iframe>
        `;
        
        this.modal.show();
    }

    showError(message) {
        const grid = document.getElementById('video-grid');
        grid.innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger">
                    <p>${message}</p>
                    <button class="btn btn-outline-danger btn-sm mt-2" onclick="window.location.reload()">
                        Try Again
                    </button>
                </div>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.videoPlayer = new VideoPlayer();
}); 