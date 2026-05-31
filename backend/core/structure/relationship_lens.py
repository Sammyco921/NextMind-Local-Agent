from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Any, Dict, List, Set, Tuple

from core.structure.relationship_store import RelationshipRecord, RelationshipStore


class RelationshipLens:
    """Deterministic read-model over RelationshipStore.

    Provides:
      - file_relationships: for each file, files it co-occurred with + count
      - component_relationships: for each component, components it co-occurred with + count
      - goal_relationships: goals with overlapping file/component sets

    Purely observational — counts only, no scoring, no confidence, no dependency labels.
    """

    def __init__(self, store: RelationshipStore | None = None) -> None:
        self._store = store

    def file_relationships(self) -> List[Dict[str, Any]]:
        if self._store is None:
            return []
        cooccur: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for rec in self._store.get_all():
            files = sorted(set(rec.artifacts))
            for a, b in combinations(files, 2):
                if a != b:
                    cooccur[a][b] += 1
                    cooccur[b][a] += 1
        result: List[Dict[str, Any]] = []
        for file_path, peers in sorted(cooccur.items()):
            peer_list = [
                {"file_path": p, "cooccurrence_count": c}
                for p, c in sorted(peers.items(), key=lambda x: -x[1])
            ]
            result.append({
                "file_path": file_path,
                "observed_with": peer_list,
                "total_cooccurrences": sum(peers.values()),
            })
        result.sort(key=lambda x: -x["total_cooccurrences"])
        return result

    def component_relationships(self) -> List[Dict[str, Any]]:
        if self._store is None:
            return []
        cooccur: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for rec in self._store.get_all():
            comps = sorted(set(rec.components))
            for a, b in combinations(comps, 2):
                if a != b:
                    cooccur[a][b] += 1
                    cooccur[b][a] += 1
        result: List[Dict[str, Any]] = []
        for comp, peers in sorted(cooccur.items()):
            peer_list = [
                {"component": p, "cooccurrence_count": c}
                for p, c in sorted(peers.items(), key=lambda x: -x[1])
            ]
            result.append({
                "component": comp,
                "observed_with": peer_list,
                "total_cooccurrences": sum(peers.values()),
            })
        result.sort(key=lambda x: -x["total_cooccurrences"])
        return result

    def goal_relationships(self) -> List[Dict[str, Any]]:
        if self._store is None:
            return []
        goals = self._store.get_all()
        goal_file_sets: Dict[str, Tuple[str, Set[str], Set[str]]] = {}
        for rec in goals:
            gid = rec.goal_id
            if gid not in goal_file_sets:
                goal_file_sets[gid] = (rec.goal_description, set(), set())
            desc, files_seen, comps_seen = goal_file_sets[gid]
            goal_file_sets[gid] = (
                desc or rec.goal_description,
                files_seen | set(rec.artifacts),
                comps_seen | set(rec.components),
            )

        gids = sorted(goal_file_sets.keys())
        overlaps: List[Dict[str, Any]] = []
        for i in range(len(gids)):
            for j in range(i + 1, len(gids)):
                gid_a, gid_b = gids[i], gids[j]
                desc_a, files_a, comps_a = goal_file_sets[gid_a]
                desc_b, files_b, comps_b = goal_file_sets[gid_b]
                shared_files = files_a & files_b
                shared_comps = comps_a & comps_b
                if shared_files or shared_comps:
                    overlaps.append({
                        "goal_id_a": gid_a,
                        "goal_description_a": desc_a,
                        "goal_id_b": gid_b,
                        "goal_description_b": desc_b,
                        "shared_files": sorted(shared_files),
                        "shared_components": sorted(shared_comps),
                        "overlap_count": len(shared_files) + len(shared_comps),
                    })

        overlaps.sort(key=lambda x: -x["overlap_count"])
        return overlaps
