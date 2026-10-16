/* Offline graph exploration. Activity nodes keep their global source identity. */
(() => {
    'use strict';
    const root = document.querySelector('#goal-explorer');
    const data = JSON.parse(document.querySelector('#goal-explorer-data').textContent);
    const nodes = new Map(data.nodes.map(node => [node.id, node]));
    const children = new Map(data.nodes.map(node => [node.id, []]));
    for (const [from, to] of data.edges) children.get(from).push(to);
    const parents = new Map(data.nodes.map(node => [node.id, []]));
    for (const [from, to] of data.edges) parents.get(to).push(from);
    const objectives = data.nodes.filter(node => node.kind === 'objective');
    const filters = [...root.querySelectorAll('[data-status-filter]')];
    const expanded = new Set();
    const stage = root.querySelector('.explorer-stage');
    const viewport = root.querySelector('.explorer-viewport');
    const canvas = root.querySelector('.explorer-canvas');
    const status = root.querySelector('.explorer-status');
    const elements = new Map();
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('aria-hidden', 'true');
    stage.append(svg);
    const empty = document.createElement('p');
    empty.className = 'explorer-empty';
    empty.hidden = true;
    stage.append(empty);
    const levels = ['Objectives', 'Key Results', 'Beiträge'].map(text => {
        const label = document.createElement('p');
        label.className = 'explorer-level';
        label.textContent = text;
        stage.append(label);
        return label;
    });
    const states = {'active': 'Active', 'on hold': 'On hold', 'closed': 'Closed'};
    let visibleEdges = [];
    let geometry = null, scale = 1, fitMode = false;
    const minScale = .1, maxScale = 2;

    function zoom(next, fit = false) {
        fitMode = fit;
        if (!geometry || !viewport.clientWidth) return;
        const centerX = (viewport.scrollLeft + viewport.clientWidth / 2) / scale;
        const centerY = (viewport.scrollTop + viewport.clientHeight / 2) / scale;
        if (fitMode) {
            const height = parseFloat(getComputedStyle(viewport).maxHeight);
            next = Math.min(1, (viewport.clientWidth - 2) / geometry.width,
                (height - 2) / geometry.height);
        }
        scale = Math.max(minScale, Math.min(maxScale, next));
        stage.style.transform = `scale(${scale})`;
        canvas.style.width = Math.ceil(geometry.width * scale) + 'px';
        canvas.style.height = Math.ceil(geometry.height * scale) + 'px';
        root.querySelector('[data-action=zoom-reset]').textContent = Math.round(scale * 100) + '%';
        root.querySelector('[data-action=zoom-reset]').setAttribute('aria-label',
            `Zoom ${Math.round(scale * 100)} %. Auf 100 % zurücksetzen / Reset to 100 percent`);
        root.querySelector('[data-action=zoom-out]').disabled = scale <= minScale;
        root.querySelector('[data-action=zoom-in]').disabled = scale >= maxScale;
        root.querySelector('[data-action=zoom-fit]').setAttribute('aria-pressed', String(fitMode));
        viewport.scrollTo(fitMode ? 0 : centerX * scale - viewport.clientWidth / 2,
            fitMode ? 0 : centerY * scale - viewport.clientHeight / 2);
    }

    function highlight(id) {
        const related = new Set(id ? [id] : []);
        for (const edge of visibleEdges) {
            const active = edge.from === id || edge.to === id;
            edge.path.classList.toggle('is-highlighted', active);
            if (active) { related.add(edge.from); related.add(edge.to); }
        }
        stage.classList.toggle('has-highlight', visibleEdges.some(edge => edge.from === id || edge.to === id));
        for (const [key, element] of elements) element.classList.toggle('is-highlighted', related.has(key));
    }

    function toggle(id) {
        if (!children.get(id).length) return;
        if (expanded.has(id)) expanded.delete(id); else expanded.add(id);
        render();
    }

    for (const node of data.nodes) {
        const element = document.createElement('article');
        element.className = 'explorer-node';
        element.id = 'explorer-node-' + elements.size;
        element.dataset.node = node.id;
        element.dataset.kind = node.kind;
        element.dataset.status = node.status || '';
        const kicker = document.createElement('span');
        kicker.className = 'explorer-kicker';
        kicker.textContent = node.kind === 'objective' ? node.label + ' · ' + (states[node.status] || '') : node.label || 'Beitrag';
        const title = document.createElement('h3');
        title.textContent = node.title;
        title.id = element.id + '-title';
        element.setAttribute('aria-labelledby', title.id);
        const footer = document.createElement('div');
        footer.className = 'explorer-node-footer';
        element.append(kicker, title, footer);
        if (node.url) {
            const link = document.createElement('a');
            link.href = node.url;
            link.textContent = 'Details ↗';
            link.setAttribute('aria-label', 'Details: ' + node.title);
            footer.append(link);
        }
        if (children.get(node.id).length) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'explorer-toggle';
            button.addEventListener('click', () => toggle(node.id));
            footer.append(button);
            element.addEventListener('dblclick', event => {
                if (!event.target.closest('button,a')) { event.preventDefault(); toggle(node.id); }
            });
        } else if (node.kind !== 'activity') {
            const empty = document.createElement('span');
            empty.textContent = node.kind === 'objective' ? '0 KR' : 'Keine Beiträge zugeordnet';
            if (node.kind === 'objective') empty.setAttribute('aria-label', 'Keine Key Results');
            footer.append(empty);
        }
        if (node.kind === 'kr') {
            element.title = node.measure;
            const description = document.createElement('span');
            description.className = 'explorer-description';
            description.id = element.id + '-description';
            description.textContent = 'Objective: ' + parents.get(node.id).map(id => nodes.get(id).title).join('; ') + '. ' + node.measure;
            element.setAttribute('aria-describedby', description.id);
            element.append(description);
        }
        element.addEventListener('pointerenter', () => highlight(node.id));
        element.addEventListener('pointerleave', () => highlight(null));
        element.addEventListener('focusin', () => highlight(node.id));
        element.addEventListener('focusout', event => {
            if (!element.contains(event.relatedTarget)) highlight(null);
        });
        element.hidden = true;
        stage.append(element);
        elements.set(node.id, element);
    }

    function projection() {
        // Form controls own the filter, including values restored by the browser.
        const selectedStatuses = new Set(filters.filter(filter => filter.checked && !filter.disabled)
            .map(filter => filter.value));
        const selected = objectives.filter(o => selectedStatuses.has(o.status));
        const krIds = selected.flatMap(o => expanded.has(o.id) ? children.get(o.id) : []);
        const activityIds = [...new Set(krIds.flatMap(id => expanded.has(id) ? children.get(id) : []))];
        const rows = [selected.map(o => o.id), krIds, activityIds];
        const visible = new Set(rows.flat());
        const edges = data.edges.filter(([from, to]) => visible.has(from) && visible.has(to) && expanded.has(from));
        const incoming = new Map([...visible].map(id => [id, []]));
        for (const [from, to] of edges) incoming.get(to).push(from);
        return {rows, visible, edges, incoming};
    }

    function syncNodes(view) {
        for (const [id, element] of elements) {
            element.hidden = !view.visible.has(id);
            const button = element.querySelector('button');
            if (button) {
                const count = children.get(id).length;
                const unit = nodes.get(id).kind === 'objective' ? (count === 1 ? 'Key Result' : 'Key Results') : (count === 1 ? 'Beitrag' : 'Beiträge');
                const shortUnit = nodes.get(id).kind === 'objective' ? 'KR' : unit;
                button.textContent = (expanded.has(id) ? '− ' : '+ ') + count + ' ' + shortUnit;
                button.setAttribute('aria-expanded', String(expanded.has(id)));
                button.setAttribute('aria-controls', children.get(id).map(key => elements.get(key).id).join(' '));
                button.setAttribute('aria-label', nodes.get(id).title + ': ' + count + ' ' + unit + (expanded.has(id) ? ' einklappen' : ' aufklappen'));
            }
            if (nodes.get(id).kind === 'activity' && view.visible.has(id)) {
                const contributors = view.incoming.get(id).map(key => nodes.get(key).title);
                element.querySelector('.explorer-kicker').textContent = 'Beitrag · ' + contributors.length + (contributors.length === 1 ? ' sichtbares KR' : ' sichtbare KRs');
                let description = element.querySelector('.explorer-description');
                if (!description) {
                    description = document.createElement('span');
                    description.className = 'explorer-description';
                    description.id = element.id + '-description';
                    element.setAttribute('aria-describedby', description.id);
                    element.append(description);
                }
                description.textContent = 'Beitrag zu: ' + contributors.join('; ');
            }
        }
    }

    function spacedCenters(desired, gap) {
        // Isotonic regression keeps nodes nearest their contributing KRs while
        // enforcing separation. Merge colliding blocks symmetrically, not rightward.
        const blocks = [];
        desired.forEach((center, index) => {
            blocks.push({sum: center - index * gap, count: 1});
            while (blocks.length > 1) {
                const right = blocks[blocks.length - 1], left = blocks[blocks.length - 2];
                if (left.sum / left.count <= right.sum / right.count) break;
                blocks.splice(-2, 2, {sum: left.sum + right.sum, count: left.count + right.count});
            }
        });
        const result = [];
        for (const block of blocks) {
            for (let i = 0; i < block.count; i++) result.push(block.sum / block.count + result.length * gap);
        }
        return result;
    }

    function layout(view) {
        const step = 260, padding = 24;
        const selected = view.rows[0].map(id => nodes.get(id));
        const slots = selected.map(o => Math.max(1, expanded.has(o.id) ? children.get(o.id).length : 1));
        const totalSlots = slots.reduce((sum, n) => sum + n, 0);
        let width = Math.max(viewport.clientWidth, totalSlots * step + padding * 2 - 28);
        const centers = new Map();
        let cursor = (width - totalSlots * step) / 2;
        selected.forEach((o, i) => {
            centers.set(o.id, cursor + slots[i] * step / 2);
            if (expanded.has(o.id)) children.get(o.id).forEach((id, j) => centers.set(id, cursor + (j + .5) * step));
            cursor += slots[i] * step;
        });
        const averages = new Map(view.rows[2].map(id => {
            const sources = view.incoming.get(id);
            return [id, sources.reduce((sum, key) => sum + centers.get(key), 0) / sources.length];
        }));
        view.rows[2].sort((a, b) => averages.get(a) - averages.get(b));
        const activityCenters = spacedCenters(view.rows[2].map(id => averages.get(id)), step);
        view.rows[2].forEach((id, i) => centers.set(id, activityCenters[i]));
        if (centers.size) {
            const shift = Math.max(0, padding + 116 - Math.min(...centers.values()));
            for (const [id, x] of centers) centers.set(id, x + shift);
            width = Math.max(width, Math.max(...centers.values()) + 116 + padding);
        }
        // Measure natural heights in one batch, then equalize each visible rank.
        stage.style.width = width + 'px';
        for (const id of view.visible) elements.get(id).style.height = 'auto';
        const heights = view.rows.map(row => Math.max(0, ...row.map(id => elements.get(id).offsetHeight)));
        const positions = new Map();
        let top = 24;
        view.rows.forEach((row, index) => {
            levels[index].hidden = !row.length;
            if (!row.length) return;
            levels[index].style.top = top + 'px';
            top += 34;
            for (const id of row) {
                const element = elements.get(id);
                const x = centers.get(id);
                element.style.left = (x - 116) + 'px';
                element.style.top = top + 'px';
                element.style.height = heights[index] + 'px';
                positions.set(id, {x, top, bottom: top + heights[index]});
            }
            top += heights[index] + 70;
        });
        const height = Math.max(220, top - 46);
        stage.style.height = height + 'px';
        return {positions, width, height};
    }

    function paintEdges(view, geometry) {
        svg.setAttribute('width', geometry.width);
        svg.setAttribute('height', geometry.height);
        const fragment = document.createDocumentFragment();
        visibleEdges = view.edges.map(([from, to]) => {
            const source = geometry.positions.get(from), target = geometry.positions.get(to);
            const middle = (source.bottom + target.top) / 2;
            const path = document.createElementNS(svgNS, 'path');
            path.classList.add('explorer-edge');
            path.dataset.from = from; path.dataset.to = to;
            path.setAttribute('d', `M ${source.x} ${source.bottom} C ${source.x} ${middle}, ${target.x} ${middle}, ${target.x} ${target.top}`);
            fragment.append(path);
            return {from, to, path};
        });
        svg.replaceChildren(fragment);
    }

    function render() {
        if (!viewport.clientWidth) return;
        const view = projection();
        syncNodes(view);
        geometry = layout(view);
        paintEdges(view, geometry);
        zoom(scale, fitMode);
        const active = document.activeElement.closest('.explorer-node') || stage.querySelector('.explorer-node:hover');
        highlight(active ? active.dataset.node : null);
        status.textContent = `${view.rows[0].length} Objectives · ${view.rows[1].length} KR · ${view.rows[2].length} Beiträge sichtbar`;
        if (!objectives.length) status.textContent = 'Noch keine Objectives vorhanden.';
        empty.hidden = Boolean(view.rows[0].length);
        empty.textContent = objectives.length ? 'Keine Objectives ausgewählt.' : 'Noch keine Objectives vorhanden.';
        root.querySelector('[data-action=all-statuses]').setAttribute('aria-pressed',
            String(filters.every(filter => filter.disabled || filter.checked)));
        root.querySelector('[data-action=collapse]').disabled = !expanded.size;
    }
    filters.forEach(filter => filter.addEventListener('change', () => {
        render(); viewport.scrollTo(0, 0);
    }));
    root.querySelector('[data-action=all-statuses]').addEventListener('click', () => {
        filters.forEach(filter => { if (!filter.disabled) filter.checked = true; });
        render(); viewport.scrollTo(0, 0);
    });
    root.querySelector('[data-action=collapse]').addEventListener('click', () => {
        expanded.clear(); render(); viewport.scrollTo(0, 0);
    });
    const zoomActions = {
        'zoom-out': () => zoom(scale / 1.2),
        'zoom-in': () => zoom(scale * 1.2),
        'zoom-reset': () => zoom(1),
        'zoom-fit': () => zoom(scale, true),
    };
    for (const [action, handler] of Object.entries(zoomActions)) {
        root.querySelector(`[data-action=${action}]`).addEventListener('click', handler);
    }
    viewport.addEventListener('keydown', event => {
        if (event.target !== viewport || event.ctrlKey || event.metaKey || event.altKey) return;
        const action = {'+': 'zoom-in', '=': 'zoom-in', '-': 'zoom-out', '0': 'zoom-reset',
            f: 'zoom-fit', F: 'zoom-fit'}[event.key];
        if (action) { event.preventDefault(); zoomActions[action](); }
    });
    root.querySelector('.explorer-toolbar').hidden = false;
    viewport.hidden = false;
    let lastWidth = -1;
    new ResizeObserver(() => {
        if (viewport.clientWidth !== lastWidth) {
            lastWidth = viewport.clientWidth;
            render();
        }
    }).observe(viewport);
    window.addEventListener('pageshow', render);
    document.fonts.ready.then(render);
})();
