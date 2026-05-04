import { BellOutlined, DoubleLeftOutlined, DoubleRightOutlined, IdcardOutlined, QuestionCircleOutlined, SearchOutlined, UserOutlined } from '@ant-design/icons';
import { Avatar, Badge, Button, ConfigProvider, Layout, Select } from 'antd';
import jaJP from 'antd/locale/ja_JP';
import zhCN from 'antd/locale/zh_CN';
import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchMe, fetchPortalData } from './lib/api';
import { t } from './lib/i18n';
import type { CurrentUser, Environment, Lang, Organization } from './lib/types';
import EnvironmentPage from './pages/EnvironmentPage';
import CustomerMasterPage from './pages/CustomerMasterPage';
import DataNavigator from './components/DataNavigator';
import onecrmLogo from './assets/onecrm-logo.svg';
import LoginPage from './pages/LoginPage';
import { SystemMenu } from './components/SystemModals';

const { Sider, Content } = Layout;
const DataAdminPage = lazy(() => import('./pages/DataAdminPage'));
const RemoteAdminPage = lazy(() => import('./pages/RemoteAdminPage'));

type PageKey = 'customers' | 'environments' | 'data' | 'remote';

const navItems = [
  { key: 'customers', icon: <IdcardOutlined /> },
  { key: 'environments', icon: <UserOutlined /> },
] as const;

export default function App({ initialLang }: { initialLang: string }) {
  useEffect(() => {
    document.documentElement.dataset.onecrmBuild = import.meta.env.VITE_ONECRM_BUILD || 'dev';
    console.info('OneCRM frontend build', import.meta.env.VITE_ONECRM_BUILD || 'dev');
  }, []);

  const [lang, setLang] = useState<Lang>(initialLang === 'zh' ? 'zh' : 'ja');
  const [page, setPage] = useState<PageKey>(() => location.pathname.includes('customers') ? 'customers' : location.pathname.includes('admin') ? 'data' : location.pathname.includes('rdp') ? 'remote' : 'environments');
  const [selectedOrg, setSelectedOrgState] = useState<string>(() => localStorage.getItem('onecrm.selectedOrg') || 'all');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [navCollapsed, setNavCollapsed] = useState(() => localStorage.getItem('onecrm.navCollapsed') === '1');
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);

  const meQuery = useQuery({ queryKey: ['auth-me'], queryFn: fetchMe });
  useEffect(() => {
    if (meQuery.data?.authenticated && meQuery.data.user) setCurrentUser(meQuery.data.user);
    if (meQuery.data && !meQuery.data.authenticated) setCurrentUser(null);
  }, [meQuery.data]);

  const dataQuery = useQuery({ queryKey: ['portal-data'], queryFn: fetchPortalData, refetchInterval: 60_000, enabled: Boolean(currentUser) });
  const data = dataQuery.data || { organizations: [], tags: [] };
  const selectedOrgExists = selectedOrg === 'all' || data.organizations.some((org) => org.id === selectedOrg);

  useEffect(() => {
    if (data.organizations.length > 0 && !selectedOrgExists) {
      localStorage.setItem('onecrm.selectedOrg', 'all');
      setSelectedOrgState('all');
    }
  }, [data.organizations.length, selectedOrgExists]);

  const organizations = useMemo(() => filterOrganizations(data.organizations, selectedOrg, selectedTags), [data.organizations, selectedOrg, selectedTags]);
  const isGlobalView = selectedOrg === 'all' && selectedTags.length === 0;

  const changeLang = (value: Lang) => {
    localStorage.setItem('onecrm.lang', value);
    document.documentElement.lang = value === 'zh' ? 'zh-CN' : 'ja';
    setLang(value);
  };

  if (!meQuery.isLoading && !currentUser) {
    return (
      <ConfigProvider locale={lang === 'zh' ? zhCN : jaJP}>
        <LoginPage lang={lang} onLangChange={changeLang} onLogin={setCurrentUser} />
      </ConfigProvider>
    );
  }

  if (!currentUser) return null;

  const toggleNav = () => {
    const next = !navCollapsed;
    localStorage.setItem('onecrm.navCollapsed', next ? '1' : '0');
    setNavCollapsed(next);
  };

  const setSelectedOrg = (id: string) => {
    localStorage.setItem('onecrm.selectedOrg', id);
    setSelectedOrgState(id);
  };

  return (
    <ConfigProvider
      locale={lang === 'zh' ? zhCN : jaJP}
      theme={{
        token: {
          colorPrimary: '#c58a23',
          colorInfo: '#1e3d68',
          colorSuccess: '#21a76a',
          colorWarning: '#f2a51a',
          colorError: '#e84b43',
          borderRadius: 16,
          colorText: '#16233b',
          colorTextSecondary: '#738092',
          colorBorder: 'rgba(52, 64, 88, 0.16)',
          colorBgContainer: '#fffcf6',
          fontFamily: '"Inter", "Segoe UI", "Yu Gothic UI", "Meiryo", sans-serif'
        },
        components: {
          Card: { borderRadiusLG: 22 },
          Button: { borderRadius: 12 },
          Select: { borderRadius: 14 },
          Input: { borderRadius: 14 }
        }
      }}
    >
    <Layout className={navCollapsed ? 'app-shell nav-collapsed' : 'app-shell'}>
      <Sider width={navCollapsed ? 84 : 236} className="app-sider">
        <div className="brand">
          <img className="brand-mark" src={onecrmLogo} alt="OneCRM" />
          <div className="brand-copy">
            <div className="brand-name">OneCRM</div>
          <div className="brand-sub">{t(lang, 'brandSub')}</div>
          </div>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => {
            const enabledPage = item.key;
            const active = page === enabledPage;
            return (
              <button key={item.key} className={active ? 'nav-item active' : 'nav-item'} onClick={() => setPage(enabledPage)}>
                {item.icon}<span className="nav-label">{t(lang, item.key)}</span>
                {active && <span className="nav-chevron">›</span>}
              </button>
            );
          })}
          {/*
          <button className={page === 'data' ? 'nav-item active' : 'nav-item'} onClick={() => setPage('data')}>
            <DatabaseOutlined /><span className="nav-label">{t(lang, 'dataAdmin')}</span>
          </button>
          <button className={page === 'remote' ? 'nav-item active' : 'nav-item'} onClick={() => setPage('remote')}>
            <NodeIndexOutlined /><span className="nav-label">{t(lang, 'remoteAdmin')}</span>
          </button>
          */}
        </nav>
        <div className="admin-box">
          <Avatar className="admin-avatar">A</Avatar>
          <div className="admin-copy">
            <div className="admin-name">Admin</div>
          <div className="admin-role">{t(lang, 'adminRole')}</div>
          </div>
          <Button type="text" className="nav-collapse-button" icon={navCollapsed ? <DoubleRightOutlined /> : <DoubleLeftOutlined />} onClick={toggleNav} />
        </div>
      </Sider>
      <Layout className="main-layout">
        <div className="hero-top">
          <div>
            <h1>{page === 'customers' ? t(lang, 'customerMaster') : page === 'data' ? t(lang, 'dataAdmin') : page === 'remote' ? t(lang, 'remoteAdmin') : t(lang, 'title')}</h1>
            <p>{t(lang, 'subtitle')}</p>
          </div>
          <div className="top-actions">
            <Button type="text" icon={<SearchOutlined />} />
            <Badge count={3} size="small"><Button type="text" icon={<BellOutlined />} /></Badge>
            <Button type="text" icon={<QuestionCircleOutlined />} />
            <SystemMenu lang={lang} user={currentUser} onUserChange={setCurrentUser} onLoggedOut={() => setCurrentUser(null)} />
            <Avatar size={30} src={currentUser.avatarUrl ? `${currentUser.avatarUrl}?t=${Date.now()}` : undefined}>{currentUser.username[0]}</Avatar>
            <span className="lang-label">{t(lang, 'language')}</span>
            <Select value={lang} onChange={changeLang} className="lang-select" options={[{ value: 'ja', label: '日本語' }, { value: 'zh', label: '中文' }]} />
          </div>
        </div>
        {/*
          Reserved for a future full-text search surface.
          Current filtering is intentionally limited to the data navigator and tags.
          <div className="tool-bar">
            <Space size={18} wrap>
              <Input className="global-search" prefix={<SearchOutlined />} value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t(lang, 'search')} />
            </Space>
          </div>
        */}
        <div className={page === 'environments' ? 'workbench-layout' : 'workbench-layout no-data-nav'}>
          <Content className="content-wrap">
            {page === 'customers' && (
              <CustomerMasterPage lang={lang} organizations={data.organizations} canWrite={currentUser.role === 'Admins'} />
            )}
            {page === 'environments' && (
              <EnvironmentPage lang={lang} organizations={organizations} allOrganizations={data.organizations} tags={data.tags} selectedTags={selectedTags} setSelectedTags={setSelectedTags} isGlobalView={isGlobalView} canWrite={currentUser.role === 'Admins'} />
            )}
            <Suspense fallback={null}>
              {page === 'data' && <DataAdminPage lang={lang} organizations={data.organizations} />}
              {page === 'remote' && <RemoteAdminPage lang={lang} organizations={data.organizations} />}
            </Suspense>
          </Content>
          {page === 'environments' && (
            <DataNavigator
              lang={lang}
              organizations={data.organizations}
              selectedOrg={selectedOrg}
              setSelectedOrg={setSelectedOrg}
            />
          )}
        </div>
      </Layout>
    </Layout>
    </ConfigProvider>
  );
}

function filterOrganizations(orgs: Organization[], selectedOrg: string, selectedTags: string[]): Organization[] {
  return orgs
    .filter((org) => selectedOrg === 'all' || org.id === selectedOrg)
    .map((org) => {
      const environments = org.environments.filter((env) => {
        const tagNames = env.tags.map((tag) => tag.name);
        const matchesTags = selectedTags.every((tag) => tagNames.includes(tag));
        return matchesTags;
      });
      return { ...org, environments };
    })
    .filter((org) => org.environments.length > 0 || selectedTags.length === 0);
}
