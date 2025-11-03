/**
 * BrowseState.js
 * State management for browse mode with observer pattern and localStorage persistence
 */

/**
 * Manages the state for browse mode navigation and UI
 * Implements observer pattern for reactive state updates
 */
class BrowseState {
    /**
     * Initialize browse state with default values
     */
    constructor() {
        this.currentPath = '';
        this.expandedFolders = new Set();
        this.currentSort = { column: 'name', ascending: true, foldersFirst: true };
        this.searchQuery = '';
        this.searchScope = 'local'; // 'local' or 'global'
        this.listeners = [];
    }

    /**
     * Register a listener for state changes
     * @param {Function} listener - Callback function to execute on state change
     */
    onChange(listener) {
        this.listeners.push(listener);
    }

    /**
     * Notify all registered listeners of state change
     */
    notify() {
        this.listeners.forEach(fn => fn(this));
    }

    /**
     * Set the current folder path
     * @param {string} path - New folder path
     */
    setPath(path) {
        this.currentPath = path;
        this.notify();
    }

    /**
     * Toggle folder expansion state in the tree
     * @param {string} path - Folder path to toggle
     */
    toggleFolder(path) {
        if (this.expandedFolders.has(path)) {
            this.expandedFolders.delete(path);
        } else {
            this.expandedFolders.add(path);
        }
        this.notify();
    }

    /**
     * Set sort configuration
     * @param {string} column - Column name to sort by
     * @param {boolean} ascending - Sort direction
     * @param {boolean} foldersFirst - Whether to show folders before files
     */
    setSort(column, ascending, foldersFirst = true) {
        this.currentSort = { column, ascending, foldersFirst };
        localStorage.setItem('browseSort', JSON.stringify(this.currentSort));
        this.notify();
    }

    /**
     * Set search query and scope
     * @param {string} query - Search query string
     * @param {string} scope - Search scope ('local' or 'global')
     */
    setSearch(query, scope) {
        this.searchQuery = query;
        this.searchScope = scope;
        this.notify();
    }

    /**
     * Restore state from localStorage
     * @returns {BrowseState} New state instance with restored values
     */
    static restore() {
        const state = new BrowseState();

        // Restore sort preferences
        const savedSort = localStorage.getItem('browseSort');
        if (savedSort) {
            try {
                state.currentSort = JSON.parse(savedSort);
            } catch (e) {
                console.warn('Failed to restore sort preferences:', e);
            }
        }

        // Restore expanded folders
        const savedExpanded = localStorage.getItem('browseExpandedFolders');
        if (savedExpanded) {
            try {
                const expanded = JSON.parse(savedExpanded);
                state.expandedFolders = new Set(expanded);
            } catch (e) {
                console.warn('Failed to restore expanded folders:', e);
            }
        }

        return state;
    }

    /**
     * Save current state to localStorage
     */
    save() {
        localStorage.setItem('browseExpandedFolders', JSON.stringify(Array.from(this.expandedFolders)));
    }
}
