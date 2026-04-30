/**
 * Stress Meter Module — SVG gauge showing schedule health
 */

const Stress = (() => {
    function init() {
        refresh();
    }

    async function refresh() {
        try {
            const data = await Api.getStress();
            render(data);
        } catch (err) {
            // Silent fail
        }
    }

    function render(data) {
        const arc = document.getElementById('stress-arc');
        const valueText = document.getElementById('stress-value');
        const labelText = document.getElementById('stress-label');
        const stats = document.getElementById('stress-stats');

        if (!arc || !valueText) return;

        const score = data.score || 0;
        const level = data.level || 'green';

        // Arc calculation (semicircle, total length ~251)
        const totalLength = 251;
        const offset = totalLength - (totalLength * score / 100);

        // Color based on level
        const colors = {
            green: '#10B981',
            yellow: '#F59E0B',
            red: '#EF4444'
        };

        arc.style.transition = 'stroke-dashoffset 1s ease-out, stroke 0.5s ease';
        arc.setAttribute('stroke-dashoffset', offset);
        arc.setAttribute('stroke', colors[level] || '#10B981');

        valueText.textContent = `${score}%`;
        labelText.textContent = data.label || '';

        // Stats
        if (stats) {
            stats.innerHTML = `
                <span class="stress-stat"><span class="dot" style="background: ${colors.green}"></span> ${data.completed || 0} done</span>
                <span class="stress-stat"><span class="dot" style="background: ${colors.yellow}"></span> ${data.upcoming || 0} upcoming</span>
                <span class="stress-stat"><span class="dot" style="background: ${colors.red}"></span> ${data.missed || 0} missed</span>
            `;
        }
    }

    return { init, refresh };
})();
