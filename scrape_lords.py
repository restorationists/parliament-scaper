#!/usr/bin/env python3
"""
Scrape contact details for Lords using the cached list
"""

import requests
import csv
import time
import sys
import os
from urllib.parse import urljoin

class LordsContactScraper:
    def __init__(self):
        self.base_url = "https://members-api.parliament.uk/api"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-GB,en;q=0.9'
        })
    
    def get_api_data(self, endpoint, retries=3):
        """Get data from API with retries and error handling"""
        url = urljoin(self.base_url, endpoint)
        
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    print(f"Rate limited, waiting 30 seconds...")
                    time.sleep(30)
                    continue
                else:
                    print(f"API returned status {response.status_code} for {url}")
                    if attempt < retries - 1:
                        time.sleep(2)
                        continue
                    return None
                    
            except requests.RequestException as e:
                print(f"Error fetching {url} (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(3)
                else:
                    return None
    
    def extract_contact_info(self, contact_data):
        """Extract contact information from API response for Lords"""
        contact_info = {
            'parliament_email': '',
            'phone': '',
            'fax': '',
            'address_line1': '',
            'address_line2': '',
            'postcode': '',
            'website': '',
            'facebook': '',
            'twitter': ''
        }
        
        if not contact_data or 'value' not in contact_data:
            return contact_info
        
        contacts = contact_data['value']
        if not isinstance(contacts, list):
            return contact_info
        
        for contact in contacts:
            if not isinstance(contact, dict):
                continue
                
            contact_type = contact.get('type', '').lower()
            
            # Lords typically only have Parliamentary office
            if 'parliamentary office' in contact_type:
                if contact.get('email'):
                    contact_info['parliament_email'] = contact['email']
                if contact.get('phone'):
                    contact_info['phone'] = contact['phone']
                if contact.get('fax'):
                    contact_info['fax'] = contact['fax']
                if contact.get('line1'):
                    contact_info['address_line1'] = contact['line1']
                if contact.get('line2'):
                    contact_info['address_line2'] = contact['line2']
                if contact.get('postcode'):
                    contact_info['postcode'] = contact['postcode']
            
            # Check for any website or social media (though rare for Lords)
            elif 'website' in contact_type:
                if contact.get('line1'):
                    contact_info['website'] = contact['line1']
            
            elif 'facebook' in contact_type:
                if contact.get('line1'):
                    contact_info['facebook'] = contact['line1']
            
            elif 'twitter' in contact_type or 'x (formerly twitter)' in contact_type:
                if contact.get('line1'):
                    contact_info['twitter'] = contact['line1']
        
        return contact_info
    
    def extract_member_details(self, member_data):
        """Extract additional member details from member API response"""
        details = {
            'full_title': '',
            'gender': '',
            'membership_type': '',
            'membership_start_date': '',
            'is_active': True
        }
        
        if not member_data or 'value' not in member_data:
            return details
        
        value = member_data['value']
        
        # Extract full title (e.g., "The Lord Aberdare")
        details['full_title'] = value.get('nameFullTitle', '')
        
        # Extract gender
        details['gender'] = value.get('gender', '')
        
        # Extract membership details
        latest_membership = value.get('latestHouseMembership', {})
        if latest_membership:
            details['membership_type'] = latest_membership.get('membershipFrom', '')
            details['membership_start_date'] = latest_membership.get('membershipStartDate', '')
            
            # Check if still active
            status = latest_membership.get('membershipStatus', {})
            details['is_active'] = status.get('statusIsActive', False)
        
        return details
    
    def load_cached_lords(self, cache_file='lords_cache.csv'):
        """Load Lords from cache file"""
        if not os.path.exists(cache_file):
            print(f"Cache file {cache_file} not found. Run cache_lords.py first.")
            return []
        
        lords = []
        with open(cache_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                lords.append(row)
        
        print(f"Loaded {len(lords)} Lords from cache")
        return lords
    
    def scrape_contacts(self, start_index=0, max_lords=None):
        """Scrape contact details for cached Lords"""
        lords = self.load_cached_lords()
        if not lords:
            return []
        
        if max_lords:
            lords = lords[start_index:start_index + max_lords]
        else:
            lords = lords[start_index:]
        
        print(f"Scraping contact details for {len(lords)} Lords starting from index {start_index}...")
        
        # Initialize the CSV file with headers (or append if continuing)
        csv_file = 'uk_lords_complete.csv'
        fieldnames = [
            'member_id', 'contact_url', 'full_name', 'full_title', 'first_name', 'last_name', 
            'membership_type', 'membership_from', 'membership_start_date', 'party', 'gender',
            'parliament_email', 'phone', 'fax', 'address_line1', 'address_line2', 'postcode',
            'website', 'facebook', 'twitter', 'is_active'
        ]
        
        # Write header only if starting from beginning
        if start_index == 0:
            with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
        
        for i, lord in enumerate(lords):
            member_id = lord['member_id']
            print(f"Processing Lord {start_index + i + 1}: {lord['full_name']} (ID: {member_id})")
            
            # Get contact information
            contact_data = self.get_api_data(f'/api/Members/{member_id}/Contact')
            contact_info = self.extract_contact_info(contact_data)
            
            # Get additional member details
            member_data = self.get_api_data(f'/api/Members/{member_id}')
            member_details = self.extract_member_details(member_data)
            
            # Debug output
            if contact_info.get('parliament_email') and contact_info['parliament_email'] != 'contactholmember@parliament.uk':
                print(f"    ✓ Personal email: {contact_info['parliament_email']}")
            else:
                print(f"    → Generic email or none")
            
            if contact_info.get('phone'):
                print(f"    ✓ Phone: {contact_info['phone']}")
            
            # Create result record
            result = {
                'member_id': member_id,
                'contact_url': f'https://members.parliament.uk/member/{member_id}/contact',
                'full_name': lord['full_name'],
                'full_title': member_details['full_title'],
                'first_name': lord['first_name'],
                'last_name': lord['last_name'],
                'membership_type': member_details['membership_type'] or lord.get('membership_type', ''),
                'membership_from': lord.get('membership_from', ''),
                'membership_start_date': member_details['membership_start_date'],
                'party': lord['party'],
                'gender': member_details['gender'],
                'parliament_email': contact_info.get('parliament_email', ''),
                'phone': contact_info.get('phone', ''),
                'fax': contact_info.get('fax', ''),
                'address_line1': contact_info.get('address_line1', ''),
                'address_line2': contact_info.get('address_line2', ''),
                'postcode': contact_info.get('postcode', ''),
                'website': contact_info.get('website', ''),
                'facebook': contact_info.get('facebook', ''),
                'twitter': contact_info.get('twitter', ''),
                'is_active': member_details['is_active']
            }
            
            # Append this row immediately to CSV
            with open(csv_file, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow(result)
            
            print(f"    Row {start_index + i + 1} written to {csv_file}")
            
            time.sleep(1)  # Be respectful to the API
        
        print(f"All done! Results written to {csv_file}")
        return []  # No need to return anything since we're writing directly
    
    def save_progress(self, results, filename):
        """Save progress to CSV - for compatibility"""
        fieldnames = [
            'member_id', 'contact_url', 'full_name', 'full_title', 'first_name', 'last_name', 
            'membership_type', 'membership_from', 'membership_start_date', 'party', 'gender',
            'parliament_email', 'phone', 'fax', 'address_line1', 'address_line2', 'postcode',
            'website', 'facebook', 'twitter', 'is_active'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"Progress saved to {filename}")

def main():
    start_index = 0
    max_lords = None  # Process ALL Lords by default
    
    if len(sys.argv) > 1:
        try:
            start_index = int(sys.argv[1])
            if len(sys.argv) > 2:
                max_lords = int(sys.argv[2])
                if max_lords == -1:  # -1 means all
                    max_lords = None
        except ValueError:
            print("Usage: python lords_contact_scraper.py [start_index] [max_lords]")
            print("Leave max_lords blank or use -1 to process all remaining Lords")
            sys.exit(1)
    
    print(f"Starting from Lord index {start_index}, processing {'all remaining' if max_lords is None else max_lords} Lords")
    
    scraper = LordsContactScraper()
    
    try:
        scraper.scrape_contacts(start_index, max_lords)
        print("Contact scraping completed!")
            
    except KeyboardInterrupt:
        print(f"\nInterrupted by user. Check uk_lords_complete.csv for partial results.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()