#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧮 GEM OS - Math Plugin (plugins/math_plugin.py)

Provides math expression evaluation and symbolic calculations.
Registers commands with PluginManager:
- "math:calc"
"""

from __future__ import annotations

try:
    import sympy
    from sympy.parsing.sympy_parser import parse_expr
except ImportError:
    sympy = None


def calc_expression(expr: str) -> str:
    """Evaluate a math expression safely."""
    if sympy:
        try:
            parsed = parse_expr(expr, evaluate=True)
            simplified = sympy.simplify(parsed)
            return f"🧮 {expr} = {simplified}"
        except Exception as e:
            return f"❌ Error evaluating '{expr}': {e}"
    else:
        try:
            # ⚠️ fallback (unsafe if misused, but limited here)
            result = eval(expr, {"__builtins__": {}}, {"abs": abs, "round": round})
            return f"🧮 {expr} = {result}"
        except Exception as e:
            return f"❌ Error: {e}"


def register(plugin_manager):
    """Register plugin commands."""
    plugin_manager.register_command("math:calc", calc_expression)
