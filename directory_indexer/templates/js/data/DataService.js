/**
 * DataService.js
 * Unified interface for data access across JSON and database modes
 */

/**
 * Abstract data service interface for file/folder access
 * Provides a unified API for both JSON (inline) and database modes
 */
class DataService {
    /**
     * Initialize data service
     * @param {string} mode - Mode: 'inline' (JSON) or 'database' (SQLite)
     * @param {Object|Object} dataSource - Directory tree (inline) or db instance (database)
     */
    constructor(mode, dataSource) {
        this.mode = mode; // 'inline' or 'database'
        this.dataSource = dataSource; // directoryTree or db instance
    }

    /**
     * Get folder information by path
     * @param {string} path - Folder path
     * @returns {Promise<Object>} Folder object with name, path, fileCount, totalSize, children, files
     */
    async getFolder(path) {
        if (this.mode === 'inline') {
            return this._getFolderInline(path);
        } else {
            return await this._getFolderFromDB(path);
        }
    }

    /**
     * Get files and folders in a path with filtering and sorting
     * @param {string} path - Folder path
     * @param {Object} options - Options for sort, search, pagination
     * @returns {Promise<Object>} Object with items array and total count
     */
    async getFiles(path, options = {}) {
        const defaults = {
            sort: { column: 'name', ascending: true, foldersFirst: true },
            search: '',
            limit: 1000,
            offset: 0
        };
        const opts = { ...defaults, ...options };

        if (this.mode === 'inline') {
            return this._getFilesInline(path, opts);
        } else {
            return await this._getFilesFromDB(path, opts);
        }
    }

    /**
     * Search globally across all files and folders
     * @param {string} query - Search query
     * @returns {Promise<Array>} Array of matching files and folders
     */
    async searchGlobal(query) {
        if (this.mode === 'inline') {
            return this._searchInline(query);
        } else {
            return await this._searchDB(query);
        }
    }

    /**
     * Get all files (for files tab)
     * @returns {Promise<Array>} Array of all files
     */
    async getAllFiles() {
        if (this.mode === 'inline') {
            return this._getAllFilesInline();
        } else {
            return await this._getAllFilesFromDB();
        }
    }

    // ============ INLINE MODE IMPLEMENTATIONS ============

    /**
     * Get folder from inline tree structure
     * @param {string} path - Folder path
     * @returns {Object} Folder object
     * @private
     */
    _getFolderInline(path) {
        let node = this.dataSource; // directoryTree root
        if (path) {
            const parts = path.split('/');
            for (const part of parts) {
                node = node.children[part];
                if (!node) return null;
            }
        }
        return {
            name: node.name,
            path: path,
            fileCount: node.file_count,
            totalSize: node.total_size,
            children: Object.keys(node.children || {}),
            files: node.files || []
        };
    }

    /**
     * Get files in a folder from inline tree structure
     * @param {string} path - Folder path
     * @param {Object} opts - Options for filtering/sorting
     * @returns {Object} Object with items and total
     * @private
     */
    _getFilesInline(path, opts) {
        const folder = this._getFolderInline(path);
        if (!folder) return { items: [], total: 0 };

        let files = [...folder.files];

        // Apply search filter to files
        if (opts.search) {
            const query = opts.search.toLowerCase();
            files = files.filter(f =>
                f.name.toLowerCase().includes(query) ||
                f.extension.toLowerCase().includes(query)
            );
        }

        // Get child folders
        let folders = folder.children.map(name => {
            const childPath = path ? `${path}/${name}` : name;
            const childFolder = this._getFolderInline(childPath);
            return {
                type: 'folder',
                name: name,
                fileCount: childFolder.fileCount,
                totalSize: childFolder.totalSize,
                path: childPath
            };
        });

        // Apply search filter to folders
        if (opts.search) {
            const query = opts.search.toLowerCase();
            folders = folders.filter(f => f.name.toLowerCase().includes(query));
        }

        // Sort folders and files separately
        folders = this._sortItems(folders, opts.sort);
        files = this._sortItems(files, opts.sort);

        // Combine with folders first (if foldersFirst is enabled)
        const combined = opts.sort.foldersFirst ? [...folders, ...files] : [...folders, ...files].sort((a, b) =>
            compareWithFoldersFirst(a, b, opts.sort.column, opts.sort.ascending, false)
        );

        const total = combined.length;

        // Apply pagination
        const paginated = combined.slice(opts.offset, opts.offset + opts.limit);

        return { items: paginated, total };
    }

    /**
     * Search inline tree structure recursively
     * @param {string} query - Search query
     * @returns {Array} Array of matching items
     * @private
     */
    _searchInline(query) {
        const results = [];
        const queryLower = query.toLowerCase();

        const searchNode = (node, currentPath) => {
            // Search files in current node
            (node.files || []).forEach(file => {
                if (file.name.toLowerCase().includes(queryLower) ||
                    file.extension.toLowerCase().includes(queryLower)) {
                    results.push({
                        ...file,
                        path: currentPath,
                        type: 'file'
                    });
                }
            });

            // Search folder names and recurse
            Object.entries(node.children || {}).forEach(([name, child]) => {
                const childPath = currentPath ? `${currentPath}/${name}` : name;
                if (name.toLowerCase().includes(queryLower)) {
                    results.push({
                        type: 'folder',
                        name: name,
                        path: childPath,
                        fileCount: child.file_count,
                        totalSize: child.total_size
                    });
                }
                searchNode(child, childPath);
            });
        };

        searchNode(this.dataSource, '');
        return results.slice(0, 1000); // Limit to 1000 results
    }

    /**
     * Get all files from inline tree structure
     * @returns {Array} Array of all files
     * @private
     */
    _getAllFilesInline() {
        const allFiles = [];

        const collectFiles = (node, currentPath) => {
            // Collect files from current node
            (node.files || []).forEach(file => {
                allFiles.push({
                    ...file,
                    directory: currentPath
                });
            });

            // Recurse into child folders
            Object.entries(node.children || {}).forEach(([name, child]) => {
                const childPath = currentPath ? `${currentPath}/${name}` : name;
                collectFiles(child, childPath);
            });
        };

        collectFiles(this.dataSource, '');
        return allFiles;
    }

    /**
     * Sort items by column
     * @param {Array} items - Items to sort
     * @param {Object} sort - Sort configuration
     * @returns {Array} Sorted items
     * @private
     */
    _sortItems(items, sort) {
        return items.sort((a, b) =>
            compareWithFoldersFirst(a, b, sort.column, sort.ascending, false)
        );
    }

    // ============ DATABASE MODE IMPLEMENTATIONS ============

    /**
     * Get folder from database
     * @param {string} path - Folder path
     * @returns {Promise<Object>} Folder object
     * @private
     */
    async _getFolderFromDB(path) {
        try {
            // Get direct files in this folder
            const filesQuery = path === '' || path === null
                ? `SELECT name, extension, directory, size_bytes, modified, created, icon FROM files WHERE directory = '' OR directory IS NULL`
                : `SELECT name, extension, directory, size_bytes, modified, created, icon FROM files WHERE directory = ?`;

            const filesStmt = this.dataSource.prepare(filesQuery);
            if (path) {
                filesStmt.bind([path]);
            }

            const files = [];
            while (filesStmt.step()) {
                const row = filesStmt.get();
                files.push({
                    name: row[0],
                    extension: row[1],
                    size: row[3],
                    modified: row[4],
                    created: row[5],
                    icon: row[6]
                });
            }
            filesStmt.free();

            // Get child folders by finding unique directory prefixes
            const childFolders = new Set();
            const pathPrefix = path ? `${path}/` : '';
            const pathPrefixPattern = path ? `${path}/%` : '%';

            const dirsQuery = `SELECT DISTINCT directory FROM files WHERE directory LIKE ?`;
            const dirsStmt = this.dataSource.prepare(dirsQuery);
            dirsStmt.bind([pathPrefixPattern]);

            while (dirsStmt.step()) {
                const dir = dirsStmt.get()[0];
                if (dir && dir !== path) {
                    // Check if this is a direct child
                    if (path === '' || path === null) {
                        // Root level - get first segment
                        const firstSegment = dir.split('/')[0];
                        if (firstSegment) {
                            childFolders.add(firstSegment);
                        }
                    } else if (dir.startsWith(pathPrefix)) {
                        // Get the next segment after the current path
                        const remainder = dir.substring(pathPrefix.length);
                        const nextSegment = remainder.split('/')[0];
                        if (nextSegment) {
                            childFolders.add(nextSegment);
                        }
                    }
                }
            }
            dirsStmt.free();

            // Get folder stats
            const stats = await this._getFolderStats(path);

            // Get folder name
            const folderName = path ? path.split('/').pop() : 'root';

            return {
                name: folderName,
                path: path || '',
                fileCount: stats.fileCount,
                totalSize: stats.totalSize,
                children: Array.from(childFolders).sort(),
                files: files
            };
        } catch (error) {
            console.error('Error getting folder from database:', error);
            return { name: 'root', path: '', fileCount: 0, totalSize: 0, children: [], files: [] };
        }
    }

    /**
     * Get files from database
     * @param {string} path - Folder path
     * @param {Object} opts - Options
     * @returns {Promise<Object>} Object with items and total
     * @private
     */
    async _getFilesFromDB(path, opts) {
        try {
            const folder = await this._getFolderFromDB(path);
            if (!folder) return { items: [], total: 0 };

            let files = [...folder.files];

            // Apply search filter to files
            if (opts.search) {
                const query = opts.search.toLowerCase();
                files = files.filter(f =>
                    f.name.toLowerCase().includes(query) ||
                    f.extension.toLowerCase().includes(query)
                );
            }

            // Get child folders with stats
            let folders = [];
            for (const childName of folder.children) {
                const childPath = path ? `${path}/${childName}` : childName;
                const stats = await this._getFolderStats(childPath);

                folders.push({
                    type: 'folder',
                    name: childName,
                    fileCount: stats.fileCount,
                    totalSize: stats.totalSize,
                    path: childPath
                });
            }

            // Apply search filter to folders
            if (opts.search) {
                const query = opts.search.toLowerCase();
                folders = folders.filter(f => f.name.toLowerCase().includes(query));
            }

            // Sort folders and files separately
            folders = this._sortItems(folders, opts.sort);
            files = this._sortItems(files, opts.sort);

            // Combine with folders first (if foldersFirst is enabled)
            const combined = opts.sort.foldersFirst ? [...folders, ...files] : [...folders, ...files].sort((a, b) =>
                compareWithFoldersFirst(a, b, opts.sort.column, opts.sort.ascending, false)
            );

            const total = combined.length;

            // Apply pagination
            const paginated = combined.slice(opts.offset, opts.offset + opts.limit);

            return { items: paginated, total };
        } catch (error) {
            console.error('Error getting files from database:', error);
            return { items: [], total: 0 };
        }
    }

    /**
     * Search database
     * @param {string} query - Search query
     * @returns {Promise<Array>} Search results
     * @private
     */
    async _searchDB(query) {
        try {
            const queryLower = query.toLowerCase();
            const searchPattern = `%${queryLower}%`;

            const sql = `
                SELECT name, extension, directory, size_bytes, modified, created, icon
                FROM files
                WHERE LOWER(name) LIKE ? OR LOWER(extension) LIKE ? OR LOWER(directory) LIKE ?
                ORDER BY name ASC
                LIMIT 1000
            `;

            const stmt = this.dataSource.prepare(sql);
            stmt.bind([searchPattern, searchPattern, searchPattern]);

            const results = [];
            while (stmt.step()) {
                const row = stmt.get();
                const directory = row[2];
                const fullPath = directory ? `${directory}/${row[0]}` : row[0];

                results.push({
                    type: 'file',
                    name: row[0],
                    extension: row[1],
                    path: directory,
                    directory: directory,
                    size: row[3],
                    totalSize: row[3],
                    modified: row[4],
                    created: row[5],
                    icon: row[6]
                });
            }
            stmt.free();

            // Also search for matching folder names by extracting unique directories
            const folderMatches = new Set();
            const folderQuery = `
                SELECT DISTINCT directory
                FROM files
                WHERE LOWER(directory) LIKE ?
                LIMIT 200
            `;

            const folderStmt = this.dataSource.prepare(folderQuery);
            folderStmt.bind([searchPattern]);

            while (folderStmt.step()) {
                const dir = folderStmt.get()[0];
                if (dir) {
                    // Split directory path and check each part for matches
                    const parts = dir.split('/');
                    let currentPath = '';
                    for (const part of parts) {
                        currentPath = currentPath ? `${currentPath}/${part}` : part;
                        if (part.toLowerCase().includes(queryLower) && !folderMatches.has(currentPath)) {
                            folderMatches.add(currentPath);
                        }
                    }
                }
            }
            folderStmt.free();

            // Add folder matches to results
            for (const folderPath of folderMatches) {
                // Get stats for this folder
                const stats = await this._getFolderStats(folderPath);
                const folderName = folderPath.split('/').pop();
                const parentPath = folderPath.substring(0, folderPath.lastIndexOf('/'));

                results.push({
                    type: 'folder',
                    name: folderName,
                    path: parentPath || '',
                    fileCount: stats.fileCount,
                    totalSize: stats.totalSize
                });
            }

            return results.slice(0, 1000); // Limit to 1000 total results
        } catch (error) {
            console.error('Error searching database:', error);
            return [];
        }
    }

    /**
     * Get all files from database
     * @returns {Promise<Array>} Array of all files
     * @private
     */
    async _getAllFilesFromDB() {
        try {
            const query = 'SELECT name, extension, directory, size_bytes, modified, created, icon FROM files ORDER BY name ASC';
            const stmt = this.dataSource.prepare(query);

            const allFiles = [];
            while (stmt.step()) {
                const row = stmt.get();
                allFiles.push({
                    name: row[0],
                    extension: row[1],
                    directory: row[2],
                    size: row[3],
                    modified: row[4],
                    created: row[5],
                    icon: row[6]
                });
            }
            stmt.free();

            return allFiles;
        } catch (error) {
            console.error('Error querying all files from database:', error);
            return [];
        }
    }

    /**
     * Get folder statistics (file count and total size)
     * @param {string} path - Folder path
     * @returns {Promise<Object>} Object with fileCount and totalSize
     * @private
     */
    async _getFolderStats(path) {
        try {
            // Query for files in this folder and all subfolders
            let query, params;

            if (path === '' || path === null) {
                // Root folder - count all files
                query = 'SELECT COUNT(*) as count, COALESCE(SUM(size_bytes), 0) as total_size FROM files';
                params = [];
            } else {
                // Specific folder - count files in this folder and subfolders
                query = `
                    SELECT COUNT(*) as count, COALESCE(SUM(size_bytes), 0) as total_size
                    FROM files
                    WHERE directory = ? OR directory LIKE ?
                `;
                params = [path, `${path}/%`];
            }

            const stmt = this.dataSource.prepare(query);
            if (params.length > 0) {
                stmt.bind(params);
            }
            stmt.step();

            const result = stmt.get();
            stmt.free();

            return {
                fileCount: result[0] || 0,
                totalSize: result[1] || 0
            };
        } catch (error) {
            console.error('Error getting folder stats:', error);
            return { fileCount: 0, totalSize: 0 };
        }
    }
}
