import { SitemapList } from './index';
import { renderResourceComponent, waitForListToRender } from '../testUtils';

test('SitemapList renders without crashing', async () => {
  const { container } = renderResourceComponent(
    <SitemapList resource="sitemap" />
  );
  await waitForListToRender(container);
});
