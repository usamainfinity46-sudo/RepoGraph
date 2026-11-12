"""Bounded, evidence-backed canvas projections. No UI or MCP dependencies."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from repograph.config import Settings
from repograph.discovery import RepositoryError, normalize_relative
from repograph.git_service import GitService
from repograph.graph import GraphService
from repograph.impact import ImpactService
from repograph.models import (
    ChangeReport,
    Diagnostic,
    GraphEdge,
    GraphNode,
    ImpactReport,
    TestSuggestionReport,
    VerificationResult,
)
from repograph.scenarios import ProposedFile, ScenarioReport, prepare_preview
from repograph.service import pagination
from repograph.testing import TestIntelligence
from repograph.verification import VerificationService

BoundedText = Annotated[str, Field(max_length=2000)]


class CanvasCitation(BaseModel):
    snapshot_id: str = Field(max_length=200)
    edge_id: str = Field(max_length=200)


class CanvasExplanation(BaseModel):
    node_id: str = Field(max_length=200)
    text: str = Field(min_length=1, max_length=2000)
    citations: list[CanvasCitation] = Field(min_length=1, max_length=20)
    basis: Literal["agent_interpretation"] = "agent_interpretation"


class TourStep(BaseModel):
    title: str
    description: str
    node_ids: list[str] = Field(default_factory=list)


class CanvasRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["repository", "impact", "changes", "scenario"] = "repository"
    paths: list[BoundedText] | None = Field(default=None, max_length=200)
    node_ids: list[BoundedText] | None = Field(default=None, max_length=200)
    snapshot_id: str | None = Field(default=None, max_length=200)
    before_snapshot_id: str | None = Field(default=None, max_length=200)
    baseline: str | None = Field(default=None, max_length=1000)
    query: str = Field(default="", max_length=1000)
    offset: int = Field(default=0, ge=0, le=1_000_000)
    limit: int = Field(default=100, ge=1, le=200)
    max_depth: int = Field(default=6, ge=0, le=20)
    intent: str = Field(default="", max_length=2000)
    assumptions: list[BoundedText] = Field(default_factory=list, max_length=20)
    proposed_files: list[ProposedFile] = Field(default_factory=list, max_length=20)
    explanations: list[CanvasExplanation] = Field(default_factory=list, max_length=50)
    verification_plan_id: str | None = Field(default=None, max_length=200)


class CanvasEdge(BaseModel):
    snapshot_id: str
    edge: GraphEdge


class CanvasFolder(BaseModel):
    path: str
    files: int


class CanvasFolderLink(BaseModel):
    source: str
    target: str
    imports: int
    confidence: Literal["static", "heuristic"]


class CanvasReport(BaseModel):
    schema_version: Literal[1] = 1
    repository_name: str
    mode: Literal["repository", "impact", "changes", "scenario"]
    snapshot_ids: list[str]
    nodes: list[GraphNode]
    edges: list[CanvasEdge]
    total_nodes: int
    total_edges: int
    omitted_edges: int
    next_offset: int | None = None
    freshness: Literal["current", "stale", "unknown"] = "unknown"
    complete: bool
    view_complete: bool
    impact: ImpactReport | None = None
    changes: ChangeReport | None = None
    tests: TestSuggestionReport | None = None
    scenario: ScenarioReport | None = None
    tour: list[TourStep] = Field(default_factory=list)
    explanations: list[CanvasExplanation] = Field(default_factory=list)
    request: dict = Field(default_factory=dict)
    verification: VerificationResult | None = None
    total_files: int = 0
    folders: list[CanvasFolder] = Field(default_factory=list)
    folder_links: list[CanvasFolderLink] = Field(default_factory=list)
    total_folders: int = 0
    total_folder_links: int = 0
    unresolved_dependencies: int = 0
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    limitations: list[str] = Field(
        default_factory=lambda: [
            "Connections describe static dependencies, not observed or guaranteed effects.",
            "Unresolved and dynamic relationships may hide additional dependents.",
            "Test suggestions are not test results; no tests run when creating this canvas.",
            "This report is a saved view and does not update when source files change.",
        ]
    )


class CanvasService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.graph = GraphService(settings)

    def get(self, **kwargs) -> CanvasReport:
        try:
            request = CanvasRequest.model_validate(kwargs)
        except ValidationError as error:
            raise RepositoryError("invalid_canvas_request", "Invalid canvas options") from error
        pagination(request.offset, request.limit)
        if request.mode == "repository" and (request.paths is not None or request.node_ids):
            raise RepositoryError("invalid_canvas_request", "Use impact mode for explicit seeds")
        if request.mode == "changes" and request.node_ids:
            raise RepositoryError(
                "invalid_canvas_request", "Changes mode accepts paths, not node IDs"
            )
        if request.mode != "repository" and request.query:
            raise RepositoryError(
                "invalid_canvas_request", "Query filtering is for repository mode"
            )
        if request.mode == "impact" and request.paths is None and not request.node_ids:
            raise RepositoryError("invalid_canvas_request", "Impact mode requires explicit seeds")
        if request.mode != "scenario" and (
            request.proposed_files or request.intent or request.assumptions
        ):
            raise RepositoryError(
                "invalid_canvas_request", "Use scenario mode for proposed changes"
            )
        if request.proposed_files and (request.node_ids or request.before_snapshot_id):
            raise RepositoryError(
                "invalid_scenario", "Content previews select their own base and seeds"
            )
        if (
            request.mode == "scenario"
            and not request.proposed_files
            and (request.paths is None and not request.node_ids)
        ):
            raise RepositoryError(
                "invalid_scenario", "Select existing paths, symbols or proposed files"
            )
        active_graph = self.graph
        scenario = None
        scenario_diagnostics = []
        impact_service = ImpactService(self.settings)
        if request.proposed_files:
            active_graph, impact_service, scenario, scenario_diagnostics = prepare_preview(
                self.settings, self.graph, request.proposed_files, request.snapshot_id
            )
            request.paths = scenario.paths
            request.snapshot_id = scenario.proposed_snapshot_id
            request.before_snapshot_id = scenario.base_snapshot_id
        snapshot = active_graph.snapshot(request.snapshot_id)
        snapshots = [snapshot]
        if request.before_snapshot_id and request.before_snapshot_id != snapshot.id:
            snapshots.append(active_graph.snapshot(request.before_snapshot_id))
        if request.mode == "scenario":
            scenario = scenario or ScenarioReport(
                kind="selected_scope",
                base_snapshot_id=snapshot.id,
                paths=request.paths or [],
            )
            scenario.intent = request.intent
            scenario.assumptions = request.assumptions
        changes = None
        impact = None
        tests = None
        diagnostics = list(scenario_diagnostics)
        complete = True
        paths = request.paths
        if paths is not None:
            paths = sorted({normalize_relative(path) for path in paths})
        if request.mode == "changes":
            changes = GitService(self.settings).get_changes(
                baseline=request.baseline, paths=paths, limit=200
            )
            paths = sorted({p for c in changes.changes for p in (c.path, c.old_path) if p})
            complete = changes.complete and changes.next_offset is None and len(paths) <= 200
            diagnostics.extend(changes.diagnostics)
            if not complete:
                diagnostics.append(
                    Diagnostic(
                        code="canvas_changes_incomplete",
                        message="Change preview is incomplete; seeds cover only this preview.",
                    )
                )
            paths = paths[:200]
        if request.mode == "repository":
            nodes = sorted(
                (
                    n
                    for n in snapshot.nodes
                    if request.query.casefold() in (n.path + " " + n.qualified_name).casefold()
                ),
                key=lambda n: (n.kind != "file", n.path, n.start_line, n.id),
            )
            total = len(nodes)
            matching_paths = {n.path for n in nodes}
            nodes = nodes[request.offset : request.offset + request.limit]
            next_offset = (
                request.offset + request.limit if request.offset + request.limit < total else None
            )
        else:
            impact = impact_service.analyze(
                paths=paths if paths is not None else [],
                node_ids=request.node_ids,
                snapshot_id=snapshot.id,
                before_snapshot_id=request.before_snapshot_id,
                max_depth=request.max_depth,
                max_nodes=2000,
                offset=request.offset,
                limit=request.limit,
            )
            nodes = [item.node for item in impact.affected]
            total = impact.total
            next_offset = impact.next_offset
            complete = complete and impact.complete
            diagnostics.extend(impact.diagnostics)
            # Node-specific impact remains narrow; test selection is explicitly file-level.
            test_paths = paths or []
            if request.node_ids:
                all_nodes = {n.id: n for s in snapshots for n in s.nodes}
                test_paths = sorted(
                    set(test_paths)
                    | {
                        all_nodes[node_id].path
                        for node_id in request.node_ids
                        if node_id in all_nodes
                    }
                )
            tests = TestIntelligence(self.settings).suggest(
                paths=test_paths,
                snapshot_id=scenario.base_snapshot_id if request.proposed_files else snapshot.id,
                before_snapshot_id=None if request.proposed_files else request.before_snapshot_id,
                limit=200,
            )
            diagnostics.extend(tests.diagnostics)
            complete = complete and tests.complete
            if request.proposed_files:
                tests.broader_run_recommended = True
                complete = complete and not scenario_diagnostics
                diagnostics.append(
                    Diagnostic(
                        code="scenario_base_tests",
                        message="Base-graph test suggestions; broader verification is required.",
                    )
                )
        selected = {n.id for n in nodes}
        folders = []
        folder_links = []
        file_count = len({n.path for n in nodes})
        if request.mode == "repository":
            file_nodes = [
                n for n in snapshot.nodes if n.kind == "file" and n.path in matching_paths
            ]
            file_count = len(file_nodes)
            query_prefix = request.query.rstrip("/").casefold()
            depth = 1
            if query_prefix and any(
                n.path.casefold().startswith(query_prefix + "/") for n in file_nodes
            ):
                depth = len(query_prefix.split("/")) + 1
            ownership = {}
            counts = {}
            for node in file_nodes:
                folder = "/".join(node.path.split("/")[:-1][:depth]) or "Repository root"
                ownership[node.id] = folder
                counts[folder] = counts.get(folder, 0) + 1
            folders = [
                CanvasFolder(path=path, files=count) for path, count in sorted(counts.items())
            ]
            links = {}
            for edge in snapshot.edges:
                if edge.relation != "imports" or edge.target is None:
                    continue
                source, target = ownership.get(edge.source), ownership.get(edge.target)
                if not source or not target or source == target:
                    continue
                key = (source, target)
                prior = links.get(key)
                links[key] = CanvasFolderLink(
                    source=source,
                    target=target,
                    imports=(prior.imports if prior else 0) + 1,
                    confidence="heuristic"
                    if edge.confidence != "static"
                    or prior is not None
                    and prior.confidence == "heuristic"
                    else "static",
                )
            folder_links = [links[key] for key in sorted(links)]
        # Include only renderable edges. Preserve snapshot provenance, including old edges.
        candidates = [
            CanvasEdge(snapshot_id=s.id, edge=e)
            for s in snapshots
            for e in s.edges
            if e.source in selected and (e.target is None or e.target in selected)
        ]
        candidates.sort(key=lambda item: (item.snapshot_id, item.edge.id))
        edges = candidates[:800]
        total_edges = sum(len(s.edges) for s in snapshots)
        view_complete = (
            len(nodes) == total
            and len(candidates) <= 800
            and (tests is None or tests.next_offset is None)
            and (changes is None or changes.next_offset is None)
            and len(folders) <= 200
            and len(folder_links) <= 400
        )
        if not view_complete:
            diagnostics.append(
                Diagnostic(
                    code="canvas_view_partial",
                    message="Bounded canvas view. Use query, seeds or offset to explore more.",
                )
            )
        if request.mode == "repository":
            diagnostics.append(
                Diagnostic(
                    code="canvas_freshness_unknown",
                    message="Saved graph data; current source freshness has not been checked.",
                )
            )
        all_nodes = {n.id: n for s in snapshots for n in s.nodes}
        all_edges = {(s.id, e.id): e for s in snapshots for e in s.edges}
        for explanation in request.explanations:
            if explanation.node_id not in all_nodes:
                raise RepositoryError("invalid_canvas_citation", "Explanation node is not indexed")
            for citation in explanation.citations:
                edge = all_edges.get((citation.snapshot_id, citation.edge_id))
                if edge is None or explanation.node_id not in {edge.source, edge.target}:
                    raise RepositoryError("invalid_canvas_citation", "Citation must touch its node")
        files = [n for n in nodes if n.kind == "file"]
        tour = [
            TourStep(
                title="Start with the source modules",
                description=f"This view has {len(files)} source modules, {len(nodes)} nodes. "
                "Folder names describe organization; product roles need source review.",
                node_ids=[n.id for n in files[:8]],
            ),
            TourStep(
                title="Follow the evidence",
                description="Select a card to inspect imports, calls and ownership separately. "
                "Dashed connections are heuristic candidates, not observed execution.",
                node_ids=[n.id for n in nodes[:8]],
            ),
            TourStep(
                title="Review the unknowns",
                description="Check freshness, unresolved relationships and partial-view notices. "
                "A missing connection does not establish that a change is safe.",
            ),
        ]
        if impact:
            tour.insert(
                1,
                TourStep(
                    title="Trace the potential ripple effect",
                    description="Start at the selected scope, then inspect direct and transitive "
                    "dependents. Every impact path includes source evidence.",
                    node_ids=[i.node.id for i in impact.affected if i.evidence][:8],
                ),
            )
        original_request = request.model_dump(exclude={"proposed_files", "explanations"})
        original_request["snapshot_id"] = snapshot.id
        # Virtual graphs are not persisted and must never be used as refresh IDs.
        if request.proposed_files:
            original_request = {
                "mode": "scenario",
                "paths": scenario.paths,
                "snapshot_id": scenario.base_snapshot_id,
                "intent": request.intent,
                "assumptions": request.assumptions,
            }
        verification = None
        if request.verification_plan_id:
            verification = VerificationService(self.settings).result(
                request.verification_plan_id, limit=200
            )
            if verification.next_offset is not None:
                view_complete = False
                diagnostics.append(
                    Diagnostic(
                        code="canvas_verification_partial",
                        message="Saved case preview; use the verification result tool for more.",
                    )
                )
        report = CanvasReport(
            repository_name=self.settings.root.name,
            mode=request.mode,
            snapshot_ids=[s.id for s in snapshots],
            nodes=nodes,
            edges=edges,
            total_nodes=total,
            total_edges=total_edges,
            omitted_edges=total_edges - len(edges),
            next_offset=next_offset,
            freshness=impact.freshness if impact else "unknown",
            complete=complete,
            view_complete=view_complete,
            impact=impact,
            changes=changes,
            tests=tests,
            scenario=scenario,
            tour=tour,
            explanations=request.explanations,
            request=original_request,
            verification=verification,
            total_files=file_count,
            folders=folders[:200],
            folder_links=folder_links[:400],
            total_folders=len(folders),
            total_folder_links=len(folder_links),
            unresolved_dependencies=sum(e.target is None for s in snapshots for e in s.edges),
            diagnostics=diagnostics[:200],
        )
        if len(report.model_dump_json().encode("utf-8")) > 8_000_000:
            raise RepositoryError("canvas_output_limit", "Narrow the canvas scope or page size")
        return report
