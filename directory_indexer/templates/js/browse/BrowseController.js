/**
 * BrowseController.js
 * Main controller coordinating all browse mode functionality
 */

/**
 * Main controller for browse mode - coordinates state, tree, file list, and breadcrumb
 */
class BrowseController {
    /**
     * Initialize browse controller
     * @param {DataService} dataService - Data service for file/folder access
     * @param {BrowseState} state - Browse state instance
     */
    constructor(dataService, state) {
        this.dataService = dataService;
        this.state = state;
        this.searchDebounce = null;
        this.currentFolder = null;

        // Components (initialized in init())
        this.treeRenderer = null;
        this.fileListRenderer = null;
        this.breadcrumbManager = null;

        // Listen to state changes
        state.onChange(() => this.handleStateChange());
    }

    /**
     * Initialize browse mode - setup components and event listeners
     */
    async init() {
        // Initialize components
        const treeContainer = document.getElementById('folderTree');
        const tbody = document.getElementById('browseTableBody');
        const emptyState = document.getElementById('browseEmptyState');
        const countElement = document.getElementById('browseFileCount');
        const breadcrumbContainer = document.getElementById('browseBreadcrumb');
        const upButton = document.getElementById('upButton');

        // Get root node from data service
        const rootNode = this.dataService.dataSource;

        this.treeRenderer = new TreeRenderer(
            treeContainer,
            this.state,
            rootNode,
            (path) => this.navigateToFolder(path)
        );

        this.fileListRenderer = new FileListRenderer(
            tbody,
            emptyState,
            countElement,
            this.state,
            rootNode,
            (path) => this.handleFolderClick(path)
        );

        this.breadcrumbManager = new BreadcrumbManager(
            breadcrumbContainer,
            upButton,
            this.state,
            rootNode,
            (path) => this.navigateToFolder(path)
        );

        this.setupEventListeners();
        await this.navigateToFolder('');
    }

    /**
     * Handle state changes
     */
    handleStateChange() {
        // State changed, re-render if needed
        // For now, renders are triggered explicitly
    }

    /**
     * Navigate to a folder
     * @param {string} path - Folder path to navigate to
     */
    async navigateToFolder(path) {
        this.state.setPath(path);
        const folder = await this.dataService.getFolder(path);
        this.currentFolder = folder;
        await this.render();
    }

    /**
     * Navigate up one level in the folder hierarchy
     */
    async navigateUp() {
        if (!this.state.currentPath) return;
        const parts = this.state.currentPath.split('/');
        parts.pop();
        await this.navigateToFolder(parts.join('/'));
    }

    /**
     * Sort file list by column
     * @param {string} column - Column name to sort by
     */
    async sort(column) {
        const current = this.state.currentSort;
        const ascending = current.column === column ? !current.ascending : true;
        this.state.setSort(column, ascending, true);
        await this.renderFileList();
    }

    /**
     * Search files
     * @param {string} query - Search query
     * @param {string} scope - Search scope ('local' or 'global')
     */
    async search(query, scope) {
        clearTimeout(this.searchDebounce);
        this.searchDebounce = setTimeout(async () => {
            this.state.setSearch(query, scope);
            if (scope === 'global' && query) {
                await this.renderGlobalSearch(query);
            } else {
                await this.renderFileList();
            }
        }, 300);
    }

    /**
     * Render all components
     */
    async render() {
        await this.renderTree();
        await this.renderBreadcrumb();
        await this.renderFileList();
    }

    /**
     * Render folder tree
     */
    async renderTree() {
        if (this.treeRenderer) {
            await this.treeRenderer.render();
        }
    }

    /**
     * Render breadcrumb navigation
     */
    async renderBreadcrumb() {
        if (this.breadcrumbManager) {
            this.breadcrumbManager.render();
        }
    }

    /**
     * Render file list for current folder
     */
    async renderFileList() {
        const { items, total } = await this.dataService.getFiles(
            this.state.currentPath,
            {
                sort: this.state.currentSort,
                search: this.state.searchScope === 'local' ? this.state.searchQuery : '',
                limit: 1000,
                offset: 0
            }
        );

        if (this.fileListRenderer) {
            this.fileListRenderer.render(items, total);
        }
    }

    /**
     * Render global search results
     * @param {string} query - Search query
     */
    async renderGlobalSearch(query) {
        const results = await this.dataService.searchGlobal(query);

        if (this.fileListRenderer) {
            this.fileListRenderer.renderSearchResults(results);
        }
    }

    /**
     * Handle folder click in file list
     * @param {string} path - Path of clicked folder
     */
    async handleFolderClick(path) {
        await this.navigateToFolder(path);
        this.state.expandedFolders.add(this.state.currentPath);
        this.state.save();
        await this.renderTree();
    }

    /**
     * Setup event listeners for browse mode UI
     */
    setupEventListeners() {
        // Search box
        const searchBox = document.getElementById('browseSearchBox');
        const searchAllCheckbox = document.getElementById('searchAllFolders');

        if (searchBox) {
            searchBox.addEventListener('input', (e) => {
                const scope = (searchAllCheckbox && searchAllCheckbox.checked) ? 'global' : 'local';
                this.search(e.target.value, scope);
            });
        }

        if (searchAllCheckbox) {
            searchAllCheckbox.addEventListener('change', (e) => {
                const query = (searchBox && searchBox.value) || '';
                const scope = e.target.checked ? 'global' : 'local';
                this.search(query, scope);
            });
        }

        // Up button
        const upButton = document.getElementById('upButton');
        if (upButton) {
            upButton.addEventListener('click', () => this.navigateUp());
        }

        // Sort headers
        document.querySelectorAll('#browseFileList th[data-column]').forEach(header => {
            header.addEventListener('click', () => {
                this.sort(header.dataset.column);
            });
        });

        // Splitter resize
        this.setupSplitterResize();
    }

    /**
     * Setup resizable splitter for sidebar
     */
    setupSplitterResize() {
        const splitter = document.getElementById('browseSplitter');
        const sidebar = document.querySelector('.browse-sidebar');
        let isResizing = false;

        if (!splitter) return;

        splitter.addEventListener('mousedown', (e) => {
            isResizing = true;
            splitter.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            const container = document.querySelector('.browse-container');
            if (!container) return;

            const containerRect = container.getBoundingClientRect();
            const newWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
            if (newWidth >= 15 && newWidth <= 50) {
                document.documentElement.style.setProperty('--sidebar-width', newWidth + '%');
                localStorage.setItem('browseSidebarWidth', newWidth);
            }
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                splitter.classList.remove('resizing');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });

        // Restore sidebar width
        const savedWidth = localStorage.getItem('browseSidebarWidth');
        if (savedWidth) {
            document.documentElement.style.setProperty('--sidebar-width', savedWidth + '%');
        }
    }
}
