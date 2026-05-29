import sys

def main():
    file_path = 'c:/Users/Snoozie/Downloads/Calculator-Fair-Value/Calculator-Fair-Value/app.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    bad = """                                    else if (k === 'PS') {
                                    else if (k === 'PB') {"""
                                    
    good = """                                    else if (k === 'PS') {
                                        val = impliedPs || (globalData.company_profile && (globalData.company_profile.fwd_ps || globalData.company_profile.forward_ev_sales));
                                    }
                                    else if (k === 'PB') {"""

    if bad in content:
        content = content.replace(bad, good)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Success")
    else:
        print("Failed to find bad")

if __name__ == '__main__':
    main()
