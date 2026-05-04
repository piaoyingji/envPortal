import { DatabaseOutlined, FileProtectOutlined, GitlabOutlined, PlusOutlined, ProductOutlined, SaveOutlined, UsergroupAddOutlined } from '@ant-design/icons';
import { Button, Card, Empty, Input, Modal, Space, Tooltip, message } from 'antd';
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { createOrganization, updateOrganization } from '../lib/api';
import { t } from '../lib/i18n';
import type { AppServer, Environment, Lang, Organization, RemoteConnection } from '../lib/types';
import OneTag from '../components/OneTag';

type Props = {
  lang: Lang;
  organizations: Organization[];
  canWrite: boolean;
};

type CustomerDraft = {
  code: string;
  name: string;
};

export default function CustomerMasterPage({ lang, organizations, canWrite }: Props) {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState(() => organizations[0]?.id || '');
  const [createOpen, setCreateOpen] = useState(false);
  const [createDraft, setCreateDraft] = useState<CustomerDraft>({ code: '', name: '' });
  const [editMode, setEditMode] = useState(false);
  const [editDraft, setEditDraft] = useState<CustomerDraft>({ code: '', name: '' });
  const [saving, setSaving] = useState(false);

  const selected = useMemo(
    () => organizations.find((org) => org.id === selectedId) || organizations[0] || null,
    [organizations, selectedId]
  );

  useEffect(() => {
    if (selected && selected.id !== selectedId) setSelectedId(selected.id);
    if (!selected && organizations[0]) setSelectedId(organizations[0].id);
  }, [organizations, selected, selectedId]);

  useEffect(() => {
    if (selected && !editMode) setEditDraft({ code: selected.code, name: selected.name });
  }, [selected, editMode]);

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['portal-data'] });
    await queryClient.refetchQueries({ queryKey: ['portal-data'] });
  };

  const saveNewCustomer = async () => {
    setSaving(true);
    try {
      const created = await createOrganization(createDraft);
      setCreateOpen(false);
      setCreateDraft({ code: '', name: '' });
      message.success(t(lang, 'customerSaved'));
      await refresh();
      setSelectedId(created.id);
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Failed to create customer');
    } finally {
      setSaving(false);
    }
  };

  const saveCurrentCustomer = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      const updated = await updateOrganization(selected.id, editDraft);
      setSelectedId(updated.id);
      setEditMode(false);
      message.success(t(lang, 'customerSaved'));
      await refresh();
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Failed to update customer');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="customer-master-page">
      <Card className="customer-master-hero">
        <div>
          <h2>{t(lang, 'customerMaster')}</h2>
          <p>{t(lang, 'customerMasterSubtitle')}</p>
        </div>
        {canWrite && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            {t(lang, 'addCustomer')}
          </Button>
        )}
      </Card>

      <div className="customer-master-layout">
        <Card className="customer-master-list-card" title={t(lang, 'customers')}>
          <div className="customer-master-list">
            {organizations.map((org) => (
              <button
                key={org.id}
                type="button"
                className={org.id === selected?.id ? 'customer-master-item active' : 'customer-master-item'}
                onClick={() => {
                  setSelectedId(org.id);
                  setEditMode(false);
                }}
              >
                <span className="customer-master-code">{org.code}</span>
                <span className="customer-master-name">{org.name}</span>
                <span className="customer-master-meta">
                  {t(lang, 'environmentCount')} {org.environments.length} / {t(lang, 'vpnGuideCount')} {org.vpnGuides?.length || 0}
                </span>
              </button>
            ))}
          </div>
        </Card>

        <div className="customer-master-detail">
          {selected ? (
            <>
              <Card className="customer-master-basic-card">
                <div className="customer-master-detail-head">
                  <div>
                    <h2>{selected.name}</h2>
                    <span>{selected.code}</span>
                  </div>
                  {canWrite && (
                    <Space>
                      {editMode ? (
                        <>
                          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={saveCurrentCustomer}>{t(lang, 'save')}</Button>
                          <Button onClick={() => {
                            setEditDraft({ code: selected.code, name: selected.name });
                            setEditMode(false);
                          }}>{t(lang, 'cancel')}</Button>
                        </>
                      ) : (
                        <Button onClick={() => setEditMode(true)}>{t(lang, 'edit')}</Button>
                      )}
                    </Space>
                  )}
                </div>
                <div className="customer-master-fields">
                  <label>
                    <span>{t(lang, 'customerCode')}</span>
                    {editMode ? (
                      <Input value={editDraft.code} onChange={(event) => setEditDraft((draft) => ({ ...draft, code: event.target.value }))} />
                    ) : (
                      <b>{selected.code}</b>
                    )}
                  </label>
                  <label>
                    <span>{t(lang, 'customerName')}</span>
                    {editMode ? (
                      <Input value={editDraft.name} onChange={(event) => setEditDraft((draft) => ({ ...draft, name: event.target.value }))} />
                    ) : (
                      <b>{selected.name}</b>
                    )}
                  </label>
                  <label>
                    <span>{t(lang, 'lastUpdated')}</span>
                    <b>{formatDate(selected.updatedAt || selected.createdAt, lang)}</b>
                  </label>
                </div>
              </Card>

              <Card className="customer-master-section-card" title={t(lang, 'relatedEnvironments')}>
                {selected.environments.length > 0 ? (
                  <div className="customer-env-summary-list">
                    {selected.environments.map((env) => <EnvironmentSummary key={env.id} env={env} lang={lang} />)}
                  </div>
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t(lang, 'noEnvironments')} />
                )}
              </Card>

              <div className="customer-master-future-grid">
                <FutureCard title={t(lang, 'contractInfo')} icon={<FileProtectOutlined />} lang={lang} />
                <FutureCard title={t(lang, 'implementedProducts')} icon={<ProductOutlined />} lang={lang} />
                <FutureCard title={t(lang, 'customDevelopment')} icon={<UsergroupAddOutlined />} lang={lang} />
                <FutureCard title={t(lang, 'codeComparison')} icon={<GitlabOutlined />} lang={lang} />
              </div>
            </>
          ) : (
            <Card className="customer-master-section-card"><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} /></Card>
          )}
        </div>
      </div>

      <Modal
        open={createOpen}
        title={t(lang, 'addCustomer')}
        okText={t(lang, 'create')}
        cancelText={t(lang, 'cancel')}
        confirmLoading={saving}
        onOk={saveNewCustomer}
        onCancel={() => {
          setCreateOpen(false);
          setCreateDraft({ code: '', name: '' });
        }}
      >
        <div className="customer-create-form">
          <label>
            <span>{t(lang, 'customerCode')}</span>
            <Input value={createDraft.code} placeholder={t(lang, 'customerCodePlaceholder')} onChange={(event) => setCreateDraft((draft) => ({ ...draft, code: event.target.value }))} />
          </label>
          <label>
            <span>{t(lang, 'customerName')}</span>
            <Input value={createDraft.name} placeholder={t(lang, 'customerNamePlaceholder')} onChange={(event) => setCreateDraft((draft) => ({ ...draft, name: event.target.value }))} />
          </label>
        </div>
      </Modal>
    </div>
  );
}

function EnvironmentSummary({ env, lang }: { env: Environment; lang: Lang }) {
  const remotes = (env.remoteConnections || []).filter((remote) => remote.host);
  const services = (env.appServers || []).filter((server) => server.host || server.name || server.type);
  return (
    <article className="customer-env-summary">
      <div className="customer-env-summary-head">
        <div>
          <h3>{env.title}</h3>
          <Space size={[4, 4]} wrap>
            {env.tags.map((tag) => <OneTag key={`${env.id}-${tag.name}`} name={tag.name} />)}
          </Space>
        </div>
        <span>{env.vpn_required ? t(lang, 'vpnRequired') : t(lang, 'direct')}</span>
      </div>
      <div className="customer-env-summary-grid">
        <SummaryLine label={t(lang, 'appAccess')} value={env.url} />
        <SummaryLine label={t(lang, 'databaseInfo')} value={formatDb(env)} icon={env.db_type ? <DatabaseOutlined /> : undefined} />
        <SummaryLine label={t(lang, 'serverInfo')} value={formatRemotes(remotes, services)} />
      </div>
    </article>
  );
}

function SummaryLine({ label, value, icon }: { label: string; value: string; icon?: ReactNode }) {
  return (
    <div className="customer-env-summary-line">
      <span>{icon}{label}</span>
      <Tooltip title={value || '-'}>
        <b>{value || '-'}</b>
      </Tooltip>
    </div>
  );
}

function FutureCard({ title, icon, lang }: { title: string; icon: ReactNode; lang: Lang }) {
  return (
    <Card className="customer-master-future-card">
      <div className="future-icon">{icon}</div>
      <div>
        <h3>{title}</h3>
        <p>{t(lang, 'plannedFeature')}</p>
      </div>
    </Card>
  );
}

function formatDb(env: Environment): string {
  const address = [env.db_host, env.db_port].filter(Boolean).join(':');
  const db = [address, env.db_name].filter(Boolean).join('/');
  const type = [env.db_type, env.db_version].filter(Boolean).join(' ');
  return [type, db].filter(Boolean).join(' · ');
}

function formatRemotes(remotes: RemoteConnection[], services: AppServer[]): string {
  const remoteText = remotes.map((remote) => [remote.type, [remote.host, remote.port].filter(Boolean).join(':')].filter(Boolean).join(' '));
  const serviceText = services.map((server) => [server.type, server.name, [server.host, server.port].filter(Boolean).join(':')].filter(Boolean).join(' '));
  return [...remoteText, ...serviceText].filter(Boolean).slice(0, 4).join(' / ');
}

function formatDate(value: string | undefined, lang: Lang): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return new Intl.DateTimeFormat(lang === 'zh' ? 'zh-CN' : 'ja-JP', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(date);
}
