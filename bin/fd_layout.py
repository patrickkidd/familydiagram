"""
Recursive subtree layout algorithm for Bowen family diagrams.

Input: list of person dicts with keys:
  id, gender, size, partners (list of ids), parent_a (id), parent_b (id)

Output: dict mapping person_id -> (x, y)

All spacing is proportional to person symbol size. For size=5 (125px):
  Generation gap: ~219px  (1.75 × size)
  Partner spacing: ~200px  (1.6 × size, center-to-center)
  Sibling gap: max(0.5 × size, label_width + 20px) — label-aware
  Between-subtree gap: ~125px (1.0 × size)
"""

SIZE_PX = {1: 8, 2: 16, 3: 40, 4: 80, 5: 125}
DEFAULT_SIZE = 125

GEN_GAP_FACTOR = 1.75
PARTNER_FACTOR = 1.6       # center-to-center spacing as multiple of avg size
SIBLING_GAP_FACTOR = 0.5   # minimum edge-to-edge gap between siblings (label-aware override may be larger)
SUBTREE_GAP_FACTOR = 1.0   # gap between independent subtrees
PAIR_BOND_BEYOND = 0.75    # how far parents extend past outermost child (as multiple of avg parent size)
LABEL_CHAR_WIDTH = 0.6     # char width as fraction of font height
LABEL_BUFFER = 20          # extra buffer after label end
R_SIBLING_EXTRA = 60       # extra gap when an R symbol exists between adjacent siblings


def _px(person):
    return SIZE_PX.get(person.get("size", 5), DEFAULT_SIZE) if person else DEFAULT_SIZE


def _label_px(person):
    """
    Minimum edge-to-edge gap so this person's Qt label clears the next sibling's symbol.

    Qt label starts at (0.7 * sz) from symbol center (PERSON_RECT.topRight + 0.2*width offset).
    Symbol edge is at (0.5 * sz). So minimum gap = 0.2*sz + label_text_width.
    Font: 26pt (~35px) for size>4, 16pt (~21px) otherwise.
    """
    if not person:
        return 0
    name = person.get("name") or ""
    if not name:
        return 0
    sz = _px(person)
    font_px = 35 if sz > 100 else 21
    label_text_w = int(len(name) * font_px * LABEL_CHAR_WIDTH) + LABEL_BUFFER
    return int(0.2 * sz) + label_text_w


def _sibling_gap(by_id, left_id, right_id, r_pairs=None):
    """Minimum edge-to-edge gap so left sibling's label (and any R symbol) clears the right sibling."""
    left = by_id.get(left_id)
    right = by_id.get(right_id)
    lsz = _px(left) if left else DEFAULT_SIZE
    rsz = _px(right) if right else DEFAULT_SIZE
    size_gap = max(lsz, rsz) * SIBLING_GAP_FACTOR
    label_gap = _label_px(left) if left else 0
    gap = max(size_gap, label_gap)
    if r_pairs and frozenset([left_id, right_id]) in r_pairs:
        gap = max(gap, label_gap + R_SIBLING_EXTRA)
    return gap


def _children_of(by_id, pa_id, pb_id):
    """People whose parent_a/parent_b matches this couple (order-independent)."""
    couple = frozenset([pa_id, pb_id])
    return [
        p["id"]
        for p in by_id.values()
        if frozenset([p.get("parent_a"), p.get("parent_b")]) == couple
    ]


def _sort_children(by_id, child_ids):
    def key(cid):
        p = by_id.get(cid, {})
        return (p.get("birth_date") or "", cid)
    return sorted(child_ids, key=key)


def _subtree_width(by_id, pid, placed, depth=0, r_pairs=None):
    """Minimum horizontal width needed to lay out pid's subtree."""
    if depth > 25 or pid not in by_id:
        return _px(by_id.get(pid))

    p = by_id[pid]
    sz = _px(p)

    has_parents = lambda qid: bool(
        by_id.get(qid, {}).get("parent_a") or by_id.get(qid, {}).get("parent_b")
    )
    partner_family_placed = lambda qid: not has_parents(qid) or any(
        par in placed
        for par in [by_id.get(qid, {}).get("parent_a"), by_id.get(qid, {}).get("parent_b")]
        if par
    )
    partner_ids = [qid for qid in (p.get("partners") or []) if qid in by_id]
    primary_partner = next(
        (qid for qid in partner_ids if qid not in placed and not has_parents(qid)),
        next(
            (qid for qid in partner_ids if qid not in placed and partner_family_placed(qid)),
            None,
        ),
    )

    if primary_partner:
        pp = by_id.get(primary_partner)
        psz = _px(pp) if pp else DEFAULT_SIZE
        spacing = max(sz, psz) * PARTNER_FACTOR
        couple_width = sz / 2 + spacing + psz / 2
        children = _sort_children(by_id, _children_of(by_id, pid, primary_partner))
    else:
        couple_width = sz + max(0, _label_px(p) - LABEL_BUFFER)
        children = []

    if not children:
        primary_width = couple_width
    else:
        child_widths = [_subtree_width(by_id, c, placed, depth + 1, r_pairs) for c in children]
        total_gap = sum(
            _sibling_gap(by_id, children[i], children[i + 1], r_pairs)
            for i in range(len(children) - 1)
        )
        children_width = sum(child_widths) + total_gap

        # The rightmost child's label may extend beyond the subtree's right edge.
        rightmost = by_id.get(children[-1])
        if rightmost:
            rc_w = child_widths[-1]
            label_end = _label_px(rightmost) - LABEL_BUFFER + _px(rightmost) / 2
            overhang = max(0, label_end - rc_w / 2)
            children_width += overhang

        primary_width = max(couple_width, children_width)

    # Secondary partners with children create lateral extensions to the left.
    # Skip partners whose family is already placed (they place themselves laterally
    # when their subtree processes; no reservation needed here).
    max_lateral = 0
    for qid in partner_ids:
        if qid == primary_partner or qid in placed:
            continue
        qp = by_id.get(qid, {})
        q_pa, q_pb = qp.get("parent_a"), qp.get("parent_b")
        if (q_pa and q_pa in placed) or (q_pb and q_pb in placed):
            continue  # partner's family already laid out; lateral slot already claimed
        sec_children = _children_of(by_id, pid, qid)
        if not sec_children:
            continue
        qsz = _px(qp) if qp else DEFAULT_SIZE
        sec_spacing = max(sz, qsz) * PARTNER_FACTOR
        sec_w = sum(
            _subtree_width(by_id, c, placed, depth + 1, r_pairs) for c in sec_children
        )
        # Secondary couple center is ~sec_spacing/2 to the left of pid;
        # children span sec_w symmetrically around that center.
        max_lateral = max(max_lateral, sec_spacing / 2 + sec_w / 2)

    return max(primary_width, 2 * max_lateral)


def _compute_y_levels(by_id):
    """
    Propagate Y-level constraints until stable:
      - child.y >= parent.y + (parent_size + child_size)/2 * GEN_GAP_FACTOR  (INV-4)
      - spouse.y == partner.y                                                  (INV-2)
    """
    y = {pid: 0 for pid in by_id}
    changed = True
    iters = 0
    while changed and iters < 200:
        changed = False
        iters += 1
        for pid, p in by_id.items():
            child_sz = _px(p)
            for par in [p.get("parent_a"), p.get("parent_b")]:
                if par and par in y:
                    gap = (_px(by_id[par]) + child_sz) / 2 * GEN_GAP_FACTOR
                    need = y[par] + gap
                    if y[pid] < need:
                        y[pid] = need
                        changed = True
            for partner in (p.get("partners") or []):
                if partner in y and y[partner] > y[pid]:
                    y[pid] = y[partner]
                    changed = True
                elif partner in y and y[pid] > y[partner]:
                    y[partner] = y[pid]
                    changed = True
    return y


R_SYMBOL_FACTOR = 1.4  # extra pair-bond width multiplier for couples with R symbols


def layout(people, r_pairs=None):
    """
    Compute (x, y) positions for all people.
    Returns dict: person_id -> (x, y)

    r_pairs: optional set of frozenset({id_a, id_b}) for couples with relationship symbols.
    """
    by_id = {p["id"]: p for p in people}
    r_pairs = r_pairs or set()
    positions = {}
    placed = set()

    y_levels = _compute_y_levels(by_id)

    # Forward-declared; populated after root_entries is built so closures see it.
    coupled_roots: set = set()

    def place_couple(pa_id, pb_id, cx):
        """
        Place a couple centered at cx using precomputed y_levels, then
        recursively place their children.
        If both are already placed, still places children under the actual centre.
        If one is already placed, places the other adjacent at the placed one's x.
        """
        pa = by_id.get(pa_id)
        pb = by_id.get(pb_id)
        if not pa or not pb:
            return

        sa, sb = _px(pa), _px(pb)
        factor = PARTNER_FACTOR * R_SYMBOL_FACTOR if frozenset([pa_id, pb_id]) in r_pairs else PARTNER_FACTOR
        spacing = max(sa, sb) * factor

        # Male left of female (SOFT-2)
        left_id, right_id = pa_id, pb_id
        if pa.get("gender") == "female" and pb.get("gender") == "male":
            left_id, right_id = pb_id, pa_id

        # Label-aware minimum: left person's label must clear right person's symbol.
        left_p, right_p = by_id.get(left_id), by_id.get(right_id)
        if left_p and right_p:
            label_min = _px(left_p) / 2 + _label_px(left_p) + _px(right_p) / 2
            spacing = max(spacing, label_min)

        # Pre-compute children span to expand the pair-bond to encompass children.
        children = _sort_children(by_id, _children_of(by_id, pa_id, pb_id))
        if children:
            child_widths = [_subtree_width(by_id, c, placed, r_pairs=r_pairs) for c in children]
            gaps = [
                _sibling_gap(by_id, children[i], children[i + 1], r_pairs)
                for i in range(len(children) - 1)
            ]
            total = sum(child_widths) + sum(gaps)
            children_span = total - child_widths[0] / 2 - child_widths[-1] / 2
            beyond = max(sa, sb) * PAIR_BOND_BEYOND
            effective_spacing = max(spacing, children_span + beyond)
        else:
            child_widths = []
            gaps = []
            total = 0
            effective_spacing = spacing

        def _push_clear_same_y(new_id, new_y, go_right):
            """Push new_id past same-y symbol conflicts; skips if the push would land in q's label."""
            new_sz = _px(by_id.get(new_id))
            new_x = positions[new_id][0]
            conflicts = sorted(
                [q for q in placed if q != new_id and q in positions and abs(positions[q][1] - new_y) <= 5],
                key=lambda q: positions[q][0],
                reverse=not go_right,
            )
            for qid in conflicts:
                qx = positions[qid][0]
                q_sz = _px(by_id.get(qid))
                sym_ov = min(new_x + new_sz / 2, qx + q_sz / 2) - max(new_x - new_sz / 2, qx - q_sz / 2)
                if sym_ov > 0:
                    if go_right:
                        # Skip if q's label would overlap new_id's symbol after the push.
                        q_lbl = _label_px(by_id.get(qid))
                        if min(new_sz, q_lbl) - 0.2 * q_sz > LABEL_BUFFER:
                            continue
                        new_x = qx + q_sz / 2 + new_sz / 2
                    else:
                        new_x = qx - q_sz / 2 - new_sz / 2
            positions[new_id] = (new_x, new_y)

        if pa_id in placed and pb_id in placed:
            actual_cx = (positions[pa_id][0] + positions[pb_id][0]) / 2
            actual_y = max(positions[pa_id][1], positions[pb_id][1])
        elif pa_id in placed:
            pa_pos = positions[pa_id]
            go_right = (pa_id == left_id)
            if go_right:
                positions[pb_id] = (pa_pos[0] + effective_spacing, y_levels[pb_id])
            else:
                positions[pb_id] = (pa_pos[0] - effective_spacing, y_levels[pb_id])
            placed.add(pb_id)
            _push_clear_same_y(pb_id, y_levels[pb_id], go_right)
            actual_cx = (positions[pa_id][0] + positions[pb_id][0]) / 2
            actual_y = max(pa_pos[1], y_levels[pb_id])
        elif pb_id in placed:
            pb_pos = positions[pb_id]
            go_right = (pb_id == left_id)
            if pb_id == right_id:
                positions[pa_id] = (pb_pos[0] - effective_spacing, y_levels[pa_id])
            else:
                positions[pa_id] = (pb_pos[0] + effective_spacing, y_levels[pa_id])
            placed.add(pa_id)
            _push_clear_same_y(pa_id, y_levels[pa_id], go_right)
            actual_cx = (positions[pa_id][0] + positions[pb_id][0]) / 2
            actual_y = max(y_levels[pa_id], pb_pos[1])
        else:
            positions[left_id] = (cx - effective_spacing / 2, y_levels[left_id])
            positions[right_id] = (cx + effective_spacing / 2, y_levels[right_id])
            placed.add(pa_id)
            placed.add(pb_id)
            actual_cx = cx
            actual_y = y_levels[pa_id]  # spouses always same level after propagation

        if not children:
            return

        # Push children away from already-placed half-siblings at the same y level.
        if total > 0:
            child_y = y_levels.get(children[0])
            if child_y is not None:
                def _is_halfsib(cid):
                    if cid in children or cid not in positions:
                        return False
                    if abs(positions[cid][1] - child_y) > 5:
                        return False
                    p = by_id.get(cid, {})
                    return p.get("parent_a") in (pa_id, pb_id) or p.get("parent_b") in (pa_id, pb_id)
                halfsiblings = sorted([c for c in placed if _is_halfsib(c)], key=lambda c: positions[c][0])
                if halfsiblings:
                    hs_right = [c for c in halfsiblings if positions[c][0] > actual_cx]
                    hs_left  = [c for c in halfsiblings if positions[c][0] <= actual_cx]
                    if hs_right:
                        hs_first = hs_right[0]
                        gap = _sibling_gap(by_id, children[-1], hs_first, r_pairs)
                        max_right = positions[hs_first][0] - _px(by_id[hs_first]) / 2 - gap
                        if actual_cx + total / 2 > max_right:
                            actual_cx = max_right - total / 2
                    if hs_left:
                        hs_last = hs_left[-1]
                        gap = _sibling_gap(by_id, hs_last, children[0], r_pairs)
                        min_left = positions[hs_last][0] + _px(by_id[hs_last]) / 2 + gap
                        if actual_cx - total / 2 < min_left:
                            actual_cx = min_left + total / 2

        child_xs = []
        start_x = actual_cx - total / 2
        for i, w in enumerate(child_widths):
            child_xs.append(start_x + w / 2)
            start_x += w + (gaps[i] if i < len(gaps) else 0)

        for i, cid in enumerate(children):
            placed_before = set(placed)
            place_person(cid, child_xs[i])
            child_y = y_levels.get(cid)
            newly_placed = placed - placed_before
            if child_y is not None and newly_placed:
                # Check A: newly placed person's label extends past next sibling's allocated slot.
                if i < len(children) - 1:
                    next_sz = _px(by_id.get(children[i + 1]))
                    min_next_cx = child_xs[i + 1]
                    for qid in newly_placed:
                        if qid not in positions or qid == cid:
                            continue
                        qx, qy = positions[qid]
                        if abs(qy - child_y) > 5:
                            continue
                        q_lbl_end = qx + _px(by_id.get(qid)) / 2 + _label_px(by_id.get(qid))
                        needed = q_lbl_end + next_sz / 2
                        if needed > min_next_cx:
                            min_next_cx = needed
                    if min_next_cx > child_xs[i + 1]:
                        diff = min_next_cx - child_xs[i + 1]
                        for j in range(i + 1, len(child_xs)):
                            child_xs[j] += diff

    def place_person(pid, cx):
        """Place a person (and their partner if any) centered at cx."""
        if pid in placed:
            return
        p = by_id.get(pid)
        if not p:
            return

        partner_ids = [qid for qid in (p.get("partners") or []) if qid in by_id]

        # Prefer TC-4 anchors (roots with multiple root-partners) when selecting
        # which unplaced partner to form a couple with.
        def _tc4_priority(qid):
            q = by_id[qid]
            if q.get("parent_a") or q.get("parent_b"):
                return 0
            return sum(
                1 for p2 in (q.get("partners") or [])
                if p2 in by_id
                and p2 != pid
                and not by_id[p2].get("parent_a")
                and not by_id[p2].get("parent_b")
            ) + 1

        def _parent_placed(qid):
            """True if qid is a root OR at least one of its parents is placed."""
            q = by_id.get(qid, {})
            pa, pb = q.get("parent_a"), q.get("parent_b")
            if not pa and not pb:
                return True
            return (pa and pa in placed) or (pb and pb in placed)

        unplaced = sorted(
            [
                qid for qid in partner_ids
                if qid not in placed and qid not in coupled_roots and _parent_placed(qid)
            ],
            key=_tc4_priority,
            reverse=True,
        )

        def _is_cross_family(qid):
            """True if pid and qid have parents from different families."""
            q = by_id.get(qid, {})
            q_pa, q_pb = q.get("parent_a"), q.get("parent_b")
            p_pa, p_pb = p.get("parent_a"), p.get("parent_b")
            if not (p_pa or p_pb) or not (q_pa or q_pb):
                return False
            return frozenset([p_pa, p_pb]) != frozenset([q_pa, q_pb])

        primary_partner = None
        if unplaced:
            primary_partner = unplaced[0]
            place_couple(pid, primary_partner, cx)
        elif partner_ids:
            # All partners already placed — place this person adjacent to the
            # first placed partner, choosing the side with more free space.
            first_placed = next((q for q in partner_ids if q in positions), None)
            if first_placed:
                primary_partner = first_placed
                if _is_cross_family(first_placed):
                    # Cross-family: stay in own subtree position; children placed
                    # at the midpoint by place_couple below.
                    positions[pid] = (cx, y_levels[pid])
                else:
                    qpos = positions[first_placed]
                    qsz = _px(by_id[first_placed])
                    sz = _px(p)
                    spacing = max(sz, qsz) * PARTNER_FACTOR
                    # Same label-aware minimum as place_couple: label must clear partner symbol.
                    lbl_p = _label_px(p)
                    lbl_q = _label_px(by_id[first_placed])
                    spacing = max(spacing, sz / 2 + lbl_p + qsz / 2, qsz / 2 + lbl_q + sz / 2)
                    right_x = qpos[0] + spacing
                    left_x = qpos[0] - spacing
                    # Place on the side AWAY from the spouse's parents (outer side).
                    q = by_id[first_placed]
                    parent_xs = [
                        positions[par][0]
                        for par in [q.get("parent_a"), q.get("parent_b")]
                        if par and par in positions
                    ]
                    def _same_row(other):
                        return (
                            other != first_placed
                            and abs(positions[other][1] - qpos[1]) < sz
                        )
                    def _side_taken(candidate_x):
                        return any(
                            abs(positions[other][0] - candidate_x) < spacing * 0.8
                            for other in placed if _same_row(other)
                        )
                    right_free = not _side_taken(right_x)
                    left_free = not _side_taken(left_x)
                    if parent_xs:
                        preferred_right = sum(parent_xs) / len(parent_xs) <= qpos[0]
                        if preferred_right:
                            go_right = right_free or not left_free
                        else:
                            go_right = not left_free and right_free
                    else:
                        go_right = right_free or not left_free
                    if right_free or left_free:
                        target_x = right_x if go_right else left_x
                    else:
                        # Both immediate slots taken; cascade outward on preferred side.
                        if go_right:
                            occupied = [
                                positions[o][0] for o in placed if _same_row(o)
                                and positions[o][0] > qpos[0]
                            ]
                            target_x = (max(occupied) + spacing) if occupied else right_x
                        else:
                            occupied = [
                                positions[o][0] for o in placed if _same_row(o)
                                and positions[o][0] < qpos[0]
                            ]
                            target_x = (min(occupied) - spacing) if occupied else left_x
                    positions[pid] = (target_x, y_levels[pid])
                placed.add(pid)
                place_couple(pid, first_placed, 0)  # cx ignored — both placed
            else:
                positions[pid] = (cx, y_levels[pid])
                placed.add(pid)
        else:
            positions[pid] = (cx, y_levels[pid])
            placed.add(pid)

        # Trigger child placement for any additional placed partners (multiple marriages).
        # The primary couple was handled above; remaining placed partners' children
        # would otherwise be missed and fall through to the fallback placer.
        if pid in placed and primary_partner is not None:
            for qid in partner_ids:
                if qid in placed and qid != primary_partner:
                    place_couple(pid, qid, 0)

    # Identify root people (no parents in diagram)
    has_parents = {
        p["id"]
        for p in by_id.values()
        if p.get("parent_a") or p.get("parent_b")
    }
    roots = [p for p in by_id.values() if p["id"] not in has_parents]
    root_ids = {p["id"] for p in roots}

    def _has_nonroot_partner(rid):
        return any(
            by_id.get(qid, {}).get("parent_a") or by_id.get(qid, {}).get("parent_b")
            for qid in (by_id.get(rid, {}).get("partners") or [])
        )

    # Pre-collect root couples and singles
    root_entries = []
    paired_collect = set()
    for root in roots:
        if root["id"] in paired_collect:
            continue
        partner_ids = [
            qid for qid in (root.get("partners") or [])
            if qid in by_id and qid in root_ids and qid not in paired_collect
        ]
        if partner_ids:
            partner_id = partner_ids[0]
            paired_collect.add(root["id"])
            paired_collect.add(partner_id)
            root_entries.append((root, partner_id))
        else:
            paired_collect.add(root["id"])
            root_entries.append((root, None))

    # Sort root_entries: TC-4 couples (any member with a non-root partner) come last.
    def _tc4_score(entry):
        r, pid = entry
        score = int(_has_nonroot_partner(r["id"]))
        if pid is not None:
            score += int(_has_nonroot_partner(pid))
        return score

    root_entries.sort(key=_tc4_score)

    # coupled_roots: root IDs reserved for root-root couple placement.
    # Exclude TC-4 anchors (roots with non-root partners) so they can be freely
    # placed by their non-root partner's subtree.
    coupled_roots.update(
        rid
        for r, pid in root_entries
        if pid is not None
        for rid in (r["id"], pid)
        if not _has_nonroot_partner(rid)
    )

    def _placed_children_of_couple(pa_id, pb_id):
        return [c for c in _children_of(by_id, pa_id, pb_id) if c in positions]

    def _placed_children_of_person(pid):
        return [
            p["id"] for p in by_id.values()
            if (p.get("parent_a") == pid or p.get("parent_b") == pid)
            and p["id"] in positions
        ]

    def _should_defer_root(root, partner_id):
        """
        True if this root should be skipped in Pass 1 because all of its
        non-root partners have parents in the diagram. These roots will be
        placed when their partner's parent subtree calls place_person.
        """
        if partner_id:
            return False
        non_root_unplaced = [
            qid for qid in (root.get("partners") or [])
            if qid in by_id and qid not in placed and qid not in root_ids
        ]
        return bool(non_root_unplaced) and all(
            by_id[qid].get("parent_a") or by_id[qid].get("parent_b")
            for qid in non_root_unplaced
        )

    current_x = 0
    paired = set()

    def _process_root(root, partner_id):
        nonlocal current_x

        if partner_id:
            root_placed = root["id"] in placed
            partner_placed = partner_id in placed

            if root_placed and not partner_placed:
                place_couple(root["id"], partner_id, 0)
                return
            if root_placed and partner_placed:
                place_couple(root["id"], partner_id, 0)
                return

            children_placed = _placed_children_of_couple(root["id"], partner_id)
            if children_placed:
                # Phase 3: anchor X above already-placed children; Y from y_levels.
                cx = sum(positions[c][0] for c in children_placed) / len(children_placed)
                place_couple(root["id"], partner_id, cx)
            else:
                w = max(
                    _subtree_width(by_id, root["id"], placed, r_pairs=r_pairs),
                    _subtree_width(by_id, partner_id, placed, r_pairs=r_pairs),
                )
                cx = current_x + w / 2
                place_couple(root["id"], partner_id, cx)
                current_x += w + DEFAULT_SIZE * SUBTREE_GAP_FACTOR
        else:
            if root["id"] in placed:
                place_person(root["id"], 0)  # already placed — returns immediately
                return

            children_placed = _placed_children_of_person(root["id"])
            if children_placed:
                cx = sum(positions[c][0] for c in children_placed) / len(children_placed)
                place_person(root["id"], cx)
            else:
                w = _subtree_width(by_id, root["id"], placed, r_pairs=r_pairs)
                cx = current_x + w / 2
                place_person(root["id"], cx)
                current_x += w + DEFAULT_SIZE * SUBTREE_GAP_FACTOR

    # Pass 1: subtrees with no pre-placed children.
    for root, partner_id in root_entries:
        if root["id"] in placed:
            continue
        if _should_defer_root(root, partner_id):
            continue
        if partner_id:
            kids = _placed_children_of_couple(root["id"], partner_id)
        else:
            kids = _placed_children_of_person(root["id"])
        if not kids:
            paired.add(root["id"])
            if partner_id:
                paired.add(partner_id)
            _process_root(root, partner_id)

    # Pass 2: Phase 3 — roots anchored above pre-placed children, or TC-4 roots
    # already placed adjacent to their non-root spouse.
    for root, partner_id in root_entries:
        if root["id"] in placed and (partner_id is None or partner_id in placed):
            continue
        paired.add(root["id"])
        if partner_id:
            paired.add(partner_id)
        _process_root(root, partner_id)

    # Fallback: place any remaining unplaced people
    for p in by_id.values():
        if p["id"] not in placed:
            place_person(p["id"], current_x)
            current_x += _px(p) * 2

    _sweep(by_id, positions)
    return positions


def _sweep(by_id, positions):
    """Post-placement: iteratively push subtrees right to fix label→symbol overlaps."""
    children_of = {pid: [] for pid in by_id}
    for p in by_id.values():
        for par in [p.get("parent_a"), p.get("parent_b")]:
            if par in children_of:
                children_of[par].append(p["id"])

    def _subtree(pid):
        seen, queue = set(), [pid]
        while queue:
            curr = queue.pop()
            if curr in seen:
                continue
            seen.add(curr)
            queue += by_id.get(curr, {}).get("partners") or []
            queue += children_of.get(curr, [])
        return seen

    for _ in range(20):
        changed = False
        rows = {}
        for pid, (_, y) in positions.items():
            rows.setdefault(round(y), []).append(pid)
        for y in sorted(rows):
            row = sorted(rows[y], key=lambda p: positions[p][0])
            for i in range(len(row) - 1):
                pid, qid = row[i], row[i + 1]
                p, q = by_id.get(pid), by_id.get(qid)
                if not p or not q:
                    continue
                px, qx = positions[pid][0], positions[qid][0]
                overlap = px + _px(p) / 2 + _label_px(p) - LABEL_BUFFER - (qx - _px(q) / 2)
                if overlap > 0:
                    for mid in _subtree(qid):
                        if mid in positions:
                            mx, my = positions[mid]
                            positions[mid] = (mx + overlap, my)
                    changed = True
        if not changed:
            break
