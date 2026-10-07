import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

const GITHUB = 'https://github.com/zeroDtree/server-manager'
const AGENT = 'https://github.com/zeroDtree/server-agent'
const PREPARE = 'https://github.com/zeroDtree/account-prepare'

const config = withMermaid(
  defineConfig({
    title: 'GSAD',
    description: 'GPU Server Access Dashboard',
    base: '/server-manager/',
    ignoreDeadLinks: [/\.\.\//],
    themeConfig: {
      socialLinks: [{ icon: 'github', link: GITHUB }],
      search: {
        provider: 'local',
        options: {
          locales: {
            zh: {
              translations: {
                button: {
                  buttonText: '搜索文档',
                  buttonAriaLabel: '搜索文档',
                },
                modal: {
                  displayDetails: '显示详细列表',
                  noResultsText: '无法找到相关结果',
                  resetButtonTitle: '清除查询条件',
                  footer: {
                    selectText: '选择',
                    navigateText: '切换',
                    closeText: '关闭',
                  },
                },
              },
            },
          },
        },
      },
    },
    locales: {
      root: {
        label: 'English',
        lang: 'en-US',
        description: 'GPU Server Access Dashboard',
        themeConfig: {
          nav: [
            { text: 'Guide', link: '/' },
            { text: 'GitHub', link: GITHUB },
          ],
          outline: { label: 'On this page' },
          sidebar: [
            {
              text: 'Overview',
              items: [
                { text: 'GSAD', link: '/' },
                { text: 'User manual', link: '/gsad-user-manual' },
                { text: 'Admin manual', link: '/gsad-admin-manual' },
              ],
            },
            {
              text: 'Operations',
              items: [
                { text: 'Local tryout without TLS', link: '/local-prod' },
                { text: 'External edge Traefik', link: '/external-traefik' },
                { text: 'Backup and restore', link: '/backup' },
              ],
            },
            {
              text: 'Agents',
              items: [
                { text: 'Agent network and security', link: '/agent-network' },
                { text: 'Agent PSK', link: '/agent-psk' },
              ],
            },
            {
              text: 'Development',
              items: [{ text: 'Development', link: '/dev' }],
            },
            {
              text: 'Also',
              items: [
                { text: 'GPU host agent install', link: AGENT },
                { text: 'Student registration provisioning', link: PREPARE },
              ],
            },
          ],
        },
      },
      zh: {
        label: '中文',
        lang: 'zh-CN',
        description: 'GPU 服务器访问控制台',
        themeConfig: {
          nav: [
            { text: '指南', link: '/zh/' },
            { text: 'GitHub', link: GITHUB },
          ],
          outline: { label: '本页目录' },
          docFooter: { prev: '上一页', next: '下一页' },
          returnToTopLabel: '返回顶部',
          sidebarMenuLabel: '菜单',
          darkModeSwitchLabel: '外观',
          lightModeSwitchTitle: '切换到浅色模式',
          darkModeSwitchTitle: '切换到深色模式',
          langMenuLabel: '切换语言',
          sidebar: [
            {
              text: '概览',
              items: [
                { text: 'GSAD', link: '/zh/' },
                { text: '用户手册', link: '/zh/gsad-user-manual' },
                { text: '管理员手册', link: '/zh/gsad-admin-manual' },
              ],
            },
            {
              text: '运维',
              items: [
                { text: '本地无 TLS 试用', link: '/zh/local-prod' },
                { text: '接入已有边缘 Traefik', link: '/zh/external-traefik' },
                { text: '备份与恢复', link: '/zh/backup' },
              ],
            },
            {
              text: 'Agent',
              items: [
                { text: 'Agent 网络与安全', link: '/zh/agent-network' },
                { text: 'Agent PSK', link: '/zh/agent-psk' },
              ],
            },
            {
              text: '开发',
              items: [{ text: '开发环境', link: '/zh/dev' }],
            },
            {
              text: '相关项目',
              items: [
                { text: 'GPU 主机 Agent 安装', link: AGENT },
                { text: '学生注册开通流程', link: PREPARE },
              ],
            },
          ],
        },
      },
    },
  }),
)

// mermaid 11 no longer depends on debug; the plugin still lists it for prebundle.
const include = config.vite?.optimizeDeps?.include
if (include) {
  config.vite!.optimizeDeps!.include = include.filter((id) => id !== 'debug')
}

export default config
