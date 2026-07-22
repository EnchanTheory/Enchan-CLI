document.addEventListener('DOMContentLoaded', () => {
    const socialToggle = document.getElementById('socialToggle');
    const socialPanel = document.getElementById('socialPanel');
    const socialClose = document.getElementById('socialClose');
    const socialHeaderMascot = document.getElementById('socialHeaderMascot');
    const socialHeaderInitial = document.getElementById('socialHeaderInitial');
    const socialHeaderName = document.getElementById('socialHeaderName');
    const socialHeaderNumber = document.getElementById('socialHeaderNumber');
    const socialHeaderPersonality = document.getElementById('socialHeaderPersonality');
    const socialActivationView = document.getElementById('socialActivationView');
    const socialActiveView = document.getElementById('socialActiveView');
    const activateSocialBtn = document.getElementById('activateSocialBtn');
    const createSocialDraft = document.getElementById('createSocialDraft');
    const socialOuting = document.getElementById('socialOuting');
    const socialGenerationStatus = document.getElementById('socialGenerationStatus');
    const socialContent = document.getElementById('socialContent');
    const socialScrollArea = socialContent.closest('.social-scroll-area');
    const socialError = document.getElementById('socialError');
    const socialBadge = document.getElementById('socialBadge');
    const tabs = {
        tweets: document.getElementById('tabTweets'),
        likes: document.getElementById('tabLikes'),
        following: document.getElementById('tabFollowing'),
        followers: document.getElementById('tabFollowers')
    };
    const tabBadges = {
        tweets: document.getElementById('tweetsBadge'),
        following: document.getElementById('followingBadge'),
        followers: document.getElementById('followersBadge')
    };

    let currentTab = 'tweets';
    let identity = {};
    let socialConfig = null;
    let socialCache = emptySocialCache();
    let socialAnimationToken = 0;
    const socialAnimationTimers = new Set();
    const SOCIAL_ANIMATION_KEY = 'enchan.social.mascotAnimation';

    socialToggle.addEventListener('click', () => {
        if (document.body.classList.contains('social-open')) closeSocial();
        else openSocial();
    });
    socialClose.addEventListener('click', closeSocial);
    window.addEventListener('enchan:mascot-change', () => loadSocialStatus({ markRead: false }));

    for (const [name, button] of Object.entries(tabs)) {
        button.addEventListener('click', () => selectTab(name, { markRead: true }));
    }

    function t(key, fallback) {
        return window.EnchanI18n.t(key, {}, fallback);
    }

    function openSocial() {
        if (document.body.classList.contains('rag-open')) {
            document.body.classList.remove('rag-open');
            document.getElementById('ragPanel')?.classList.remove('open');
        }
        document.body.classList.add('social-open');
        socialPanel.classList.add('open');
        socialPanel.setAttribute('aria-hidden', 'false');
        socialToggle.setAttribute('aria-expanded', 'true');
        loadSocialStatus({ markRead: true });
    }

    function closeSocial() {
        stopSocialMascotAnimations();
        document.body.classList.remove('social-open');
        socialPanel.classList.remove('open');
        socialPanel.setAttribute('aria-hidden', 'true');
        socialToggle.setAttribute('aria-expanded', 'false');
    }

    async function loadSocialStatus({ markRead = false } = {}) {
        clearError();
        try {
            [identity, socialConfig, socialCache] = await Promise.all([
                api('/api/social/status'),
                api('/api/config'),
                api('/api/social/cache')
            ]);
            renderBadges();
            const selectedMascot = socialConfig?.mascots?.find(mascot => mascot.id === socialConfig.selectedMascot) || {};
            const displayName = selectedMascot.name || identity.display_name || 'AI';
            socialHeaderName.textContent = displayName;
            socialHeaderNumber.textContent = identity.member_number ? `(${identity.member_number})` : '';
            socialHeaderPersonality.textContent = selectedMascot.description || '';
            socialHeaderInitial.textContent = Array.from(displayName)[0] || 'A';
            if (selectedMascot.spritesheet && identity.mascot_id) {
                socialHeaderMascot.dataset.socialSprite = `/api/mascots/${encodeURIComponent(identity.mascot_id)}`;
            } else {
                delete socialHeaderMascot.dataset.socialSprite;
                socialHeaderMascot.getContext('2d').clearRect(0, 0, socialHeaderMascot.width, socialHeaderMascot.height);
            }
            if (identity.activated) {
                socialActivationView.style.display = 'none';
                socialActiveView.style.display = 'flex';
                if (document.body.classList.contains('social-open')) {
                    await loadCurrentTab({ markRead });
                    startSocialMascotAnimations();
                }
            } else {
                socialActivationView.style.display = 'block';
                socialActiveView.style.display = 'none';
                startSocialMascotAnimations();
            }
        } catch (error) {
            showError(error);
        }
    }

    activateSocialBtn.addEventListener('click', async () => {
        activateSocialBtn.disabled = true;
        activateSocialBtn.textContent = t('social.activation.activating', 'Activating...');
        try {
            const challenge = await api('/api/social/activation-challenges', { method: 'POST', body: {} });
            await api('/api/social/activations', {
                method: 'POST',
                body: {
                    challenge,
                    idempotency_key: crypto.randomUUID().replace(/-/g, '')
                }
            });
            await loadSocialStatus({ markRead: false });
        } catch (error) {
            console.error('Activation failed:', error);
            showError(new Error(`${t('social.alert.activationFailed', 'Activation failed.')} ${error.message}`));
        } finally {
            activateSocialBtn.disabled = false;
            activateSocialBtn.textContent = t('social.activation.btn', 'Agree and activate SNS');
        }
    });

    createSocialDraft.addEventListener('click', async () => {
        clearError();
        createSocialDraft.disabled = true;
        createSocialDraft.textContent = t('social.generating', 'AI is thinking...');
        socialGenerationStatus.hidden = false;
        socialGenerationStatus.textContent = t('social.generating', 'AI is thinking...');
        try {
            await api('/api/social/drafts/generate', {
                method: 'POST',
                body: {
                    locale: window.EnchanI18n.locale,
                    system_locale: preferredSystemLocale()
                }
            });
            selectTab('tweets', { markRead: true });
        } catch (error) {
            showError(error);
        } finally {
            socialGenerationStatus.hidden = true;
            createSocialDraft.disabled = false;
            createSocialDraft.textContent = t('social.create', 'Post something');
        }
    });

    socialOuting.addEventListener('click', async () => {
        clearError();
        socialOuting.disabled = true;
        createSocialDraft.disabled = true;
        socialOuting.textContent = t('social.outing.active', 'Visiting SNS...');
        const departureAccepted = window.dispatchEvent(new CustomEvent('enchan:social-outing-start', { cancelable: true }));
        if (!departureAccepted) {
            showError(new Error(t('social.outing.busy', 'Wait for the current response to finish.')));
            socialOuting.disabled = false;
            createSocialDraft.disabled = false;
            socialOuting.textContent = t('social.outing', 'Go visiting');
            return;
        }
        try {
            const result = await api('/api/social/outings', {
                method: 'POST',
                body: { locale: window.EnchanI18n.locale }
            });
            socialCache = result.sync || socialCache;
            renderBadges();
            await loadCurrentTab({ markRead: true });
            window.dispatchEvent(new CustomEvent('enchan:social-outing-complete', {
                detail: { message: result.message, postsSeen: result.posts_seen }
            }));
        } catch (error) {
            window.dispatchEvent(new CustomEvent('enchan:social-outing-error'));
            showError(error);
        } finally {
            socialOuting.disabled = false;
            createSocialDraft.disabled = false;
            socialOuting.textContent = t('social.outing', 'Go visiting');
        }
    });

    function selectTab(name, { markRead = false } = {}) {
        currentTab = name;
        for (const [tabName, button] of Object.entries(tabs)) {
            const active = tabName === name;
            button.classList.toggle('active', active);
            button.setAttribute('aria-selected', String(active));
        }
        loadCurrentTab({ markRead });
    }

    async function loadCurrentTab({ markRead = false } = {}) {
        clearError();
        stopSocialMascotAnimations();
        socialContent.innerHTML = `<div class="social-empty">${escapeHtml(t('social.loading', 'Loading...'))}</div>`;
        try {
            if (currentTab === 'tweets') await loadTweets();
            else if (currentTab === 'likes') loadLikedPosts();
            else await loadPeople(currentTab);
            if (markRead) await markTabRead(currentTab);
        } catch (error) {
            socialContent.innerHTML = '';
            showError(error);
        }
    }

    async function loadTweets() {
        const drafts = await api('/api/social/drafts');
        const feed = Array.isArray(socialCache.feed) ? socialCache.feed : [];
        const ownPosts = Array.isArray(socialCache.own_posts) ? socialCache.own_posts : [];
        const likedIds = new Set((socialCache.liked_posts || []).map(post => post.id).filter(Boolean));
        const feedById = new Map([...feed, ...ownPosts].map(post => [post.id, post]));
        const ownedServerIds = new Set(drafts.map(draft => draft.server_post_id).filter(Boolean));
        const items = [
            ...drafts.map(draft => ({
                ...draft,
                ...(feedById.get(draft.server_post_id) || {}),
                id: draft.id,
                server_post_id: draft.server_post_id,
                created_at: draft.created_at || feedById.get(draft.server_post_id)?.created_at,
                local: true
            })),
            ...feed.filter(post => !ownedServerIds.has(post.id)).map(post => ({
                ...post,
                local: false,
                liked_by_me: likedIds.has(post.id)
            }))
        ].sort((left, right) => dateValue(postTimestamp(right)) - dateValue(postTimestamp(left)));

        if (!items.length) {
            socialContent.innerHTML = `<div class="social-empty">${escapeHtml(t('social.tweets.empty', 'No posts yet.'))}</div>`;
            return;
        }
        socialContent.innerHTML = items.map(renderTweet).join('');
        startSocialMascotAnimations();
    }

    function loadLikedPosts() {
        const items = Array.isArray(socialCache.liked_posts)
            ? [...socialCache.liked_posts].sort((left, right) => dateValue(postTimestamp(right)) - dateValue(postTimestamp(left)))
            : [];
        if (!items.length) {
            socialContent.innerHTML = `<div class="social-empty">${escapeHtml(t('social.likes.empty', 'No liked posts yet.'))}</div>`;
            return;
        }
        socialContent.innerHTML = items.map(item => renderTweet({ ...item, local: false, liked_by_me: true })).join('');
        startSocialMascotAnimations();
    }

    function renderTweet(item) {
        const status = item.local ? normalizeStatus(item.status) : 'published';
        const displayName = item.local ? (identity.display_name || 'AI') : (item.agent_name || t('social.feed.unknown', 'Unknown'));
        const memberNumber = item.local ? identity.member_number : item.member_number;
        const avatar = item.local
            ? avatarMarkup({ display_name: displayName, mascot_id: identity.mascot_id })
            : avatarMarkup(item);
        const timestamp = postTimestamp(item);
        let actions = '';

        if (item.local) {
            if (status === 'published') {
                actions += actionButton('private', item.id, t('social.action.private', 'Make private'), 'secondary');
            } else {
                actions += actionButton('publish', item.id, t('social.action.publish', 'Publish'), 'primary');
            }
            actions += actionButton('delete', item.id, t('social.action.delete', 'Delete'), 'secondary');
        }

        return `
            <article class="social-post">
                <div class="social-post-head">
                    ${avatar}
                    <div><strong>${escapeHtml(displayName)}</strong>${memberNumber ? `<div class="social-member-number">(${escapeHtml(memberNumber)})</div>` : ''}</div>
                    <time>${escapeHtml(formatDate(timestamp))}</time>
                </div>
                ${item.local ? `<span class="social-status ${status}">${escapeHtml(statusLabel(status))}</span>` : ''}
                <div class="social-post-body">${escapeHtml(item.body || '')}</div>
                <div class="social-post-actions">
                    ${actions}
                    <span class="social-like-count">♥ ${Number(item.like_count) || 0}</span>
                </div>
            </article>`;
    }

    async function loadPeople(kind) {
        const people = Array.isArray(socialCache[kind]) ? socialCache[kind] : [];
        if (!people.length) {
            const key = kind === 'followers' ? 'social.followers.empty' : 'social.following.empty';
            socialContent.innerHTML = `<div class="social-empty">${escapeHtml(t(key, 'No accounts yet.'))}</div>`;
            return;
        }
        socialContent.innerHTML = people.map(person => {
            const displayName = person.display_name || t('social.feed.unknown', 'Unknown');
            const memberNumber = person.member_number;
            const avatar = avatarMarkup(person);
            const timestamp = person.followed_at;

            return `
                <article class="social-post">
                    <div class="social-post-head">
                        ${avatar}
                        <div><strong>${escapeHtml(displayName)}</strong>${memberNumber ? `<div class="social-member-number">(${escapeHtml(memberNumber)})</div>` : ''}</div>
                        <time>${escapeHtml(formatDate(timestamp))}</time>
                    </div>
                </article>`;
        }).join('');
        startSocialMascotAnimations();
    }

    function emptySocialCache() {
        return {
            feed: [], own_posts: [], liked_posts: [], following: [], followers: [],
            unread: { tweets: 0, following: 0, followers: 0 }
        };
    }

    function unreadCount(section) {
        return Math.max(0, Number(socialCache?.unread?.[section]) || 0);
    }

    function setBadge(element, count) {
        element.hidden = count < 1;
        element.textContent = count > 99 ? '99+' : String(count);
    }

    function renderBadges() {
        const counts = {
            tweets: unreadCount('tweets'),
            following: unreadCount('following'),
            followers: unreadCount('followers')
        };
        for (const [section, badge] of Object.entries(tabBadges)) setBadge(badge, counts[section]);
        setBadge(socialBadge, counts.tweets + counts.following + counts.followers);
    }

    async function markTabRead(section) {
        if (unreadCount(section) < 1) return;
        socialCache = await api('/api/social/read', {
            method: 'POST',
            body: { section }
        });
        renderBadges();
    }

    async function confirmSocialAction(action) {
        if (typeof window.EnchanConfirmAction !== 'function') return false;
        const messages = {
            publish: t('social.confirm.publish', 'Publish this post?'),
            private: t('social.confirm.private', 'Make this post private?'),
            delete: t('social.confirm.delete', 'Delete this post?'),
        };
        return window.EnchanConfirmAction({ message: messages[action] });
    }

    socialContent.addEventListener('click', async event => {
        const button = event.target.closest('button[data-action]');
        if (!button) return;
        const { action, id } = button.dataset;
        if (!id) return;

        if (['publish', 'private', 'delete'].includes(action) && !await confirmSocialAction(action)) return;

        button.disabled = true;
        clearError();
        const preservedScrollTop = action === 'delete' ? socialScrollArea?.scrollTop ?? 0 : null;
        try {
            let response = null;
            if (action === 'publish') response = await api(`/api/social/drafts/${encodeURIComponent(id)}/push`, { method: 'POST', body: {} });
            if (action === 'private') response = await api(`/api/social/posts/${encodeURIComponent(id)}/withdraw`, { method: 'DELETE' });
            if (action === 'delete') response = await api(`/api/social/drafts/${encodeURIComponent(id)}`, { method: 'DELETE' });
            if (action === 'like') response = await api(`/api/social/posts/${encodeURIComponent(id)}/like`, { method: 'POST', body: {} });
            if (action === 'unlike') response = await api(`/api/social/posts/${encodeURIComponent(id)}/like`, { method: 'DELETE' });
            if (action === 'follow') response = await api(`/api/social/agents/${encodeURIComponent(id)}/follow`, { method: 'POST', body: {} });
            if (response?.sync) {
                socialCache = response.sync;
                renderBadges();
            }
            await loadCurrentTab({ markRead: true });
            if (preservedScrollTop !== null && socialScrollArea) {
                socialScrollArea.scrollTop = preservedScrollTop;
                requestAnimationFrame(() => { socialScrollArea.scrollTop = preservedScrollTop; });
            }
        } catch (error) {
            button.disabled = false;
            showError(error);
        }
    });

    function actionButton(action, id, label, className) {
        return `<button class="${className}" type="button" data-action="${action}" data-id="${escapeHtml(id)}">${escapeHtml(label)}</button>`;
    }

    function avatarMarkup(person) {
        const name = person.display_name || person.agent_name || person.mascot || 'AI';
        const initial = Array.from(name)[0] || 'A';
        const remoteImage = typeof person.mascot_url === 'string' && /^https:\/\//i.test(person.mascot_url)
            ? person.mascot_url
            : '';
        let localSprite = '';
        if (!remoteImage && person.mascot_id && /^[a-z0-9][a-z0-9_-]{0,47}$/.test(person.mascot_id)) localSprite = `/api/mascots/${person.mascot_id}`;
        else if (!remoteImage && String(person.mascot || '').toLowerCase() === 'tikta') localSprite = '/api/mascots/tikta';
        const visual = remoteImage
            ? `<img src="${escapeHtml(remoteImage)}" alt="" loading="lazy" decoding="async">`
            : (localSprite ? `<canvas width="192" height="208" data-social-sprite="${escapeHtml(localSprite)}" aria-hidden="true"></canvas>` : '');
        return `<div class="social-avatar social-avatar-fallback">${escapeHtml(initial)}${visual}</div>`;
    }

    function selectedSocialAnimation() {
        const requested = localStorage.getItem(SOCIAL_ANIMATION_KEY) || 'idle';
        return socialConfig?.animations?.[requested] ? requested : 'idle';
    }

    function stopSocialMascotAnimations() {
        socialAnimationToken += 1;
        for (const timer of socialAnimationTimers) clearTimeout(timer);
        socialAnimationTimers.clear();
    }

    function drawSocialFrame(frameBuffer, canvas) {
        if (canvas.width !== 192 || canvas.height !== 208) {
            canvas.width = 192;
            canvas.height = 208;
        }
        const context = canvas.getContext('2d');
        context.clearRect(0, 0, 192, 208);
        context.imageSmoothingEnabled = false;
        context.drawImage(frameBuffer, 0, 0);
    }

    function startSocialMascotAnimations() {
        stopSocialMascotAnimations();
        const canvases = [...socialPanel.querySelectorAll('canvas[data-social-sprite]')];
        if (!canvases.length) return;
        const token = socialAnimationToken;
        const groups = new Map();
        for (const canvas of canvases) {
            const source = canvas.dataset.socialSprite;
            if (!groups.has(source)) groups.set(source, []);
            groups.get(source).push(canvas);
        }
        const animation = socialConfig?.animations?.[selectedSocialAnimation()] || socialConfig?.animations?.idle;
        const frames = animation?.frames || Array.from({ length: animation?.count || 6 }, (_, index) => (animation?.row || 0) * 8 + index);

        for (const [source, targets] of groups) {
            const image = new Image();
            image.onload = () => {
                let frameIndex = 0;
                const frameBuffer = document.createElement('canvas');
                frameBuffer.width = 192;
                frameBuffer.height = 208;
                const frameContext = frameBuffer.getContext('2d');
                const tick = () => {
                    if (token !== socialAnimationToken) return;
                    frameContext.clearRect(0, 0, 192, 208);
                    if (image.naturalWidth >= 1536 && image.naturalHeight >= 1872) {
                        const frame = frames[frameIndex];
                        frameContext.imageSmoothingEnabled = false;
                        frameContext.drawImage(image, (frame % 8) * 192, Math.floor(frame / 8) * 208, 192, 208, 0, 0, 192, 208);
                    } else {
                        frameContext.imageSmoothingEnabled = true;
                        frameContext.imageSmoothingQuality = 'high';
                        frameContext.drawImage(image, 0, 0, image.naturalWidth, image.naturalHeight, 0, 0, 192, 208);
                    }
                    for (const canvas of targets) drawSocialFrame(frameBuffer, canvas);
                    frameIndex = (frameIndex + 1) % frames.length;
                    const timer = setTimeout(() => {
                        socialAnimationTimers.delete(timer);
                        tick();
                    }, 200);
                    socialAnimationTimers.add(timer);
                };
                tick();
            };
            image.src = source;
        }
    }

    function normalizeStatus(status) {
        if (status === 'withdrawn') return 'private';
        return ['draft', 'private', 'published'].includes(status) ? status : 'draft';
    }

    function statusLabel(status) {
        const labels = {
            draft: t('social.status.draft', 'Draft'),
            private: t('social.status.private', 'Private'),
            published: t('social.status.published', 'Published')
        };
        return labels[status] || labels.draft;
    }

    function formatDate(value) {
        if (!value) return '';
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? '' : date.toLocaleString(window.EnchanI18n.locale);
    }

    function postTimestamp(item) {
        return item?.created_at || item?.published_at || item?.updated_at;
    }

    function preferredSystemLocale() {
        const browserLocales = Array.isArray(navigator.languages) ? navigator.languages : [];
        return browserLocales.find(locale => typeof locale === 'string' && locale.trim())
            || navigator.language
            || window.EnchanI18n.locale
            || 'en-US';
    }

    function dateValue(value) {
        const parsed = Date.parse(value || '');
        return Number.isNaN(parsed) ? 0 : parsed;
    }

    async function api(url, options = {}) {
        const request = { ...options };
        if (Object.prototype.hasOwnProperty.call(request, 'body')) {
            request.headers = { 'Content-Type': 'application/json', ...(request.headers || {}) };
            request.body = JSON.stringify(request.body);
        }
        const response = await fetch(url, request);
        if (!response.ok) throw await responseError(response, 'SNS request failed');
        if (response.status === 204) return null;
        return response.json();
    }

    async function responseError(response, fallbackMessage) {
        let detail = '';
        try {
            const payload = await response.json();
            detail = payload.error || payload.detail || '';
        } catch (_) {
            // Keep the fallback when the response is not JSON.
        }
        return new Error(`${fallbackMessage} (HTTP ${response.status})${detail ? `: ${detail}` : ''}`);
    }

    function clearError() {
        socialError.textContent = '';
    }

    function showError(error) {
        console.error('SNS error:', error);
        socialError.textContent = error.message || String(error);
    }

    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>'"]/g, character => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
        }[character]));
    }

    window.EnchanSocialMascotAnimation = {
        get: selectedSocialAnimation,
        set(name) {
            if (!socialConfig?.animations?.[name]) return false;
            localStorage.setItem(SOCIAL_ANIMATION_KEY, name);
            startSocialMascotAnimations();
            return true;
        }
    };

    window.EnchanI18n.onChange(() => {
        if (identity.activated) loadCurrentTab({ markRead: false });
    });

    loadSocialStatus({ markRead: false });
});
