/*! SwiftBI metrics engine for the browser. MIT License, Christoforos Kapsalis.
 *
 * Evaluates a SwiftBI metric spec over in-memory rows with the same semantics as
 * swiftbi_spec.py (Python) and its to-sql output: star-schema filter flow,
 * ratios of metrics, blank (null) for empty sets and division by zero.
 *
 * Usage inside a dashboard:
 *   const bundle = {...};                       // from `swiftbi_spec.py bundle`
 *   const bi = SwiftBI.engine(bundle.spec, bundle.data);
 *   bi.value("CTR %", [{column: "Segments.segment_name", op: "=", value: "VIP"}]);
 *   bi.table(["Total Revenue", "CTR %"], "CampaignSends.send_date:month", where);
 *   bi.format(0.0412, "0.0%")                   // "4.1%"
 *   bi.describe("CTR %")                        // {name, description, format, color, ...}
 * No dependencies. Works as a plain <script>, an ES module import of the
 * global, or require() in Node/Bun for tests.
 */
(function (root) {
  "use strict";

  function splitRef(ref) {
    if (typeof ref !== "string" || ref.indexOf(".") < 0) return ["", ""];
    const i = ref.indexOf(".");
    return [ref.slice(0, i), ref.slice(i + 1)];
  }

  function pad(n, w) { return String(n).padStart(w, "0"); }

  function timeBucket(value, grain) {
    if (value === null || value === undefined) return null;
    const s = String(value).slice(0, 10);
    const y = Number(s.slice(0, 4)), m = Number(s.slice(5, 7)), d = Number(s.slice(8, 10));
    if (grain === "day") return s;
    if (grain === "month") return pad(y, 4) + "-" + pad(m, 2);
    if (grain === "quarter") return pad(y, 4) + "-Q" + (Math.floor((m - 1) / 3) + 1);
    if (grain === "year") return pad(y, 4);
    if (grain === "week") {
      const t = Date.UTC(y, m - 1, d);
      const dow = (new Date(t).getUTCDay() + 6) % 7; // Monday = 0
      return new Date(t - dow * 864e5).toISOString().slice(0, 10);
    }
    throw new Error("unknown time grain " + grain);
  }

  function match(value, op, target) {
    if (op === "in") return (target || []).some(function (t) { return t === value; });
    if (op === "not in") return !(target || []).some(function (t) { return t === value; });
    if (value === null || value === undefined) return false;
    switch (op) {
      case "=": return value === target;
      case "!=": return value !== target;
      case ">": return value > target;
      case ">=": return value >= target;
      case "<": return value < target;
      case "<=": return value <= target;
    }
    throw new Error("unknown filter op " + op);
  }

  // Formula: [Metric] refs, numbers, + - * / and parentheses. Recursive descent.
  function parseFormula(src) {
    let i = 0;
    function ws() { while (i < src.length && /\s/.test(src[i])) i++; }
    function primary() {
      ws();
      if (src[i] === "(") { i++; const e = expr(); ws(); if (src[i++] !== ")") throw new Error("missing )"); return e; }
      if (src[i] === "[") { const j = src.indexOf("]", i); if (j < 0) throw new Error("missing ]"); const r = src.slice(i + 1, j); i = j + 1; return { ref: r }; }
      if (src[i] === "-" || src[i] === "+") { const op = src[i++]; return { un: op, a: primary() }; }
      const m = /^[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?/.exec(src.slice(i));
      if (!m) throw new Error("unexpected '" + (src[i] || "end") + "' in formula");
      i += m[0].length; return { num: Number(m[0]) };
    }
    function term() { let a = primary(); for (;;) { ws(); const c = src[i]; if (c === "*" || c === "/") { i++; a = { op: c, a: a, b: primary() }; } else return a; } }
    function expr() { let a = term(); for (;;) { ws(); const c = src[i]; if (c === "+" || c === "-") { i++; a = { op: c, a: a, b: term() }; } else return a; } }
    const tree = expr(); ws();
    if (i !== src.length) throw new Error("unexpected '" + src[i] + "' in formula");
    return tree;
  }

  function evalFormula(node, env) {
    if ("num" in node) return node.num;
    if ("ref" in node) return env(node.ref);
    if ("un" in node) { const v = evalFormula(node.a, env); return v === null ? null : (node.un === "-" ? -v : v); }
    const a = evalFormula(node.a, env), b = evalFormula(node.b, env);
    if (node.op === "+" || node.op === "-") {
      if (a === null && b === null) return null;
      return node.op === "+" ? (a || 0) + (b || 0) : (a || 0) - (b || 0);
    }
    if (a === null || b === null) return null;
    if (node.op === "*") return a * b;
    return b === 0 ? null : a / b;
  }

  function format(v, fmt) {
    if (v === null || v === undefined || Number.isNaN(v)) return "";
    fmt = fmt || "#,0.##";
    const pct = fmt.indexOf("%") >= 0;
    const x = pct ? v * 100 : v;
    const m = /0\.(0+)/.exec(fmt);
    const decimals = m ? m[1].length : 0;
    let body = Math.abs(x).toFixed(decimals);
    if (fmt.indexOf(",") >= 0) {
      const parts = body.split(".");
      parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
      body = parts.join(".");
    }
    const sign = x < 0 && Number(body.replace(/,/g, "")) !== 0 ? "-" : "";
    let prefix = "";
    if (!/^[#0]/.test(fmt)) prefix = fmt.split("#")[0].split("0")[0];
    const suffix = pct ? fmt.replace(/^[^%]*/, "") : (/"x"$/.test(fmt) ? "x" : "");
    return sign + prefix + body + suffix;
  }

  function engine(spec, data) {
    const tables = {}; (spec.tables || []).forEach(function (t) { tables[t.name] = t; });
    const metrics = {}; (spec.metrics || []).forEach(function (m) { metrics[m.name] = m; });
    const formulas = {};

    function fkTo(fact, dim) {
      const cols = (tables[fact] && tables[fact].columns) || [];
      for (let i = 0; i < cols.length; i++) {
        const r = splitRef(cols[i].references || "");
        if (r[0] === dim) return [cols[i].name, r[1]];
      }
      return null;
    }

    function rows(table, filters) {
      let rs = data[table] || [];
      filters.forEach(function (f) {
        const ref = splitRef(f.column), ft = ref[0], fc = ref[1];
        const op = f.op || "=", val = f.value, grain = f.grain;
        const get = function (r) { const v = r[fc]; return grain ? timeBucket(v, grain) : v; };
        if (ft === table) { rs = rs.filter(function (r) { return match(get(r), op, val); }); return; }
        const link = fkTo(table, ft);
        if (!link) return; // filter does not reach this table
        const keys = new Set((data[ft] || []).filter(function (d) { return match(get(d), op, val); })
          .map(function (d) { return d[link[1]]; }));
        rs = rs.filter(function (r) { return keys.has(r[link[0]]); });
      });
      return rs;
    }

    function value(name, filters, depth) {
      filters = filters || []; depth = depth || 0;
      if (depth > 50) throw new Error("metric recursion too deep");
      const m = metrics[name];
      if (!m) throw new Error("unknown metric " + name);
      const typ = m.type;
      if (typ === "sum" || typ === "count_distinct" || typ === "min" || typ === "max" || typ === "average") {
        const ref = splitRef(m.column), c = ref[1];
        const vals = rows(ref[0], filters).map(function (r) { return r[c]; })
          .filter(function (v) { return v !== null && v !== undefined; });
        if (!vals.length) return null;
        if (typ === "sum") return vals.reduce(function (a, b) { return a + b; }, 0);
        if (typ === "count_distinct") return new Set(vals).size;
        if (typ === "min") return Math.min.apply(null, vals);
        if (typ === "max") return Math.max.apply(null, vals);
        return vals.reduce(function (a, b) { return a + b; }, 0) / vals.length;
      }
      if (typ === "count_rows") { const n = rows(m.table, filters).length; return n ? n : null; }
      if (typ === "ratio") {
        const num = value(m.numerator, filters, depth + 1), den = value(m.denominator, filters, depth + 1);
        if (num === null || !den) return null;
        return num / den * (m.multiplier === undefined ? 1 : m.multiplier);
      }
      if (typ === "filtered") {
        const extra = (m.filters || []).map(function (f) { return Object.assign({ op: "=" }, f); });
        return value(m.metric, filters.concat(extra), depth + 1);
      }
      if (typ === "formula") {
        if (!formulas[name]) formulas[name] = parseFormula(m.expression);
        return evalFormula(formulas[name], function (r) { return value(r, filters, depth + 1); });
      }
      throw new Error("unknown metric type " + typ);
    }

    function distinct(ref, grain) {
      const r = splitRef(ref), seen = new Set();
      (data[r[0]] || []).forEach(function (row) {
        const v = grain ? timeBucket(row[r[1]], grain) : row[r[1]];
        if (v !== null && v !== undefined) seen.add(v);
      });
      return Array.from(seen).sort(function (a, b) { return a < b ? -1 : a > b ? 1 : 0; });
    }

    function table(names, by, where) {
      where = where || [];
      if (!by) { const o = { _group: "Total" }; names.forEach(function (n) { o[n] = value(n, where); }); return [o]; }
      const i = by.indexOf(":"), ref = i < 0 ? by : by.slice(0, i), grain = i < 0 ? null : by.slice(i + 1);
      return distinct(ref, grain).map(function (v) {
        const f = { column: ref, op: "=", value: v }; if (grain) f.grain = grain;
        const o = { _group: v }; names.forEach(function (n) { o[n] = value(n, where.concat([f])); });
        return o;
      });
    }

    function describe(name) { return Object.assign({}, metrics[name]); }

    return { value: value, table: table, distinct: distinct, format: format, describe: describe,
             metrics: (spec.metrics || []).map(function (m) { return m.name; }) };
  }

  const api = { engine: engine, format: format, timeBucket: timeBucket, version: "0.1.0" };
  if (typeof module === "object" && module.exports) module.exports = api;
  root.SwiftBI = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
