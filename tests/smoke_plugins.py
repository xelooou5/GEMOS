# -*- coding: utf-8 -*-

---

# ðŸ“„ Script de Smoke Test

`tests/smoke_plugins.py`:

```python
#!/usr/bin/env python3
"""
Smoke test para verificar carregamento de plugins no GEM OS.
"""
import sys
from core.plugins import PluginManager

def main():
    pm = PluginManager("plugins")
    pm.load_plugins()

    print("ðŸ”Œ Plugins carregados:")
    for cmd in sorted(pm.commands.keys()):
        print(" -", cmd)

if __name__ == "__main__":
    main()
