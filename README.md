# Attorney Database Scraper

Scrapes attorney data from state bar directories for recruiting research.

## States Covered (Pilot)

| State | Attorneys | Source |
|-------|-----------|--------|
| California | ~190,000 | California State Bar |
| New York | ~180,000 | NY Courts Attorney Registry |
| Texas | ~100,000 | State Bar of Texas |
| Florida | ~80,000 | The Florida Bar |
| Illinois | ~65,000 | ARDC |

**Total: ~615,000 attorneys**

## Data Collected

| Field | Description |
|-------|-------------|
| `full_name` | Attorney's full name |
| `first_name` | First name |
| `last_name` | Last name |
| `bar_number` | State bar registration number |
| `state` | State of registration |
| `status` | Active, Inactive, Suspended, etc. |
| `admission_date` | Date admitted to bar |
| `city` | City location |
| `firm_name` | Law firm name |
| `practice_areas` | Areas of practice |
| `phone` | Office phone (where available) |
| `email` | Business email (where available) |

## Installation

```bash
# Clone/download the project
cd attorney-scraper

# Install dependencies
pip install requests beautifulsoup4

# Initialize the database
python run_scrapers.py --init
```

## Usage

### Run All Scrapers
```bash
python run_scrapers.py
```

### Run Specific State
```bash
python run_scrapers.py --state CA
python run_scrapers.py --state CA,NY,TX  # Multiple states
```

### View Statistics
```bash
python run_scrapers.py --stats
```

### Search Attorneys
```bash
python run_scrapers.py --search "Smith"
python run_scrapers.py --search "Johnson" --state FL
python run_scrapers.py --search "Jones" --city "Miami"
```

### Export to CSV
```bash
python run_scrapers.py --export attorneys.csv
python run_scrapers.py --export --state CA  # Export CA only
python run_scrapers.py --export --practice-area "Corporate"
```

## Database

SQLite database (`attorneys.db`) with tables:

- `attorneys` - Main attorney records
- `practice_areas` - Attorney practice areas (many-to-many)
- `firms` - Law firm information
- `scrape_logs` - Scraping history and stats

### Query Examples

```python
from database import search_attorneys, get_connection

# Search by practice area
results = search_attorneys(practice_area="Corporate", state="CA")

# Custom SQL query
conn = get_connection()
cursor = conn.cursor()
cursor.execute("""
    SELECT a.full_name, a.firm_name, pa.practice_area
    FROM attorneys a
    JOIN practice_areas pa ON a.id = pa.attorney_id
    WHERE a.state = 'NY' AND pa.practice_area LIKE '%litigation%'
    LIMIT 100
""")
```

## Project Structure

```
attorney-scraper/
├── run_scrapers.py          # Main runner script
├── database.py              # Database models and helpers
├── attorneys.db             # SQLite database (created on first run)
├── scrapers/
│   ├── base_scraper.py      # Base class for all scrapers
│   ├── california_bar.py    # California State Bar
│   ├── new_york_bar.py      # New York Courts
│   ├── texas_bar.py         # State Bar of Texas
│   ├── florida_bar.py       # The Florida Bar
│   └── illinois_bar.py      # Illinois ARDC
└── README.md
```

## Extending to More States

To add a new state:

1. Create `scrapers/[state]_bar.py`
2. Extend `BaseBarScraper` class
3. Implement `scrape()` method
4. Add to `SCRAPERS` dict in `run_scrapers.py`

Example template:
```python
from base_scraper import BaseBarScraper

class NewStateBarScraper(BaseBarScraper):
    STATE = "XX"
    STATE_NAME = "State Name"
    BASE_URL = "https://example.com"
    
    def scrape(self):
        # Your scraping logic here
        pass
```

## Rate Limiting

The scrapers include:
- Random delays between requests (1-3 seconds)
- Retry logic for failed requests
- Progress saving every batch

Please be respectful of the bar association websites.

## Legal Notes

This tool scrapes **publicly available** data from state bar directories. The data collected is:
- Publicly searchable by anyone
- Limited to business/professional information
- Intended for legitimate recruiting purposes

**Not collected:**
- Personal cell phone numbers
- Home addresses
- Private/non-public information

## Support

For issues or to add more states, please contact the development team.
