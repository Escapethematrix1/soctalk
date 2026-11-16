import type { DemoIncident } from './types';

/**
 * RH Sentry browser-only fixtures.
 * This is NOT tenant isolation; production must enforce authorisation server-side.
 */
export interface DemoCustomer {
	id: string;
	name: string;
	sector: string;
	region: string;
	sectorCode: string;
	exampleAssets: number;
	demoContact: string;
}

export const demoCustomers: DemoCustomer[] = [
	{ id: 'alderwick', name: 'Alderwick Logistics', sector: 'Transport & logistics', region: 'Northern Ireland', sectorCode: 'AL', exampleAssets: 48, demoContact: 'security@alderwick.demo.invalid' },
	{ id: 'harbourline', name: 'Harbourline Legal', sector: 'Professional services', region: 'United Kingdom', sectorCode: 'HL', exampleAssets: 32, demoContact: 'it@harbourline.demo.invalid' },
	{ id: 'summit', name: 'Summit Retail', sector: 'Retail & e-commerce', region: 'United Kingdom', sectorCode: 'SR', exampleAssets: 79, demoContact: 'support@summit.demo.invalid' }
];

export function incidentsForDemoCustomer(incidents: DemoIncident[], customerId: string): DemoIncident[] {
	return incidents.filter((incident) => incident.tenantId === customerId);
}
