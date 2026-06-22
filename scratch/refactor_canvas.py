import os
import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find def _update_canvas(self, *args): ...
    # We will use regex to find the method and rename it to _do_update_canvas(self, dt)
    # Then insert _update_canvas that schedules it.
    
    # Regex to match:
    #     def _update_canvas(self, *args):
    #         self.canvas.before.clear()
    
    pattern = r"([ \t]+)def _update_canvas\(self(?:, \*args)?\):\n(?:\1    .*?\n)*?\1    self\.canvas\.before\.clear\(\)"
    
    def repl(m):
        indent = m.group(1)
        # We replace the signature and the body will just be indented the same.
        # Wait, it's easier to just do string replacement:
        return m.group(0) # We will do it manually

    # A simpler approach:
    # Just replace:
    #     def _update_canvas(self, *args):
    #         self.canvas.before.clear()
    # with:
    #     def _update_canvas(self, *args):
    #         from kivy.clock import Clock
    #         Clock.schedule_once(self._deferred_update_canvas, -1)
    # 
    #     def _deferred_update_canvas(self, dt):
    #         self.canvas.before.clear()
    
    lines = content.split('\n')
    out_lines = []
    i = 0
    changed = False
    while i < len(lines):
        line = lines[i]
        if 'def _update_canvas(self' in line and lines[i+1].strip() == 'self.canvas.before.clear()':
            indent = line[:line.find('def')]
            out_lines.append(line)
            out_lines.append(indent + "    from kivy.clock import Clock")
            out_lines.append(indent + "    Clock.schedule_once(self._deferred_update_canvas, -1)")
            out_lines.append("")
            out_lines.append(indent + "def _deferred_update_canvas(self, dt):")
            out_lines.append(lines[i+1])
            i += 1
            changed = True
        elif 'def _update_canvas(self' in line and 'pass' in lines[i+1]:
            # skip
            out_lines.append(line)
        else:
            out_lines.append(line)
        i += 1
        
    if changed:
        # also handle _update_bg
        # actually _update_bg is on screens, which is fine, but let's do it too if we want
        pass
        
    # Let's do another pass for _update_bg just in case
    content = '\n'.join(out_lines)
    lines = content.split('\n')
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'def _update_bg(self' in line and 'self.canvas.before.clear()' in lines[i+1]:
            indent = line[:line.find('def')]
            out_lines.append(line)
            out_lines.append(indent + "    from kivy.clock import Clock")
            out_lines.append(indent + "    Clock.schedule_once(self._deferred_update_bg, -1)")
            out_lines.append("")
            out_lines.append(indent + "def _deferred_update_bg(self, dt):")
            out_lines.append(lines[i+1])
            i += 1
            changed = True
        else:
            out_lines.append(line)
        i += 1

    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out_lines))
        print(f"Updated {filepath}")

for root, _, files in os.walk(r"c:\Users\thesa\Downloads\ZIDON\Implementation\frontend"):
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
