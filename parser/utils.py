"""
Utility functions for the EU5 Values Viewer parser.
"""

import re
from typing import Optional

# Known strength modifier mappings (estimated values based on game file analysis)
STRENGTH_VALUES = {
    'societal_value_tiny_monthly_move': 0.02,
    'societal_value_minor_monthly_move': 0.05,
    'societal_value_monthly_move': 0.10,
    'societal_value_large_monthly_move': 0.20,
    'societal_value_huge_monthly_move': 0.50,  # Special for temporary effects
}

# Value name mappings (left side of value pair -> full pair name)
VALUE_SIDES = {}  # Will be populated by values extractor

# Advances and their requirements (populated by parser)
ADVANCES = {}  # advance_id -> {requirements: {...}, age: str}


def resolve_advance_requirements(requirements: dict) -> dict:
    """
    If requirements include has_advance, look up the advance's requirements
    and merge them into the item's requirements.
    """
    if 'has_advance' not in requirements or not requirements['has_advance']:
        return requirements

    for advance_id in requirements['has_advance']:
        if advance_id in ADVANCES:
            advance_data = ADVANCES[advance_id]
            advance_reqs = advance_data.get('requirements', {})

            # Merge advance requirements into item requirements
            for key, values in advance_reqs.items():
                if key == 'has_or_condition':
                    requirements['has_or_condition'] = True
                elif isinstance(values, list):
                    # Normalize values (strip prefixes like "religion:")
                    normalized = []
                    for v in values:
                        if isinstance(v, str) and ':' in v:
                            v = v.split(':')[-1]  # Take part after colon
                        normalized.append(v)
                    requirements.setdefault(key, []).extend(normalized)
                else:
                    requirements[key] = values

            # Also note the advance's age requirement
            if advance_data.get('age') and not requirements.get('age'):
                requirements['age'] = advance_data['age']

    # Deduplicate list values
    for key, value in requirements.items():
        if isinstance(value, list):
            requirements[key] = list(dict.fromkeys(value))  # Preserve order, remove dupes

    return requirements


def prettify_id(id_str: str) -> str:
    """Convert a game ID to a human-readable display name."""
    if not id_str:
        return id_str

    # Remove common prefixes
    prefixes = [
        'government_reform:', 'estate_privilege:', 'law:', 'policy:',
        'trait:', 'building:', 'religion:', 'culture:', 'advance:'
    ]
    for prefix in prefixes:
        if id_str.startswith(prefix):
            id_str = id_str[len(prefix):]

    # Replace underscores with spaces
    name = id_str.replace('_', ' ')

    # Title case
    name = name.title()

    # Fix common terms
    replacements = {
        ' Vs ': ' vs ',
        ' Of ': ' of ',
        ' The ': ' the ',
        ' And ': ' and ',
        ' For ': ' for ',
        ' To ': ' to ',
        ' In ': ' in ',
        ' On ': ' on ',
        ' A ': ' a ',
        ' An ': ' an ',
        'Hre ': 'HRE ',
        ' Hre': ' HRE',
        'Dop ': '',  # Remove "Distribution of Power" prefix
        'Io ': 'IO ',
        ' Io': ' IO',
        'Ai ': 'AI ',
        ' Ai': ' AI',
    }
    for old, new in replacements.items():
        name = name.replace(old, new)

    # Ensure first letter is capitalized
    if name:
        name = name[0].upper() + name[1:]

    return name.strip()


def get_strength_value(modifier_value) -> Optional[float]:
    """
    Convert a strength modifier to a numeric value.

    Args:
        modifier_value: Either a numeric value or a string constant

    Returns:
        Float value or None if unknown
    """
    if isinstance(modifier_value, (int, float)):
        return float(modifier_value)

    if isinstance(modifier_value, str):
        return STRENGTH_VALUES.get(modifier_value)

    return None


def extract_value_effects(modifiers: dict) -> list:
    """
    Extract value effects from a modifier block.

    Args:
        modifiers: Dictionary of modifiers (e.g., country_modifier block)

    Returns:
        List of value effect dicts with value_pair, direction, strength
    """
    effects = []

    if not isinstance(modifiers, dict):
        return effects

    for key, value in modifiers.items():
        if key.startswith('monthly_towards_'):
            value_side = key[len('monthly_towards_'):]

            # Determine the value pair and direction
            value_pair, direction = find_value_pair(value_side)

            if value_pair:
                strength = get_strength_value(value)
                effects.append({
                    'value_pair': value_pair,
                    'direction': direction,
                    'target': value_side,
                    'strength': strength,
                    'strength_raw': str(value) if not isinstance(value, (int, float)) else value
                })

    return effects


def find_value_pair(value_side: str) -> tuple:
    """
    Find which value pair a side belongs to and whether it's left or right.

    Returns:
        (value_pair_id, 'left'|'right') or (None, None) if not found
    """
    # Will be populated after values are extracted
    if value_side in VALUE_SIDES:
        return VALUE_SIDES[value_side]
    return (None, None)


def extract_requirements(data: dict) -> dict:
    """
    Extract requirements from potential/allow/locked blocks.

    Args:
        data: The full item data dictionary

    Returns:
        Dictionary of requirements
    """
    requirements = {}

    # Government type
    if 'government' in data:
        gov = data['government']
        if isinstance(gov, list):
            requirements['government'] = gov
        else:
            requirements['government'] = [gov]

    # Age requirement
    if 'age' in data:
        requirements['age'] = data['age']

    # Parse potential block
    if 'potential' in data and isinstance(data['potential'], dict):
        _extract_trigger_requirements(data['potential'], requirements)

    # Parse allow block
    if 'allow' in data and isinstance(data['allow'], dict):
        _extract_trigger_requirements(data['allow'], requirements)

    return requirements


def _extract_trigger_requirements(trigger: dict, requirements: dict):
    """Extract requirements from a trigger block."""

    # Religion
    if 'religion' in trigger:
        rel = trigger['religion']
        if isinstance(rel, list):
            requirements.setdefault('religion', []).extend(rel)
        elif isinstance(rel, str):
            requirements.setdefault('religion', []).append(rel)

    if 'religion_group' in trigger:
        rg = trigger['religion_group']
        if isinstance(rg, list):
            requirements.setdefault('religion_group', []).extend(rg)
        elif isinstance(rg, str):
            requirements.setdefault('religion_group', []).append(rg)

    # Country tag - both 'tag' and 'has_or_had_tag'
    if 'tag' in trigger:
        tag = trigger['tag']
        if isinstance(tag, list):
            requirements.setdefault('country', []).extend(tag)
        elif isinstance(tag, str):
            requirements.setdefault('country', []).append(tag)

    if 'has_or_had_tag' in trigger:
        tag = trigger['has_or_had_tag']
        if isinstance(tag, list):
            requirements.setdefault('country', []).extend(tag)
        elif isinstance(tag, str):
            requirements.setdefault('country', []).append(tag)

    # Has reform
    if 'has_reform' in trigger:
        reform = trigger['has_reform']
        if isinstance(reform, list):
            requirements.setdefault('has_reform', []).extend(reform)
        elif isinstance(reform, str):
            requirements.setdefault('has_reform', []).append(reform)

    # Has privilege
    if 'has_privilege' in trigger:
        priv = trigger['has_privilege']
        if isinstance(priv, list):
            requirements.setdefault('has_privilege', []).extend(priv)
        elif isinstance(priv, str):
            requirements.setdefault('has_privilege', []).append(priv)

    # Government type in trigger
    if 'government_type' in trigger:
        gov = trigger['government_type']
        if isinstance(gov, str):
            # Handle "government_type:monarchy" format
            if ':' in gov:
                gov = gov.split(':')[1]
            requirements.setdefault('government', []).append(gov)

    if 'has_government_type' in trigger:
        gov_data = trigger['has_government_type']
        if isinstance(gov_data, dict) and 'type' in gov_data:
            gov = gov_data['type']
            if isinstance(gov, str) and ':' in gov:
                gov = gov.split(':')[1]
            requirements.setdefault('government', []).append(gov)

    # Culture
    if 'culture' in trigger:
        culture = trigger['culture']
        if isinstance(culture, list):
            requirements.setdefault('culture', []).extend(culture)
        elif isinstance(culture, str):
            requirements.setdefault('culture', []).append(culture)

    if 'culture_group' in trigger:
        cg = trigger['culture_group']
        if isinstance(cg, list):
            requirements.setdefault('culture_group', []).extend(cg)
        elif isinstance(cg, str):
            # Handle "culture_group:xxx" format
            if ':' in cg:
                cg = cg.split(':')[1]
            requirements.setdefault('culture_group', []).append(cg)

    if 'has_culture_group' in trigger:
        cg_data = trigger['has_culture_group']
        if isinstance(cg_data, dict):
            # Could have nested structure
            pass
        elif isinstance(cg_data, str):
            if ':' in cg_data:
                cg_data = cg_data.split(':')[1]
            requirements.setdefault('culture_group', []).append(cg_data)

    # Estate
    if 'estate' in trigger:
        estate = trigger['estate']
        if isinstance(estate, list):
            requirements.setdefault('estate', []).extend(estate)
        elif isinstance(estate, str):
            requirements.setdefault('estate', []).append(estate)

    # Has advance (technology/unlock requirement)
    if 'has_advance' in trigger:
        advance = trigger['has_advance']
        if isinstance(advance, list):
            requirements.setdefault('has_advance', []).extend(advance)
        elif isinstance(advance, str):
            requirements.setdefault('has_advance', []).append(advance)

    # OR blocks - recurse into them to find requirements
    if 'OR' in trigger and isinstance(trigger['OR'], dict):
        requirements['has_or_condition'] = True
        _extract_trigger_requirements(trigger['OR'], requirements)

    # NOT blocks - note exclusions
    if 'NOT' in trigger and isinstance(trigger['NOT'], dict):
        not_block = trigger['NOT']
        if 'tag' in not_block:
            requirements.setdefault('excluded_countries', []).append(not_block['tag'])
        if 'has_or_had_tag' in not_block:
            requirements.setdefault('excluded_countries', []).append(not_block['has_or_had_tag'])
        if 'has_reform' in not_block:
            requirements.setdefault('excluded_reforms', []).append(not_block['has_reform'])
        if 'culture_group' in not_block:
            cg = not_block['culture_group']
            if isinstance(cg, str) and ':' in cg:
                cg = cg.split(':')[1]
            requirements.setdefault('excluded_culture_groups', []).append(cg)
