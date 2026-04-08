# Standard 002: Safe pikepdf Structure Tree Traversal

**Date:** 2026-04-07
**Status:** DEFINITIVE
**Components Affected:** `compliance_checker.py`

## Pain Point

When traversing the PDF structure tree (`/StructTreeRoot` → `/K` → children), pikepdf's `Array` and `Dictionary` objects behave differently from Python's native `list` and `dict`:

1. `isinstance(node, list)` returns `False` for pikepdf `Array` objects
2. `isinstance(node, dict)` returns `False` for pikepdf `Dictionary` objects
3. Calling `.get()` on an `Array` type **throws an exception** (arrays don't have a `.get()` method)
4. pikepdf objects can raise `RuntimeError` when accessed in certain contexts

This caused the compliance checker to crash mid-traversal when encountering array nodes in the structure tree.

## Root Cause

pikepdf wraps the underlying qpdf C++ library. Its `Array` and `Dictionary` types are Python wrappers around C++ objects that:
- Inherit from neither `list` nor `dict`
- Have a `.get()` method on Dictionary but NOT on Array
- Can throw exceptions on attribute access in edge cases

## Fix Applied

Added defensive helper functions that safely determine node types:

```python
from pikepdf import Array, Dictionary

def _is_array(node):
    """Safely check if a pikepdf object is an Array."""
    try:
        return isinstance(node, (Array, list))
    except Exception:
        return isinstance(node, list)

def _is_dict(node):
    """Safely check if a pikepdf object is a Dictionary."""
    try:
        return isinstance(node, (Dictionary, dict))
    except Exception:
        return hasattr(node, 'keys')
```

Every recursive tree traversal function follows this pattern:

```python
def collect_elements(node):
    if node is None:
        return
    if _is_array(node):
        for item in node:
            collect_elements(item)
        return
    if not _is_dict(node):
        return
    try:
        elem_type = node.get("/S")
    except Exception:
        return
    # ... process element
    try:
        children = node.get("/K")
    except Exception:
        return
    if children:
        collect_elements(children)
```

## Definitive Standard

**Rule 1:** ALL pikepdf node type checks MUST use `_is_array()` and `_is_dict()` helpers — never raw `isinstance()` checks.

**Rule 2:** ALL `.get()` calls on pikepdf objects MUST be wrapped in `try/except` blocks.

**Rule 3:** Recursive tree traversal functions MUST check for `None`, `Array`, and non-dict types before attempting dictionary access.

**Rule 4:** The helper functions themselves MUST be wrapped in `try/except` to handle edge cases where even `isinstance()` throws.

## Related Standards

- Standard 001 (pikepdf for catalog modifications)

## References

- `compliance_checker.py` — Contains `_is_array()`, `_is_dict()`, and all traversal functions
