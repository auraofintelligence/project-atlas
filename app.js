(() => {
  "use strict";

  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const state = {
    data: null,
    projects: [],
  };

  const byId = (id) => document.getElementById(id);

  function element(tag, options = {}, children = []) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(options)) {
      if (value === undefined || value === null || value === "") continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key === "htmlFor") node.htmlFor = value;
      else if (key.startsWith("data-")) node.setAttribute(key, value);
      else node.setAttribute(key, value);
    }
    for (const child of Array.isArray(children) ? children : [children]) {
      if (child) node.append(child);
    }
    return node;
  }

  function externalLink(label, href, className = "button") {
    return element("a", {
      class: className,
      href,
      target: "_blank",
      rel: "noopener noreferrer",
      text: label,
    });
  }

  function formatDate(value) {
    if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "Build date not evidenced";
    const [year, month, day] = value.split("-");
    return `${Number(day)} ${MONTHS[Number(month) - 1]} ${year}`;
  }

  function dateStamp(project) {
    const label = project.firstBuilt ? `First built: ${formatDate(project.firstBuilt)}` : "First build date not evidenced";
    return element("span", { class: "date-stamp", text: label });
  }

  function truncate(value, length = 205) {
    const text = String(value || "");
    if (text.length <= length) return text;
    const cut = text.slice(0, length).replace(/\s+\S*$/, "");
    return `${cut}...`;
  }

  function titleLink(project, className) {
    return externalLink(project.title, project.publicPage || project.repositoryUrl, className);
  }

  function qrFilename(project) {
    const stem = String(project.name)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
    return `assets/qr/${stem}.svg`;
  }

  function projectSearchText(project) {
    const chunks = [
      project.name,
      project.title,
      project.description,
      ...(project.families || []).map((family) => family.title),
      ...(project.neighbours || []).flatMap((neighbour) => [neighbour.name, neighbour.title, ...(neighbour.labels || [])]),
    ];
    return chunks.join(" ").toLocaleLowerCase("en-AU");
  }

  function relationshipDetails(project) {
    const details = element("details", { class: "relationships" });
    const count = project.relationshipCount || 0;
    const summary = element("summary", {
      text: count ? `Show all ${count} related public project${count === 1 ? "" : "s"}` : "No listed public neighbours",
    });
    details.append(summary);

    if (!count) {
      const explanation = project.name === "project-atlas"
        ? "This is the collection navigator, so it leads to the full public directory without claiming a subject-matter relationship to every entry."
        : "No evidence-backed public relationship was recorded for this project in this audit snapshot.";
      details.append(element("p", { class: "relationship-reason", text: explanation }));
      return details;
    }

    const list = element("ul", { class: "relationship-list" });
    for (const neighbour of project.neighbours) {
      const item = element("li", { class: "relationship-item" });
      item.append(element("span", { class: "relationship-title", text: neighbour.title }));
      const reason = [...(neighbour.labels || []), ...(neighbour.directionalLabels || [])].join("; ");
      item.append(element("span", { class: "relationship-reason", text: reason || "Evidence-backed public relationship" }));
      const actions = element("div", { class: "neighbour-actions" });
      if (neighbour.publicPage) actions.append(externalLink("Public page", neighbour.publicPage));
      actions.append(externalLink("GitHub", neighbour.repositoryUrl));
      item.append(actions);
      list.append(item);
    }
    details.append(list);
    return details;
  }

  function projectCard(project) {
    const card = element("article", { class: "project-card", id: `project-${project.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}` });
    card.append(dateStamp(project));
    const heading = element("h3");
    const link = titleLink(project, "");
    link.removeAttribute("class");
    heading.append(link);
    card.append(heading);
    card.append(element("p", { class: "project-description", text: truncate(project.description) }));

    const meta = element("ul", { class: "card-meta" });
    meta.append(element("li", { text: project.firstBuilt ? `Original build evidence: ${project.buildConfidence || "not stated"}` : "Original build evidence is not yet confirmed" }));
    meta.append(element("li", { text: `${project.relationshipCount || 0} related public project${project.relationshipCount === 1 ? "" : "s"}` }));
    if (project.meaningfulRebuild?.published || project.meaningfulRebuild?.started) {
      const rebuild = project.meaningfulRebuild;
      const releaseDate = rebuild.published || rebuild.started;
      const timing = rebuild.published ? `published ${formatDate(releaseDate)}` : `started ${formatDate(releaseDate)}`;
      const label = rebuild.title || "Current meaningful release";
      const status = rebuild.status ? ` ${rebuild.status}` : "";
      meta.append(element("li", { text: `${label} ${timing}. Original date remains ${formatDate(project.firstBuilt)}.${status}` }));
    }
    card.append(meta);

    if (project.families?.length) {
      const families = element("ul", { class: "family-list", "aria-label": "Project families" });
      for (const family of project.families) families.append(element("li", { text: family.title }));
      card.append(families);
    }

    const actions = element("div", { class: "card-actions" });
    if (project.publicPage) actions.append(externalLink("Visit public page", project.publicPage));
    actions.append(externalLink("View on GitHub", project.repositoryUrl));
    card.append(actions, relationshipDetails(project));
    return card;
  }

  function freshCard(project) {
    const card = element("article", { class: "fresh-card" });
    card.append(dateStamp(project));
    card.append(element("h3", { text: project.title }));
    card.append(element("p", { text: truncate(project.description, 150) }));
    if (project.meaningfulRebuild?.published || project.meaningfulRebuild?.started) {
      const rebuild = project.meaningfulRebuild;
      const releaseDate = rebuild.published || rebuild.started;
      const timing = rebuild.published ? `published ${formatDate(releaseDate)}` : `started ${formatDate(releaseDate)}`;
      const label = rebuild.title || "Current meaningful release";
      const status = rebuild.status ? ` ${rebuild.status}` : "";
      card.append(element("p", { class: "fresh-rebuild", text: `${label} ${timing}. The original build date above has been retained.${status}` }));
    }
    card.append(externalLink(project.publicPage ? "Visit public page" : "View on GitHub", project.publicPage || project.repositoryUrl, "button button-secondary"));
    return card;
  }

  function printProject(project) {
    const url = project.publicPage || project.repositoryUrl;
    const article = element("article", { class: "print-project", "data-qr-url": url });
    const qr = element("div", { class: "qr-slot" });
    qr.append(element("img", {
      src: qrFilename(project),
      alt: `Scannable QR code for ${project.title}`,
      width: "180",
      height: "180",
    }));
    article.append(qr);
    const copy = element("div");
    const heading = element("h3");
    const link = externalLink(project.title, url, "");
    link.removeAttribute("class");
    heading.append(link);
    copy.append(heading);
    copy.append(element("p", { text: project.firstBuilt ? `Original build: ${formatDate(project.firstBuilt)}` : "Original build: not evidenced" }));
    if (project.meaningfulRebuild?.published || project.meaningfulRebuild?.started) {
      const rebuild = project.meaningfulRebuild;
      const releaseDate = rebuild.published || rebuild.started;
      const timing = rebuild.published ? `published ${formatDate(releaseDate)}` : `started ${formatDate(releaseDate)}`;
      copy.append(element("p", { text: `${rebuild.title || "Meaningful rebuild"} ${timing}` }));
    }
    copy.append(element("a", { class: "print-url", href: url, text: url }));
    article.append(copy);
    return article;
  }

  function lineageCard(lineage, projectsByName) {
    const card = element("article", { class: "lineage-card" });
    card.append(element("h3", { text: lineage.title }));
    if (lineage.description) card.append(element("p", { text: lineage.description }));
    const stages = element("ol", { class: "lineage-stages" });
    for (const stage of lineage.stages) {
      const project = projectsByName.get(stage.repository);
      const linkTarget = project?.publicPage || project?.repositoryUrl;
      const item = element("li", { class: "lineage-stage" });
      item.append(element("span", { class: "stage-number", text: String(stage.order) }));
      const copy = element("div");
      copy.append(linkTarget ? externalLink(stage.title, linkTarget, "stage-project") : element("span", { class: "stage-project", text: stage.title }));
      const detail = [stage.role, stage.firstBuilt ? formatDate(stage.firstBuilt) : "Build date not evidenced"].filter(Boolean).join(" | ");
      copy.append(element("span", { class: "stage-role", text: detail }));
      item.append(copy);
      stages.append(item);
    }
    card.append(stages);
    return card;
  }

  function displayCounts(data) {
    const publicPageCount = data.projects.filter((project) => project.publicPage).length;
    const relationshipCount = data.projects.reduce((total, project) => total + (project.relationshipCount || 0), 0);
    byId("audited-count").textContent = String(data.auditedProjectCount);
    byId("public-page-count").textContent = String(publicPageCount);
    byId("relationship-count").textContent = String(relationshipCount);
    byId("date-method").textContent = data.dateMethod;
    const refresh = data.refreshSnapshotDate ? ` Public refresh: ${formatDate(data.refreshSnapshotDate)}.` : "";
    byId("snapshot-note").textContent = `Public audit snapshot: ${data.auditSnapshotDate || "date to be confirmed"}.${refresh} Atlas data generated ${formatDate(data.generatedOn)}.`;
  }

  function buildYearOptions(projects) {
    const select = byId("year-filter");
    const years = [...new Set(projects.map((project) => project.firstBuilt?.slice(0, 4)).filter(Boolean))].sort().reverse();
    for (const year of years) select.append(element("option", { value: year, text: year }));
  }

  function activeFilters() {
    return {
      query: byId("project-search").value.trim().toLocaleLowerCase("en-AU"),
      year: byId("year-filter").value,
      page: byId("page-filter").value,
      connections: byId("connection-filter").value,
      sort: byId("sort-filter").value,
    };
  }

  function filteredProjects() {
    const filters = activeFilters();
    const results = state.projects.filter((project) => {
      if (filters.query && !project._searchText.includes(filters.query)) return false;
      if (filters.year && project.firstBuilt?.slice(0, 4) !== filters.year) return false;
      if (filters.page === "has-page" && !project.publicPage) return false;
      if (filters.page === "github-only" && project.publicPage) return false;
      if (filters.connections === "connected" && !(project.relationshipCount > 0)) return false;
      if (filters.connections === "standalone" && project.relationshipCount > 0) return false;
      return true;
    });

    const dateValue = (project) => project.firstBuilt || "0000-00-00";
    results.sort((left, right) => {
      if (filters.sort === "oldest") return dateValue(left).localeCompare(dateValue(right)) || left.title.localeCompare(right.title, "en-AU");
      if (filters.sort === "connected") return (right.relationshipCount - left.relationshipCount) || dateValue(right).localeCompare(dateValue(left)) || left.title.localeCompare(right.title, "en-AU");
      if (filters.sort === "az") return left.title.localeCompare(right.title, "en-AU");
      return dateValue(right).localeCompare(dateValue(left)) || left.title.localeCompare(right.title, "en-AU");
    });
    return results;
  }

  function renderProjects() {
    const grid = byId("project-grid");
    const projects = filteredProjects();
    grid.replaceChildren();
    const total = state.projects.length;
    byId("results-status").textContent = `Showing ${projects.length} of ${total} public projects.`;
    if (!projects.length) {
      grid.append(element("p", { class: "empty-state", text: "Nothing matches those filters yet. Try clearing one or more filters." }));
      return;
    }
    const fragment = document.createDocumentFragment();
    for (const project of projects) fragment.append(projectCard(project));
    grid.append(fragment);
  }

  function renderFresh(data) {
    const curated = data.projects.filter((project) => project.freshlyCompleted);
    const meaningfulRebuilds = data.projects.filter((project) => project.meaningfulRebuild?.published || project.meaningfulRebuild?.started);
    const fallback = [...data.projects]
      .filter((project) => project.firstBuilt)
      .sort((left, right) => right.firstBuilt.localeCompare(left.firstBuilt))
      .slice(0, 6);
    const featured = [...curated, ...meaningfulRebuilds.filter((project) => !curated.some((item) => item.name === project.name))];
    const projects = featured.length ? featured.sort((left, right) => {
      const leftDate = left.meaningfulRebuild?.published || left.meaningfulRebuild?.started || left.firstBuilt || "0000-00-00";
      const rightDate = right.meaningfulRebuild?.published || right.meaningfulRebuild?.started || right.firstBuilt || "0000-00-00";
      return rightDate.localeCompare(leftDate);
    }) : fallback;
    byId("fresh-explainer").textContent = featured.length
      ? "These are explicitly marked new public projects and meaningful rebuilds from the latest refresh. Their original build dates remain visible, even where a new release has been published."
      : "This first edition is showing the six latest dated builds in the audit. New projects can be explicitly marked here once their public page and original build evidence are confirmed.";
    const grid = byId("fresh-grid");
    grid.replaceChildren(...projects.map(freshCard));
  }

  function renderLineages(data) {
    const grid = byId("lineage-grid");
    const byName = new Map(data.projects.map((project) => [project.name, project]));
    grid.replaceChildren();
    if (!data.lineages?.length) {
      grid.append(element("p", { class: "empty-state", text: "No multi-stage public storylines were supplied with this audit." }));
      return;
    }
    for (const lineage of data.lineages) grid.append(lineageCard(lineage, byName));
  }

  function renderPrintDirectory(projects) {
    const list = byId("print-directory-list");
    const sorted = [...projects].sort((left, right) => left.title.localeCompare(right.title, "en-AU"));
    list.replaceChildren(...sorted.map(printProject));
  }

  function wireInteractions() {
    const filters = byId("filters");
    filters.addEventListener("input", renderProjects);
    filters.addEventListener("change", renderProjects);
    filters.addEventListener("reset", () => window.setTimeout(renderProjects, 0));
    document.querySelectorAll("[data-print]").forEach((button) => {
      button.addEventListener("click", () => window.print());
    });
  }

  function showLoadError(error) {
    const grid = byId("project-grid");
    grid.replaceChildren(element("p", { class: "empty-state", text: "Project data could not be loaded. Please use a local web server or the published Atlas page, then try again." }));
    byId("results-status").textContent = "Data unavailable";
    console.error(error);
  }

  async function initialise() {
    try {
      const response = await fetch("data/projects.json", { cache: "no-store" });
      if (!response.ok) throw new Error(`Project data request failed: ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data.projects) || !data.projects.length) throw new Error("Project data has no projects");
      state.data = data;
      state.projects = data.projects.map((project) => ({ ...project, _searchText: projectSearchText(project) }));
      displayCounts(data);
      buildYearOptions(state.projects);
      renderFresh(data);
      renderProjects();
      renderLineages(data);
      renderPrintDirectory(data.projects);
      wireInteractions();
    } catch (error) {
      showLoadError(error);
    }
  }

  initialise();
})();
