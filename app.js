// EU5 Values Viewer - Main Application

// Global state
let data = {
    values: {},
    ages: {},
    governments: {},
    religions: {},
    movers: []
};

let state = {
    selectedValue: null,
    filters: {
        age: '',
        government: '',
        religion: '',
        search: ''
    }
};

// Age order for comparison
const AGE_ORDER = {
    'age_1_traditions': 1,
    'age_2_renaissance': 2,
    'age_3_discovery': 3,
    'age_4_reformation': 4,
    'age_5_absolutism': 5,
    'age_6_revolutions': 6
};

// Load all data
async function loadData() {
    try {
        const [values, ages, governments, religions, movers] = await Promise.all([
            fetch('data/values.json').then(r => r.json()),
            fetch('data/ages.json').then(r => r.json()),
            fetch('data/governments.json').then(r => r.json()),
            fetch('data/religions.json').then(r => r.json()),
            fetch('data/movers.json').then(r => r.json())
        ]);

        data.values = values;
        data.ages = ages;
        data.governments = governments;
        data.religions = religions;
        data.movers = movers;

        initializeUI();
    } catch (error) {
        console.error('Failed to load data:', error);
        document.querySelector('.panels').innerHTML = `
            <div class="loading" style="grid-column: 1/-1;">
                Failed to load data. Make sure you're running this from a web server.
            </div>
        `;
    }
}

// Initialize the UI
function initializeUI() {
    populateFilters();
    populateValueButtons();
    setupEventListeners();

    // Select first value by default
    const firstValue = Object.keys(data.values)[0];
    if (firstValue) {
        selectValue(firstValue);
    }
}

// Populate filter dropdowns
function populateFilters() {
    // Age filter
    const ageSelect = document.getElementById('age-select');
    Object.entries(data.ages).forEach(([id, age]) => {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = `${age.name} (${age.year}+)`;
        ageSelect.appendChild(option);
    });

    // Government filter
    const govSelect = document.getElementById('government-select');
    Object.entries(data.governments).forEach(([id, gov]) => {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = gov.name;
        govSelect.appendChild(option);
    });

    // Religion filter - group by religion group
    const relSelect = document.getElementById('religion-select');
    const groups = {};
    Object.entries(data.religions).forEach(([id, rel]) => {
        const group = rel.group || 'other';
        if (!groups[group]) groups[group] = [];
        groups[group].push({ id, name: rel.name });
    });

    Object.entries(groups).sort().forEach(([group, religions]) => {
        const optgroup = document.createElement('optgroup');
        optgroup.label = prettifyId(group);
        religions.sort((a, b) => a.name.localeCompare(b.name)).forEach(rel => {
            const option = document.createElement('option');
            option.value = rel.id;
            option.textContent = rel.name;
            optgroup.appendChild(option);
        });
        relSelect.appendChild(optgroup);
    });
}

// Populate value buttons
function populateValueButtons() {
    const container = document.getElementById('value-buttons');
    container.innerHTML = '';

    Object.entries(data.values).forEach(([id, value]) => {
        const btn = document.createElement('button');
        btn.className = 'value-btn';
        btn.dataset.valueId = id;
        btn.textContent = `${value.left.name} vs ${value.right.name}`;

        // Mark as unavailable if age-restricted and no age selected
        if (value.age_requirement) {
            btn.title = `Available from ${prettifyId(value.age_requirement)}`;
        }

        btn.addEventListener('click', () => selectValue(id));
        container.appendChild(btn);
    });
}

// Select a value pair
function selectValue(valueId) {
    state.selectedValue = valueId;

    // Update button states
    document.querySelectorAll('.value-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.valueId === valueId);
    });

    // Update panel headers
    const value = data.values[valueId];
    document.getElementById('left-value-name').textContent = value.left.name;
    document.getElementById('right-value-name').textContent = value.right.name;

    // Update value info
    updateValueInfo(value);

    // Update items
    updateItems();
}

// Update the center info panel
function updateValueInfo(value) {
    const container = document.getElementById('value-info');

    // Count movers for this value
    const leftMovers = data.movers.filter(m =>
        m.value_effects.some(e => e.value_pair === state.selectedValue && e.direction === 'left')
    );
    const rightMovers = data.movers.filter(m =>
        m.value_effects.some(e => e.value_pair === state.selectedValue && e.direction === 'right')
    );

    container.innerHTML = `
        <div class="value-info-section">
            <h3>Selected Value</h3>
            <p><strong>${value.left.name}</strong> vs <strong>${value.right.name}</strong></p>
            ${value.age_requirement ? `<p style="color: var(--accent-neutral);">Available from ${prettifyId(value.age_requirement)}</p>` : ''}
            ${value.conditions ? `<p style="color: var(--text-muted); font-size: 0.8rem;">Has special conditions</p>` : ''}
        </div>

        <div class="value-info-section">
            <h3>Statistics</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value" style="color: var(--accent-left);">${leftMovers.length}</div>
                    <div class="stat-label">Push Left</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" style="color: var(--accent-right);">${rightMovers.length}</div>
                    <div class="stat-label">Push Right</div>
                </div>
            </div>
        </div>

        <div class="value-info-section">
            <h3>Tips</h3>
            <p style="font-size: 0.8rem; color: var(--text-secondary);">
                Grayed items don't match your current filters but are still available under different conditions.
            </p>
        </div>
    `;
}

// Update items in left and right panels
function updateItems() {
    if (!state.selectedValue) return;

    const leftContainer = document.getElementById('left-items');
    const rightContainer = document.getElementById('right-items');

    // Filter movers that affect this value
    const leftMovers = data.movers.filter(m =>
        m.value_effects.some(e => e.value_pair === state.selectedValue && e.direction === 'left')
    );
    const rightMovers = data.movers.filter(m =>
        m.value_effects.some(e => e.value_pair === state.selectedValue && e.direction === 'right')
    );

    // Apply search filter
    const searchTerm = state.filters.search.toLowerCase();
    const filterBySearch = (movers) => {
        if (!searchTerm) return movers;
        return movers.filter(m =>
            m.name.toLowerCase().includes(searchTerm) ||
            m.type.toLowerCase().includes(searchTerm) ||
            (m.category_name && m.category_name.toLowerCase().includes(searchTerm))
        );
    };

    // Render panels
    leftContainer.innerHTML = renderItems(filterBySearch(leftMovers), 'left');
    rightContainer.innerHTML = renderItems(filterBySearch(rightMovers), 'right');
}

// Render items for a panel
function renderItems(movers, direction) {
    if (movers.length === 0) {
        return '<p class="placeholder">No items found</p>';
    }

    // Sort by type, then by grayed-out status, then by name
    const sorted = [...movers].sort((a, b) => {
        const aGrayed = shouldGrayOut(a);
        const bGrayed = shouldGrayOut(b);
        if (aGrayed !== bGrayed) return aGrayed ? 1 : -1;
        if (a.type !== b.type) return a.type.localeCompare(b.type);
        return a.name.localeCompare(b.name);
    });

    // Group by type
    const groups = {};
    sorted.forEach(mover => {
        const type = mover.type;
        if (!groups[type]) groups[type] = [];
        groups[type].push(mover);
    });

    let html = '';
    Object.entries(groups).forEach(([type, items]) => {
        html += `<div class="item-group">
            <div class="item-type-header" style="padding: 0.5rem 0; color: var(--text-secondary); font-size: 0.75rem; text-transform: uppercase; border-bottom: 1px solid var(--border-color); margin-bottom: 0.5rem;">
                ${prettifyId(type)}s (${items.length})
            </div>`;

        items.forEach(mover => {
            html += renderItemCard(mover, direction);
        });

        html += '</div>';
    });

    return html;
}

// Render a single item card
function renderItemCard(mover, direction) {
    const grayed = shouldGrayOut(mover);
    const effect = mover.value_effects.find(e =>
        e.value_pair === state.selectedValue && e.direction === direction
    );

    // Get other effects this item has
    const otherEffects = mover.value_effects.filter(e =>
        e.value_pair !== state.selectedValue
    );

    let strengthDisplay = effect.strength !== null ? effect.strength.toFixed(2) : effect.strength_raw;

    let requirementsHtml = '';
    const reqs = mover.requirements || {};
    const reqParts = [];

    if (reqs.age) reqParts.push(`Age: ${prettifyId(reqs.age)}`);
    if (reqs.government) reqParts.push(`Gov: ${reqs.government.map(prettifyId).join(', ')}`);
    if (reqs.religion) reqParts.push(`Religion: ${reqs.religion.slice(0, 3).map(prettifyId).join(', ')}${reqs.religion.length > 3 ? '...' : ''}`);
    if (mover.estate) reqParts.push(`Estate: ${prettifyId(mover.estate)}`);
    if (mover.category_name) reqParts.push(`Law: ${mover.category_name}`);

    if (reqParts.length > 0) {
        requirementsHtml = `<div class="item-requirements">${reqParts.join(' | ')}</div>`;
    }

    // Other effects indicator
    let otherEffectsHtml = '';
    if (otherEffects.length > 0) {
        otherEffectsHtml = '<div class="multi-effect">';
        otherEffects.slice(0, 3).forEach(e => {
            const valueName = data.values[e.value_pair];
            if (valueName) {
                const targetName = e.direction === 'left' ? valueName.left.name : valueName.right.name;
                otherEffectsHtml += `<span class="effect-tag ${e.direction}">+${targetName}</span>`;
            }
        });
        if (otherEffects.length > 3) {
            otherEffectsHtml += `<span class="effect-tag">+${otherEffects.length - 3} more</span>`;
        }
        otherEffectsHtml += '</div>';
    }

    return `
        <div class="item-card ${grayed ? 'grayed-out' : ''}">
            <div class="item-header">
                <span class="item-name">${mover.name}</span>
                <span class="item-strength">${strengthDisplay}/mo</span>
            </div>
            <div class="item-meta">
                <span class="item-type ${mover.type}">${prettifyId(mover.type)}</span>
            </div>
            ${otherEffectsHtml}
            ${requirementsHtml}
        </div>
    `;
}

// Check if an item should be grayed out based on filters
function shouldGrayOut(mover) {
    const reqs = mover.requirements || {};

    // Age check
    if (state.filters.age && reqs.age) {
        const selectedAgeOrder = AGE_ORDER[state.filters.age] || 0;
        const requiredAgeOrder = AGE_ORDER[reqs.age] || 0;
        if (requiredAgeOrder > selectedAgeOrder) {
            return true;
        }
    }

    // Government check
    if (state.filters.government && reqs.government) {
        if (!reqs.government.includes(state.filters.government)) {
            return true;
        }
    }

    // Religion check
    if (state.filters.religion && reqs.religion) {
        if (!reqs.religion.includes(state.filters.religion)) {
            // Also check religion group
            const selectedRel = data.religions[state.filters.religion];
            if (selectedRel && reqs.religion_group) {
                if (!reqs.religion_group.includes(selectedRel.group)) {
                    return true;
                }
            } else {
                return true;
            }
        }
    }

    return false;
}

// Setup event listeners
function setupEventListeners() {
    // Filter changes
    document.getElementById('age-select').addEventListener('change', (e) => {
        state.filters.age = e.target.value;
        updateValueButtonAvailability();
        updateItems();
    });

    document.getElementById('government-select').addEventListener('change', (e) => {
        state.filters.government = e.target.value;
        updateItems();
    });

    document.getElementById('religion-select').addEventListener('change', (e) => {
        state.filters.religion = e.target.value;
        updateItems();
    });

    // Search input with debounce
    let searchTimeout;
    document.getElementById('search-input').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            state.filters.search = e.target.value;
            updateItems();
        }, 200);
    });
}

// Update value button availability based on age filter
function updateValueButtonAvailability() {
    document.querySelectorAll('.value-btn').forEach(btn => {
        const valueId = btn.dataset.valueId;
        const value = data.values[valueId];

        if (value.age_requirement && state.filters.age) {
            const selectedAgeOrder = AGE_ORDER[state.filters.age] || 0;
            const requiredAgeOrder = AGE_ORDER[value.age_requirement] || 0;
            btn.classList.toggle('unavailable', requiredAgeOrder > selectedAgeOrder);
        } else {
            btn.classList.remove('unavailable');
        }
    });
}

// Utility: Prettify ID string
function prettifyId(id) {
    if (!id) return '';
    return id
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase())
        .replace(/ Vs /g, ' vs ')
        .replace(/ Of /g, ' of ')
        .replace(/ The /g, ' the ')
        .replace(/ And /g, ' and ')
        .replace(/^Age (\d)/, 'Age $1:');
}

// Initialize on load
document.addEventListener('DOMContentLoaded', loadData);
