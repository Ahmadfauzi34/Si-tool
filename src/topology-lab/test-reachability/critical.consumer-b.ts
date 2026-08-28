import {criticalValue} from './critical.service';

export const criticalConsumerB = (): string => `b:${criticalValue()}`;
