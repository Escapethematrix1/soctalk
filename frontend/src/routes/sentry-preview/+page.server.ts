import { redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { canonicalSentryPreviewPath } from '$lib/sentry-contracts/preview-url';

/** Redirect browser requests to the clean RH Sentry demo URL before rendering. */
export const load: PageServerLoad = ({ url }) => {
	const canonical = canonicalSentryPreviewPath(url);
	if (canonical !== null) {
		redirect(307, canonical);
	}
	return {};
};
