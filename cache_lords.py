#!/usr/bin/env python3
"""
Cache the Lords list to avoid re-scraping the index every time
"""

import requests
import csv
import time
import sys
from urllib.parse import urljoin

class LordsListCacher:
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
    
    def cache_lords_list(self):
        """Cache the Lords list to CSV"""
        all_lords = []
        skip = 0
        take = 20
        
        print("Caching Lords list from API...")
        
        while True:
            params = {
                'House': 'Lords',  # Changed from 'Commons' to 'Lords'
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
                    lord = item['value']
                    membership = lord.get('latestHouseMembership', {})
                    status = membership.get('membershipStatus', {})
                    
                    if (status.get('statusIsActive') == True and 
                        membership.get('membershipEndDate') is None):
                        member_items.append(lord)
            
            print(f"Retrieved {len(member_items)} current Lords (total so far: {len(all_lords) + len(member_items)})")
            all_lords.extend(member_items)
            
            skip += take
            time.sleep(0.5)
            
            # Lords have more members than MPs (around 800), so increased the limit
            if len(all_lords) > 850:
                print(f"Warning: Retrieved {len(all_lords)} Lords, stopping...")
                break
        
        # Process and save to cache file
        cache_records = []
        for lord in all_lords:
            member_id = lord.get('id')
            full_name = lord.get('nameDisplayAs', '')
            first_name, last_name = self.split_name(full_name)
            
            latest_membership = lord.get('latestHouseMembership', {})
            # Lords don't have constituencies, they have membership types
            membership_type = latest_membership.get('membershipFromDescription', '')
            membership_from = latest_membership.get('membershipFrom', '')
            
            # Get the type of peerage (Life peer, Hereditary, Bishop, etc.)
            # Check if 'house' exists and is a dictionary before accessing 'name'
            house_info = latest_membership.get('house', {})
            if isinstance(house_info, dict):
                house_membership_type = house_info.get('name', '')
            else:
                house_membership_type = ''
            
            latest_party = lord.get('latestParty', {})
            party = latest_party.get('name', '')
            
            cache_record = {
                'member_id': member_id,
                'full_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'membership_type': membership_type,
                'membership_from': membership_from,
                'party': party
            }
            cache_records.append(cache_record)
        
        # Save to CSV cache
        cache_file = 'lords_cache.csv'
        with open(cache_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['member_id', 'full_name', 'first_name', 'last_name', 'membership_type', 'membership_from', 'party']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(cache_records)
        
        print(f"Cached {len(cache_records)} Lords to {cache_file}")
        return cache_records

def main():
    cacher = LordsListCacher()
    try:
        lords_data = cacher.cache_lords_list()
        print(f"Successfully cached {len(lords_data)} Lords")
        
        # Print first few records
        print("\nFirst few records:")
        for i, lord in enumerate(lords_data[:10]):
            print(f"{i+1}. {lord['first_name']} {lord['last_name']} ({lord['party']}) - {lord['membership_type']} [ID: {lord['member_id']}]")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()