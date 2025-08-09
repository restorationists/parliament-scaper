# Parliament Scraper

For generating handy CSVs of MPs and Lords types.

```
python3 -m venv parliament_scraper_env
source parliament_scraper_env/bin/activate
pip install requests beautifulsoup4
python3 cache_mps.py
python3 cache_lords.py
python3 scrape_mps.py
python3 scrape_lords.py
```