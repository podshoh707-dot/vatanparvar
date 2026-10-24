import os
import sys
import re
import glob

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

admin_files = glob.glob('handlers/admin_panel/*.py')

buttons = []
handlers = []

for f in admin_files:
    with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
        content = fp.read()
        
        # Find callback_data
        cb_datas = re.findall(r'callback_data=["\']([^"\']+)["\']', content)
        for cb in cb_datas:
            buttons.append((f, cb))
            
        # Find callback handlers
        cb_handlers = re.findall(r'@\w+\.callback_query\((.*?)\)', content, re.DOTALL)
        for h in cb_handlers:
            handlers.append((f, h.strip().replace('\n', ' ')))

print(f'Total buttons in admin panel: {len(buttons)}')
print(f'Total handlers in admin panel: {len(handlers)}')

# Check main menu buttons
main_menu_cbs = [
    'admin_stats', 'admin_broadcast', 'admin_tests', 'admin_signs', 
    'admin_rules', 'admin_videos', 'admin_premium', 'admin_groups', 
    'adm_mgmt', 'admin_system'
]

print('\n--- MAIN MENU BUTTONS AUDIT ---')
for cb in main_menu_cbs:
    found = [h for h in handlers if cb in h[1]]
    if found:
        print(f'✅ {cb} -> {found[0][0]}')
    else:
        print(f'❌ MISSING HANDLER FOR: {cb}')

# Check all buttons across admin panel
print('\n--- SUBMENU BUTTONS AUDIT ---')
missing_count = 0
for f, cb in buttons:
    # Check if matched by exact or regex/startswith
    matched = False
    for h_file, h_code in handlers:
        if f'"{cb}"' in h_code or f"'{cb}'" in h_code:
            matched = True
            break
        # startswith or regex
        if 'startswith' in h_code or 'regexp' in h_code or 'in_' in h_code:
            # extract string from startswith
            sw = re.findall(r'startswith\(["\']([^"\']+)["\']', h_code)
            for s in sw:
                if cb.startswith(s):
                    matched = True
                    break
            if matched: break
            
            rx = re.findall(r'regexp\(r?["\']([^"\']+)["\']', h_code)
            for r in rx:
                if re.search(r, cb):
                    matched = True
                    break
            if matched: break
            
    if not matched and not cb.startswith('http'):
        print(f'⚠️ UNHANDLED BUTTON in {os.path.basename(f)}: "{cb}"')
        missing_count += 1

print(f'\nTotal unhandled buttons: {missing_count}')
