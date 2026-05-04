export type Lang = 'ja' | 'zh';

export type TagItem = {
  name: string;
  source: 'manual' | 'migration' | 'auto' | string;
};

export type RemoteConnection = {
  id: string;
  type: string;
  host: string;
  port?: number;
  username: string;
  password: string;
};

export type AppServer = {
  id?: string;
  environment_id?: string;
  type: string;
  name: string;
  host: string;
  port?: number | null;
  os?: string;
  note?: string;
  details?: Array<{ key: string; value: string }>;
};

export type VpnWorkflowStep = {
  order: number;
  title: string;
  description: string;
  action: 'mail' | 'request' | 'contact' | 'connect' | 'note' | string;
  details?: Array<{ label: string; value: string }>;
  credentialGroups?: Array<{
    title?: string;
    host?: string;
    address?: string;
    username?: string;
    password?: string;
    port?: string;
    protocol?: string;
    note?: string;
    details?: Array<{ label: string; value: string }>;
  }>;
  mailTemplate?: {
    to?: string;
    cc?: string;
    bcc?: string;
    subject?: string;
    body?: string;
  } | null;
};

export type VpnGuide = {
  id: string;
  organization_id: string;
  name: string;
  rawText: string;
  sourceRawText?: string;
  manualRawText?: string;
  analysisRawText?: string;
  workflow: VpnWorkflowStep[];
  tags?: string[];
  workflowStatus?: 'analyzing' | 'ready' | 'error' | string;
  workflowSource?: 'ai' | 'rule' | 'none' | string;
  workflowError?: string;
  updatedAt?: string;
  sourceFiles?: SourceFile[];
};

export type SourceFile = {
  id: string;
  sha256: string;
  objectKey?: string;
  filename: string;
  storedFilename?: string;
  relativePath?: string;
  sizeBytes: number;
  contentType?: string;
  clientModifiedAt?: string;
  uploadedAt?: string;
  sourceRole?: 'current' | 'historical' | 'supplement' | 'override' | 'unknown' | string;
  dateHints?: string[];
  effectiveFrom?: string;
  effectiveTo?: string;
  createdAt?: string;
};

export type VpnImportJob = {
  id: string;
  organizationId: string;
  guideId: string;
  status: 'queued' | 'parsing' | 'rebuilding' | 'analyzing' | 'summarizing' | 'analyzed' | 'failed' | string;
  progress: number;
  error?: string;
  rawText?: string;
  fragments?: Array<Record<string, unknown>>;
  warnings?: string[];
  fileIds?: string[];
  mode?: string;
  sourceFileIds?: string[];
  sourceFileCount?: number;
  sourceMeta?: Array<Record<string, unknown>>;
  precedenceSummary?: string;
  createdAt?: string;
  updatedAt?: string;
};

export type Environment = {
  id: string;
  organization_id: string;
  organization_code: string;
  organization_name: string;
  title: string;
  url: string;
  login_id: string;
  login_password: string;
  db_type: string;
  db_version: string;
  db_host: string;
  db_port?: number;
  db_name: string;
  db_user: string;
  db_password: string;
  vpn_required: boolean;
  vpn_guide_id?: string | null;
  vpnGuide?: VpnGuide | null;
  tags: TagItem[];
  appServers: AppServer[];
  remoteConnections: RemoteConnection[];
};

export type Organization = {
  id: string;
  code: string;
  name: string;
  vpnGuide?: VpnGuide | null;
  vpnGuides: VpnGuide[];
  environments: Environment[];
};

export type PortalData = {
  organizations: Organization[];
  tags: TagItem[];
};

export type PortalConfig = {
  appName: string;
  version: string;
  guacamoleEnabled: boolean;
  guacamoleAvailable: boolean;
  guacamoleStatus: string;
  guacamoleUrl: string;
  guacamoleAutoLogin: boolean;
};

export type HealthResult = {
  status: number | string;
  elapsedMs: number;
  platform: string;
  ttl?: number | string;
  ttlGuess?: string;
  serverStack?: string;
};

export type UserRole = 'Admins' | 'Users';

export type CurrentUser = {
  id: string;
  username: string;
  role: UserRole;
  email: string;
  displayName: string;
  avatarUrl?: string;
  disabled?: boolean;
};

export type AuthState = {
  authenticated: boolean;
  user?: CurrentUser | null;
};
