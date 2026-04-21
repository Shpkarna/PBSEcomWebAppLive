import React from 'react';

export interface ProductFormState {
  name: string; sku: string; barcode: string;
  stock_price: string; sell_price: string; description: string;
  category: string;
  discount: '' | 'Discount percentage' | 'Discount amount';
  discount_value: string;
  discount_type: '' | 'per quantity' | 'Total quantity' | 'Category';
  stock_quantity: string; gst_rate: string;
}

export const defaultFormState: ProductFormState = {
  name: '', sku: '', barcode: '', stock_price: '', sell_price: '',
  description: '', category: '', discount: '', discount_value: '', discount_type: '', stock_quantity: '0', gst_rate: '0.18',
};

interface Props {
  formState: ProductFormState;
  categoryOptions: string[];
  categoriesLoading: boolean;
  editingId: string | null;
  saving: boolean;
  onFieldChange: (field: keyof ProductFormState, value: string) => void;
  onImageFilesChange: (files: File[]) => void;
  onVideoFilesChange: (files: File[]) => void;
  selectedImageCount: number;
  selectedVideoCount: number;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
}

const gridStyle = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '15px' };
const noMb = { marginBottom: 0 };

export const AdminProductForm: React.FC<Props> = ({
  formState,
  categoryOptions,
  categoriesLoading,
  editingId,
  saving,
  onFieldChange,
  onImageFilesChange,
  onVideoFilesChange,
  selectedImageCount,
  selectedVideoCount,
  onSubmit,
  onCancel,
}) => (
  <div className="card" style={{ marginBottom: '30px' }}>
    <h3 style={{ marginTop: 0 }}>{editingId ? 'Edit Product' : 'Create Product'}</h3>
    <form onSubmit={onSubmit}>
      {(() => {
        const isDiscountPercentage = formState.discount === 'Discount percentage';
        const isDiscountAmount = formState.discount === 'Discount amount';
        return (
          <>
      <div style={gridStyle}>
        <div className="form-group" style={noMb}>
          <label htmlFor="name">Name</label>
          <input id="name" value={formState.name} onChange={(e) => onFieldChange('name', e.target.value)} required />
        </div>
        <div className="form-group" style={noMb}>
          <label htmlFor="sku">SKU</label>
          <input id="sku" value={formState.sku} onChange={(e) => onFieldChange('sku', e.target.value)} required />
        </div>
        <div className="form-group" style={noMb}>
          <label htmlFor="barcode">Barcode</label>
          <input id="barcode" value={formState.barcode} onChange={(e) => onFieldChange('barcode', e.target.value)} required />
        </div>
        <div className="form-group" style={noMb}>
          <label htmlFor="category">Category</label>
          <select
            id="category"
            value={formState.category}
            onChange={(e) => onFieldChange('category', e.target.value)}
            disabled={categoriesLoading}
          >
            <option value="">{categoriesLoading ? 'Loading categories...' : 'Select category'}</option>
            {categoryOptions.map((catName) => (
              <option key={catName} value={catName}>{catName}</option>
            ))}
          </select>
        </div>
        <div className="form-group" style={noMb}>
          <label htmlFor="stockPrice">Stock Price</label>
          <input id="stockPrice" type="number" step="0.01" min="0.01" value={formState.stock_price} onChange={(e) => onFieldChange('stock_price', e.target.value)} required />
        </div>
        <div className="form-group" style={noMb}>
          <label htmlFor="sellPrice">Sell Price</label>
          <input id="sellPrice" type="number" step="0.01" min="0.01" value={formState.sell_price} onChange={(e) => onFieldChange('sell_price', e.target.value)} required />
        </div>
        <div className="form-group" style={noMb}>
          <label htmlFor="stockQuantity">Stock Quantity</label>
          <input id="stockQuantity" type="number" step="1" min="0" value={formState.stock_quantity} onChange={(e) => onFieldChange('stock_quantity', e.target.value)} required />
        </div>
        <div className="form-group" style={noMb}>
          <label htmlFor="gstRate">GST Rate (0-1)</label>
          <input id="gstRate" type="number" step="0.01" min="0" max="1" value={formState.gst_rate} onChange={(e) => onFieldChange('gst_rate', e.target.value)} required />
        </div>
        <div className="form-group" style={noMb}>
          <label htmlFor="discount">Discount</label>
          <select id="discount" value={formState.discount} onChange={(e) => onFieldChange('discount', e.target.value)}>
            <option value="">Select discount</option>
            <option value="Discount percentage">Discount percentage</option>
            <option value="Discount amount">Discount amount</option>
          </select>
        </div>
        <div className="form-group" style={noMb}>
          <label htmlFor="discountValue">Discount Value</label>
          <input
            id="discountValue"
            type="number"
            step="0.01"
            min="0"
            max={isDiscountPercentage ? 100 : undefined}
            value={formState.discount_value}
            onChange={(e) => onFieldChange('discount_value', e.target.value)}
            disabled={!formState.discount}
            placeholder={isDiscountPercentage ? 'Enter percentage (0-100)' : isDiscountAmount ? 'Enter amount (>= 0)' : 'Select discount first'}
          />
        </div>
        <div className="form-group" style={noMb}>
          <label htmlFor="discountType">Discount Type</label>
          <select id="discountType" value={formState.discount_type} onChange={(e) => onFieldChange('discount_type', e.target.value)}>
            <option value="">Select discount type</option>
            <option value="per quantity">per quantity</option>
            <option value="Total quantity">Total quantity</option>
            <option value="Category">Category</option>
          </select>
        </div>
      </div>
      {formState.discount && (
        <p style={{ color: '#666', fontSize: 12, marginTop: 8 }}>
          {isDiscountPercentage ? 'Discount value accepts percentage only (0 to 100).' : 'Discount value accepts amount only (0 or greater).'}
        </p>
      )}
          </>
        );
      })()}
      <div className="form-group" style={{ marginTop: '15px' }}>
        <label htmlFor="description">Description</label>
        <textarea id="description" rows={3} value={formState.description} onChange={(e) => onFieldChange('description', e.target.value)} />
      </div>

      <div className="form-group" style={{ marginTop: '15px' }}>
        <label htmlFor="productImages">Product Images (multiple)</label>
        <input
          id="productImages"
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => onImageFilesChange(Array.from(e.target.files || []))}
        />
        <small style={{ color: '#666' }}>{selectedImageCount} image file(s) selected</small>
      </div>

      <div className="form-group" style={{ marginTop: '15px' }}>
        <label htmlFor="productVideos">Product Videos (multiple)</label>
        <input
          id="productVideos"
          type="file"
          accept="video/*"
          multiple
          onChange={(e) => onVideoFilesChange(Array.from(e.target.files || []))}
        />
        <small style={{ color: '#666' }}>{selectedVideoCount} video file(s) selected</small>
      </div>

      {!editingId && (
        <p style={{ color: '#666', fontSize: 12, marginTop: 8 }}>
          You can select media now. Selected files will be uploaded after product creation.
        </p>
      )}

      <div style={{ display: 'flex', gap: '10px' }}>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Saving...' : editingId ? 'Update Product' : 'Create Product'}
        </button>
        {editingId && (
          <button type="button" className="btn btn-secondary" onClick={onCancel}>Cancel Edit</button>
        )}
      </div>
    </form>
  </div>
);
