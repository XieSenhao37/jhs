#!/usr/bin/env python3
"""
Post-build anti-anti-frida patching script.
This script patches frida-server, frida-inject, and frida-agent.so
to remove/randomize frida-specific strings and symbols.
"""
import lief
import sys
import random
import os
import glob

random_charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def log_color(msg):
    print(f"\033[1;31;40m{msg}\033[0m")

def patch_elf(input_file):
    log_color(f"\n[*] Patching ELF: {input_file}")
    
    binary = lief.parse(input_file)
    if not binary:
        log_color(f"[!] Not a valid ELF, skipping: {input_file}")
        return

    # 1. Patch symbols: replace frida/FRIDA with random strings
    random_name = "".join(random.choices(random_charset, k=5))
    log_color(f"[*] Replacing `frida` symbol names with `{random_name}`")
    
    patched_symbols = 0
    for symbol in binary.symbols:
        if symbol.name == "frida_agent_main":
            symbol.name = "main"
            patched_symbols += 1
        
        if "frida" in symbol.name:
            symbol.name = symbol.name.replace("frida", random_name)
            patched_symbols += 1
        
        if "FRIDA" in symbol.name:
            symbol.name = symbol.name.replace("FRIDA", random_name)
            patched_symbols += 1
    
    log_color(f"[*] Patched {patched_symbols} symbols")

    # 2. Patch .rodata section strings
    all_patch_strings = [
        "FridaScriptEngine",
        "GLib-GIO", 
        "GDBusProxy",
        "GumScript",
        "frida-agent",
        "re.frida.server",
        "FRIDA_",
    ]
    
    patched_strings = 0
    for section in binary.sections:
        if section.name != ".rodata":
            continue
        for patch_str in all_patch_strings:
            addr_all = section.search_all(patch_str)
            for addr in addr_all:
                # Reverse the string as replacement (same length)
                patch = [ord(n) for n in list(patch_str)[::-1]]
                log_color(f"[*] Patching .rodata offset={hex(section.file_offset + addr)} `{patch_str}` -> `{''.join(list(patch_str)[::-1])}`")
                binary.patch_address(section.file_offset + addr, patch)
                patched_strings += 1
    
    log_color(f"[*] Patched {patched_strings} .rodata strings")
    
    binary.write(input_file)

    # 3. Patch thread names using sed (binary-safe)
    thread_patches = [
        ("gum-js-loop", 11),
        ("gmain", 5),
        ("gdbus", 5),
        ("pool-frida", 10),
        ("frida-server", 12),
    ]
    
    for name, length in thread_patches:
        random_name = "".join(random.choices(random_charset, k=length))
        log_color(f"[*] Patching `{name}` -> `{random_name}`")
        ret = os.system(f"sed -i 's/{name}/{random_name}/g' '{input_file}'")
        if ret != 0:
            log_color(f"[!] sed failed for {name}")

    log_color(f"[*] Finished patching: {input_file}")

def main():
    if len(sys.argv) < 2:
        print("Usage: post_build_patch.py <build_dir>")
        print("  build_dir: path to the build output directory")
        sys.exit(1)
    
    build_dir = sys.argv[1]
    
    # Find all ELF files to patch
    targets = [
        os.path.join(build_dir, "subprojects/frida-core/server/frida-server"),
        os.path.join(build_dir, "subprojects/frida-core/inject/frida-inject"),
        os.path.join(build_dir, "subprojects/frida-core/lib/gadget/frida-gadget.so"),
    ]
    
    # Also find frida-agent*.so files
    agent_patterns = [
        os.path.join(build_dir, "**/frida-agent*.so"),
        os.path.join(build_dir, "**/frida-agent-*.so"),
    ]
    for pattern in agent_patterns:
        for f in glob.glob(pattern, recursive=True):
            if f not in targets:
                targets.append(f)
    
    log_color(f"[*] Found {len(targets)} files to patch")
    
    for target in targets:
        if os.path.exists(target):
            patch_elf(target)
        else:
            log_color(f"[!] File not found: {target}")
    
    log_color(f"\n[*] All patching complete!")

if __name__ == "__main__":
    main()
