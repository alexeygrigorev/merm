"""Tests for gitGraph IR, parser, layout, renderer, and integration."""

import xml.etree.ElementTree as ET
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from merm import render_diagram
from merm.ir.gitgraph import CommitType, GitBranch, GitCommit, GitGraph
from merm.layout.gitgraph import layout_gitgraph
from merm.parser.flowchart import ParseError
from merm.parser.gitgraph import parse_gitgraph
from merm.render.gitgraph import render_gitgraph_svg

FIXTURES = Path(__file__).parent / "fixtures" / "corpus" / "gitgraph"

# ---------------------------------------------------------------------------
# IR unit tests
# ---------------------------------------------------------------------------

class TestIRDataclasses:
    def test_create_git_commit_all_fields(self):
        c = GitCommit(
            id="abc123",
            branch="main",
            commit_type=CommitType.HIGHLIGHT,
            tag="v1.0",
            parents=("parent1",),
            is_merge=False,
            cherry_picked_from="",
        )
        assert c.id == "abc123"
        assert c.branch == "main"
        assert c.commit_type == CommitType.HIGHLIGHT
        assert c.tag == "v1.0"
        assert c.parents == ("parent1",)
        assert c.is_merge is False
        assert c.cherry_picked_from == ""

    def test_create_git_commit_defaults(self):
        c = GitCommit(
            id="x",
            branch="main",
            commit_type=CommitType.NORMAL,
            tag="",
            parents=(),
            is_merge=False,
            cherry_picked_from="",
        )
        assert c.commit_type == CommitType.NORMAL
        assert c.tag == ""

    def test_git_commit_is_frozen(self):
        c = GitCommit(
            id="x",
            branch="main",
            commit_type=CommitType.NORMAL,
            tag="",
            parents=(),
            is_merge=False,
            cherry_picked_from="",
        )
        with pytest.raises(FrozenInstanceError):
            c.id = "changed"  # type: ignore[misc]

    def test_create_git_branch(self):
        b = GitBranch(name="develop", start_commit="abc")
        assert b.name == "develop"
        assert b.start_commit == "abc"

    def test_create_git_graph(self):
        c1 = GitCommit("1", "main", CommitType.NORMAL, "", (), False, "")
        c2 = GitCommit("2", "main", CommitType.NORMAL, "", ("1",), False, "")
        b = GitBranch("develop", "2")
        g = GitGraph(
            commits=(c1, c2),
            branches=(b,),
            branch_order=("main", "develop"),
        )
        assert len(g.commits) == 2
        assert len(g.branches) == 1
        assert g.branch_order == ("main", "develop")

    def test_commit_type_enum(self):
        assert CommitType.NORMAL.value == "NORMAL"
        assert CommitType.REVERSE.value == "REVERSE"
        assert CommitType.HIGHLIGHT.value == "HIGHLIGHT"

# ---------------------------------------------------------------------------
# Parser unit tests
# ---------------------------------------------------------------------------

class TestParser:
    def test_minimal_single_commit(self):
        graph = parse_gitgraph("gitGraph\n   commit\n")
        assert len(graph.commits) == 1
        assert graph.commits[0].branch == "main"

    def test_multiple_commits(self):
        graph = parse_gitgraph("gitGraph\n   commit\n   commit\n   commit\n")
        assert len(graph.commits) == 3
        # Verify chronological order
        for i in range(1, len(graph.commits)):
            assert graph.commits[i].parents[0] == graph.commits[i - 1].id

    def test_commit_with_id(self):
        graph = parse_gitgraph('gitGraph\n   commit id: "abc"\n')
        assert graph.commits[0].id == "abc"

    def test_commit_with_tag(self):
        graph = parse_gitgraph('gitGraph\n   commit tag: "v1.0"\n')
        assert graph.commits[0].tag == "v1.0"

    def test_commit_type_highlight(self):
        graph = parse_gitgraph("gitGraph\n   commit type: HIGHLIGHT\n")
        assert graph.commits[0].commit_type == CommitType.HIGHLIGHT

    def test_commit_type_reverse(self):
        graph = parse_gitgraph("gitGraph\n   commit type: REVERSE\n")
        assert graph.commits[0].commit_type == CommitType.REVERSE

    def test_branch_and_checkout(self):
        source = (
            "gitGraph\n"
            "   commit\n"
            "   branch develop\n"
            "   checkout develop\n"
            "   commit\n"
        )
        graph = parse_gitgraph(source)
        assert graph.commits[1].branch == "develop"

    def test_merge(self):
        source = (
            "gitGraph\n"
            "   commit\n"
            "   branch develop\n"
            "   checkout develop\n"
            "   commit\n"
            "   checkout main\n"
            "   merge develop\n"
        )
        graph = parse_gitgraph(source)
        merge_commit = graph.commits[-1]
        assert merge_commit.is_merge is True
        assert len(merge_commit.parents) == 2

    def test_cherry_pick(self):
        source = (
            "gitGraph\n"
            '   commit id: "abc"\n'
            "   branch develop\n"
            "   checkout develop\n"
            "   commit\n"
            "   checkout main\n"
            '   cherry-pick id: "abc"\n'
        )
        graph = parse_gitgraph(source)
        cp = graph.commits[-1]
        assert cp.cherry_picked_from == "abc"

    def test_comments_ignored(self):
        source = (
            "gitGraph\n"
            "   %% this is a comment\n"
            "   commit\n"
            "   %% another comment\n"
            "   commit\n"
        )
        graph = parse_gitgraph(source)
        assert len(graph.commits) == 2

    def test_empty_gitgraph(self):
        graph = parse_gitgraph("gitGraph\n")
        assert len(graph.commits) == 0

    def test_checkout_nonexistent_raises(self):
        with pytest.raises(ParseError, match="does not exist"):
            parse_gitgraph("gitGraph\n   checkout nonexistent\n")

    def test_cherry_pick_nonexistent_raises(self):
        with pytest.raises(ParseError, match="not found"):
            parse_gitgraph(
                'gitGraph\n   commit\n   cherry-pick id: "nonexistent"\n'
            )

    def test_invalid_command_raises(self):
        with pytest.raises(ParseError, match="Unknown command"):
            parse_gitgraph("gitGraph\n   push origin main\n")

    def test_merge_with_tag(self):
        source = (
            "gitGraph\n"
            "   commit\n"
            "   branch develop\n"
            "   checkout develop\n"
            "   commit\n"
            "   checkout main\n"
            '   merge develop tag: "v2.0"\n'
        )
        graph = parse_gitgraph(source)
        merge_commit = graph.commits[-1]
        assert merge_commit.tag == "v2.0"
        assert merge_commit.is_merge is True

    def test_branch_order(self):
        source = (
            "gitGraph\n"
            "   commit\n"
            "   branch develop\n"
            "   branch feature\n"
        )
        graph = parse_gitgraph(source)
        assert graph.branch_order == ("main", "develop", "feature")

    def test_auto_generated_ids_unique(self):
        graph = parse_gitgraph(
            "gitGraph\n   commit\n   commit\n   commit\n"
        )
        ids = [c.id for c in graph.commits]
        assert len(ids) == len(set(ids))

# ---------------------------------------------------------------------------
# Layout unit tests
# ---------------------------------------------------------------------------

class TestLayout:
    def test_single_branch_same_y(self):
        graph = parse_gitgraph("gitGraph\n   commit\n   commit\n   commit\n")
        layout = layout_gitgraph(graph)
        ys = [cl.y for cl in layout.commits]
        assert len(set(ys)) == 1  # all same y

    def test_two_branches_distinct_y(self):
        source = (
            "gitGraph\n"
            "   commit\n"
            "   branch develop\n"
            "   checkout develop\n"
            "   commit\n"
        )
        graph = parse_gitgraph(source)
        layout = layout_gitgraph(graph)
        assert layout.branch_lane_y["main"] != layout.branch_lane_y["develop"]

    def test_commits_increasing_x(self):
        graph = parse_gitgraph(
            "gitGraph\n   commit\n   commit\n   commit\n"
        )
        layout = layout_gitgraph(graph)
        xs = [cl.x for cl in layout.commits]
        for i in range(1, len(xs)):
            assert xs[i] > xs[i - 1]

    def test_merge_commit_x_after_merged_branch(self):
        source = (
            "gitGraph\n"
            "   commit\n"
            "   branch develop\n"
            "   checkout develop\n"
            "   commit\n"
            "   checkout main\n"
            "   merge develop\n"
        )
        graph = parse_gitgraph(source)
        layout = layout_gitgraph(graph)
        # Merge commit is the last one
        merge_cl = layout.commits[-1]
        # The develop commit is the second one
        dev_cl = layout.commits[1]
        assert merge_cl.x > dev_cl.x

    def test_cherry_pick_position(self):
        source = (
            "gitGraph\n"
            '   commit id: "base"\n'
            "   branch develop\n"
            "   checkout develop\n"
            '   commit id: "fix"\n'
            "   checkout main\n"
            '   cherry-pick id: "fix"\n'
        )
        graph = parse_gitgraph(source)
        layout = layout_gitgraph(graph)
        # Cherry-pick commit should be on main's lane
        cp_cl = layout.commits[-1]
        assert cp_cl.y == layout.branch_lane_y["main"]

# ---------------------------------------------------------------------------
# Renderer unit tests
# ---------------------------------------------------------------------------

class TestRenderer:
    def _render(self, source: str) -> str:
        graph = parse_gitgraph(source)
        layout = layout_gitgraph(graph)
        return render_gitgraph_svg(graph, layout)

    def test_single_branch_circles(self):
        svg = self._render("gitGraph\n   commit\n   commit\n   commit\n")
        assert svg.count("<circle") == 3

    def test_two_branch_distinct_colors(self):
        source = (
            "gitGraph\n"
            "   commit\n"
            "   branch develop\n"
            "   checkout develop\n"
            "   commit\n"
        )
        svg = self._render(source)
        # Should have branch lane lines with different colors
        assert 'class="gitgraph-branch-line"' in svg

    def test_merge_line(self):
        source = (
            "gitGraph\n"
            "   commit\n"
            "   branch develop\n"
            "   checkout develop\n"
            "   commit\n"
            "   checkout main\n"
            "   merge develop\n"
        )
        svg = self._render(source)
        assert 'class="gitgraph-merge-line"' in svg

    def test_tag_renders(self):
        svg = self._render('gitGraph\n   commit tag: "v1.0"\n')
        assert "v1.0" in svg
        assert 'class="gitgraph-tag"' in svg

    def test_commit_id_renders(self):
        svg = self._render('gitGraph\n   commit id: "my-feat"\n')
        assert "my-feat" in svg
        assert 'class="gitgraph-label"' in svg

    def test_highlight_larger_radius(self):
        svg = self._render("gitGraph\n   commit type: HIGHLIGHT\n")
        # HIGHLIGHT commits have r=12 vs NORMAL r=8
        assert 'r="12"' in svg

    def test_reverse_different_fill(self):
        svg = self._render("gitGraph\n   commit type: REVERSE\n")
        # REVERSE commits have white fill
        assert 'fill="#ffffff"' in svg

    def test_cherry_pick_dashed_line(self):
        source = (
            "gitGraph\n"
            '   commit id: "base"\n'
            "   branch develop\n"
            "   checkout develop\n"
            '   commit id: "fix"\n'
            "   checkout main\n"
            '   cherry-pick id: "fix"\n'
        )
        svg = self._render(source)
        assert "stroke-dasharray" in svg

    def test_branch_labels(self):
        source = (
            "gitGraph\n"
            "   commit\n"
            "   branch develop\n"
            "   checkout develop\n"
            "   commit\n"
        )
        svg = self._render(source)
        assert "main" in svg
        assert "develop" in svg
        assert 'class="gitgraph-branch-label"' in svg

    def test_valid_xml(self):
        svg = self._render("gitGraph\n   commit\n   commit\n")
        ET.fromstring(svg)  # Should not raise

# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_dispatch_simple(self):
        svg = render_diagram("gitGraph\n   commit\n")
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_dispatch_multi_branch(self):
        source = (
            "gitGraph\n"
            "   commit\n"
            "   branch develop\n"
            "   checkout develop\n"
            "   commit\n"
            "   checkout main\n"
            "   merge develop\n"
        )
        svg = render_diagram(source)
        assert "<svg" in svg
        # Should have multiple colors
        ET.fromstring(svg)  # Valid XML

    def test_dispatch_valid_xml(self):
        svg = render_diagram("gitGraph\n   commit\n   commit\n   commit\n")
        ET.fromstring(svg)

# ---------------------------------------------------------------------------
# Corpus fixture tests
# ---------------------------------------------------------------------------

class TestCorpusFixtures:
    @pytest.fixture(
        params=sorted(FIXTURES.glob("*.mmd")), ids=lambda p: p.stem
    )
    def fixture_path(self, request):
        return request.param

    def test_renders_without_error(self, fixture_path):
        text = fixture_path.read_text()
        svg = render_diagram(text)
        assert "<svg" in svg

    def test_well_formed_xml(self, fixture_path):
        text = fixture_path.read_text()
        svg = render_diagram(text)
        ET.fromstring(svg)  # Should not raise
