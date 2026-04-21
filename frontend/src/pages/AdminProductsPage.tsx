import React, { useEffect, useState } from 'react';
import { productService, Product, ProductMediaItem } from '../services/productService';
import { categoryService, CategoryRow } from '../services/categoryService';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { authService } from '../services/authService';
import { AdminProductForm, ProductFormState, defaultFormState } from '../components/AdminProductForm';
import { AdminProductTable } from '../components/AdminProductTable';

export const AdminProductsPage: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [canNextPage, setCanNextPage] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formExpanded, setFormExpanded] = useState(true);
  const [formState, setFormState] = useState<ProductFormState>(defaultFormState);
  const [isAdmin, setIsAdmin] = useState(false);
  const [categories, setCategories] = useState<CategoryRow[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [videoFiles, setVideoFiles] = useState<File[]>([]);
  const [mediaItems, setMediaItems] = useState<ProductMediaItem[]>([]);

  useEffect(() => { void resolveUserRole(); void loadCategories(); }, []);
  useEffect(() => { void loadProducts(page, pageSize); }, [page, pageSize]);

  const resolveUserRole = async () => {
    try {
      const user = await authService.getCurrentUser();
      setIsAdmin(user?.role === 'admin');
    } catch {
      setIsAdmin(false);
    }
  };

  const loadProducts = async (targetPage: number = page, targetPageSize: number = pageSize) => {
    try {
      setLoading(true);
      setError('');
      const skip = (targetPage - 1) * targetPageSize;
      const rows = await productService.getProducts(skip, targetPageSize);
      setProducts(rows);
      setCanNextPage(rows.length === targetPageSize);
    }
    catch { setError('Failed to load products. Please ensure you are logged in as admin.'); }
    finally { setLoading(false); }
  };

  const loadCategories = async () => {
    try {
      setCategoriesLoading(true);
      setCategories(await categoryService.list(0, 200));
    } catch {
      setCategories([]);
    } finally {
      setCategoriesLoading(false);
    }
  };

  const clearMessages = () => { setMessage(''); setError(''); };
  const resetForm = (expandForm: boolean = true) => {
    setFormState(defaultFormState);
    setEditingId(null);
    setFormExpanded(expandForm);
    setImageFiles([]);
    setVideoFiles([]);
    setMediaItems([]);
  };
  const onFieldChange = (field: keyof ProductFormState, value: string) => {
    setFormState((prev) => {
      if (field === 'discount') {
        const typedDiscount = value as ProductFormState['discount'];
        return { ...prev, discount: typedDiscount, discount_value: '' };
      }
      if (field === 'discount_type') {
        const typedDiscountType = value as ProductFormState['discount_type'];
        return { ...prev, discount_type: typedDiscountType };
      }
      return { ...prev, [field]: value };
    });
  };

  const loadMedia = async (productId: string) => {
    try {
      const items = await productService.listProductMedia(productId);
      setMediaItems(items);
    } catch {
      setMediaItems([]);
    }
  };

  const validateForm = (): boolean => {
    if (!formState.name.trim() || !formState.sku.trim() || !formState.barcode.trim()) { setError('Name, SKU, and barcode are required.'); return false; }
    const sp = Number(formState.stock_price), slp = Number(formState.sell_price);
    const sq = Number(formState.stock_quantity), gr = Number(formState.gst_rate);
    if (Number.isNaN(sp) || sp <= 0) { setError('Stock price must be greater than 0.'); return false; }
    if (Number.isNaN(slp) || slp <= 0) { setError('Sell price must be greater than 0.'); return false; }
    if (Number.isNaN(sq) || sq < 0) { setError('Stock quantity must be 0 or greater.'); return false; }
    if (Number.isNaN(gr) || gr < 0 || gr > 1) { setError('GST rate must be between 0 and 1.'); return false; }

    const discount = formState.discount;
    const discountValueStr = formState.discount_value.trim();
    const discountType = formState.discount_type.trim();
    if (discount) {
      if (!discountValueStr) { setError('Discount value is required when discount is selected.'); return false; }
      const dv = Number(discountValueStr);
      if (Number.isNaN(dv)) { setError('Discount value must be a valid number.'); return false; }
      if (discount === 'Discount percentage' && (dv < 0 || dv > 100)) {
        setError('Discount percentage must be between 0 and 100.');
        return false;
      }
      if (discount === 'Discount amount' && dv < 0) {
        setError('Discount amount must be 0 or greater.');
        return false;
      }
      if (!discountType) {
        setError('Discount type is required when discount is selected.');
        return false;
      }
    } else if (discountValueStr) {
      setError('Select discount before entering discount value.');
      return false;
    }

    return true;
  };

  const toPayload = () => ({
    name: formState.name.trim(), sku: formState.sku.trim(), barcode: formState.barcode.trim(),
    stock_price: Number(formState.stock_price), sell_price: Number(formState.sell_price),
    description: formState.description.trim() || undefined, category: formState.category.trim() || undefined,
    discount: formState.discount || undefined,
    discount_value: formState.discount ? Number(formState.discount_value) : undefined,
    discount_type: formState.discount_type || undefined,
    stock_quantity: Number(formState.stock_quantity), gst_rate: Number(formState.gst_rate),
  });

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault(); clearMessages();
    if (!validateForm()) return;
    try {
      setSaving(true);
      let savedProductId = editingId;
      if (editingId) {
        const updated = await productService.updateProduct(editingId, toPayload());
        savedProductId = updated.id;
        setMessage('Product updated successfully.');
      } else {
        const created = await productService.createProduct(toPayload());
        savedProductId = created.id;
        setMessage('Product created successfully.');
      }

      if (savedProductId && (imageFiles.length > 0 || videoFiles.length > 0)) {
        await productService.uploadProductMedia(savedProductId, imageFiles, videoFiles);
        setMessage('Product saved and media uploaded successfully.');
      }

      resetForm(false);
      await loadProducts(page, pageSize);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to save product. Please check product values and permissions.');
    }
    finally { setSaving(false); }
  };

  const handleEdit = (product: Product) => {
    clearMessages(); setEditingId(product.id);
    setFormExpanded(true);
    setFormState({ name: product.name, sku: product.sku, barcode: product.barcode,
      stock_price: String(product.stock_price), sell_price: String(product.sell_price),
      description: product.description || '', category: product.category || '',
      discount: product.discount || '', discount_value: product.discount_value != null ? String(product.discount_value) : '',
      discount_type: product.discount_type || '',
      stock_quantity: String(product.stock_quantity), gst_rate: String(product.gst_rate) });
    setImageFiles([]);
    setVideoFiles([]);
    void loadMedia(product.id);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDelete = async (product: Product) => {
    clearMessages();
    if (!window.confirm('Delete product "' + product.name + '"? This cannot be undone.')) return;
    try { await productService.deleteProduct(product.id); setMessage('Product deleted successfully.');
      if (editingId === product.id) resetForm(); await loadProducts(page, pageSize);
    } catch { setError('Unable to delete product.'); }
  };

  return (
    <ProtectedRoute requiredFunctionality="inventory_manage">
      <div className="container" style={{ marginTop: '30px', marginBottom: '50px' }}>
        <h1>Manage Inventory</h1>
        <p>Create and update products and stock levels.</p>
        {message && <div className="alert alert-success">{message}</div>}
        {error && <div className="alert alert-danger">{error}</div>}
        <div className="card" style={{ marginBottom: '30px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0 }}>{editingId ? 'Edit Product' : 'Create Product'}</h3>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setFormExpanded((prev) => !prev)}
              disabled={!!editingId}
              style={{ padding: '6px 12px' }}
            >
              {editingId ? 'Locked While Editing' : formExpanded ? 'Collapse' : 'Expand'}
            </button>
          </div>

          {formExpanded && (
            <>
              <div style={{ marginTop: '14px' }}>
                <AdminProductForm formState={formState} editingId={editingId} saving={saving}
                  categoryOptions={categories.map((c) => c.name)}
                  categoriesLoading={categoriesLoading}
                  onFieldChange={onFieldChange}
                  onImageFilesChange={setImageFiles}
                  onVideoFilesChange={setVideoFiles}
                  selectedImageCount={imageFiles.length}
                  selectedVideoCount={videoFiles.length}
                  onSubmit={handleSubmit}
                  onCancel={resetForm}
                />
              </div>

              {editingId && (
                <div className="card" style={{ marginBottom: 0 }}>
                  <h3 style={{ marginTop: 0 }}>Uploaded Media</h3>
                  {mediaItems.length === 0 ? (
                    <p style={{ color: '#666' }}>No media uploaded for this product yet.</p>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
                      {mediaItems.map((item) => (
                        <div key={item.id} style={{ border: '1px solid #ddd', borderRadius: 6, padding: 8 }}>
                          {item.media_type === 'image' ? (
                            <img
                              src={item.url}
                              alt={item.filename}
                              style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 4, marginBottom: 6 }}
                            />
                          ) : (
                            <video
                              src={item.url}
                              controls
                              style={{ width: '100%', height: 120, borderRadius: 4, marginBottom: 6, background: '#000' }}
                            />
                          )}
                          <div style={{ fontSize: 12, color: '#555', wordBreak: 'break-word' }}>{item.filename}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        <AdminProductTable products={products} loading={loading} isAdmin={isAdmin}
          page={page}
          pageSize={pageSize}
          canNextPage={canNextPage}
          onRefresh={() => void loadProducts(page, pageSize)}
          onPageChange={(nextPage) => {
            if (nextPage < 1) return;
            setPage(nextPage);
          }}
          onPageSizeChange={(nextPageSize) => {
            setPageSize(nextPageSize);
            setPage(1);
          }}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      </div>
    </ProtectedRoute>
  );
};
