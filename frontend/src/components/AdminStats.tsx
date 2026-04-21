import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { reportService } from '../services/reportService';

export const AdminStats: React.FC = () => {
  const navigate = useNavigate();
  const [salesReport, setSalesReport] = useState<any>(null);
  const [stockReport, setStockReport] = useState<any>(null);
  const [finances, setFinances] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [sales, stock, fin] = await Promise.all([
          reportService.getSalesReport(),
          reportService.getStockReport(),
          reportService.getCompanyFinances(),
        ]);
        setSalesReport(sales);
        setStockReport(stock);
        setFinances(fin);
      } catch {
        // Keep dashboard usable even if reports API is unavailable.
        setSalesReport(null);
        setStockReport(null);
        setFinances(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div style={{ padding: 20 }}>Loading stats…</div>;

  const stats = [
    {
      label: 'Total Sales',
      value: `₹${salesReport?.total_sales?.toFixed(2) || '0.00'}`,
      sub: `${salesReport?.total_orders || 0} orders`,
      bg: '#e3f2fd',
      color: '#1976d2',
      clickable: true,
      href: '/admin/sales-orders',
    },
    { label: 'GST Collected', value: `₹${finances?.total_gst_collected?.toFixed(2) || '0.00'}`, sub: '', bg: '#f3e5f5', color: '#7b1fa2' },
    { label: 'Net Profit', value: `₹${finances?.profit?.toFixed(2) || '0.00'}`, sub: `Margin: ${finances?.profit_margin?.toFixed(2) || '0'}%`, bg: '#e8f5e9', color: '#388e3c' },
    { label: 'Products', value: String(stockReport?.total_products || 0), sub: `Low Stock: ${stockReport?.low_stock_items || 0}`, bg: '#fce4ec', color: '#c2185b' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 20, marginBottom: 20 }}>
      {stats.map(s => (
        <div
          key={s.label}
          className="card"
          style={{
            backgroundColor: s.bg,
            cursor: s.clickable ? 'pointer' : 'default',
            transition: 'transform 0.15s ease',
          }}
          onClick={() => {
            if (s.clickable && s.href) navigate(s.href);
          }}
          role={s.clickable ? 'button' : undefined}
          tabIndex={s.clickable ? 0 : -1}
          onKeyDown={(e) => {
            if (s.clickable && s.href && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault();
              navigate(s.href);
            }
          }}
        >
          <h3 style={{ margin: '0 0 8px 0', color: s.color, fontSize: 16 }}>{s.label}</h3>
          <p style={{ margin: 0, fontSize: 26, fontWeight: 'bold', color: s.color }}>{s.value}</p>
          {s.sub && <p style={{ margin: '6px 0 0 0', color: '#666', fontSize: 13 }}>{s.sub}</p>}
        </div>
      ))}
    </div>
  );
};
