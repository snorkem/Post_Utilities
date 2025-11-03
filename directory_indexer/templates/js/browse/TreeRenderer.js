/**
 * TreeRenderer.js
 * Renders the hierarchical folder tree in the sidebar
 */

/**
 * Renders and manages the folder tree navigation sidebar
 */
class TreeRenderer {
    /**
     * Initialize tree renderer
     * @param {HTMLElement} container - Container element for the tree
     * @param {BrowseState} state - Browse state instance
     * @param {Object} rootNode - Root directory tree node
     * @param {Function} onNavigate - Callback when folder is navigated to
     */
    constructor(container, state, rootNode, onNavigate) {
        this.container = container;
        this.state = state;
        this.rootNode = rootNode;
        this.onNavigate = onNavigate;
    }

    /**
     * Render the entire tree from root
     */
    async render() {
        this.container.innerHTML = '';
        await this._renderNode(this.rootNode, this.container, '');
    }

    /**
     * Render a single tree node and its children
     * @param {Object} node - Directory node to render
     * @param {HTMLElement} parentElement - Parent DOM element
     * @param {string} path - Current path in the tree
     * @private
     */
    async _renderNode(node, parentElement, path) {
        const hasChildren = Object.keys(node.children || {}).length > 0;
        const isExpanded = this.state.expandedFolders.has(path);

        const treeItem = document.createElement('div');
        treeItem.className = 'tree-item' +
                            (isExpanded ? ' expanded' : '') +
                            (this.state.currentPath === path ? ' selected' : '');
        treeItem.dataset.path = path;

        const content = document.createElement('div');
        content.className = 'tree-item-content';

        // Toggle icon
        const toggle = document.createElement('div');
        toggle.className = 'tree-toggle' + (hasChildren ? '' : ' empty');
        toggle.textContent = hasChildren ? (isExpanded ? '▼' : '▶') : '';
        content.appendChild(toggle);

        // Folder icon
        const icon = document.createElement('span');
        icon.className = 'tree-icon';
        icon.textContent = '📁';
        content.appendChild(icon);

        // Label
        const label = document.createElement('span');
        label.className = 'tree-label';
        label.textContent = node.name;
        label.title = node.name;
        content.appendChild(label);

        // File count badge
        if (node.file_count > 0) {
            const badge = document.createElement('span');
            badge.className = 'tree-badge';
            badge.textContent = node.file_count;
            content.appendChild(badge);
        }

        // Folder size
        const size = document.createElement('span');
        size.className = 'tree-size';
        size.textContent = formatSize(node.total_size);
        content.appendChild(size);

        treeItem.appendChild(content);

        // Click handler
        content.addEventListener('click', async (e) => {
            e.stopPropagation();

            if (hasChildren && (e.target === toggle || e.target === icon)) {
                // Toggle expansion
                this.state.toggleFolder(path);
                this.state.save();
                await this.render();
            } else {
                // Navigate to folder
                await this.onNavigate(path);
            }
        });

        parentElement.appendChild(treeItem);

        // Render children if expanded
        if (hasChildren && isExpanded) {
            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'tree-children';
            treeItem.appendChild(childrenContainer);

            const sortedChildren = Object.entries(node.children).sort((a, b) =>
                a[1].name.localeCompare(b[1].name)
            );

            for (const [childName, childNode] of sortedChildren) {
                const childPath = path ? `${path}/${childName}` : childName;
                await this._renderNode(childNode, childrenContainer, childPath);
            }
        }
    }

    /**
     * Expand a folder by path
     * @param {string} path - Folder path to expand
     */
    expandFolder(path) {
        this.state.expandedFolders.add(path);
        this.state.save();
        this.render();
    }

    /**
     * Collapse a folder by path
     * @param {string} path - Folder path to collapse
     */
    collapseFolder(path) {
        this.state.expandedFolders.delete(path);
        this.state.save();
        this.render();
    }

    /**
     * Select a folder (highlight in tree)
     * @param {string} path - Folder path to select
     */
    selectFolder(path) {
        this.state.setPath(path);
        this.render();
    }
}
