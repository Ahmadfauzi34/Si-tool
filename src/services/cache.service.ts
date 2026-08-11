export class CacheService {
  private cache = new Map();
  private userCache = new Map();

  set(key: string, value: unknown) {
    const cacheKey = key + Date.now();
    this.cache.set(cacheKey, value);
  }

  setUser(userId: string, tenantId: string, data: unknown) {
    const key = userId + tenantId;
    this.userCache.set(key, data);
  }
}
