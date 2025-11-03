/**
 * Virtual Table Renderer
 *
 * Implements virtual scrolling for large file lists to maintain performance.
 * Only renders visible rows plus a buffer, dramatically improving performance
 * for large datasets.
 */

class VirtualTableRenderer {
    /**
     * Create a virtual table renderer
     * @param {Object} config - Configuration object
     * @param {string} config.containerId - ID of scroll container element
     * @param {string} config.spacerId - ID of spacer element
     * @param {string} config.viewportId - ID of viewport element
     * @param {string} config.tbodyId - ID of table body element
     * @param {string} config.noResultsId - ID of no results message element
     * @param {string} config.resultNumberId - ID of result count element
     * @param {number} config.rowHeight - Height of each row in pixels
     * @param {number} config.bufferSize - Number of extra rows to render above/below viewport
     */
    constructor(config) {
        this.container = document.getElementById(config.containerId);
        this.spacer = document.getElementById(config.spacerId);
        this.viewport = document.getElementById(config.viewportId);
        this.tbody = document.getElementById(config.tbodyId);
        this.noResults = document.getElementById(config.noResultsId);
        this.resultNumber = document.getElementById(config.resultNumberId);

        this.rowHeight = config.rowHeight || 45;
        this.bufferSize = config.bufferSize || 10;

        this.data = [];
        this.maxFileSize = 0;

        this.virtualScroll = {
            startIndex: 0,
            endIndex: 0,
            visibleRows: 0
        };

        // Bind scroll handler
        if (this.container) {
            this.container.addEventListener('scroll', throttle(() => this.render(), 16));
        }
    }

    /**
     * Set the data to be rendered
     * @param {Array} data - Array of file objects
     * @param {number} maxFileSize - Maximum file size for size bar calculation
     */
    setData(data, maxFileSize) {
        this.data = data;
        this.maxFileSize = maxFileSize;
    }

    /**
     * Render the table based on current scroll position
     */
    render() {
        if (!this.container || !this.tbody) {
            console.error('Table elements not found');
            return;
        }

        // Handle empty data
        if (this.data.length === 0) {
            this.tbody.style.display = 'none';
            if (this.noResults) this.noResults.style.display = 'block';
            return;
        }

        this.tbody.style.display = '';
        if (this.noResults) this.noResults.style.display = 'none';

        // Update result count
        if (this.resultNumber) {
            this.resultNumber.textContent = this.data.length.toLocaleString();
        }

        // Calculate virtual scroll parameters
        const scrollTop = this.container.scrollTop;
        const containerHeight = this.container.clientHeight;
        const totalHeight = this.data.length * this.rowHeight;

        // Set spacer height to create scrollable area
        if (this.spacer) {
            this.spacer.style.height = totalHeight + 'px';
        }

        // Calculate visible row indices
        this.virtualScroll.visibleRows = Math.ceil(containerHeight / this.rowHeight);
        this.virtualScroll.startIndex = Math.max(
            0,
            Math.floor(scrollTop / this.rowHeight) - this.bufferSize
        );
        this.virtualScroll.endIndex = Math.min(
            this.data.length,
            this.virtualScroll.startIndex + this.virtualScroll.visibleRows + (this.bufferSize * 2)
        );

        // Transform viewport to correct position
        if (this.viewport) {
            this.viewport.style.transform = `translateY(${this.virtualScroll.startIndex * this.rowHeight}px)`;
        }

        // Render only visible rows
        this.renderRows();
    }

    /**
     * Render the visible rows
     */
    renderRows() {
        const visibleData = this.data.slice(
            this.virtualScroll.startIndex,
            this.virtualScroll.endIndex
        );

        this.tbody.innerHTML = visibleData.map(file => {
            const sizePercent = this.maxFileSize > 0
                ? (file.size_bytes / this.maxFileSize * 100).toFixed(1)
                : 0;

            return `
                <tr>
                    <td>
                        <div class="file-name">
                            <span class="file-icon">${file.icon}</span>
                            <span>${escapeHtml(file.name)}</span>
                        </div>
                    </td>
                    <td><span class="file-extension">${escapeHtml(file.extension)}</span></td>
                    <td class="file-path">${escapeHtml(file.directory)}</td>
                    <td>
                        <div class="size-cell">
                            <div class="size-bar-container">
                                <div class="size-bar" style="width: ${sizePercent}%"></div>
                            </div>
                            <span class="size-text">${file.size_human}</span>
                        </div>
                    </td>
                    <td class="modified">${file.modified}</td>
                    <td class="modified">${file.created}</td>
                </tr>
            `;
        }).join('');
    }

    /**
     * Scroll to top of table
     */
    scrollToTop() {
        if (this.container) {
            this.container.scrollTop = 0;
        }
    }
}
