/**
 * Table Sorter
 *
 * Handles sorting of table data by different columns.
 */

class TableSorter {
    /**
     * Create a table sorter
     * @param {Object} config - Configuration object
     * @param {string} config.tableId - ID of table element
     * @param {Function} config.onSort - Callback function when sort changes
     */
    constructor(config) {
        this.table = document.getElementById(config.tableId);
        this.onSortCallback = config.onSort;

        this.currentSort = {
            column: 'name',
            ascending: true
        };

        // Set up event listeners on headers
        if (this.table) {
            this.table.querySelectorAll('th[data-column]').forEach(header => {
                header.addEventListener('click', () => {
                    const column = header.dataset.column;
                    this.setSort(column);
                });
            });
        }
    }

    /**
     * Set sort column and direction
     * @param {string} column - Column name to sort by
     */
    setSort(column) {
        if (this.currentSort.column === column) {
            this.currentSort.ascending = !this.currentSort.ascending;
        } else {
            this.currentSort.column = column;
            this.currentSort.ascending = true;
        }

        this.updateSortHeaders();

        if (this.onSortCallback) {
            this.onSortCallback(this.currentSort);
        }
    }

    /**
     * Sort data array in place
     * @param {Array} data - Array of file objects to sort
     */
    sort(data) {
        const column = this.currentSort.column;
        const ascending = this.currentSort.ascending;

        data.sort((a, b) => {
            let valA = a[column];
            let valB = b[column];

            // Handle size column specially
            if (column === 'size') {
                valA = a.size_bytes;
                valB = b.size_bytes;
            }

            // Case-insensitive string comparison
            if (typeof valA === 'string') {
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
    updateSortHeaders() {
        if (!this.table) return;

        this.table.querySelectorAll('th[data-column]').forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
            if (header.dataset.column === this.currentSort.column) {
                header.classList.add(this.currentSort.ascending ? 'sort-asc' : 'sort-desc');
            }
        });
    }

    /**
     * Get current sort configuration
     * @returns {Object} Current sort settings {column, ascending}
     */
    getCurrentSort() {
        return { ...this.currentSort };
    }
}
