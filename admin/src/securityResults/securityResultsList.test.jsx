import { SecurityResultsList } from './index';
import { renderResourceComponent, waitForListToRender } from '../testUtils';

test('SecurityResultsList renders without crashing', async () => {
  const { container } = renderResourceComponent(
    <SecurityResultsList resource="security_details" />
  );
  await waitForListToRender(container);
});
