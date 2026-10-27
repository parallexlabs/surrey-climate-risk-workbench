/* Surrey Climate Risk Workbench: renders the derived data in data.js. No network requests. */
(function () {
  "use strict";
  var D = window.WORKBENCH;
  var F = D.frame;
  var SVGNS = "http://www.w3.org/2000/svg";
  var $ = function (id) { return document.getElementById(id); };
  var fmt = function (n, d) { return Number(n).toLocaleString("en-CA", { maximumFractionDigits: d || 0, minimumFractionDigits: d || 0 }); };
  var title = function (s) { return String(s).toLowerCase().replace(/\b\w/g, function (c) { return c.toUpperCase(); }); };

  $("built").textContent = "Built " + (D.metrics.built_at || "").slice(0, 10) + ".";

  /* ---------- tabs ---------- */
  var tabs = Array.prototype.slice.call(document.querySelectorAll('[role="tab"]'));
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { select(i); });
    t.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        var j = (i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length;
        select(j); tabs[j].focus();
      }
    });
  });
  function select(i) {
    tabs.forEach(function (t, k) {
      t.setAttribute("aria-selected", k === i ? "true" : "false");
      t.tabIndex = k === i ? 0 : -1;
      $(t.getAttribute("aria-controls")).hidden = k !== i;
    });
  }
  select(0);

  /* ---------- map ---------- */
  var svg = $("map");
  svg.setAttribute("viewBox", "0 0 " + F.width + " " + F.height);
  function pathOf(rings) {
    return rings.map(function (r) { return "M" + r.map(function (p) { return p[0] + " " + p[1]; }).join("L") + "Z"; }).join("");
  }
  function group(id) { var g = document.createElementNS(SVGNS, "g"); g.setAttribute("id", "g-" + id); svg.appendChild(g); return g; }
  function poly(g, rings, fill, stroke, opacity, width) {
    var p = document.createElementNS(SVGNS, "path");
    p.setAttribute("d", pathOf(rings)); p.setAttribute("fill", fill); p.setAttribute("fill-rule", "evenodd");
    p.setAttribute("fill-opacity", opacity); p.setAttribute("stroke", stroke); p.setAttribute("stroke-width", width || 0);
    g.appendChild(p);
  }
  var css = getComputedStyle(document.documentElement);
  var C = function (v) { return css.getPropertyValue(v).trim(); };
  var L = D.layers;
  var gCity = group("city"); L.city.forEach(function (r) { poly(gCity, r, "#ffffff", "#7d8b93", 1, 30); });
  /* hazard and natural-area layers reach past the city edge; clip them to it */
  var defs = document.createElementNS(SVGNS, "defs"), clip = document.createElementNS(SVGNS, "clipPath");
  clip.setAttribute("id", "cityclip");
  L.city.forEach(function (r) { var cp = document.createElementNS(SVGNS, "path"); cp.setAttribute("d", pathOf(r)); cp.setAttribute("clip-rule", "evenodd"); clip.appendChild(cp); });
  defs.appendChild(clip); svg.insertBefore(defs, svg.firstChild);
  function clipped(id) { var g = group(id); g.setAttribute("clip-path", "url(#cityclip)"); return g; }
  var gNatural = clipped("natural"); L.natural.forEach(function (r) { poly(gNatural, r, C("--natural"), "none", 0.45); });
  var gFlood = clipped("flood"); L.floodplain.forEach(function (r) { poly(gFlood, r, C("--flood"), "none", 0.5); });
  var gSteep = clipped("steep"); L.steep.forEach(function (r) { poly(gSteep, r, C("--steep"), "none", 0.55); });
  var gFire = clipped("fire"); L.wildfire.forEach(function (w) { poly(gFire, w.rings, C("--fire"), C("--fire"), w.cls >= 7 ? 0.85 : 0.55, 6); });
  var gComm = group("communities");
  L.communities.forEach(function (c) { poly(gComm, c.rings, "none", "#33424b", 0, 22); });
  L.communities.forEach(function (c) {
    var xs = [], ys = [];
    c.rings[0].forEach(function (p) { xs.push(p[0]); ys.push(p[1]); });
    var t = document.createElementNS(SVGNS, "text");
    t.setAttribute("x", (Math.min.apply(null, xs) + Math.max.apply(null, xs)) / 2);
    t.setAttribute("y", (Math.min.apply(null, ys) + Math.max.apply(null, ys)) / 2);
    t.setAttribute("text-anchor", "middle"); t.setAttribute("font-size", "420"); t.setAttribute("fill", "#33424b");
    t.setAttribute("paint-order", "stroke"); t.setAttribute("stroke", "#ffffff"); t.setAttribute("stroke-width", "90");
    t.textContent = title(c.name); gComm.appendChild(t);
  });
  var KINDS = { "fire halls": "#b3261e", "emergency services": "#7a1f5c", "drainage pump stations": "#1f5f8b",
    "water utility facilities": "#2a7f8f", "schools": "#5b4a8a", "community-based organizations": "#8a6a1f" };
  var gServices = group("services");
  D.services.forEach(function (s) {
    var c = document.createElementNS(SVGNS, "circle");
    c.setAttribute("cx", s.sx); c.setAttribute("cy", s.sy); c.setAttribute("r", 130);
    c.setAttribute("fill", KINDS[s.kind] || "#333"); c.setAttribute("stroke", "#fff"); c.setAttribute("stroke-width", 35);
    c.setAttribute("data-kind", s.kind);
    var tt = document.createElementNS(SVGNS, "title"); tt.textContent = title(s.kind) + ": " + (s.name || "unnamed"); c.appendChild(tt);
    gServices.appendChild(c);
  });
  var gDykes = group("dykes");
  L.dykes.forEach(function (p) {
    var r = document.createElementNS(SVGNS, "rect");
    r.setAttribute("x", p[0] - 40); r.setAttribute("y", p[1] - 40); r.setAttribute("width", 80); r.setAttribute("height", 80);
    r.setAttribute("fill", "#4a5961"); gDykes.appendChild(r);
  });
  var gPin = group("pin");
  /* scale bar: 2 km */
  var sb = group("scale");
  var sx = 600, sy = F.height - 600;
  [[sx, sy, 2000, 90, "#22313a"], [sx, sy, 1000, 90, "#ffffff"]].forEach(function (b) {
    var r = document.createElementNS(SVGNS, "rect"); r.setAttribute("x", b[0]); r.setAttribute("y", b[1]);
    r.setAttribute("width", b[2]); r.setAttribute("height", b[3]); r.setAttribute("fill", b[4]); r.setAttribute("stroke", "#22313a"); r.setAttribute("stroke-width", 20); sb.appendChild(r);
  });
  var st = document.createElementNS(SVGNS, "text"); st.setAttribute("x", sx); st.setAttribute("y", sy - 80); st.setAttribute("font-size", "300"); st.textContent = "2 km"; sb.appendChild(st);

  var TOGGLES = [
    ["flood", "200-year floodplain", C("--flood")], ["steep", "Steep slope hazard lands", C("--steep")],
    ["fire", "Wildfire threat, moderate or high (public land)", C("--fire")], ["natural", "Park natural areas", C("--natural")],
    ["services", "Service sites", "#5b4a8a"], ["dykes", "Dyke records", "#22313a"], ["communities", "Communities", "#33424b"]
  ];
  TOGGLES.forEach(function (t) {
    var b = document.createElement("button"); b.type = "button"; b.setAttribute("aria-pressed", "true");
    var sw = document.createElement("span"); sw.className = "swatch"; sw.style.background = t[2];
    b.appendChild(sw); b.appendChild(document.createTextNode(t[1]));
    b.addEventListener("click", function () {
      var on = b.getAttribute("aria-pressed") !== "true";
      b.setAttribute("aria-pressed", on ? "true" : "false");
      $("g-" + t[0]).style.display = on ? "" : "none";
    });
    $("toggles").appendChild(b);
  });

  /* ---------- screening ---------- */
  function inRings(x, y, rings) {
    var inside = false;
    rings.forEach(function (ring) {
      for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        var xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
        if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
      }
    });
    return inside;
  }
  function segDist(px, py, ax, ay, bx, by) {
    var dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
    var t = l2 ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l2)) : 0;
    var qx = ax + t * dx - px, qy = ay + t * dy - py;
    return Math.sqrt(qx * qx + qy * qy);
  }
  function distTo(x, y, rings) {
    if (inRings(x, y, rings)) return 0;
    var best = Infinity;
    rings.forEach(function (r) { for (var i = 0, j = r.length - 1; i < r.length; j = i++) best = Math.min(best, segDist(x, y, r[j][0], r[j][1], r[i][0], r[i][1])); });
    return best;
  }
  var commBySize = L.communities.slice().sort(function (a, b) { return area(a.rings) - area(b.rings); });
  function area(rings) { var s = 0; rings.forEach(function (r) { for (var i = 0, j = r.length - 1; i < r.length; j = i++) s += (r[j][0] * r[i][1] - r[i][0] * r[j][1]); }); return Math.abs(s / 2); }

  function screen(sx, sy) {
    var E = F.x0 + sx, N = F.y1 - sy;
    $("in-x").value = Math.round(E); $("in-y").value = Math.round(N);
    gPin.innerHTML = "";
    var pin = document.createElementNS(SVGNS, "circle");
    pin.setAttribute("cx", sx); pin.setAttribute("cy", sy); pin.setAttribute("r", 170); pin.setAttribute("fill", "none");
    pin.setAttribute("stroke", "#111"); pin.setAttribute("stroke-width", 60); gPin.appendChild(pin);
    var comm = commBySize.filter(function (c) { return inRings(sx, sy, c.rings); })[0];
    var flood = L.floodplain.some(function (r) { return inRings(sx, sy, r); });
    var steep = L.steep.some(function (r) { return inRings(sx, sy, r); });
    var fireD = Math.min.apply(null, L.wildfire.map(function (w) { return distTo(sx, sy, w.rings); }).concat([Infinity]));
    var natD = Math.min.apply(null, L.natural.map(function (r) { return distTo(sx, sy, r); }).concat([Infinity]));
    var g = D.elevation_grid_m, key = Math.floor(sx / g) + "," + Math.floor(sy / g), elev = D.elevation[key];
    var halls = D.services.filter(function (s) { return s.kind === "fire halls"; });
    var hallD = Math.min.apply(null, halls.map(function (s) { return Math.hypot(s.sx - sx, s.sy - sy); }));
    var low = elev === undefined ? null : elev <= D.metrics.parameters.low_ground_m;
    function row(state, text) { return '<li><span class="' + state[0] + '">' + state[1] + "</span><span>" + text + "</span></li>"; }
    var Y = ["yes", "Yes"], N0 = ["no", "No"], A = ["ask", "Project"];
    var out = "";
    if (!comm) { $("screen-out").innerHTML = '<p class="notice">That point is outside Surrey\'s nine communities.</p>'; return; }
    out += "<p><strong>" + title(comm.name) + "</strong>, at " + fmt(E) + " E, " + fmt(N) + " N (UTM 10N).</p>";
    out += '<ul class="check">';
    out += row(flood ? Y : N0, "Inside the City's mapped 200-year floodplain." + (flood ? " Check flood construction levels and floodproofing with the City's engineering staff." : ""));
    out += row(low === null ? A : (low ? Y : N0), low === null ? "Ground elevation: no nearby building elevations to estimate it." : "Ground at or below " + D.metrics.parameters.low_ground_m + " m (median of nearby buildings, " + fmt(elev, 1) + " m, datum as published). Low ground is where sea level rise and heavier rain reach first.");
    out += row(steep ? Y : N0, "Inside the steep slope hazard lands or their 10 to 30 m buffer." + (steep ? " A geotechnical review is the usual next step." : ""));
    out += row(fireD <= D.metrics.parameters.wildfire_near_m ? Y : N0, "Within " + D.metrics.parameters.wildfire_near_m + " m of moderate or high provincial wildfire threat (public land only; nearest " + (isFinite(fireD) ? fmt(fireD) + " m" : "none") + ").");
    out += row(natD <= D.metrics.parameters.interface_near_m ? Y : N0, "Within " + D.metrics.parameters.interface_near_m + " m of a park natural area (nearest " + fmt(natD) + " m): interface vegetation and ember exposure.");
    out += row(["ask", fmt(hallD) + " m"], "Straight-line distance to the nearest fire hall.");
    out += row(A, "Will the asset still be in service after 2050, when the hazards above are larger?");
    out += row(A, "Does it serve or house people more sensitive to heat, smoke or flooding (older adults, young children, people living alone)?");
    out += row(A, "Is it needed during or right after an emergency?");
    out += "</ul><p class=\"muted\">Screening only: a yes means look closer, not that the site is unsafe. Distances use simplified map shapes.</p>";
    $("screen-out").innerHTML = out;
  }
  svg.addEventListener("click", function (e) {
    var pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
    var p = pt.matrixTransform(svg.getScreenCTM().inverse());
    screen(p.x, p.y);
  });
  $("screen-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var E = Number($("in-x").value), N = Number($("in-y").value);
    if (isFinite(E) && isFinite(N) && E && N) screen(E - F.x0, F.y1 - N);
  });

  /* ---------- register ---------- */
  var R = D.register;
  var lik = {};
  Object.keys(R.hazards).forEach(function (k) { lik[k] = R.hazards[k].likelihood; });
  var LIK_LABELS = ["1 Rare", "2 Unlikely", "3 Possible", "4 Likely", "5 Almost certain"];
  Object.keys(R.hazards).forEach(function (k) {
    var lab = document.createElement("label");
    lab.innerHTML = "Likelihood: " + R.hazards[k].name;
    var s = document.createElement("select");
    LIK_LABELS.forEach(function (t, i) { var o = document.createElement("option"); o.value = i + 1; o.textContent = t; s.appendChild(o); });
    s.value = lik[k];
    s.addEventListener("change", function () { lik[k] = Number(s.value); renderRegister(); });
    lab.appendChild(s); $("lik-controls").appendChild(lab);
  });
  function cls(score) { for (var i = 0; i < R.classes.length; i++) if (score <= R.classes[i][0]) return R.classes[i][1]; return "Very high"; }
  var current = [];
  function renderRegister() {
    current = R.rows.map(function (r) {
      var score = lik[r.hazard] * r.consequence;
      return Object.assign({}, r, { likelihood: lik[r.hazard], score: score, "class": cls(score) });
    }).sort(function (a, b) { return b.score - a.score || ({ High: 0, Medium: 1, Low: 2 }[a.confidence] - { High: 0, Medium: 1, Low: 2 }[b.confidence]); });
    var h = '<thead><tr><th class="num">Rank</th><th>Hazard</th><th>Value area</th><th class="num">Exposure</th><th class="num">L</th><th class="num">C</th><th class="num">Score</th><th>Class</th><th>Confidence</th><th>Most exposed communities</th></tr></thead><tbody>';
    current.forEach(function (r, i) {
      var top = Object.keys(r.by_community).filter(function (n) { return r.by_community[n] > 0 && n !== "null"; })
        .sort(function (a, b) { return r.by_community[b] - r.by_community[a]; }).slice(0, 3).map(title).join(", ");
      var unit = r.unit === "share of the city's buildings" ? "%" : (r.unit === "sites" ? " sites" : " ha");
      h += "<tr><td class=\"num\">" + (i + 1) + "</td><td>" + r.hazard_name + "</td><td>" + r.value_area_name + "</td><td class=\"num\">" +
        fmt(r.exposure, unit === "%" ? 2 : (unit === " ha" ? 1 : 0)) + unit + "</td><td class=\"num\">" + r.likelihood + "</td><td class=\"num\">" + r.consequence +
        "</td><td class=\"num\">" + r.score + "</td><td><span class=\"cls cls-" + r["class"].replace(" ", "-") + "\">" + r["class"] + "</span></td><td>" + r.confidence + "</td><td>" + (top || "none") + "</td></tr>" +
        (r.note ? '<tr class="note"><td></td><td colspan="9" class="muted">' + r.note + "</td></tr>" : "");
    });
    $("reg-table").innerHTML = h + "</tbody>";
    var m = "<div></div>";
    for (var c = 1; c <= 5; c++) m += "<div><strong>C" + c + "</strong></div>";
    for (var l = 5; l >= 1; l--) {
      m += "<div><strong>L" + l + "</strong></div>";
      for (c = 1; c <= 5; c++) {
        var n = current.filter(function (r) { return r.likelihood === l && r.consequence === c; }).length;
        m += '<div class="cls-' + cls(l * c).replace(" ", "-") + '">' + (n || "") + "</div>";
      }
    }
    $("matrix").innerHTML = m;
  }
  renderRegister();
  $("not-assessed").innerHTML = R.not_assessed.map(function (n) { return "<li><strong>" + n.hazard + ".</strong> " + n.why + "</li>"; }).join("");
  $("csv").addEventListener("click", function () {
    var lines = [["rank", "hazard", "value area", "exposure", "unit", "likelihood", "consequence", "score", "class", "confidence"]];
    current.forEach(function (r, i) { lines.push([i + 1, r.hazard_name, r.value_area_name, r.exposure, r.unit, r.likelihood, r.consequence, r.score, r["class"], r.confidence]); });
    var text = lines.map(function (row) { return row.map(function (v) { v = String(v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }).join(","); }).join("\n");
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
    a.download = "surrey-climate-risk-register.csv"; document.body.appendChild(a); a.click(); a.remove();
  });

  /* ---------- communities ---------- */
  var M = D.metrics.communities;
  var ch = '<thead><tr><th>Community</th><th class="num">Buildings</th><th class="num">200-year floodplain</th><th class="num">Ground at or below 3 m</th><th class="num">Steep slope</th><th class="num">Near wildfire threat</th><th class="num">Near natural areas</th><th class="num">Service sites in floodplain</th><th class="num">Tree canopy</th></tr></thead><tbody>';
  Object.keys(M).sort(function (a, b) { return M[b].flood / M[b].buildings - M[a].flood / M[a].buildings; }).forEach(function (n) {
    var c = M[n], b = c.buildings || 1, pct = function (k) { return fmt(100 * c[k] / b, 1) + "%"; };
    var sites = D.services.filter(function (s) { return s.community === n && s.flood; }).length;
    ch += "<tr><td>" + title(n) + '</td><td class="num">' + fmt(c.buildings) + '</td><td class="num">' + pct("flood") + '</td><td class="num">' + pct("low") +
      '</td><td class="num">' + pct("steep") + '</td><td class="num">' + pct("wildfire") + '</td><td class="num">' + pct("interface") + '</td><td class="num">' + sites +
      '</td><td class="num">' + (c.canopy_pct === null ? "n/a" : fmt(c.canopy_pct, 1) + "%") + "</td></tr>";
  });
  $("comm-table").innerHTML = ch + "</tbody>";

  /* ---------- inventory ---------- */
  var ih = "<thead><tr><th>Source</th><th>Provider and licence</th><th>Form</th><th>Retrieved</th><th>Hazards</th><th>Status</th><th>Use and limits</th></tr></thead><tbody>";
  D.inventory.forEach(function (r) {
    ih += "<tr><td>" + r.source + "</td><td>" + r.provider + "<br><span class=\"muted\">" + r.licence + "</span></td><td>" + r.form + "</td><td>" + r.retrieved +
      "</td><td>" + r.hazards + "</td><td>" + r.status + "</td><td>" + r.use + " <span class=\"muted\">" + r.limits + "</span></td></tr>";
  });
  $("inv-table").innerHTML = ih + "</tbody>";

  /* ---------- method ---------- */
  var P = D.metrics.parameters;
  $("method").innerHTML =
    "<h2>Method and limits</h2>" +
    "<h3>What is measured</h3><p>Each of the City's " + fmt(Object.keys(M).reduce(function (s, n) { return s + M[n].buildings; }, 0)) +
    " building footprints is placed at its centroid and tested against the 200-year floodplain, the steep slope hazard lands (with their buffer) and, by a " + P.raster_cell_m +
    " m grid, the distance to moderate or high provincial wildfire threat (" + P.wildfire_near_m + " m) and to park natural areas (" + P.interface_near_m +
    " m). Service sites and natural areas get the same tests. Ground at or below " + P.low_ground_m + " m uses the City's published building ground elevation, datum as published.</p>" +
    "<h3>How the register is rated</h3><p>Score = likelihood × consequence on a 5 by 5 matrix. Consequence comes from measured exposure through stated bins (buildings: share of the city's buildings; services: number of sites; natural areas: hectares). Likelihood is a stated default per hazard that the assessment team sets with the City, under its chosen time horizons and climate scenarios. Confidence reflects the source: High for the City's mapped layers, Medium where the provincial wildfire layer leaves private land unrated.</p>" +
    "<h3>What it is not</h3><p>It models no flood depth, no damage, no probability under future climate and no social vulnerability yet. People enter in the next pass, through dissemination-area census data and, during an assessment, the City's own Social Vulnerability Index. The wildfire layer does not rate private land, so private-land interface exposure is not measured. It is a prototype built from public data; it is not the City's assessment and is not endorsed by the City.</p>" +
    "<h3>Reproduce it</h3><p>Every input page is saved with its address, retrieval time and SHA-256; one script rebuilds every figure on this page from those inputs.</p>";
})();
