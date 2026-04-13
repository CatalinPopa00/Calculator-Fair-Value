import sys
import asyncio
import os
sys.path.insert(0, os.path.abspath('api'))
import index as api
res = asyncio.run(api.calculate_fair_value_logic('NVDA', 'dummy_id'))
print('MEDIAN PEG:', res['relative']['median_peer_peg'])
