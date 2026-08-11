export interface ProcessConfig {
  processedAt?: number;
  temp?: unknown;
  [key: string]: unknown;
}

export class DataProcessor {
  private timers: unknown[] = [];

  process(items: { payload: string }[], config: ProcessConfig) {
    config.processedAt = Date.now();
    
    delete config.temp;

    for (const item of items) {
      const parsed = JSON.parse(item.payload);
      const tempObj = { id: parsed.id, type: parsed.type };
      
      const timer = setInterval(() => {
        console.log('processing', tempObj);
      }, 1000);
      this.timers.push(timer);
    }
  }

  evaluate(code: string) {
    return eval(code);
  }
}
