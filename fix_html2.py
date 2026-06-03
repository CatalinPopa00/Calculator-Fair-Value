import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Fix excess closing divs after Ownership
fixed_html = re.sub(r'(\s*</div>\s*){4,8}<!-- 2\. Historical Trends Segment -->', 
                    '\n                                        </div>\n                                    </div>\n                                </div>\n                            </div>\n                        </div>\n\n<!-- 2. Historical Trends Segment -->', html)

# Fix excess closing divs after Historical Trends
fixed_html = re.sub(r'<div class="research-footer">\s*\* EPS values represent Diluted EPS \(GAAP\) for historical accuracy\.\s*</div>(\s*</div>\s*){1,6}</section>',
                    '<div class="research-footer">\n                                    * EPS values represent Diluted EPS (GAAP) for historical accuracy.\n                                </div>\n                            </div>\n                        </div>\n                    </section>', fixed_html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(fixed_html)
print('Fixed excess div tags')
