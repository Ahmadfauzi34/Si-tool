import {criticalValue} from './critical.service';

export const criticalConsumerA = (): string => `a:${criticalValue()}`;
