import sys
import re

content = open('index.html', 'r', encoding='utf-8').read()

old_block = """                                <div class="analyst-tabs-wrapper">
                                    <div class="analyst-tabs-control">
                                        <button class="analyst-tab-btn ownership-tab-btn active" data-tab="holders">Holders</button>
                                        <button class="analyst-tab-btn ownership-tab-btn" data-tab="top-holders">Top</button>
                                        <button class="analyst-tab-btn ownership-tab-btn" data-tab="insiders">Insiders</button>
                                        <button class="analyst-tab-btn ownership-tab-btn" data-tab="stats">Stats</button>
                                        <button class="analyst-tab-btn ownership-tab-btn" data-tab="roster-table">Roster</button>
                                        <button class="analyst-tab-btn ownership-tab-btn" data-tab="roster-chart">Pie</button>
                                    </div>
                                </div>"""

new_block = """                                <div class="corporate-tabs-wrapper" style="display: flex; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 15px; gap: 10px; overflow-x: auto; scrollbar-width: none;">
                                    <button class="brief-tab ownership-tab-btn active" data-tab="holders">👥 Holders</button>
                                    <button class="brief-tab ownership-tab-btn" data-tab="top-holders">🔝 Top</button>
                                    <button class="brief-tab ownership-tab-btn" data-tab="insiders">🕵️ Insiders</button>
                                    <button class="brief-tab ownership-tab-btn" data-tab="stats">📊 Stats</button>
                                    <button class="brief-tab ownership-tab-btn" data-tab="roster-table">📋 Roster</button>
                                    <button class="brief-tab ownership-tab-btn" data-tab="roster-chart">🥧 Pie</button>
                                </div>"""

content = content.replace(old_block, new_block)

# Let's also add the carousel lines for Historical Anchors!
# Find where the historical-carousel-viewport ends and insert lines
# <div class="historical-carousel-viewport">
# ...
# </div>
hist_pattern = r'(<div class="historical-carousel-viewport">.*?</div>\s*</div>\s*</div>)'
# Actually, the div ends at line 1128. Let's find exactly where to insert:
carousel_nav_html = """
                                    <!-- Navigation Controls (Dashes) for Historical Anchors -->
                                    <div class="mobile-carousel-indicators" style="display: flex; gap: 6px; justify-content: center; width: 100%; margin-top: 15px;">
                                        <div class="carousel-indicator-line active" id="hist-dot-0" onclick="document.getElementById('tab-financials').click()"></div>
                                        <div class="carousel-indicator-line" id="hist-dot-1" onclick="document.getElementById('tab-ai-kpis').click()"></div>
                                    </div>
"""

# Let's insert it after <div class="historical-carousel-viewport">...</div>
# To do this safely, let's look for `<!-- Slide 2: AI KPI Audit -->` block end.
# In index.html, it's:
# 1126:                                             </div>
# 1127: 
# 1128:                                         </div>
# 1129:                                     </div>
# So after line 1129, we have `<script>`.
search_str = """                                        </div>
                                    </div>

                                    <script>"""
replace_str = """                                        </div>
                                    </div>
""" + carousel_nav_html + """
                                    <script>"""
content = content.replace(search_str, replace_str)

# Also update the inline script for historical anchors to toggle active state on hist-dots
script_search = """                                                if (index === 0) {"""
script_replace = """                                                document.getElementById('hist-dot-0')?.classList.toggle('active', index === 0);
                                                document.getElementById('hist-dot-1')?.classList.toggle('active', index === 1);
                                                if (index === 0) {"""
content = content.replace(script_search, script_replace)

open('index.html', 'w', encoding='utf-8').write(content)
print("Done.")
