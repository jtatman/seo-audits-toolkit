import { WebsiteList } from './index';
import { renderResourceComponent, waitForListToRender } from '../testUtils';

test('WebsiteList renders without crashing', async () => {
  const { container } = renderResourceComponent(
    <WebsiteList resource="website_user" />
  );
  await waitForListToRender(container);
});
