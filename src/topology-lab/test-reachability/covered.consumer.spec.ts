import {consumeCoveredValue} from './covered.consumer';

describe('covered consumer topology lab', () => {
  it('has a static path to its dependency', () => {
    expect(consumeCoveredValue()).toBe('consumer:covered');
  });
});
