import os

with open('/Users/kumarreddyt/app-antigravity/SkillsyncAI/app.py', 'r') as f:
    text = f.read()

start_str = 'def init_sample_data():'
end_str = 'print("Sample data initialization complete!")\n'

start_idx = text.find(start_str)
end_idx = text.find(end_str)

if start_idx != -1 and end_idx != -1:
    text = text[:start_idx] + 'def init_sample_data():\n    pass\n' + text[end_idx + len(end_str):]
    with open('/Users/kumarreddyt/app-antigravity/SkillsyncAI/app.py', 'w') as f:
        f.write(text)
    print("Replaced successfully")
else:
    print("Failed to find start or end")
