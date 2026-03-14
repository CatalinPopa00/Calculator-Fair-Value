import sys
sys.path.append('api')
from scraper.yahoo import get_lightweight_company_data
print(get_lightweight_company_data('AMD'))
