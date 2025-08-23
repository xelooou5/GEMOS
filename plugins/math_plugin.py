#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ğŸ§® GEM OS - Math Plugin (plugins/math_plugin.py)

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
            return f"ğŸ§® {expr} = {simplified}"
        except Exception as e:
            return f"â�Œ Error evaluating '{expr}': {e}"
    else:
        try:
            # âš ï¸� fallback (unsafe if misused, but limited here)
            result = eval(expr, {"__builtins__": {}}, {"abs": abs, "round": round})
            return f"ğŸ§® {expr} = {result}"
        except Exception as e:
            return f"â�Œ Error: {e}"


def register(plugin_manager):
    """Register plugin commands."""
    plugin_manager.register_command("math:calc", calc_expression)
