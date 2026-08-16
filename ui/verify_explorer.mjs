/**
 * Smoke check for policy_explorer.html — run it, don't just read it.
 *
 *   node ui/verify_explorer.mjs [<v2 spec dir> <v1 spec dir> <policy doc.md>]
 *
 * The explorer is a single self-contained HTML file with no build step and no
 * test runner, so this pulls its <script> out, runs it against a stub DOM, and
 * drives the data pipeline (load -> derive -> filter -> match) over real specs
 * in both formats. It asserts the things that would silently break the tool:
 * that a spec loads at all, that its items survive the default filters, and
 * that their references can be located in the policy document.
 *
 * v1 specs quote an HTML rendering of the document (`<strong>own data</strong>`)
 * while the document itself is markdown, so their references are expected to
 * match as `fuzzy` rather than `exact`. v2 quotes the markdown verbatim, so its
 * references must match `exact`.
 */

import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const HTML = join(HERE, "policy_explorer.html");

// ---------- stub DOM ----------------------------------------------------------
// The explorer wires event handlers at load time. None of that matters here; it
// just has to not throw.
const noop = () => {};
const fakeList = [];
fakeList.forEach = noop;

function fakeEl() {
  const target = {
    classList: { add: noop, remove: noop, toggle: noop, contains: () => false },
    style: {},
    dataset: {},
    children: [],
    innerHTML: "",
    textContent: "",
    value: "",
    querySelectorAll: () => fakeList,
    querySelector: () => null,
    addEventListener: noop,
    removeEventListener: noop,
    appendChild: noop,
    remove: noop,
    getBoundingClientRect: () => ({ top: 0, left: 0, width: 0, height: 0 }),
    scrollIntoView: noop,
    closest: () => null,
    setAttribute: noop,
    getAttribute: () => null,
    focus: noop,
  };
  return new Proxy(target, {
    get(t, k) {
      if (k in t) return t[k];
      return undefined;
    },
    set(t, k, v) {
      t[k] = v;
      return true;
    },
  });
}

const document = {
  getElementById: () => fakeEl(),
  querySelectorAll: () => fakeList,
  querySelector: () => null,
  createElement: () => fakeEl(),
  addEventListener: noop,
  body: fakeEl(),
};
const window = { addEventListener: noop, getComputedStyle: () => ({}) };

// ---------- load the explorer's script --------------------------------------
const html = readFileSync(HTML, "utf8");
const open = html.indexOf("<script>");
const close = html.lastIndexOf("</script>");
if (open === -1 || close === -1) {
  throw new Error("policy_explorer.html has no inline <script> to check");
}
const source = html.slice(open + "<script>".length, close);

const api = new Function(
  "document",
  "window",
  `${source}
   return { state, classifyAndStore, rebuildDerived, passesFilters, matchRef,
            refStats, reqChips, visiblePoliciesFor };`,
)(document, window);

// ---------- fixtures ---------------------------------------------------------
const BENCH = "/Users/naamazwerdling/workspace/evaluate-tool-guard/benchmarks/employee";
const [v2Dir, v1Dir, docPath] = [
  process.argv[2] || join(BENCH, "ground_truth/step1"),
  process.argv[3] || join(BENCH, "outputs/claude-sonnet-4-6/step1_v1"),
  process.argv[4] || join(BENCH, "inputs/employee_policy_doc.md"),
];

const failures = [];
const check = (label, cond, detail = "") => {
  if (cond) {
    console.log(`  ok    ${label}${detail ? ` — ${detail}` : ""}`);
  } else {
    failures.push(label);
    console.log(`  FAIL  ${label}${detail ? ` — ${detail}` : ""}`);
  }
};

function loadDir(dir) {
  api.state.specs = [];
  const files = readdirSync(dir).filter((f) => f.endsWith(".json"));
  let loaded = 0;
  for (const f of files) {
    if (api.classifyAndStore(f, join(dir, f), readFileSync(join(dir, f), "utf8"))) {
      loaded += 1;
    }
  }
  api.rebuildDerived();
  return { files: files.length, loaded };
}

function report(kind, dir, expectedMatch) {
  console.log(`\n${kind}  (${dir})`);
  if (!existsSync(dir)) {
    check(`${kind}: directory exists`, false, dir);
    return;
  }
  const { files, loaded } = loadDir(dir);
  check(`${kind}: every spec file is recognised`, loaded === files, `${loaded}/${files}`);
  check(`${kind}: policy items were flattened`, api.state.policies.length > 0,
        `${api.state.policies.length} items`);

  const visible = api.visiblePoliciesFor("all");
  check(`${kind}: all items pass the default filters`,
        visible.length === api.state.policies.length,
        `${visible.length}/${api.state.policies.length}`);

  const tally = { exact: 0, fuzzy: 0, none: 0, nodoc: 0 };
  for (const p of api.state.policies) {
    const st = api.refStats(p);
    for (const k of Object.keys(tally)) tally[k] += st[k];
  }
  const total = tally.exact + tally.fuzzy + tally.none + tally.nodoc;
  check(`${kind}: every reference is located in the document`, tally.none === 0 && tally.nodoc === 0,
        `exact=${tally.exact} fuzzy=${tally.fuzzy} none=${tally.none}`);
  check(`${kind}: references match as ${expectedMatch}`, tally[expectedMatch] > 0,
        `${tally[expectedMatch]} of ${total}`);

  // the requires panel must not claim anything a v1 spec never said
  const chips = api.reqChips(api.state.policies[0].requires);
  check(`${kind}: requires panel renders`, typeof chips === "string" && chips.length > 0);
  return chips;
}

// the document must be loaded first: reference matching needs it
api.classifyAndStore(basename(docPath), docPath, readFileSync(docPath, "utf8"));
api.state.activeDoc = docPath;
api.state.docPinned = true;

const v2Chips = report("v2 (step1 ground truth)", v2Dir, "exact");
const v1Chips = report("v1 (generated)", v1Dir, "fuzzy");

console.log("\nrequires panel, v2 first item:", v2Chips?.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim());
console.log("requires panel, v1 first item:", v1Chips?.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim());

console.log(
  failures.length ? `\n${failures.length} check(s) failed` : "\nall checks passed",
);
process.exit(failures.length ? 1 : 0);
