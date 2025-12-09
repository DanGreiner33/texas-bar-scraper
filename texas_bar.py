"""
Texas State Bar Scraper
=======================
Scrapes attorney data from the State Bar of Texas Member Directory.
https://www.texasbar.com/AM/Template.cfm?Section=Find_A_Lawyer

~100,000 licensed attorneys
"""

import re
from bs4 import BeautifulSoup
from base_scraper import BaseBarScraper


class TexasBarScraper(BaseBarScraper):
    
    STATE = "TX"
    STATE_NAME = "Texas"
    BASE_URL = "https://www.texasbar.com"
    SEARCH_URL = "https://www.texasbar.com/AM/Template.cfm?Section=Find_A_Lawyer"
    API_URL = "https://www.texasbar.com/AM/CustomSource/MemberDirectory/Search.cfm"
    
    def scrape(self):
        """Scrape Texas Bar directory."""
        print(f"\n📍 Scraping {self.STATE_NAME} State Bar...")
        print(f"   Source: {self.SEARCH_URL}")
        
        # Texas bar has a searchable directory
        # Search by major cities and by last name
        
        # Major Texas cities
        cities = [
            'Houston', 'Dallas', 'Austin', 'San Antonio', 'Fort Worth',
            'El Paso', 'Arlington', 'Plano', 'Corpus Christi', 'Lubbock',
            'Irving', 'Garland', 'Frisco', 'McKinney', 'Amarillo',
            'Grand Prairie', 'Brownsville', 'Killeen', 'Pasadena', 'McAllen',
        ]
        
        for city in cities:
            print(f"\n   Searching: {city}...")
            self.search_by_city(city)
        
        # Also search by letter for comprehensive coverage
        print(f"\n   Searching by last name...")
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            self.delay(1, 2)
            self.search_by_letter(letter)
        
        print(f"\n\n✅ Texas scraping complete!")
    
    def search_by_city(self, city):
        """Search attorneys by city."""
        
        try:
            form_data = {
                'City': city,
                'State': 'TX',
                'LastName': '',
                'FirstName': '',
                'BarNumber': '',
                'PracticeArea': '',
            }
            
            response = self.post_page(self.API_URL, data=form_data)
            if not response:
                return
            
            self.parse_results(response.text, f"City: {city}")
            
        except Exception as e:
            print(f"  ❌ Error searching {city}: {e}")
            self.stats['errors'] += 1
    
    def search_by_letter(self, letter):
        """Search by last name letter."""
        
        try:
            form_data = {
                'LastName': letter,
                'FirstName': '',
                'City': '',
                'BarNumber': '',
            }
            
            response = self.post_page(self.API_URL, data=form_data)
            if not response:
                return
            
            self.parse_results(response.text, f"Letter: {letter}")
            
        except Exception as e:
            print(f"  ❌ Error searching letter {letter}: {e}")
            self.stats['errors'] += 1
    
    def parse_results(self, html, context):
        """Parse search results."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find attorney listings
        # Texas bar typically shows results in a list or table format
        
        results = soup.select('.attorney-result, .member-listing, .search-result')
        
        if not results:
            # Try table format
            table = soup.find('table', {'class': re.compile(r'result|member|attorney', re.I)})
            if table:
                results = table.find_all('tr')[1:]
        
        if not results:
            # Try any div with attorney info
            results = soup.find_all('div', {'class': re.compile(r'member|attorney|result', re.I)})
        
        count = 0
        for result in results:
            try:
                attorney = self.parse_result(result)
                if attorney:
                    self.save_attorney(attorney)
                    self.stats['found'] += 1
                    count += 1
                    
                    if count % 50 == 0:
                        self.print_progress(self.stats['found'], message=context)
                        
            except Exception as e:
                self.stats['errors'] += 1
                continue
        
        # Check for pagination
        pager = soup.find('a', text=re.compile(r'Next|»', re.I))
        if pager and pager.get('href'):
            self.delay(2, 3)
            next_url = pager['href']
            if not next_url.startswith('http'):
                next_url = self.BASE_URL + next_url
            response = self.get_page(next_url)
            if response:
                self.parse_results(response.text, context)
    
    def parse_result(self, element):
        """Parse a single result element."""
        
        # Handle both table rows and divs
        if element.name == 'tr':
            return self.parse_table_row(element)
        else:
            return self.parse_div_result(element)
    
    def parse_table_row(self, row):
        """Parse table row format."""
        cells = row.find_all('td')
        if len(cells) < 2:
            return None
        
        name = None
        bar_number = None
        city = None
        status = 'Active'
        practice_areas = []
        
        for cell in cells:
            text = self.clean_text(cell.get_text())
            link = cell.find('a')
            
            if link and not name:
                name = self.clean_text(link.get_text())
                # Check href for bar number
                href = link.get('href', '')
                match = re.search(r'BarNumber=(\d+)', href)
                if match:
                    bar_number = match.group(1)
            elif text and re.match(r'^\d{8}$', text):
                bar_number = text
            elif text and len(text) > 2:
                # Could be city or practice area
                if text.title() in ['Houston', 'Dallas', 'Austin', 'San Antonio', 'Fort Worth']:
                    city = text.title()
        
        if not name:
            return None
        
        first_name, last_name = self.parse_name(name)
        
        return {
            'bar_number': bar_number,
            'full_name': name,
            'first_name': first_name,
            'last_name': last_name,
            'status': status,
            'city': city,
            'practice_areas': practice_areas,
        }
    
    def parse_div_result(self, div):
        """Parse div-based result format."""
        
        name = None
        bar_number = None
        city = None
        firm = None
        practice_areas = []
        
        # Look for name in heading or link
        name_elem = div.find(['h2', 'h3', 'h4', 'a', 'strong'])
        if name_elem:
            name = self.clean_text(name_elem.get_text())
        
        # Look for bar number
        text = div.get_text()
        bar_match = re.search(r'Bar\s*(?:No\.?|Number|#)?\s*:?\s*(\d{8})', text, re.I)
        if bar_match:
            bar_number = bar_match.group(1)
        
        # Look for city
        city_match = re.search(r'(Houston|Dallas|Austin|San Antonio|Fort Worth|El Paso)', text, re.I)
        if city_match:
            city = city_match.group(1).title()
        
        # Look for firm
        firm_elem = div.find(text=re.compile(r'Firm|Company|Employer', re.I))
        if firm_elem:
            firm = self.clean_text(firm_elem.find_next().get_text() if firm_elem.find_next() else None)
        
        if not name:
            return None
        
        first_name, last_name = self.parse_name(name)
        
        return {
            'bar_number': bar_number,
            'full_name': name,
            'first_name': first_name,
            'last_name': last_name,
            'status': 'Active',
            'city': city,
            'firm_name': firm,
            'practice_areas': practice_areas,
        }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '..')
    from database import init_database
    
    init_database("../attorneys.db")
    
    scraper = TexasBarScraper(db_path="../attorneys.db")
    scraper.run()
