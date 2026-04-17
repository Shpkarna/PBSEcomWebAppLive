import React, { useState } from 'react';
import { CategoryDiscountType } from '../services/categoryService';

type Props = {
  onSubmit: (payload: {
    name: string;
    description?: string;
    discount_type?: CategoryDiscountType;
    discount_value?: number;
  }) => Promise<void>;
};

const DISCOUNT_OPTIONS: CategoryDiscountType[] = ['Discount percentage', 'Discount amount'];

export const CategoryForm: React.FC<Props> = ({ onSubmit }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [discountType, setDiscountType] = useState<CategoryDiscountType | ''>('');
  const [discountValue, setDiscountValue] = useState('');

  const handleDiscountTypeChange = (value: CategoryDiscountType | '') => {
    setDiscountType(value);
    setDiscountValue('');
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit({
      name,
      description,
      discount_type: discountType || undefined,
      discount_value: discountValue === '' ? undefined : Number(discountValue),
    });
    setName('');
    setDescription('');
    setDiscountType('');
    setDiscountValue('');
  };
  return (
    <form onSubmit={submit} className="card" style={{ marginBottom: 20 }}>
      <h3>Create Category</h3>
      <input className="form-input" value={name} onChange={e => setName(e.target.value)} placeholder="Name" required />
      <input className="form-input" value={description} onChange={e => setDescription(e.target.value)} placeholder="Description" />
      <label style={{ fontWeight: 600, marginTop: 8 }}>Discount</label>
      <select className="form-input" value={discountType} onChange={e => handleDiscountTypeChange(e.target.value as CategoryDiscountType | '')} required>
        <option value="">Select Discount Type</option>
        {DISCOUNT_OPTIONS.map((option) => (
          <option key={option} value={option}>{option}</option>
        ))}
      </select>
      <label style={{ fontWeight: 600, marginTop: 8 }}>
        Discount Value {discountType === 'Discount percentage' ? '(%)' : discountType === 'Discount amount' ? '(Amount)' : ''}
      </label>
      <input
        className="form-input"
        type="number"
        step="0.01"
        min="0"
        max={discountType === 'Discount percentage' ? '100' : undefined}
        value={discountValue}
        onChange={e => setDiscountValue(e.target.value)}
        disabled={!discountType}
        placeholder={discountType === 'Discount percentage' ? 'Discount percentage (0-100)' : 'Discount amount'}
        required
      />
      {discountType === 'Discount percentage' && <small style={{ color: '#666' }}>Enter a percentage between 0 and 100.</small>}
      {discountType === 'Discount amount' && <small style={{ color: '#666' }}>Enter the discount amount value.</small>}
      <button className="btn btn-primary" type="submit">Create</button>
    </form>
  );
};
