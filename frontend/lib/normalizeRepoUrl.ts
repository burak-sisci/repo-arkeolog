/** GitHub repo girişini backend'in beklediği tam URL'ye çevirir (tarayıcı url doğrulamasını baypas etmek için). */
export function normalizeRepoUrl(raw: string): string {
  let u = raw.trim().replace(/^["']|["']$/g, "");
  if (!u) return u;
  if (!/^https?:\/\//i.test(u)) {
    u = `https://${u}`;
  }
  try {
    const parsed = new URL(u);
    const path = parsed.pathname.replace(/\/+$/, "") || "";
    return `${parsed.origin}${path}${parsed.search}${parsed.hash}`;
  } catch {
    return u.replace(/\/+$/, "");
  }
}
