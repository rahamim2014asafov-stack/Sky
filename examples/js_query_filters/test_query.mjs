import test from "node:test";
import assert from "node:assert/strict";

const version = process.env.DEMO_VERSION ?? "after";
if (!["before", "after"].includes(version)) {
  throw new Error("DEMO_VERSION must be before or after");
}
const { buildQuery } = await import(`./${version}.mjs`);

test("zero, false, and empty strings remain explicit parameters", () => {
  assert.equal(buildQuery({ page: 0, archived: false, search: "" }), "page=0&archived=false&search=");
});

test("ordinary scalar filters retain order", () => {
  assert.equal(buildQuery({ search: "hello world", limit: 25, active: true }), "search=hello+world&limit=25&active=true");
});

test("null and undefined are omitted", () => {
  assert.equal(buildQuery({ absent: null, missing: undefined, status: "open" }), "status=open");
});

test("arrays encode repeated keys, including commas inside one selection", () => {
  const query = new URLSearchParams(buildQuery({ tag: ["a,b", "python", "python"] }));
  assert.deepEqual(query.getAll("tag"), ["a,b", "python", "python"]);
});

test("array values follow the same nullish and falsy rules", () => {
  const query = new URLSearchParams(buildQuery({ value: [null, 0, undefined, false, ""] }));
  assert.deepEqual(query.getAll("value"), ["0", "false", ""]);
});

test("empty arrays and empty parameter objects produce no parameters", () => {
  assert.equal(buildQuery({ tag: [] }), "");
  assert.equal(buildQuery({}), "");
});

test("reserved characters and Unicode round-trip without injecting a parameter", () => {
  const input = { "a&b": "x=y & admin=true", search: "שלום / café +" };
  const query = new URLSearchParams(buildQuery(input));
  assert.deepEqual([...query.entries()], Object.entries(input));
  assert.equal(query.has("admin"), false);
});

test("input arrays and objects are not changed", () => {
  const tags = Object.freeze(["python", "javascript"]);
  const input = Object.freeze({ tag: tags, page: 1 });
  buildQuery(input);
  assert.deepEqual(input, { tag: ["python", "javascript"], page: 1 });
});

test("unsupported objects, nested arrays, and nonfinite numbers are rejected", () => {
  for (const value of [{ a: 1 }, [["nested"]], NaN, Infinity, -Infinity]) {
    assert.throws(() => buildQuery({ value }), TypeError);
  }
});
