/**
 * Table Filter
 *
 * Handles filtering of table data based on search query and extension filter.
 */

class TableFilter {
    /**
     * Create a table filter
     * @param {Object} config - Configuration object
     * @param {string} config.searchBoxId - ID of search input element
     * @param {string} config.extensionFilterId - ID of extension select element
     * @param {Function} config.onFilter - Callback function when filter changes
     */
    constructor(config) {
        this.searchBox = document.getElementById(config.searchBoxId);
        this.extensionFilter = document.getElementById(config.extensionFilterId);
        this.onFilterCallback = config.onFilter;

        this.data = [];
        this.filteredData = [];

        // Set up event listeners
        if (this.searchBox) {
            this.searchBox.addEventListener('input', () => this.applyFilter());
        }

        if (this.extensionFilter) {
            this.extensionFilter.addEventListener('change', () => this.applyFilter());
        }
    }

    /**
     * Set the data to be filtered
     * @param {Array} data - Array of file objects
     */
    setData(data) {
        this.data = data;
        this.applyFilter();
    }

    /**
     * Apply current filter criteria to data
     */
    applyFilter() {
        const searchTerm = this.searchBox ? this.searchBox.value.toLowerCase() : '';
        const extensionFilter = this.extensionFilter ? this.extensionFilter.value : '';

        this.filteredData = this.data.filter(file => {
            const matchesSearch = searchTerm === '' ||
                file.name.toLowerCase().includes(searchTerm) ||
                file.path.toLowerCase().includes(searchTerm) ||
                file.directory.toLowerCase().includes(searchTerm);

            const matchesExtension = extensionFilter === '' || file.extension === extensionFilter;

            return matchesSearch && matchesExtension;
        });

        // Notify callback
        if (this.onFilterCallback) {
            this.onFilterCallback(this.filteredData);
        }
    }

    /**
     * Get filtered data
     * @returns {Array} Filtered file array
     */
    getFilteredData() {
        return this.filteredData;
    }

    /**
     * Clear all filters
     */
    clearFilters() {
        if (this.searchBox) this.searchBox.value = '';
        if (this.extensionFilter) this.extensionFilter.value = '';
        this.applyFilter();
    }
}
