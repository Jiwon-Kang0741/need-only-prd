import vue from '@vitejs/plugin-vue';
import path from 'path';
import { ConfigEnv, defineConfig, loadEnv } from 'vite';
import tsconfigPaths from 'vite-tsconfig-paths';

/** 백엔드 미기동 시 axios 인터셉터·화면이 기대하는 최소 응답 봉투 */
const proxyErrorJsonBody = JSON.stringify({
  header: { responseCode: 'S0000', responseMessage: 'OK (proxy fallback)' },
  payload: null,
});

export default defineConfig((configEnv: ConfigEnv) => {
  const { mode } = configEnv;
  const env = loadEnv(mode, process.cwd());

  const isMock = env.VITE_USE_MOCK === 'true';
  /** 브라우저 요청 baseURL(비우면 같은 오리진 → dev 서버 프록시 경유, CORS 없음) */
  const devApiBase = env.VITE_API_BASE_URL?.trim() || '';
  /** dev 서버 프록시가 실제로 넘길 백엔드 주소(baseURL이 비어 있어도 8888로 전달) */
  const proxyTarget = isMock
    ? env.VITE_MOCK_BASE_URL || 'http://localhost:8081'
    : devApiBase || 'http://localhost:8888';

  return {
    plugins: [vue(), tsconfigPaths()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    build: {
      target: 'esnext',
    },
    // 프록시 설정
    server: {
      port: 8081,
      open: true,
      proxy: {
        '/online/api': {
          target: proxyTarget,
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on('error', (_err, _req, res) => {
              if (!res.headersSent) {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(proxyErrorJsonBody);
              }
            });
          },
        },
        '/online/mvcJson': {
          target: proxyTarget,
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on('error', (_err, _req, res) => {
              if (!res.headersSent) {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(proxyErrorJsonBody);
              }
            });
          },
        },
        '/online/files': {
          target: proxyTarget,
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on('error', (_err, _req, res) => {
              if (!res.headersSent) {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(proxyErrorJsonBody);
              }
            });
          },
        },
        '/online/download': {
          target: proxyTarget,
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on('error', (_err, _req, res) => {
              if (!res.headersSent) {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(proxyErrorJsonBody);
              }
            });
          },
        },
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: ``,
        },
      },
    },
    optimizeDeps: {
      exclude: ['msw'],
    },
  };
});
