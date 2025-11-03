/**
 * Tab Manager
 *
 * Manages tab switching between different views (Files, Browse, Statistics).
 */

class TabManager {
    /**
     * Create a tab manager
     * @param {Object} config - Configuration object
     * @param {Function} config.onTabChange - Callback when tab changes (optional)
     */
    constructor(config = {}) {
        this.onTabChangeCallback = config.onTabChange;
        this.currentTab = 'files';

        this.init();
    }

    /**
     * Initialize the tab manager
     */
    init() {
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;
                this.switchTab(tabName);
            });
        });
    }

    /**
     * Switch to a specific tab
     * @param {string} tabName - Name of tab to switch to
     */
    switchTab(tabName) {
        // Update active tab button
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        const activeTab = document.querySelector(`.tab[data-tab="${tabName}"]`);
        if (activeTab) activeTab.classList.add('active');

        // Update active content
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        const activeContent = document.getElementById(tabName + 'Tab');
        if (activeContent) activeContent.classList.add('active');

        this.currentTab = tabName;

        // Notify callback
        if (this.onTabChangeCallback) {
            this.onTabChangeCallback(tabName);
        }
    }

    /**
     * Get currently active tab
     * @returns {string} Current tab name
     */
    getCurrentTab() {
        return this.currentTab;
    }
}
