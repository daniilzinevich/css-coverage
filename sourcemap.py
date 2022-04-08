"""Extract generated -> source mappings"""

from bisect import bisect
from collections import defaultdict
from dataclasses import dataclass, field
from functools import partial
from itertools import count
from typing import List, Literal, Mapping, Optional, Tuple, TypedDict, Union

from base64vlq import base64vlq_decode, base64vlq_encode


class autoindex(defaultdict):
    def __init__(self, *args, **kwargs):
        super().__init__(partial(next, count()), *args, **kwargs)


class JSONSourceMap(TypedDict, total=False):
    version: Literal[3]
    file: Optional[str]
    sourceRoot: Optional[str]
    sources: List[str]
    sourcesContent: Optional[List[Optional[str]]]
    names: List[str]
    mappings: str


@dataclass(frozen=True)
class SourceMapping:
    line: int
    column: int
    source: Optional[str] = None
    source_line: Optional[int] = None
    source_column: Optional[int] = None
    name: Optional[str] = None
    source_content: Optional[str] = None

    def __post_init__(self):
        if self.source is not None and (
            self.source_line is None or self.source_column is None
        ):
            raise TypeError(
                "Invalid source mapping; missing line and column for source file"
            )
        if self.name is not None and self.source is None:
            raise TypeError(
                "Invalid source mapping; name entry without source location info"
            )

    @property
    def content_line(self) -> Optional[str]:
        try:
            self.source_content.splitlines()[self.source_line]
        except (TypeError, IndexError):
            return None


@dataclass(frozen=True)
class SourceMap:
    file: Optional[str]
    source_root: Optional[str]
    entries: Mapping[Tuple[int, int], SourceMapping]
    _index: List[Tuple[int, ...]] = field(default_factory=list)

    def __repr__(self) -> str:
        parts = []
        if self.file is not None:
            parts += [f"file={self.file!r}"]
        if self.source_root is not None:
            parts += [f"source_root={self.source_root!r}"]
        parts += [f"len={len(self.entries)}"]
        return f"<SourceMap({', '.join(parts)})>"

    @classmethod
    def from_json(cls, smap: JSONSourceMap) -> "SourceMap":
        if smap["version"] != 3:
            raise ValueError("Only version 3 sourcemaps are supported")
        entries, index = {}, []
        spos = npos = sline = scol = 0
        sources, contents = (
            smap["sources"],
            smap.get("sourcesContent", []),
        )
        for gline, vlqs in enumerate(smap["mappings"].split(";")):
            index += [[]]
            if not vlqs:
                continue
            gcol = 0
            for gcd, *ref in map(base64vlq_decode, vlqs.split(",")):
                gcol += gcd
                kwargs = {}
                if len(ref) >= 3:
                    sd, sld, scd, *namedelta = ref
                    spos, sline, scol = spos + sd, sline + sld, scol + scd
                    scont = contents[spos] if len(contents) > spos else None
                    kwargs = {
                        "source": sources[spos],
                        "source_line": sline,
                        "source_column": scol,
                        "source_content": scont,
                    }
                    if namedelta:
                        npos += namedelta[0]
                entries[gline, gcol] = SourceMapping(line=gline, column=gcol, **kwargs)
                index[gline].append(gcol)

        return cls(
            smap.get("file"),
            smap.get("sourceRoot"),
            entries,
            [tuple(cs) for cs in index],
        )

    def to_json(self) -> JSONSourceMap:
        content, mappings = [], []
        sources, names = autoindex(), autoindex()
        entries = self.entries
        spos = sline = scol = npos = 0
        for gline, cols in enumerate(self._index):
            gcol = 0
            mapping = []
            for col in cols:
                entry = entries[gline, col]
                ds, gcol = [col - gcol], col

                if entry.source is not None:
                    assert entry.source_line is not None
                    assert entry.source_column is not None
                    ds += (
                        sources[entry.source] - spos,
                        entry.source_line - sline,
                        entry.source_column - scol,
                    )
                    spos, sline, scol = (spos + ds[1], sline + ds[2], scol + ds[3])
                    if spos == len(content):
                        content.append(entry.source_content)
                    if entry.name is not None:
                        ds += (names[entry.name] - npos,)
                        npos += ds[-1]
                mapping.append(base64vlq_encode(*ds))

            mappings.append(",".join(mapping))

        encoded = {
            "version": 3,
            "sources": [s for s, _ in sorted(sources.items(), key=lambda si: si[1])],
            "sourcesContent": content,
            "names": [n for n, _ in sorted(names.items(), key=lambda ni: ni[1])],
            "mappings": ";".join(mappings),
        }
        if self.file is not None:
            encoded["file"] = self.file
        if self.source_root is not None:
            encoded["sourceRoot"] = self.source_root
        return encoded

    def __getitem__(self, idx: Union[int, Tuple[int, int]]):
        try:
            l, c = idx
        except TypeError:
            l, c = idx, 0
        try:
            return self.entries[l, c]
        except KeyError:
            # find the closest column
            if not (cols := self._index[l]):
                raise IndexError(idx)
            cidx = bisect(cols, c)
            return self.entries[l, cols[cidx and cidx - 1]]
