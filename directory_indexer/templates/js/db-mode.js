/**
 * db-mode.js
 * Entry point and initialization for database mode (SQLite via sql.js)
 *
 * This file orchestrates all components for database mode:
 * - Database loading and initialization
 * - Virtual table rendering with pagination
 * - Search and filtering via SQL queries
 * - Browse mode (future)
 * - Statistics display
 * - Column management
 * - Tab switching
 */

// ====================================================================
// Global State
// ====================================================================

let db = null;
let maxFileSize = 0;
let totalFilteredCount = 0;

let currentSort = { column: 'name', ascending: true };
let currentFilter = { search: '', extension: null };

const ROW_HEIGHT = 32;
const BUFFER_SIZE = 10;

let virtualScroll = {
    startIndex: 0,
    endIndex: 0,
    visibleRows: 0
};

// Component instances
let dataService = null;
let tabManager = null;
let browseController = null;

// ====================================================================
// Database Initialization
// ====================================================================

/**
 * Initialize sql.js and load database
 */
async function initDatabase() {
    try {
        // Update progress
        updateLoadingProgress(10, 'Loading sql.js library...');

        // Initialize SQL.js
        const SQL = await initSqlJs({
            locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/${file}`
        });

        updateLoadingProgress(30, 'Fetching database file...');

        // Fetch the database file
        const dbFilename = window.dbFilename || 'directory_index.db';
        const response = await fetch(dbFilename);
        if (!response.ok) {
            throw new Error('Failed to load database. Make sure to run this via HTTP server (python serve.py)');
        }
        const arrayBuffer = await response.arrayBuffer();
        const bytes = new Uint8Array(arrayBuffer);

        updateLoadingProgress(70, 'Initializing database...');

        // Create database
        db = new SQL.Database(bytes);

        updateLoadingProgress(90, 'Loading statistics...');

        // Calculate max file size for progress bars
        const maxSizeResult = db.exec('SELECT MAX(size_bytes) as max_size FROM files');
        if (maxSizeResult.length > 0 && maxSizeResult[0].values.length > 0) {
            maxFileSize = maxSizeResult[0].values[0][0] || 0;
        }

        updateLoadingProgress(100, 'Ready!');

        // Initialize data service
        dataService = new DatabaseLoader(db);

        // Initialize UI
        await initializeUI();

        // Hide loading overlay
        document.getElementById('loadingOverlay').classList.add('hidden');

    } catch (error) {
        console.error('Failed to load database:', error);
        document.getElementById('loadingStats').textContent = 'Error loading database: ' + error.message;
    }
}

/**
 * Update loading progress display
 * @param {number} percent - Progress percentage
 * @param {string} message - Status message
 */
function updateLoadingProgress(percent, message) {
    const fill = document.getElementById('loadingProgressFill');
    const stats = document.getElementById('loadingStats');
    if (fill) {
        fill.style.width = percent + '%';
        fill.textContent = percent + '%';
    }
    if (stats) {
        stats.textContent = message;
    }
}

// ====================================================================
// UI Initialization
// ====================================================================

/**
 * Initialize UI components and event listeners
 */
async function initializeUI() {
    console.log('Initializing UI...');

    // Initialize components
    initializeComponents();

    // Load statistics tab data
    loadStatistics();

    // Initial table render
    updateFilteredCount();
    renderTable();

    // Setup event listeners
    setupEventListeners();

    // Update sort headers
    updateSortHeaders();

    console.log('UI initialized successfully');
}

/**
 * Initialize all component instances
 */
function initializeComponents() {
    // Tab manager (DB mode doesn't have column settings, tooltips, or table sorter)
    tabManager = new TabManager();
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Search box
    const searchBox = document.getElementById('searchBox');
    if (searchBox) {
        searchBox.addEventListener('input', debounce(handleFilterChange, 300));
    }

    // Extension filter
    const extensionFilter = document.getElementById('extensionFilter');
    if (extensionFilter) {
        extensionFilter.addEventListener('change', handleFilterChange);
    }

    // Sort headers
    document.querySelectorAll('th[data-column]').forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.column;
            handleSort(column);
        });
    });

    // Virtual scroll
    const tableContainer = document.getElementById('tableContainer');
    if (tableContainer) {
        tableContainer.addEventListener('scroll', throttle(renderTable, 16));
    }

    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', async () => {
            const tabName = tab.dataset.tab;
            tabManager.switchTab(tabName);

            // Initialize Browse mode when tab is clicked
            if (tabName === 'browse' && !window.browseController) {
                await initBrowseMode();
            }
        });
    });
}

// ====================================================================
// Event Handlers
// ====================================================================

/**
 * Handle search/filter changes
 */
function handleFilterChange() {
    const searchBox = document.getElementById('searchBox');
    const extensionFilter = document.getElementById('extensionFilter');

    currentFilter.search = searchBox ? searchBox.value.toLowerCase() : '';
    currentFilter.extension = extensionFilter ? extensionFilter.value : null;

    updateFilteredCount();
    renderTable();
}

/**
 * Handle column sort
 * @param {string} column - Column name to sort by
 */
function handleSort(column) {
    if (currentSort.column === column) {
        currentSort.ascending = !currentSort.ascending;
    } else {
        currentSort.column = column;
        currentSort.ascending = true;
    }

    updateSortHeaders();
    renderTable();
}

/**
 * Update sort indicator arrows in table headers
 */
function updateSortHeaders() {
    document.querySelectorAll('th[data-column]').forEach(header => {
        header.classList.remove('sort-asc', 'sort-desc');
        if (header.dataset.column === currentSort.column) {
            header.classList.add(currentSort.ascending ? 'sort-asc' : 'sort-desc');
        }
    });
}

/**
 * Update filtered file count from database
 */
function updateFilteredCount() {
    let query = 'SELECT COUNT(*) as count FROM files WHERE 1=1';
    const params = [];

    if (currentFilter.search) {
        query += ' AND (LOWER(name) LIKE ? OR LOWER(directory) LIKE ?)';
        params.push('%' + currentFilter.search + '%', '%' + currentFilter.search + '%');
    }

    if (currentFilter.extension && currentFilter.extension !== 'all') {
        query += ' AND extension = ?';
        params.push(currentFilter.extension);
    }

    try {
        const stmt = db.prepare(query);
        stmt.bind(params);
        stmt.step();
        const result = stmt.getAsObject();
        totalFilteredCount = result.count || 0;
        stmt.free();

        const resultNumber = document.getElementById('resultNumber');
        if (resultNumber) {
            resultNumber.textContent = totalFilteredCount.toLocaleString();
        }
    } catch (error) {
        console.error('Error counting filtered files:', error);
        totalFilteredCount = 0;
    }
}

/**
 * Render table with virtual scrolling and database pagination
 */
function renderTable() {
    const tbody = document.getElementById('tableBody');
    const noResults = document.getElementById('noResults');
    const container = document.getElementById('tableContainer');
    const spacer = document.getElementById('tableSpacer');
    const viewport = document.getElementById('tableViewport');

    if (!tbody || !container) return;

    if (totalFilteredCount === 0) {
        tbody.style.display = 'none';
        if (noResults) noResults.style.display = 'block';
        return;
    }

    tbody.style.display = '';
    if (noResults) noResults.style.display = 'none';

    // Calculate virtual scroll parameters
    const scrollTop = container.scrollTop;
    const containerHeight = container.clientHeight;
    const totalHeight = totalFilteredCount * ROW_HEIGHT;

    if (spacer) spacer.style.height = totalHeight + 'px';

    virtualScroll.visibleRows = Math.ceil(containerHeight / ROW_HEIGHT);
    virtualScroll.startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - BUFFER_SIZE);
    virtualScroll.endIndex = Math.min(
        totalFilteredCount,
        virtualScroll.startIndex + virtualScroll.visibleRows + (BUFFER_SIZE * 2)
    );

    if (viewport) {
        viewport.style.transform = `translateY(${virtualScroll.startIndex * ROW_HEIGHT}px)`;
    }

    // Build query
    let query = 'SELECT name, extension, directory, size_bytes, size_human, modified, created, icon FROM files WHERE 1=1';
    const params = [];

    if (currentFilter.search) {
        query += ' AND (LOWER(name) LIKE ? OR LOWER(directory) LIKE ?)';
        params.push('%' + currentFilter.search + '%', '%' + currentFilter.search + '%');
    }

    if (currentFilter.extension && currentFilter.extension !== 'all') {
        query += ' AND extension = ?';
        params.push(currentFilter.extension);
    }

    // Add sorting
    query += ` ORDER BY ${currentSort.column} ${currentSort.ascending ? 'ASC' : 'DESC'}`;

    // Add pagination
    query += ` LIMIT ? OFFSET ?`;
    params.push(virtualScroll.endIndex - virtualScroll.startIndex, virtualScroll.startIndex);

    // Execute query
    try {
        const stmt = db.prepare(query);
        stmt.bind(params);

        const rows = [];
        while (stmt.step()) {
            rows.push(stmt.get());
        }
        stmt.free();

        if (rows.length === 0) {
            tbody.innerHTML = '';
            return;
        }

        // Render rows
        tbody.innerHTML = rows.map(row => {
            const [name, extension, directory, size_bytes, size_human, modified, created, icon] = row;
            const sizePercent = maxFileSize > 0 ? (size_bytes / maxFileSize * 100).toFixed(1) : 0;
            return `
            <tr>
                <td>
                    <div class="file-name">
                        <span class="file-icon">${escapeHtml(icon)}</span>
                        <span>${escapeHtml(name)}</span>
                    </div>
                </td>
                <td><span class="file-extension">${escapeHtml(extension)}</span></td>
                <td class="path-cell" title="${escapeHtml(directory)}">${escapeHtml(directory)}</td>
                <td>
                    <div class="size-container">
                        <div class="size-bar" style="width: ${sizePercent}%"></div>
                        <span class="size-text">${escapeHtml(size_human)}</span>
                    </div>
                </td>
                <td class="modified">${escapeHtml(modified)}</td>
            </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Error rendering table:', error);
        tbody.innerHTML = '<tr><td colspan="5">Error loading data</td></tr>';
    }
}

// ====================================================================
// Statistics
// ====================================================================

/**
 * Load statistics tab data from database
 */
function loadStatistics() {
    try {
        // This would populate the statistics tab
        // The actual statistics HTML is pre-generated server-side
        console.log('Statistics loaded');
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// ====================================================================
// Browse Mode
// ====================================================================

/**
 * Build directory tree structure from database
 * @returns {Promise<Object>} Root directory tree node
 */
async function buildTreeFromDatabase() {
    try {
        // Get root path from metadata to extract actual directory name
        let rootName = 'Root';
        try {
            const metaStmt = db.prepare('SELECT value FROM metadata WHERE key = ?');
            metaStmt.bind(['root_path']);
            if (metaStmt.step()) {
                const rootPath = metaStmt.get()[0];
                // Extract directory name from path
                if (rootPath) {
                    const parts = rootPath.replace(/\\/g, '/').split('/');
                    rootName = parts[parts.length - 1] || parts[parts.length - 2] || 'Root';
                }
            }
            metaStmt.free();
        } catch (error) {
            console.warn('Could not retrieve root path from metadata:', error);
        }

        // Get all unique directories
        const dirsQuery = 'SELECT DISTINCT directory FROM files ORDER BY directory';
        const dirsStmt = db.prepare(dirsQuery);

        const allDirs = new Set(['']); // Include root
        while (dirsStmt.step()) {
            const dir = dirsStmt.get()[0];
            if (dir) {
                allDirs.add(dir);
                // Add all parent directories
                const parts = dir.split('/');
                let currentPath = '';
                for (const part of parts) {
                    if (part) {
                        currentPath = currentPath ? `${currentPath}/${part}` : part;
                        allDirs.add(currentPath);
                    }
                }
            }
        }
        dirsStmt.free();

        // Build tree structure
        const tree = {
            name: rootName,
            path: '',
            file_count: 0,
            total_size: 0,
            children: {},
            files: []
        };

        // Create nodes for all directories
        const nodeMap = { '': tree };

        for (const dirPath of Array.from(allDirs).sort()) {
            if (dirPath === '') continue; // Skip root, already created

            const parts = dirPath.split('/');
            const name = parts[parts.length - 1];
            const parentPath = parts.slice(0, -1).join('/');

            const node = {
                name: name,
                path: dirPath,
                file_count: 0,
                total_size: 0,
                children: {},
                files: []
            };

            nodeMap[dirPath] = node;

            // Add to parent's children
            const parent = nodeMap[parentPath];
            if (parent) {
                parent.children[name] = node;
            }
        }

        // Query file counts and sizes for each directory
        for (const dirPath of allDirs) {
            const statsQuery = dirPath === ''
                ? 'SELECT COUNT(*) as count, COALESCE(SUM(size_bytes), 0) as total_size FROM files WHERE directory = ? OR directory LIKE ?'
                : 'SELECT COUNT(*) as count, COALESCE(SUM(size_bytes), 0) as total_size FROM files WHERE directory = ? OR directory LIKE ?';

            const statsStmt = db.prepare(statsQuery);
            const params = dirPath === '' ? ['', '%'] : [dirPath, `${dirPath}/%`];
            statsStmt.bind(params);
            statsStmt.step();

            const stats = statsStmt.get();
            const node = nodeMap[dirPath];
            if (node) {
                node.file_count = stats[0] || 0;
                node.total_size = stats[1] || 0;
            }
            statsStmt.free();

            // Get direct files in this directory
            const filesQuery = dirPath === ''
                ? 'SELECT name, extension, size_bytes, modified, created, icon FROM files WHERE directory = "" OR directory IS NULL'
                : 'SELECT name, extension, size_bytes, modified, created, icon FROM files WHERE directory = ?';

            const filesStmt = db.prepare(filesQuery);
            if (dirPath !== '') {
                filesStmt.bind([dirPath]);
            }

            const files = [];
            while (filesStmt.step()) {
                const row = filesStmt.get();
                files.push({
                    name: row[0],
                    extension: row[1],
                    size: row[2],
                    modified: row[3],
                    created: row[4],
                    icon: row[5]
                });
            }
            filesStmt.free();

            if (node) {
                node.files = files;
            }
        }

        return tree;
    } catch (error) {
        console.error('Error building tree from database:', error);
        return {
            name: 'Root',
            path: '',
            file_count: 0,
            total_size: 0,
            children: {},
            files: []
        };
    }
}

/**
 * Initialize browse mode
 */
async function initBrowseMode() {
    if (window.browseController) return; // Already initialized

    try {
        console.log('Initializing Browse mode for database...');

        // Build directory tree from database
        const directoryTree = await buildTreeFromDatabase();

        // Create DataService with the tree structure for browse compatibility
        const browseDataService = new DataService('inline', directoryTree);

        const browseState = BrowseState.restore();

        browseController = new BrowseController(browseDataService, browseState);

        window.browseController = browseController;
        await browseController.init();

        console.log('Browse mode initialized successfully');
    } catch (error) {
        console.error('Failed to initialize Browse mode:', error);
        alert('Failed to initialize Browse mode: ' + error.message);
    }
}

// ====================================================================
// Application Start
// ====================================================================

// Start loading database when page loads
initDatabase();
