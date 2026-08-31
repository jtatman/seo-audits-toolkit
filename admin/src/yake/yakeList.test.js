import { YakeList } from './index';
import { renderResourceComponent, waitForListToRender } from '../testUtils';

test('YakeList renders without crashing', async () => {
  const { container } = renderResourceComponent(
    <YakeList resource="keywords/yake" basePath="/keywords/yake" />
  );
  await waitForListToRender(container);
});
