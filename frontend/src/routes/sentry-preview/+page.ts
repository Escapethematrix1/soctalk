import { error } from '@sveltejs/kit';

/** The RH Sentry preview has mock data and intentionally no backend.
 *  It must never be treated as an authenticated SOC application.
 *  Keep it unavailable in production builds until real security is ready.
 */
export const load = () => {
	if (!import.meta.env.DEV) {
		throw error(404, 'RH Sentry preview is available in development only');
	}
	return {};
};
