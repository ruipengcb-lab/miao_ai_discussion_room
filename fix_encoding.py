import re

with open(r'C:\Users\ruipe\CodeGeeXProjects\miao_ai_discussion_room\ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '                ui.label("���� AI ������").classes("app-title")'
new = '                ui.label("🐱 喵酱 AI 讨论室").classes("app-title")'

if old in content:
    content = content.replace(old, new)
    with open(r'C:\Users\ruipe\CodeGeeXProjects\miao_ai_discussion_room\ui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed title!')
else:
    idx = content.find('app-title')
    if idx >= 0:
        print('Found at idx', idx, ':', repr(content[idx:idx+80]))
    else:
        print('app-title not found')