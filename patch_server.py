#!/usr/bin/env python3
"""
SkillPilot Registration Fix — v2
Rewrites toggle_global_registration() to bypass get_db() entirely.
Run: C:\Futurecoverage\skillpilot\.venv1\Scripts\python patch_server.py
"""
import os, re, shutil

TARGET = r"C:\Futurecoverage\skillpilot\app\routes\super_admin.py"
CACHE  = r"C:\Futurecoverage\skillpilot\app\routes\__pycache__"

CLEAN_FUNC = '''
@super_admin_bp.route('/api/registration/global', methods=['POST'])
@admin_dashboard_required
def toggle_global_registration():
    """Pause or resume registration across ALL courses."""
    try:
        from app.models import db as _mdb, KeyValueSetting
        data = request.get_json() or {}
        paused = bool(data.get('paused', False))
        setting = KeyValueSetting.query.filter_by(key='registration_paused').first()
        if setting:
            setting.value = '1' if paused else '0'
        else:
            setting = KeyValueSetting(key='registration_paused',
                                      value='1' if paused else '0')
            _mdb.session.add(setting)
        _mdb.session.commit()
        state = 'paused' if paused else 'open'
        return jsonify({'success': True, 'paused': paused,
                        'message': f'Global registration is now {state}'})
    except Exception as e:
        import traceback
        try:
            from app.models import db as _mdb2
            _mdb2.session.rollback()
        except Exception:
            pass
        return jsonify({'error': str(e),
                        'detail': traceback.format_exc()}), 500
'''

print("\n  SkillPilot Registration Fix v2")
print("  ================================\n")

if not os.path.exists(TARGET):
    print(f"  ERROR: Not found: {TARGET}")
    input("\n  Press Enter to exit"); exit(1)

with open(TARGET, "r", encoding="utf-8") as f:
    content = f.read()

# Find the function and replace it
PATTERN = re.compile(
    r"@super_admin_bp\.route\('/api/registration/global', methods=\['POST'\]\).*?"
    r"(?=\n\n@|\Z)",
    re.DOTALL
)
m = PATTERN.search(content)
if not m:
    print("  WARNING: Could not locate toggle_global_registration route block.")
    print("           Trying line-by-line search...")
    if "def toggle_global_registration" in content:
        print("  Function exists but pattern didn't match — backup and manual check needed.")
    else:
        print("  Function NOT found in file at all.")
    input("\n  Press Enter to exit"); exit(1)

print(f"  Found route block at chars {m.start()}–{m.end()}")
backup = TARGET + ".bak2"
shutil.copy2(TARGET, backup)
print(f"  Backup saved: {backup}")

new_content = content[:m.start()] + CLEAN_FUNC + "\n\n" + content[m.end():]

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(new_content)
print("  Function replaced with clean version (uses db directly).")

# Clear pycache
if os.path.exists(CACHE):
    shutil.rmtree(CACHE)
    print(f"  Cache cleared: {CACHE}")

print("\n  SUCCESS! Now:")
print("    1. Stop serve.py (Ctrl+C)")
print("    2. cd C:\\Futurecoverage\\skillpilot")
print("    3. .venv1\\Scripts\\python serve.py")
print("    4. Test Pause All Registrations button\n")
input("  Press Enter to close")
