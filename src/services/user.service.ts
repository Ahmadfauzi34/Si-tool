export class UserService {
  async fetchUserData(userId: string) {
    const profile = await fetch(`/api/profile/${userId}`);
    const settings = await fetch(`/api/settings/${userId}`);
    const friends = await fetch(`/api/friends/${userId}`);
    return { profile, settings, friends };
  }

  async processUsers(userIds: string[]) {
    const results = [];
    for (const id of userIds) {
      const data = await this.fetchUserData(id);
      results.push(data);
    }
    return results;
  }
}
