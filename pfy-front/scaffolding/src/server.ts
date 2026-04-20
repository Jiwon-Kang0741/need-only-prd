import path from 'path';
import dotenv from 'dotenv';
// .env 위치를 server.ts 기준으로 명시 (실행 디렉터리에 무관하게 로드)
dotenv.config({ path: path.join(__dirname, '..', '.env') });

import express from 'express';
import cors from 'cors';

import scaffoldRouter from './routes/scaffold';
import generateRouter from './routes/generate';
import aiGenerateRouter from './routes/ai-generate';
import aiInterviewRouter from './routes/ai-interview-questions';
import aiAnnotateRouter from './routes/ai-annotate';
import interviewResultRouter from './routes/interview-result';
import annotateConstraintsRouter from './routes/annotate-constraints';
import { PATHS } from './utils/paths';

const app  = express();
const PORT = process.env.PORT ? Number(process.env.PORT) : 4000;

// ── Middleware ──────────────────────────────────────────────────────────────
app.use(cors());
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true }));

// ── Static UI (public/) ─────────────────────────────────────────────────────
app.use(express.static(PATHS.publicDir));

// ── API Routes ───────────────────────────────────────────────────────────────
app.use('/api/scaffold', scaffoldRouter);
app.use('/api/generate', generateRouter);
app.use('/api/ai-generate', aiGenerateRouter);
app.use('/api/ai-interview-questions', aiInterviewRouter);
app.use('/api/ai-annotate', aiAnnotateRouter);
app.use('/api/generate-interview-result', interviewResultRouter);
app.use('/api/annotate-constraints',     annotateConstraintsRouter);

// ── Health Check ─────────────────────────────────────────────────────────────
app.get('/api/health', (_req, res) => {
  res.json({
    status:      'ok',
    server:      'pfy-scaffolding',
    projectRoot: PATHS.projectRoot,
    timestamp:   new Date().toISOString(),
  });
});

// ── SPA Fallback → index.html ────────────────────────────────────────────────
app.get('*', (_req, res) => {
  res.sendFile(path.join(PATHS.publicDir, 'index.html'));
});

// ── Start ─────────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log('');
  console.log('╔══════════════════════════════════════════════════╗');
  console.log('║       pfy-front  Scaffolding Server              ║');
  console.log('╠══════════════════════════════════════════════════╣');
  console.log(`║  UI     →  http://localhost:${PORT}                  ║`);
  console.log(`║  API    →  http://localhost:${PORT}/api/scaffold      ║`);
  console.log(`║  Health →  http://localhost:${PORT}/api/health        ║`);
  console.log('╚══════════════════════════════════════════════════╝');
  console.log('');
  console.log(`  project root : ${PATHS.projectRoot}`);
  console.log(`  pages dir    : ${PATHS.pagesGenerated}`);
  console.log(`  router file  : ${PATHS.staticRoutes}`);
  console.log('');
});

export default app;
