import { describe, expect, it } from 'vitest';
import { canonicalSentryPreviewPath } from './preview-url';

describe('RH Sentry preview URL canonicalisation', () => {
	it('removes tracking attribution without showing it in the visible URL', () => {
		const original = new URL('http://127.0.0.1:5173/sentry-preview?utm_source=chatgpt');
		expect(canonicalSentryPreviewPath(original)).toBe('/sentry-preview');
		expect(original.searchParams.get('utm_source')).toBe('chatgpt');
	});

	it('preserves real search parameters, path and hash', () => {
		const original = new URL('http://127.0.0.1:5173/sentry-preview?utm_source=chatgpt&case=SEN-2048&utm_medium=link#investigations');
		expect(canonicalSentryPreviewPath(original)).toBe('/sentry-preview?case=SEN-2048#investigations');
	});

	it('ignores case differences in tracking keys', () => {
		const original = new URL('http://localhost:5173/sentry-preview?UTM_Source=referral&foo=bar');
		expect(canonicalSentryPreviewPath(original)).toBe('/sentry-preview?foo=bar');
	});

	it('keeps an already-clean address unchanged', () => {
		const original = new URL('http://127.0.0.1:5173/sentry-preview?case=SEN-2048#evidence');
		expect(canonicalSentryPreviewPath(original)).toBeNull();
	});
});
