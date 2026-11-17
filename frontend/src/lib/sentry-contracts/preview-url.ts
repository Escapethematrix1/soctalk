/**
 * Canonicalise the RH Sentry demonstration URL without leaking attribution
 * tags into the visible browser address. Preserve genuine route parameters
 * and the URL fragment; strip only conventional marketing UTM keys.
 */
export function canonicalSentryPreviewPath(url: URL): string | null {
	const result = new URL(url);
	let removed = false;
	for (const key of [...result.searchParams.keys()]) {
		if (key.toLowerCase().startsWith('utm_')) {
			result.searchParams.delete(key);
			removed = true;
		}
	}
	if (!removed) return null;
	return result.pathname + result.search + result.hash;
}
