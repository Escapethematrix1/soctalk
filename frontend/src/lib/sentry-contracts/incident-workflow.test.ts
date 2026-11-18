import { describe, expect, it } from 'vitest';
import { CASE_STAGES, nextCaseAction, nextCaseStatuses, orderCasesForTriage } from './incident-workflow';
import type { LabCase } from '$lib/sentry-lab/scope';
import type { CaseWorkContext } from './incident-workflow';

const incident: LabCase = {
	id:'SEN-DEMO',tenantId:'alderwick',title:'Fictional alert',
	severity:'high',status:'investigating',version:1,assignedTo:'alderwick-analyst'
};
const context: CaseWorkContext = {
	tenantId:'alderwick',incidentId:'SEN-DEMO',incidentVersion:1,
	evidence:{analystNoteCount:1,verifiedTelemetryCount:0},
	assets:[],responses:{pending:0,approvedDryRun:0,rejected:0,recordedDryRuns:0},
	caseChangeCount:1,dataSource:'local-sqlite-fictional',
	liveTelemetry:false,aiInference:false,responseExecution:false
};
const withIncident = (details: Partial<LabCase>): LabCase => ({...incident,...details});
const withContext = (details: Partial<CaseWorkContext>): CaseWorkContext =>
	({...context,...details});

describe('guided RH Sentry incident workflow', () => {
	it('keeps only four focused operator stages', () => {
		expect(CASE_STAGES.map((item) => item.id)).toEqual(['review','evidence','decision','response']);
	});
	it('makes customer viewers read-only and fails closed when context is missing', () => {
		expect(nextCaseAction(incident,context,false).stage).toBe('review');
		expect(nextCaseAction(incident,context,false).explanation).toContain('read-only');
		expect(nextCaseAction(incident,null,true).stage).toBe('review');
		expect(nextCaseAction(incident,null,true).explanation).toContain('not yet verified');
	});
	it('selects an owner before advancing an unassigned case', () => {
		const suggestion = nextCaseAction(withIncident({assignedTo:null}),context,true);
		expect(suggestion.stage).toBe('decision');
		expect(suggestion.label).toContain('owner');
	});
	it('prioritises triage then evidence, then pending independent approval', () => {
		expect(nextCaseAction(withIncident({status:'triage'}),context,true).stage).toBe('decision');
		expect(nextCaseAction(incident,
			withContext({evidence:{analystNoteCount:0,verifiedTelemetryCount:0}}),true).stage).toBe('evidence');
		const result=nextCaseAction(incident,
			withContext({responses:{pending:1,approvedDryRun:0,rejected:0,recordedDryRuns:0}}),true);
		expect(result.stage).toBe('response');
		expect(result.explanation).toContain('no live action');
	});
	it('does not confuse closed cases or fictional approvals with verified containment', () => {
		expect(nextCaseAction(withIncident({status:'closed'}),context,true).explanation).toContain('not proof');
		expect(nextCaseAction(withIncident({status:'contained'}),context,true).stage).toBe('decision');
		const approved=nextCaseAction(incident,
			withContext({responses:{pending:0,approvedDryRun:1,rejected:0,recordedDryRuns:1}}),true);
		expect(approved.explanation).toContain('not evidence');
	});
	it('limits local status selectors to valid adjacent workflow transitions', () => {
		expect(nextCaseStatuses('triage')).toEqual(['triage','investigating']);
		expect(nextCaseStatuses('investigating')).toEqual(['investigating','contained']);
		expect(nextCaseStatuses('contained')).toEqual(['contained','closed']);
		expect(nextCaseStatuses('closed')).toEqual(['closed']);
		expect(nextCaseStatuses('unknown')).toEqual(['unknown']);
	});
	it('orders active unassigned cases before assigned or closed cases without editing input', () => {
		const closed=withIncident({id:'C',status:'closed'});
		const assigned=withIncident({id:'B',severity:'critical'});
		const unassigned=withIncident({id:'A',assignedTo:null,severity:'medium'});
		const input=[closed,assigned,unassigned];
		expect(orderCasesForTriage(input).map((item)=>item.id)).toEqual(['A','B','C']);
		expect(input[0]).toBe(closed);
	});
});
