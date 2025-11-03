/**
 * JsonDataLoader.js
 * Data loader for JSON (inline) mode
 * Extends DataService to work with embedded JSON data
 */

/**
 * Data loader for JSON mode
 * Uses embedded window.fileData and directory tree
 */
class JsonDataLoader extends DataService {
    /**
     * Initialize JSON data loader
     * @param {Object} directoryTree - Root directory tree structure
     * @param {Array} fileData - Array of all file objects (optional, for Files tab)
     */
    constructor(directoryTree, fileData = null) {
        super('inline', directoryTree);
        this.fileData = fileData;
    }

    /**
     * Get all files for Files tab
     * @returns {Array} Array of all files
     */
    async getAllFiles() {
        if (this.fileData) {
            return this.fileData;
        }
        // Fallback to collecting from tree
        return this._getAllFilesInline();
    }

    /**
     * Get statistics about the dataset
     * @returns {Object} Statistics object
     */
    getStatistics() {
        const allFiles = this.fileData || this._getAllFilesInline();

        const stats = {
            totalFiles: allFiles.length,
            totalSize: allFiles.reduce((sum, f) => sum + (f.size || 0), 0),
            extensions: {},
            folders: new Set()
        };

        allFiles.forEach(file => {
            // Count extensions
            const ext = file.extension || 'no extension';
            if (!stats.extensions[ext]) {
                stats.extensions[ext] = { count: 0, size: 0 };
            }
            stats.extensions[ext].count++;
            stats.extensions[ext].size += file.size || 0;

            // Collect folders
            if (file.directory) {
                stats.folders.add(file.directory);
            }
        });

        return stats;
    }

    /**
     * Search files by query
     * @param {string} query - Search query
     * @param {Array} files - Files array to search (optional)
     * @returns {Array} Filtered files
     */
    searchFiles(query, files = null) {
        const filesToSearch = files || this.fileData || this._getAllFilesInline();
        const queryLower = query.toLowerCase();

        return filesToSearch.filter(file =>
            file.name.toLowerCase().includes(queryLower) ||
            file.extension.toLowerCase().includes(queryLower) ||
            (file.directory && file.directory.toLowerCase().includes(queryLower))
        );
    }

    /**
     * Filter files by extension
     * @param {string} extension - File extension to filter by
     * @param {Array} files - Files array to filter (optional)
     * @returns {Array} Filtered files
     */
    filterByExtension(extension, files = null) {
        const filesToFilter = files || this.fileData || this._getAllFilesInline();

        if (!extension || extension === 'all') {
            return filesToFilter;
        }

        return filesToFilter.filter(file => file.extension === extension);
    }

    /**
     * Sort files by column
     * @param {Array} files - Files to sort
     * @param {string} column - Column name
     * @param {boolean} ascending - Sort direction
     * @returns {Array} Sorted files
     */
    sortFiles(files, column, ascending) {
        return this._sortItems(files, { column, ascending, foldersFirst: false });
    }
}
