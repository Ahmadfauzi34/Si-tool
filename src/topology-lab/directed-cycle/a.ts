import {labCycleB} from './b';

export function labCycleA(depth = 0): string {
  return depth >= 3 ? 'a' : `a>${labCycleB(depth + 1)}`;
}
