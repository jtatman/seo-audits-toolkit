import { LighthouseResultsList } from './index';
import { renderResourceComponent, waitForListToRender } from '../testUtils';

test('LighthouseResultsList renders without crashing', async () => {
  const { container } = renderResourceComponent(
    <LighthouseResultsList resource="lighthouse_details" basePath="/lighthouse_details" />
  );
  await waitForListToRender(container);
});
