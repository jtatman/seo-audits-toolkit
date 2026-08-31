import { BertList } from './index';
import { renderResourceComponent, waitForListToRender } from '../testUtils';

test('BertList renders without crashing', async () => {
  const { container } = renderResourceComponent(
    <BertList resource="summarize" />
  );
  await waitForListToRender(container);
});
