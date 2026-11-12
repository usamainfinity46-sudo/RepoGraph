/* Trusted viewer. Repository strings enter the DOM only through textContent. */
(() => {
  "use strict";
  let dispose = () => {};
  window.RepoGraphCanvas = { dispose: () => dispose(), mount };
  function mount(data) {
    dispose();
    const $ = (id) => document.getElementById(id);
    const el = (tag, cls, text) => {
      const n = document.createElement(tag);
      if (cls) n.className = cls;
      if (text !== undefined) n.textContent = text;
      return n;
    };
    const svgNS = "http://www.w3.org/2000/svg";
    const icons = {
      map: ["M3 5l6-2 6 2 6-2v16l-6 2-6-2-6 2z", "M9 3v16M15 5v16"],
      ripple: [
        "M12 3v4M12 17v4M3 12h4M17 12h4",
        "M8 8a6 6 0 1 0 8 0",
        "M10 10l2-2 2 2M12 8v6",
      ],
      check: ["M9 12l2 2 4-5", "M20 12a8 8 0 1 1-4-7"],
      search: ["M21 21l-5-5", "M18 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0"],
      info: ["M12 11v6M12 7v.1", "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0"],
      file: [
        "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z",
        "M14 2v6h6M8 13h8M8 17h5",
      ],
      code: ["M8 7l-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"],
      panel: ["M3 4h18v16H3zM15 4v16"],
      route: [
        "M6 5v10a4 4 0 0 0 4 4h8M14 15l4 4-4 4",
        "M9 5a3 3 0 1 1-6 0 3 3 0 0 1 6 0M18 3v8M14 7h8",
      ],
      fit: ["M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5"],
      layers: ["M12 3l10 5-10 5L2 8zM2 12l10 5 10-5M2 16l10 5 10-5"],
      link: [
        "M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-2 2",
        "M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l2-2",
      ],
    };
    function icon(name) {
      const s = document.createElementNS(svgNS, "svg");
      s.setAttribute("viewBox", "0 0 24 24");
      s.setAttribute("class", "icon");
      s.setAttribute("aria-hidden", "true");
      for (const d of icons[name] || icons.code) {
        const p = document.createElementNS(svgNS, "path");
        p.setAttribute("d", d);
        s.append(p);
      }
      return s;
    }
    document
      .querySelectorAll("[data-icon]")
      .forEach((n) => n.replaceChildren(icon(n.dataset.icon)));
    for (const id of ["stats", "files", "notices", "limitations-body"])
      $(id).replaceChildren();
    const nodeById = new Map(data.nodes.map((n) => [n.id, n]));
    const impactById = new Map(
      (data.impact?.affected || []).map((n) => [n.node.id, n]),
    );
    const changedPaths = new Set(
      (data.changes?.changes || [])
        .flatMap((c) => [c.path, c.old_path])
        .filter(Boolean),
    );
    const uncertainPaths = new Set(data.impact?.uncertain_modules || []);
    const files = [...new Set(data.nodes.map((n) => n.path))].sort();
    let view = data.impact ? "impact" : "map",
      selected = null,
      developer = false,
      filter = "",
      fileFilter = null;
    let folderFilter = null,
      renderedEdges = data.edges;
    $("search").value = "";
    document.body.classList.remove("developer");
    document
      .querySelectorAll("[data-view]")
      .forEach((b) => b.classList.toggle("active", b.dataset.view === view));
    let scale = 1,
      pan = { x: 30, y: 24 },
      positions = new Map(),
      trace = [],
      traceStep = -1;
    let sceneSize = { width: 900, height: 500 };
    const label = (n) =>
      n.kind === "file"
        ? n.path.split("/").pop()
        : developer
          ? n.qualified_name
          : n.name;
    $("repo-name").textContent = data.repository_name;
    $("crumb").textContent = data.repository_name;
    $("freshness").textContent = {
      current: "Source checked at export",
      stale: "Source differs from graph",
      unknown: "Freshness not checked",
    }[data.freshness];
    $("freshness").classList.add(data.freshness);
    $("impact-count").textContent = data.impact ? data.impact.total : "";
    $("tests-count").textContent = data.tests ? data.tests.total : "";
    $("file-count").textContent = files.length;
    $("scope").textContent =
      `${data.nodes.length} of ${data.total_nodes} nodes · ${data.edges.length} displayed relationships · Snapshot ${data.snapshot_ids[0].slice(0, 8)}${data.view_complete ? "" : " · Partial view"}`;
    const scopeDescription = $("scope").textContent;
    const statEntries = [
      [
        "Source files",
        data.total_files || files.length,
        data.mode === "repository"
          ? "Across the indexed scope"
          : "In this saved view",
        "file",
      ],
      [
        "Relationships",
        data.edges.length,
        `${data.omitted_edges} outside this view`,
        "link",
      ],
      [
        "Potential dependents",
        data.impact
          ? data.impact.affected.filter((n) =>
              ["direct", "transitive"].includes(n.classification),
            ).length
          : "—",
        "Static paths, not runtime effects",
        "ripple",
      ],
      [
        "Suggested tests",
        data.tests ? data.tests.total : "—",
        "Not executed",
        "check",
      ],
    ];
    for (const [name, value, note, glyph] of statEntries) {
      const s = el("div", "stat");
      const top = el("div", "stat-top", name);
      top.append(icon(glyph));
      s.append(
        top,
        el("div", "stat-number", String(value)),
        el("div", "stat-note", note),
      );
      $("stats").append(s);
    }
    for (const path of files) {
      const b = el("button", "file-item");
      b.title = path;
      b.append(icon("file"), el("span", "", path));
      b.onclick = () => {
        folderFilter = null;
        fileFilter = fileFilter === path ? null : path;
        document
          .querySelectorAll(".file-item")
          .forEach((n) => n.classList.remove("selected"));
        if (fileFilter) b.classList.add("selected");
        render();
        fit();
      };
      $("files").append(b);
    }
    function transform() {
      $("scene").style.transform =
        `translate(${pan.x}px,${pan.y}px) scale(${scale})`;
      $("zoom-label").textContent = `${Math.round(scale * 100)}%`;
    }
    function fit(readable = true) {
      const r = $("viewport").getBoundingClientRect();
      scale = Math.max(
        readable ? 0.65 : 0.12,
        Math.min(
          1,
          (r.width - 45) / sceneSize.width,
          (r.height - 40) / sceneSize.height,
        ),
      );
      pan = { x: (r.width - sceneSize.width * scale) / 2, y: 18 };
      transform();
    }
    function setZoom(next) {
      const r = $("viewport").getBoundingClientRect(),
        x = r.width / 2,
        y = r.height / 2;
      const prev = scale;
      scale = Math.min(2, Math.max(0.12, next));
      pan = {
        x: x - ((x - pan.x) * scale) / prev,
        y: y - ((y - pan.y) * scale) / prev,
      };
      transform();
    }
    $("zoom-in").onclick = () => setZoom(scale * 1.2);
    $("zoom-out").onclick = () => setZoom(scale / 1.2);
    $("fit").onclick = () => fit(false);
    let drag = null;
    $("viewport").onpointerdown = (e) => {
      if (e.target.closest("button")) return;
      drag = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
      $("viewport").setPointerCapture(e.pointerId);
      $("viewport").classList.add("dragging");
    };
    $("viewport").onpointermove = (e) => {
      if (!drag) return;
      pan = {
        x: drag.px + e.clientX - drag.x,
        y: drag.py + e.clientY - drag.y,
      };
      transform();
    };
    $("viewport").onkeydown = (e) => {
      if (e.target !== $("viewport")) return;
      const moves = {
        ArrowLeft: [40, 0],
        ArrowRight: [-40, 0],
        ArrowUp: [0, 40],
        ArrowDown: [0, -40],
      };
      if (moves[e.key]) {
        e.preventDefault();
        pan.x += moves[e.key][0];
        pan.y += moves[e.key][1];
        transform();
      } else if (e.key === "Home") {
        e.preventDefault();
        fit();
      } else if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        setZoom(scale * 1.2);
      } else if (e.key === "-") {
        e.preventDefault();
        setZoom(scale / 1.2);
      }
    };
    for (const name of ["onpointerup", "onpointercancel"])
      $("viewport")[name] = () => {
        drag = null;
        $("viewport").classList.remove("dragging");
      };
    function empty(title, copy) {
      const box = $("empty");
      box.replaceChildren(el("strong", "", title), el("span", "", copy));
      box.hidden = false;
    }
    function render() {
      renderedEdges = data.edges;
      $("scope").textContent =
        scopeDescription + (folderFilter ? " · Folder " + folderFilter : "");
      $("nodes").replaceChildren();
      $("connections").replaceChildren();
      positions = new Map();
      $("empty").hidden = true;
      $("map-title").textContent = {
        map: "Repository map",
        impact: "Change impact",
        tests: "Suggested tests",
      }[view];
      if (view === "tests") {
        renderTests();
        return;
      }
      if (view === "impact" && !data.impact) {
        empty(
          "Choose a change to explore.",
          "Export an impact or changes canvas to see evidence-backed dependents.",
        );
        return;
      }
      let nodes = data.nodes.filter(
        (n) =>
          (!fileFilter || n.path === fileFilter) &&
          (!folderFilter ||
            (folderFilter === "Repository root"
              ? !n.path.includes("/")
              : n.path.startsWith(folderFilter + "/"))) &&
          `${n.path} ${n.qualified_name}`.toLowerCase().includes(filter),
      );
      if (!developer) {
        const fileNodes = nodes.filter((n) => n.kind === "file");
        if (fileNodes.length && view === "map") nodes = fileNodes;
      }
      if (
        view === "map" &&
        !developer &&
        !filter &&
        !fileFilter &&
        !folderFilter &&
        (data.total_files || nodes.length) > 16 &&
        !(
          data.folders?.length === 1 &&
          (data.folders[0].path ===
            (data.request?.query || "").replace(/\/$/, "") ||
            data.folders[0].path === "Repository root")
        )
      ) {
        renderFolders(nodes);
        return;
      }
      if (!nodes.length) {
        empty(
          "No nodes in this view.",
          "Try a different search, clear the file selection, or export another page.",
        );
        return;
      }
      const groups = new Map();
      for (const [index, n] of nodes.entries()) {
        const info = impactById.get(n.id);
        const key =
          view === "impact"
            ? Math.min(info?.depth || 0, 3)
            : Math.floor(index / Math.max(4, Math.ceil(nodes.length / 3)));
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(n);
      }
      const keys = [...groups.keys()].sort((a, b) => a - b);
      let maxRows = 0;
      keys.forEach((key, col) => {
        const list = groups.get(key);
        maxRows = Math.max(maxRows, list.length);
        const heading = el(
          "div",
          "column-label",
          view === "impact"
            ? key === 0
              ? "SELECTED SCOPE"
              : key === 1
                ? "DIRECT DEPENDENTS"
                : key === 3
                  ? "3+ HOPS"
                  : "2 HOPS"
            : developer
              ? "INDEXED CODE"
              : "SOURCE MODULES",
        );
        heading.style.left = `${col * 250 + 8}px`;
        heading.style.top = "0px";
        $("nodes").append(heading);
        list.forEach((n, row) => {
          const x = col * 250,
            y = 32 + row * 97;
          positions.set(n.id, { x, y });
          const b = el("button", "node");
          b.dataset.nodeId = n.id;
          b.style.left = `${x}px`;
          b.style.top = `${y}px`;
          b.setAttribute(
            "aria-label",
            `${n.kind} ${n.qualified_name}, ${n.path}:${n.start_line}`,
          );
          const info = impactById.get(n.id);
          if (info && ["direct", "transitive"].includes(info.classification))
            b.classList.add("dependent");
          if (uncertainPaths.has(n.path)) b.classList.add("uncertain");
          if (selected?.id === n.id) b.classList.add("selected");
          const ni = el("span", "node-icon");
          ni.append(icon(n.kind === "file" ? "file" : "code"));
          const copy = el("span", "node-copy");
          copy.append(
            el("strong", "", label(n)),
            el(
              "small",
              "",
              developer
                ? `${n.path}:${n.start_line}`
                : n.kind === "file"
                  ? n.path.includes("/")
                    ? n.path.slice(0, n.path.lastIndexOf("/"))
                    : "Repository root"
                  : `${n.kind} · ${n.path.split("/").pop()}`,
            ),
          );
          b.append(ni, copy);
          if (info?.classification === "changed" || changedPaths.has(n.path))
            b.append(
              el(
                "span",
                "pill",
                data.mode === "changes" ? "CHANGED" : "SELECTED",
              ),
            );
          b.onclick = () => select(n);
          $("nodes").append(b);
        });
      });
      sceneSize = {
        width: keys.length * 250 - 55,
        height: Math.max(130, 32 + maxRows * 97),
      };
      $("scene").style.width = `${sceneSize.width}px`;
      $("scene").style.height = `${sceneSize.height}px`;
      drawEdges();
      transform();
    }
    function folderOf(path) {
      return path.includes("/")
        ? path.slice(0, path.lastIndexOf("/"))
        : "Repository root";
    }
    function renderFolders(nodes) {
      const folders = new Map();
      for (const n of nodes) {
        const folder = folderOf(n.path);
        if (!folders.has(folder)) folders.set(folder, []);
        folders.get(folder).push(n);
      }
      if (data.folders?.length) {
        folders.clear();
        for (const folder of data.folders)
          folders.set(folder.path, { length: folder.files });
      }
      const entries = [...folders].sort(([a], [b]) => a.localeCompare(b));
      const columns = Math.min(3, entries.length);
      const groupIds = new Map(
        entries.map(([folder]) => [folder, "folder:" + folder]),
      );
      selected = null;
      entries.forEach(([folder, modules], i) => {
        const id = groupIds.get(folder),
          x = (i % columns) * 250,
          y = Math.floor(i / columns) * 110 + 20;
        positions.set(id, { x, y });
        const b = el("button", "node folder-node");
        b.style.left = `${x}px`;
        b.style.top = `${y}px`;
        b.setAttribute(
          "aria-label",
          `Folder ${folder}, ${modules.length} included modules`,
        );
        const glyph = el("span", "node-icon");
        glyph.append(icon("layers"));
        const copy = el("span", "node-copy");
        copy.append(
          el("strong", "", folder),
          el("small", "", `${modules.length} source modules · Expand`),
        );
        b.append(glyph, copy);
        b.onclick = () => {
          if (
            window.RepoGraphCanvas.request &&
            data.folders?.length &&
            folder !== "Repository root"
          ) {
            window.RepoGraphCanvas.request({
              mode: "repository",
              query: folder + "/",
              offset: 0,
              paths: null,
              node_ids: null,
              before_snapshot_id: null,
              intent: "",
              assumptions: [],
              proposed_files: [],
            }).catch((error) => {
              $("bridge-status").textContent = error.message;
            });
            return;
          }
          folderFilter = folder;
          render();
          fit();
          const back = el("button", "action-button", "Show all folders");
          back.onclick = () => {
            folderFilter = null;
            render();
            fit();
            initialInspector();
          };
          $("inspector-content").replaceChildren(
            el("div", "detail-icon"),
            el("h2", "detail-title", folder),
            section(
              "Folder group",
              `${modules.length} included source modules. Folder grouping describes organization, not a verified product role. Connections between groups aggregate indexed imports. Select a module for original source evidence.`,
            ),
            back,
          );
        };
        $("nodes").append(b);
      });
      const grouped = new Map();
      for (const { edge, snapshot_id } of data.edges) {
        if (edge.relation !== "imports" || !edge.target) continue;
        const a = nodeById.get(edge.source),
          b = nodeById.get(edge.target);
        if (!a || !b) continue;
        const source = groupIds.get(folderOf(a.path)),
          target = groupIds.get(folderOf(b.path));
        if (!source || !target || source === target) continue;
        const key = source + "→" + target;
        const prior = grouped.get(key);
        grouped.set(key, {
          snapshot_id,
          edge: {
            id: key,
            source,
            target,
            confidence:
              prior?.edge.confidence === "heuristic" ||
              edge.confidence !== "static"
                ? "heuristic"
                : "static",
          },
        });
      }
      renderedEdges = [...grouped.values()];
      if (data.folders?.length)
        renderedEdges = (data.folder_links || [])
          .filter(
            (link) => groupIds.has(link.source) && groupIds.has(link.target),
          )
          .map((link) => ({
            snapshot_id: data.snapshot_ids[0],
            edge: {
              id: `folder:${link.source}:${link.target}`,
              source: groupIds.get(link.source),
              target: groupIds.get(link.target),
              confidence: link.confidence,
            },
          }));
      sceneSize = {
        width: columns * 250 - 55,
        height: Math.ceil(entries.length / columns) * 110 + 20,
      };
      $("scene").style.width = `${sceneSize.width}px`;
      $("scene").style.height = `${sceneSize.height}px`;
      $("scope").textContent =
        scopeDescription +
        ` · ${entries.length} of ${data.total_folders || entries.length} folder groups; arrows aggregate cross-folder imports`;
      drawEdges();
      transform();
    }
    function drawEdges() {
      $("connections").replaceChildren();
      const defs = document.createElementNS(svgNS, "defs");
      const marker = document.createElementNS(svgNS, "marker");
      marker.id = "edge-arrow";
      marker.setAttribute("viewBox", "0 0 10 10");
      marker.setAttribute("refX", "9");
      marker.setAttribute("refY", "5");
      marker.setAttribute("markerWidth", "5");
      marker.setAttribute("markerHeight", "5");
      marker.setAttribute("orient", "auto-start-reverse");
      const tip = document.createElementNS(svgNS, "path");
      tip.setAttribute("d", "M0 1 L9 5 L0 9");
      tip.setAttribute("fill", "none");
      tip.setAttribute("stroke", "#93a5c1");
      tip.setAttribute("stroke-width", "1.5");
      marker.append(tip);
      defs.append(marker);
      $("connections").append(defs);
      const seen = new Set();
      for (const { edge: e, snapshot_id: sid } of renderedEdges) {
        let a = positions.get(e.source),
          b = positions.get(e.target);
        if (!a || !b) continue;
        const key = [e.source, e.target, e.relation, sid].join(":");
        if (seen.has(key)) continue;
        seen.add(key);
        const p = document.createElementNS(svgNS, "path");
        p.dataset.edgeId = e.id;
        p.setAttribute("marker-end", "url(#edge-arrow)");
        let ax = a.x + 195,
          ay = a.y + 34,
          bx = b.x,
          by = b.y + 34;
        if (a.x === b.x) {
          ax = a.x + 195;
          bx = b.x + 195;
          p.setAttribute(
            "d",
            `M${ax},${ay} C${ax + 40},${ay} ${bx + 40},${by} ${bx},${by}`,
          );
        } else
          p.setAttribute(
            "d",
            `M${ax},${ay} C${ax + 45},${ay} ${bx - 45},${by} ${bx},${by}`,
          );
        p.setAttribute(
          "class",
          `connection ${e.confidence}${sid !== data.snapshot_ids[0] ? " historical" : ""}${selected && (e.source === selected.id || e.target === selected.id) ? " highlight" : ""}`,
        );
        $("connections").append(p);
      }
    }
    function section(title, text) {
      const s = el("section", "detail-section");
      s.append(el("h3", "", title));
      if (text) s.append(el("p", "", text));
      return s;
    }
    function select(n, keepTrace = false) {
      selected = n;
      if (!keepTrace) {
        resetTrace();
      }
      document
        .querySelectorAll(".node")
        .forEach((b) =>
          b.classList.toggle("selected", b.dataset.nodeId === n.id),
        );
      drawEdges();
      const box = $("inspector-content");
      box.replaceChildren();
      const glyph = el("div", "detail-icon");
      glyph.append(icon(n.kind === "file" ? "file" : "code"));
      box.append(
        glyph,
        el("h2", "detail-title", label(n)),
        el("p", "detail-path", `${n.path}:${n.start_line}–${n.end_line}`),
      );
      const info = impactById.get(n.id);
      box.append(
        el(
          "span",
          "badge",
          info
            ? `${info.classification} · ${info.confidence}`
            : `${n.kind} · indexed source`,
        ),
      );
      box.append(
        section(
          "What you’re looking at",
          n.kind === "file"
            ? "A source module. Its connections show relationships found in the indexed source."
            : `A ${n.kind} declaration in this module. Its product role requires interpretation of the source.`,
        ),
      );
      if (info)
        box.append(
          section(
            "Why it is in scope",
            info.classification === "changed"
              ? "This node belongs to the selected change scope. File selection includes declarations conservatively; not every declaration necessarily changed."
              : info.classification === "context"
                ? "This node supplies ownership context. Containment is not a function call."
                : `A reverse dependency path reaches this node in ${info.depth} semantic hop${info.depth === 1 ? "" : "s"}. This is a potential effect, not an observed failure.`,
          ),
        );
      const change = data.changes?.changes.find(
        (c) => c.path === n.path || c.old_path === n.path,
      );
      if (change) {
        const s = section(
          "Actual file change",
          `${change.status}${change.old_path ? " · " + change.old_path + " → " + change.path : ""}. ${change.total_symbols} changed declarations; ${change.total_hunks} line ranges.`,
        );
        for (const symbol of change.symbols.slice(0, 15))
          s.append(
            el(
              "p",
              "",
              `${symbol.status} ${symbol.qualified_name} · ${symbol.old_line ?? "—"} → ${symbol.new_line ?? "—"}`,
            ),
          );
        for (const hunk of change.hunks.slice(0, 8))
          s.append(
            el(
              "p",
              "",
              `Lines ${hunk.old_start} (+${hunk.old_count}) → ${hunk.new_start} (+${hunk.new_count})`,
            ),
          );
        box.append(s);
      }
      const witness = info?.evidence || [];
      const related = data.edges.filter(
        ({ edge: e }) => e.source === n.id || e.target === n.id,
      );
      const evidence = section(
        witness.length ? "Impact evidence" : "Source relationships",
      );
      if (!witness.length && !related.length)
        evidence.append(
          el(
            "p",
            "",
            "No relationships are included for this node in the current view. This does not prove isolation.",
          ),
        );
      const records = witness.length
        ? witness.map((e) => ({
            source: e.source,
            target: e.target,
            relation: e.relation,
            path: e.path,
            line: e.line,
            confidence: e.confidence,
            snapshot: e.snapshot_id,
          }))
        : related.map(({ edge: e, snapshot_id: sid }) => ({
            ...e,
            snapshot: sid,
          }));
      for (const e of records.slice(0, 20)) {
        const b = el("button", "evidence-button");
        const source = nodeById.get(e.source),
          target = nodeById.get(e.target);
        b.textContent = `${source ? label(source) : "Source outside view"} ${e.relation} ${target ? label(target) : e.target_name || "target outside view"}`;
        b.append(
          el(
            "span",
            "evidence-meta",
            `${e.path}:${e.line} · ${e.confidence} · ${e.snapshot.slice(0, 8)}`,
          ),
        );
        const other = e.source === n.id ? target : source;
        if (other) b.onclick = () => select(other);
        else b.disabled = true;
        evidence.append(b);
      }
      if (records.length > 20)
        evidence.append(
          el(
            "p",
            "",
            `${records.length - 20} more relationships omitted from this panel.`,
          ),
        );
      box.append(evidence);
      if (related.some(({ edge: e }) => !e.target))
        box.append(
          section(
            "Uncertainty",
            "Some targets could not be resolved. Additional consumers or runtime behavior may be missing.",
          ),
        );
      for (const explanation of data.explanations || []) {
        if (explanation.node_id !== n.id) continue;
        const s = section("Agent interpretation", explanation.text);
        for (const c of explanation.citations)
          s.append(
            el(
              "p",
              "citation",
              `Source edge ${c.edge_id.slice(0, 12)} · Snapshot ${c.snapshot_id.slice(0, 8)}`,
            ),
          );
        box.append(s);
      }
      if (
        window.RepoGraphCanvas.request &&
        !data.scenario?.proposed_snapshot_id
      ) {
        const actions = section("Explore further");
        const expand = el("button", "action-button", "Expand this module");
        expand.onclick = () =>
          window.RepoGraphCanvas.request({
            mode: "repository",
            paths: null,
            node_ids: null,
            query: n.path,
            offset: 0,
            limit: 200,
            intent: "",
            assumptions: [],
            proposed_files: [],
          }).catch(() => {});
        const scenario = el(
          "button",
          "action-button",
          "What if I change this?",
        );
        scenario.onclick = () =>
          window.RepoGraphCanvas.request({
            mode: "scenario",
            paths: [],
            node_ids: [n.id],
            query: "",
            offset: 0,
            intent: `Explore a proposed change to ${n.name}`,
            proposed_files: [],
          }).catch(() => {});
        actions.append(expand, scenario);
        box.append(actions);
      }
      if (developer) {
        const s = section("Source identity");
        s.append(
          el("code", "", `Node ${n.id}`),
          el("p", "", `Content ${n.content_hash.slice(0, 16)}`),
        );
        box.append(s);
      }
      const path = witness.filter((e) => e.relation !== "contains");
      $("walk").disabled = !path.length;
      $("walk").textContent = trace.length ? "Next step →" : "Trace impact →";
      $("walk-title").textContent = path.length
        ? "See why this node could be affected."
        : "Follow a connection.";
      $("walk-copy").textContent = path.length
        ? `${path.length} source relationship${path.length === 1 ? "" : "s"} connect this node to the selected scope.`
        : "Select a dependent node to walk through its impact evidence.";
    }
    function initialInspector() {
      const box = $("inspector-content");
      const glyph = el("div", "detail-icon");
      glyph.append(icon("layers"));
      box.replaceChildren(
        glyph,
        el("h2", "detail-title", "The details, in context."),
        el("p", "detail-path", "Select a node on the canvas."),
      );
      box.append(
        section(
          "Start with a source module",
          "Each card represents indexed code. Select one to see its source location and the relationships available in this view.",
        ),
        section(
          "Read the connections",
          "Dashed lines are heuristic candidates. Ownership, imports, calls and inheritance remain distinct in the evidence panel.",
        ),
      );
    }
    function renderTests() {
      const tests = (data.tests?.tests || []).filter((t) =>
        t.path.toLowerCase().includes(filter),
      );
      if (!tests.length) {
        empty(
          "No test suggestions in this view.",
          data.tests
            ? "An empty list does not establish coverage."
            : "Export an impact or changes canvas to request static test suggestions.",
        );
        return;
      }
      const columns = 2;
      tests.forEach((t, i) => {
        const b = el("button", "test-card");
        b.style.left = `${(i % columns) * 295}px`;
        b.style.top = `${Math.floor(i / columns) * 125}px`;
        b.append(
          el("strong", "", t.path),
          el(
            "small",
            "",
            `${t.reason.replaceAll("_", " ")} · ${t.confidence}\n${t.frameworks.join(", ") || "Unknown framework"} · Not executed`,
          ),
        );
        b.onclick = () => {
          const box = $("inspector-content");
          box.replaceChildren(
            el("div", "detail-icon"),
            el("h2", "detail-title", t.path),
            section(
              "Why this test was suggested",
              `${t.reason.replaceAll("_", " ")}. Confidence: ${t.confidence}. Selection is file-level and does not establish exhaustive coverage.`,
            ),
            section(
              "Verification status",
              "Not executed. Running tests requires a separately reviewed and approved verification plan.",
            ),
          );
          for (const e of t.evidence.slice(0, 15))
            box.append(
              section(
                e.relation,
                `${e.path}:${e.line} · ${e.confidence} · Snapshot ${e.snapshot_id.slice(0, 8)}`,
              ),
            );
        };
        $("nodes").append(b);
      });
      sceneSize = {
        width: 565,
        height: Math.ceil(tests.length / columns) * 125,
      };
      $("scene").style.width = `${sceneSize.width}px`;
      $("scene").style.height = `${sceneSize.height}px`;
      transform();
    }
    $("walk").onclick = () => {
      if (!selected) return;
      if (!trace.length) {
        const info = impactById.get(selected.id);
        trace = (info?.evidence || []).filter((e) => e.relation !== "contains");
        traceStep = -1;
      }
      if (!trace.length) return;
      traceStep = (traceStep + 1) % trace.length;
      const e = trace[traceStep];
      document
        .querySelectorAll(".connection")
        .forEach((p) =>
          p.classList.toggle("trace", p.dataset.edgeId === e.edge_id),
        );
      $("walk-title").textContent =
        `Relationship ${traceStep + 1} of ${trace.length}`;
      const a = nodeById.get(e.source),
        b = nodeById.get(e.target);
      $("walk-copy").textContent =
        `${a ? label(a) : e.source} ${e.relation} ${b ? label(b) : e.target} · ${e.path}:${e.line} · ${e.confidence}. Dependency evidence, not execution order.`;
      $("walk").textContent =
        traceStep === trace.length - 1 ? "Start again →" : "Next step →";
      document
        .querySelectorAll(".node")
        .forEach((n) =>
          n.classList.toggle(
            "dimmed",
            ![e.source, e.target].includes(n.dataset.nodeId),
          ),
        );
    };
    function resetTrace() {
      trace = [];
      traceStep = -1;
      document
        .querySelectorAll(".dimmed")
        .forEach((n) => n.classList.remove("dimmed"));
    }
    document.querySelectorAll("[data-view]").forEach(
      (b) =>
        (b.onclick = () => {
          view = b.dataset.view;
          folderFilter = null;
          fileFilter = null;
          resetTrace();
          document
            .querySelectorAll("[data-view]")
            .forEach((n) => n.classList.toggle("active", n === b));
          $("title").textContent = {
            map: "A clearer view of your code.",
            impact: "Understand the ripple effect.",
            tests: "Know what to check next.",
          }[view];
          $("subtitle").textContent = {
            map: "Explore the pieces. Follow the relationships. Understand what connects.",
            impact:
              "Follow potential dependents, with the source evidence behind every step.",
            tests:
              "Static recommendations, with their reasons. No tests have been executed.",
          }[view];
          render();
          fit();
        }),
    );
    $("search").oninput = (e) => {
      filter = e.target.value.toLowerCase();
      resetTrace();
      render();
      fit();
    };
    function detailLevel(value) {
      developer = value;
      document.body.classList.toggle("developer", value);
      $("simple").classList.toggle("selected", !value);
      $("detailed").classList.toggle("selected", value);
      $("simple").setAttribute("aria-pressed", String(!value));
      $("detailed").setAttribute("aria-pressed", String(value));
      resetTrace();
      render();
      if (selected) select(selected);
      fit();
    }
    $("simple").onclick = () => detailLevel(false);
    $("detailed").onclick = () => detailLevel(true);
    $("help").onclick = () => $("limitations").showModal();
    $("close-help").onclick = () => $("limitations").close();
    for (const text of data.limitations)
      $("limitations-body").append(el("p", "", text));
    $("limitations-body").append(
      el("p", "", `Snapshot IDs: ${data.snapshot_ids.join(", ")}`),
    );
    const notices = [];
    if (data.impact?.unresolved_dependencies)
      notices.push(
        `${data.impact.unresolved_dependencies} unresolved relationships remain; ${data.impact.relevant_unresolved_dependencies} may hide additional consumers. Static analysis cannot establish exhaustive effects.`,
      );
    if (!data.complete)
      notices.push(
        "Analysis is incomplete. Inspect diagnostics before drawing conclusions.",
      );
    if (!data.view_complete)
      notices.push(
        `Partial canvas. ${data.total_nodes} nodes match this scope; ${data.nodes.length} are included. Export another page or narrow the scope.`,
      );
    if (data.freshness !== "current")
      notices.push(
        data.freshness === "stale"
          ? "Source has changed since indexing. Refresh the graph before relying on this impact."
          : "Freshness has not been established for this saved graph.",
      );
    if (data.tests?.broader_run_recommended)
      notices.push(
        "Broader verification is recommended. These suggestions do not establish complete coverage.",
      );
    if (data.mode === "changes" && !data.changes?.changes.length)
      notices.push(
        "No changes found in the compared scope. This is not a runtime safety assessment.",
      );
    for (const text of notices) $("notices").append(el("div", "notice", text));
    if (data.impact?.uncertain_modules.length)
      $("limitations-body").append(
        el(
          "p",
          "",
          `Uncertain consumer modules: ${data.impact.uncertain_modules.join(", ")} (${data.impact.total_uncertain_modules} total)`,
        ),
      );
    for (const d of data.diagnostics)
      $("limitations-body").append(
        el("p", "", `${d.code}: ${d.message}${d.path ? " · " + d.path : ""}`),
      );
    let tourIndex = -1;
    $("tour").onclick = () => {
      const steps = data.tour || [];
      if (!steps.length) return;
      tourIndex = (tourIndex + 1) % steps.length;
      const step = steps[tourIndex];
      $("tour-title").textContent =
        `${tourIndex + 1} / ${steps.length} · ${step.title}`;
      $("tour-copy").textContent = step.description;
      $("tour").textContent =
        tourIndex === steps.length - 1 ? "Start again →" : "Next →";
      const target = (step.node_ids || [])
        .map((id) => nodeById.get(id))
        .find(Boolean);
      if (target) {
        select(target);
        document
          .querySelectorAll(".node")
          .forEach((n) =>
            n.classList.toggle(
              "dimmed",
              !(step.node_ids || []).includes(n.dataset.nodeId),
            ),
          );
      }
    };
    $("scenario").replaceChildren();
    $("scenario").hidden = !data.scenario;
    if (data.scenario) {
      $("scenario").append(
        el("strong", "", "Proposed change · Source unchanged"),
        el(
          "p",
          "",
          data.scenario.intent ||
            "Explore the potential impact of changing the selected scope.",
        ),
      );
      for (const assumption of data.scenario.assumptions)
        $("scenario").append(el("p", "", `Assumption: ${assumption}`));
      if (data.scenario.kind === "proposed_content")
        $("scenario").append(
          el(
            "p",
            "",
            `${data.scenario.added_nodes} added · ${data.scenario.modified_nodes} modified · ${data.scenario.removed_nodes} removed nodes in the proposed graph.`,
          ),
        );
      for (const text of data.scenario.limitations)
        $("limitations-body").append(el("p", "", text));
    }
    $("changes").hidden = !data.changes;
    $("change-files").replaceChildren();
    for (const change of data.changes?.changes || []) {
      const button = el(
        "button",
        "change-file",
        `${change.status} · ${change.old_path ? change.old_path + " → " : ""}${change.path}`,
      );
      button.onclick = () => {
        const n = data.nodes.find(
          (n) => n.path === change.path || n.path === change.old_path,
        );
        if (n) select(n);
        else {
          $("inspector-content").replaceChildren(
            el("h2", "detail-title", change.path),
            section(
              "Actual file change",
              `${change.status}. This path has no indexed node in the included graph page. Supply a retained before snapshot for deleted-code evidence.`,
            ),
          );
        }
      };
      $("change-files").append(button);
    }
    $("verification").hidden = !data.verification;
    $("verification").replaceChildren();
    if (data.verification) {
      const run = data.verification;
      $("verification").append(
        el("strong", "", `Saved verification · ${run.status}`),
        el(
          "p",
          "",
          `${run.framework} · ${run.counts.passed} passed · ${run.counts.failed} failed · ${run.counts.errors} errors · ${run.counts.skipped} skipped`,
        ),
        el(
          "p",
          "",
          `Plan ${run.plan_id}. This is a saved run; applicability to the displayed tree has not been established. No tests ran when creating this canvas.`,
        ),
      );
      for (const item of run.cases.slice(0, 15))
        $("verification").append(
          el("p", "", `${item.status} · ${item.path} · ${item.name}`),
        );
    }
    $("refresh").onclick = () =>
      window.RepoGraphCanvas.request?.(
        data.scenario?.kind === "proposed_content"
          ? {}
          : { snapshot_id: null, offset: 0 },
      ).catch(() => {});
    $("next-page").disabled =
      data.next_offset === null ||
      data.next_offset === undefined ||
      data.scenario?.kind === "proposed_content";
    $("next-page").onclick = () =>
      window.RepoGraphCanvas.request?.({ offset: data.next_offset }).catch(
        () => {},
      );
    $("title").textContent =
      view === "impact"
        ? data.scenario
          ? "Explore a change before you make it."
          : "Understand the ripple effect."
        : "A clearer view of your code.";
    if (data.impact)
      $("subtitle").textContent =
        "Follow potential dependents, with the source evidence behind every step.";
    initialInspector();
    render();
    requestAnimationFrame(fit);
    const observer = new ResizeObserver(() => fit());
    observer.observe($("viewport"));
    dispose = () => observer.disconnect();
    document.dispatchEvent(
      new CustomEvent("repograph:mounted", { detail: data }),
    );
  }
  const initial = JSON.parse(
    document.getElementById("canvas-data").textContent,
  );
  if (initial) mount(initial);
  else
    document.getElementById("bridge-status").textContent =
      "Waiting for the host to deliver repository analysis…";
})();
