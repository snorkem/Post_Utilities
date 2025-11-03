/**
 * Tooltip Component
 *
 * Manages tooltip display for file paths and other elements.
 */

class Tooltip {
    /**
     * Create a tooltip manager
     * @param {Object} config - Configuration object
     * @param {string} config.tooltipId - ID of tooltip element
     * @param {string} config.targetSelector - CSS selector for elements that trigger tooltip
     */
    constructor(config) {
        this.tooltip = document.getElementById(config.tooltipId);
        this.targetSelector = config.targetSelector || '.file-path';

        if (this.tooltip) {
            this.init();
        }
    }

    /**
     * Initialize tooltip event listeners
     */
    init() {
        document.addEventListener('mouseover', (e) => {
            const target = e.target.closest(this.targetSelector);
            if (target) {
                this.show(target.textContent, e);
            }
        });

        document.addEventListener('mousemove', (e) => {
            if (e.target.closest(this.targetSelector)) {
                this.updatePosition(e);
            }
        });

        document.addEventListener('mouseout', (e) => {
            if (!e.relatedTarget || !e.relatedTarget.closest(this.targetSelector)) {
                this.hide();
            }
        });
    }

    /**
     * Show tooltip with content
     * @param {string} content - Content to display
     * @param {MouseEvent} event - Mouse event for positioning
     */
    show(content, event) {
        if (!this.tooltip) return;

        this.tooltip.textContent = content;
        this.tooltip.classList.add('visible');
        this.updatePosition(event);
    }

    /**
     * Hide tooltip
     */
    hide() {
        if (this.tooltip) {
            this.tooltip.classList.remove('visible');
        }
    }

    /**
     * Update tooltip position based on mouse event
     * @param {MouseEvent} event - Mouse event
     */
    updatePosition(event) {
        if (!this.tooltip) return;

        const offset = 15;
        this.tooltip.style.left = (event.pageX + offset) + 'px';
        this.tooltip.style.top = (event.pageY + offset) + 'px';
    }
}
