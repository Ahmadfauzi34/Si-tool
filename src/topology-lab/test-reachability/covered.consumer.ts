import {coveredValue} from './covered.service';

export function consumeCoveredValue(): string {
  return `consumer:${coveredValue()}`;
}
