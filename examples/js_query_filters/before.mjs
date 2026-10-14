// Original demonstration implementation: drops falsy filters.
export function buildQuery(params) {
  return new URLSearchParams(
    Object.entries(params).filter(([, value]) => value),
  ).toString();
}
