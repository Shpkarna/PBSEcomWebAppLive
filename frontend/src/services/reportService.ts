import api from './api';

export const reportService = {
  async getSalesReport(startDate?: string, endDate?: string) {
    const response = await api.get('/reports/sales/', {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
  },

  async getPurchaseReport(startDate?: string, endDate?: string) {
    const response = await api.get('/reports/purchases/', {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
  },

  async getStockReport() {
    const response = await api.get('/reports/stock/');
    return response.data;
  },

  async getCustomerReport() {
    const response = await api.get('/reports/customers/');
    return response.data;
  },

  async getVendorReport() {
    const response = await api.get('/reports/vendors/');
    return response.data;
  },

  async getCompanyFinances(startDate?: string, endDate?: string) {
    const response = await api.get('/reports/finances/', {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
  },

  async getLedger(category?: string, startDate?: string, endDate?: string) {
    const response = await api.get('/reports/ledger/', {
      params: { category, start_date: startDate, end_date: endDate },
    });
    return response.data;
  },
};
