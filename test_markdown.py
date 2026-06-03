"""Quick test: does ui.markdown render text at all?"""
from nicegui import ui

@ui.page('/')
def test():
    ui.label("=== Markdown Render Test ===").style("font-size:20px;font-weight:bold;")
    
    # Test 1: Simple text, default sanitize=True
    ui.label("Test 1: ui.markdown('Hello', sanitize=True)")
    ui.markdown("Hello World - default sanitize")
    
    # Test 2: Simple text, sanitize=False
    ui.label("Test 2: ui.markdown('Hello', sanitize=False)")
    ui.markdown("Hello World - no sanitize", sanitize=False)
    
    # Test 3: Chinese text, default
    ui.label("Test 3: ui.markdown Chinese, default sanitize")
    ui.markdown("这是一条中文测试消息")
    
    # Test 4: Chinese text, sanitize=False
    ui.label("Test 4: ui.markdown Chinese, sanitize=False")
    ui.markdown("这是一条中文测试消息", sanitize=False)
    
    # Test 5: Using ui.html directly
    ui.label("Test 5: ui.html (bypass markdown)")
    ui.html("<p>Direct HTML render - 直接HTML渲染</p>")
    
    # Test 6: Using ui.label
    ui.label("Test 6: ui.label")
    ui.label("Plain label render - 纯label渲染")

ui.run(port=9998, reload=False, title="Markdown Test")
