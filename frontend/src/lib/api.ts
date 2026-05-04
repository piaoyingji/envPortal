import type { AppServer, AuthState, CurrentUser, Environment, HealthResult, Organization, PortalConfig, PortalData, VpnGuide, VpnImportJob } from './types';

async function readJson<T>(response: Response, fallback: string): Promise<T> {
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result?.detail || result?.message || fallback);
  return result as T;
}

export async function fetchPortalData(): Promise<PortalData> {
  const response = await fetch('/api/organizations');
  return readJson(response, 'Failed to load organizations');
}

export async function fetchMe(): Promise<AuthState> {
  const response = await fetch('/api/auth/me');
  return readJson(response, 'Failed to load current user');
}

export async function login(username: string, password: string): Promise<{ user: CurrentUser }> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  return readJson(response, 'Login failed');
}

export async function logout(): Promise<void> {
  await fetch('/api/auth/logout', { method: 'POST' });
}

export async function forgotPassword(usernameOrEmail: string): Promise<void> {
  const response = await fetch('/api/auth/forgot-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ usernameOrEmail })
  });
  await readJson(response, 'Failed to send reset mail');
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  const response = await fetch('/api/auth/reset-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, newPassword })
  });
  await readJson(response, 'Failed to reset password');
}

export async function changeOwnPassword(currentPassword: string, newPassword: string): Promise<void> {
  const response = await fetch('/api/auth/me/password', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ currentPassword, newPassword })
  });
  await readJson(response, 'Failed to change password');
}

export async function updateOwnProfile(values: { displayName: string; email: string }): Promise<CurrentUser> {
  const response = await fetch('/api/auth/me/profile', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values)
  });
  return readJson(response, 'Failed to update profile');
}

export async function uploadOwnAvatar(file: File): Promise<CurrentUser> {
  const form = new FormData();
  form.append('avatar', file);
  const response = await fetch('/api/auth/me/avatar', { method: 'POST', body: form });
  return readJson(response, 'Failed to upload avatar');
}

export async function fetchUsers(): Promise<{ users: CurrentUser[] }> {
  const response = await fetch('/api/users');
  return readJson(response, 'Failed to load users');
}

export async function createUser(values: Record<string, unknown>): Promise<CurrentUser & { temporaryPassword?: string }> {
  const response = await fetch('/api/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values)
  });
  return readJson(response, 'Failed to create user');
}

export async function updateUser(userId: string, values: Record<string, unknown>): Promise<CurrentUser> {
  const response = await fetch(`/api/users/${encodeURIComponent(userId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values)
  });
  return readJson(response, 'Failed to update user');
}

export async function resetUserPassword(userId: string, password?: string): Promise<CurrentUser & { temporaryPassword?: string }> {
  const response = await fetch(`/api/users/${encodeURIComponent(userId)}/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password })
  });
  return readJson(response, 'Failed to reset password');
}

export async function setUserEnabled(userId: string, enabled: boolean): Promise<CurrentUser> {
  const response = await fetch(`/api/users/${encodeURIComponent(userId)}/${enabled ? 'enable' : 'disable'}`, { method: 'POST' });
  return readJson(response, 'Failed to update user status');
}

export async function fetchPortalConfig(): Promise<PortalConfig> {
  const response = await fetch('/api/config');
  if (!response.ok) throw new Error('Failed to load portal config');
  return response.json();
}

export async function fetchHealth(url: string): Promise<HealthResult> {
  const response = await fetch(`/api/env-check?url=${encodeURIComponent(url)}`);
  if (!response.ok) throw new Error('Failed to check environment');
  return response.json();
}

export async function postForm(url: string, values: Record<string, string>): Promise<Response> {
  const form = new URLSearchParams(values);
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form
  });
}

export async function createEnvironment(organizationId: string, values: { title: string; tags: string[] }): Promise<Environment> {
  const response = await fetch(`/api/organizations/${encodeURIComponent(organizationId)}/environments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values)
  });
  if (!response.ok) throw new Error('Failed to create server');
  return response.json();
}

export async function createOrganization(values: { code: string; name: string }): Promise<Organization> {
  const response = await fetch('/api/organizations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values)
  });
  return readJson(response, 'Failed to create customer');
}

export async function updateOrganization(organizationId: string, values: { code: string; name: string }): Promise<Organization> {
  const response = await fetch(`/api/organizations/${encodeURIComponent(organizationId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values)
  });
  return readJson(response, 'Failed to update customer');
}

export async function deleteEnvironment(environmentId: string): Promise<{ ok?: boolean; id?: string; deleted?: Record<string, number> }> {
  const response = await fetch(`/api/environments/${encodeURIComponent(environmentId)}/delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}'
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(result?.detail || result?.message || 'Failed to delete server');
  }
  return result;
}

export async function saveOrganizationVpnGuide(organizationId: string, values: { id?: string; name: string; rawText: string }): Promise<VpnGuide> {
  const response = await fetch(`/api/organizations/${encodeURIComponent(organizationId)}/vpn-guide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values)
  });
  if (!response.ok) throw new Error('Failed to save VPN guide');
  return response.json();
}

export async function importOrganizationVpnGuide(organizationId: string, values: { id?: string; name: string; rawText: string; files: File[] }): Promise<{ guide: VpnGuide; job: VpnImportJob }> {
  const form = new FormData();
  form.append('name', values.name);
  form.append('rawText', values.rawText);
  if (values.id) form.append('guideId', values.id);
  form.append('fileMeta', JSON.stringify(values.files.map((file) => {
    const relativeName = (file as File & { webkitRelativePath?: string }).webkitRelativePath;
    return {
      filename: file.name,
      relativePath: relativeName || file.name,
      clientModifiedAt: Number.isFinite(file.lastModified) ? new Date(file.lastModified).toISOString() : '',
      sizeBytes: file.size
    };
  })));
  values.files.forEach((file) => {
    const relativeName = (file as File & { webkitRelativePath?: string }).webkitRelativePath;
    form.append('files', file, relativeName || file.name);
  });
  const response = await fetch(`/api/organizations/${encodeURIComponent(organizationId)}/vpn-guide/import`, {
    method: 'POST',
    body: form
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result?.detail || 'Failed to import VPN files');
  return result;
}

export async function reanalyzeOrganizationVpnGuide(organizationId: string, guideId: string): Promise<{ guide: VpnGuide; job?: VpnImportJob }> {
  const response = await fetch(`/api/organizations/${encodeURIComponent(organizationId)}/vpn-guide/${encodeURIComponent(guideId)}/reanalyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}'
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result?.detail || 'Failed to reanalyze VPN guide');
  return result;
}

export async function fetchVpnImportJob(jobId: string): Promise<VpnImportJob> {
  const response = await fetch(`/api/vpn-import-jobs/${encodeURIComponent(jobId)}`);
  if (!response.ok) throw new Error('Failed to load VPN import job');
  return response.json();
}

export async function retryVpnImportJob(jobId: string): Promise<VpnImportJob> {
  const response = await fetch(`/api/vpn-import-jobs/${encodeURIComponent(jobId)}/retry`, { method: 'POST' });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result?.detail || 'Failed to retry VPN import job');
  return result;
}

export async function saveEnvironmentVpnSetting(environmentId: string, values: { vpnRequired: boolean; vpnGuideId?: string | null }): Promise<{ id: string; vpn_required: boolean; vpn_guide_id?: string | null }> {
  const response = await fetch(`/api/environments/${encodeURIComponent(environmentId)}/vpn`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values)
  });
  if (!response.ok) throw new Error('Failed to save VPN setting');
  return response.json();
}

export async function saveEnvironmentDetails(environmentId: string, values: Record<string, unknown>): Promise<void> {
  const response = await fetch(`/api/environments/${encodeURIComponent(environmentId)}/details`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values)
  });
  if (!response.ok) throw new Error('Failed to save environment details');
}

export async function saveEnvironmentAppServers(environmentId: string, servers: AppServer[]): Promise<AppServer[]> {
  const response = await fetch(`/api/environments/${encodeURIComponent(environmentId)}/app-servers`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ servers })
  });
  if (!response.ok) throw new Error('Failed to save WEB/AP servers');
  const data = await response.json();
  return data.servers || [];
}
