import { ArrowDownOutlined, ArrowRightOutlined, CopyOutlined, DeleteOutlined, DownOutlined, EditOutlined, EyeInvisibleOutlined, EyeOutlined, FileTextOutlined, FolderOpenOutlined, GlobalOutlined, MailOutlined, MoreOutlined, PlusOutlined, ReloadOutlined, SafetyCertificateOutlined, SaveOutlined, UpOutlined, UploadOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Col, Dropdown, Input, Modal, Popconfirm, Progress, Row, Select, Space, Tag, Tooltip, Upload, message } from 'antd';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { createEnvironment, deleteEnvironment, fetchHealth, fetchPortalConfig, fetchRemoteCheck, fetchVpnImportJob, importOrganizationVpnGuide, postForm, reanalyzeOrganizationVpnGuide, saveEnvironmentAppServers, saveEnvironmentDetails, saveEnvironmentRemoteConnections, saveEnvironmentVpnSetting, saveOrganizationVpnGuide } from '../lib/api';
import { buildConnectionSummary } from '../lib/connectionSummary';
import { t } from '../lib/i18n';
import type { AppServer, Environment, Lang, Organization, PortalData, RemoteConnection, SourceFile, TagItem, VpnGuide, VpnImportJob, VpnWorkflowStep } from '../lib/types';
import DashboardStats from '../components/DashboardStats';
import OneTag, { oneTagColor, serviceTagColor } from '../components/OneTag';
import { RemoteActions } from '../components/RemoteActions';

type Props = {
  lang: Lang;
  organizations: Organization[];
  allOrganizations: Organization[];
  tags: TagItem[];
  selectedTags: string[];
  setSelectedTags: (tags: string[]) => void;
  isGlobalView: boolean;
  canWrite: boolean;
};

type EnvironmentDraft = {
  title: string;
  tags: string;
  url: string;
  login_id: string;
  login_password: string;
  db_type: string;
  db_version: string;
  db_host: string;
  db_port: number | null;
  db_name: string;
  db_user: string;
  db_password: string;
};

export default function EnvironmentPage({ lang, organizations, allOrganizations, tags, selectedTags, setSelectedTags, isGlobalView, canWrite }: Props) {
  const queryClient = useQueryClient();
  const stats = useMemo(() => {
    const envs = allOrganizations.flatMap((org) => org.environments);
    return {
      customers: allOrganizations.length,
      envs: envs.length,
      vpns: allOrganizations.filter((org) => org.vpnGuides?.some((guide) => guide.rawText?.trim()) || org.environments.some(isVpnRequired)).length,
      issues: 2
    };
  }, [allOrganizations]);

  return (
    <div className="dashboard-page">
      <Card className="filter-card">
        <div>
          <h3>{t(lang, 'tagFilter')}</h3>
          <Space wrap>
            {tags.map((tag) => (
              <button
                key={tag.name}
                className={selectedTags.includes(tag.name) ? 'tag-button selected' : 'tag-button'}
                data-color={tagColor(tag.name)}
                onClick={() => setSelectedTags(selectedTags.includes(tag.name) ? selectedTags.filter((item) => item !== tag.name) : [...selectedTags, tag.name])}
              >
                {tag.name}
              </button>
            ))}
            {selectedTags.length > 0 && <button className="tag-button clear" onClick={() => setSelectedTags([])}>{t(lang, 'clear')}</button>}
          </Space>
        </div>
        <span className="filter-hint">{t(lang, 'tagAndHint')}</span>
      </Card>

      {isGlobalView && (
        <section className="global-overview">
          <DashboardStats lang={lang} customers={stats.customers} servers={stats.envs} vpns={stats.vpns} issues={stats.issues} />
        </section>
      )}
      {!isGlobalView && (
        <section className="scoped-overview">
          <ConnectionSection lang={lang} organizations={organizations} />
        </section>
      )}

      <div className="org-list">
        {organizations.map((org) => (
          <section className="org-section" key={org.id}>
            <div className="org-title">
              <div className="org-title-main">
                <h2>{org.name}</h2>
                <span className="org-code">{org.code}</span>
              </div>
              {canWrite && <AddEnvironmentButton
                lang={lang}
                org={org}
                onCreated={async () => {
                  await queryClient.invalidateQueries({ queryKey: ['portal-data'] });
                  await queryClient.refetchQueries({ queryKey: ['portal-data'] });
                }}
              />}
            </div>
            <OrgVpnGuide
              lang={lang}
              org={org}
              canWrite={canWrite}
              onSaved={() => queryClient.invalidateQueries({ queryKey: ['portal-data'] })}
            />
            <div className="env-grid">
              {org.environments.map((env) => <EnvironmentCard key={env.id} env={env} vpnGuides={org.vpnGuides || []} lang={lang} canWrite={canWrite} />)}
            </div>
          </section>
        ))}
      </div>
      <ChangeLog lang={lang} />
    </div>
  );
}

function AddEnvironmentButton({ lang, org, onCreated }: { lang: Lang; org: Organization; onCreated: () => Promise<unknown> | unknown }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [tagText, setTagText] = useState('');
  const [saving, setSaving] = useState(false);
  const [reanalyzingGuideId, setReanalyzingGuideId] = useState<string | null>(null);

  const reset = () => {
    setTitle('');
    setTagText('');
  };

  const submit = async () => {
    if (saving) return;
    setSaving(true);
    try {
      await createEnvironment(org.id, {
        title: title.trim() || t(lang, 'environmentName'),
        tags: splitTags(tagText),
      });
      message.success(t(lang, 'save'));
      setOpen(false);
      reset();
      await onCreated();
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Failed to create server');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Button icon={<PlusOutlined />} onClick={() => setOpen(true)}>{t(lang, 'addEnvironment')}</Button>
      <Modal
        title={`${org.code} - ${org.name}`}
        open={open}
        confirmLoading={saving}
        okText={t(lang, 'create')}
        cancelText={t(lang, 'cancel')}
        okButtonProps={{ disabled: saving }}
        cancelButtonProps={{ disabled: saving }}
        onOk={submit}
        onCancel={() => {
          setOpen(false);
          reset();
        }}
      >
        <div className="add-env-form">
          <label>
            <span>{t(lang, 'environmentName')}</span>
            <Input value={title} placeholder={t(lang, 'environmentNamePlaceholder')} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label>
            <span>{t(lang, 'tags')}</span>
            <Input value={tagText} placeholder={t(lang, 'environmentTagsPlaceholder')} onChange={(event) => setTagText(event.target.value)} />
          </label>
        </div>
      </Modal>
    </>
  );
}

function splitTags(value: string): string[] {
  return value
    .split(/[,，、\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function removeEnvironmentFromPortalData(data: PortalData | undefined, environmentId: string): PortalData | undefined {
  if (!data) return data;
  return {
    ...data,
    organizations: data.organizations.map((org) => ({
      ...org,
      environments: org.environments.filter((env) => env.id !== environmentId)
    }))
  };
}

function OrgVpnGuide({ lang, org, canWrite, onSaved }: { lang: Lang; org: Organization; canWrite: boolean; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [editingGuide, setEditingGuide] = useState<VpnGuide | null>(null);
  const [guideName, setGuideName] = useState('');
  const [rawText, setRawText] = useState('');
  const [sourceFiles, setSourceFiles] = useState<File[]>([]);
  const [saving, setSaving] = useState(false);
  const [reanalyzingGuideId, setReanalyzingGuideId] = useState<string | null>(null);
  const [pendingGuide, setPendingGuide] = useState<VpnGuide | null>(null);
  const [importJob, setImportJob] = useState<VpnImportJob | null>(null);
  const vpnGuides = org.vpnGuides || [];
  const displayVpnGuides = mergePendingGuide(vpnGuides, pendingGuide);
  const hasGuide = displayVpnGuides.length > 0;
  const hasGuideContent = displayVpnGuides.some((guide) => guide.rawText?.trim() || (guide.workflow || []).length > 0 || (guide.sourceFiles || []).length > 0);
  const analyzing = displayVpnGuides.some((guide) => guide.workflowStatus === 'analyzing');

  useEffect(() => {
    if (!editing) {
      setEditingGuide(null);
      setGuideName('');
      setRawText('');
      setSourceFiles([]);
    }
  }, [editing]);

  useEffect(() => {
    if (!pendingGuide) return;
    const refreshed = vpnGuides.find((guide) => guide.id === pendingGuide.id);
    if (refreshed && refreshed.workflowStatus !== 'analyzing') {
      setPendingGuide(null);
    }
  }, [pendingGuide, vpnGuides]);

  useEffect(() => {
    if (!analyzing || editing) return undefined;
    const timer = window.setInterval(onSaved, 2500);
    return () => window.clearInterval(timer);
  }, [analyzing, editing, onSaved]);

  useEffect(() => {
    if (!importJob || ['analyzed', 'failed'].includes(importJob.status)) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const next = await fetchVpnImportJob(importJob.id);
        setImportJob(next);
        if (['analyzed', 'failed'].includes(next.status)) {
          onSaved();
        }
      } catch {
        // Keep the current status; the next poll may recover.
      }
    }, 2500);
    return () => window.clearInterval(timer);
  }, [importJob, onSaved]);

  const startEdit = (guide?: VpnGuide) => {
    setEditingGuide(guide || null);
    setGuideName(guide?.name || '');
    setRawText(guide?.manualRawText || guide?.rawText || '');
    setSourceFiles([]);
    setEditing(true);
  };

  const sourceFileKey = (file: File) => {
    const relativeName = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
    return `${relativeName}:${file.size}:${file.lastModified}`;
  };

  const addSourceFile = (file: File) => {
    if (file.name.toLowerCase().endsWith('.dmp')) {
      message.error(lang === 'zh' ? 'DMP 文件不能上传。' : 'DMP ファイルはアップロードできません。');
      return false;
    }
    setSourceFiles((files) => {
      const existing = new Set(files.map(sourceFileKey));
      if (existing.has(sourceFileKey(file))) return files;
      return [...files, file];
    });
    return true;
  };

  const save = async () => {
    setSaving(true);
    const importingFiles = sourceFiles.length > 0;
    const importMessageKey = `vpn-import-${org.id}`;
    try {
      const cleanName = guideName || t(lang, 'vpnGuide');
      if (importingFiles) {
        const totalBytes = sourceFiles.reduce((sum, file) => sum + file.size, 0);
        message.loading({
          key: importMessageKey,
          content: lang === 'zh'
            ? `正在上传 ${sourceFiles.length} 个文件（${formatBytes(totalBytes)}）...`
            : `${sourceFiles.length} 件のファイル（${formatBytes(totalBytes)}）をアップロードしています...`,
          duration: 0
        });
      }
      const saved = importingFiles
        ? await importOrganizationVpnGuide(org.id, {
            id: editingGuide?.id,
            name: cleanName,
            rawText,
            files: sourceFiles
          }).then((result) => {
            setImportJob(result.job);
            message.success({
              key: importMessageKey,
              content: lang === 'zh'
                ? `已受理 ${sourceFiles.length} 个文件，解析任务已开始。任务ID: ${shortId(result.job.id)}`
                : `${sourceFiles.length} 件のファイルを受け付け、解析ジョブを開始しました。ジョブID: ${shortId(result.job.id)}`,
              duration: 8
            });
            return result.guide;
          })
        : await saveOrganizationVpnGuide(org.id, {
          id: editingGuide?.id,
          name: cleanName,
          rawText
        });
      setPendingGuide(saved);
      if (!importingFiles) message.success(t(lang, 'save'));
      setEditing(false);
      onSaved();
    } catch (error) {
      if (importingFiles) message.destroy(importMessageKey);
      const detail = error instanceof Error ? error.message : 'Failed to save VPN guide';
      Modal.error({
        title: importingFiles
          ? (lang === 'zh' ? 'VPN 原始资料导入失败' : 'VPN 原資料の取り込みに失敗しました')
          : (lang === 'zh' ? '保存失败' : '保存に失敗しました'),
        content: detail
      });
    } finally {
      setSaving(false);
    }
  };

  const reanalyze = async (guide: VpnGuide) => {
    if (reanalyzingGuideId) return;
    setReanalyzingGuideId(guide.id);
    try {
      const result = await reanalyzeOrganizationVpnGuide(org.id, guide.id);
      setPendingGuide(result.guide);
      if (result.job) setImportJob(result.job);
      message.success(t(lang, 'reanalyzeStarted'));
      onSaved();
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Failed to reanalyze VPN guide');
    } finally {
      setReanalyzingGuideId(null);
    }
  };

  if (!hasGuide && !editing) {
    return (
      <div className="vpn-guide-empty">
        <span>{t(lang, 'noVpnGuide')}</span>
        {canWrite && <Button icon={<SafetyCertificateOutlined />} onClick={() => startEdit()}>{t(lang, 'addVpnGuide')}</Button>}
      </div>
    );
  }

  return (
    <div className="vpn-guide">
      <div className="vpn-guide-head">
        <Space>
          <SafetyCertificateOutlined />
          <strong>{t(lang, 'vpnGuide')}</strong>
          {analyzing ? <Tag color="processing">{t(lang, 'aiAnalyzing')}</Tag> : hasGuideContent && <Tag color="gold">{t(lang, 'aiReady')}</Tag>}
        </Space>
        <Space>
          {editing ? (
            <>
              <Button icon={<SaveOutlined />} type="primary" loading={saving} onClick={save}>{t(lang, 'save')}</Button>
              <Button onClick={() => setEditing(false)}>{t(lang, 'cancel')}</Button>
            </>
          ) : canWrite ? (
            <Button icon={<EditOutlined />} disabled={analyzing} onClick={() => startEdit()}>{t(lang, 'addVpnGuide')}</Button>
          ) : null}
        </Space>
      </div>
      {importJob && (
        <Alert
          className="vpn-import-status"
          showIcon
          type={importJob.status === 'failed' ? 'error' : importJob.status === 'analyzed' ? 'success' : 'info'}
          message={lang === 'zh' ? 'VPN 原始资料导入状态' : 'VPN 原資料取り込み状態'}
          description={formatImportJobStatus(lang, importJob)}
        />
      )}
      {editing ? (
        <Space direction="vertical" size={12} className="vpn-guide-editor">
          <Input
            value={guideName}
            onChange={(event) => setGuideName(event.target.value)}
            placeholder={t(lang, 'vpnNamePlaceholder')}
            addonBefore={t(lang, 'vpnName')}
          />
          <Input.TextArea
            value={rawText}
            onChange={(event) => setRawText(event.target.value)}
            placeholder={t(lang, 'vpnGuidePlaceholder')}
            autoSize={{ minRows: 4, maxRows: 10 }}
          />
          <Upload.Dragger
            multiple
            fileList={sourceFiles.map((file, index) => ({
              uid: `${sourceFileKey(file)}-${index}`,
              name: (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name,
              size: file.size,
              status: 'done'
            }))}
            beforeUpload={(file) => {
              addSourceFile(file as File);
              return Upload.LIST_IGNORE;
            }}
            onRemove={(file) => {
              const removeKey = String(file.uid).replace(/-\d+$/, '');
              setSourceFiles((files) => files.filter((item) => sourceFileKey(item) !== removeKey));
            }}
          >
            <p className="ant-upload-drag-icon"><UploadOutlined /></p>
            <p className="ant-upload-text">{lang === 'zh' ? '拖放或选择 VPN 原始资料文件' : 'VPN 原資料ファイルをドラッグまたは選択'}</p>
            <p className="ant-upload-hint">{lang === 'zh' ? '除 .dmp 外均可上传，文件会按 hash 归档保存到 MinIO。' : '.dmp 以外をアップロードできます。ファイルは hash で MinIO に保存します。'}</p>
          </Upload.Dragger>
          <Upload
            directory
            multiple
            showUploadList={false}
            beforeUpload={(file) => {
              addSourceFile(file as File);
              return Upload.LIST_IGNORE;
            }}
          >
            <Button icon={<FolderOpenOutlined />}>
              {lang === 'zh' ? '选择文件夹递归导入' : 'フォルダを再帰的に取り込む'}
            </Button>
          </Upload>
        </Space>
      ) : (
        <div className="vpn-guide-list">
          {displayVpnGuides.map((guide) => (
            <div className={guide.workflowStatus === 'analyzing' ? 'vpn-guide-item analyzing' : 'vpn-guide-item'} key={guide.id}>
              <div className="vpn-guide-item-head">
                <Space>
                  <strong>{guide.name}</strong>
                  {(guide.tags || []).map((tag) => <Tag key={tag} color={tagColor(tag)}>{tag}</Tag>)}
                  {guide.workflowStatus === 'analyzing' && <Tag color="processing">{t(lang, 'aiAnalyzing')}</Tag>}
                  {(guide.sourceFiles || []).length > 0 && <Tag icon={<FileTextOutlined />}>{(guide.sourceFiles || []).length}</Tag>}
                </Space>
                {canWrite && (
                  <Space size={6}>
                    <Button
                      size="small"
                      icon={<ReloadOutlined />}
                      loading={reanalyzingGuideId === guide.id}
                      disabled={guide.workflowStatus === 'analyzing'}
                      onClick={() => reanalyze(guide)}
                    >
                      {t(lang, 'reanalyze')}
                    </Button>
                    <Button size="small" icon={<EditOutlined />} disabled={guide.workflowStatus === 'analyzing'} onClick={() => startEdit(guide)}>{t(lang, 'edit')}</Button>
                  </Space>
                )}
              </div>
              {(guide.sourceFiles || []).length > 0 && <SourceFileSummary lang={lang} files={guide.sourceFiles || []} />}
              {guide.workflowSource === 'rule' && (
                <Alert
                  className="vpn-rule-warning"
                  type="warning"
                  showIcon
                  message={lang === 'zh' ? '规则兜底结果，需要人工确认' : 'ルール補完結果です。内容確認が必要です'}
                  description={guide.workflowError || (lang === 'zh' ? 'AI 分析失败后仅保守显示清洗后的连接相关信息，请重新 AI 分析。' : 'AI分析に失敗したため、清掃済みの接続関連情報だけを保守的に表示しています。再分析してください。')}
                />
              )}
              {guide.workflowStatus === 'analyzing' && (guide.workflow || []).length === 0 ? (
                <div className="vpn-analysis-note">{t(lang, 'aiAnalyzing')}</div>
              ) : (
                <div className="vpn-step-flow">
                  {(guide.workflow || []).map((step, index, steps) => (
                    <VpnStep key={`${guide.id}-${step.order}-${step.description}`} lang={lang} step={step} index={index} showArrow={index < steps.length - 1} />
                  ))}
                </div>
              )}
              {guide.workflowStatus === 'analyzing' && (
                <div className="vpn-analysis-mask">
                  <span className="vpn-analysis-spinner" />
                  <strong>{t(lang, 'aiAnalyzing')}</strong>
                  <p>{t(lang, 'aiAnalyzingHint')}</p>
                </div>
              )}
              {guide.rawText?.trim() && (
                <details className="vpn-original">
                  <summary>{t(lang, 'originalText')}</summary>
                  <pre>{guide.rawText}</pre>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function mergePendingGuide(guides: VpnGuide[], pendingGuide: VpnGuide | null): VpnGuide[] {
  if (!pendingGuide) return guides;
  const index = guides.findIndex((guide) => guide.id === pendingGuide.id);
  if (index < 0) return [pendingGuide, ...guides];
  return guides.map((guide) => guide.id === pendingGuide.id && guide.workflowStatus !== 'analyzing' ? pendingGuide : guide);
}

function sourceRoleColor(role?: string) {
  if (role === 'current') return 'green';
  if (role === 'override') return 'volcano';
  if (role === 'supplement') return 'blue';
  if (role === 'historical') return 'default';
  return 'gold';
}

function sourceFileName(file?: SourceFile) {
  return file?.relativePath || file?.filename || '';
}

function sourceFileSummaryText(lang: Lang, files: SourceFile[]) {
  const firstName = sourceFileName(files[0]);
  const count = files.length;
  if (!firstName) return lang === 'zh' ? `${count} 个来源文件` : `${count} 件の原資料`;
  if (count <= 1) return firstName;
  return lang === 'zh' ? `${firstName} 等 ${count} 个文件` : `${firstName} ほか ${count} 件`;
}

function SourceFileSummary({ lang, files, compact = false }: { lang: Lang; files: SourceFile[]; compact?: boolean }) {
  if (files.length === 0) return null;
  const first = files[0];
  const title = [
    sourceFileName(first),
    first?.sourceRole && first.sourceRole !== 'unknown' ? `${lang === 'zh' ? '角色' : '役割'}: ${first.sourceRole}` : '',
    first?.clientModifiedAt ? `${lang === 'zh' ? '修改时间' : '更新日時'}: ${first.clientModifiedAt}` : '',
    lang === 'zh' ? `来源文件总数: ${files.length}` : `原資料合計: ${files.length}`,
  ].filter(Boolean).join('\n');
  return (
    <div className={compact ? 'vpn-source-summary compact' : 'vpn-source-summary'}>
      <Tooltip title={title}>
        <Tag color={sourceRoleColor(first?.sourceRole)} icon={<FileTextOutlined />}>
          <span className="source-summary-name">{sourceFileSummaryText(lang, files)}</span>
        </Tag>
      </Tooltip>
      {files.length > 1 && <Tag>{lang === 'zh' ? `共 ${files.length}` : `全 ${files.length}`}</Tag>}
    </div>
  );
}

function formatBytes(bytes: number) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function shortId(id?: string) {
  return id ? id.slice(0, 8) : '-';
}

function formatImportJobStatus(lang: Lang, job: VpnImportJob) {
  const count = job.sourceFileCount ?? job.sourceFileIds?.length ?? job.fileIds?.length ?? 0;
  const statusText = lang === 'zh'
    ? { queued: '排队中', parsing: '解析文件中', rebuilding: '重建原文中', analyzing: 'AI分析中', summarizing: '汇总中', analyzed: '完成', failed: '失败' }[job.status] || job.status
    : { queued: '待機中', parsing: 'ファイル解析中', rebuilding: '原文再構築中', analyzing: 'AI分析中', summarizing: '要約中', analyzed: '完了', failed: '失敗' }[job.status] || job.status;
  const base = lang === 'zh'
    ? `任务 ${shortId(job.id)} / 状态: ${statusText} / 进度: ${job.progress ?? 0}% / 来源文件: ${count}`
    : `ジョブ ${shortId(job.id)} / 状態: ${statusText} / 進捗: ${job.progress ?? 0}% / ソースファイル: ${count}`;
  return job.error ? `${base}\n${job.error}` : base;
}

function VpnStep({ lang, step, index, showArrow }: { lang: Lang; step: VpnWorkflowStep; index: number; showArrow: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const color = step.action === 'mail' ? 'purple' : step.action === 'request' ? 'orange' : step.action === 'contact' ? 'blue' : step.action === 'connect' ? 'green' : step.action === 'verify' ? 'gold' : 'default';
  const derivedMailTemplate = deriveMailTemplate(step);
  const mailTemplate = hasMailAddress(derivedMailTemplate) ? derivedMailTemplate : null;
  const credentialGroups = normalizeCredentialGroups(step);
  const groupedDetailKeys = new Set(credentialGroups.flatMap((group) => (group.details || []).map((detail) => `${detail.label}\u0000${detail.value}`)));
  const details = (step.details || []).filter((detail) => !(mailTemplate && mailFieldType(detail.label)) && !groupedDetailKeys.has(`${detail.label}\u0000${detail.value}`));
  const childCount = details.length + credentialGroups.length + (mailTemplate ? 1 : 0);
  const hasMore = childCount > 0;
  const copyMail = async () => {
    const text = formatMailTemplate(lang, mailTemplate);
    await navigator.clipboard.writeText(text);
    message.success(t(lang, 'copyMail'));
  };
  const copyValue = async (text: string) => {
    await navigator.clipboard.writeText(text || '');
    message.success(t(lang, 'copy'));
  };
  const openMail = () => {
    const url = buildMailtoUrl(mailTemplate);
    if (url) window.location.href = url;
  };
  return (
    <>
      <div className={['vpn-step', expanded ? 'expanded' : '', mailTemplate ? 'mail-step' : ''].filter(Boolean).join(' ')}>
        <div className="vpn-step-head">
          <span className="vpn-step-index">{step.order}</span>
          <div className="vpn-step-title">
            <strong>{step.title}</strong>
            <Tag color={color}>{vpnActionLabel(lang, step.action)}</Tag>
          </div>
        </div>
        <p>{step.description}</p>
        {expanded && Boolean(details.length) && (
          <div className="vpn-step-details">
            {details.map((detail, index) => (
              <div className="vpn-step-detail" key={`${detail.label}-${index}`}>
                <span>{detail.label}</span>
                <div className="vpn-copy-value">
                  <b>{detail.value}</b>
                  <Tooltip title={t(lang, 'copy')}>
                    <Button size="small" icon={<CopyOutlined />} onClick={() => copyValue(detail.value)} />
                  </Tooltip>
                </div>
              </div>
            ))}
          </div>
        )}
        {expanded && credentialGroups.length > 0 && (
          <div className="vpn-credential-groups">
            {credentialGroups.map((group, index) => (
              <div className="vpn-credential-card" key={`${group.title || group.host || group.address || index}-${index}`}>
                <div className="vpn-credential-head">
                  <strong>{group.title || group.host || group.address || (lang === 'zh' ? '服务器凭证' : 'サーバー認証情報')}</strong>
                  {group.protocol && <Tag>{group.protocol}</Tag>}
                </div>
                <div className="vpn-credential-grid">
                  {group.host && <CredentialValue lang={lang} label={lang === 'zh' ? '主机' : 'ホスト'} value={group.host} onCopy={copyValue} />}
                  {group.address && <CredentialValue lang={lang} label={lang === 'zh' ? '地址' : 'アドレス'} value={group.address} onCopy={copyValue} />}
                  {group.port && <CredentialValue lang={lang} label={lang === 'zh' ? '端口' : 'ポート'} value={group.port} onCopy={copyValue} />}
                  {group.username && <CredentialValue lang={lang} label={lang === 'zh' ? '用户' : 'ユーザー'} value={group.username} onCopy={copyValue} />}
                  {group.password && <CredentialValue lang={lang} label={lang === 'zh' ? '密码' : 'パスワード'} value={group.password} onCopy={copyValue} secret />}
                  {group.note && <CredentialValue lang={lang} label={lang === 'zh' ? '备注' : 'メモ'} value={group.note} onCopy={copyValue} />}
                  {(group.details || []).map((detail, detailIndex) => (
                    <CredentialValue key={`${detail.label}-${detailIndex}`} lang={lang} label={detail.label} value={detail.value} onCopy={copyValue} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
        {expanded && mailTemplate && (
          <div className="vpn-mail-template">
            <div className="vpn-mail-head">
              <span><MailOutlined /> {t(lang, 'mailBody')}</span>
              <Space size={6}>
                <Button size="small" icon={<MailOutlined />} onClick={openMail}>{t(lang, 'openMail')}</Button>
                <Button size="small" icon={<CopyOutlined />} onClick={copyMail}>{t(lang, 'copyMail')}</Button>
              </Space>
            </div>
            <div className="vpn-mail-fields">
              {mailTemplate?.to && <MailValueRow lang={lang} label={t(lang, 'mailTo')} value={mailTemplate.to} onCopy={copyValue} />}
              {mailTemplate?.cc && <MailValueRow lang={lang} label={t(lang, 'mailCc')} value={mailTemplate.cc} onCopy={copyValue} />}
              {mailTemplate?.bcc && <MailValueRow lang={lang} label={t(lang, 'mailBcc')} value={mailTemplate.bcc} onCopy={copyValue} />}
              {mailTemplate?.subject && <MailValueRow lang={lang} label={t(lang, 'mailSubject')} value={mailTemplate.subject} onCopy={copyValue} />}
            </div>
            {mailTemplate?.body && (
              <div className="vpn-mail-body">
                <div className="vpn-mail-body-head">
                  <span>{t(lang, 'mailBody')}</span>
                  <Tooltip title={t(lang, 'copy')}>
                    <Button size="small" icon={<CopyOutlined />} onClick={() => copyValue(mailTemplate.body || '')} />
                  </Tooltip>
                </div>
                <pre>{mailTemplate.body}</pre>
              </div>
            )}
          </div>
        )}
        <div className="vpn-step-foot">
          {!expanded && childCount > 0 && <span className="vpn-step-more">+{childCount}</span>}
          {hasMore && (
            <Button type="text" size="small" className="vpn-step-toggle" icon={expanded ? <UpOutlined /> : <DownOutlined />} onClick={() => setExpanded(!expanded)}>
              {expanded ? t(lang, 'collapse') : t(lang, 'expand')}
            </Button>
          )}
        </div>
      </div>
      {showArrow && <div className={index % 4 === 3 ? 'vpn-step-arrow turn' : 'vpn-step-arrow'}>{index % 4 === 3 ? <ArrowDownOutlined /> : <ArrowRightOutlined />}</div>}
    </>
  );
}

function MailValueRow({ lang, label, value, onCopy }: { lang: Lang; label: string; value: string; onCopy: (value: string) => void }) {
  return (
    <div className="vpn-mail-row">
      <span>{label}</span>
      <div className="vpn-copy-value">
        <b>{value}</b>
        <Tooltip title={t(lang, 'copy')}>
          <Button size="small" icon={<CopyOutlined />} onClick={() => onCopy(value)} />
        </Tooltip>
      </div>
    </div>
  );
}

function CredentialValue({ label, value, secret, onCopy }: { lang: Lang; label: string; value: string; secret?: boolean; onCopy: (value: string) => void }) {
  const [shown, setShown] = useState(!secret);
  return (
    <div className="vpn-credential-value">
      <span>{label}</span>
      <b>{shown ? value : '••••••••'}</b>
      <Space size={4}>
        {secret && <Button size="small" icon={shown ? <EyeInvisibleOutlined /> : <EyeOutlined />} onClick={() => setShown((value) => !value)} />}
        <Button size="small" icon={<CopyOutlined />} onClick={() => onCopy(value)} />
      </Space>
    </div>
  );
}

function normalizeCredentialGroups(step: VpnWorkflowStep): NonNullable<VpnWorkflowStep['credentialGroups']> {
  const groups = Array.isArray(step.credentialGroups) ? step.credentialGroups.filter(Boolean) : [];
  if (groups.length > 0) {
    return groups.map((group) => ({
      ...group,
      details: Array.isArray(group.details) ? group.details.filter((detail) => detail.label || detail.value) : []
    }));
  }
  const details = step.details || [];
  const hostDetails = details.filter((detail) => credentialField(detail.label) === 'host');
  return hostDetails.map((hostDetail) => {
    const title = hostDetail.value || hostDetail.label;
    const related = details.filter((detail) => detail !== hostDetail && isLikelyRelatedCredential(hostDetail, detail, details));
    return {
      title,
      host: hostDetail.value,
      username: related.find((detail) => credentialField(detail.label) === 'username')?.value || '',
      password: related.find((detail) => credentialField(detail.label) === 'password')?.value || '',
      port: related.find((detail) => credentialField(detail.label) === 'port')?.value || '',
      protocol: related.find((detail) => credentialField(detail.label) === 'protocol')?.value || '',
      note: related.find((detail) => credentialField(detail.label) === 'note')?.value || '',
      details: related.filter((detail) => !['username', 'password', 'port', 'protocol', 'note'].includes(credentialField(detail.label) || ''))
    };
  }).filter((group) => group.username || group.password || group.port || group.protocol || group.details.length > 0);
}

function credentialField(label: string): 'host' | 'username' | 'password' | 'port' | 'protocol' | 'note' | null {
  const normalized = label.toLowerCase();
  if (/(host|server|サーバ|ホスト|主机|地址|アドレス)/.test(normalized)) return 'host';
  if (/(user|username|ユーザ|ユーザー|ログイン|账号|帳號|账户)/.test(normalized)) return 'username';
  if (/(password|pass|pwd|pw|パスワード|密码|密碼)/.test(normalized)) return 'password';
  if (/(port|ポート|端口)/.test(normalized)) return 'port';
  if (/(protocol|type|方式|種別|类型)/.test(normalized)) return 'protocol';
  if (/(note|memo|備考|备注|メモ)/.test(normalized)) return 'note';
  return null;
}

function isLikelyRelatedCredential(hostDetail: { label: string; value: string }, detail: { label: string; value: string }, allDetails: Array<{ label: string; value: string }>): boolean {
  const field = credentialField(detail.label);
  if (!field || field === 'host') return false;
  const hostIndex = allDetails.indexOf(hostDetail);
  const detailIndex = allDetails.indexOf(detail);
  if (hostIndex < 0 || detailIndex < 0 || detailIndex < hostIndex) return false;
  const nextHostIndex = allDetails.findIndex((item, index) => index > hostIndex && credentialField(item.label) === 'host');
  return nextHostIndex < 0 || detailIndex < nextHostIndex;
}

function vpnActionLabel(lang: Lang, action: string): string {
  const labels: Record<string, { ja: string; zh: string }> = {
    request: { ja: '申請', zh: '申请' },
    mail: { ja: 'メール', zh: '邮件' },
    contact: { ja: '連絡', zh: '联系' },
    connect: { ja: '接続', zh: '连接' },
    verify: { ja: '認証', zh: '验证' },
    remote: { ja: '遠隔', zh: '远程' },
    note: { ja: 'メモ', zh: '备注' },
  };
  return labels[action]?.[lang] || labels.note[lang];
}

function formatMailTemplate(lang: Lang, template: VpnWorkflowStep['mailTemplate']): string {
  if (!template) return '';
  const lines = [
    template.to ? `${t(lang, 'mailTo')}: ${template.to}` : '',
    template.cc ? `${t(lang, 'mailCc')}: ${template.cc}` : '',
    template.bcc ? `${t(lang, 'mailBcc')}: ${template.bcc}` : '',
    template.subject ? `${t(lang, 'mailSubject')}: ${template.subject}` : '',
    template.body ? `${t(lang, 'mailBody')}:\n${template.body}` : ''
  ].filter(Boolean);
  return lines.join('\n');
}

function hasMailAddress(template: VpnWorkflowStep['mailTemplate']): boolean {
  return Boolean(template && (template.to || template.cc || template.bcc));
}

function buildMailtoUrl(template: VpnWorkflowStep['mailTemplate']): string {
  if (!hasMailAddress(template)) return '';
  const params = new URLSearchParams();
  if (template?.cc) params.set('cc', template.cc);
  if (template?.bcc) params.set('bcc', template.bcc);
  if (template?.subject) params.set('subject', template.subject);
  if (template?.body) params.set('body', template.body);
  return `mailto:${encodeURIComponent(template?.to || '')}${params.toString() ? `?${params.toString()}` : ''}`;
}

function deriveMailTemplate(step: VpnWorkflowStep): VpnWorkflowStep['mailTemplate'] {
  const direct = step.mailTemplate;
  const result = {
    to: direct?.to || '',
    cc: direct?.cc || '',
    bcc: direct?.bcc || '',
    subject: direct?.subject || '',
    body: direct?.body || ''
  };
  for (const detail of step.details || []) {
    const type = mailFieldType(detail.label);
    if (type && !result[type]) {
      result[type] = detail.value;
    }
  }
  return Object.values(result).some(Boolean) ? result : direct;
}

function mailFieldType(label: string): 'to' | 'cc' | 'bcc' | 'subject' | 'body' | null {
  const normalized = label.trim().toLowerCase();
  if (!normalized) return null;
  if (['宛先', '收件人', 'to', 'to:', 'recipient', 'recipients'].includes(normalized)) return 'to';
  if (['cc', 'cc:'].includes(normalized)) return 'cc';
  if (['bcc', 'bcc:'].includes(normalized)) return 'bcc';
  if (['件名', '标题', '標題', '标题', 'タイトル', '主题', 'subject', 'subject:'].includes(normalized)) return 'subject';
  if (['本文', '正文', '文面', 'body', 'content', 'mail body', '邮件正文', 'メール本文'].includes(normalized)) return 'body';
  return null;
}

function isVpnRequired(env: Environment): boolean {
  return env.tags.some((tag) => {
    const name = tag.name.trim().toLowerCase();
    return name === 'vpn' || name.includes('需vpn') || name.includes('要vpn') || name.includes('vpn必須') || name.includes('vpn必需');
  });
}

function EnvironmentCard({ env, vpnGuides, lang, canWrite }: { env: Environment; vpnGuides: VpnGuide[]; lang: Lang; canWrite: boolean }) {
  const health = useQuery({ queryKey: ['health', env.url], queryFn: () => fetchHealth(env.url), enabled: Boolean(env.url), refetchInterval: 60_000, staleTime: 50_000 });
  const config = useQuery({ queryKey: ['portal-config'], queryFn: fetchPortalConfig, refetchInterval: 30_000, staleTime: 20_000 });
  const queryClient = useQueryClient();
  const ok = health.data && health.data.status !== 'ERROR';
  const remotes = env.remoteConnections || [];
  const appServers = env.appServers || [];
  const [busy, setBusy] = useState(false);
  const [vpnBusy, setVpnBusy] = useState(false);
  const [editingDetails, setEditingDetails] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [serverBusy, setServerBusy] = useState(false);
  const [appServerDraft, setAppServerDraft] = useState<AppServer[]>([]);
  const [remoteDraft, setRemoteDraft] = useState<RemoteConnection[]>([]);
  const [envDraft, setEnvDraft] = useState<EnvironmentDraft>(() => createEnvironmentDraft(env));
  const [showAppAccessEditor, setShowAppAccessEditor] = useState(() => hasAppAccess(env));
  const [showDatabaseEditor, setShowDatabaseEditor] = useState(() => hasDatabaseInfo(env));
  const serverVpnRequired = Boolean(env.vpn_required);
  const serverVpnGuideId = env.vpn_guide_id || env.vpnGuide?.id || undefined;
  const [vpnState, setVpnState] = useState<{ required: boolean; guideId?: string }>({ required: serverVpnRequired, guideId: serverVpnGuideId });
  const [vpnTouched, setVpnTouched] = useState(false);
  const selectedVpnGuideId = vpnState.guideId;
  const selectedVpnGuide = vpnGuides.find((guide) => guide.id === selectedVpnGuideId) || vpnGuides[0];
  const canCheckHealth = hasAppAccess(env) && Boolean(env.url);
  const showDetails = expanded || editingDetails;

  useEffect(() => {
    if (!vpnTouched) {
      setVpnState({ required: serverVpnRequired, guideId: serverVpnGuideId });
    }
  }, [env.id, serverVpnRequired, serverVpnGuideId, vpnTouched]);

  useEffect(() => {
    if (!editingDetails) {
      setAppServerDraft(appServers.map((server) => ({ ...server })));
      setRemoteDraft(remotes.map((remote) => ({ ...remote })));
      setEnvDraft(createEnvironmentDraft(env));
      setShowAppAccessEditor(hasAppAccess(env));
      setShowDatabaseEditor(hasDatabaseInfo(env));
    }
  }, [editingDetails, appServers, remotes, env]);

  const copy = async (text: string) => {
    await navigator.clipboard.writeText(text || '');
    message.success(t(lang, 'copy'));
  };

  const updateVpn = async (vpnRequired: boolean, vpnGuideId?: string | null) => {
    if (!canWrite) return;
    const previous = vpnState;
    const next = {
      required: vpnRequired,
      guideId: vpnRequired ? vpnGuideId || vpnGuides[0]?.id : undefined
    };
    setVpnTouched(true);
    setVpnState(next);
    setVpnBusy(true);
    try {
      const saved = await saveEnvironmentVpnSetting(env.id, { vpnRequired: next.required, vpnGuideId: next.guideId });
      setVpnState({ required: Boolean(saved.vpn_required), guideId: saved.vpn_guide_id || undefined });
      await queryClient.invalidateQueries({ queryKey: ['portal-data'] });
      setVpnTouched(false);
      message.success(t(lang, 'save'));
    } catch (error) {
      setVpnState(previous);
      setVpnTouched(false);
      message.error(error instanceof Error ? error.message : 'Failed to save VPN setting');
    } finally {
      setVpnBusy(false);
    }
  };

  const startEditDetails = () => {
    setEnvDraft(createEnvironmentDraft(env));
    setAppServerDraft(appServers.map((server) => ({ ...server })));
    setRemoteDraft(remotes.map((remote) => ({ ...remote })));
    setShowAppAccessEditor(hasAppAccess(env));
    setShowDatabaseEditor(hasDatabaseInfo(env));
    setExpanded(true);
    setEditingDetails(true);
  };

  const cancelEditDetails = () => {
    setEnvDraft(createEnvironmentDraft(env));
    setAppServerDraft(appServers.map((server) => ({ ...server })));
    setRemoteDraft(remotes.map((remote) => ({ ...remote })));
    setShowAppAccessEditor(hasAppAccess(env));
    setShowDatabaseEditor(hasDatabaseInfo(env));
    setEditingDetails(false);
  };

  const updateEnvDraft = (patch: Partial<EnvironmentDraft>) => {
    setEnvDraft((draft) => ({ ...draft, ...patch }));
  };

  const updateAppServerDraft = (index: number, patch: Partial<AppServer>) => {
    setAppServerDraft((servers) => servers.map((server, itemIndex) => itemIndex === index ? { ...server, ...patch } : server));
  };

  const addAppServer = () => {
    setAppServerDraft((servers) => [...servers, emptyAppServer()]);
  };

  const removeAppServer = (index: number) => {
    setAppServerDraft((servers) => servers.filter((_, itemIndex) => itemIndex !== index));
  };

  const updateRemoteDraft = (index: number, patch: Partial<RemoteConnection>) => {
    setRemoteDraft((items) => items.map((remote, itemIndex) => itemIndex === index ? { ...remote, ...patch } : remote));
  };

  const addRemoteConnection = () => {
    setRemoteDraft((items) => [...items, emptyRemoteConnection()]);
  };

  const removeRemoteConnection = (index: number) => {
    setRemoteDraft((items) => items.filter((_, itemIndex) => itemIndex !== index));
  };

  const removeAppAccess = () => {
    updateEnvDraft({ url: '', login_id: '', login_password: '' });
    setShowAppAccessEditor(false);
  };

  const removeDatabaseInfo = () => {
    updateEnvDraft({
      db_type: '',
      db_version: '',
      db_host: '',
      db_port: null,
      db_name: '',
      db_user: '',
      db_password: ''
    });
    setShowDatabaseEditor(false);
  };

  const saveAppServerDraft = async () => {
    setServerBusy(true);
    try {
      await saveEnvironmentDetails(env.id, envDraft);
      await saveEnvironmentAppServers(env.id, appServerDraft);
      await saveEnvironmentRemoteConnections(env.id, remoteDraft);
      await queryClient.invalidateQueries({ queryKey: ['portal-data'] });
      setEditingDetails(false);
      message.success(t(lang, 'save'));
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Failed to save WEB/AP servers');
    } finally {
      setServerBusy(false);
    }
  };

  const deleteThisEnvironment = async () => {
    const previous = queryClient.getQueryData<PortalData>(['portal-data']);
    queryClient.setQueryData<PortalData>(['portal-data'], (current) => removeEnvironmentFromPortalData(current, env.id));
    try {
      const result = await deleteEnvironment(env.id);
      await queryClient.invalidateQueries({ queryKey: ['portal-data'] });
      await queryClient.refetchQueries({ queryKey: ['portal-data'] });
      const count = result.deleted?.environments ?? 0;
      message.success(`${t(lang, 'delete')} (${count})`);
    } catch (error) {
      if (previous) {
        queryClient.setQueryData(['portal-data'], previous);
      }
      message.error(error instanceof Error ? error.message : 'Failed to delete server');
      throw error;
    }
  };

  const remoteTarget = (remote: RemoteConnection) => `${remote.host}${remote.port ? `:${remote.port}` : ''}`;

  const downloadRdp = async (remote: RemoteConnection, showBusy = true) => {
    if (!remote) return;
    if (showBusy) setBusy(true);
    try {
      await navigator.clipboard.writeText(remote.password || '');
      const response = await postForm('/api/rdp/file', {
        target: remoteTarget(remote),
        user: remote.username,
        password: remote.password,
        org: env.organization_name,
        env: env.title
      });
      if (!response.ok) {
        const result = await response.json().catch(() => ({}));
        throw new Error(result?.message || 'RDP file error');
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${env.organization_code}_${env.title}.rdp`;
      anchor.click();
      URL.revokeObjectURL(url);
      message.success(t(lang, 'rdpFileReady'));
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'RDP file error');
    } finally {
      if (showBusy) setBusy(false);
    }
  };

  const connectRdp = async (remote: RemoteConnection) => {
    if (!remote) return;
    setBusy(true);
    try {
      await navigator.clipboard.writeText(remote.password || '');
      const response = await postForm('/api/rdp/connect', {
        target: remoteTarget(remote),
        user: remote.username,
        password: remote.password
      });
      const result = await response.json().catch(() => ({}));
      if (response.ok && result?.ok !== false) {
        message.success(result?.message || t(lang, 'rdpConnectStarted'));
        return;
      }
      message.warning(result?.message || t(lang, 'remoteFallback'));
      await downloadRdp(remote, false);
    } catch (error) {
      message.warning(error instanceof Error ? error.message : t(lang, 'remoteFallback'));
      await downloadRdp(remote, false);
    } finally {
      setBusy(false);
    }
  };

  const openGuac = async (remote: RemoteConnection) => {
    if (!remote) return;
    setBusy(true);
    try {
      const response = await postForm('/api/guacamole/connect', {
        target: remoteTarget(remote),
        user: remote.username,
        password: remote.password
      });
      const result = await response.json().catch(() => ({}));
      if (response.ok && result?.url) {
        window.open(result.url, '_blank');
        return;
      }
      message.warning(result?.message || t(lang, 'remoteFallback'));
      await downloadRdp(remote, false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="env-card" loading={busy}>
      <div className="env-head">
        <div>
          <Space>
            <span className="env-arrow">→</span>
            <h3>{env.title}</h3>
            {remotes[0]?.type && <Tag color="blue">{remotes[0].type}</Tag>}
          </Space>
          <TagLine tags={env.tags} />
        </div>
        <div className="env-card-actions">
          {vpnGuides.length > 0 && (
              <EnvVpnSetting
              lang={lang}
              vpnGuides={vpnGuides}
              vpnRequired={vpnState.required}
              selectedVpnGuideId={selectedVpnGuideId}
              loading={vpnBusy}
              onChange={updateVpn}
              disabled={!canWrite}
            />
          )}
          {showDetails && canCheckHealth && <Tag color={ok ? 'success' : 'error'}>{ok ? t(lang, 'running') : t(lang, 'unreachable')}</Tag>}
          {editingDetails ? (
            <>
              <Button size="small" type="primary" icon={<SaveOutlined />} loading={serverBusy} onClick={saveAppServerDraft}>{t(lang, 'save')}</Button>
              <Button size="small" disabled={serverBusy} onClick={cancelEditDetails}>{t(lang, 'cancel')}</Button>
            </>
          ) : canWrite ? (
            <Dropdown
              trigger={['click']}
              menu={{
                items: [
                  { key: 'edit', icon: <EditOutlined />, label: t(lang, 'edit') },
                  {
                    key: 'delete',
                    danger: true,
                    label: (
                      <Popconfirm
                        title={t(lang, 'deleteEnvironmentConfirmTitle')}
                        description={`${env.organization_code} - ${env.organization_name} / ${env.title}`}
                        okText={t(lang, 'delete')}
                        cancelText={t(lang, 'cancel')}
                        okButtonProps={{ danger: true }}
                        onConfirm={deleteThisEnvironment}
                      >
                        <span className="danger-menu-action" onClick={(event) => event.stopPropagation()}>
                          <DeleteOutlined />
                          {t(lang, 'deleteEnvironment')}
                        </span>
                      </Popconfirm>
                    )
                  },
                ],
                onClick: ({ key }) => {
                  if (key === 'edit') startEditDetails();
                }
              }}
            >
              <Button type="text" className="more-action" icon={<MoreOutlined />} />
            </Dropdown>
          ) : null}
          {!editingDetails && (
            <Button
              size="small"
              className="env-expand-toggle"
              icon={expanded ? <UpOutlined /> : <DownOutlined />}
              onClick={() => setExpanded((value) => !value)}
              aria-label={expanded ? t(lang, 'collapse') : t(lang, 'expand')}
            />
          )}
        </div>
      </div>
      {showDetails && canCheckHealth && (
        <div className="health-line">
          <Tag>HTTP {health.data?.status || '...'}</Tag>
          <Tag>{health.data?.elapsedMs ?? '-'} ms</Tag>
          {health.data?.platform && <Tag>{lang === 'zh' ? 'OS推测' : 'OS推測'}: {health.data.platform}</Tag>}
          {health.data?.ttl && <Tag>TTL {health.data.ttl}</Tag>}
        </div>
      )}
      {showDetails && selectedVpnGuide && (
        <EnvVpnDetail lang={lang} guide={selectedVpnGuide} enabled={vpnState.required} />
      )}
      {showDetails && editingDetails && (
        <EnvironmentBasicEditor lang={lang} draft={envDraft} disabled={serverBusy} onChange={updateEnvDraft} />
      )}
      {showDetails && editingDetails && (
        <OptionalFunctionPicker
          lang={lang}
          disabled={serverBusy}
          showAppAccess={showAppAccessEditor}
          showDatabase={showDatabaseEditor}
          onAddAppAccess={() => setShowAppAccessEditor(true)}
          onAddDatabase={() => setShowDatabaseEditor(true)}
        />
      )}
      {showDetails && editingDetails && showAppAccessEditor ? (
        <AppAccessEditor lang={lang} draft={envDraft} disabled={serverBusy} onChange={updateEnvDraft} onRemove={removeAppAccess} />
      ) : showDetails && !editingDetails && hasAppAccess(env) ? (
        <InfoBlock title={t(lang, 'appAccess')}>
          <InfoRow label={t(lang, 'url')} value={env.url} link disabled={!ok} onCopy={copy} />
          <InfoRow label={t(lang, 'loginId')} value={env.login_id} onCopy={copy} />
          <InfoRow label={t(lang, 'password')} value={env.login_password} secret onCopy={copy} />
        </InfoBlock>
      ) : null}
      {showDetails && editingDetails && showDatabaseEditor ? (
        <DatabaseEditor lang={lang} draft={envDraft} disabled={serverBusy} onChange={updateEnvDraft} onRemove={removeDatabaseInfo} />
      ) : showDetails && !editingDetails && hasDatabaseInfo(env) ? (
        <InfoBlock title={t(lang, 'databaseInfo')} tags={[env.db_type, env.db_version && `${env.db_type} ${env.db_version}`].filter(Boolean)}>
          <InfoRow label={t(lang, 'dbAddress')} value={[env.db_host, env.db_port, env.db_name].filter(Boolean).join(':')} onCopy={copy} />
          <InfoRow label={t(lang, 'dbUser')} value={env.db_user} onCopy={copy} />
          <InfoRow label={t(lang, 'dbPassword')} value={env.db_password} secret onCopy={copy} />
        </InfoBlock>
      ) : null}
      {showDetails && editingDetails ? (
        <AppServerEditor
          lang={lang}
          servers={appServerDraft}
          disabled={serverBusy}
          onAdd={addAppServer}
          onRemove={removeAppServer}
          onChange={updateAppServerDraft}
        />
      ) : showDetails && appServers.length > 0 ? (
        <AppServerInfoBlock lang={lang} servers={appServers} onCopy={copy} />
      ) : null}
      {showDetails && editingDetails ? (
        <RemoteConnectionEditor lang={lang} remotes={remoteDraft} disabled={serverBusy} onAdd={addRemoteConnection} onRemove={removeRemoteConnection} onChange={updateRemoteDraft} />
      ) : showDetails && remotes.length > 0 ? (
        <RemoteConnectionInfoBlock
          lang={lang}
          remotes={remotes}
          guacamoleAvailable={Boolean(config.data?.guacamoleAvailable)}
          onCopy={copy}
          onDirect={connectRdp}
          onGuac={openGuac}
          onRdp={(remote) => downloadRdp(remote)}
        />
      ) : null}
    </Card>
  );
}

function createEnvironmentDraft(env: Environment): EnvironmentDraft {
  return {
    title: env.title || '',
    tags: env.tags.filter((tag) => tag.source !== 'auto').map((tag) => tag.name).join(', '),
    url: env.url || '',
    login_id: env.login_id || '',
    login_password: env.login_password || '',
    db_type: env.db_type || '',
    db_version: env.db_version || '',
    db_host: env.db_host || '',
    db_port: env.db_port ?? null,
    db_name: env.db_name || '',
    db_user: env.db_user || '',
    db_password: env.db_password || ''
  };
}

function hasAppAccess(env: Environment): boolean {
  return [env.url, env.login_id, env.login_password].some((value) => Boolean(String(value || '').trim()));
}

function hasDatabaseInfo(env: Environment): boolean {
  return [env.db_type, env.db_version, env.db_host, env.db_port, env.db_name, env.db_user, env.db_password].some((value) => Boolean(String(value || '').trim()));
}

function EnvironmentBasicEditor({ lang, draft, disabled, onChange }: { lang: Lang; draft: EnvironmentDraft; disabled: boolean; onChange: (patch: Partial<EnvironmentDraft>) => void }) {
  return (
    <InfoBlock title={t(lang, 'serverBasicInfo')}>
      <div className="env-edit-grid env-basic-edit">
        <label>
          <span>{t(lang, 'environmentName')}</span>
          <Input disabled={disabled} value={draft.title} onChange={(event) => onChange({ title: event.target.value })} />
        </label>
        <label>
          <span>{t(lang, 'tags')}</span>
          <Input disabled={disabled} value={draft.tags} placeholder={t(lang, 'environmentTagsPlaceholder')} onChange={(event) => onChange({ tags: event.target.value })} />
        </label>
      </div>
    </InfoBlock>
  );
}

function OptionalFunctionPicker({ lang, disabled, showAppAccess, showDatabase, onAddAppAccess, onAddDatabase }: { lang: Lang; disabled: boolean; showAppAccess: boolean; showDatabase: boolean; onAddAppAccess: () => void; onAddDatabase: () => void }) {
  if (showAppAccess && showDatabase) return null;
  return (
    <div className="optional-function-picker">
      <span>{t(lang, 'addServerFunctionHint')}</span>
      <Space wrap>
        {!showAppAccess && (
          <Button size="small" icon={<PlusOutlined />} disabled={disabled} onClick={onAddAppAccess}>
            {t(lang, 'addAppAccess')}
          </Button>
        )}
        {!showDatabase && (
          <Button size="small" icon={<PlusOutlined />} disabled={disabled} onClick={onAddDatabase}>
            {t(lang, 'addDatabaseInfo')}
          </Button>
        )}
      </Space>
    </div>
  );
}

function AppAccessEditor({ lang, draft, disabled, onChange, onRemove }: { lang: Lang; draft: EnvironmentDraft; disabled: boolean; onChange: (patch: Partial<EnvironmentDraft>) => void; onRemove: () => void }) {
  return (
    <InfoBlock
      title={t(lang, 'appAccess')}
      action={<Button danger size="small" icon={<DeleteOutlined />} disabled={disabled} onClick={onRemove} />}
    >
      <div className="env-edit-grid app-access-edit">
        <label className="wide">
          <span>{t(lang, 'url')}</span>
          <Input disabled={disabled} value={draft.url} onChange={(event) => onChange({ url: event.target.value })} />
        </label>
        <label>
          <span>{t(lang, 'loginId')}</span>
          <Input disabled={disabled} value={draft.login_id} onChange={(event) => onChange({ login_id: event.target.value })} />
        </label>
        <label>
          <span>{t(lang, 'password')}</span>
          <Input.Password disabled={disabled} value={draft.login_password} onChange={(event) => onChange({ login_password: event.target.value })} />
        </label>
      </div>
    </InfoBlock>
  );
}

function DatabaseEditor({ lang, draft, disabled, onChange, onRemove }: { lang: Lang; draft: EnvironmentDraft; disabled: boolean; onChange: (patch: Partial<EnvironmentDraft>) => void; onRemove: () => void }) {
  return (
    <InfoBlock
      title={t(lang, 'databaseInfo')}
      tags={[draft.db_type, draft.db_version && `${draft.db_type} ${draft.db_version}`].filter(Boolean)}
      action={<Button danger size="small" icon={<DeleteOutlined />} disabled={disabled} onClick={onRemove} />}
    >
      <div className="env-edit-grid database-edit">
        <label>
          <span>{t(lang, 'dbType')}</span>
          <Input disabled={disabled} value={draft.db_type} onChange={(event) => onChange({ db_type: event.target.value })} />
        </label>
        <label>
          <span>{t(lang, 'dbVersion')}</span>
          <Input disabled={disabled} value={draft.db_version} onChange={(event) => onChange({ db_version: event.target.value })} />
        </label>
        <label>
          <span>{t(lang, 'dbHost')}</span>
          <Input disabled={disabled} value={draft.db_host} onChange={(event) => onChange({ db_host: event.target.value })} />
        </label>
        <label>
          <span>{t(lang, 'dbPort')}</span>
          <Input disabled={disabled} value={draft.db_port ?? ''} onChange={(event) => onChange({ db_port: event.target.value ? Number(event.target.value) : null })} />
        </label>
        <label>
          <span>{t(lang, 'dbName')}</span>
          <Input disabled={disabled} value={draft.db_name} onChange={(event) => onChange({ db_name: event.target.value })} />
        </label>
        <label>
          <span>{t(lang, 'dbUser')}</span>
          <Input disabled={disabled} value={draft.db_user} onChange={(event) => onChange({ db_user: event.target.value })} />
        </label>
        <label className="wide">
          <span>{t(lang, 'dbPassword')}</span>
          <Input.Password disabled={disabled} value={draft.db_password} onChange={(event) => onChange({ db_password: event.target.value })} />
        </label>
      </div>
    </InfoBlock>
  );
}

function emptyAppServer(): AppServer {
  return { type: '', name: '', host: '', port: null, os: '', note: '', details: [] };
}

function AppServerInfoBlock({ lang, servers, onCopy }: { lang: Lang; servers: AppServer[]; onCopy: (value: string) => void }) {
  return (
    <InfoBlock title={t(lang, 'appServerInfo')} tags={Array.from(new Set(servers.map((server) => server.type).filter(Boolean)))}>
      <div className="app-server-list">
        {servers.map((server, index) => {
          const address = [server.host, server.port].filter(Boolean).join(':');
          const details = normalizeAppServerDetails(server.details);
          return (
            <div className="app-server-item" key={server.id || `${server.type}-${server.host}-${index}`}>
              <div className="app-server-head">
                <strong>{server.name || server.host || `${t(lang, 'serverInfo')} ${index + 1}`}</strong>
                {server.type && <Tag color={serverTypeColor(server.type)}>{server.type}</Tag>}
              </div>
              <InfoRow label={t(lang, 'appServerHost')} value={address} onCopy={onCopy} />
              {server.os && <InfoRow label={t(lang, 'appServerOs')} value={server.os} onCopy={onCopy} />}
              {server.note && <InfoRow label={t(lang, 'appServerNote')} value={server.note} onCopy={onCopy} />}
              {details.map((detail, detailIndex) => (
                <InfoRow
                  key={`${detail.key}-${detailIndex}`}
                  label={detail.key || t(lang, 'appServerDetails')}
                  value={detail.value}
                  onCopy={onCopy}
                />
              ))}
            </div>
          );
        })}
      </div>
    </InfoBlock>
  );
}

function AppServerEditor({ lang, servers, disabled, onAdd, onRemove, onChange }: { lang: Lang; servers: AppServer[]; disabled: boolean; onAdd: () => void; onRemove: (index: number) => void; onChange: (index: number, patch: Partial<AppServer>) => void }) {
  return (
    <InfoBlock title={t(lang, 'appServerInfo')}>
      <div className="app-server-editor-list">
        {servers.map((server, index) => (
          <div className="app-server-edit-card" key={index}>
            <div className="app-server-edit-grid">
              <label>
                <span>{t(lang, 'appServerType')}</span>
                <Input
                  value={server.type || ''}
                  disabled={disabled}
                  placeholder="Apache / Tomcat / Nginx / MinIO / Nacos"
                  onChange={(event) => onChange(index, { type: event.target.value })}
                />
              </label>
              <label>
                <span>{t(lang, 'appServerName')}</span>
                <Input disabled={disabled} value={server.name || ''} onChange={(event) => onChange(index, { name: event.target.value })} />
              </label>
              <label>
                <span>{t(lang, 'appServerHost')}</span>
                <Input disabled={disabled} value={server.host || ''} onChange={(event) => onChange(index, { host: event.target.value })} />
              </label>
              <label>
                <span>{t(lang, 'appServerPort')}</span>
                <Input
                  disabled={disabled}
                  value={server.port ?? ''}
                  onChange={(event) => onChange(index, { port: event.target.value ? Number(event.target.value) : null })}
                />
              </label>
              <label>
                <span>{t(lang, 'appServerOs')}</span>
                <Input disabled={disabled} value={server.os || ''} onChange={(event) => onChange(index, { os: event.target.value })} />
              </label>
              <label className="app-server-note-input">
                <span>{t(lang, 'appServerNote')}</span>
                <Input disabled={disabled} value={server.note || ''} onChange={(event) => onChange(index, { note: event.target.value })} />
              </label>
              <div className="app-server-detail-editor">
                <div className="app-server-detail-head">
                  <span>{t(lang, 'appServerDetails')}</span>
                  <Button
                    size="small"
                    icon={<PlusOutlined />}
                    disabled={disabled}
                    onClick={() => onChange(index, { details: [...normalizeAppServerDetails(server.details), { key: '', value: '' }] })}
                  >
                    {t(lang, 'addAppServerDetail')}
                  </Button>
                </div>
                {normalizeAppServerDetails(server.details).map((detail, detailIndex) => (
                  <div className="app-server-detail-row" key={detailIndex}>
                    <Input
                      disabled={disabled}
                      value={detail.key}
                      placeholder={t(lang, 'appServerDetailKey')}
                      onChange={(event) => {
                        const details = normalizeAppServerDetails(server.details);
                        details[detailIndex] = { ...details[detailIndex], key: event.target.value };
                        onChange(index, { details });
                      }}
                    />
                    <Input
                      disabled={disabled}
                      value={detail.value}
                      placeholder={t(lang, 'appServerDetailValue')}
                      onChange={(event) => {
                        const details = normalizeAppServerDetails(server.details);
                        details[detailIndex] = { ...details[detailIndex], value: event.target.value };
                        onChange(index, { details });
                      }}
                    />
                    <Button
                      danger
                      size="small"
                      icon={<DeleteOutlined />}
                      disabled={disabled}
                      onClick={() => onChange(index, { details: normalizeAppServerDetails(server.details).filter((_, itemIndex) => itemIndex !== detailIndex) })}
                    />
                  </div>
                ))}
              </div>
            </div>
            <Button danger size="small" icon={<DeleteOutlined />} disabled={disabled} onClick={() => onRemove(index)} />
          </div>
        ))}
        <Button icon={<PlusOutlined />} disabled={disabled} onClick={onAdd}>{t(lang, 'addAppServer')}</Button>
      </div>
    </InfoBlock>
  );
}

function emptyRemoteConnection(): RemoteConnection {
  return { id: '', scope: 'private', source: 'private', name: '', type: 'RDP', host: '', port: 3389, username: '', password: '', note: '' };
}

function RemoteConnectionInfoBlock({ lang, remotes, guacamoleAvailable, onCopy, onDirect, onGuac, onRdp }: { lang: Lang; remotes: RemoteConnection[]; guacamoleAvailable: boolean; onCopy: (value: string) => void; onDirect: (remote: RemoteConnection) => void; onGuac: (remote: RemoteConnection) => void; onRdp: (remote: RemoteConnection) => void }) {
  return (
    <InfoBlock title={t(lang, 'remoteConnectionInfo')} tags={Array.from(new Set(remotes.map((remote) => remote.type).filter(Boolean)))}>
      <div className="app-server-list">
        {remotes.map((remote, index) => (
          <RemoteConnectionItem
            key={remote.id || remote.masterId || `${remote.host}-${remote.port}-${index}`}
            lang={lang}
            remote={remote}
            guacamoleAvailable={guacamoleAvailable}
            onCopy={onCopy}
            onDirect={onDirect}
            onGuac={onGuac}
            onRdp={onRdp}
          />
        ))}
      </div>
    </InfoBlock>
  );
}

function RemoteConnectionItem({ lang, remote, guacamoleAvailable, onCopy, onDirect, onGuac, onRdp }: { lang: Lang; remote: RemoteConnection; guacamoleAvailable: boolean; onCopy: (value: string) => void; onDirect: (remote: RemoteConnection) => void; onGuac: (remote: RemoteConnection) => void; onRdp: (remote: RemoteConnection) => void }) {
  const check = useQuery({
    queryKey: ['remote-check', remote.type, remote.host, remote.port],
    queryFn: () => fetchRemoteCheck(remote),
    enabled: Boolean(remote.host),
    refetchInterval: 60_000,
    staleTime: 50_000
  });
  const reachable = Boolean(check.data?.ok);
  const target = `${remote.host}${remote.port ? `:${remote.port}` : ''}`;
  const scopeLabel = remote.scope === 'shared' ? t(lang, 'remoteShared') : t(lang, 'remotePrivate');
  const sourceLabel = remote.source === 'autoShared' ? t(lang, 'autoShared') : scopeLabel;
  return (
    <div className="app-server-item">
      <div className="app-server-head">
        <strong>{remote.name || target || t(lang, 'remoteConnectionInfo')}</strong>
        <Space size={6} wrap>
          <Tag color={remote.scope === 'shared' ? 'gold' : 'default'}>{sourceLabel}</Tag>
          <Tag color={reachable ? 'success' : 'error'}>{reachable ? t(lang, 'remoteReachable') : t(lang, 'remoteUnreachable')}</Tag>
        </Space>
      </div>
      {!reachable && <div className="remote-check-warning">{t(lang, 'remoteCheckHint')}</div>}
      <InfoRow label={t(lang, 'serverAddress')} value={target} onCopy={onCopy} extra={<RemoteActions disabled={!reachable} guacamoleAvailable={guacamoleAvailable} lang={lang} remote={remote} onDirect={() => onDirect(remote)} onGuac={() => onGuac(remote)} onRdp={() => onRdp(remote)} />} />
      <InfoRow label={t(lang, 'serverUser')} value={remote.username} onCopy={onCopy} />
      <InfoRow label={t(lang, 'serverPassword')} value={remote.password} secret onCopy={onCopy} />
      {remote.note && <InfoRow label={t(lang, 'remoteNote')} value={remote.note} onCopy={onCopy} />}
    </div>
  );
}

function RemoteConnectionEditor({ lang, remotes, disabled, onAdd, onRemove, onChange }: { lang: Lang; remotes: RemoteConnection[]; disabled: boolean; onAdd: () => void; onRemove: (index: number) => void; onChange: (index: number, patch: Partial<RemoteConnection>) => void }) {
  return (
    <InfoBlock title={t(lang, 'remoteConnectionInfo')}>
      <div className="app-server-editor-list">
        {remotes.map((remote, index) => (
          <div className="app-server-edit-card" key={remote.id || remote.masterId || index}>
            <div className="app-server-edit-grid">
              <label>
                <span>{t(lang, 'remoteScope')}</span>
                <Select
                  disabled={disabled || remote.source === 'autoShared'}
                  value={remote.scope || 'private'}
                  options={[{ value: 'private', label: t(lang, 'remotePrivate') }, { value: 'shared', label: t(lang, 'remoteShared') }]}
                  onChange={(value) => onChange(index, { scope: value })}
                />
              </label>
              <label>
                <span>{t(lang, 'type')}</span>
                <Select disabled={disabled || remote.source === 'autoShared'} value={remote.type || 'RDP'} options={[{ value: 'RDP', label: 'RDS/RDP' }, { value: 'SSH', label: 'SSH' }]} onChange={(value) => onChange(index, { type: value, port: value === 'SSH' ? 22 : 3389 })} />
              </label>
              <label>
                <span>{t(lang, 'remoteName')}</span>
                <Input disabled={disabled || remote.source === 'autoShared'} value={remote.name || ''} onChange={(event) => onChange(index, { name: event.target.value })} />
              </label>
              <label>
                <span>{t(lang, 'remoteHost')}</span>
                <Input disabled={disabled || remote.source === 'autoShared'} value={remote.host || ''} onChange={(event) => onChange(index, { host: event.target.value })} />
              </label>
              <label>
                <span>{t(lang, 'remotePort')}</span>
                <Input disabled={disabled || remote.source === 'autoShared'} value={remote.port ?? ''} onChange={(event) => onChange(index, { port: event.target.value ? Number(event.target.value) : undefined })} />
              </label>
              <label>
                <span>{t(lang, 'serverUser')}</span>
                <Input disabled={disabled || remote.source === 'autoShared'} value={remote.username || ''} onChange={(event) => onChange(index, { username: event.target.value })} />
              </label>
              <label>
                <span>{t(lang, 'serverPassword')}</span>
                <Input.Password disabled={disabled || remote.source === 'autoShared'} value={remote.password || ''} onChange={(event) => onChange(index, { password: event.target.value })} />
              </label>
              <label className="app-server-note-input">
                <span>{t(lang, 'remoteNote')}</span>
                <Input disabled={disabled || remote.source === 'autoShared'} value={remote.note || ''} onChange={(event) => onChange(index, { note: event.target.value })} />
              </label>
            </div>
            <Button danger size="small" icon={<DeleteOutlined />} disabled={disabled} onClick={() => onRemove(index)} />
          </div>
        ))}
        <Button icon={<PlusOutlined />} disabled={disabled} onClick={onAdd}>{t(lang, 'addRemoteConnection')}</Button>
      </div>
    </InfoBlock>
  );
}

function normalizeAppServerDetails(details: AppServer['details']): Array<{ key: string; value: string }> {
  return (details || []).map((detail) => ({
    key: detail.key || '',
    value: detail.value || ''
  }));
}

function EnvVpnDetail({ lang, guide, enabled }: { lang: Lang; guide: VpnGuide; enabled: boolean }) {
  const steps = guide.workflow || [];
  const sourceCount = (guide.sourceFiles || []).length;
  const stepLabel = lang === 'zh' ? `${steps.length} 个步骤` : `${steps.length} 手順`;
  const sourceLabel = lang === 'zh' ? `${sourceCount} 个来源文件` : `${sourceCount} 件の原資料`;

  return (
    <div className={enabled ? 'env-vpn-reference enabled' : 'env-vpn-reference'}>
      <div className="env-vpn-detail-head">
        <Space wrap>
          <SafetyCertificateOutlined />
          <strong>{guide.name}</strong>
          {(guide.tags || []).map((tag) => <Tag key={tag} color={tagColor(tag)}>{tag}</Tag>)}
          <Tag color={enabled ? 'success' : 'default'}>{enabled ? (lang === 'zh' ? '已启用' : '有効') : (lang === 'zh' ? '可选流程' : '選択可能')}</Tag>
          {guide.workflowStatus === 'analyzing' && <Tag color="processing">{t(lang, 'aiAnalyzing')}</Tag>}
        </Space>
      </div>
      <div className="env-vpn-reference-body">
        <span>{t(lang, 'vpnReferenceHint')}</span>
        <Space wrap size={6}>
          {steps.length > 0 && <Tag>{stepLabel}</Tag>}
          {sourceCount > 0 && <Tag icon={<FileTextOutlined />}>{sourceLabel}</Tag>}
          {guide.workflowStatus === 'ready' && <Tag color="gold">{t(lang, 'aiReady')}</Tag>}
        </Space>
      </div>
    </div>
  );
}

function EnvVpnSetting({ lang, vpnRequired, vpnGuides, selectedVpnGuideId, loading, disabled, onChange }: { lang: Lang; vpnRequired: boolean; vpnGuides: VpnGuide[]; selectedVpnGuideId?: string; loading: boolean; disabled?: boolean; onChange: (vpnRequired: boolean, vpnGuideId?: string | null) => void }) {
  const visibleGuideId = vpnRequired ? selectedVpnGuideId || vpnGuides[0]?.id : undefined;

  return (
    <div className="env-vpn-setting">
      <Button
        size="small"
        loading={loading}
        disabled={disabled}
        className={vpnRequired ? 'vpn-toggle active' : 'vpn-toggle'}
        icon={<SafetyCertificateOutlined />}
        onClick={() => onChange(!vpnRequired, !vpnRequired ? selectedVpnGuideId || vpnGuides[0]?.id : null)}
      >
        VPN
      </Button>
      <Select
        size="small"
        popupMatchSelectWidth={false}
        disabled={disabled || loading || !vpnRequired || vpnGuides.length === 0}
        value={visibleGuideId}
        placeholder={t(lang, 'selectVpnGuide')}
        className={vpnRequired ? 'vpn-guide-select active' : 'vpn-guide-select available'}
        options={vpnGuides.map((guide) => ({ value: guide.id, label: guide.name }))}
        onChange={(value) => onChange(true, value)}
      />
    </div>
  );
}

function TagLine({ tags }: { tags: TagItem[] }) {
  return (
    <div className="tag-line">
      {tags.slice(0, 6).map((tag) => <OneTag key={tag.name} name={tag.name} />)}
      {tags.length > 6 && <Tag>+{tags.length - 6}</Tag>}
    </div>
  );
}

function InfoBlock({ title, children, tags = [], action }: { title: string; children: ReactNode; tags?: string[]; action?: ReactNode }) {
  return (
    <div className="info-block">
      <div className="info-title-row">
        <div className="info-title">▼ {title} {tags.map((tag) => <OneTag key={tag} name={tag} kind="service" />)}</div>
        {action}
      </div>
      {children}
    </div>
  );
}

function serverTypeColor(type: string): string {
  return serviceTagColor(type);
}

function tagColor(name: string): string {
  return oneTagColor(name);
}

function InfoRow({ label, value, link, secret, disabled, onCopy, extra }: { label: string; value: string; link?: boolean; secret?: boolean; disabled?: boolean; onCopy: (value: string) => void; extra?: React.ReactNode }) {
  const [shown, setShown] = useState(!secret);
  return (
    <div className="info-row">
      <span className="info-label">{label}</span>
      <span className="info-value">{link && !disabled ? <a href={value} target="_blank">{value}</a> : shown ? value : '••••••••'}</span>
      <Space size={6}>
        {link && <Tooltip title="Open"><Button disabled={disabled} icon={<GlobalOutlined />} href={disabled ? undefined : value} target="_blank" /></Tooltip>}
        {secret && <Button icon={shown ? <EyeInvisibleOutlined /> : <EyeOutlined />} onClick={() => setShown(!shown)} />}
        {extra}
        <Button icon={<CopyOutlined />} onClick={() => onCopy(value)} />
      </Space>
    </div>
  );
}

function ConnectionSection({ lang, organizations }: { lang: Lang; organizations: Organization[] }) {
  const summary = useMemo(() => buildConnectionSummary(organizations), [organizations]);
  const guideFileRows = summary.guides.filter((item) => (item.guide.sourceFiles || []).length > 0);
  const vpnPercent = summary.total > 0 ? Math.round((summary.vpn / summary.total) * 100) : 0;
  const directLabel = lang === 'zh' ? '直接访问' : '直接訪問';
  const vpnLabel = lang === 'zh' ? '需 VPN 访问' : 'VPN 訪問が必要';
  const dedicatedLabel = lang === 'zh' ? '专线访问' : '専用線訪問';
  const unit = lang === 'zh' ? '个环境' : '件の環境';
  const noGuides = lang === 'zh' ? '当前范围内没有登记 VPN 流程' : '現在の範囲に VPN 流程はありません';
  const noFiles = lang === 'zh' ? '当前范围内没有 AI 来源资料' : '現在の範囲に AI 原資料はありません';

  return (
    <Card className="connection-section">
      <h2>{t(lang, 'connection')}</h2>
      <Row gutter={[20, 20]}>
        <Col xs={24} lg={8}>
          <div className="donut-box">
            <Progress type="circle" percent={vpnPercent} format={() => summary.total} strokeColor="#ee9f13" trailColor="#d8eef3" />
            <ul>
              <li><span className="dot blue" />{directLabel} <b>{summary.direct}</b> {unit}</li>
              <li><span className="dot gold" />{vpnLabel} <b>{summary.vpn}</b> {unit}</li>
              <li><span className="dot teal" />{dedicatedLabel} <b>{summary.dedicated}</b> {unit}</li>
            </ul>
          </div>
        </Col>
        <Col xs={24} lg={10}>
          <div className="vpn-table">
            {summary.guides.length === 0 && <div className="empty-row">{noGuides}</div>}
            {summary.guides.map((item) => (
              <div className="vpn-row" key={item.key}>
                <span>
                  <strong>{item.guide.name}</strong>
                  <small>{item.organizationCode} - {item.organizationName} / {item.usedBy} {unit}</small>
                </span>
                <Tag color={item.requestRequired ? 'orange' : 'gold'}>{item.requestRequired ? (lang === 'zh' ? '申请必要' : '申請必要') : t(lang, 'vpn')}</Tag>
                <Tag icon={<FileTextOutlined />}>{(item.guide.sourceFiles || []).length}</Tag>
              </div>
            ))}
          </div>
        </Col>
        <Col xs={24} lg={6}>
          <div className="file-box">
            {guideFileRows.length === 0 && <div className="empty-row">{noFiles}</div>}
            {guideFileRows.slice(0, 6).map((item) => (
              <div key={item.key}>
                <span>
                  <strong>{sourceFileName(item.guide.sourceFiles?.[0])}</strong>
                  <small>{item.organizationCode} - {item.guide.name}</small>
                </span>
                <Tag icon={<FileTextOutlined />}>{item.guide.sourceFiles?.length || 0}</Tag>
              </div>
            ))}
          </div>
        </Col>
      </Row>
    </Card>
  );
}

function ChangeLog({ lang }: { lang: Lang }) {
  return (
    <Card className="change-log">
      <div className="section-title-row"><h2>{t(lang, 'changeLog')}</h2><Button>{t(lang, 'registerAllLogs')}</Button></div>
      {[1, 2, 3, 4].map((item) => (
        <div className="log-row" key={item}>
          <span>2026-05-01 10:{30 + item}</span><span>Admin</span><span>{t(lang, 'update')}</span><span>{t(lang, 'title')}</span><span>{t(lang, 'updatedServerDb')}</span><Button type="text" icon={<MoreOutlined />} />
        </div>
      ))}
    </Card>
  );
}
