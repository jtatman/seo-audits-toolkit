import { LighthouseList } from './index';
import { renderResourceComponent, waitForListToRender } from '../testUtils';

test('LighthouseList renders without crashing', async () => {
  const { container } = renderResourceComponent(
    <LighthouseList resource="lighthouse" basePath="/lighthouse" />
  );
  await waitForListToRender(container);
});
