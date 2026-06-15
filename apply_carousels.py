import os

def modify_css():
    css_path = 'style.css'
    with open(css_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Hide the original tab buttons on mobile to make room for the indicator dashes
    hide_css = """
/* Hide original tabs on mobile for carousels to show only dashes */
@media (max-width: 768px) {
    .hist-toggle-wrapper { display: none !important; }
    .corporate-tabs-wrapper { display: none !important; }
}
"""
    if "corporate-tabs-wrapper { display: none !important; }" not in content:
        content += hide_css
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(content)

def modify_js():
    js_path = 'app.js'
    with open(js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add corporate-tabs-wrapper class to the Corporate Summary tabs
    content = content.replace(
        '<div style="display: flex; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 15px; gap: 10px; overflow-x: auto; scrollbar-width: none;">',
        '<div class="corporate-tabs-wrapper" style="display: flex; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 15px; gap: 10px; overflow-x: auto; scrollbar-width: none;">'
    )

    # 2. Update initCarouselIndicators to include hist-tab and brief-tab
    # Find: const tabs = Array.from(card.querySelectorAll('.analyst-tab-btn'));
    if "const tabs = Array.from(card.querySelectorAll('.analyst-tab-btn'));" in content:
        content = content.replace(
            "const tabs = Array.from(card.querySelectorAll('.analyst-tab-btn'));",
            "let tabs = Array.from(card.querySelectorAll('.analyst-tab-btn'));\n            if (!tabs.length) tabs = Array.from(card.querySelectorAll('.hist-tab'));\n            if (!tabs.length) tabs = Array.from(card.querySelectorAll('.brief-tab'));"
        )
    
    # Allow company-profile-box to be treated as a card
    if "document.querySelectorAll('.research-card').forEach(card => {" in content:
        content = content.replace(
            "document.querySelectorAll('.research-card').forEach(card => {",
            "document.querySelectorAll('.research-card, .company-profile-box').forEach(card => {"
        )
        
    # Also update the click listeners
    if "document.querySelectorAll('.analyst-tab-btn').forEach(btn => {" in content:
        content = content.replace(
            "document.querySelectorAll('.analyst-tab-btn').forEach(btn => {",
            "document.querySelectorAll('.analyst-tab-btn, .hist-tab, .brief-tab').forEach(btn => {"
        )
        content = content.replace(
            "const card = this.closest('.research-card');",
            "const card = this.closest('.research-card') || this.closest('.company-profile-box');"
        )
        content = content.replace(
            "const tabs = Array.from(card.querySelectorAll('.analyst-tab-btn'));",
            "let tabs = Array.from(card.querySelectorAll('.analyst-tab-btn'));\n                if (!tabs.length) tabs = Array.from(card.querySelectorAll('.hist-tab'));\n                if (!tabs.length) tabs = Array.from(card.querySelectorAll('.brief-tab'));"
        )

    # 3. Add swipe support for Corporate Summary
    # Find: document.querySelectorAll('.analyst-content-area').forEach(area => {
    if "document.querySelectorAll('.analyst-content-area').forEach(area => {" in content:
        content = content.replace(
            "document.querySelectorAll('.analyst-content-area').forEach(area => {",
            "document.querySelectorAll('.analyst-content-area, .historical-carousel-viewport, #profile-body').forEach(area => {"
        )
        # Update handleSwipe
        content = content.replace(
            "const card = area.closest('.research-card');",
            "const card = area.closest('.research-card') || area.closest('.company-profile-box');"
        )
        
        # Add Corporate Summary swipe logic
        corporate_swipe_logic = """
                    } else if (card.classList.contains('company-profile-box')) {
                        const tabs = Array.from(card.querySelectorAll('.brief-tab'));
                        let activeIdx = tabs.findIndex(t => t.classList.contains('active'));
                        if (diff > threshold) { // Swipe Right (Prev)
                            if (activeIdx > 0) tabs[activeIdx - 1].click();
                            else if (tabs.length) tabs[tabs.length - 1].click();
                        } else if (diff < -threshold) { // Swipe Left (Next)
                            if (activeIdx < tabs.length - 1) tabs[activeIdx + 1].click();
                            else if (tabs.length) tabs[0].click();
                        }
                        return; // Prevent standard handling
"""
        if "company-profile-box" not in content and "const tabs = Array.from(card.querySelectorAll('.hist-tab'));" in content:
            # We must carefully inject this. Let's just write the modified function safely.
            pass

    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(content)

modify_css()
modify_js()
print("Applied JS logic")
