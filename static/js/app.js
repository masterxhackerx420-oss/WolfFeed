let currentMode = 'classic';
let currentUser = null;
let pollInterval = null;
let currentPostId = null;

document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    setupEventListeners();
    loadFeed();
    startPolling();
    // Theme
    if (localStorage.getItem('theme') === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
});

async function checkAuth() {
    const res = await fetch('/api/me');
    const data = await res.json();
    if (data.logged_in) {
        currentUser = data;
        showLoggedIn(data.username);
    } else {
        showLoggedOut();
    }
}

function showLoggedIn(username) {
    document.getElementById('loginBtn').style.display = 'none';
    document.getElementById('registerBtn').style.display = 'none';
    document.getElementById('usernameDisplay').textContent = username;
    document.getElementById('usernameDisplay').style.display = 'inline';
    document.getElementById('logoutBtn').style.display = 'inline';
    document.getElementById('composer').style.display = 'block';
}

function showLoggedOut() {
    document.getElementById('loginBtn').style.display = 'inline';
    document.getElementById('registerBtn').style.display = 'inline';
    document.getElementById('usernameDisplay').style.display = 'none';
    document.getElementById('logoutBtn').style.display = 'none';
    document.getElementById('composer').style.display = 'none';
    currentUser = null;
}

function setupEventListeners() {
    // Modes
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMode = btn.dataset.mode;
            document.getElementById('currentMode').textContent = currentMode;
            loadFeed();
        });
    });

    // Theme
    document.getElementById('themeBtn').addEventListener('click', () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        if (isDark) {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('theme', 'light');
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        }
    });

    // Auth
    document.getElementById('loginBtn').addEventListener('click', () => openAuth('login'));
    document.getElementById('registerBtn').addEventListener('click', () => openAuth('register'));
    document.getElementById('logoutBtn').addEventListener('click', logout);
    document.getElementById('authCancel').addEventListener('click', () => {
        document.getElementById('authModal').style.display = 'none';
    });
    document.getElementById('authSubmit').addEventListener('click', submitAuth);

    // Post
    document.getElementById('postBtn').addEventListener('click', createPost);

    // Comments
    document.getElementById('commentClose').addEventListener('click', () => {
        document.getElementById('commentModal').style.display = 'none';
    });
    document.getElementById('commentSubmit').addEventListener('click', submitComment);
}

function openAuth(type) {
    document.getElementById('modalTitle').textContent = type === 'login' ? 'Log In' : 'Register';
    document.getElementById('authSubmit').dataset.type = type;
    document.getElementById('authUsername').value = '';
    document.getElementById('authPassword').value = '';
    document.getElementById('authError').textContent = '';
    document.getElementById('authModal').style.display = 'flex';
}

async function submitAuth() {
    const type = document.getElementById('authSubmit').dataset.type;
    const username = document.getElementById('authUsername').value.trim();
    const password = document.getElementById('authPassword').value.trim();
    const endpoint = type === 'login' ? '/api/login' : '/api/register';
    const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (data.success) {
        if (type === 'register') {
            // Auto login after register
            const loginRes = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const loginData = await loginRes.json();
            if (loginData.success) {
                currentUser = { username };
                showLoggedIn(username);
            }
        } else {
            currentUser = { username: data.username };
            showLoggedIn(data.username);
        }
        document.getElementById('authModal').style.display = 'none';
        loadFeed();
    } else {
        document.getElementById('authError').textContent = data.error || 'Failed';
    }
}

async function logout() {
    await fetch('/api/logout', { method: 'POST' });
    showLoggedOut();
    loadFeed();
}

async function loadFeed() {
    const container = document.getElementById('feedContainer');
    container.innerHTML = '<div class="loading">Loading living feed...</div>';
    const res = await fetch(`/api/posts?mode=${currentMode}`);
    const posts = await res.json();
    container.innerHTML = '';
    if (posts.length === 0) {
        container.innerHTML = '<div class="loading">No posts in this mode yet. Be the first!</div>';
    } else {
        posts.forEach(post => container.appendChild(createPostElement(post)));
    }
    document.getElementById('postCount').textContent = posts.length;
}

function createPostElement(post) {
    const div = document.createElement('div');
    div.className = 'post';
    const time = new Date(post.timestamp).toLocaleString();
    div.innerHTML = `
        <div class="post-header">
            <span class="post-username">${escapeHtml(post.username)}</span>
            <span class="post-time">${time} • ${post.mode}</span>
        </div>
        <div class="post-content">${escapeHtml(post.content)}</div>
        <div class="post-actions">
            <button class="action-btn ${post.liked_by_me ? 'liked' : ''}" data-id="${post.id}" data-action="like">
                👍 ${post.likes}
            </button>
            <button class="action-btn" data-id="${post.id}" data-action="comment">
                💬 ${post.comment_count}
            </button>
        </div>
    `;
    div.querySelector('[data-action="like"]').addEventListener('click', () => toggleLike(post.id, div));
    div.querySelector('[data-action="comment"]').addEventListener('click', () => openComments(post.id));
    return div;
}

async function toggleLike(postId, postEl) {
    if (!currentUser) {
        openAuth('login');
        return;
    }
    const res = await fetch(`/api/posts/${postId}/like`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
        const btn = postEl.querySelector('[data-action="like"]');
        btn.innerHTML = `👍 ${data.likes}`;
        btn.classList.toggle('liked', data.liked);
    }
}

async function createPost() {
    const content = document.getElementById('postContent').value.trim();
    const mode = document.getElementById('postMode').value;
    if (!content) return;
    const res = await fetch('/api/posts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, mode })
    });
    const data = await res.json();
    if (data.success) {
        document.getElementById('postContent').value = '';
        loadFeed();
    }
}

async function openComments(postId) {
    currentPostId = postId;
    document.getElementById('commentModal').style.display = 'flex';
    document.getElementById('commentComposer').style.display = currentUser ? 'block' : 'none';
    await loadComments(postId);
}

async function loadComments(postId) {
    const res = await fetch(`/api/posts/${postId}/comments`);
    const comments = await res.json();
    const list = document.getElementById('commentsList');
    list.innerHTML = comments.map(c => `
        <div class="comment">
            <div class="comment-user">${escapeHtml(c.username)}</div>
            <div class="comment-text">${escapeHtml(c.content)}</div>
        </div>
    `).join('') || '<div class="loading">No comments yet.</div>';
}

async function submitComment() {
    const content = document.getElementById('commentContent').value.trim();
    if (!content || !currentPostId) return;
    const res = await fetch(`/api/posts/${currentPostId}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
    });
    const data = await res.json();
    if (data.success) {
        document.getElementById('commentContent').value = '';
        await loadComments(currentPostId);
        loadFeed(); // refresh counts
    }
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(loadFeed, 5000); // Living: refresh every 5s
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
