import api from './api';

export type AppRole = 'admin' | 'business' | 'user' | 'customer' | 'vendor';

export interface Functionality {
  code: string;
  name: string;
  description: string;
}

export interface RoleMapping {
  role: AppRole;
  functionalities: string[];
}

export interface RbacUser {
  id: string;
  username: string;
  email?: string;
  role: AppRole;
  is_active: boolean;
}

export interface MyAccess {
  username: string;
  role: AppRole;
  functionalities: string[];
}

export const rbacService = {
  async getValidRoles(): Promise<AppRole[]> {
    const response = await api.get('/rbac/valid-roles');
    return response.data.roles;
  },

  async getFunctionalities(): Promise<Functionality[]> {
    const response = await api.get('/rbac/functionalities');
    return response.data;
  },

  async getRoleMappings(): Promise<RoleMapping[]> {
    const response = await api.get('/rbac/roles');
    return response.data.roles;
  },

  async updateRoleFunctionalities(role: AppRole, functionalities: string[]) {
    const response = await api.put(`/rbac/roles/${role}/functionalities`, functionalities);
    return response.data;
  },

  async getUsers(): Promise<RbacUser[]> {
    const response = await api.get('/rbac/users');
    return response.data.users;
  },

  async updateUserRole(username: string, role: AppRole) {
    const response = await api.put(`/rbac/users/${username}/role`, null, {
      params: { new_role: role },
    });
    return response.data;
  },

  async updateUserStatus(username: string, isActive: boolean) {
    const response = await api.put(`/rbac/users/${username}/status`, null, {
      params: { is_active: isActive },
    });
    return response.data;
  },

  async getMyAccess(): Promise<MyAccess> {
    const response = await api.get('/rbac/me');
    return response.data;
  },
};
