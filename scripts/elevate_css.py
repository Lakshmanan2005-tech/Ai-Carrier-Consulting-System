import re
import os

css_path = r'd:\Ai-Carrier-Consulting-System\static\css\roadmap.css'
with open(css_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update IQ Card (Indigo Neon)
content = re.sub(
    r'\.iq-card:hover \{\s+transform: translateY\(-8px\);\s+box-shadow: 0 20px 40px rgba\(99, 102, 241, 0.15\);\s+border-color: rgba\(99, 102, 241, 0.3\);\s+\}',
    r'''.iq-card:hover {
                transform: translateY(-10px) scale(1.01);
                box-shadow: 0 20px 40px rgba(99, 102, 241, 0.2), 0 0 20px rgba(99, 102, 241, 0.1);
                border-color: rgba(99, 102, 241, 0.4);
            }''',
    content
)

# 2. Update LR Card (Emerald Neon)
content = re.sub(
    r'\.lr-card:hover \{\s+transform: translateY\(-4px\);\s+box-shadow: 0 10px 30px rgba\(16, 185, 129, 0.1\);\s+border-color: rgba\(16, 185, 129, 0.25\);\s+\}',
    r'''.lr-card:hover {
                transform: translateY(-10px) scale(1.01);
                box-shadow: 0 20px 40px rgba(16, 185, 129, 0.2), 0 0 20px rgba(16, 185, 129, 0.1);
                border-color: rgba(16, 185, 129, 0.4);
            }''',
    content
)

# 3. Update CM Cards (Blue, Purple, Emerald Neon)
content = re.sub(
    r'\.cm-section-wrapper \.cm-card:nth-child\(3n\+1\):hover \{\s+transform: translateY\(-8px\) scale\(1\.02\);\s+box-shadow: 0 15px 35px rgba\(59, 130, 246, 0.3\), 0 0 30px rgba\(59, 130, 246, 0.2\);\s+border-color: rgba\(59, 130, 246, 0.6\);\s+\}',
    r'''.cm-section-wrapper .cm-card:nth-child(3n+1):hover {
                transform: translateY(-12px) scale(1.03);
                box-shadow: 0 20px 40px rgba(59, 130, 246, 0.4), 0 0 30px rgba(59, 130, 246, 0.25);
                border-color: rgba(59, 130, 246, 0.7);
            }''',
    content
)

content = re.sub(
    r'\.cm-section-wrapper \.cm-card:nth-child\(3n\+2\):hover \{\s+transform: translateY\(-8px\) scale\(1\.02\);\s+box-shadow: 0 15px 35px rgba\(168, 85, 247, 0.3\), 0 0 30px rgba\(168, 85, 247, 0.2\);\s+border-color: rgba\(168, 85, 247, 0.6\);\s+\}',
    r'''.cm-section-wrapper .cm-card:nth-child(3n+2):hover {
                transform: translateY(-12px) scale(1.03);
                box-shadow: 0 20px 40px rgba(168, 85, 247, 0.4), 0 0 30px rgba(168, 85, 247, 0.25);
                border-color: rgba(168, 85, 247, 0.7);
            }''',
    content
)

content = re.sub(
    r'\.cm-section-wrapper \.cm-card:nth-child\(3n\+3\):hover \{\s+transform: translateY\(-8px\) scale\(1\.02\);\s+box-shadow: 0 15px 35px rgba\(16, 185, 129, 0.3\), 0 0 30px rgba\(16, 185, 129, 0.2\);\s+border-color: rgba\(16, 185, 129, 0.6\);\s+\}',
    r'''.cm-section-wrapper .cm-card:nth-child(3n+3):hover {
                transform: translateY(-12px) scale(1.03);
                box-shadow: 0 20px 40px rgba(16, 185, 129, 0.4), 0 0 30px rgba(16, 185, 129, 0.25);
                border-color: rgba(16, 185, 129, 0.7);
            }''',
    content
)

# 4. Global Transitions and Typography Refinement
content = content.replace('transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);', 'transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);')
content = content.replace('font-family: \'Plus Jakarta Sans\', sans-serif;', 'font-family: \'Plus Jakarta Sans\', sans-serif; letter-spacing: -0.02em;')

with open(css_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully elevated roadmap.css with Neon Glows and Premium Transitions.")
