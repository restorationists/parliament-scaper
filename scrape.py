#!/usr/bin/env python3
"""
Scrape contact details for MPs using the cached list
"""

import requests
import csv
import time
import sys
import os
from urllib.parse import urljoin

class MPContactScraper:
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
        """Extract contact information from API response"""
        contact_info = {
            'parliament_email': '',
            'phone': '',
            'constituency_email': '',
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
            
            if 'parliamentary office' in contact_type:
                if contact.get('email'):
                    contact_info['parliament_email'] = contact['email']
                if contact.get('phone'):
                    contact_info['phone'] = contact['phone']
            
            elif 'constituency office' in contact_type:
                if contact.get('email'):
                    contact_info['constituency_email'] = contact['email']
            
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
    
    def load_cached_mps(self, cache_file='mps_cache.csv'):
        """Load MPs from cache file"""
        if not os.path.exists(cache_file):
            print(f"Cache file {cache_file} not found. Run cache_mps_list.py first.")
            return []
        
        mps = []
        with open(cache_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                mps.append(row)
        
        print(f"Loaded {len(mps)} MPs from cache")
        return mps
    
    def scrape_contacts(self, start_index=0, max_mps=None):
        """Scrape contact details for cached MPs"""
        mps = self.load_cached_mps()
        if not mps:
            return []
        
        if max_mps:
            mps = mps[start_index:start_index + max_mps]
        else:
            mps = mps[start_index:]
        
        print(f"Scraping contact details for {len(mps)} MPs starting from index {start_index}...")
        
        # Initialize the CSV file with headers (or append if continuing)
        csv_file = 'uk_mps_complete.csv'
        fieldnames = [
            'member_id', 'contact_url', 'first_name', 'last_name', 'constituency_name', 'party',
            'parliament_email', 'phone', 'constituency_email',
            'website', 'facebook', 'twitter'
        ]
        
        # Write header only if starting from beginning
        if start_index == 0:
            with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
        
        for i, mp in enumerate(mps):
            member_id = mp['member_id']
            print(f"Processing MP {start_index + i + 1}: {mp['full_name']} (ID: {member_id})")
            
            # Get contact information
            contact_data = self.get_api_data(f'/api/Members/{member_id}/Contact')
            
            # Debug: print what we got from the contact API
            print(f"    Contact API response:")
            if contact_data and 'value' in contact_data:
                for contact in contact_data['value']:
                    contact_type = contact.get('type', 'Unknown')
                    email = contact.get('email', '')
                    phone = contact.get('phone', '')
                    line1 = contact.get('line1', '')
                    print(f"      {contact_type}: email='{email}', phone='{phone}', line1='{line1}'")
            else:
                print(f"      No contact data returned")
            
            contact_info = self.extract_contact_info(contact_data)
            
            # Debug: print extracted contact info
            print(f"    Extracted contact info:")
            print(f"      Parliament email: '{contact_info.get('parliament_email', '')}'")
            print(f"      Phone: '{contact_info.get('phone', '')}'")
            print(f"      Constituency email: '{contact_info.get('constituency_email', '')}'")
            print(f"      Website: '{contact_info.get('website', '')}'")
            print(f"      Facebook: '{contact_info.get('facebook', '')}'")
            print(f"      Twitter: '{contact_info.get('twitter', '')}'")
            print()
            
            # Create result record
            result = {
                'member_id': member_id,
                'contact_url': f'https://members.parliament.uk/member/{member_id}/contact',
                'first_name': mp['first_name'],
                'last_name': mp['last_name'],
                'constituency_name': mp['constituency_name'],
                'party': mp['party'],
                'parliament_email': contact_info.get('parliament_email', ''),
                'phone': contact_info.get('phone', ''),
                'constituency_email': contact_info.get('constituency_email', ''),
                'website': contact_info.get('website', ''),
                'facebook': contact_info.get('facebook', ''),
                'twitter': contact_info.get('twitter', '')
            }
            
            # Append this row immediately to CSV
            with open(csv_file, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow(result)
            
            print(f"    Row {start_index + i + 1} written to {csv_file}")
            
            time.sleep(1)  # Be respectful
        
        print(f"All done! Results written to {csv_file}")
        return []  # No need to return anything since we're writing directly
    
    def save_progress(self, results, filename):
        """Save progress to CSV - ONLY the current batch"""
        fieldnames = [
            'member_id', 'contact_url', 'first_name', 'last_name', 'constituency_name', 'party',
            'parliament_email', 'phone', 'constituency_email',
            'website', 'facebook', 'twitter'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"Progress saved to {filename}")
    
    def save_batch_only(self, results, batch_start, filename):
        """Save only the current batch, not all results"""
        fieldnames = [
            'member_id', 'contact_url', 'first_name', 'last_name', 'constituency_name', 'party',
            'parliament_email', 'phone', 'constituency_email',
            'website', 'facebook', 'twitter'
        ]
        
        # Only save the last 10 results (current batch)
        batch_results = results[-10:] if len(results) >= 10 else results
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(batch_results)
        
        print(f"Batch progress saved to {filename}")
    
    def save_final_results(self, results, filename='uk_mps_final.csv'):
        """Save final results to CSV"""
        self.save_progress(results, filename)
        print(f"Final results saved to {filename}")

def main():
    start_index = 0
    max_mps = None  # Process ALL MPs by default
    
    if len(sys.argv) > 1:
        try:
            start_index = int(sys.argv[1])
            if len(sys.argv) > 2:
                max_mps = int(sys.argv[2])
                if max_mps == -1:  # -1 means all
                    max_mps = None
        except ValueError:
            print("Usage: python contact_scraper.py [start_index] [max_mps]")
            print("Leave max_mps blank or use -1 to process all remaining MPs")
            sys.exit(1)
    
    print(f"Starting from MP index {start_index}, processing {'all remaining' if max_mps is None else max_mps} MPs")
    
    scraper = MPContactScraper()
    
    try:
        scraper.scrape_contacts(start_index, max_mps)
        print("Contact scraping completed!")
            
    except KeyboardInterrupt:
        print(f"\nInterrupted by user. Check uk_mps_complete.csv for partial results.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
