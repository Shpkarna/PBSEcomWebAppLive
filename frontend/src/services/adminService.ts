import api from './api';

export interface SalesOrderFilters {
  orderId?: string;
  orderNumber?: string;
  dateFrom?: string;
  dateTo?: string;
  amountMin?: number;
  amountMax?: number;
}

export interface SalesOrderListResponse {
  items: any[];
  total: number;
  skip: number;
  limit: number;
}

export interface DataSyncJob {
  id: string;
  entity: string;
  job_type: 'import' | 'export';
  status: string;
  requested_by: string;
  source_filename?: string;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  processed_rows: number;
  success_rows: number;
  failed_rows: number;
  errors: Array<{ row: number; errors: string[] }>;
}

export const adminService = {
  async loadSampleData() {
    const res = await api.post('/admin/load-sample-data');
    return res.data;
  },

  async discardSampleData() {
    const res = await api.post('/admin/discard-sample-data');
    return res.data;
  },

  async listUsers(skip = 0, limit = 200, search?: string) {
    const params: Record<string, unknown> = { skip, limit };
    if (search && search.trim()) params.search = search.trim();
    const res = await api.get('/admin/users', { params });
    return res.data;
  },

  async listAllUsers(search?: string) {
    const PAGE_SIZE = 200;
    let all: Record<string, unknown>[] = [];
    let skip = 0;
    while (true) {
      const batch = await this.listUsers(skip, PAGE_SIZE, search);
      if (!Array.isArray(batch) || batch.length === 0) break;
      all = all.concat(batch);
      if (batch.length < PAGE_SIZE) break;
      skip += PAGE_SIZE;
    }
    return all;
  },

  async createUser(data: Record<string, unknown>) {
    const res = await api.post('/admin/users', data);
    return res.data;
  },

  async updateUser(username: string, data: Record<string, unknown>) {
    const res = await api.put(`/admin/users/${username}`, data);
    return res.data;
  },

  async deleteUser(username: string) {
    await api.delete(`/admin/users/${username}`);
  },

  async listOrders(skip = 0, limit = 50, orderStatus?: string) {
    const params: Record<string, unknown> = { skip, limit };
    if (orderStatus) params.order_status = orderStatus;
    const res = await api.get('/admin/orders', { params });
    return res.data;
  },

  async updateOrderStatus(orderId: string, newStatus: string) {
    const res = await api.put(`/admin/orders/${orderId}/status`, null, { params: { new_status: newStatus } });
    return res.data;
  },

  async listSalesOrders(skip = 0, limit = 20, filters?: SalesOrderFilters): Promise<SalesOrderListResponse> {
    const params: Record<string, unknown> = { skip, limit };
    if (filters?.orderId?.trim()) params.order_id = filters.orderId.trim();
    if (filters?.orderNumber?.trim()) params.order_number = filters.orderNumber.trim();
    if (filters?.dateFrom) params.date_from = filters.dateFrom;
    if (filters?.dateTo) params.date_to = filters.dateTo;
    if (filters?.amountMin != null) params.amount_min = filters.amountMin;
    if (filters?.amountMax != null) params.amount_max = filters.amountMax;

    const res = await api.get('/admin/orders/sales', { params });
    return res.data;
  },

  async getPaymentGateway(gatewayId: string) {
    const res = await api.get(`/admin/payment-gateways/${gatewayId}`);
    return res.data as { gatewayId: string; key_id: string; key_secret: string };
  },

  async updatePaymentGateway(gatewayId: string, data: { key_id: string; key_secret: string }) {
    const res = await api.put(`/admin/payment-gateways/${gatewayId}`, data);
    return res.data as { message: string };
  },

  async getMsg91Config() {
    const res = await api.get('/admin/company-config/msg91');
    return res.data as {
      authkey: string;
      template_id: string;
      sender_id: string;
      enable_mobile_otp_verification: boolean;
    };
  },

  async updateMsg91Config(data: {
    authkey: string;
    template_id: string;
    sender_id: string;
    enable_mobile_otp_verification: boolean;
  }) {
    const res = await api.put('/admin/company-config/msg91', data);
    return res.data as { message: string };
  },

  async getMiscConfig() {
    const res = await api.get('/admin/company-config/misc');
    return res.data as {
      enable_email_verification: boolean;
    };
  },

  async updateMiscConfig(data: { enable_email_verification: boolean }) {
    const res = await api.put('/admin/company-config/misc', data);
    return res.data as { message: string };
  },

  async listDataSyncEntities() {
    const res = await api.get('/admin/data-sync/entities');
    return res.data as { entities: string[] };
  },

  async createImportJob(entity: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post('/admin/data-sync/import-jobs', formData, {
      params: { entity },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data as { job_id: string; status: string; entity: string; job_type: 'import' };
  },

  async createExportJob(entity: string) {
    const res = await api.post('/admin/data-sync/export-jobs', null, { params: { entity } });
    return res.data as { job_id: string; status: string; entity: string; job_type: 'export' };
  },

  async listDataSyncJobs(skip = 0, limit = 30) {
    const res = await api.get('/admin/data-sync/jobs', { params: { skip, limit } });
    return res.data as DataSyncJob[];
  },

  async downloadExportJob(jobId: string) {
    const res = await api.get(`/admin/data-sync/jobs/${jobId}/download`, { responseType: 'blob' });
    return res.data as Blob;
  },

  async downloadTemplate(entity: string) {
    const res = await api.get(`/admin/data-sync/templates/${entity}`, { responseType: 'blob' });
    return res.data as Blob;
  },

  async downloadErrorReport(jobId: string) {
    const res = await api.get(`/admin/data-sync/jobs/${jobId}/error-report`, { responseType: 'blob' });
    return res.data as Blob;
  },
};
