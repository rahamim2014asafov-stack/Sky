# Search URLs lose valid filter values

This is a synthetic, AI-assisted demonstration, not a customer incident.

## Reproduction

`buildQuery({ page: 0, archived: false, search: "" })` returns an empty string in the original code. The expected result is `page=0&archived=false&search=`: these values have explicit meaning to the receiving endpoint.

An array such as `{ tag: ["a,b", "python"] }` also loses its structure when converted to a single comma-separated value.

## Cause and change

Filtering on truthiness removes more than missing values. Passing arrays directly to `URLSearchParams` also stringifies them. The correction skips only `null` and `undefined`, appends array items individually, and lets `URLSearchParams` handle escaping.

## Acceptance criteria

- Return an encoded query string without the leading `?`.
- Accept string, finite-number, and boolean values, plus arrays of those values.
- Keep `0`, `false`, and the empty string.
- Omit nullish values, including inside arrays; an empty array adds no parameters.
- Preserve parameter order, array order, and duplicates.
- Reject unsupported values instead of silently producing misleading strings.
- Leave the input unchanged and escape reserved characters.

## Files and verification

- [Original](before.mjs), [correction](after.mjs), [patch](fix.patch).
- [Nine regression tests](test_query.mjs), run against both versions.
- From the repository root: `node --test examples/js_query_filters/test_query.mjs`.
- Set `DEMO_VERSION=before` to reproduce the failing original behavior on Unix-like shells.

## Scope

The caller supplies a plain object with enumerable string keys. This contract uses repeated keys for multiple selections; the receiving API must support that convention. It does not implement a universal serializer for APIs using bracketed keys, comma-separated lists, or nested objects. It performs no HTTP requests.
