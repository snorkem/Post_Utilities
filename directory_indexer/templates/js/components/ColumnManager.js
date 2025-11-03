/**
 * Column Manager
 *
 * Manages column widths for the file table, including presets and persistence.
 */

class ColumnManager {
    /**
     * Create a column manager
     * @param {Object} config - Configuration object
     * @param {string} config.settingsToggleId - ID of settings toggle button
     * @param {string} config.settingsPanelId - ID of settings panel
     */
    constructor(config) {
        this.settingsToggle = document.getElementById(config.settingsToggleId);
        this.settingsPanel = document.getElementById(config.settingsPanelId);

        this.defaultWidths = {
            name: 20,
            type: 8,
            path: 45,
            size: 15,
            modified: 12
        };

        this.presets = {
            compact: { name: 18, type: 8, path: 40, size: 20, modified: 14 },
            default: { name: 20, type: 8, path: 45, size: 15, modified: 12 },
            'wide-path': { name: 15, type: 8, path: 55, size: 12, modified: 10 }
        };

        this.currentWidths = this.loadColumnWidths();

        this.init();
    }

    /**
     * Initialize the column manager
     */
    init() {
        // Apply saved widths
        this.applyColumnWidths(this.currentWidths);

        // Set up settings panel toggle
        if (this.settingsToggle) {
            this.settingsToggle.addEventListener('click', () => {
                if (this.settingsPanel) {
                    this.settingsPanel.classList.toggle('visible');
                }
            });
        }

        // Set up width slider event listeners
        const sliders = [
            { id: 'nameWidth', key: 'name', valueId: 'nameValue' },
            { id: 'typeWidth', key: 'type', valueId: 'typeValue' },
            { id: 'pathWidth', key: 'path', valueId: 'pathValue' },
            { id: 'sizeWidth', key: 'size', valueId: 'sizeValue' },
            { id: 'modifiedWidth', key: 'modified', valueId: 'modifiedValue' }
        ];

        sliders.forEach(slider => {
            const element = document.getElementById(slider.id);
            const valueDisplay = document.getElementById(slider.valueId);

            if (element && valueDisplay) {
                element.addEventListener('input', (e) => {
                    const value = parseInt(e.target.value);
                    valueDisplay.textContent = value + '%';
                    this.currentWidths[slider.key] = value;
                    this.applyColumnWidths(this.currentWidths);
                    this.saveColumnWidths(this.currentWidths);
                });
            }
        });

        // Set up preset buttons
        document.querySelectorAll('.preset-btn[data-preset]').forEach(btn => {
            btn.addEventListener('click', () => {
                const presetName = btn.dataset.preset;
                this.applyPreset(presetName);
            });
        });

        // Set up reset button
        const resetButton = document.getElementById('resetWidths');
        if (resetButton) {
            resetButton.addEventListener('click', () => {
                this.reset();
            });
        }

        // Set up column resize handles
        this.initColumnResize();
    }

    /**
     * Load column widths from localStorage
     * @returns {Object} Column width configuration
     */
    loadColumnWidths() {
        const saved = localStorage.getItem('columnWidths');
        return saved ? JSON.parse(saved) : { ...this.defaultWidths };
    }

    /**
     * Save column widths to localStorage
     * @param {Object} widths - Column width configuration
     */
    saveColumnWidths(widths) {
        localStorage.setItem('columnWidths', JSON.stringify(widths));
    }

    /**
     * Apply column widths to the table
     * @param {Object} widths - Column width configuration
     */
    applyColumnWidths(widths) {
        const root = document.documentElement;
        root.style.setProperty('--col-name-width', widths.name + '%');
        root.style.setProperty('--col-type-width', widths.type + '%');
        root.style.setProperty('--col-path-width', widths.path + '%');
        root.style.setProperty('--col-size-width', widths.size + '%');
        root.style.setProperty('--col-modified-width', widths.modified + '%');

        // Update slider values
        const sliderMappings = {
            nameWidth: 'name',
            typeWidth: 'type',
            pathWidth: 'path',
            sizeWidth: 'size',
            modifiedWidth: 'modified'
        };

        Object.entries(sliderMappings).forEach(([sliderId, key]) => {
            const slider = document.getElementById(sliderId);
            const valueDisplay = document.getElementById(sliderId.replace('Width', 'Value'));

            if (slider) slider.value = widths[key];
            if (valueDisplay) valueDisplay.textContent = widths[key] + '%';
        });
    }

    /**
     * Apply a preset configuration
     * @param {string} presetName - Name of preset to apply
     */
    applyPreset(presetName) {
        if (this.presets[presetName]) {
            this.currentWidths = { ...this.presets[presetName] };
            this.applyColumnWidths(this.currentWidths);
            this.saveColumnWidths(this.currentWidths);
        }
    }

    /**
     * Reset to default widths
     */
    reset() {
        this.currentWidths = { ...this.defaultWidths };
        this.applyColumnWidths(this.currentWidths);
        this.saveColumnWidths(this.currentWidths);
    }

    /**
     * Initialize column resize handles
     */
    initColumnResize() {
        const table = document.getElementById('fileTable');
        if (!table) return;

        const headers = table.querySelectorAll('th');
        const columnKeys = ['name', 'type', 'path', 'size', 'modified'];

        headers.forEach((header, index) => {
            // Skip the last header (no resize needed)
            if (index === headers.length - 1) return;

            const resizeHandle = document.createElement('div');
            resizeHandle.className = 'resize-handle';
            header.appendChild(resizeHandle);

            let startX, startWidth, columnKey;

            resizeHandle.addEventListener('mousedown', (e) => {
                e.preventDefault();
                e.stopPropagation();

                columnKey = columnKeys[index];
                startX = e.pageX;
                startWidth = this.currentWidths[columnKey];

                resizeHandle.classList.add('resizing');
                document.body.style.cursor = 'col-resize';
                document.body.style.userSelect = 'none';

                document.addEventListener('mousemove', handleMouseMove);
                document.addEventListener('mouseup', handleMouseUp);
            });

            const handleMouseMove = (e) => {
                const diff = e.pageX - startX;
                const tableWidth = table.offsetWidth;
                const percentChange = (diff / tableWidth) * 100;
                const newWidth = Math.max(5, Math.min(70, startWidth + percentChange));

                this.currentWidths[columnKey] = Math.round(newWidth);
                this.applyColumnWidths(this.currentWidths);
            };

            const handleMouseUp = () => {
                resizeHandle.classList.remove('resizing');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';

                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);

                this.saveColumnWidths(this.currentWidths);
            };
        });
    }
}
