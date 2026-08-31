import { render, screen } from '@testing-library/react';
import App from './App';

test('App module imports without throwing', () => {
  expect(App).toBeDefined();
});

// Regression test for a real production bug: react-admin v5's
// MenuItemLink/DashboardMenuItem render MUI's MenuItem internally, which
// throws ("MenuListContext is missing") unless it sits inside an MUI
// MenuList/Menu ancestor. Our custom layout/Menu.jsx used to wrap its
// children in a plain <Box>, which crashed react-admin's error boundary
// into "Something went wrong" on every load. None of the per-resource List
// smoke tests caught this because they render a resource in isolation
// (AdminContext + a bare List), never the full App -> Layout -> Sidebar ->
// Menu chain where the bug actually lived. This test renders that full
// chain so a regression here fails loudly instead of shipping silently.
test('App renders the full layout without crashing (clean localStorage)', async () => {
    window.localStorage.clear();
    render(<App />);

    // "Something went wrong" is react-admin's own error-boundary fallback
    // text - if a child component throws during render, this is what a
    // real user sees instead of the app.
    expect(await screen.findByText(/dashboard/i)).toBeInTheDocument();
    expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();
});
