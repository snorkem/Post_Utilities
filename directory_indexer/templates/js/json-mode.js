/**
 * json-mode.js
 * Entry point and initialization for JSON mode (inline data)
 *
 * This file orchestrates all components for JSON mode:
 * - Virtual table rendering
 * - Search and filtering
 * - Browse mode
 * - Statistics display
 * - Column management
 * - Tab switching
 */

// ====================================================================
// Global State
// ====================================================================

let tableData = [];
let filteredData = [];
let maxFileSize = 0;

let currentSort = { column: 'name', ascending: true };
let currentFilter = { search: '', extension: 'all' };

let virtualScroll = {
    startIndex: 0,
    endIndex: 0,
    visibleRows: 0
};

// Component instances
let virtualTableRenderer = null;
let columnManager = null;
let tabManager = null;
let tooltip = null;
let browseController = null;
let dataService = null;

// ====================================================================
// Initialization
// ====================================================================

/**
 * Initialize the application
 */
async function initializeApp() {
    try {
        console.log('Initializing JSON mode application...');

        // Initialize data service with embedded data
        const directoryTree = window.directoryTree;
        const fileData = window.fileData;

        dataService = new JsonDataLoader(directoryTree, fileData);

        // Set global data
        tableData = fileData;
        filteredData = [...tableData];
        maxFileSize = Math.max(...tableData.map(f => f.size_bytes || 0), 0);

        // Initialize components
        initializeComponents();

        // Setup event listeners
        setupEventListeners();

        // Initial render
        renderTable();

        // Hide loading overlay
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            loadingOverlay.classList.add('hidden');
        }

        console.log('Application initialized successfully');
    } catch (error) {
        console.error('Error initializing application:', error);
        const loadingOverlay = document.getElementById('loadingOverlay');
        if (loadingOverlay) {
            const stats = document.getElementById('loadingStats');
            if (stats) {
                stats.textContent = 'Error loading data: ' + error.message;
            }
        }
    }
}

/**
 * Initialize all component instances
 */
function initializeComponents() {
    // Virtual table renderer
    virtualTableRenderer = new VirtualTableRenderer({
        containerId: 'tableContainer',
        spacerId: 'tableSpacer',
        viewportId: 'tableViewport',
        tbodyId: 'tableBody',
        noResultsId: 'noResults',
        resultNumberId: 'resultNumber',
        rowHeight: 45,
        bufferSize: 10
    });
    virtualTableRenderer.setData(filteredData);

    // Column manager
    columnManager = new ColumnManager({
        settingsToggleId: 'settingsToggle',
        settingsPanelId: 'settingsPanel'
    });

    // Tab manager
    tabManager = new TabManager();

    // Tooltip
    tooltip = new Tooltip({
        tooltipId: 'pathTooltip',
        targetSelector: '.file-path'
    });
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
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            tabManager.switchTab(tabName);

            // Hide loading overlay when not on Files tab
            const loadingOverlay = document.getElementById('loadingOverlay');
            if (tabName !== 'files' && loadingOverlay) {
                loadingOverlay.classList.add('hidden');
            }

            // Initialize browse mode if switching to it
            if (tabName === 'browse' && !document.getElementById('folderTree').hasChildNodes()) {
                initializeBrowseMode();
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

    const searchTerm = searchBox ? searchBox.value.toLowerCase() : '';
    const extensionValue = extensionFilter ? extensionFilter.value : '';

    currentFilter.search = searchTerm;
    currentFilter.extension = extensionValue;

    // Apply filters manually
    filteredData = tableData.filter(file => {
        const matchesSearch = searchTerm === '' ||
            file.name.toLowerCase().includes(searchTerm) ||
            (file.path && file.path.toLowerCase().includes(searchTerm)) ||
            (file.directory && file.directory.toLowerCase().includes(searchTerm));

        const matchesExtension = extensionValue === '' || file.extension === extensionValue;

        return matchesSearch && matchesExtension;
    });

    // Update filtered count
    updateFilteredCount();

    // Re-sort filtered data
    sortData(filteredData);

    // Update renderer and render
    virtualTableRenderer.setData(filteredData);
    virtualTableRenderer.scrollToTop();
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

    // Sort filtered data
    sortData(filteredData);

    // Update sort indicators in headers
    updateSortHeaders();

    // Update UI
    virtualTableRenderer.setData(filteredData);
    renderTable();
}

/**
 * Sort data array in place
 * @param {Array} data - Array to sort
 */
function sortData(data) {
    const column = currentSort.column;
    const ascending = currentSort.ascending;

    data.sort((a, b) => {
        let valA = a[column];
        let valB = b[column];

        // Handle size column specially
        if (column === 'size') {
            valA = a.size_bytes || 0;
            valB = b.size_bytes || 0;
        }

        // Case-insensitive string comparison
        if (typeof valA === 'string' && typeof valB === 'string') {
            valA = valA.toLowerCase();
            valB = valB.toLowerCase();
        }

        if (valA < valB) return ascending ? -1 : 1;
        if (valA > valB) return ascending ? 1 : -1;
        return 0;
    });
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
 * Update filtered file count display
 */
function updateFilteredCount() {
    const fileCount = document.getElementById('fileCount');
    if (fileCount) {
        const filtered = filteredData.length;
        const total = tableData.length;
        if (filtered === total) {
            fileCount.textContent = `${total.toLocaleString()} files`;
        } else {
            fileCount.textContent = `${filtered.toLocaleString()} of ${total.toLocaleString()} files`;
        }
    }
}

/**
 * Render the virtual table
 */
function renderTable() {
    virtualTableRenderer.render();
}

/**
 * Initialize browse mode
 */
async function initializeBrowseMode() {
    if (browseController) return; // Already initialized

    try {
        console.log('Initializing browse mode...');

        const browseState = BrowseState.restore();

        browseController = new BrowseController(dataService, browseState);
        await browseController.init();

        console.log('Browse mode initialized');
    } catch (error) {
        console.error('Error initializing browse mode:', error);
    }
}

// ====================================================================
// Data Loading
// ====================================================================

/**
 * Load data in chunks (for large datasets)
 * This function handles progressive loading with progress indicators
 */
async function loadDataInChunks() {
    const CHUNK_SIZE = 1000;
    let chunksLoaded = 0;
    const totalChunks = Math.ceil(tableData.length / CHUNK_SIZE);

    function loadNextChunk() {
        if (chunksLoaded >= totalChunks) {
            // All chunks loaded
            document.getElementById('loadingOverlay').classList.add('hidden');
            return;
        }

        const start = chunksLoaded * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, tableData.length);
        const chunk = tableData.slice(start, end);

        chunksLoaded++;

        // Update progress
        const progress = Math.round((chunksLoaded / totalChunks) * 100);
        const progressFill = document.getElementById('loadingProgressFill');
        const loadingStats = document.getElementById('loadingStats');

        if (progressFill && loadingStats) {
            progressFill.style.width = progress + '%';
            progressFill.textContent = progress + '%';
            loadingStats.textContent = `Loaded ${filteredData.length.toLocaleString()} of ${tableData.length.toLocaleString()} files...`;
        }

        // Update maxFileSize incrementally
        if (chunk.length > 0) {
            const chunkMax = Math.max(...chunk.map(f => f.size_bytes || 0));
            maxFileSize = Math.max(maxFileSize, chunkMax);
        }

        // Initialize UI on first chunk
        if (chunksLoaded === 1) {
            try {
                updateSortHeaders();
                columnManager.init();
                tooltip.init();
            } catch (initError) {
                console.error('Error during initialization:', initError);
            }
        }

        // Update table
        try {
            renderTable();
        } catch (renderError) {
            console.error('Error rendering table:', renderError);
        }

        // Load next chunk with small delay to keep UI responsive
        setTimeout(loadNextChunk, 50);
    }

    loadNextChunk();
}

// ====================================================================
// Application Start
// ====================================================================

// Start the application when data is available
if (window.fileData && window.directoryTree) {
    // Data is already embedded, initialize immediately
    initializeApp();
} else {
    // Wait for data to load
    console.log('Waiting for data to load...');
    let attempts = 0;
    const checkInterval = setInterval(() => {
        attempts++;
        if (window.fileData && window.directoryTree) {
            clearInterval(checkInterval);
            initializeApp();
        } else if (attempts > 50) {
            clearInterval(checkInterval);
            console.error('Data failed to load');
            const stats = document.getElementById('loadingStats');
            if (stats) {
                stats.textContent = 'Error: Data failed to load';
            }
        }
    }, 100);
}
