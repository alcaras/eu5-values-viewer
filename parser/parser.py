#!/usr/bin/env python3
"""
EU5 Values Viewer - Data Parser

Extracts game data from EU5 files and generates JSON for the web viewer.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

from clausewitz import parse_file, parse_all_in_directory
import utils


# Base path to game files
GAME_PATH = Path(__file__).parent.parent
COMMON_PATH = GAME_PATH / "common"
SETUP_PATH = GAME_PATH / "setup"
EVENTS_PATH = GAME_PATH / "events"
OUTPUT_PATH = GAME_PATH / "values-viewer" / "data"


def extract_values() -> dict:
    """Extract societal value pair definitions."""
    print("Extracting societal values...")

    values_file = COMMON_PATH / "societal_values" / "00_default.txt"
    data = parse_file(values_file)

    values = {}

    for key, value_data in data.items():
        if not isinstance(value_data, dict):
            continue

        # Parse value pair name
        if '_vs_' in key:
            parts = key.split('_vs_')
            left_id = parts[0]
            right_id = '_'.join(parts[1:]) if len(parts) > 1 else parts[0]
        else:
            continue  # Skip non-value entries

        # Register the value sides for lookup
        utils.VALUE_SIDES[left_id] = (key, 'left')
        utils.VALUE_SIDES[right_id] = (key, 'right')

        # Extract age requirement
        age_req = value_data.get('age')

        # Extract allow conditions for conditional values
        conditions = None
        if 'allow' in value_data:
            conditions = str(value_data['allow'])

        values[key] = {
            'id': key,
            'left': {
                'id': left_id,
                'name': utils.prettify_id(left_id)
            },
            'right': {
                'id': right_id,
                'name': utils.prettify_id(right_id)
            },
            'age_requirement': age_req,
            'conditions': conditions
        }

    print(f"  Found {len(values)} value pairs")
    return values


def extract_ages() -> dict:
    """Extract age definitions."""
    print("Extracting ages...")

    ages_file = COMMON_PATH / "age" / "00_default.txt"
    data = parse_file(ages_file)

    ages = {}

    for key, age_data in data.items():
        if not isinstance(age_data, dict):
            continue
        if not key.startswith('age_'):
            continue

        year = age_data.get('year', 0)

        ages[key] = {
            'id': key,
            'name': utils.prettify_id(key),
            'year': year
        }

    # Sort by year
    ages = dict(sorted(ages.items(), key=lambda x: x[1]['year']))

    print(f"  Found {len(ages)} ages")
    return ages


def extract_governments() -> dict:
    """Extract government type definitions."""
    print("Extracting government types...")

    gov_file = COMMON_PATH / "government_types" / "00_default.txt"
    data = parse_file(gov_file)

    governments = {}

    for key, gov_data in data.items():
        if not isinstance(gov_data, dict):
            continue

        governments[key] = {
            'id': key,
            'name': utils.prettify_id(key),
            'power_type': gov_data.get('government_power')
        }

    print(f"  Found {len(governments)} government types")
    return governments


def extract_religions() -> dict:
    """Extract religion definitions."""
    print("Extracting religions...")

    religions_path = COMMON_PATH / "religions"
    religions = {}

    for filepath in religions_path.glob("*.txt"):
        try:
            data = parse_file(filepath)

            for key, rel_data in data.items():
                if not isinstance(rel_data, dict):
                    continue

                group = rel_data.get('group', 'unknown')

                religions[key] = {
                    'id': key,
                    'name': utils.prettify_id(key),
                    'group': group
                }
        except Exception as e:
            print(f"  Warning: Failed to parse {filepath}: {e}")

    print(f"  Found {len(religions)} religions")
    return religions


def extract_countries() -> dict:
    """Extract country definitions."""
    print("Extracting countries...")

    countries_path = SETUP_PATH / "countries"
    countries = {}

    for filepath in countries_path.glob("*.txt"):
        try:
            # First pass: extract tag -> name from comments
            # Format: TAG = { #Name
            tag_names = {}
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    # Match patterns like "YEM = { #Yemen" or "YEM = {#Yemen"
                    match = re.match(r'^([A-Z]{3})\s*=\s*\{?\s*#(.+)$', line.strip())
                    if match:
                        tag = match.group(1)
                        name = match.group(2).strip()
                        tag_names[tag] = name

            # Second pass: parse the file for actual data
            data = parse_file(filepath)

            for tag, country_data in data.items():
                if not isinstance(country_data, dict):
                    continue
                if len(tag) != 3:  # Country tags are 3 letters
                    continue

                # Use extracted name from comment, fallback to prettified tag
                name = tag_names.get(tag, utils.prettify_id(tag))

                countries[tag] = {
                    'tag': tag,
                    'name': name,
                    'religion': country_data.get('religion_definition'),
                    'culture': country_data.get('culture_definition')
                }
        except Exception as e:
            print(f"  Warning: Failed to parse {filepath}: {e}")

    print(f"  Found {len(countries)} countries")
    return countries


def extract_estates() -> dict:
    """Extract estate definitions."""
    print("Extracting estates...")

    estates_file = COMMON_PATH / "estates" / "00_default.txt"
    data = parse_file(estates_file)

    estates = {}

    for key, estate_data in data.items():
        if not isinstance(estate_data, dict):
            continue
        # Accept any key that looks like an estate definition
        if '_estate' not in key and key != 'crown_estate':
            continue

        # Prettify the name - remove '_estate' suffix for display
        display_name = key.replace('_estate', '')
        if display_name == 'crown':
            display_name = 'Crown'

        estates[key] = {
            'id': key,
            'name': utils.prettify_id(display_name)
        }

    print(f"  Found {len(estates)} estates")
    return estates


def extract_advances_definitions():
    """Extract advance definitions and store their requirements in utils.ADVANCES.

    This must be called before extracting movers so that items requiring advances
    can have the advance's requirements merged in.
    """
    print("Extracting advance definitions...")

    advances_path = COMMON_PATH / "advances"
    if not advances_path.exists():
        print("  No advances directory found")
        return

    count = 0
    for filepath in sorted(advances_path.glob("*.txt")):
        try:
            data = parse_file(filepath)

            for advance_id, advance_data in data.items():
                if not isinstance(advance_data, dict):
                    continue

                # Extract requirements from potential block
                requirements = {}
                if 'potential' in advance_data and isinstance(advance_data['potential'], dict):
                    _extract_advance_potential(advance_data['potential'], requirements)

                # Get age requirement
                age = advance_data.get('age')

                # Store in utils.ADVANCES
                utils.ADVANCES[advance_id] = {
                    'requirements': requirements,
                    'age': age
                }
                count += 1

        except Exception as e:
            print(f"  Warning: Failed to parse {filepath}: {e}")

    print(f"  Found {count} advance definitions")


def _extract_advance_potential(potential: dict, requirements: dict):
    """Extract requirements from an advance's potential block.

    Advances use slightly different syntax like:
    - culture = { has_culture_group = culture_group:confucian_group }
    - religion = religion:sanjiao
    """
    # Direct religion reference
    if 'religion' in potential:
        rel = potential['religion']
        if isinstance(rel, str):
            # Format: religion:sanjiao
            if ':' in rel:
                rel = rel.split(':')[1]
            requirements.setdefault('religion', []).append(rel)

    # Culture with has_culture_group
    if 'culture' in potential:
        culture_block = potential['culture']
        if isinstance(culture_block, dict):
            if 'has_culture_group' in culture_block:
                cg = culture_block['has_culture_group']
                if isinstance(cg, str) and ':' in cg:
                    cg = cg.split(':')[1]
                requirements.setdefault('culture_group', []).append(cg)

    # Direct culture group
    if 'has_culture_group' in potential:
        cg = potential['has_culture_group']
        if isinstance(cg, str) and ':' in cg:
            cg = cg.split(':')[1]
        requirements.setdefault('culture_group', []).append(cg)

    # Country tag
    if 'tag' in potential:
        tag = potential['tag']
        if isinstance(tag, str):
            requirements.setdefault('country', []).append(tag)

    if 'has_or_had_tag' in potential:
        tag = potential['has_or_had_tag']
        if isinstance(tag, str):
            requirements.setdefault('country', []).append(tag)

    # OR blocks - recurse
    if 'OR' in potential and isinstance(potential['OR'], dict):
        requirements['has_or_condition'] = True
        _extract_advance_potential(potential['OR'], requirements)

    # Use standard extraction too for other fields
    utils._extract_trigger_requirements(potential, requirements)


def extract_value_movers(category: str, path: Path, extractor_fn) -> list:
    """Generic extractor for items that affect values."""
    print(f"Extracting {category}...")

    items = []

    for filepath in sorted(path.glob("*.txt")):
        try:
            data = parse_file(filepath)
            extracted = extractor_fn(data, filepath.stem)
            items.extend(extracted)
        except Exception as e:
            print(f"  Warning: Failed to parse {filepath}: {e}")

    print(f"  Found {len(items)} {category} with value effects")
    return items


def extract_reforms_from_data(data: dict, source: str) -> list:
    """Extract government reforms from parsed data."""
    items = []

    for key, reform_data in data.items():
        if not isinstance(reform_data, dict):
            continue

        # Get modifier block
        modifiers = reform_data.get('country_modifier', {})
        if not isinstance(modifiers, dict):
            continue

        # Extract value effects
        effects = utils.extract_value_effects(modifiers)

        if not effects:
            continue

        # Extract requirements
        requirements = utils.extract_requirements(reform_data)
        requirements = utils.resolve_advance_requirements(requirements)

        items.append({
            'id': key,
            'name': utils.prettify_id(key),
            'type': 'reform',
            'source': source,
            'value_effects': effects,
            'requirements': requirements,
            'is_major': reform_data.get('major', False),
            'is_unique': reform_data.get('unique', False)
        })

    return items


def extract_laws_from_data(data: dict, source: str) -> list:
    """Extract laws from parsed data."""
    items = []

    for law_key, law_data in data.items():
        if not isinstance(law_data, dict):
            continue

        law_category = law_data.get('law_category', source)

        # Laws contain multiple policies
        for policy_key, policy_data in law_data.items():
            if not isinstance(policy_data, dict):
                continue
            if policy_key in ['law_category', 'potential', 'allow']:
                continue

            # Get modifier block
            modifiers = policy_data.get('country_modifier', {})
            if not isinstance(modifiers, dict):
                continue

            # Extract value effects
            effects = utils.extract_value_effects(modifiers)

            if not effects:
                continue

            # Extract requirements
            requirements = utils.extract_requirements(policy_data)
            # Add law-level requirements
            if 'potential' in law_data:
                utils._extract_trigger_requirements(law_data.get('potential', {}), requirements)
            if 'allow' in law_data:
                utils._extract_trigger_requirements(law_data.get('allow', {}), requirements)

            # Get estate preferences
            estate_prefs = policy_data.get('estate_preferences', [])
            if isinstance(estate_prefs, dict):
                estate_prefs = list(estate_prefs.keys())

            # Resolve advance requirements
            requirements = utils.resolve_advance_requirements(requirements)

            items.append({
                'id': policy_key,
                'name': utils.prettify_id(policy_key),
                'type': 'law',
                'source': source,
                'category': law_key,
                'category_name': utils.prettify_id(law_key),
                'value_effects': effects,
                'requirements': requirements,
                'estate_preferences': estate_prefs
            })

    return items


def extract_privileges_from_data(data: dict, source: str) -> list:
    """Extract estate privileges from parsed data."""
    items = []

    for key, priv_data in data.items():
        if not isinstance(priv_data, dict):
            continue

        # Get modifier block
        modifiers = priv_data.get('country_modifier', {})
        if not isinstance(modifiers, dict):
            continue

        # Extract value effects
        effects = utils.extract_value_effects(modifiers)

        if not effects:
            continue

        # Extract requirements
        requirements = utils.extract_requirements(priv_data)
        requirements = utils.resolve_advance_requirements(requirements)

        # Get estate
        estate = priv_data.get('estate', source.replace('_estate', '') + '_estate')

        items.append({
            'id': key,
            'name': utils.prettify_id(key),
            'type': 'privilege',
            'source': source,
            'estate': estate,
            'estate_name': utils.prettify_id(estate.replace('_estate', '')),
            'value_effects': effects,
            'requirements': requirements
        })

    return items


def extract_traits_from_data(data: dict, source: str) -> list:
    """Extract traits from parsed data."""
    items = []

    for key, trait_data in data.items():
        if not isinstance(trait_data, dict):
            continue

        # Get modifier block - traits use "modifier" key
        modifiers = trait_data.get('modifier', {})
        if not isinstance(modifiers, dict):
            continue

        # Extract value effects
        effects = utils.extract_value_effects(modifiers)

        if not effects:
            continue

        # Extract requirements
        requirements = utils.extract_requirements(trait_data)
        requirements = utils.resolve_advance_requirements(requirements)

        # Add trait category if present
        category = trait_data.get('category')

        items.append({
            'id': key,
            'name': utils.prettify_id(key),
            'type': 'trait',
            'source': source,
            'category': category,
            'value_effects': effects,
            'requirements': requirements
        })

    return items


def extract_buildings_from_data(data: dict, source: str) -> list:
    """Extract buildings from parsed data."""
    items = []

    for key, building_data in data.items():
        if not isinstance(building_data, dict):
            continue

        # Get modifier block - buildings can use various keys
        all_effects = []
        modifier_keys = [
            'country_modifier', 'capital_country_modifier', 'province_modifier',
            'modifier', 'location_modifier', 'area_modifier'
        ]

        for mod_key in modifier_keys:
            modifiers = building_data.get(mod_key, {})
            if isinstance(modifiers, dict):
                effects = utils.extract_value_effects(modifiers)
                all_effects.extend(effects)

        if not all_effects:
            continue

        # Extract requirements
        requirements = utils.extract_requirements(building_data)
        requirements = utils.resolve_advance_requirements(requirements)

        # Add building category if present
        category = building_data.get('category')

        items.append({
            'id': key,
            'name': utils.prettify_id(key),
            'type': 'building',
            'source': source,
            'category': category,
            'value_effects': all_effects,
            'requirements': requirements
        })

    return items


def extract_religious_aspects_from_data(data: dict, source: str) -> list:
    """Extract religious aspects from parsed data."""
    items = []

    for key, aspect_data in data.items():
        if not isinstance(aspect_data, dict):
            continue

        # Get modifier block - religious aspects use "modifier" key
        modifiers = aspect_data.get('modifier', {})
        if not isinstance(modifiers, dict):
            continue

        # Extract value effects
        effects = utils.extract_value_effects(modifiers)

        if not effects:
            continue

        # Extract requirements
        requirements = utils.extract_requirements(aspect_data)

        # Get religions this aspect applies to
        religions = []
        for k, v in aspect_data.items():
            if k == 'religion' and isinstance(v, str):
                religions.append(v)
            elif k == 'religion' and isinstance(v, list):
                religions.extend(v)

        if religions:
            requirements['religion'] = religions

        requirements = utils.resolve_advance_requirements(requirements)

        items.append({
            'id': key,
            'name': utils.prettify_id(key),
            'type': 'religious_aspect',
            'source': source,
            'value_effects': effects,
            'requirements': requirements
        })

    return items


def extract_parliament_issues_from_data(data: dict, source: str) -> list:
    """Extract parliament issues from parsed data."""
    items = []

    for key, issue_data in data.items():
        if not isinstance(issue_data, dict):
            continue

        # Get modifier block - parliament issues use "modifier_when_in_debate"
        modifiers = issue_data.get('modifier_when_in_debate', {})
        if not isinstance(modifiers, dict):
            modifiers = issue_data.get('modifier', {})
        if not isinstance(modifiers, dict):
            continue

        # Extract value effects
        effects = utils.extract_value_effects(modifiers)

        if not effects:
            continue

        # Extract requirements
        requirements = utils.extract_requirements(issue_data)

        # Get estate if present
        estate = issue_data.get('estate')
        if estate:
            requirements['estate'] = [estate] if isinstance(estate, str) else estate

        requirements = utils.resolve_advance_requirements(requirements)

        items.append({
            'id': key,
            'name': utils.prettify_id(key),
            'type': 'parliament_issue',
            'source': source,
            'estate': estate,
            'value_effects': effects,
            'requirements': requirements
        })

    return items


def extract_auto_modifiers_from_data(data: dict, source: str) -> list:
    """Extract auto modifiers - these have monthly_towards_* at top level."""
    items = []

    for key, item_data in data.items():
        if not isinstance(item_data, dict):
            continue

        # Auto modifiers have monthly_towards_* directly in the item dict
        effects = utils.extract_value_effects(item_data)

        if not effects:
            continue

        # Extract conditions from potential_trigger
        requirements = {}
        if 'potential_trigger' in item_data and isinstance(item_data['potential_trigger'], dict):
            utils._extract_trigger_requirements(item_data['potential_trigger'], requirements)

        requirements = utils.resolve_advance_requirements(requirements)

        items.append({
            'id': key,
            'name': utils.prettify_id(key),
            'type': 'auto_modifier',
            'source': source,
            'value_effects': effects,
            'requirements': requirements
        })

    return items


def extract_parliament_agendas_from_data(data: dict, source: str) -> list:
    """Extract parliament agendas - these use change_societal_value in on_accept."""
    items = []

    for key, item_data in data.items():
        if not isinstance(item_data, dict):
            continue

        # Parliament agendas have change_societal_value in on_accept
        on_accept = item_data.get('on_accept', {})
        if not isinstance(on_accept, dict):
            continue

        change_sv = on_accept.get('change_societal_value', {})
        if not isinstance(change_sv, dict):
            continue

        sv_type = change_sv.get('type')
        sv_value = change_sv.get('value')

        if not sv_type or not sv_value:
            continue

        # Parse the value type and direction
        # Format: societal_value_minor_move_to_left
        direction = 'left' if 'to_left' in str(sv_value) else 'right'

        # Determine strength from value name
        strength = None
        strength_raw = sv_value
        if 'tiny' in str(sv_value):
            strength = 0.02
        elif 'minor' in str(sv_value):
            strength = 0.05
        elif 'large' in str(sv_value):
            strength = 0.20
        else:
            strength = 0.10  # default "move"

        # The sv_type format is like "centralization_vs_decentralization"
        value_pair = sv_type

        # Determine target side
        if value_pair and '_vs_' in value_pair:
            parts = value_pair.split('_vs_')
            target = parts[0] if direction == 'left' else ('_'.join(parts[1:]) if len(parts) > 1 else parts[0])
        else:
            target = value_pair

        effects = [{
            'value_pair': value_pair,
            'direction': direction,
            'target': target,
            'strength': strength,
            'strength_raw': strength_raw
        }]

        # Extract requirements
        requirements = {}
        estate = item_data.get('estate')
        if estate:
            requirements['estate'] = [estate] if isinstance(estate, str) else estate

        if 'potential' in item_data and isinstance(item_data['potential'], dict):
            utils._extract_trigger_requirements(item_data['potential'], requirements)

        requirements = utils.resolve_advance_requirements(requirements)

        items.append({
            'id': key,
            'name': utils.prettify_id(key),
            'type': 'parliament_agenda',
            'source': source,
            'estate': estate,
            'value_effects': effects,
            'requirements': requirements,
            'is_one_time': True  # These are one-time effects, not monthly
        })

    return items


def extract_events_from_data(data: dict, source: str) -> list:
    """Extract events that have change_societal_value effects.

    Events have multiple options (player choices), each option can have different
    value changes. We extract each option with value changes as a separate mover.
    """
    items = []

    for event_id, event_data in data.items():
        if not isinstance(event_data, dict):
            continue

        # Skip namespace declarations
        if event_id == 'namespace':
            continue

        # Extract trigger requirements
        base_requirements = {}
        if 'trigger' in event_data and isinstance(event_data['trigger'], dict):
            _extract_event_trigger(event_data['trigger'], base_requirements)

        # Check for dynamic_historical_event tag restrictions
        if 'dynamic_historical_event' in event_data:
            dhe = event_data['dynamic_historical_event']
            if isinstance(dhe, dict):
                if 'tag' in dhe:
                    tag = dhe['tag']
                    if isinstance(tag, str):
                        base_requirements.setdefault('country', []).append(tag)
                    elif isinstance(tag, list):
                        base_requirements.setdefault('country', []).extend(tag)

        # Extract from each option
        option_num = 0
        for key, value in event_data.items():
            if key == 'option' and isinstance(value, dict):
                option_num += 1
                effects = _extract_event_option_value_effects(value)
                if effects:
                    option_name = value.get('name', f'Option {option_num}')
                    # Clean up option name (remove event prefix)
                    if isinstance(option_name, str) and '.' in option_name:
                        parts = option_name.split('.')
                        option_name = parts[-1] if parts[-1] else option_name

                    requirements = base_requirements.copy()
                    requirements = utils.resolve_advance_requirements(requirements)

                    items.append({
                        'id': f"{event_id}_{option_name}",
                        'name': f"{utils.prettify_id(event_id)} ({option_name})",
                        'type': 'event_choice',
                        'source': source,
                        'event_id': event_id,
                        'option': option_name,
                        'value_effects': effects,
                        'requirements': requirements,
                        'is_one_time': True
                    })

    return items


def _extract_event_trigger(trigger: dict, requirements: dict):
    """Extract requirements from event trigger block."""
    # Use standard extraction
    utils._extract_trigger_requirements(trigger, requirements)

    # Also check for societal_value conditions that indicate what value is affected
    for key, value in trigger.items():
        if key.startswith('societal_value:'):
            # This indicates the event relates to a specific value pair
            value_pair = key[len('societal_value:'):]
            requirements.setdefault('related_value', []).append(value_pair)


def _extract_event_option_value_effects(option: dict) -> list:
    """Extract value effects from an event option."""
    effects = []

    def find_value_changes(d: dict):
        """Recursively find change_societal_value blocks."""
        if not isinstance(d, dict):
            return

        if 'change_societal_value' in d:
            csv = d['change_societal_value']
            if isinstance(csv, dict):
                process_csv(csv)
            elif isinstance(csv, list):
                for item in csv:
                    if isinstance(item, dict):
                        process_csv(item)

        # Recurse into nested blocks
        for key, value in d.items():
            if isinstance(value, dict):
                find_value_changes(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        find_value_changes(item)

    def process_csv(csv: dict):
        sv_type = csv.get('type')
        sv_value = csv.get('value')

        if not sv_type or not sv_value:
            return

        direction = 'left' if 'to_left' in str(sv_value) else 'right'

        # Determine strength from value name
        strength = None
        if 'tiny' in str(sv_value):
            strength = 0.02
        elif 'minor' in str(sv_value):
            strength = 0.05
        elif 'large' in str(sv_value):
            strength = 0.20
        elif 'huge' in str(sv_value):
            strength = 0.50
        else:
            strength = 0.10

        value_pair = sv_type
        if value_pair and '_vs_' in value_pair:
            parts = value_pair.split('_vs_')
            target = parts[0] if direction == 'left' else ('_'.join(parts[1:]) if len(parts) > 1 else parts[0])
        else:
            target = value_pair

        effects.append({
            'value_pair': value_pair,
            'direction': direction,
            'target': target,
            'strength': strength,
            'strength_raw': sv_value
        })

    find_value_changes(option)
    return effects


def extract_generic_from_data(data: dict, source: str, item_type: str) -> list:
    """Generic extractor for any item type with modifiers."""
    items = []

    def find_modifiers(d: dict, path: str = "") -> list:
        """Recursively find all modifier blocks with value effects."""
        results = []

        if not isinstance(d, dict):
            return results

        # Check all common modifier keys
        modifier_keys = [
            'country_modifier', 'modifier', 'province_modifier', 'effect',
            'capital_country_modifier', 'modifier_when_in_debate', 'high_power',
            'low_power', 'satisfaction', 'location_modifier', 'area_modifier'
        ]

        for mod_key in modifier_keys:
            if mod_key in d and isinstance(d[mod_key], dict):
                effects = utils.extract_value_effects(d[mod_key])
                if effects:
                    results.append((path, d, effects))

        # Recurse into nested dicts
        for key, value in d.items():
            if isinstance(value, dict):
                nested_path = f"{path}.{key}" if path else key
                results.extend(find_modifiers(value, nested_path))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        nested_path = f"{path}.{key}[{i}]" if path else f"{key}[{i}]"
                        results.extend(find_modifiers(item, nested_path))

        return results

    for key, item_data in data.items():
        if not isinstance(item_data, dict):
            continue

        # Find all modifier blocks with value effects
        found = find_modifiers(item_data, key)

        for path, context, effects in found:
            # Use the top-level key as the item ID
            item_id = path.split('.')[0] if '.' in path else path

            # Extract requirements from context
            requirements = utils.extract_requirements(context)
            requirements = utils.resolve_advance_requirements(requirements)

            items.append({
                'id': item_id,
                'name': utils.prettify_id(item_id),
                'type': item_type,
                'source': source,
                'value_effects': effects,
                'requirements': requirements
            })

    # Deduplicate by id
    seen = set()
    unique_items = []
    for item in items:
        if item['id'] not in seen:
            seen.add(item['id'])
            unique_items.append(item)

    return unique_items


def main():
    """Main extraction pipeline."""
    print("=" * 60)
    print("EU5 Values Viewer - Data Extraction")
    print("=" * 60)
    print()

    # Ensure output directory exists
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract value definitions (needed first for VALUE_SIDES lookup)
    values = extract_values()

    # Step 2: Extract other definitions
    ages = extract_ages()
    governments = extract_governments()
    religions = extract_religions()
    countries = extract_countries()
    estates = extract_estates()

    # Step 2.5: Extract advance definitions (needed before movers for requirement resolution)
    extract_advances_definitions()

    # Step 3: Extract value movers from all sources
    all_movers = []

    # Government Reforms
    reforms = extract_value_movers(
        "government reforms",
        COMMON_PATH / "government_reforms",
        extract_reforms_from_data
    )
    all_movers.extend(reforms)

    # Laws
    laws = extract_value_movers(
        "laws",
        COMMON_PATH / "laws",
        extract_laws_from_data
    )
    all_movers.extend(laws)

    # Estate Privileges
    privileges = extract_value_movers(
        "estate privileges",
        COMMON_PATH / "estate_privileges",
        extract_privileges_from_data
    )
    all_movers.extend(privileges)

    # Traits
    traits = extract_value_movers(
        "traits",
        COMMON_PATH / "traits",
        extract_traits_from_data
    )
    all_movers.extend(traits)

    # Buildings
    buildings = extract_value_movers(
        "buildings",
        COMMON_PATH / "building_types",
        extract_buildings_from_data
    )
    all_movers.extend(buildings)

    # Religious Aspects
    religious = extract_value_movers(
        "religious aspects",
        COMMON_PATH / "religious_aspects",
        extract_religious_aspects_from_data
    )
    all_movers.extend(religious)

    # Parliament Issues
    parliament = extract_value_movers(
        "parliament issues",
        COMMON_PATH / "parliament_issues",
        extract_parliament_issues_from_data
    )
    all_movers.extend(parliament)

    # Auto Modifiers (specialized extractor - monthly_towards at top level)
    print("Extracting auto modifiers...")
    auto_mod_file = COMMON_PATH / "auto_modifiers" / "country.txt"
    if auto_mod_file.exists():
        try:
            data = parse_file(auto_mod_file)
            auto_mods = extract_auto_modifiers_from_data(data, "auto_modifiers")
            all_movers.extend(auto_mods)
            print(f"  Found {len(auto_mods)} auto modifiers with value effects")
        except Exception as e:
            print(f"  Warning: Failed to parse auto modifiers: {e}")

    # Parliament Agendas (one-time value changes)
    parliament_agendas = extract_value_movers(
        "parliament agendas",
        COMMON_PATH / "parliament_agendas",
        extract_parliament_agendas_from_data
    )
    all_movers.extend(parliament_agendas)

    # Employment Systems
    print("Extracting employment systems...")
    emp_file = COMMON_PATH / "employment_systems" / "00_default.txt"
    if emp_file.exists():
        try:
            data = parse_file(emp_file)
            emp_items = extract_generic_from_data(data, "employment_systems", "employment_system")
            all_movers.extend(emp_items)
            print(f"  Found {len(emp_items)} employment systems with value effects")
        except Exception as e:
            print(f"  Warning: Failed to parse employment systems: {e}")

    # Cabinet Actions
    cabinet = extract_value_movers(
        "cabinet actions",
        COMMON_PATH / "cabinet_actions",
        lambda d, s: extract_generic_from_data(d, s, "cabinet_action")
    )
    all_movers.extend(cabinet)

    # Regencies
    regencies = extract_value_movers(
        "regencies",
        COMMON_PATH / "regencies",
        lambda d, s: extract_generic_from_data(d, s, "regency")
    )
    all_movers.extend(regencies)

    # Disasters
    disasters = extract_value_movers(
        "disasters",
        COMMON_PATH / "disasters",
        lambda d, s: extract_generic_from_data(d, s, "disaster")
    )
    all_movers.extend(disasters)

    # Religious Schools
    if (COMMON_PATH / "religious_schools").exists():
        r_schools = extract_value_movers(
            "religious schools",
            COMMON_PATH / "religious_schools",
            lambda d, s: extract_generic_from_data(d, s, "religious_school")
        )
        all_movers.extend(r_schools)

    # Estates base (00_default.txt)
    print("Extracting estates base modifiers...")
    estates_file = COMMON_PATH / "estates" / "00_default.txt"
    if estates_file.exists():
        try:
            data = parse_file(estates_file)
            estate_mods = extract_generic_from_data(data, "estates", "estate_modifier")
            all_movers.extend(estate_mods)
            print(f"  Found {len(estate_mods)} estate modifiers with value effects")
        except Exception as e:
            print(f"  Warning: Failed to parse estates: {e}")

    # International Organizations
    if (COMMON_PATH / "international_organizations").exists():
        io_items = extract_value_movers(
            "international organizations",
            COMMON_PATH / "international_organizations",
            lambda d, s: extract_generic_from_data(d, s, "international_org")
        )
        all_movers.extend(io_items)

    # Generic Actions
    if (COMMON_PATH / "generic_actions").exists():
        generic = extract_value_movers(
            "generic actions",
            COMMON_PATH / "generic_actions",
            lambda d, s: extract_generic_from_data(d, s, "generic_action")
        )
        all_movers.extend(generic)

    # Missions (informational only - these are transient)
    if (COMMON_PATH / "missions").exists():
        missions = extract_value_movers(
            "missions",
            COMMON_PATH / "missions",
            lambda d, s: extract_generic_from_data(d, s, "mission")
        )
        all_movers.extend(missions)

    # Advances (country specific)
    if (COMMON_PATH / "advances").exists():
        advances = extract_value_movers(
            "advances",
            COMMON_PATH / "advances",
            lambda d, s: extract_generic_from_data(d, s, "advance")
        )
        all_movers.extend(advances)

    # Subject Types
    if (COMMON_PATH / "subject_types").exists():
        subjects = extract_value_movers(
            "subject types",
            COMMON_PATH / "subject_types",
            lambda d, s: extract_generic_from_data(d, s, "subject_type")
        )
        all_movers.extend(subjects)

    # Events (one-time value changes from player choices)
    if EVENTS_PATH.exists():
        print("Extracting events...")
        event_count = 0
        for subdir in ['', 'DHE', 'disaster', 'economy', 'estates', 'government',
                       'religion', 'situations', 'culture', 'character', 'missionevents',
                       'exploration']:
            event_dir = EVENTS_PATH / subdir if subdir else EVENTS_PATH
            if event_dir.exists():
                for filepath in sorted(event_dir.glob("*.txt")):
                    try:
                        data = parse_file(filepath)
                        events = extract_events_from_data(data, filepath.stem)
                        if events:
                            all_movers.extend(events)
                            event_count += len(events)
                    except Exception as e:
                        # Silently skip parse errors for events (there are many)
                        pass
        print(f"  Found {event_count} event choices with value effects")

    # Write output files
    print()
    print("=" * 60)
    print("Writing output files...")
    print("=" * 60)

    def write_json(filename: str, data: Any):
        filepath = OUTPUT_PATH / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Wrote {filepath}")

    write_json("values.json", values)
    write_json("ages.json", ages)
    write_json("governments.json", governments)
    write_json("religions.json", religions)
    write_json("countries.json", countries)
    write_json("estates.json", estates)
    write_json("movers.json", all_movers)

    # Summary
    print()
    print("=" * 60)
    print("Extraction Summary")
    print("=" * 60)
    print(f"  Value pairs:        {len(values)}")
    print(f"  Ages:               {len(ages)}")
    print(f"  Government types:   {len(governments)}")
    print(f"  Religions:          {len(religions)}")
    print(f"  Countries:          {len(countries)}")
    print(f"  Estates:            {len(estates)}")
    print(f"  Value movers:       {len(all_movers)}")

    # Count by type
    by_type = {}
    for mover in all_movers:
        t = mover['type']
        by_type[t] = by_type.get(t, 0) + 1

    print()
    print("  Movers by type:")
    for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    {t}: {count}")

    print()
    print("Done!")


if __name__ == "__main__":
    main()
