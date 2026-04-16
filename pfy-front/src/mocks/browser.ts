import { setupWorker } from 'msw/browser';

import { authHandlers } from '@/mocks/handlers/auth';
import { bookmarkHandlers } from '@/mocks/handlers/bookmark';
import { commonCodeHandlers } from '@/mocks/handlers/commonCode/commonCodeHandlers';
import { localeHandlers } from '@/mocks/handlers/locale/localeHandlers';
import { menuHandlers } from '@/mocks/handlers/menu';
import { routerHandlers } from '@/mocks/handlers/routes/routerHandlers';
import { templateHandlers } from '@/mocks/handlers/template/templateHandlers';

import { SPhandlers } from './handlers/index';

export const worker = setupWorker(
  ...SPhandlers,
  ...routerHandlers,
  ...authHandlers,
  ...menuHandlers,
  ...bookmarkHandlers,
  ...localeHandlers,
  ...commonCodeHandlers,
  ...templateHandlers
);
