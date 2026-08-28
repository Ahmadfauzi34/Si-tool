import {labCycleC} from './c';

export function labCycleB(depth = 0): string {
  return depth >= 3 ? 'b' : `b>${labCycleC(depth + 1)}`;
}
