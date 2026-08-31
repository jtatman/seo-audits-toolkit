import { SecurityList } from './index';
import { renderResourceComponent, waitForListToRender } from '../testUtils';

test('SecurityList renders without crashing', async () => {
  const { container } = renderResourceComponent(
    <SecurityList resource="security" />
  );
  await waitForListToRender(container);
});
