/**
 * BioQL Lab Notebook - Real-time Collaboration Module
 * Google Docs-style collaboration with WebSocket support
 *
 * Features:
 * - Real-time cursor positions
 * - Live cell editing with conflict resolution
 * - User presence indicators
 * - Comment threads with @mentions
 * - Activity feed
 * - Sharing and permissions
 * - Notifications
 */

class CollaborationManager {
    constructor() {
        this.ws = null;
        this.notebookId = null;
        this.userId = null;
        this.userName = null;
        this.userColor = null;
        this.activeUsers = new Map();
        this.cursors = new Map();
        this.comments = new Map();
        this.activityFeed = [];
        this.pendingEdits = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.heartbeatInterval = null;
        this.eventHandlers = new Map();

        // Initialize UI
        this.initializeUI();
    }

    /**
     * Connect to WebSocket server for real-time collaboration
     * @param {string} notebookId - Notebook identifier
     * @param {string} userId - User identifier
     * @param {string} userName - User display name
     * @param {string} wsUrl - WebSocket server URL (default: ws://localhost:8080)
     */
    connect(notebookId, userId, userName = 'Anonymous', wsUrl = 'ws://localhost:8080') {
        this.notebookId = notebookId;
        this.userId = userId;
        this.userName = userName;
        this.userColor = this.generateUserColor(userId);

        try {
            // Close existing connection
            if (this.ws) {
                this.disconnect();
            }

            // Create WebSocket connection
            this.ws = new WebSocket(`${wsUrl}/collaborate/${notebookId}`);

            // Connection opened
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;

                // Send join message
                this.sendMessage({
                    type: 'join',
                    userId: this.userId,
                    userName: this.userName,
                    userColor: this.userColor,
                    timestamp: Date.now()
                });

                // Start heartbeat
                this.startHeartbeat();

                // Emit connected event
                this.emit('connected', { notebookId, userId });
            };

            // Message received
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('Error parsing message:', error);
                }
            };

            // Connection closed
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.stopHeartbeat();
                this.emit('disconnected');

                // Attempt reconnection
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    setTimeout(() => {
                        this.reconnectAttempts++;
                        this.connect(notebookId, userId, userName, wsUrl);
                    }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts));
                }
            };

            // Connection error
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.emit('error', error);
            };

        } catch (error) {
            console.error('Failed to connect:', error);
            this.emit('error', error);
        }
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        if (this.ws) {
            this.sendMessage({
                type: 'leave',
                userId: this.userId,
                timestamp: Date.now()
            });

            this.stopHeartbeat();
            this.ws.close();
            this.ws = null;
            this.activeUsers.clear();
            this.cursors.clear();
            this.updateCollaboratorsPanel();
        }
    }

    /**
     * Send WebSocket message
     */
    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, queuing message');
            this.pendingEdits.push(message);
        }
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(message) {
        switch (message.type) {
            case 'user_joined':
                this.handleUserJoined(message);
                break;
            case 'user_left':
                this.handleUserLeft(message);
                break;
            case 'cursor_position':
                this.handleCursorPosition(message);
                break;
            case 'cell_edit':
                this.handleCellEdit(message);
                break;
            case 'comment_added':
                this.handleCommentAdded(message);
                break;
            case 'comment_updated':
                this.handleCommentUpdated(message);
                break;
            case 'comment_deleted':
                this.handleCommentDeleted(message);
                break;
            case 'activity':
                this.handleActivity(message);
                break;
            case 'notification':
                this.handleNotification(message);
                break;
            case 'active_users':
                this.handleActiveUsers(message);
                break;
            case 'pong':
                // Heartbeat response
                break;
            default:
                console.warn('Unknown message type:', message.type);
        }
    }

    /**
     * Send cursor position to other users
     * @param {string} cellId - Cell identifier
     * @param {object} position - Cursor position {line, column}
     */
    sendCursorPosition(cellId, position) {
        this.sendMessage({
            type: 'cursor_position',
            userId: this.userId,
            userName: this.userName,
            userColor: this.userColor,
            cellId: cellId,
            position: position,
            timestamp: Date.now()
        });
    }

    /**
     * Synchronize cell edit with other users (with conflict resolution)
     * @param {string} cellId - Cell identifier
     * @param {string} content - Cell content
     * @param {number} version - Cell version for conflict detection
     */
    syncCellEdit(cellId, content, version = 0) {
        const edit = {
            type: 'cell_edit',
            userId: this.userId,
            userName: this.userName,
            cellId: cellId,
            content: content,
            version: version,
            timestamp: Date.now()
        };

        this.sendMessage(edit);

        return edit;
    }

    /**
     * Add comment to a cell
     * @param {string} cellId - Cell identifier
     * @param {string} text - Comment text
     * @param {array} mentions - Array of mentioned user IDs
     * @param {string} parentId - Parent comment ID for replies (optional)
     */
    addComment(cellId, text, mentions = [], parentId = null) {
        const commentId = this.generateId();
        const comment = {
            id: commentId,
            type: 'comment_added',
            userId: this.userId,
            userName: this.userName,
            userColor: this.userColor,
            cellId: cellId,
            text: text,
            mentions: mentions,
            parentId: parentId,
            timestamp: Date.now(),
            resolved: false
        };

        this.sendMessage(comment);

        // Add to local comments
        if (!this.comments.has(cellId)) {
            this.comments.set(cellId, []);
        }
        this.comments.get(cellId).push(comment);

        // Update UI
        this.updateCommentsPanel();

        return commentId;
    }

    /**
     * Update comment
     * @param {string} commentId - Comment identifier
     * @param {string} text - Updated text
     */
    updateComment(commentId, text) {
        this.sendMessage({
            type: 'comment_updated',
            commentId: commentId,
            userId: this.userId,
            text: text,
            timestamp: Date.now()
        });
    }

    /**
     * Delete comment
     * @param {string} commentId - Comment identifier
     */
    deleteComment(commentId) {
        this.sendMessage({
            type: 'comment_deleted',
            commentId: commentId,
            userId: this.userId,
            timestamp: Date.now()
        });
    }

    /**
     * Resolve comment thread
     * @param {string} commentId - Comment identifier
     */
    resolveComment(commentId) {
        this.sendMessage({
            type: 'comment_resolved',
            commentId: commentId,
            userId: this.userId,
            timestamp: Date.now()
        });
    }

    /**
     * Share notebook with team members
     * @param {string} notebookId - Notebook identifier
     * @param {array} userEmails - Array of user email addresses
     * @param {string} permission - Permission level ('view', 'edit', 'admin')
     */
    async shareNotebook(notebookId, userEmails, permission = 'view') {
        try {
            const response = await fetch('/api/notebooks/share', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    notebookId: notebookId,
                    userEmails: userEmails,
                    permission: permission,
                    sharedBy: this.userId
                })
            });

            if (!response.ok) {
                throw new Error('Failed to share notebook');
            }

            const result = await response.json();

            // Send notification to WebSocket
            this.sendMessage({
                type: 'notebook_shared',
                notebookId: notebookId,
                userEmails: userEmails,
                permission: permission,
                sharedBy: this.userId,
                timestamp: Date.now()
            });

            this.emit('notebook_shared', result);
            return result;

        } catch (error) {
            console.error('Error sharing notebook:', error);
            throw error;
        }
    }

    /**
     * Update user permission
     * @param {string} notebookId - Notebook identifier
     * @param {string} userId - User identifier
     * @param {string} permission - New permission level
     */
    async updatePermission(notebookId, userId, permission) {
        try {
            const response = await fetch('/api/notebooks/permissions', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    notebookId: notebookId,
                    userId: userId,
                    permission: permission
                })
            });

            if (!response.ok) {
                throw new Error('Failed to update permission');
            }

            return await response.json();

        } catch (error) {
            console.error('Error updating permission:', error);
            throw error;
        }
    }

    /**
     * Get activity feed for notebook
     * @param {string} notebookId - Notebook identifier
     * @param {number} limit - Maximum number of activities to return
     */
    async getActivityFeed(notebookId, limit = 50) {
        try {
            const response = await fetch(`/api/notebooks/${notebookId}/activity?limit=${limit}`);

            if (!response.ok) {
                throw new Error('Failed to fetch activity feed');
            }

            const activities = await response.json();
            this.activityFeed = activities;
            this.updateActivityTimeline();

            return activities;

        } catch (error) {
            console.error('Error fetching activity feed:', error);
            throw error;
        }
    }

    /**
     * Handle user joined event
     */
    handleUserJoined(message) {
        this.activeUsers.set(message.userId, {
            userId: message.userId,
            userName: message.userName,
            userColor: message.userColor,
            status: 'online',
            joinedAt: message.timestamp
        });

        this.updateCollaboratorsPanel();
        this.showNotification(`${message.userName} joined the notebook`, 'info');
        this.emit('user_joined', message);
    }

    /**
     * Handle user left event
     */
    handleUserLeft(message) {
        this.activeUsers.delete(message.userId);
        this.cursors.delete(message.userId);
        this.removeCursorElement(message.userId);
        this.updateCollaboratorsPanel();
        this.showNotification(`${message.userName} left the notebook`, 'info');
        this.emit('user_left', message);
    }

    /**
     * Handle cursor position update
     */
    handleCursorPosition(message) {
        if (message.userId === this.userId) return;

        this.cursors.set(message.userId, {
            cellId: message.cellId,
            position: message.position,
            userName: message.userName,
            userColor: message.userColor
        });

        this.updateCursorElement(message);
    }

    /**
     * Handle cell edit with conflict resolution
     */
    handleCellEdit(message) {
        if (message.userId === this.userId) return;

        const cellElement = document.querySelector(`[data-cell-id="${message.cellId}"]`);
        if (!cellElement) return;

        // Get current version
        const currentVersion = parseInt(cellElement.dataset.version || 0);

        // Conflict resolution
        if (message.version < currentVersion) {
            console.warn('Received outdated edit, requesting resync');
            this.requestResync(message.cellId);
            return;
        }

        // Apply edit
        const editor = cellElement.querySelector('.cell-editor');
        if (editor && document.activeElement !== editor) {
            editor.value = message.content;
            cellElement.dataset.version = message.version + 1;
        }

        // Show edit indicator
        this.showEditIndicator(message.cellId, message.userName);

        this.emit('cell_edited', message);
    }

    /**
     * Handle comment added
     */
    handleCommentAdded(message) {
        if (!this.comments.has(message.cellId)) {
            this.comments.set(message.cellId, []);
        }

        this.comments.get(message.cellId).push(message);
        this.updateCommentsPanel();
        this.updateCellCommentIndicator(message.cellId);

        // Show notification if mentioned
        if (message.mentions.includes(this.userId)) {
            this.showNotification(`${message.userName} mentioned you in a comment`, 'mention');
        }

        this.emit('comment_added', message);
    }

    /**
     * Handle comment updated
     */
    handleCommentUpdated(message) {
        for (const [cellId, comments] of this.comments.entries()) {
            const comment = comments.find(c => c.id === message.commentId);
            if (comment) {
                comment.text = message.text;
                comment.edited = true;
                comment.editedAt = message.timestamp;
                this.updateCommentsPanel();
                break;
            }
        }
    }

    /**
     * Handle comment deleted
     */
    handleCommentDeleted(message) {
        for (const [cellId, comments] of this.comments.entries()) {
            const index = comments.findIndex(c => c.id === message.commentId);
            if (index !== -1) {
                comments.splice(index, 1);
                this.updateCommentsPanel();
                this.updateCellCommentIndicator(cellId);
                break;
            }
        }
    }

    /**
     * Handle activity update
     */
    handleActivity(message) {
        this.activityFeed.unshift(message);
        if (this.activityFeed.length > 100) {
            this.activityFeed.pop();
        }
        this.updateActivityTimeline();
    }

    /**
     * Handle notification
     */
    handleNotification(message) {
        this.showNotification(message.text, message.level || 'info');
        this.emit('notification', message);
    }

    /**
     * Handle active users list
     */
    handleActiveUsers(message) {
        this.activeUsers.clear();
        message.users.forEach(user => {
            this.activeUsers.set(user.userId, user);
        });
        this.updateCollaboratorsPanel();
    }

    /**
     * Request resync for a cell
     */
    requestResync(cellId) {
        this.sendMessage({
            type: 'resync_request',
            cellId: cellId,
            userId: this.userId,
            timestamp: Date.now()
        });
    }

    /**
     * Start heartbeat to keep connection alive
     */
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.sendMessage({ type: 'ping', timestamp: Date.now() });
            }
        }, 30000); // Every 30 seconds
    }

    /**
     * Stop heartbeat
     */
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /**
     * Initialize UI elements
     */
    initializeUI() {
        // Create collaborators panel
        const collaboratorsPanel = document.createElement('div');
        collaboratorsPanel.id = 'collaborators-panel';
        collaboratorsPanel.className = 'collaboration-panel';
        collaboratorsPanel.innerHTML = `
            <div class="panel-header">
                <h3>Collaborators</h3>
                <button id="share-btn" class="btn-icon" title="Share notebook">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path>
                        <polyline points="16 6 12 2 8 6"></polyline>
                        <line x1="12" y1="2" x2="12" y2="15"></line>
                    </svg>
                </button>
            </div>
            <div id="collaborators-list" class="collaborators-list"></div>
        `;

        // Create comments panel
        const commentsPanel = document.createElement('div');
        commentsPanel.id = 'comments-panel';
        commentsPanel.className = 'collaboration-panel';
        commentsPanel.innerHTML = `
            <div class="panel-header">
                <h3>Comments</h3>
                <button id="toggle-comments-btn" class="btn-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                </button>
            </div>
            <div id="comments-list" class="comments-list"></div>
        `;

        // Create activity panel
        const activityPanel = document.createElement('div');
        activityPanel.id = 'activity-panel';
        activityPanel.className = 'collaboration-panel';
        activityPanel.innerHTML = `
            <div class="panel-header">
                <h3>Activity</h3>
                <button id="refresh-activity-btn" class="btn-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <polyline points="23 4 23 10 17 10"></polyline>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                    </svg>
                </button>
            </div>
            <div id="activity-timeline" class="activity-timeline"></div>
        `;

        // Create share modal
        const shareModal = document.createElement('div');
        shareModal.id = 'share-modal';
        shareModal.className = 'modal';
        shareModal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Share Notebook</h2>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>Share with:</label>
                        <input type="text" id="share-emails" placeholder="Enter email addresses (comma separated)" class="form-control">
                    </div>
                    <div class="form-group">
                        <label>Permission level:</label>
                        <select id="share-permission" class="form-control">
                            <option value="view">View only</option>
                            <option value="edit">Can edit</option>
                            <option value="admin">Admin</option>
                        </select>
                    </div>
                    <div class="current-shares">
                        <h4>People with access</h4>
                        <div id="current-shares-list"></div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button id="cancel-share-btn" class="btn-secondary">Cancel</button>
                    <button id="confirm-share-btn" class="btn-primary">Share</button>
                </div>
            </div>
        `;

        // Create cursor container
        const cursorContainer = document.createElement('div');
        cursorContainer.id = 'collaboration-cursors';
        cursorContainer.className = 'cursor-container';

        // Add to DOM when ready
        if (document.body) {
            this.appendUIElements(collaboratorsPanel, commentsPanel, activityPanel, shareModal, cursorContainer);
        } else {
            document.addEventListener('DOMContentLoaded', () => {
                this.appendUIElements(collaboratorsPanel, commentsPanel, activityPanel, shareModal, cursorContainer);
            });
        }
    }

    /**
     * Append UI elements to DOM
     */
    appendUIElements(collaboratorsPanel, commentsPanel, activityPanel, shareModal, cursorContainer) {
        document.body.appendChild(collaboratorsPanel);
        document.body.appendChild(commentsPanel);
        document.body.appendChild(activityPanel);
        document.body.appendChild(shareModal);
        document.body.appendChild(cursorContainer);

        // Attach event listeners
        this.attachEventListeners();
    }

    /**
     * Attach event listeners to UI elements
     */
    attachEventListeners() {
        // Share button
        const shareBtn = document.getElementById('share-btn');
        if (shareBtn) {
            shareBtn.addEventListener('click', () => this.showShareModal());
        }

        // Share modal buttons
        const confirmShareBtn = document.getElementById('confirm-share-btn');
        if (confirmShareBtn) {
            confirmShareBtn.addEventListener('click', () => this.handleShareConfirm());
        }

        const cancelShareBtn = document.getElementById('cancel-share-btn');
        if (cancelShareBtn) {
            cancelShareBtn.addEventListener('click', () => this.hideShareModal());
        }

        const modalClose = document.querySelector('#share-modal .modal-close');
        if (modalClose) {
            modalClose.addEventListener('click', () => this.hideShareModal());
        }

        // Refresh activity button
        const refreshActivityBtn = document.getElementById('refresh-activity-btn');
        if (refreshActivityBtn) {
            refreshActivityBtn.addEventListener('click', () => {
                if (this.notebookId) {
                    this.getActivityFeed(this.notebookId);
                }
            });
        }

        // Toggle comments button
        const toggleCommentsBtn = document.getElementById('toggle-comments-btn');
        if (toggleCommentsBtn) {
            toggleCommentsBtn.addEventListener('click', () => {
                const panel = document.getElementById('comments-panel');
                panel.classList.toggle('collapsed');
            });
        }
    }

    /**
     * Update collaborators panel
     */
    updateCollaboratorsPanel() {
        const list = document.getElementById('collaborators-list');
        if (!list) return;

        list.innerHTML = '';

        this.activeUsers.forEach(user => {
            const userItem = document.createElement('div');
            userItem.className = 'collaborator-item';
            userItem.innerHTML = `
                <div class="collaborator-avatar" style="background-color: ${user.userColor}">
                    ${user.userName.charAt(0).toUpperCase()}
                </div>
                <div class="collaborator-info">
                    <div class="collaborator-name">${user.userName}</div>
                    <div class="collaborator-status ${user.status}">${user.status}</div>
                </div>
            `;
            list.appendChild(userItem);
        });

        if (this.activeUsers.size === 0) {
            list.innerHTML = '<div class="empty-state">No active collaborators</div>';
        }
    }

    /**
     * Update comments panel
     */
    updateCommentsPanel() {
        const list = document.getElementById('comments-list');
        if (!list) return;

        list.innerHTML = '';

        // Flatten and sort comments
        const allComments = [];
        this.comments.forEach((comments, cellId) => {
            comments.forEach(comment => {
                allComments.push({ ...comment, cellId });
            });
        });

        allComments.sort((a, b) => b.timestamp - a.timestamp);

        allComments.forEach(comment => {
            const commentItem = document.createElement('div');
            commentItem.className = 'comment-item';
            commentItem.dataset.commentId = comment.id;

            const timeAgo = this.formatTimeAgo(comment.timestamp);

            commentItem.innerHTML = `
                <div class="comment-header">
                    <div class="comment-avatar" style="background-color: ${comment.userColor}">
                        ${comment.userName.charAt(0).toUpperCase()}
                    </div>
                    <div class="comment-meta">
                        <div class="comment-author">${comment.userName}</div>
                        <div class="comment-time">${timeAgo}</div>
                    </div>
                </div>
                <div class="comment-body">${this.renderCommentText(comment.text, comment.mentions)}</div>
                <div class="comment-actions">
                    <button class="comment-reply" data-comment-id="${comment.id}">Reply</button>
                    ${comment.userId === this.userId ? `
                        <button class="comment-edit" data-comment-id="${comment.id}">Edit</button>
                        <button class="comment-delete" data-comment-id="${comment.id}">Delete</button>
                    ` : ''}
                    ${!comment.parentId ? `
                        <button class="comment-resolve" data-comment-id="${comment.id}">
                            ${comment.resolved ? 'Unresolve' : 'Resolve'}
                        </button>
                    ` : ''}
                </div>
            `;

            // Attach event listeners
            const replyBtn = commentItem.querySelector('.comment-reply');
            if (replyBtn) {
                replyBtn.addEventListener('click', () => this.showReplyInput(comment.id, comment.cellId));
            }

            const editBtn = commentItem.querySelector('.comment-edit');
            if (editBtn) {
                editBtn.addEventListener('click', () => this.showEditInput(comment.id));
            }

            const deleteBtn = commentItem.querySelector('.comment-delete');
            if (deleteBtn) {
                deleteBtn.addEventListener('click', () => this.deleteComment(comment.id));
            }

            const resolveBtn = commentItem.querySelector('.comment-resolve');
            if (resolveBtn) {
                resolveBtn.addEventListener('click', () => this.resolveComment(comment.id));
            }

            list.appendChild(commentItem);
        });

        if (allComments.length === 0) {
            list.innerHTML = '<div class="empty-state">No comments yet</div>';
        }
    }

    /**
     * Update activity timeline
     */
    updateActivityTimeline() {
        const timeline = document.getElementById('activity-timeline');
        if (!timeline) return;

        timeline.innerHTML = '';

        this.activityFeed.forEach(activity => {
            const activityItem = document.createElement('div');
            activityItem.className = 'activity-item';

            const timeAgo = this.formatTimeAgo(activity.timestamp);
            const icon = this.getActivityIcon(activity.activityType);

            activityItem.innerHTML = `
                <div class="activity-icon">${icon}</div>
                <div class="activity-content">
                    <div class="activity-text">${activity.text}</div>
                    <div class="activity-time">${timeAgo}</div>
                </div>
            `;

            timeline.appendChild(activityItem);
        });

        if (this.activityFeed.length === 0) {
            timeline.innerHTML = '<div class="empty-state">No recent activity</div>';
        }
    }

    /**
     * Show share modal
     */
    showShareModal() {
        const modal = document.getElementById('share-modal');
        if (modal) {
            modal.classList.add('active');
        }
    }

    /**
     * Hide share modal
     */
    hideShareModal() {
        const modal = document.getElementById('share-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    /**
     * Handle share confirmation
     */
    async handleShareConfirm() {
        const emailsInput = document.getElementById('share-emails');
        const permissionSelect = document.getElementById('share-permission');

        if (!emailsInput || !permissionSelect) return;

        const emails = emailsInput.value.split(',').map(e => e.trim()).filter(e => e);
        const permission = permissionSelect.value;

        if (emails.length === 0) {
            alert('Please enter at least one email address');
            return;
        }

        try {
            await this.shareNotebook(this.notebookId, emails, permission);
            this.hideShareModal();
            emailsInput.value = '';
            this.showNotification('Notebook shared successfully', 'success');
        } catch (error) {
            alert('Failed to share notebook: ' + error.message);
        }
    }

    /**
     * Update cursor element for user
     */
    updateCursorElement(message) {
        const container = document.getElementById('collaboration-cursors');
        if (!container) return;

        let cursorElement = container.querySelector(`[data-user-id="${message.userId}"]`);

        if (!cursorElement) {
            cursorElement = document.createElement('div');
            cursorElement.className = 'remote-cursor';
            cursorElement.dataset.userId = message.userId;
            cursorElement.style.borderColor = message.userColor;

            const label = document.createElement('div');
            label.className = 'cursor-label';
            label.style.backgroundColor = message.userColor;
            label.textContent = message.userName;
            cursorElement.appendChild(label);

            container.appendChild(cursorElement);
        }

        // Position cursor
        const cellElement = document.querySelector(`[data-cell-id="${message.cellId}"]`);
        if (cellElement) {
            const editor = cellElement.querySelector('.cell-editor');
            if (editor) {
                // Calculate position based on line and column
                const rect = editor.getBoundingClientRect();
                const lineHeight = parseInt(getComputedStyle(editor).lineHeight);
                const charWidth = 8; // Approximate character width

                cursorElement.style.left = (rect.left + message.position.column * charWidth) + 'px';
                cursorElement.style.top = (rect.top + message.position.line * lineHeight) + 'px';
                cursorElement.style.display = 'block';
            }
        }
    }

    /**
     * Remove cursor element for user
     */
    removeCursorElement(userId) {
        const container = document.getElementById('collaboration-cursors');
        if (!container) return;

        const cursorElement = container.querySelector(`[data-user-id="${userId}"]`);
        if (cursorElement) {
            cursorElement.remove();
        }
    }

    /**
     * Show edit indicator
     */
    showEditIndicator(cellId, userName) {
        const cellElement = document.querySelector(`[data-cell-id="${cellId}"]`);
        if (!cellElement) return;

        let indicator = cellElement.querySelector('.edit-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'edit-indicator';
            cellElement.appendChild(indicator);
        }

        indicator.textContent = `${userName} is editing...`;
        indicator.style.display = 'block';

        // Hide after 3 seconds
        setTimeout(() => {
            indicator.style.display = 'none';
        }, 3000);
    }

    /**
     * Update cell comment indicator
     */
    updateCellCommentIndicator(cellId) {
        const cellElement = document.querySelector(`[data-cell-id="${cellId}"]`);
        if (!cellElement) return;

        const comments = this.comments.get(cellId) || [];
        const unresolvedCount = comments.filter(c => !c.resolved).length;

        let indicator = cellElement.querySelector('.comment-indicator');

        if (unresolvedCount > 0) {
            if (!indicator) {
                indicator = document.createElement('div');
                indicator.className = 'comment-indicator';
                indicator.addEventListener('click', () => {
                    this.scrollToComments(cellId);
                });
                cellElement.appendChild(indicator);
            }
            indicator.textContent = unresolvedCount;
            indicator.title = `${unresolvedCount} comment${unresolvedCount > 1 ? 's' : ''}`;
        } else if (indicator) {
            indicator.remove();
        }
    }

    /**
     * Scroll to comments for a cell
     */
    scrollToComments(cellId) {
        const commentsPanel = document.getElementById('comments-panel');
        if (commentsPanel) {
            commentsPanel.classList.remove('collapsed');
        }

        const comments = this.comments.get(cellId) || [];
        if (comments.length > 0) {
            const firstComment = document.querySelector(`[data-comment-id="${comments[0].id}"]`);
            if (firstComment) {
                firstComment.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstComment.classList.add('highlight');
                setTimeout(() => firstComment.classList.remove('highlight'), 2000);
            }
        }
    }

    /**
     * Show reply input
     */
    showReplyInput(commentId, cellId) {
        // Implementation for showing reply input
        console.log('Show reply input for comment:', commentId);
    }

    /**
     * Show edit input
     */
    showEditInput(commentId) {
        // Implementation for showing edit input
        console.log('Show edit input for comment:', commentId);
    }

    /**
     * Show notification
     */
    showNotification(message, level = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${level}`;
        notification.innerHTML = `
            <div class="notification-content">${message}</div>
            <button class="notification-close">&times;</button>
        `;

        // Add to DOM
        let notificationContainer = document.getElementById('notification-container');
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.id = 'notification-container';
            document.body.appendChild(notificationContainer);
        }

        notificationContainer.appendChild(notification);

        // Close button
        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => {
            notification.remove();
        });

        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    /**
     * Render comment text with @mentions
     */
    renderCommentText(text, mentions) {
        let rendered = text;

        // Replace @mentions with highlighted spans
        mentions.forEach(userId => {
            const user = this.activeUsers.get(userId);
            if (user) {
                const regex = new RegExp(`@${user.userName}`, 'gi');
                rendered = rendered.replace(regex, `<span class="mention">@${user.userName}</span>`);
            }
        });

        return rendered;
    }

    /**
     * Format timestamp as time ago
     */
    formatTimeAgo(timestamp) {
        const now = Date.now();
        const diff = now - timestamp;

        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 0) return `${days}d ago`;
        if (hours > 0) return `${hours}h ago`;
        if (minutes > 0) return `${minutes}m ago`;
        return 'just now';
    }

    /**
     * Get activity icon
     */
    getActivityIcon(activityType) {
        const icons = {
            edit: '✏️',
            comment: '💬',
            share: '🔗',
            join: '👋',
            leave: '👋',
            create: '➕',
            delete: '🗑️'
        };
        return icons[activityType] || '📝';
    }

    /**
     * Generate unique ID
     */
    generateId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Generate user color based on user ID
     */
    generateUserColor(userId) {
        const colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788'
        ];

        let hash = 0;
        for (let i = 0; i < userId.length; i++) {
            hash = userId.charCodeAt(i) + ((hash << 5) - hash);
        }

        return colors[Math.abs(hash) % colors.length];
    }

    /**
     * Event emitter methods
     */
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event).push(handler);
    }

    off(event, handler) {
        if (!this.eventHandlers.has(event)) return;
        const handlers = this.eventHandlers.get(event);
        const index = handlers.indexOf(handler);
        if (index > -1) {
            handlers.splice(index, 1);
        }
    }

    emit(event, data) {
        if (!this.eventHandlers.has(event)) return;
        this.eventHandlers.get(event).forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                console.error(`Error in event handler for ${event}:`, error);
            }
        });
    }

    /**
     * Get current user's permission level
     */
    async getPermission(notebookId, userId) {
        try {
            const response = await fetch(`/api/notebooks/${notebookId}/permissions/${userId}`);
            if (!response.ok) {
                throw new Error('Failed to get permission');
            }
            return await response.json();
        } catch (error) {
            console.error('Error getting permission:', error);
            return { permission: 'view' }; // Default to view
        }
    }

    /**
     * Check if user has permission
     */
    hasPermission(requiredPermission) {
        const permissionLevels = { view: 1, edit: 2, admin: 3 };
        const userLevel = permissionLevels[this.userPermission || 'view'];
        const requiredLevel = permissionLevels[requiredPermission];
        return userLevel >= requiredLevel;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CollaborationManager;
}
