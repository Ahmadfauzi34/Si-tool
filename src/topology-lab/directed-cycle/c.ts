import {labCycleA} from './a';

export function labCycleC(depth = 0): string {
  return depth >= 3 ? 'c' : `c>${labCycleA(depth + 1)}`;
}
