"""The one way to traverse the IR.

The unified container model gives the IR exactly two node shapes — a text
LEAF (text + inline runs) and a CONTAINER (children) — so one recursive
walker is correct for every consumer. Before this module, render, eval,
remap and landing each hand-rolled a walker with its own depth assumptions;
"top-level plus one child" walkers are how look-in-the-wrong-node bugs and
silently-unremappable nids happen. Use these helpers instead of writing a
new loop.

Contract details live in sources/docs/ir-contract.md.
"""

import re


def walk(nodes, skip=(), prune=()):
    """Every node dict, depth-first, in reading order.

    Accepts the body list or any children list. `skip` types are neither
    yielded nor entered (their whole subtree vanishes); `prune` types are
    yielded but not entered (the node counts, its interior doesn't) —
    landing uses prune for lists/tables whose leaf paragraphs are the
    container's content, not free-standing text.
    """
    for n in nodes or []:
        if not isinstance(n, dict):
            continue
        t = n.get("type")
        if t in skip:
            continue
        yield n
        if t in prune:
            continue
        yield from walk(n.get("children"), skip, prune)


def leaves(nodes):
    """Text-bearing nodes only, at any depth."""
    for n in walk(nodes):
        if n.get("text"):
            yield n


def find(nodes, nid):
    """The node with this nid, at any depth, or None."""
    for n in walk(nodes):
        if n.get("nid") == nid:
            return n
    return None


def find_parent(nodes, nid):
    """(containing list, node) for nid — so the node can be removed from or
    replaced in its container. Returns (nodes, None) when absent."""
    for n in nodes or []:
        if not isinstance(n, dict):
            continue
        if n.get("nid") == nid:
            return nodes, n
        if n.get("children"):
            holder, hit = find_parent(n["children"], nid)
            if hit is not None:
                return holder, hit
    return nodes, None


def subtree_text(node):
    """Plain text of a node's whole subtree (leaf texts in reading order,
    space-joined). A leaf returns its own text."""
    return " ".join(n["text"] for n in walk([node]) if n.get("text"))


def of_type(nodes, *types):
    """All nodes of the given type(s), at any depth."""
    for n in walk(nodes):
        if n.get("type") in types:
            yield n


def norm_key(text, limit=None):
    """Match key for node text: lowercase alphanumerics only. The variant
    used for remap/anchor matching — NOT for nid hashing (analyze._norm_text
    owns that and must never drift, or every saved op orphans)."""
    key = re.sub(r"[^a-z0-9]+", "", (text or "").lower())
    return key[:limit] if limit else key
