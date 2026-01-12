// EU5 Values Viewer - Main Application

// Global state
let data = {
    values: {},
    ages: {},
    governments: {},
    religions: {},
    countries: {},
    estates: {},
    movers: []
};

let state = {
    selectedValue: null,
    filters: {
        age: '',
        government: '',
        religion: '',
        country: '',
        estate: '',
        culture: '',
        search: ''
    },
    sortBy: 'type' // 'type', 'strength-desc', 'strength-asc', 'name'
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
        const [values, ages, governments, religions, countries, estates, movers] = await Promise.all([
            fetch('data/values.json').then(r => r.json()),
            fetch('data/ages.json').then(r => r.json()),
            fetch('data/governments.json').then(r => r.json()),
            fetch('data/religions.json').then(r => r.json()),
            fetch('data/countries.json').then(r => r.json()),
            fetch('data/estates.json').then(r => r.json()),
            fetch('data/movers.json').then(r => r.json())
        ]);

        data.values = values;
        data.ages = ages;
        data.governments = governments;
        data.religions = religions;
        data.countries = countries;
        data.estates = estates;
        data.movers = movers;

        initializeUI();
    } catch (error) {
        console.error('Failed to load data:', error);
        document.querySelector('.panels').innerHTML = `
            <div class="loading" style="grid-column: 1/-1;">
                Failed to load data. Make sure you're running this from a web server or GitHub Pages.
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

    // Estate filter
    const estateSelect = document.getElementById('estate-select');
    Object.entries(data.estates).forEach(([id, estate]) => {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = estate.name;
        estateSelect.appendChild(option);
    });

    // Culture filter - extract unique cultures from movers
    const cultureSelect = document.getElementById('culture-select');
    const cultures = new Set();
    data.movers.forEach(m => {
        if (m.requirements && m.requirements.culture) {
            m.requirements.culture.forEach(c => cultures.add(c));
        }
    });
    [...cultures].sort().forEach(culture => {
        const option = document.createElement('option');
        option.value = culture;
        option.textContent = prettifyId(culture);
        cultureSelect.appendChild(option);
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

    // Country filter - sorted alphabetically by tag
    const countrySelect = document.getElementById('country-select');
    const countryList = Object.entries(data.countries)
        .map(([tag, c]) => ({ tag, name: c.name || prettifyId(tag) }))
        .sort((a, b) => a.tag.localeCompare(b.tag));

    countryList.forEach(c => {
        const option = document.createElement('option');
        option.value = c.tag;
        option.textContent = `${c.tag} - ${c.name}`;
        countrySelect.appendChild(option);
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

    // Update items and info
    updateItems();
}

// Check if an item passes all filters (should be shown)
function passesFilters(mover) {
    const reqs = mover.requirements || {};

    // Age check - hide if requires a LATER age than selected
    if (state.filters.age && reqs.age) {
        const selectedAgeOrder = AGE_ORDER[state.filters.age] || 0;
        const requiredAgeOrder = AGE_ORDER[reqs.age] || 0;
        if (requiredAgeOrder > selectedAgeOrder) {
            return false;
        }
    }

    // Government check - hide if requires a DIFFERENT government
    if (state.filters.government && reqs.government && reqs.government.length > 0) {
        if (!reqs.government.includes(state.filters.government)) {
            return false;
        }
    }

    // Religion check - hide if requires a DIFFERENT religion
    if (state.filters.religion && reqs.religion && reqs.religion.length > 0) {
        const selectedRel = data.religions[state.filters.religion];
        const matchesReligion = reqs.religion.includes(state.filters.religion);
        const matchesGroup = selectedRel && reqs.religion_group &&
                             reqs.religion_group.includes(selectedRel.group);
        if (!matchesReligion && !matchesGroup) {
            return false;
        }
    }

    // Country check - hide if requires a DIFFERENT country
    if (state.filters.country && reqs.country && reqs.country.length > 0) {
        if (!reqs.country.includes(state.filters.country)) {
            return false;
        }
    }

    // Check excluded countries
    if (state.filters.country && reqs.excluded_countries && reqs.excluded_countries.length > 0) {
        if (reqs.excluded_countries.includes(state.filters.country)) {
            return false;
        }
    }

    // Estate check - only show privileges for selected estate
    if (state.filters.estate) {
        // If item is a privilege, it must match the selected estate
        if (mover.type === 'privilege') {
            if (mover.estate !== state.filters.estate) {
                return false;
            }
        }
        // Non-privilege items are hidden when estate filter is active
        // (user is specifically looking for estate privileges)
    }

    // Culture check - hide if requires a DIFFERENT culture
    if (state.filters.culture && reqs.culture && reqs.culture.length > 0) {
        if (!reqs.culture.includes(state.filters.culture)) {
            return false;
        }
    }

    return true;
}

// Update items in left and right panels
function updateItems() {
    if (!state.selectedValue) return;

    const leftContainer = document.getElementById('left-items');
    const rightContainer = document.getElementById('right-items');

    // Filter movers that affect this value
    const allLeftMovers = data.movers.filter(m =>
        m.value_effects.some(e => e.value_pair === state.selectedValue && e.direction === 'left')
    );
    const allRightMovers = data.movers.filter(m =>
        m.value_effects.some(e => e.value_pair === state.selectedValue && e.direction === 'right')
    );

    // Apply filters - only show items that pass
    let leftMovers = allLeftMovers.filter(passesFilters);
    let rightMovers = allRightMovers.filter(passesFilters);

    // Apply search filter
    const searchTerm = state.filters.search.toLowerCase();
    if (searchTerm) {
        const searchFilter = (m) =>
            m.name.toLowerCase().includes(searchTerm) ||
            m.type.toLowerCase().includes(searchTerm) ||
            (m.category_name && m.category_name.toLowerCase().includes(searchTerm)) ||
            (m.source && m.source.toLowerCase().includes(searchTerm));
        leftMovers = leftMovers.filter(searchFilter);
        rightMovers = rightMovers.filter(searchFilter);
    }

    // Update value info with counts
    updateValueInfo(leftMovers.length, rightMovers.length, allLeftMovers.length, allRightMovers.length);

    // Render panels
    leftContainer.innerHTML = renderItems(leftMovers, 'left');
    rightContainer.innerHTML = renderItems(rightMovers, 'right');
}

// Update the center info panel
function updateValueInfo(leftCount, rightCount, totalLeft, totalRight) {
    const container = document.getElementById('value-info');
    const value = data.values[state.selectedValue];

    const hasFilters = state.filters.age || state.filters.government ||
                       state.filters.religion || state.filters.country ||
                       state.filters.estate || state.filters.culture;

    container.innerHTML = `
        <div class="value-info-section">
            <h3>Selected Value</h3>
            <p><strong>${value.left.name}</strong> vs <strong>${value.right.name}</strong></p>
            ${value.age_requirement ? `<p class="age-note">Available from ${prettifyId(value.age_requirement)}</p>` : ''}
        </div>

        <div class="value-info-section">
            <h3>Matching Items</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value" style="color: var(--accent-left);">${leftCount}</div>
                    <div class="stat-label">${value.left.name}</div>
                    ${hasFilters ? `<div class="stat-total">of ${totalLeft} total</div>` : ''}
                </div>
                <div class="stat-item">
                    <div class="stat-value" style="color: var(--accent-right);">${rightCount}</div>
                    <div class="stat-label">${value.right.name}</div>
                    ${hasFilters ? `<div class="stat-total">of ${totalRight} total</div>` : ''}
                </div>
            </div>
        </div>

        <div class="value-info-section">
            <h3>Active Filters</h3>
            <div class="active-filters">
                ${state.filters.age ? `<span class="filter-tag">Age: ${prettifyId(state.filters.age)}</span>` : ''}
                ${state.filters.government ? `<span class="filter-tag">Gov: ${prettifyId(state.filters.government)}</span>` : ''}
                ${state.filters.religion ? `<span class="filter-tag">Religion: ${prettifyId(state.filters.religion)}</span>` : ''}
                ${state.filters.country ? `<span class="filter-tag">Country: ${state.filters.country}</span>` : ''}
                ${state.filters.estate ? `<span class="filter-tag">Estate: ${prettifyId(state.filters.estate.replace('_estate', ''))}</span>` : ''}
                ${state.filters.culture ? `<span class="filter-tag">Culture: ${prettifyId(state.filters.culture)}</span>` : ''}
                ${!hasFilters ? '<span class="no-filters">None - showing all items</span>' : ''}
            </div>
        </div>

        <div class="value-info-section">
            <h3>Legend</h3>
            <div class="legend">
                <div class="legend-row"><span class="legend-bar strength-large"></span> 0.20/mo (large)</div>
                <div class="legend-row"><span class="legend-bar strength-normal"></span> 0.10/mo (normal)</div>
                <div class="legend-row"><span class="legend-bar strength-minor"></span> 0.05/mo (minor)</div>
                <div class="legend-row"><span class="legend-bar strength-tiny"></span> 0.02/mo (tiny)</div>
            </div>
            <div class="tag-legend">
                <span class="source-tag source-gov">Gov</span>
                <span class="source-tag source-age">Age</span>
                <span class="source-tag source-country">Country</span>
                <span class="source-tag source-religion">Religion</span>
                <span class="source-tag source-culture">Culture</span>
                <span class="source-tag source-exclude">NOT:</span>
            </div>
        </div>
    `;
}

// Get strength for sorting
function getStrengthForSort(mover, direction) {
    const effect = mover.value_effects.find(e =>
        e.value_pair === state.selectedValue && e.direction === direction
    );
    return effect && effect.strength !== null ? effect.strength : 0;
}

// Render items for a panel
function renderItems(movers, direction) {
    if (movers.length === 0) {
        return '<p class="placeholder">No matching items</p>';
    }

    let sorted = [...movers];

    // Apply sorting
    switch (state.sortBy) {
        case 'strength-desc':
            sorted.sort((a, b) => getStrengthForSort(b, direction) - getStrengthForSort(a, direction));
            break;
        case 'strength-asc':
            sorted.sort((a, b) => getStrengthForSort(a, direction) - getStrengthForSort(b, direction));
            break;
        case 'name':
            sorted.sort((a, b) => a.name.localeCompare(b.name));
            break;
        case 'type':
        default:
            sorted.sort((a, b) => {
                if (a.type !== b.type) return a.type.localeCompare(b.type);
                return a.name.localeCompare(b.name);
            });
            break;
    }

    // Group by type only if sorting by type
    if (state.sortBy === 'type') {
        const groups = {};
        sorted.forEach(mover => {
            const type = mover.type;
            if (!groups[type]) groups[type] = [];
            groups[type].push(mover);
        });

        let html = '';
        Object.entries(groups).forEach(([type, items]) => {
            const groupId = `${direction}-${type}`;
            html += `<div class="item-group collapsed" data-group="${groupId}">
                <div class="item-type-header" onclick="toggleGroup('${groupId}')">
                    <span class="collapse-icon">▶</span>
                    ${prettifyId(type)}s (${items.length})
                </div>
                <div class="item-group-content">`;

            items.forEach(mover => {
                html += renderItemCard(mover, direction);
            });

            html += '</div></div>';
        });

        return html;
    } else {
        // Flat list for other sort modes - no collapsing
        let html = '<div class="item-group">';
        sorted.forEach(mover => {
            html += renderItemCard(mover, direction);
        });
        html += '</div>';
        return html;
    }
}

// Toggle group collapse state
function toggleGroup(groupId) {
    const group = document.querySelector(`[data-group="${groupId}"]`);
    if (group) {
        group.classList.toggle('collapsed');
    }
}

// Expand/collapse all groups in a panel
function expandAll(panelId) {
    document.querySelectorAll(`#${panelId} .item-group`).forEach(g => g.classList.remove('collapsed'));
}

function collapseAll(panelId) {
    document.querySelectorAll(`#${panelId} .item-group`).forEach(g => g.classList.add('collapsed'));
}

// Get strength class for color coding
function getStrengthClass(strength) {
    if (strength === null) return 'strength-unknown';
    if (strength >= 0.20) return 'strength-large';
    if (strength >= 0.10) return 'strength-normal';
    if (strength >= 0.05) return 'strength-minor';
    return 'strength-tiny';
}

// Render a single item card
function renderItemCard(mover, direction) {
    const effect = mover.value_effects.find(e =>
        e.value_pair === state.selectedValue && e.direction === direction
    );

    let strengthDisplay = effect.strength !== null ? effect.strength.toFixed(2) : effect.strength_raw;
    const strengthClass = getStrengthClass(effect.strength);

    // Build requirements/source display
    const reqs = mover.requirements || {};
    const sourceParts = [];

    // Type-specific source
    if (mover.type === 'reform') {
        sourceParts.push(`<span class="source-tag source-type">Reform</span>`);
        if (reqs.government && reqs.government.length > 0) {
            sourceParts.push(`<span class="source-tag source-gov">${reqs.government.map(prettifyId).join('/')}</span>`);
        }
    } else if (mover.type === 'law') {
        sourceParts.push(`<span class="source-tag source-type">Law</span>`);
        if (mover.category_name) {
            sourceParts.push(`<span class="source-tag source-category">${mover.category_name}</span>`);
        }
    } else if (mover.type === 'privilege') {
        sourceParts.push(`<span class="source-tag source-type">Privilege</span>`);
        if (mover.estate) {
            sourceParts.push(`<span class="source-tag source-estate">${prettifyId(mover.estate.replace('_estate', ''))}</span>`);
        }
    } else if (mover.type === 'trait') {
        sourceParts.push(`<span class="source-tag source-type">Ruler Trait</span>`);
    } else if (mover.type === 'building') {
        sourceParts.push(`<span class="source-tag source-type">Building</span>`);
    } else if (mover.type === 'religious_aspect') {
        sourceParts.push(`<span class="source-tag source-type">Religious Aspect</span>`);
    } else if (mover.type === 'parliament_issue') {
        sourceParts.push(`<span class="source-tag source-type">Parliament</span>`);
    } else {
        sourceParts.push(`<span class="source-tag source-type">${prettifyId(mover.type)}</span>`);
    }

    // Age requirement
    if (reqs.age) {
        sourceParts.push(`<span class="source-tag source-age">${prettifyId(reqs.age)}</span>`);
    }

    // Country requirement
    if (reqs.country && reqs.country.length > 0) {
        const tags = [...new Set(reqs.country)].slice(0, 3);
        sourceParts.push(`<span class="source-tag source-country">${tags.join('/')}${reqs.country.length > 3 ? '...' : ''}</span>`);
    }

    // Religion requirement (for non-religious-aspect items)
    if (mover.type !== 'religious_aspect' && reqs.religion && reqs.religion.length > 0) {
        const relNames = reqs.religion.slice(0, 2).map(prettifyId).join('/');
        sourceParts.push(`<span class="source-tag source-religion">${relNames}${reqs.religion.length > 2 ? '...' : ''}</span>`);
    }

    // Culture requirement
    if (reqs.culture && reqs.culture.length > 0) {
        const cultures = reqs.culture.slice(0, 2).map(prettifyId).join('/');
        sourceParts.push(`<span class="source-tag source-culture">${cultures}${reqs.culture.length > 2 ? '...' : ''}</span>`);
    }

    // Excluded reforms (blocking conditions)
    if (reqs.excluded_reforms && reqs.excluded_reforms.length > 0) {
        const excluded = reqs.excluded_reforms.slice(0, 2).map(r => prettifyId(r.replace('government_reform:', '')));
        sourceParts.push(`<span class="source-tag source-exclude">NOT: ${excluded.join('/')}${reqs.excluded_reforms.length > 2 ? '...' : ''}</span>`);
    }

    // Excluded countries
    if (reqs.excluded_countries && reqs.excluded_countries.length > 0) {
        sourceParts.push(`<span class="source-tag source-exclude">NOT: ${reqs.excluded_countries.join('/')}</span>`);
    }

    // Other effects this item has
    const otherEffects = mover.value_effects.filter(e => e.value_pair !== state.selectedValue);
    let otherEffectsHtml = '';
    if (otherEffects.length > 0) {
        otherEffectsHtml = '<div class="other-effects">';
        otherEffects.slice(0, 3).forEach(e => {
            const valueDef = data.values[e.value_pair];
            if (valueDef) {
                const targetName = e.direction === 'left' ? valueDef.left.name : valueDef.right.name;
                otherEffectsHtml += `<span class="effect-tag ${e.direction}">+${targetName}</span>`;
            }
        });
        if (otherEffects.length > 3) {
            otherEffectsHtml += `<span class="effect-tag">+${otherEffects.length - 3} more</span>`;
        }
        otherEffectsHtml += '</div>';
    }

    // Prerequisites (requires other reforms/privileges)
    let prereqHtml = '';
    if (reqs.has_reform && reqs.has_reform.length > 0) {
        prereqHtml += `<div class="prereq">Requires: ${reqs.has_reform.map(r => prettifyId(r.replace('government_reform:', ''))).join(', ')}</div>`;
    }
    if (reqs.has_privilege && reqs.has_privilege.length > 0) {
        prereqHtml += `<div class="prereq">Requires: ${reqs.has_privilege.map(prettifyId).join(', ')}</div>`;
    }

    return `
        <div class="item-card ${strengthClass}">
            <div class="item-header">
                <span class="item-name">${mover.name}</span>
                <span class="item-strength">${strengthDisplay}/mo</span>
            </div>
            <div class="item-source">
                ${sourceParts.join('')}
            </div>
            ${otherEffectsHtml}
            ${prereqHtml}
        </div>
    `;
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

    document.getElementById('country-select').addEventListener('change', (e) => {
        state.filters.country = e.target.value;
        // Auto-set religion based on country if not already set
        if (e.target.value && !state.filters.religion) {
            const country = data.countries[e.target.value];
            if (country && country.religion) {
                document.getElementById('religion-select').value = country.religion;
                state.filters.religion = country.religion;
            }
        }
        updateItems();
    });

    document.getElementById('estate-select').addEventListener('change', (e) => {
        state.filters.estate = e.target.value;
        updateItems();
    });

    document.getElementById('culture-select').addEventListener('change', (e) => {
        state.filters.culture = e.target.value;
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

    // Sort dropdown
    document.getElementById('sort-select').addEventListener('change', (e) => {
        state.sortBy = e.target.value;
        updateItems();
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
        .replace(/^Age (\d)/, 'Age $1:')
        .replace(/Government Type:?/gi, '')
        .replace(/Estate Type:?/gi, '')
        .trim();
}

// Initialize on load
document.addEventListener('DOMContentLoaded', loadData);
