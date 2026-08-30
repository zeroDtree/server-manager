import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

const config = withMermaid(
  defineConfig({
    title: 'GSAD',
    description: 'GPU Server Access Dashboard',
    base: '/server-manager/',
    ignoreDeadLinks: [/\.\.\//],
    themeConfig: {
      nav: [
        { text: 'Guide', link: '/' },
        { text: 'GitHub', link: 'https://github.com/zeroDtree/server-manager' },
      ],
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
            {
              text: 'GPU host agent install',
              link: 'https://github.com/zeroDtree/server-agent',
            },
            {
              text: 'Student registration provisioning',
              link: 'https://github.com/zeroDtree/account-prepare',
            },
          ],
        },
      ],
      socialLinks: [
        { icon: 'github', link: 'https://github.com/zeroDtree/server-manager' },
      ],
    },
  }),
)

// mermaid 11 no longer depends on debug; the plugin still lists it for prebundle.
const include = config.vite?.optimizeDeps?.include
if (include) {
  config.vite!.optimizeDeps!.include = include.filter((id) => id !== 'debug')
}

export default config
