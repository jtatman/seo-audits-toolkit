import { render, waitFor } from '@testing-library/react';
import { ThemeProvider, createMuiTheme } from '@material-ui/core/styles';
import { TestContext } from 'ra-test';
import { lightTheme } from './layout/theme';

// Minimal render harness for smoke-testing a single react-admin List/Show/
// Create/Edit component in isolation, without bootstrapping the full <Admin>
// app (auth, real data provider, routing). TestContext alone isn't enough -
// several ra-ui-materialui components call useMediaQuery(theme.breakpoints),
// which throws without an MUI ThemeProvider in the tree.
export const renderResourceComponent = (ui) =>
  render(
    <ThemeProvider theme={createMuiTheme(lightTheme)}>
      <TestContext>{ui}</TestContext>
    </ThemeProvider>
  );

// react-admin's List renders its data-driven content (Datagrid/pagination)
// only after an async data-provider round trip resolves, even against
// TestContext's fake provider - wait for the pagination chrome rather than
// asserting synchronously. With an empty result set (TestContext's default),
// react-admin shows only the pagination footer, not a literal <table>.
export const waitForListToRender = (container) =>
  waitFor(() => expect(container.querySelector('.MuiTablePagination-root')).not.toBeNull());
