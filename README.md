# EU5 Values Viewer

A web-based tool to explore how to move societal values in Europa Universalis V.

## Features

- View all 16 societal value pairs (Centralization vs Decentralization, etc.)
- See what government reforms, laws, estate privileges, traits, buildings, and more affect each value
- Filter by Age, Government Type, and Religion
- Search within results
- Items that don't match your filters are grayed out (but still visible)

## Usage

### Option 1: GitHub Pages
Visit: [Your GitHub Pages URL]

### Option 2: Local
Since this app loads JSON files via fetch, you need to serve it from a web server:

```bash
# Using Python 3
cd values-viewer
python3 -m http.server 8000

# Then open http://localhost:8000
```

## Data

The `data/` folder contains extracted game data:
- `values.json` - 16 societal value pair definitions
- `ages.json` - 6 game ages
- `governments.json` - 5 government types
- `religions.json` - 293 religions
- `movers.json` - 762 items that affect values

## Item Types

| Type | Count | Description |
|------|-------|-------------|
| Laws | 329 | Policy choices in law categories |
| Reforms | 174 | Government reforms |
| Privileges | 131 | Estate privileges |
| Religious Aspects | 34 | Religion customizations |
| Traits | 24 | Ruler personality traits |
| Buildings | 22 | Capital and special buildings |
| Parliament Issues | 19 | Debate topics |
| Estate Modifiers | 7 | Base estate power effects |
| Cabinet Actions | 6 | Special cabinet decisions |
| Regencies | 5 | Regency types |
| Employment Systems | 4 | Work organization types |
| Religious Schools | 4 | School variations |
| Disasters | 3 | Active disaster effects |

## Credits

Data extracted from Europa Universalis V by Paradox Interactive.
This is a fan-made tool and is not affiliated with Paradox Interactive.
