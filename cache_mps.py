#!/usr/bin/env python3
"""
Cache the MPs list to avoid re-scraping the index every time
"""

import requests
import csv
import time
import sys
from urllib.parse import urljoin

class MPListCacher:
    def __init__(self):
        self.base_url = "https://members-api.parliament.uk/api"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-GB,en;q=0.9'
        })
    
    def get_api_data(self, endpoint, params=None, retries=3):
        """Get data from API with retries and error handling"""
        url = urljoin(self.base_url, endpoint)
        
        for attempt in range(retries):
            try:
                response = self.session.get(url, params=params, timeout=15)
                
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
    
    def split_name(self, full_name):
        """Split full name into first and last name, removing titles"""
        titles = [
            'The Rt Hon ', 'Rt Hon ', 'Sir ', 'Dame ', 'Dr ', 'Mr ', 'Ms ', 'Mrs ', 'Miss ',
            'Lord ', 'Lady ', 'Baroness ', 'Baron ', 'Earl ', 'Countess ', 'Viscount ', 'Viscountess ',
            'Duke ', 'Duchess ', 'Marquess ', 'Marchioness ', 'Rev ', 'Revd ', 'Father ', 'Mother ',
            'Professor ', 'Prof ', 'Colonel ', 'Major ', 'Captain ', 'Lieutenant ', 'Admiral ',
            'General ', 'Air Marshal ', 'Group Captain ', 'Wing Commander ', 'Squadron Leader '
        ]
        
        name = full_name.strip()
        for title in titles:
            if name.startswith(title):
                name = name[len(title):].strip()
                break
        
        if ' ' in name:
            parts = name.split(' ', 1)
            first_name = parts[0].strip()
            last_name = parts[1].strip()
        else:
            first_name = name.strip()
            last_name = ''
        
        return first_name, last_name
    
    def cache_mps_list(self):
        """Cache the MP list to CSV"""
        all_mps = []
        skip = 0
        take = 20
        
        print("Caching MPs list from API...")
        
        while True:
            params = {
                'House': 'Commons',
                'IsEligible': 'true',
                'skip': skip,
                'take': take
            }
            
            data = self.get_api_data('/api/Members/Search', params)
            
            if not data or 'items' not in data:
                break
            
            items = data['items']
            if not items:
                break
            
            # Filter for only currently active members
            member_items = []
            for item in items:
                if 'value' in item:
                    mp = item['value']
                    membership = mp.get('latestHouseMembership', {})
                    status = membership.get('membershipStatus', {})
                    
                    if (status.get('statusIsActive') == True and 
                        membership.get('membershipEndDate') is None):
                        member_items.append(mp)
            
            print(f"Retrieved {len(member_items)} current MPs (total so far: {len(all_mps) + len(member_items)})")
            all_mps.extend(member_items)
            
            skip += take
            time.sleep(0.5)
            
            if len(all_mps) > 680:
                print(f"Warning: Retrieved {len(all_mps)} MPs, stopping...")
                break
        
        # Process and save to cache file
        cache_records = []
        for mp in all_mps:
            member_id = mp.get('id')
            full_name = mp.get('nameDisplayAs', '')
            first_name, last_name = self.split_name(full_name)
            
            latest_membership = mp.get('latestHouseMembership', {})
            constituency_name = latest_membership.get('membershipFrom', '')
            
            latest_party = mp.get('latestParty', {})
            party = latest_party.get('name', '')
            
            cache_record = {
                'member_id': member_id,
                'full_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'constituency_name': constituency_name,
                'party': party
            }
            cache_records.append(cache_record)
        
        # Save to CSV cache
        cache_file = 'mps_cache.csv'
        with open(cache_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['member_id', 'full_name', 'first_name', 'last_name', 'constituency_name', 'party']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(cache_records)
        
        print(f"Cached {len(cache_records)} MPs to {cache_file}")
        return cache_records

def main():
    cacher = MPListCacher()
    try:
        mps_data = cacher.cache_mps_list()
        print(f"Successfully cached {len(mps_data)} MPs")
        
        # Print first few records
        print("\nFirst few records:")
        for i, mp in enumerate(mps_data[:10]):
            print(f"{i+1}. {mp['first_name']} {mp['last_name']} ({mp['party']}) - {mp['constituency_name']} [ID: {mp['member_id']}]")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
