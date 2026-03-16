#!/usr/bin/env python3
"""
Manually patch embed-agent.py to call anti-anti-frida.py after agent embedding.
This is the fallback for when patch 0010 fails to apply via git am.
"""
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: patch_embed_agent.py <embed-agent.py>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if already patched
    if 'anti-anti-frida' in content:
        print("    Already patched, skipping")
        return
    
    # The injection code to add
    injection_lines = [
        '            import os',
        '            custom_script=str(output_dir)+"/../../../../frida/subprojects/frida-core/src/anti-anti-frida.py"',
        '            return_code = os.system("python3 "+custom_script+" "+str(priv_dir / f"frida-agent-{flavor}.so"))',
        '            if return_code == 0:',
        '                print("anti-anti-frida finished")',
        '            else:',
        '                print("anti-anti-frida error. Code:", return_code)',
    ]
    injection = '\n'.join(injection_lines)
    
    # Strategy 1: Find embedded_agent.write_bytes(b"")
    targets = [
        'embedded_agent.write_bytes(b"")',
        "embedded_agent.write_bytes(b'')",
    ]
    
    for target in targets:
        if target in content:
            content = content.replace(target, target + '\n' + injection, 1)
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"    Patched after '{target}'")
            return
    
    # Strategy 2: Line-by-line search for write_bytes with embedded_agent
    lines = content.split('\n')
    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if not inserted and 'write_bytes' in line and 'embedded_agent' in line:
            new_lines.extend(injection_lines)
            inserted = True
    
    if inserted:
        with open(filepath, 'w') as f:
            f.write('\n'.join(new_lines))
        print("    Patched using line-by-line search")
        return
    
    print("    ERROR: Could not find insertion point in embed-agent.py")
    sys.exit(1)

if __name__ == '__main__':
    main()
