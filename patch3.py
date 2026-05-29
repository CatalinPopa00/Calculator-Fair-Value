import sys

def main():
    file_path = 'c:/Users/Snoozie/Downloads/Calculator-Fair-Value/Calculator-Fair-Value/app.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_target = """            if (_currentScenario === 'bear') selectedMult -= 3;
            else if (_currentScenario === 'bull') selectedMult += 3;"""
    
    new_target = """            if (multVal !== 'custom') {
                if (_currentScenario === 'bear') selectedMult -= 3;
                else if (_currentScenario === 'bull') selectedMult += 3;
            }"""
    
    if old_target in content:
        content = content.replace(old_target, new_target)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Success")
    else:
        print("Failed to find target")

if __name__ == '__main__':
    main()
