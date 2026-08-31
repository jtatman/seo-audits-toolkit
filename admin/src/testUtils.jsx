import { render, waitFor } from '@testing-library/react';
import { AdminContext, testDataProvider, TestMemoryRouter } from 'react-admin';

// Minimal render harness for smoke-testing a single react-admin List/Show/
// Create/Edit component in isolation, without bootstrapping the full <Admin>
// app (auth, real data provider). AdminContext supplies theme/i18n/data
// provider context (and defaults to an empty getList/getOne/etc that throws
// unless overridden below); TestMemoryRouter supplies the React Router
// context several react-admin UI components (EditButton, DeleteButton, row
// links) need internally.
export const renderResourceComponent = (ui) =>
  render(
    <TestMemoryRouter>
      <AdminContext
        dataProvider={testDataProvider({
          getList: () => Promise.resolve({ data: [], total: 0 }),
        })}
      >
        {ui}
      </AdminContext>
    </TestMemoryRouter>
  );

// react-admin's List renders its data-driven content only after an async
// data-provider round trip resolves, even against the fake provider - wait
// rather than asserting synchronously. With an empty result set (the getList
// override above), react-admin v5 shows its RaEmpty "no results" state, not
// a Datagrid/pagination footer (a real behavior change from v3, which showed
// pagination chrome even when empty) - .list-page is the one container class
// react-admin's own List tests assert on, present in both the empty and
// populated states.
export const waitForListToRender = (container) =>
  waitFor(() => expect(container.querySelector('.list-page')).not.toBeNull());
