#!/usr/bin/env python3
"""
Attorney Database Scraper - Main Runner
=======================================
Scrapes attorney data from state bar directories.

Usage:
    python run_scrapers.py                  # Run all scrapers
    python run_scrapers.py --state CA       # Run specific state
    python run_scrapers.py --stats          # Show database stats
    python run_scrapers.py --export         # Export to CSV
    python run_scrapers.py --search "Smith" # Search attorneys

Dependencies:
    pip install requests beautifulsoup4
"""

import argparse
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_database, get_stats, export_to_csv, search_attorneys


# Available scrapers
SCRAPERS = {
    'CA': ('California', 'scrapers.california_bar', 'CaliforniaBarScraper'),
    'NY': ('New York', 'scrapers.new_york_bar', 'NewYorkBarScraper'),
    'TX': ('Texas', 'scrapers.texas_bar', 'TexasBarScraper'),
    'FL': ('Florida', 'scrapers.florida_bar', 'FloridaBarScraper'),
    'IL': ('Illinois', 'scrapers.illinois_bar', 'IllinoisBarScraper'),
}


def run_scraper(state_code, db_path="attorneys.db"):
    """Run a specific state scraper."""
    if state_code not in SCRAPERS:
        print(f"❌ Unknown state: {state_code}")
        print(f"   Available states: {', '.join(SCRAPERS.keys())}")
        return False
    
    state_name, module_name, class_name = SCRAPERS[state_code]
    
    try:
        # Dynamic import
        module = __import__(module_name, fromlist=[class_name])
        scraper_class = getattr(module, class_name)
        
        # Run scraper
        scraper = scraper_class(db_path=db_path)
        scraper.run()
        return True
        
    except ImportError as e:
        print(f"❌ Could not import scraper for {state_name}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error running {state_name} scraper: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_scrapers(db_path="attorneys.db"):
    """Run all available scrapers."""
    print("\n" + "="*60)
    print("  Attorney Database Scraper")
    print("  Running all state scrapers...")
    print("="*60)
    
    results = {}
    
    for state_code in SCRAPERS:
        success = run_scraper(state_code, db_path)
        results[state_code] = success
    
    # Summary
    print("\n" + "="*60)
    print("  SCRAPING SUMMARY")
    print("="*60)
    for state, success in results.items():
        status = "✅ Complete" if success else "❌ Failed"
        print(f"  {state}: {status}")
    
    print("="*60 + "\n")
    
    # Show final stats
    show_stats(db_path)


def show_stats(db_path="attorneys.db"):
    """Display database statistics."""
    stats = get_stats(db_path)
    
    print("\n" + "="*60)
    print("  DATABASE STATISTICS")
    print("="*60)
    
    print(f"\n  Total Attorneys: {stats['total_attorneys']:,}")
    
    print(f"\n  By State:")
    for state, count in stats['by_state'].items():
        print(f"    {state}: {count:,}")
    
    print(f"\n  By Status:")
    for status, count in stats['by_status'].items():
        print(f"    {status}: {count:,}")
    
    print(f"\n  Top Practice Areas:")
    for area, count in list(stats['top_practice_areas'].items())[:10]:
        print(f"    {area}: {count:,}")
    
    print(f"\n  Top Firms:")
    for firm, count in list(stats['top_firms'].items())[:10]:
        print(f"    {firm}: {count:,}")
    
    print("="*60 + "\n")


def do_search(query, db_path="attorneys.db", **filters):
    """Search for attorneys."""
    filters['name'] = query
    filters['limit'] = filters.get('limit', 50)
    
    results = search_attorneys(db_path, **filters)
    
    print(f"\n  Found {len(results)} attorneys matching '{query}':\n")
    
    for i, attorney in enumerate(results[:20], 1):
        print(f"  {i}. {attorney['full_name']}")
        print(f"     Bar #: {attorney['bar_number'] or 'N/A'} | State: {attorney['state']}")
        print(f"     Status: {attorney['status'] or 'N/A'} | City: {attorney['city'] or 'N/A'}")
        if attorney['firm_name']:
            print(f"     Firm: {attorney['firm_name']}")
        print()
    
    if len(results) > 20:
        print(f"  ... and {len(results) - 20} more results")


def main():
    parser = argparse.ArgumentParser(
        description='Attorney Database Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_scrapers.py                    # Run all scrapers
  python run_scrapers.py --state CA         # Run California only
  python run_scrapers.py --state CA,NY,TX   # Run multiple states
  python run_scrapers.py --stats            # Show database stats
  python run_scrapers.py --export           # Export all to CSV
  python run_scrapers.py --search "Johnson" # Search by name
  python run_scrapers.py --search "Jones" --state FL  # Search in Florida
        """
    )
    
    parser.add_argument('--state', '-s', 
                       help='State code(s) to scrape (comma-separated: CA,NY,TX)')
    parser.add_argument('--stats', action='store_true',
                       help='Show database statistics')
    parser.add_argument('--export', '-e', nargs='?', const='attorneys_export.csv',
                       help='Export to CSV file')
    parser.add_argument('--search', '-q',
                       help='Search for attorneys by name')
    parser.add_argument('--practice-area', '-p',
                       help='Filter by practice area')
    parser.add_argument('--city', '-c',
                       help='Filter by city')
    parser.add_argument('--db', default='attorneys.db',
                       help='Database file path')
    parser.add_argument('--init', action='store_true',
                       help='Initialize database only')
    
    args = parser.parse_args()
    
    # Initialize database
    if args.init or not os.path.exists(args.db):
        init_database(args.db)
        if args.init:
            print("✅ Database initialized")
            return
    
    # Show stats
    if args.stats:
        show_stats(args.db)
        return
    
    # Export to CSV
    if args.export:
        filters = {}
        if args.state:
            filters['state'] = args.state.split(',')[0]
        if args.practice_area:
            filters['practice_area'] = args.practice_area
        if args.city:
            filters['city'] = args.city
        
        export_to_csv(args.db, args.export, **filters)
        return
    
    # Search
    if args.search:
        filters = {}
        if args.state:
            filters['state'] = args.state.split(',')[0]
        if args.practice_area:
            filters['practice_area'] = args.practice_area
        if args.city:
            filters['city'] = args.city
        
        do_search(args.search, args.db, **filters)
        return
    
    # Run scrapers
    if args.state:
        states = [s.strip().upper() for s in args.state.split(',')]
        for state in states:
            run_scraper(state, args.db)
    else:
        run_all_scrapers(args.db)


if __name__ == "__main__":
    main()
