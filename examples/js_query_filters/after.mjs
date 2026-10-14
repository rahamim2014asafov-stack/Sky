// Encode filters while preserving values and repeated selections.
export function buildQuery(params) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const items = Array.isArray(value) ? value : [value];
    for (const item of items) {
      if (item === null || item === undefined) continue;
      const type = typeof item;
      if (
        !["string", "number", "boolean"].includes(type) ||
        (type === "number" && !Number.isFinite(item))
      ) {
        throw new TypeError(`Unsupported query value for ${key}`);
      }
      query.append(key, String(item));
    }
  }
  return query.toString();
}
