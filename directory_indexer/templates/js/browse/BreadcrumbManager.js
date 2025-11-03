/**
 * BreadcrumbManager.js
 * Manages breadcrumb navigation in browse mode
 */

/**
 * Manages the breadcrumb trail showing current folder path
 */
class BreadcrumbManager {
    /**
     * Initialize breadcrumb manager
     * @param {HTMLElement} container - Breadcrumb container element
     * @param {HTMLElement} upButton - Up button element
     * @param {BrowseState} state - Browse state instance
     * @param {Object} rootNode - Root directory node
     * @param {Function} onNavigate - Callback when breadcrumb is clicked
     */
    constructor(container, upButton, state, rootNode, onNavigate) {
        this.container = container;
        this.upButton = upButton;
        this.state = state;
        this.rootNode = rootNode;
        this.onNavigate = onNavigate;
    }

    /**
     * Render breadcrumb trail for current path
     */
    render() {
        this.container.innerHTML = '';
        this.container.appendChild(this.upButton);

        // Enable/disable up button
        this.upButton.disabled = !this.state.currentPath;

        const parts = this.state.currentPath ? this.state.currentPath.split('/') : [];

        // Root item
        const rootItem = document.createElement('span');
        rootItem.className = 'breadcrumb-item' + (this.state.currentPath === '' ? ' active' : '');
        rootItem.textContent = `📁 ${this.rootNode.name}`;
        rootItem.dataset.path = '';
        if (this.state.currentPath !== '') {
            rootItem.addEventListener('click', () => this.onNavigate(''));
        }
        this.container.appendChild(rootItem);

        // Path parts
        parts.forEach((part, index) => {
            const separator = document.createElement('span');
            separator.className = 'breadcrumb-separator';
            separator.textContent = '/';
            this.container.appendChild(separator);

            const partPath = parts.slice(0, index + 1).join('/');
            const item = document.createElement('span');
            item.className = 'breadcrumb-item' + (partPath === this.state.currentPath ? ' active' : '');
            item.textContent = part;
            item.dataset.path = partPath;
            if (partPath !== this.state.currentPath) {
                item.addEventListener('click', () => this.onNavigate(partPath));
            }
            this.container.appendChild(item);
        });
    }

    /**
     * Get current path from breadcrumb
     * @returns {string} Current path
     */
    getPath() {
        return this.state.currentPath;
    }

    /**
     * Navigate to a specific path via breadcrumb
     * @param {string} path - Path to navigate to
     */
    navigateTo(path) {
        this.onNavigate(path);
    }

    /**
     * Update breadcrumb when path changes
     * @param {string} path - New path
     */
    update(path) {
        this.state.setPath(path);
        this.render();
    }
}
