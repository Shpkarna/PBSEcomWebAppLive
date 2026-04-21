import React, { useState, useEffect } from 'react';
import { orderService, cartService, ShippingAddress } from '../services/productService';
import { authService } from '../services/authService';

interface CheckoutPageProps { onOrderComplete: () => void; }

const ONLINE_PAYMENT_METHODS = new Set(['card', 'upi', 'netbanking']);

const getTomorrowDateString = (): string => {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const loadRazorpayScript = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    if ((window as any).Razorpay) {
      resolve();
      return;
    }

    const existingScript = document.querySelector('script[data-razorpay-checkout="true"]') as HTMLScriptElement | null;
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve());
      existingScript.addEventListener('error', () => reject(new Error('Failed to load Razorpay SDK')));
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.setAttribute('data-razorpay-checkout', 'true');
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Razorpay SDK'));
    document.body.appendChild(script);
  });
};

export const CheckoutPage: React.FC<CheckoutPageProps> = ({ onOrderComplete }) => {
  const [address, setAddress] = useState<ShippingAddress>({
    street1: '', street2: '', landmark: '', district: '', area: '', state: '', country: '', pincode: '', phone: ''
  });
  const [paymentMethod, setPaymentMethod] = useState('card');
  const [shipmentDate, setShipmentDate] = useState(getTomorrowDateString());
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [orderNumber, setOrderNumber] = useState('');

  // Pre-fill address from profile
  useEffect(() => {
    const loadProfileAddress = async () => {
      try {
        const profile = await authService.getProfile();
        const ad = profile.address_data;
        if (ad && (ad.street1 || ad.district || ad.state)) {
          setAddress({
            street1: ad.street1 || '', street2: ad.street2 || '', landmark: ad.landmark || '',
            district: ad.district || '', area: ad.area || '', state: ad.state || '',
            country: ad.country || '', pincode: ad.pincode || '', phone: ad.phone || '',
          });
        }
      } catch { /* ignore - user fills manually */ }
    };
    loadProfileAddress();
  }, []);

  const handleAddrChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setAddress(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true); setMessage('');
    try {
      const cart = await cartService.getCart();
      if (cart.items.length === 0) { setMessage('Your cart is empty'); return; }

      const items = cart.items.map(item => ({ product_id: item.product_id, quantity: item.quantity }));
      const cartQuoteId = cart.cart_quote_id;
      let order: any;

      if (ONLINE_PAYMENT_METHODS.has(paymentMethod)) {
        await loadRazorpayScript();
        const razorpayOrder = await orderService.createRazorpayOrder(items, paymentMethod, address, shipmentDate || undefined, cartQuoteId);

        const paymentResult = await new Promise<any>((resolve, reject) => {
          const Razorpay = (window as any).Razorpay;
          if (!Razorpay) {
            reject(new Error('Razorpay SDK unavailable'));
            return;
          }

          const rz = new Razorpay({
            key: razorpayOrder.key_id,
            amount: razorpayOrder.amount,
            currency: razorpayOrder.currency,
            name: 'Hatt',
            description: 'Sales Order Payment',
            order_id: razorpayOrder.razorpay_order_id,
            handler: (response: any) => resolve(response),
            modal: {
              ondismiss: () => reject(new Error('Payment cancelled by user')),
            },
            prefill: {
              contact: address.phone,
            },
            notes: {
              shipment_date: shipmentDate || '',
            },
            theme: {
              color: '#1e4db7',
            },
          });
          rz.open();
        });

        order = await orderService.createOrder(
          items,
          paymentMethod,
          address,
          shipmentDate || undefined,
          {
            razorpay_order_id: paymentResult.razorpay_order_id,
            razorpay_payment_id: paymentResult.razorpay_payment_id,
            razorpay_signature: paymentResult.razorpay_signature,
          },
          cartQuoteId
        );
      } else {
        order = await orderService.createOrder(items, paymentMethod, address, shipmentDate || undefined, undefined, cartQuoteId);
      }

      setOrderNumber(order.order.order_number);
      setMessage('Order created successfully!');
      await cartService.clearCart();
      onOrderComplete();
    } catch (err: any) {
      setMessage(err.response?.data?.detail || 'Failed to create order');
    } finally { setLoading(false); }
  };

  const defaultMin = getTomorrowDateString();

  const inputStyle: React.CSSProperties = { width: '100%', padding: '10px', border: '1px solid #ddd', borderRadius: '4px', fontFamily: 'inherit' };

  return (
    <div className="container" style={{ marginTop: '30px', marginBottom: '50px', maxWidth: '600px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <h1 style={{ margin: 0 }}>Checkout</h1>
        <a href="/cart" className="btn btn-secondary" style={{ textDecoration: 'none' }}>&#8592; Back to Cart</a>
      </div>
      <form onSubmit={handleSubmit}>
        <fieldset style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '20px', marginBottom: '20px' }}>
          <legend style={{ fontWeight: 700, fontSize: '16px', padding: '0 8px' }}>Delivery Address</legend>
          <div className="form-group"><label>Street Address Line 1 <span style={{ color: '#c00' }}>*</span></label>
            <input name="street1" value={address.street1} onChange={handleAddrChange} required style={inputStyle} placeholder="House / Flat No., Building, Street" /></div>
          <div className="form-group"><label>Street Address Line 2</label>
            <input name="street2" value={address.street2} onChange={handleAddrChange} style={inputStyle} placeholder="Apartment, suite, etc. (optional)" /></div>
          <div className="form-group"><label>Landmark <span style={{ color: '#c00' }}>*</span></label>
            <input name="landmark" value={address.landmark} onChange={handleAddrChange} required style={inputStyle} placeholder="Nearby landmark" /></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
            <div className="form-group"><label>District <span style={{ color: '#c00' }}>*</span></label>
              <input name="district" value={address.district} onChange={handleAddrChange} required style={inputStyle} /></div>
            <div className="form-group"><label>Area / Town / Region</label>
              <input name="area" value={address.area} onChange={handleAddrChange} style={inputStyle} /></div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
            <div className="form-group"><label>State <span style={{ color: '#c00' }}>*</span></label>
              <input name="state" value={address.state} onChange={handleAddrChange} required style={inputStyle} /></div>
            <div className="form-group"><label>Country <span style={{ color: '#c00' }}>*</span></label>
              <input name="country" value={address.country} onChange={handleAddrChange} required style={inputStyle} /></div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
            <div className="form-group"><label>PIN Code <span style={{ color: '#c00' }}>*</span></label>
              <input name="pincode" value={address.pincode} onChange={handleAddrChange} required style={inputStyle} placeholder="6-digit PIN" /></div>
            <div className="form-group"><label>Phone Number <span style={{ color: '#c00' }}>*</span></label>
              <input name="phone" value={address.phone} onChange={handleAddrChange} required style={inputStyle} placeholder="10-digit mobile" /></div>
          </div>
        </fieldset>

        <div className="form-group"><label>Preferred Shipment Date</label>
          <input type="date" value={shipmentDate} onChange={(e) => setShipmentDate(e.target.value)} min={defaultMin} style={inputStyle} /></div>
        <div className="form-group"><label>Payment Method</label>
          <select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)} style={inputStyle as any}>
            <option value="card">Credit/Debit Card</option>
            <option value="upi">UPI</option>
            <option value="netbanking">Net Banking</option>
            <option value="cod">Cash on Delivery (COD)</option>
          </select></div>
        <div className="card" style={{ marginBottom: '20px', backgroundColor: '#f0f4ff' }}>
          <p style={{ margin: 0, color: '#333' }}>
            <strong>Note:</strong> Please review your cart before placing the order. Payment will be processed according to your selected method.
          </p>
        </div>
        {message && (
          <div className={`alert ${orderNumber ? 'alert-success' : 'alert-danger'}`}>
            {message}{orderNumber && <p>Order Number: <strong>{orderNumber}</strong></p>}
            {orderNumber && <p><a href="/orders" style={{ color: '#155724' }}>View My Orders</a></p>}
          </div>
        )}
        <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
          {loading ? 'Placing Order...' : 'Place Order'}
        </button>
      </form>
    </div>
  );
};
