/**
 * FileListRenderer.js
 * Renders the file list table in browse mode
 */

/**
 * Renders and manages the file list display in browse mode
 */
class FileListRenderer {
    /**
     * Initialize file list renderer
     * @param {HTMLElement} tbody - Table body element for file rows
     * @param {HTMLElement} emptyState - Empty state element
     * @param {HTMLElement} countElement - Element to display file count
     * @param {BrowseState} state - Browse state instance
     * @param {Object} rootNode - Root directory node
     * @param {Function} onFolderClick - Callback when folder is clicked
     */
    constructor(tbody, emptyState, countElement, state, rootNode, onFolderClick) {
        this.tbody = tbody;
        this.emptyState = emptyState;
        this.countElement = countElement;
        this.state = state;
        this.rootNode = rootNode;
        this.onFolderClick = onFolderClick;
    }

    /**
     * Render file list
     * @param {Array} items - Array of files and folders to render
     * @param {number} total - Total number of items
     */
    render(items, total) {
        this.tbody.innerHTML = '';

        if (items.length === 0) {
            this.tbody.style.display = 'none';
            this.emptyState.style.display = 'flex';
            return;
        }

        this.tbody.style.display = '';
        this.emptyState.style.display = 'none';

        items.forEach(item => {
            const row = this._createFileRow(item);
            this.tbody.appendChild(row);
        });

        // Update count
        if (this.countElement) {
            this.countElement.textContent = `${total} items`;
        }
    }

    /**
     * Render global search results
     * @param {Array} results - Search results to render
     */
    renderSearchResults(results) {
        this.tbody.innerHTML = '';

        if (results.length === 0) {
            this.tbody.style.display = 'none';
            this.emptyState.style.display = 'flex';
            return;
        }

        this.tbody.style.display = '';
        this.emptyState.style.display = 'none';

        // Group results by folder
        const grouped = this._groupByFolder(results);

        Object.entries(grouped).forEach(([folderPath, items]) => {
            // Add folder header
            const header = document.createElement('tr');
            header.className = 'search-folder-header';
            const displayName = folderPath || (this.rootNode ? this.rootNode.name : 'Root');
            header.innerHTML = `<td colspan="5" style="background: #f0f0f0; font-weight: 600; padding: 10px;">📁 ${displayName}</td>`;
            this.tbody.appendChild(header);

            // Add files
            items.forEach(item => {
                const row = this._createFileRow(item);
                this.tbody.appendChild(row);
            });
        });

        // Show result count
        if (this.countElement) {
            this.countElement.textContent = `${results.length} results (limited to 1000)`;
        }
    }

    /**
     * Create a table row for a file or folder
     * @param {Object} item - File or folder item
     * @returns {HTMLElement} Table row element
     * @private
     */
    _createFileRow(item) {
        const row = document.createElement('tr');

        if (item.type === 'folder') {
            row.className = 'folder-row';
            row.innerHTML = `
                <td>
                    <div class="file-name">
                        <span class="file-icon">📁</span>
                        <span>${escapeHtml(item.name)}</span>
                    </div>
                </td>
                <td><span class="file-extension">folder</span></td>
                <td>${formatSize(item.totalSize)}</td>
                <td>${item.fileCount} files</td>
                <td>-</td>
            `;
            row.style.cursor = 'pointer';
            row.addEventListener('click', () => {
                this.onFolderClick(item.path);
            });
        } else {
            row.innerHTML = `
                <td>
                    <div class="file-name">
                        <span class="file-icon">${item.icon}</span>
                        <span>${escapeHtml(item.name)}</span>
                    </div>
                </td>
                <td><span class="file-extension">${escapeHtml(item.extension)}</span></td>
                <td>${item.size_human}</td>
                <td class="modified">${item.modified}</td>
                <td class="modified">${item.created}</td>
            `;
        }

        return row;
    }

    /**
     * Group items by folder path
     * @param {Array} items - Items to group
     * @returns {Object} Items grouped by folder path
     * @private
     */
    _groupByFolder(items) {
        const grouped = {};
        items.forEach(item => {
            const folder = item.directory || item.path || '';
            if (!grouped[folder]) {
                grouped[folder] = [];
            }
            grouped[folder].push(item);
        });
        return grouped;
    }
}
