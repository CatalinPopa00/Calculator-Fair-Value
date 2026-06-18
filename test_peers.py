from scraper.yahoo import get_competitors_data
import logging

logging.basicConfig(level=logging.DEBUG)
print(get_competitors_data('FISV', limit=10))
