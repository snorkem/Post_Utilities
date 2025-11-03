/**
 * DatabaseLoader.js
 * Data loader for database mode using sql.js
 * Extends DataService to work with SQLite database
 */

/**
 * Data loader for database mode
 * Uses sql.js to query SQLite database
 */
class DatabaseLoader extends DataService {
    /**
     * Initialize database data loader
     * @param {Object} db - sql.js database instance
     */
    constructor(db) {
        super('database', db);
        this.db = db;
    }

    /**
     * Get all files from database
     * @param {Object} options - Query options (limit, offset, sort, filter)
     * @returns {Promise<Object>} Object with files array and total count
     */
    async getAllFiles(options = {}) {
        const defaults = {
            limit: 1000,
            offset: 0,
            sort: { column: 'name', ascending: true },
            search: '',
            extension: null
        };
        const opts = { ...defaults, ...options };

        try {
            // Build query
            let query = 'SELECT * FROM files WHERE 1=1';
            const params = [];

            // Add search filter
            if (opts.search) {
                query += ' AND (name LIKE ? OR extension LIKE ? OR directory LIKE ?)';
                const searchParam = `%${opts.search}%`;
                params.push(searchParam, searchParam, searchParam);
            }

            // Add extension filter
            if (opts.extension && opts.extension !== 'all') {
                query += ' AND extension = ?';
                params.push(opts.extension);
            }

            // Add sorting
            const sortColumn = this._mapSortColumn(opts.sort.column);
            const sortDir = opts.sort.ascending ? 'ASC' : 'DESC';
            query += ` ORDER BY ${sortColumn} ${sortDir}`;

            // Add pagination
            query += ' LIMIT ? OFFSET ?';
            params.push(opts.limit, opts.offset);

            // Execute query
            const stmt = this.db.prepare(query);
            stmt.bind(params);

            const files = [];
            while (stmt.step()) {
                const row = stmt.getAsObject();
                files.push(this._mapFileRow(row));
            }
            stmt.free();

            // Get total count
            let countQuery = 'SELECT COUNT(*) as count FROM files WHERE 1=1';
            const countParams = [];

            if (opts.search) {
                countQuery += ' AND (name LIKE ? OR extension LIKE ? OR directory LIKE ?)';
                const searchParam = `%${opts.search}%`;
                countParams.push(searchParam, searchParam, searchParam);
            }

            if (opts.extension && opts.extension !== 'all') {
                countQuery += ' AND extension = ?';
                countParams.push(opts.extension);
            }

            const countStmt = this.db.prepare(countQuery);
            countStmt.bind(countParams);
            countStmt.step();
            const total = countStmt.getAsObject().count;
            countStmt.free();

            return { files, total };
        } catch (error) {
            console.error('Database query error:', error);
            return { files: [], total: 0 };
        }
    }

    /**
     * Get statistics from database
     * @returns {Promise<Object>} Statistics object
     */
    async getStatistics() {
        try {
            const stats = {
                totalFiles: 0,
                totalSize: 0,
                extensions: {}
            };

            // Get total count and size
            const totalStmt = this.db.prepare('SELECT COUNT(*) as count, SUM(size) as total_size FROM files');
            totalStmt.step();
            const totalRow = totalStmt.getAsObject();
            stats.totalFiles = totalRow.count || 0;
            stats.totalSize = totalRow.total_size || 0;
            totalStmt.free();

            // Get extension statistics
            const extStmt = this.db.prepare('SELECT extension, COUNT(*) as count, SUM(size) as size FROM files GROUP BY extension ORDER BY count DESC');
            while (extStmt.step()) {
                const row = extStmt.getAsObject();
                stats.extensions[row.extension || 'no extension'] = {
                    count: row.count,
                    size: row.size || 0
                };
            }
            extStmt.free();

            return stats;
        } catch (error) {
            console.error('Database statistics error:', error);
            return { totalFiles: 0, totalSize: 0, extensions: {} };
        }
    }

    /**
     * Get unique extensions from database
     * @returns {Promise<Array>} Array of extension strings
     */
    async getExtensions() {
        try {
            const stmt = this.db.prepare('SELECT DISTINCT extension FROM files ORDER BY extension');
            const extensions = [];
            while (stmt.step()) {
                const row = stmt.getAsObject();
                extensions.push(row.extension);
            }
            stmt.free();
            return extensions;
        } catch (error) {
            console.error('Database extensions query error:', error);
            return [];
        }
    }

    /**
     * Search files in database
     * @param {string} query - Search query
     * @returns {Promise<Array>} Array of matching files
     */
    async searchFiles(query) {
        try {
            const stmt = this.db.prepare(`
                SELECT * FROM files
                WHERE name LIKE ? OR extension LIKE ? OR directory LIKE ?
                LIMIT 1000
            `);
            const searchParam = `%${query}%`;
            stmt.bind([searchParam, searchParam, searchParam]);

            const files = [];
            while (stmt.step()) {
                const row = stmt.getAsObject();
                files.push(this._mapFileRow(row));
            }
            stmt.free();

            return files;
        } catch (error) {
            console.error('Database search error:', error);
            return [];
        }
    }

    /**
     * Get largest files from database
     * @param {number} limit - Number of files to return
     * @returns {Promise<Array>} Array of largest files
     */
    async getLargestFiles(limit = 50) {
        try {
            const stmt = this.db.prepare('SELECT * FROM files ORDER BY size DESC LIMIT ?');
            stmt.bind([limit]);

            const files = [];
            while (stmt.step()) {
                const row = stmt.getAsObject();
                files.push(this._mapFileRow(row));
            }
            stmt.free();

            return files;
        } catch (error) {
            console.error('Database largest files error:', error);
            return [];
        }
    }

    /**
     * Get most recent files from database
     * @param {number} limit - Number of files to return
     * @returns {Promise<Array>} Array of recent files
     */
    async getRecentFiles(limit = 50) {
        try {
            const stmt = this.db.prepare('SELECT * FROM files ORDER BY modified_ts DESC LIMIT ?');
            stmt.bind([limit]);

            const files = [];
            while (stmt.step()) {
                const row = stmt.getAsObject();
                files.push(this._mapFileRow(row));
            }
            stmt.free();

            return files;
        } catch (error) {
            console.error('Database recent files error:', error);
            return [];
        }
    }

    /**
     * Map sort column name to database column
     * @param {string} column - UI column name
     * @returns {string} Database column name
     * @private
     */
    _mapSortColumn(column) {
        const mapping = {
            'name': 'name',
            'extension': 'extension',
            'size': 'size',
            'modified': 'modified_ts',
            'created': 'created_ts',
            'directory': 'directory'
        };
        return mapping[column] || 'name';
    }

    /**
     * Map database row to file object
     * @param {Object} row - Database row
     * @returns {Object} File object
     * @private
     */
    _mapFileRow(row) {
        return {
            name: row.name,
            extension: row.extension || '',
            size: row.size || 0,
            size_human: formatSize(row.size || 0),
            modified: row.modified || '',
            modified_ts: row.modified_ts || 0,
            created: row.created || '',
            created_ts: row.created_ts || 0,
            directory: row.directory || '',
            icon: this._getFileIcon(row.extension)
        };
    }

    /**
     * Get file icon for extension
     * @param {string} extension - File extension
     * @returns {string} Icon character
     * @private
     */
    _getFileIcon(extension) {
        const iconMap = {
            'mp4': '🎬', 'mov': '🎬', 'avi': '🎬', 'mkv': '🎬',
            'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️',
            'mp3': '🎵', 'wav': '🎵', 'flac': '🎵',
            'pdf': '📄', 'doc': '📄', 'docx': '📄', 'txt': '📄',
            'zip': '📦', 'rar': '📦', 'tar': '📦', 'gz': '📦'
        };
        return iconMap[extension] || '📄';
    }
}
