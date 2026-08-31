import { ExtractorList } from './index';
import { renderResourceComponent, waitForListToRender } from '../testUtils';

test('ExtractorList renders without crashing', async () => {
  const { container } = renderResourceComponent(
    <ExtractorList resource="extractor" basePath="/extractor" />
  );
  await waitForListToRender(container);
});
