import re

def check_html_balance(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Remove script and style tags content as they might contain < >
    content = re.sub(r'<(script|style).*?>.*?</\1>', '', content, flags=re.DOTALL)
    
    # Simple tag balancer
    tags = re.findall(r'<(/?[a-zA-Z0-9]+).*?>', content)
    stack = []
    void_tags = {'img', 'br', 'hr', 'input', 'link', 'meta'}
    
    for tag in tags:
        if tag.startswith('/'):
            # Closing tag
            tag_name = tag[1:]
            if not stack:
                print(f"Error: Unexpected closing tag </{tag_name}>")
            elif stack[-1] != tag_name:
                print(f"Error: Mismatched tag: expected </{stack[-1]}>, found </{tag_name}>")
                stack.pop()
            else:
                stack.pop()
        elif tag in void_tags:
            continue
        else:
            # Opening tag
            stack.append(tag)
    
    if stack:
        print(f"Error: Unclosed tags: {stack}")
    else:
        print("Tags are balanced (excluding void tags and script/style content)")

check_html_balance('/Users/kumarreddyt/app-antigravity/SkillsyncAI/templates/register.html')
