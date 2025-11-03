/**
 * Sorting Utilities
 *
 * Functions for sorting file and folder data.
 */

/**
 * Compare two items with optional folders-first ordering
 * @param {Object} a - First item
 * @param {Object} b - Second item
 * @param {string} column - Column name to sort by
 * @param {boolean} ascending - Sort direction
 * @param {boolean} foldersFirst - If true, folders always come before files
 * @returns {number} Comparison result (-1, 0, or 1)
 */
function compareWithFoldersFirst(a, b, column, ascending, foldersFirst = true) {
    // If folders-first is enabled, folders always come before files
    if (foldersFirst) {
        const aIsFolder = a.type === 'folder' || a.hasOwnProperty('children') || a.hasOwnProperty('fileCount');
        const bIsFolder = b.type === 'folder' || b.hasOwnProperty('children') || b.hasOwnProperty('fileCount');

        if (aIsFolder && !bIsFolder) return -1;
        if (!aIsFolder && bIsFolder) return 1;
    }

    // Within same type, sort by specified column
    let valA = a[column];
    let valB = b[column];

    if (column === 'size_bytes' || column === 'size') {
        valA = a.size_bytes || a.totalSize || 0;
        valB = b.size_bytes || b.totalSize || 0;
    }

    if (typeof valA === 'string') {
        valA = valA.toLowerCase();
        valB = valB.toLowerCase();
    }

    if (valA < valB) return ascending ? -1 : 1;
    if (valA > valB) return ascending ? 1 : -1;
    return 0;
}

/**
 * Update sort indicator arrows in table headers
 * Updates the visual indicators to show which column is currently sorted
 * and in which direction.
 */
function updateSortHeaders() {
    document.querySelectorAll('th[data-column]').forEach(header => {
        header.classList.remove('sort-asc', 'sort-desc');
        if (header.dataset.column === currentSort.column) {
            header.classList.add(currentSort.ascending ? 'sort-asc' : 'sort-desc');
        }
    });
}
